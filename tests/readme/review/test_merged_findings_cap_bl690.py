"""BL-690: a merged reply of more than 99 findings keeps the first 99 with a note on the unit records.

Hosted Words Java run 44967430141: seven units filed 105 findings in all; the merged reply was refused
('at most 99 findings; got 105', 'finding F100: id must look like F01') and the whole review was lost.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.review.llm_review import (
    MAX_MERGED_FINDINGS,
    _merged_reply,
    _unit_record,
)
from repo_presenter.readme.review.reply import (
    CONTRACT_NOTES_KEY,
    MAX_FINDINGS,
    validate_review_reply,
)
from repo_presenter.readme.review.sectionwise import ReviewUnit
from tests.readme.review.review_support import FACTS, raw_finding, raw_reply

CANDIDATE = "# T\n\nBody.\n"


def unit(index: int) -> ReviewUnit:
    return ReviewUnit(index, ("key_capabilities",), (1, 2, 3))


def reply(unit_index: int, count: int, verdict: str = "REJECT_FACTUAL", same: bool = False) -> dict[str, Any]:
    findings = [
        raw_finding(
            "unsupported_claim",
            id=f"F{n:02d}",
            unsupported_names=["same" if same else f"Name{unit_index}x{n}"],
        )
        for n in range(1, count + 1)
    ]
    return raw_reply(verdict, findings)


def replies(counts: list[int], **kw: Any) -> list[tuple[ReviewUnit, dict[str, Any]]]:
    return [(unit(i), reply(i, c, **kw)) for i, c in enumerate(counts, 1)]


def contract_errors(merged: dict[str, Any]) -> list[str]:
    errors = validate_review_reply(
        merged, candidate_readme=CANDIDATE, facts=FACTS, max_findings=MAX_MERGED_FINDINGS
    )
    return [e for e in errors if "at most" in e or "id must look like" in e]


def test_the_real_shape_105_findings_in_seven_units_is_kept_as_99_with_notes() -> None:
    counts = [15] * 7  # each unit within MAX_FINDINGS, 105 in all (hosted Words Java)
    assert max(counts) <= MAX_FINDINGS and sum(counts) == 105
    merged, origin, notes = _merged_reply(replies(counts))
    ids = [f["id"] for f in merged["findings"]]
    assert len(ids) == 99 and ids == [f"F{n:02d}" for n in range(1, 100)]
    assert contract_errors(merged) == []
    assert merged["verdict"] == "REJECT_FACTUAL"  # never an ACCEPT
    assert set(origin) == set(ids)
    assert set(notes) == {"u7"}
    assert "6 finding(s)" in "".join(sum(notes.values(), []))
    # the dropped findings are the LAST ones: the first 99 are kept in order
    assert merged["findings"][0]["unsupported_names"] == ["Name1x1"]
    assert merged["findings"][-1]["unsupported_names"] == ["Name7x9"]


def test_the_unit_record_carries_the_note() -> None:
    merged, origin, notes = _merged_reply(replies([15] * 7))
    record = _unit_record(unit(7), "sha", reply=reply(7, 15), reply_sha256="r")
    record.setdefault(CONTRACT_NOTES_KEY, []).extend(notes["u7"])
    assert record["findings"] == 15 and "set aside" in record[CONTRACT_NOTES_KEY][0]


def test_ids_are_renumbered_when_repeats_merged_away_leave_a_gap_past_99() -> None:
    units = replies([15] * 6)
    # unit 7 files 15 more, all the same finding: merged into one, id F91 survives, so no gap issue;
    # make a gap: a repeated finding inside unit 1 vanishes while later ids stay above 99
    units.append((unit(7), reply(7, 15)))
    units[0][1]["findings"][1:3] = [dict(units[0][1]["findings"][0]) for _ in range(2)]
    merged, origin, notes = _merged_reply(units)
    ids = [f["id"] for f in merged["findings"]]
    assert len(ids) <= 99 and ids == [f"F{n:02d}" for n in range(1, len(ids) + 1)]
    assert contract_errors(merged) == []
    assert set(origin) == set(ids)


def test_up_to_99_findings_are_untouched_and_carry_no_note() -> None:
    merged, origin, notes = _merged_reply(replies([15] * 6 + [9]))  # 99
    assert len(merged["findings"]) == 99 and notes == {}
    assert contract_errors(merged) == []


def test_negative_control_an_accept_stays_an_accept_and_an_unmerged_105_is_refused() -> None:
    merged, _, notes = _merged_reply(replies([0, 0], verdict="ACCEPT"))
    assert merged["verdict"] == "ACCEPT" and merged["findings"] == [] and notes == {}
    big = {"verdict": "REJECT_FACTUAL", "findings": [raw_finding(id=f"F{n:02d}") for n in range(1, 106)], "preserve": []}
    assert contract_errors(big)  # the contract itself is unchanged: only the merge sets findings aside


def test_a_mixed_accept_and_reject_stays_a_reject_with_the_findings() -> None:
    units = [(unit(1), reply(1, 0, verdict="ACCEPT"))] + replies([15] * 7)[1:]
    merged, _, _ = _merged_reply(units)
    assert merged["verdict"] == "REJECT_FACTUAL" and merged["findings"]
