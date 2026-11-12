"""The Lane L review judges the EDITS, not the whole live README (R5/R21).

Evidence (hosted runs 42682731549 Slides Java, 42682777678 PDF Cpp, 42683449087 3D .NET): the Lane L
review used Lane R's packet unchanged -- every unit of the whole live README, with an empty
``maintainer_lines`` (no S4 dispositions in Lane L), so the maintainers' untouched prose was judged
"exactly like generated text" and pre-existing unsupported claims rejected otherwise-good
corrections. The reviewer was never told which lines the correction wrote.

The fix is scoped to a real Lane L run (``rendered=False`` and a holdouts document with
``lane == "L"``): the packet names the changed lines and the already-recorded residuals, and a
finding that cites only unchanged lines is a contract error quoted back in the one re-ask. A
finding that cites a changed line is untouched and still blocks. Lane R and the calibration harness
are unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.readme.review import llm_review
from repo_presenter.readme.review.llm_review import (
    LANE_L_INSTRUCTION,
    edit_scope,
    lane_l_changed_lines,
    unchanged_text_errors,
)
from repo_presenter.readme.review.sectionwise import plan_units
from tests.readme.review.test_llm_review import (
    CONFIG,
    CONTEXT,
    DISPOSITIONS,
    FACTS,
    PLAN,
    PROMPTS,
    VALIDATION,
    Harness,
    completion,
    install,
    reply,
)
from tests.readme.review.test_sectionwise_review import LIVE, line_finding

EDITED = LIVE.replace("It supports every Python 3 release.", "It supports Python 3.9 and later.")
HOLDOUTS = {"lane": "L", "checks": [], "residuals": [{"reason": "format PDF marked supported, no fact"}]}


def _review(harness: Harness, *, candidate: str = EDITED, original: str = LIVE, validation: Any = HOLDOUTS):
    return llm_review.review_with_model(
        prompts=PROMPTS,
        config=CONFIG,
        ledger=Ledger(harness.ledger_path, invocation_id="inv-lane-l"),
        store=harness.store,
        context=CONTEXT,
        candidate_readme=candidate,
        original_readme=original,
        facts=FACTS,
        plan=PLAN,
        dispositions=DISPOSITIONS,
        validation=validation,
        rendered=False,
    )


def _line(text: str, readme: str = EDITED) -> int:
    (found,) = [i for i, row in enumerate(readme.splitlines(), 1) if text in row]
    return found


def _unit_of(line: int) -> int:
    units = plan_units(EDITED, rendered=False)
    return next(i for i, unit in enumerate(units) if line in unit.lines)


def test_changed_lines_are_the_candidate_rows_the_correction_wrote() -> None:
    assert lane_l_changed_lines(EDITED, LIVE) == frozenset({_line("Python 3.9 and later")})
    inserted = LIVE.replace("# Widget\n", "# Widget\n\nA new sentence.\n", 1)
    assert lane_l_changed_lines(inserted, LIVE) == frozenset({2, 3})  # the new blank row and sentence
    deleted = LIVE.replace("Widget renders widgets.\n\n", "", 1)
    # a pure deletion changes no candidate row: the rows on either side carry the effect
    assert lane_l_changed_lines(deleted, LIVE)


def test_edit_scope_is_only_for_a_real_lane_l_correction() -> None:
    kwargs = {"candidate_readme": EDITED, "original_readme": LIVE}
    assert edit_scope(rendered=False, validation=HOLDOUTS, **kwargs)
    assert edit_scope(rendered=True, validation=HOLDOUTS, **kwargs) is None  # Lane R
    assert edit_scope(rendered=False, validation=VALIDATION, **kwargs) is None  # calibration etc.
    assert edit_scope(rendered=False, validation=None, **kwargs) is None
    assert edit_scope(
        rendered=False, validation=HOLDOUTS, candidate_readme=LIVE, original_readme=LIVE
    ) is None  # nothing was edited


def test_the_packet_names_the_changed_lines_and_the_residuals(
    tmp_path: Path, monkeypatch
) -> None:
    client = install(monkeypatch, [completion(reply())] * 8)
    verdict = _review(Harness(tmp_path, EDITED))
    assert verdict.verdict == "ACCEPT"
    sent = "\n".join(p["messages"][1]["content"] for p in client.payloads)
    assert LANE_L_INSTRUCTION[:60] in sent
    assert "changed_lines" in sent and "lane_l" in sent
    assert "format PDF marked supported, no fact" in sent


def test_lane_r_and_unscoped_lane_l_packets_are_unchanged(tmp_path: Path, monkeypatch) -> None:
    client = install(monkeypatch, [completion(reply())] * 8)
    _review(Harness(tmp_path, EDITED), validation=VALIDATION)
    sent = "\n".join(p["messages"][1]["content"] for p in client.payloads)
    assert "Lane L review" not in sent and "changed_lines" not in sent


def test_a_finding_that_cites_only_unchanged_lines_is_a_contract_error_and_reasked(
    tmp_path: Path, monkeypatch
) -> None:
    units = plan_units(EDITED, rendered=False)
    victim = _unit_of(_line("Widget renders widgets."))
    section = units[victim].sections[0]
    bad = reply(
        "REJECT_FACTUAL",
        line_finding("unsupported_claim", _line("Widget renders widgets."), section),
    )
    replies = [completion(reply())] * (len(units) + 2)
    replies[victim] = completion(bad)
    client = install(monkeypatch, replies)
    verdict = _review(Harness(tmp_path, EDITED))
    reasked = client.payloads[victim + 1]["messages"]
    assert "unchanged live-README text" in "\n".join(m["content"] for m in reasked)
    assert verdict.verdict == "ACCEPT"


def test_a_finding_on_a_changed_line_still_blocks(tmp_path: Path, monkeypatch) -> None:
    changed_line = _line("Python 3.9 and later")
    units = plan_units(EDITED, rendered=False)
    victim = _unit_of(changed_line)
    section = units[victim].sections[0]
    blocking = reply(
        "REJECT_FACTUAL", line_finding("unsupported_claim", changed_line, section)
    )
    replies = [completion(reply())] * (len(units) + 2)
    replies[victim] = completion(blocking)
    install(monkeypatch, replies)
    verdict = _review(Harness(tmp_path, EDITED))
    assert verdict.verdict == "REJECT" and verdict.blocking_findings


def test_unchanged_text_errors_ignore_omissions_absences_and_spans_that_touch_a_change() -> None:
    changed = frozenset({7})
    unit = frozenset(range(1, 12))
    assert unchanged_text_errors(
        {"findings": [{"id": "F01", "claim_kind": "omission", "lines": [3]}]},
        changed=changed, unit_lines=unit,
    ) == []
    assert unchanged_text_errors(
        {"findings": [{"id": "F01", "claim_kind": "contradiction", "lines": [5, 8]}]},
        changed=changed, unit_lines=unit,
    ) == []
    assert unchanged_text_errors(
        {"findings": [{"id": "F01", "claim_kind": "contradiction", "lines": [3]}]},
        changed=changed, unit_lines=unit,
    )
