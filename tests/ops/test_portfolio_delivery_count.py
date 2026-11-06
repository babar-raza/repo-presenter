"""ops/checks/portfolio_delivery_count.py: TC-011's counter, re-authored to owner ruling R4.

Per-lane independent acceptance (product sets may differ), a model ACCEPT only counts under a
PASSED, version-matching reviewer calibration (otherwise `pipeline_good_uncalibrated`), and
upstream delivery is a separate outcome derived from the GitHub API, never from an editable
ledger.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "portfolio_delivery_count", REPO / "ops" / "checks" / "portfolio_delivery_count.py"
)
pdc = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = pdc  # dataclasses resolve their module by name
_SPEC.loader.exec_module(pdc)

from repo_presenter.readme.review.calibration_status import Calibration  # noqa: E402

PASSED = Calibration("PASSED", reviewer_logic_version="8", prompt_version="17")
NOT_PASSED = Calibration("NOT_PASSED", reviewer_logic_version="6", prompt_version="17")


def review(**over):
    base = {
        "verdict": "ACCEPT",
        "model_verdict": "ACCEPT",
        "calibration_status": "PASSED",
        "reviewer_logic_version": "8",
        "prompt_version": "17",
    }
    base.update(over)
    return base


def evidence(rev=None, state="ACCEPTED", readme=b"# README\n"):
    return pdc.SealedEvidence(
        source="committed", manifest={"state": state}, review=rev, readme=readme
    )


def record(state="ACCEPTED", proposal=None):
    return SimpleNamespace(state=state, proposal=proposal)


def no_github(_args):
    raise AssertionError("no GitHub call is expected without a recorded proposal")


def test_a_model_accept_under_passed_matching_calibration_is_independently_accepted():
    assert pdc.classify_review(review(), PASSED)[0] == pdc.ACCEPTED


def test_a_model_accept_under_a_not_passed_reviewer_is_uncalibrated_not_accepted():
    assert pdc.classify_review(review(calibration_status="NOT_PASSED"), NOT_PASSED)[0] == pdc.UNCALIBRATED
    # even if the committed file later says PASSED, an ACCEPT made under NOT_PASSED never counts
    assert pdc.classify_review(review(calibration_status="NOT_PASSED"), PASSED)[0] == pdc.UNCALIBRATED


@pytest.mark.parametrize("field,value", [("reviewer_logic_version", "7"), ("prompt_version", "16")])
def test_a_version_mismatch_with_the_passed_calibration_is_uncalibrated(field, value):
    assert pdc.classify_review(review(**{field: value}), PASSED)[0] == pdc.UNCALIBRATED


@pytest.mark.parametrize(
    "rev",
    [None, review(verdict="REJECT"), review(model_verdict=None), review(model_verdict="REJECT")],
)
def test_no_model_accept_is_unreviewed(rev):
    assert pdc.classify_review(rev, PASSED)[0] == pdc.UNREVIEWED


def test_a_pipeline_good_record_with_a_non_terminal_bundle_does_not_count():
    out = pdc.classify_lane("o/a", "R", record(), evidence(review(), state="INVALIDATED"), "",
                            PASSED, {}, no_github)
    assert out.bucket == pdc.UNREVIEWED and not out.independently_accepted


def test_publication_ready_needs_acceptance_and_the_r3_allowlist():
    allow = {"repositories": [{"repository": "o/a", "effects": ["pull_request"]}]}
    ok = pdc.classify_lane("o/a", "R", record(), evidence(review()), "", PASSED, allow, no_github)
    other = pdc.classify_lane("o/b", "R", record(), evidence(review()), "", PASSED, allow, no_github)
    uncal = pdc.classify_lane("o/a", "R", record(), evidence(review()), "", NOT_PASSED, allow, no_github)
    assert ok.publication_ready and not other.publication_ready and not uncal.publication_ready


def test_effect_and_live_verification_come_from_the_github_api():
    proposal = SimpleNamespace(repository="o/a", number=7, branch="presenter/x")
    calls = []

    def github(args):
        calls.append(args[0])
        if args[0].endswith("/pulls/7"):
            return json.dumps({"head": {"ref": "presenter/x"}, "merged": True}).encode()
        return b"# README\n"

    out = pdc.classify_lane("o/a", "L", record(proposal=proposal), evidence(review()), "",
                            PASSED, {}, github)
    assert out.effect_executed and out.live_verified
    drifted = pdc.classify_lane("o/a", "L", record(proposal=proposal),
                                evidence(review(), readme=b"other\n"), "", PASSED, {}, github)
    assert drifted.effect_executed and not drifted.live_verified
    unreachable = pdc.classify_lane("o/a", "L", record(proposal=proposal), evidence(review()), "",
                                    PASSED, {}, lambda _a: None)
    assert not unreachable.effect_executed and not unreachable.live_verified


def _outcomes(lane, repos, bucket=pdc.ACCEPTED):
    return [
        pdc.LaneOutcome(repository=r, lane=lane, record_state="ACCEPTED", pipeline_good=True,
                        bucket=bucket)
        for r in repos
    ]


def test_lanes_are_counted_independently_and_product_sets_may_differ():
    # 25 Lane R products and 25 DIFFERENT Lane L products: zero in common, the gate still holds
    outcomes = _outcomes("R", [f"o/r{i}" for i in range(25)]) + _outcomes("L", [f"o/l{i}" for i in range(25)])
    summary = pdc.summarize(outcomes, PASSED)
    assert pdc.evaluate(summary, 25, None) == []
    # one lane short fails, whatever the other lane has
    lopsided = _outcomes("R", [f"o/r{i}" for i in range(40)]) + _outcomes("L", [f"o/l{i}" for i in range(24)])
    assert pdc.evaluate(pdc.summarize(lopsided, PASSED), 25, None) == [
        "Lane L independently_accepted 24 < 25"
    ]


def test_uncalibrated_pipeline_good_records_are_reported_separately_and_never_counted():
    outcomes = _outcomes("R", [f"o/r{i}" for i in range(30)], bucket=pdc.UNCALIBRATED)
    lane_r = pdc.summarize(outcomes, NOT_PASSED)["lane_r"]
    assert lane_r[pdc.UNCALIBRATED] == 30 and lane_r[pdc.ACCEPTED] == 0


def test_upstream_delivery_is_a_separate_gate_from_acceptance():
    outcomes = _outcomes("R", [f"o/r{i}" for i in range(25)]) + _outcomes("L", [f"o/l{i}" for i in range(25)])
    summary = pdc.summarize(outcomes, PASSED)
    assert pdc.evaluate(summary, 25, None) == []
    assert pdc.evaluate(summary, None, 1) == ["live_verified (R+L) 0 < 1"]
