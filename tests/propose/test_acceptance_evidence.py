"""BL-731: gate 3b of `propose_candidate` is fed the evidence the official count already verifies, and runs the REAL
acceptance classifier (no stub of `effect.classify`, no stand-in certificates: the repository's own committed
`data/acceptance_calibration.json` / `data/acceptance_responsibility.json` are read).

A gate-3b pass is proven the way the module's own suite proves it: the call is then refused at the NEXT gate (no
write token) instead of at gate 3b; a gate-3b refusal is `ACCEPTANCE_NOT_CERTIFIED` and no network call is made."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from support import make_permit

from repo_presenter.acceptance.record import classify
from repo_presenter.authorization.refusals import Refusal
from repo_presenter.propose import effect
from repo_presenter.propose.acceptance_evidence import (
    AttestedAcceptance,
    evaluate_acceptance,
    read_acceptance_evidence,
)
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
REVISION = "1a6004af47b1" + "0" * 28
README = "# Cells for Rust\n\nIntro.\n"
SHA = hashlib.sha256(README.encode()).hexdigest()
OTHER_SHA = hashlib.sha256(b"other bytes").hexdigest()
VERDICTS = {"M1": True, "M2": True, "M3": True, "M4": True, "M5": True, "M6": True, "M7": True, "M10": True}

ACCEPT = ReviewVerdict.folded(
    (), model_verdict="ACCEPT", prompt_version="17", model_served="qwen3-next",
    request_sha256="a" * 64, reply_sha256="b" * 64, calibration_status="NOT_PASSED",  # R33: retired as a gate
)
REJECT = ReviewVerdict.folded(
    (), model_verdict="REJECT", prompt_version="17", model_served="qwen3-next",
    request_sha256="a" * 64, reply_sha256="b" * 64, calibration_status="PASSED",
)


def record(**changes: Any) -> AttestedAcceptance:
    fields: dict[str, Any] = dict(
        repository=REPOSITORY, lane="R", revision=REVISION, candidate_sha256=SHA,
        deterministically_validated=True, mechanism_verdicts=dict(VERDICTS), canaries={}, audit_passed=True, attested=True,
    )
    fields.update(changes)
    return AttestedAcceptance(**fields)


def never(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("a gate after acceptance certification was reached")


def propose(records: tuple[AttestedAcceptance, ...], *, review: ReviewVerdict = ACCEPT, **overrides: Any) -> effect.ProposalEffectResult:
    fields: dict[str, Any] = dict(
        repository=REPOSITORY, readme_text=README, source_revision=REVISION, base_branch="main",
        token=None,  # gate 3b passing is proven by the refusal that follows it: no write token
        environment={effect.AUTHORIZATION_VARIABLE: "1"}, review=review, permit=make_permit(REPOSITORY),
        load_authorization=never, recheck_source=never, verify_token=never, pr_title="t", pr_body="b",
        lane="R", acceptance_records=records,
    )
    fields.update(overrides)
    return effect.propose_candidate(**fields)


def test_an_accepted_attested_content_bound_record_passes_gate_3b_with_the_real_classifier() -> None:
    assert evaluate_acceptance([record()], repository=REPOSITORY, lane="R", revision=REVISION,
                               readme_bytes_sha256=SHA, classify_fn=classify).state == "publication-ready"
    result = propose((record(),))
    assert result.reason_code == Refusal.NO_WRITE_TOKEN  # past gate 3b, stopped at the token gate


def test_the_reviewers_retired_calibration_is_not_an_input() -> None:
    assert ACCEPT.pr_eligible is False  # calibration NOT_PASSED: the old gate 3b input would have been False
    assert propose((record(),)).reason_code == Refusal.NO_WRITE_TOKEN


def test_a_sealed_only_candidate_is_refused_acceptance_not_certified() -> None:
    result = propose(())
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED
    assert "'sealed'" in result.reason and result.effected is False


def test_a_revision_only_legacy_record_counts_as_accepted_but_is_not_publication_ready() -> None:
    legacy = record(candidate_sha256=None)  # a record written before candidate digests existed
    verdict = evaluate_acceptance([legacy], repository=REPOSITORY, lane="R", revision=REVISION,
                                  readme_bytes_sha256=SHA, classify_fn=classify)
    assert (verdict.state, verdict.binding) == ("independently-accepted", "revision_only")
    result = propose((legacy,))
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED
    assert "independently-accepted" in result.reason and "legacy" in result.reason


@pytest.mark.parametrize(
    ("changes", "state"),
    [
        (dict(candidate_sha256=OTHER_SHA), "independently-accepted"),  # audited other README bytes
        (dict(candidate_sha256="NOT-A-DIGEST"), "independently-accepted"),
        (dict(candidate_sha256=""), "independently-accepted"),  # an explicit null/empty is malformed, not legacy
        (dict(attested=False), "provisionally-accepted"),  # the attestation did not verify
        (dict(audit_passed=False), "provisionally-accepted"),
        (dict(mechanism_verdicts={**VERDICTS, "M3": False}), "deterministically-validated"),
        (dict(mechanism_verdicts={}), "deterministically-validated"),  # no recorded verdict is not a passed one
        (dict(canaries={"c1": False}), "deterministically-validated"),
        (dict(revision="f" * 40), "sealed"),  # a record for another revision is no evidence for this one
    ],
)
def test_each_missing_piece_of_evidence_refuses_with_acceptance_not_certified(changes: dict[str, Any], state: str) -> None:
    result = propose((record(**changes),))
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED, result.reason
    assert f"'{state}'" in result.reason


def test_the_best_record_for_the_revision_wins() -> None:
    bad, good = record(candidate_sha256=OTHER_SHA), record()
    assert propose((bad, good)).reason_code == Refusal.NO_WRITE_TOKEN
    assert propose((good, bad)).reason_code == Refusal.NO_WRITE_TOKEN


def test_binding_uses_the_sealed_files_bytes_not_the_normalised_text() -> None:
    crlf_bytes = README.replace("\n", "\r\n").encode()
    digest = hashlib.sha256(crlf_bytes).hexdigest()
    rec = record(candidate_sha256=digest)
    assert propose((rec,), readme_bytes_sha256=digest).reason_code == Refusal.NO_WRITE_TOKEN
    assert propose((rec,)).reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED  # default digest is of the LF text


def test_a_review_reject_still_refuses_before_the_acceptance_gate() -> None:
    assert propose((record(),), review=REJECT).reason_code == Refusal.REVIEW_REJECTED


def test_the_kill_switch_is_still_first() -> None:
    assert propose((record(),), environment={}).reason_code == Refusal.WRITE_NOT_ENABLED


# --- the reader agrees with the official count -------------------------------------------------------------------


def _count_module() -> Any:
    spec = importlib.util.spec_from_file_location("_count_for_test", Path(__file__).resolve().parents[2] / "ops" / "checks" / "portfolio_delivery_count.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _doc(*records: dict[str, Any], dry_run: bool = False, schema: str = "acceptance-records/1") -> bytes:
    return json.dumps({"schema": schema, "dry_run": dry_run, "records": list(records)}).encode()


def _row(**changes: Any) -> dict[str, Any]:
    row: dict[str, Any] = dict(
        role="clean_control", repository=REPOSITORY, lane="R", revision=REVISION, candidate_sha256=SHA,
        deterministically_validated=True, mechanism_verdicts=dict(VERDICTS), canaries={}, audit_passed=True,
    )
    row.update(changes)
    return row


def _runner(ok: bool):
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, 0 if ok else 1, b"", b"")

    return run


def test_the_reader_keeps_what_the_count_discards_and_verifies_the_attestation_once_per_file() -> None:
    files = [("acceptance-record/x", "acceptance-records-1.json", _doc(_row(), _row(lane="L"), _row(role="treated_control")))]
    found = read_acceptance_evidence(REPOSITORY, "R", fetcher=lambda: files, gh_runner=_runner(True))
    assert len(found) == 1
    assert found[0].attested and found[0].audit_passed and found[0].candidate_sha256 == SHA
    assert found[0].mechanism_verdicts == VERDICTS
    assert read_acceptance_evidence(REPOSITORY, "R", fetcher=lambda: files, gh_runner=_runner(False))[0].attested is False


def test_dry_run_other_schema_and_malformed_documents_yield_nothing() -> None:
    files = [
        ("b", "acceptance-records-1.json", _doc(_row(), dry_run=True)),
        ("b", "acceptance-records-2.json", _doc(_row(), schema="other/1")),
        ("b", "acceptance-records-3.json", b"not json"),
    ]
    assert read_acceptance_evidence(REPOSITORY, "R", fetcher=lambda: files, gh_runner=_runner(True)) == ()

    def broken() -> list[tuple[str, str, bytes]]:
        raise OSError("no git")

    assert read_acceptance_evidence(REPOSITORY, "R", fetcher=broken, gh_runner=_runner(True)) == ()


@pytest.mark.parametrize(
    ("row", "counted"),
    [(_row(), True), (_row(audit_passed=False), False), (_row(mechanism_verdicts={**VERDICTS, "M2": False}), False), (_row(candidate_sha256=None), True)],
)
def test_the_reader_and_the_official_count_agree_on_which_records_count(row: dict[str, Any], counted: bool) -> None:
    files = [("acceptance-record/x", "acceptance-records-1.json", _doc(row))]
    count = _count_module().read_attested_records(lambda: files, _runner(True))
    in_count = bool(count.get((REPOSITORY, "R")))
    mine = read_acceptance_evidence(REPOSITORY, "R", fetcher=lambda: files, gh_runner=_runner(True))
    state = evaluate_acceptance(mine, repository=REPOSITORY, lane="R", revision=REVISION, readme_bytes_sha256=SHA, classify_fn=classify).state
    assert in_count is counted
    assert (state in {"independently-accepted", "publication-ready"}) is counted
