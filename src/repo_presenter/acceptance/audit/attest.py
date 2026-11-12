"""TC-014 M9: ATTESTATION-VERIFICATION LOGIC for the hosted audit writer's own output.

As of this card's writing, the current GitHub mechanism for signing a build artifact and later
proving who produced it is the ``actions/attest-build-provenance`` GitHub Action (which emits a
Sigstore-backed, in-toto-shaped attestation bundle) and the ``gh attestation verify`` CLI
subcommand, whose ``--signer-workflow <owner>/<repo>/.github/workflows/<file>@<ref>`` flag
confirms the signer. This module trusts that name/flag exactly as
``repo_presenter.acceptance.record.verify_attestation`` (TC-013) already does for the published
candidate bundle - if GitHub has since renamed or changed this mechanism, whoever wires this
module to a real ``gh`` CLI must update the argv this module builds; nothing else in its contract
needs to change (see this card's closeout for this explicit caveat).

This module is a SECOND, independent attestation check, for a SECOND, independent artifact: the
M9 audit writer's own output (seed manifest / findings / scorecard), not the published README
candidate `record.py` already covers. It adds one thing `record.py`'s wrapper does not need:
verifying that the specific artifact a caller expected is the one that was actually signed, via
an explicit ``subject_digest`` comparison against the attestation's own subject digest - because
``gh attestation verify`` only proves the bundle is internally self-consistent and correctly
signed, never that it is signing the exact bytes a caller has in hand.

Every test here fakes the subprocess call; none makes a live ``gh`` call or needs a real GitHub
attestation bundle - that live proof is separate, later work gated on the owner actions this
card's own taskcard names (a restricted GitHub Environment and CODEOWNERS review), not something
this card's checks can create.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

__all__ = ["GhRunner", "verify_attestation"]

GhRunner = Callable[[list[str]], "subprocess.CompletedProcess[bytes]"]


def _default_runner(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
    return subprocess.run(args, capture_output=True, timeout=120, check=False)


def verify_attestation(
    artifact_path: str,
    expected_signer_workflow: str,
    subject_digest: str,
    *,
    expected_ref: str = "refs/heads/main",
    runner: GhRunner = _default_runner,
) -> bool:
    """``True`` only when ALL of the following hold:

    1. ``gh attestation verify <artifact_path> --signer-workflow
       <expected_signer_workflow>@<expected_ref> --format json`` exits ``0`` - the attestation
       exists, its signature is valid, and it was signed by exactly the expected workflow on the
       expected ref. This module trusts ``gh``'s own exit code for signature/signer verification,
       exactly as ``record.verify_attestation`` already does; neither module re-implements
       signature checking.
    2. ``gh``'s own stdout parses as JSON holding a non-empty list of verification results.
    3. At least one of those results' statement subjects carries a ``sha256`` digest equal to
       ``subject_digest`` (case-insensitively, with or without a ``sha256:`` prefix on either
       side). This is this module's OWN check: a bundle can be internally self-consistent and
       validly signed while attesting a DIFFERENT artifact than the one the caller has in hand
       (a tampered-but-still-well-formed bundle, or simply the wrong file) - ``gh`` alone cannot
       catch that, because it only checks the bundle against itself.

    Every failure mode returns ``False`` and never raises past the caller - a missing
    attestation (non-zero exit), a wrong signer/workflow/ref (also a non-zero exit, by ``gh``'s
    own rule), a tampered or mismatched subject digest, malformed/absent JSON output, and a
    ``gh`` CLI that is missing, times out, or raises for any other ``OSError`` reason are all
    ``False``. Unverifiable is never verified."""
    signer_workflow = f"{expected_signer_workflow}@{expected_ref}"
    try:
        result = runner(
            [
                "gh",
                "attestation",
                "verify",
                str(artifact_path),
                "--signer-workflow",
                signer_workflow,
                "--format",
                "json",
            ]
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    try:
        verifications = json.loads(result.stdout)
    except (ValueError, TypeError):
        return False
    if not isinstance(verifications, list) or not verifications:
        return False
    expected = _normalise_digest(subject_digest)
    for entry in verifications:
        if expected in _subject_digests(entry):
            return True
    return False


def _normalise_digest(digest: str) -> str:
    return digest.strip().lower().removeprefix("sha256:")


def _subject_digests(entry: Any) -> Sequence[str]:
    """Every ``sha256`` subject digest one ``gh attestation verify --format json`` result entry
    reports, normalised to bare lowercase hex. Never raises on a malformed or unexpected shape -
    a result this function cannot read contributes no digests, which can only make verification
    stricter, never looser."""
    digests: list[str] = []
    if not isinstance(entry, dict):
        return digests
    verification_result = entry.get("verificationResult")
    if not isinstance(verification_result, dict):
        return digests
    statement = verification_result.get("statement")
    if not isinstance(statement, dict):
        return digests
    subjects = statement.get("subject")
    if not isinstance(subjects, list):
        return digests
    for subject in subjects:
        if not isinstance(subject, dict):
            continue
        digest_map = subject.get("digest")
        if not isinstance(digest_map, dict):
            continue
        sha256 = digest_map.get("sha256")
        if isinstance(sha256, str):
            digests.append(_normalise_digest(sha256))
    return digests
