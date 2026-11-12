"""``recertify.gate()`` / ``--gate`` hardening (TC-028a, R10): token-exact justifications, a replaced
latest seal cannot dodge the gate, an unreadable explicit base baseline fails closed.

Row shapes are those of the real ``data/recertification_baseline.json`` (``seals[]`` with
repository/lane/commit/outcome/failing_checks/justification)."""

from __future__ import annotations

import json
from pathlib import Path

from repo_presenter import recertify
from repo_presenter.recertify import Recertification, gate

REPO, LANE = "aspose-3d-foss/Aspose.3D-FOSS-for-Java", "L"
OLD, NEW = "e0d4134ef1ea7d75b8d8d528887f20fec8c3479a", "ffffffffffff7d75b8d8d528887f20fec8c3479a"


def row(commit: str, outcome: str, failing=(), justification: str | None = None) -> dict:
    out = {
        "commit": commit, "failing_checks": list(failing), "lane": LANE, "outcome": outcome,
        "regenerations": 0, "repository": REPO, "revision": "3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3",
    }
    if justification is not None:
        out["justification"] = justification
    return out


def doc(*rows: dict) -> dict:
    return {"recertify_version": "1", "schema_version": 1, "seals": list(rows)}


def result(commit: str, failing=("BC-17",), outcome: str = "NEEDS_REPAIR") -> Recertification:
    return Recertification(REPO, LANE, "3d2ed6be", outcome, tuple(failing), seal_commit=commit)


def test_a_justification_must_name_each_failing_check_as_a_whole_token() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    bad = doc(row(OLD, "NEEDS_REPAIR", ["BC-17"], "BC-1 newly fails because of a detector change"))
    assert gate([result(OLD)], bad, base), "BC-1 must not 'name' BC-17"
    good = doc(row(OLD, "NEEDS_REPAIR", ["BC-17"], "BC-17 newly fails (real defect): see notes."))
    assert gate([result(OLD)], good, base) == []


def test_a_check_id_inside_a_longer_id_never_counts() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    working = doc(row(OLD, "NEEDS_REPAIR", ["L-05"], "L-051 is the only thing mentioned here"))
    assert gate([result(OLD, ["L-05"])], working, base)


def test_trailing_punctuation_does_not_hide_a_named_check() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    working = doc(row(OLD, "NEEDS_REPAIR", ["REVIEW:claim_contradiction"], "(REVIEW:claim_contradiction)."))
    assert gate([result(OLD, ["REVIEW:claim_contradiction"])], working, base) == []


def test_a_replaced_latest_seal_that_fails_is_held_to_the_base_lane_row() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    # the lane's latest seal is a NEW commit the base never saw; with no working row it is a regression
    problems = gate([result(NEW)], doc(row(OLD, "RECERTIFIED")), base)
    assert len(problems) == 1 and "no baseline row records it" in problems[0]
    justified = doc(row(OLD, "RECERTIFIED"), row(NEW, "NEEDS_REPAIR", ["BC-17"], "BC-17 genuine defect"))
    assert gate([result(NEW)], justified, base) == []


def test_a_replaced_seal_that_certifies_is_not_a_regression() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    assert gate([result(NEW, [], "RECERTIFIED")], base, base) == []


def test_a_lane_with_no_recertified_base_row_is_not_judged() -> None:
    base = doc(row(OLD, "NEEDS_REPAIR", ["BC-17"]))
    assert gate([result(NEW)], base, base) == []


def test_existing_behaviour_a_same_commit_regression_without_justification_fails() -> None:
    base = doc(row(OLD, "RECERTIFIED"))
    assert len(gate([result(OLD)], base, base)) == 1


def test_the_working_baseline_vouches_only_when_no_base_is_given() -> None:
    working = doc(row(OLD, "RECERTIFIED"))
    assert gate([result(OLD)], working, None)  # falls back to the working baseline as the base


def test_the_real_committed_baseline_gates_itself_clean() -> None:
    baseline = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "recertification_baseline.json").read_text("utf-8")
    )
    results = [
        Recertification(
            r["repository"], r["lane"], r["revision"], r["outcome"], tuple(r["failing_checks"]),
            seal_commit=r["commit"],
        )
        for r in baseline["seals"]
    ]
    assert gate(results, baseline, baseline) == []


def test_an_unreadable_explicit_base_baseline_fails_the_cli_gate(tmp_path: Path, monkeypatch, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(doc(row(OLD, "RECERTIFIED"))), encoding="utf-8")
    monkeypatch.setattr(
        recertify, "portfolio_recertification", lambda **kwargs: ([result(OLD, [], "RECERTIFIED")], {})
    )
    missing = tmp_path / "does-not-exist.json"
    code = recertify.main(["--gate", "--baseline", str(baseline), "--base-baseline", str(missing)])
    assert code == 1 and "unreadable" in capsys.readouterr().out
    garbage = tmp_path / "garbage.json"
    garbage.write_text("{not json", encoding="utf-8")
    assert recertify.main(["--gate", "--baseline", str(baseline), "--base-baseline", str(garbage)]) == 1
    ok = recertify.main(["--gate", "--baseline", str(baseline)])  # no flag: first-adoption behaviour kept
    assert ok == 0
