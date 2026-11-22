"""BL-870: what a Lane L review is shown and asked about the lines a correction rewrote.

Evidence: hosted Lane L PDF Cpp run 45007577791 (2026-11-22) ended 'independent review returned REJECT
with 12 blocking finding(s) of 12', a zero-call replay of the same pinned revision (4b83c9f) reproduced
every cited line byte for byte, and two classes explain all twelve:

* F02-F12: the correction rewrote 118 API rows to "Class that inherits from X and declares the methods
  A and B." from SUPPORTED member facts, and the review packet of a corrected live README carried none of
  those member facts (the type's ``members`` rode only with rows an author wrote in a RENDERED candidate),
  so the reviewer faulted true rows ("no fact supports Icon"; ``SoundAnnotation.Icon`` is a fact);
* F01: the only edit on the opening's line renamed a product ("the commercial Aspose.PDF for .NET" ->
  "Aspose.PDF for .NET -- Enterprise Edition"); the reviewer faulted the maintainers' own sentence around it.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.applied_edits import drop_carried_claim_findings
from repo_presenter.readme.review.llm_review import review_checks
from repo_presenter.readme.review.sectionwise import plan_units, unit_packet


def _fact(fact_id: str, value: str, detail: str, **attributes: Any) -> Fact:
    return Fact(
        fact_id, "public_symbol", value, (Evidence("include/a.hpp", detail=detail),), "SUPPORTED",
        attributes=attributes,
    )  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/pdf",
    "a" * 40,
    (
        _fact("public_symbol:n.soundannotation", "N.SoundAnnotation", "line 32; class;", symbol_kind="class"),
        _fact("public_symbol:n.soundannotation.accept", "N.SoundAnnotation.Accept", "line 38; method;", symbol_kind="method"),
        _fact("public_symbol:n.soundannotation.icon", "N.SoundAnnotation.Icon", "line 40; method;", symbol_kind="method"),
        _fact("public_symbol:n.otherannotation", "N.OtherAnnotation", "line 9; class;", symbol_kind="class"),
        _fact("public_symbol:n.otherannotation.zap", "N.OtherAnnotation.Zap", "line 10; method;", symbol_kind="method"),
    ),
)
ORIGINAL = (
    "# Widget\n\nIntro.\n\n## API Reference\n\n| Class | Description |\n| --- | --- |\n"
    "| `SoundAnnotation` | Class with 3 methods. |\n| `OtherAnnotation` | Class with 2 methods. |\n"
)
CANDIDATE = ORIGINAL.replace(
    "Class with 3 methods.", "Class that inherits from MarkupAnnotation and declares the methods Accept and Icon."
)
ROW = 9  # the SoundAnnotation row


def _packet(candidate: str, changed: frozenset[int] | None):
    units = plan_units(candidate, rendered=False)
    unit = next(u for u in units if "api_reference" in u.sections)
    return unit_packet(
        unit, units=units, repository="org/pdf", candidate_readme=candidate, original_readme=ORIGINAL,
        facts=FACTS, plan={"sections": []}, changed=changed,
    )


def _members(packet: dict[str, Any]) -> dict[str, str]:
    return {r["id"]: r["members"] for r in packet["facts"] if r.get("members")}


def test_a_rewritten_row_carries_the_member_facts_it_restates() -> None:
    assert _members(_packet(CANDIDATE, frozenset({ROW}))) == {
        "public_symbol:n.soundannotation": "Accept, Icon"
    }


def test_a_row_the_correction_did_not_touch_is_not_given_members() -> None:
    packet = _members(_packet(CANDIDATE, frozenset({ROW})))
    assert "public_symbol:n.otherannotation" not in packet  # negative control: only changed rows


def test_without_an_edit_scope_the_packet_is_unchanged() -> None:
    assert _members(_packet(CANDIDATE, None)) == {}  # Lane R / audit callers keep their bytes


def test_a_changed_line_that_is_not_a_type_row_adds_nothing() -> None:
    assert _members(_packet(CANDIDATE.replace("Intro.", "New intro."), frozenset({3}))) == {}


# --- F01: a wording-only edit does not make the maintainers' sentence the edit's claim ---------------

LIVE = (
    "# Widget\n\nIts public API is a\nstrict subset of the commercial Aspose.PDF for .NET library, "
    "class names mirror it.\n\nDone.\n"
)
NAMED = LIVE.replace("the commercial Aspose.PDF for .NET", "Aspose.PDF for .NET — Enterprise Edition")
WORDING = {
    "detector": "enterprise_edition_naming",
    "original": "the commercial Aspose.PDF for .NET",
    "replacement": "Aspose.PDF for .NET — Enterprise Edition",
}
LINE = 4


def _reply(kind: str = "unsupported_claim", lines: list[int] | None = None) -> dict[str, Any]:
    return {"verdict": "REJECT_FACTUAL", "findings": [{"id": "F01", "claim_kind": kind, "lines": lines or [LINE]}]}


def _drop(reply: dict[str, Any], edits: list[dict[str, str]], candidate: str = NAMED, changed=frozenset({LINE})):
    return drop_carried_claim_findings(
        reply, all_edits=edits, candidate_readme=candidate, original_readme=LIVE, changed=changed
    )


def test_a_finding_on_the_carried_sentence_of_a_renamed_line_is_dropped_and_noted() -> None:
    reply = _reply()
    notes = _drop(reply, [WORDING])
    assert reply["findings"] == [] and reply["verdict"] == "ACCEPT"
    assert [n.get("rule") for n in notes] == ["BL-870", "BL-870"]
    assert reply["contract_notes"] == notes


def test_another_finding_keeps_the_verdict() -> None:
    reply = _reply()
    reply["findings"].append({"id": "F02", "claim_kind": "unsupported_claim", "lines": [6]})
    _drop(reply, [WORDING])
    assert [f["id"] for f in reply["findings"]] == ["F02"] and reply["verdict"] == "REJECT_FACTUAL"


def test_a_finding_of_another_kind_is_never_dropped() -> None:
    reply = _reply("contradiction")
    assert _drop(reply, [WORDING]) == [] and len(reply["findings"]) == 1


def test_a_line_another_edit_also_wrote_is_still_judged() -> None:
    candidate = NAMED.replace("class names", "249 class names")
    other = {"detector": "stale_type_count", "original": "class names", "replacement": "249 class names"}
    reply = _reply()
    assert _drop(reply, [WORDING, other], candidate) == [] and len(reply["findings"]) == 1


def test_a_value_edit_alone_is_never_wording() -> None:
    value = {"detector": "stale_type_count", "original": "243", "replacement": "385"}
    live = LIVE.replace("strict subset", "243 strict subset")
    candidate = live.replace("243", "385")
    reply = _reply()
    assert drop_carried_claim_findings(
        reply, all_edits=[value], candidate_readme=candidate, original_readme=live, changed=frozenset({LINE})
    ) == []
    assert len(reply["findings"]) == 1


def test_a_line_the_maintainers_never_wrote_is_still_judged() -> None:
    candidate = NAMED.replace("class names mirror it", "it is certified by ISO")
    reply = _reply()
    assert _drop(reply, [WORDING], candidate) == [] and len(reply["findings"]) == 1


def test_an_unchanged_line_or_no_edits_drops_nothing() -> None:
    assert _drop(_reply(), [WORDING], changed=frozenset({6})) == []
    assert _drop(_reply(), []) == []


def test_review_checks_applies_the_drop_for_a_lane_l_scope() -> None:
    reply = _reply()
    reply["findings"][0].update(summary="s", quote="q", section_id="opening", reason="r")
    errors = review_checks(
        reply, candidate_readme=NAMED, facts=FACTS, plan={"sections": []}, scope=None,
        changed=frozenset({LINE}), applied=[], original_readme=LIVE, edit_rows=[WORDING],
    )
    assert reply["findings"] == [] and reply["verdict"] == "ACCEPT"
    assert not any("F01" in e for e in errors)
