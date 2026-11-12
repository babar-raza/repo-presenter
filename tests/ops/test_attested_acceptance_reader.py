"""The counter's attested-record reader (ops/checks/portfolio_delivery_count.py): only a record whose
file `gh attestation verify` ties to the hosted acceptance writer on main can be counted."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("portfolio_delivery_count_att", _ROOT / "ops" / "checks" / "portfolio_delivery_count.py")
pdc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pdc
_SPEC.loader.exec_module(pdc)

REPO = "org/repo-a"


def _record(**over) -> dict:
    base = {
        "case_id": "c0", "repository": REPO, "lane": "R", "revision": "rev1", "role": "clean_control",
        "deterministically_validated": True, "mechanism_verdicts": {"recertify": True}, "canaries": {}, "audit_passed": True,
    }
    return {**base, **over}


def _document(*records: dict, **over) -> bytes:
    doc = {"schema": pdc.RECORDS_SCHEMA, "seed_run_id": "1", "dry_run": False, "records": list(records)}
    return json.dumps({**doc, **over}).encode()


def _fetch(blob: bytes):
    return lambda: [("acceptance-record/run-1", "acceptance-records-1.json", blob)]


def _gh(ok: bool = True, signer: str | None = None):
    """Fake `gh attestation verify`: succeeds only when `ok` and the requested signer matches."""
    def run(args):
        asked = args[args.index("--signer-workflow") + 1] if "--signer-workflow" in args else ""
        good = ok and (signer is None or asked == signer)
        return subprocess.CompletedProcess(args, 0 if good else 1, stdout=b"[]", stderr=b"")
    return run


MAIN_SIGNER = f"{pdc.ACCEPTANCE_WRITER}@refs/heads/main"


def _read(blob: bytes, gh):
    return pdc.read_attested_acceptances(_fetch(blob), gh)


def test_an_attested_audited_clean_control_is_counted():
    assert _read(_document(_record()), _gh(signer=MAIN_SIGNER)) == {(REPO, "R"): "rev1"}


def test_a_forged_record_without_an_attestation_is_not_counted():
    assert _read(_document(_record()), _gh(ok=False)) == {}


def test_an_attestation_from_the_wrong_signer_is_not_counted():
    wrong = "babar-raza/repo-presenter/.github/workflows/something-else.yml@refs/heads/main"
    assert _read(_document(_record()), _gh(signer=wrong)) == {}


def test_a_failed_audit_is_not_counted_even_when_attested():
    assert _read(_document(_record(audit_passed=False)), _gh()) == {}


def test_mechanism_passing_without_an_audit_stays_out():
    blob = _document(_record(audit_passed=False, deterministically_validated=True))
    assert _read(blob, _gh()) == {}


def test_a_record_that_is_not_deterministically_validated_is_not_counted():
    assert _read(_document(_record(deterministically_validated=False, mechanism_verdicts={"recertify": False})), _gh()) == {}


def test_a_seeded_copy_is_never_counted():
    assert _read(_document(_record(role="seeded")), _gh()) == {}


def test_a_dry_run_document_is_never_counted():
    assert _read(_document(_record(), dry_run=True), _gh()) == {}


def test_a_wrong_schema_or_malformed_file_is_ignored_not_raised():
    assert _read(_document(_record(), schema="other/1"), _gh()) == {}
    assert _read(b"{not json", _gh()) == {}
    assert _read(json.dumps({"schema": pdc.RECORDS_SCHEMA, "dry_run": False}).encode(), _gh()) == {}


def test_a_missing_branch_or_a_broken_fetch_counts_zero():
    assert pdc.read_attested_acceptances(lambda: [], _gh()) == {}

    def boom():
        raise OSError("git unavailable")

    assert pdc.read_attested_acceptances(boom, _gh()) == {}


def _outcome(bucket: str, *, repo: str = REPO, lane: str = "R", current: bool = True, good: bool = True):
    return pdc.LaneOutcome(
        repository=repo, lane=lane, record_state="x", pipeline_good=good, current=current,
        bucket=bucket, revision="rev1",
    )


ALLOW = {"repositories": [{"repository": REPO, "effects": ["pull_request"]}]}


def test_the_frozen_calibration_path_can_no_longer_produce_an_accepted_count():
    outcomes = [_outcome(pdc.ACCEPTED)]
    pdc.apply_attested(outcomes, {}, ALLOW)
    assert outcomes[0].bucket == pdc.UNCALIBRATED and not outcomes[0].independently_accepted
    assert outcomes[0].publication_ready is False


def test_an_attested_record_moves_a_current_outcome_into_the_accepted_bucket():
    outcomes = [_outcome(pdc.UNCALIBRATED)]
    pdc.apply_attested(outcomes, {(REPO, "R"): "rev1"}, ALLOW)
    assert outcomes[0].independently_accepted and outcomes[0].publication_ready is True


def test_an_audit_of_an_older_revision_does_not_count_after_the_repository_is_resealed():
    resealed = _outcome(pdc.UNCALIBRATED)
    resealed.revision = "rev2"
    pdc.apply_attested([resealed], {(REPO, "R"): "rev1"}, ALLOW)
    assert not resealed.independently_accepted and resealed.publication_ready is False


def test_an_attested_record_does_not_count_an_older_version_set_or_the_other_lane():
    older, other_lane = _outcome(pdc.UNCALIBRATED, current=False), _outcome(pdc.UNCALIBRATED, lane="L")
    pdc.apply_attested([older, other_lane], {(REPO, "R"): "rev1"}, ALLOW)
    assert not older.independently_accepted and not other_lane.independently_accepted


def test_terminal_non_candidates_never_increment_accepted():
    not_good = _outcome("", good=False)
    pdc.apply_attested([not_good], {(REPO, "R"): "rev1"}, ALLOW)
    assert not not_good.independently_accepted
    summary = pdc.summarize([not_good], SimpleCalibration())
    assert summary["lane_r"][pdc.ACCEPTED] == 0


class SimpleCalibration:
    status = "NOT_PASSED"
    problem = ""
