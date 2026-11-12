"""TC-013: ``verify_attestation`` is a pure function around ``gh attestation verify`` - every
test here fakes the subprocess call (``runner``); none makes a live ``gh`` call or needs a real
GitHub attestation. That live proof is TC-014's and M1's own closeout evidence, not this card's."""

from __future__ import annotations

import subprocess

from repo_presenter.acceptance.record import verify_attestation

ARTIFACT = "candidate-bundle.tar.gz"
WORKFLOW = "babar-raza/repo-presenter/.github/workflows/writer.yml"
REF = "refs/heads/main"


class _FakeRun:
    """Records the exact argv it was called with and returns a canned ``CompletedProcess``."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[bytes]:
        self.calls.append(args)
        return subprocess.CompletedProcess(args, self.returncode)


def test_a_matching_signer_workflow_and_ref_verifies() -> None:
    runner = _FakeRun(returncode=0)
    assert verify_attestation(ARTIFACT, WORKFLOW, REF, runner=runner) is True
    (call,) = runner.calls
    assert call == [
        "gh",
        "attestation",
        "verify",
        ARTIFACT,
        "--signer-workflow",
        f"{WORKFLOW}@{REF}",
    ]


def test_a_non_zero_exit_is_never_verified() -> None:
    runner = _FakeRun(returncode=1)
    assert verify_attestation(ARTIFACT, WORKFLOW, REF, runner=runner) is False


def test_an_oserror_from_a_missing_gh_cli_is_never_verified() -> None:
    def missing_gh(args: list[str]) -> subprocess.CompletedProcess[bytes]:
        raise OSError("gh: command not found")

    assert verify_attestation(ARTIFACT, WORKFLOW, REF, runner=missing_gh) is False


def test_a_timeout_is_never_verified() -> None:
    def timed_out(args: list[str]) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd=args, timeout=120)

    assert verify_attestation(ARTIFACT, WORKFLOW, REF, runner=timed_out) is False


def test_the_wrong_ref_is_a_different_signer_workflow_argument() -> None:
    """A fake that only accepts the exact expected signer-workflow string stands in for `gh`
    itself rejecting a mismatched signer/workflow/ref - this module's job is only to pass the
    right argument and trust gh's own exit code, not to re-verify the signature itself."""

    def strict(args: list[str]) -> subprocess.CompletedProcess[bytes]:
        expected = f"{WORKFLOW}@{REF}"
        ok = "--signer-workflow" in args and args[args.index("--signer-workflow") + 1] == expected
        return subprocess.CompletedProcess(args, 0 if ok else 1)

    assert verify_attestation(ARTIFACT, WORKFLOW, REF, runner=strict) is True
    assert (
        verify_attestation(ARTIFACT, WORKFLOW, "refs/heads/not-main", runner=strict) is False
    )
    assert (
        verify_attestation(ARTIFACT, "some/other/workflow.yml", REF, runner=strict) is False
    )


def test_defaults_to_refs_heads_main() -> None:
    runner = _FakeRun(returncode=0)
    verify_attestation(ARTIFACT, WORKFLOW, runner=runner)
    (call,) = runner.calls
    assert call[-1] == f"{WORKFLOW}@refs/heads/main"
