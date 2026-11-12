"""Net improvement (R21, TC-025 point 4), replacing the old all-or-nothing L-05.

``report.outcome_of`` keeps its own, unconditional, honest account of whether a defect remains
(``tests/readme/correction/test_lane_l_report.py``'s
``test_a_repaired_defect_beside_an_unrepaired_one_still_refuses_the_run`` pins exactly that, and
stays unchanged by this card: the correction-level ``outcome`` field never claims a run is fully
clean when it is not). What changes is a layer up, at the review's own holdout
(``lane_l_review.holdout_findings``): a net-improving edit no longer has its own candidacy killed
by a sibling defect it did not cause and cannot repair -- that defect is recorded
(``report.finding_rows``/``report.corrections_document``'s own ``unapplied`` list) and surfaced to
a reader, never blocked on here and never printed into the README itself.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from repo_presenter.lane_l_review import (
    RULE_UNREPAIRED_DEFECT,
    holdout_findings,
    net_improvement,
)
from repo_presenter.readme.correction.engine import correct
from repo_presenter.readme.correction.model import Finding
from repo_presenter.readme.correction.report import (
    OUTCOME_REFUSED,
    finding_rows,
    outcome_of,
)
from repo_presenter.readme_findings import LANE_L
from tests.readme.correction.conftest import base_facts, context
from tests.readme.correction.test_lane_l_report import README, TREE, broken_link, failing_example, unit

#: The same accounting fact ``tests/test_lane_l_review.py`` uses beside ``broken_link()``: without
#: it the link repair is (correctly) reported as a loss of the live README's own text, which is a
#: different holdout (``RULE_LOSS``) than the one this module is about.
NOTES_UNIT = unit(
    "inherited_unit:004.paragraph",
    "See [the notes](upstream-issues.md) for details.",
    "7-7",
    "paragraph",
)


def corrected(readme: str = README, *extra: Any) -> tuple[Any, Any]:
    ctx = context(readme, base_facts(*extra), tree=TREE)
    return ctx, correct(ctx)


def rules(findings: Any) -> list[str]:
    return [finding.rule for finding in findings]


# --- net_improvement itself -------------------------------------------------------------------------


def test_zero_edits_is_never_a_net_improvement() -> None:
    ctx, result = corrected(README, failing_example())
    assert result.edits == []
    assert net_improvement(ctx, result) is False


def test_at_least_one_edit_with_no_new_defect_on_rerun_is_a_net_improvement() -> None:
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert result.edits
    assert net_improvement(ctx, result) is True


def test_a_rerun_that_finds_a_defect_the_first_pass_did_not_is_not_a_net_improvement() -> None:
    """The ``compute`` seam (mirroring ``engine.is_stable``'s own) lets this be proven without a
    real detector that regresses itself -- which no detector in this package is designed to do."""
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert result.edits

    def rerun_finds_a_new_defect(after_ctx: Any) -> Any:
        after = correct(after_ctx)
        return dataclasses.replace(
            after,
            findings=[
                *after.findings,
                Finding("new_detector", 1, "x", "a defect the first pass never saw"),
            ],
        )

    assert net_improvement(ctx, result, compute=rerun_finds_a_new_defect) is False


# --- the holdout: an unrelated unrepaired defect no longer blocks a net-improving edit -------------


def test_an_unrepaired_defect_beside_a_net_improving_edit_no_longer_blocks_the_holdout() -> None:
    ctx, result = corrected(README, broken_link(), NOTES_UNIT, failing_example())
    assert [edit.kind for edit in result.edits] == ["BROKEN_LINK"]
    # The correction-level record stays exactly as honest as it always was.
    assert outcome_of(result) == OUTCOME_REFUSED
    # The review's own holdout, which actually gates whether the model is ever asked, no longer
    # blocks on it: this is the one thing TC-025 changes.
    findings = holdout_findings(ctx, result, deterministic=True)
    assert RULE_UNREPAIRED_DEFECT not in rules(findings)


def test_zero_edits_beside_an_unrepaired_defect_still_blocks_the_holdout() -> None:
    """The old, strict rule stands without a net improvement to point to."""
    ctx, result = corrected(README, failing_example())
    assert result.edits == []
    findings = holdout_findings(ctx, result, deterministic=True)
    assert RULE_UNREPAIRED_DEFECT in rules(findings)


def test_a_clean_correction_with_no_defect_anywhere_is_unaffected_by_the_gate() -> None:
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert holdout_findings(ctx, result, deterministic=True) == []


# --- the findings-register bridge (point 3): the remaining defect is still owned and visible -------


def test_the_remaining_defect_still_produces_a_findings_register_row() -> None:
    """Point 3: every defect the engine detects gets exactly one row -- including one a net
    improvement elsewhere in the same run no longer blocks on."""
    ctx, result = corrected(README, broken_link(), NOTES_UNIT, failing_example())
    rows = finding_rows(ctx, result, route=LANE_L, first_seen_at="2026-11-07")
    assert len(rows) == 1
    (row,) = rows
    assert row["repository"] == ctx.facts.repository
    assert "failing_example" in row["description"]
    assert row["route"] == LANE_L and row["first_seen_at"] == "2026-11-07"


def test_a_fully_clean_correction_produces_no_findings_register_rows() -> None:
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert finding_rows(ctx, result, route=LANE_L, first_seen_at="2026-11-07") == []


def test_finding_rows_feed_append_finding_directly(tmp_path: Any) -> None:
    from repo_presenter.readme_findings import append_finding, read_findings

    ctx, result = corrected(README, broken_link(), NOTES_UNIT, failing_example())
    path = tmp_path / "readme_findings.json"
    for row in finding_rows(ctx, result, route=LANE_L, first_seen_at="2026-11-07"):
        append_finding(path, **row)
    (saved,) = read_findings(path)
    assert saved.repository == ctx.facts.repository and saved.route == LANE_L
