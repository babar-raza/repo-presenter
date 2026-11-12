"""TC-014: `repo_presenter.acceptance.audit.attest.verify_attestation` is a pure function around
`gh attestation verify --format json` - every test here fakes the subprocess call; none makes a
live `gh` call or needs a real GitHub attestation bundle. That live proof is separate, later work
(gated on a restricted GitHub Environment and CODEOWNERS review this card cannot create), never
this card's own closeout evidence."""

from __future__ import annotations

import json
import subprocess

import pytest

from repo_presenter.acceptance.audit.attest import verify_attestation

ARTIFACT = "audit-findings-bundle.tar.gz"
WORKFLOW = "babar-raza/repo-presenter/.github/workflows/audit-writer.yml"
REF = "refs/heads/main"
DIGEST = "a" * 64


class _FakeRun:
    """Records every argv it was called with and returns a canned ``CompletedProcess``."""

    def __init__(self, returncode: int, stdout: bytes = b"[]") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> "subprocess.CompletedProcess[bytes]":
        self.calls.append(args)
        return subprocess.CompletedProcess(args, self.returncode, stdout=self.stdout)


def _bundle(sha256: str, *, artifact_name: str = ARTIFACT) -> bytes:
    """A fixture ``gh attestation verify --format json`` payload: a one-element list holding one
    verification result whose statement subject carries ``sha256``."""
    document = [
        {
            "verificationResult": {
                "statement": {
                    "_type": "https://in-toto.io/Statement/v1",
                    "subject": [{"name": artifact_name, "digest": {"sha256": sha256}}],
                    "predicateType": "https://slsa.dev/provenance/v1",
                    "predicate": {},
                },
                "signature": {"verified": True},
            }
        }
    ]
    return json.dumps(document).encode("utf-8")


def test_a_matching_signer_workflow_and_digest_verifies() -> None:
    runner = _FakeRun(returncode=0, stdout=_bundle(DIGEST))
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is True
    (call,) = runner.calls
    assert call == [
        "gh",
        "attestation",
        "verify",
        ARTIFACT,
        "--signer-workflow",
        f"{WORKFLOW}@{REF}",
        "--format",
        "json",
    ]


def test_a_missing_attestation_is_a_non_zero_exit_and_never_verifies() -> None:
    runner = _FakeRun(returncode=1, stdout=b"[]")
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_a_wrong_signer_workflow_is_never_verified() -> None:
    def strict(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
        expected = f"{WORKFLOW}@{REF}"
        ok = "--signer-workflow" in args and args[args.index("--signer-workflow") + 1] == expected
        return subprocess.CompletedProcess(
            args, 0 if ok else 1, stdout=_bundle(DIGEST) if ok else b"[]"
        )

    assert verify_attestation(ARTIFACT, "some/other/workflow.yml", DIGEST, runner=strict) is False
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, expected_ref="refs/heads/dev", runner=strict) is False
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=strict) is True


def test_a_tampered_subject_digest_is_never_verified() -> None:
    """``gh`` itself is happy (exit 0, a well-formed, validly-signed bundle) but the bundle's own
    subject digest does not match what the caller expected - this module's own check, which `gh`
    alone cannot make, must still refuse."""
    tampered_digest = "b" * 64
    runner = _FakeRun(returncode=0, stdout=_bundle(tampered_digest))
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_subject_digest_comparison_is_case_insensitive_and_prefix_tolerant() -> None:
    runner = _FakeRun(returncode=0, stdout=_bundle(DIGEST.upper()))
    assert verify_attestation(ARTIFACT, WORKFLOW, f"sha256:{DIGEST}", runner=runner) is True


def test_gh_missing_from_path_is_never_verified_not_an_exception() -> None:
    def missing_gh(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
        raise OSError("gh: command not found")

    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=missing_gh) is False


def test_gh_timeout_is_never_verified_not_an_exception() -> None:
    def timed_out(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
        raise subprocess.TimeoutExpired(cmd=args, timeout=120)

    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=timed_out) is False


def test_malformed_json_output_is_never_verified() -> None:
    runner = _FakeRun(returncode=0, stdout=b"not json at all {{{")
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_an_empty_verification_result_list_is_never_verified() -> None:
    runner = _FakeRun(returncode=0, stdout=b"[]")
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_a_non_list_json_document_is_never_verified() -> None:
    runner = _FakeRun(returncode=0, stdout=b'{"not": "a list"}')
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_a_result_entry_missing_the_expected_shape_contributes_no_digest() -> None:
    runner = _FakeRun(returncode=0, stdout=b'[{"unexpected": "shape"}]')
    assert verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner) is False


def test_defaults_to_refs_heads_main() -> None:
    runner = _FakeRun(returncode=0, stdout=_bundle(DIGEST))
    verify_attestation(ARTIFACT, WORKFLOW, DIGEST, runner=runner)
    (call,) = runner.calls
    assert call[-3] == f"{WORKFLOW}@refs/heads/main"
