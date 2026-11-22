"""BL-710: a finding that breaks the per-finding contract must not lose the unit's whole review.

Hosted PSD Java run 44985283929 (unit u2): "finding F06: a contradiction finding must cite at least one
product fact (not only inherited text)", rejected twice, so the unit and the candidate had no review.
Every per-finding error the validator can raise is either repaired deterministically or the finding is
dropped with a recorded note; nothing valid is touched, and nothing a model asserted with a checkable
basis is cleared."""

from __future__ import annotations

import copy

import pytest

from repo_presenter.core.llm.jobs import RECOVERY_NOTES_KEY
from repo_presenter.readme.review.llm_review import _unit_record, review_checks, review_recover
from repo_presenter.readme.review.reply import (
    CONTRACT_NOTES_KEY,
    ReviewScope,
    set_aside_void_findings,
    validate_review_reply,
)
from repo_presenter.readme.review.sectionwise import ReviewUnit
from tests.readme.review.review_support import FACTS, raw_finding, raw_reply
from tests.readme.review.test_scoped_contract import CANDIDATE, FIRST, OPENING, at, cited, scope


def _run(reply: dict, unit: ReviewScope | None = None, *, changed=None) -> list[str]:
    """What the job does with a reply the re-ask did not fix: ``review_recover`` (Lane R only), then the
    ordinary ``review_checks`` on the corrected reply. Errors are what still rejects it."""
    unit = unit or scope("key_capabilities")
    sink: list[dict] = []
    if changed is None:
        fixed = review_recover(copy.deepcopy(reply), candidate_readme=CANDIDATE, facts=FACTS, plan={},
                               scope=unit, sink=sink)
        if fixed is not None:
            fixed.pop(RECOVERY_NOTES_KEY)
            assert sink == [n for n in sink]
            fixed[CONTRACT_NOTES_KEY] = sink
            reply.clear()
            reply.update(fixed)
    return review_checks(
        reply, candidate_readme=CANDIDATE, facts=FACTS, plan={}, scope=unit, changed=changed,
    )


def _notes(reply: dict, action: str | None = None) -> list[dict]:
    return [n for n in reply.get(CONTRACT_NOTES_KEY, []) if action is None or n["action"] == action]


def _unit(reply: dict) -> ReviewScope:
    return scope("key_capabilities")


# --- the hosted shape -------------------------------------------------------------------------------


def test_a_contradiction_citing_no_product_fact_is_dropped_and_the_other_findings_survive() -> None:
    good = cited("contradiction", FIRST + 1, fact_ids=["public_symbol:legacyexport"], id="F05")
    void = cited("contradiction", FIRST, fact_ids=["inherited_unit:001.paragraph"], id="F06")
    reply = raw_reply("REJECT_FACTUAL", [good, void])
    assert _run(reply) == []
    assert [f["id"] for f in reply["findings"]] == ["F05"]
    assert reply["verdict"] == "REJECT_FACTUAL"  # a real finding stays: the REJECT is not softened
    (note,) = _notes(reply, "dropped")
    assert note["finding"] == "F06" and note["class"] == "no_product_fact" and note["rule"] == "BL-710"


def test_a_contradiction_citing_no_fact_at_all_and_only_one_finding_gives_accept_with_a_note() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=[])])
    assert _run(reply) == []
    assert reply["findings"] == [] and reply["verdict"] == "ACCEPT"
    assert _notes(reply, "verdict_changed")[0]["verdict_changed"] == ["REJECT_FACTUAL", "ACCEPT"]


def test_replay_is_identical_and_a_valid_reply_is_untouched() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=[])])
    _run(reply)
    once = copy.deepcopy(reply)
    assert _run(reply) == [] and reply == once
    valid = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=["public_symbol:legacyexport"])])
    before = copy.deepcopy(valid)
    assert _run(valid) == []
    assert CONTRACT_NOTES_KEY not in valid
    assert {k: v for k, v in valid.items()} == {**before, "findings": valid["findings"]}
    assert valid["findings"][0]["fact_ids"] == ["public_symbol:legacyexport"]


def test_the_notes_reach_the_unit_record() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=[])])
    _run(reply)
    record = _unit_record(ReviewUnit(2, ("key_capabilities",), (FIRST, FIRST + 1)), "r" * 64,
                          reply=reply, reply_sha256="s" * 64)
    assert record[CONTRACT_NOTES_KEY] == reply[CONTRACT_NOTES_KEY]


# --- each per-finding contract class: repaired when deterministic, else dropped with a note -------------


def test_unknown_fact_ids_are_removed_and_a_product_fact_still_cited_keeps_the_finding() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST,
                                               fact_ids=["public_symbol:legacyexport", "bogus:1"])])
    assert _run(reply) == []
    assert reply["findings"][0]["fact_ids"] == ["public_symbol:legacyexport"]
    assert _notes(reply, "repaired")[0]["repairs"][0].startswith("fact_ids named facts not in the input")


def test_unknown_fact_ids_only_on_a_contradiction_drops_it() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=["bogus:1"])])
    assert _run(reply) == []
    assert _notes(reply, "dropped")[0]["class"] == "no_product_fact"


def test_empty_repair_or_text_is_taken_from_its_sibling() -> None:
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST, repair="  "),
                                                cited("quality", FIRST + 1, text="", id="F02")])
    assert _run(reply) == []
    one, two = reply["findings"]
    assert one["repair"] == one["text"] and two["text"] == two["repair"]


def test_both_empty_is_dropped() -> None:
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST, repair="", text=""),
                                                cited("quality", FIRST + 1, id="F02")])
    assert _run(reply) == [] and _notes(reply, "dropped")[0]["class"] == "empty_text"


def test_an_unknown_causal_stage_becomes_unclear() -> None:
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST, causal_stage="S1")])
    assert _run(reply) == []
    assert reply["findings"][0]["causal_stage"] == "unclear"


def test_a_bad_criterion_claim_kind_or_missing_section_is_dropped() -> None:
    for override, expected in (
        ({"criterion": "taste"}, "criterion"),
        ({"kind": "vibes"}, "claim_kind"),
    ):
        override = dict(override)
        kind = override.pop("kind", "quality")
        reply = raw_reply("REJECT_PRESENTATION", [cited(kind, FIRST, **override),
                                                   cited("quality", FIRST + 1, id="F02")])
        assert _run(reply) == [], override
        assert [f["id"] for f in reply["findings"]] == ["F02"]
        assert _notes(reply, "dropped")[0]["class"] == expected


def test_a_section_outside_the_unit_with_cited_lines_is_taken_from_the_lines() -> None:
    omission = cited("omission", FIRST, section_id="quick_start", criterion="completeness",
                     fact_ids=[], omission={"kind": "omission", "section_id": "quick_start",
                                            "missing_ids": ["format:png"], "missing_quotes": []})
    reply = raw_reply("REJECT_PRESENTATION", [omission])
    assert _run(reply) == []
    assert reply["findings"][0]["section_id"] == "key_capabilities"
    assert reply["findings"][0]["omission"]["section_id"] == "key_capabilities"


def test_an_omission_naming_a_non_supported_fact_keeps_only_the_supported_ones() -> None:
    omission = cited("omission", FIRST, criterion="completeness", fact_ids=[],
                     omission={"kind": "omission", "section_id": "key_capabilities",
                               "missing_ids": ["format:png", "public_symbol:legacyexport", "bogus:1"],
                               "missing_quotes": []})
    reply = raw_reply("REJECT_PRESENTATION", [omission])
    assert _run(reply) == []
    assert reply["findings"][0]["omission"]["missing_ids"] == ["format:png"]


def test_an_omission_that_names_nothing_supported_is_dropped() -> None:
    omission = cited("omission", FIRST, criterion="completeness", fact_ids=[],
                     omission={"kind": "omission", "section_id": "key_capabilities",
                               "missing_ids": ["public_symbol:legacyexport"], "missing_quotes": []})
    reply = raw_reply("REJECT_PRESENTATION", [omission, cited("quality", FIRST + 1, id="F02")])
    assert _run(reply) == []
    assert _notes(reply, "dropped")[0]["class"] == "typed_field"


def test_an_omission_filed_as_factuality_cites_its_own_missing_facts() -> None:
    omission = cited("omission", FIRST, criterion="factuality", fact_ids=[],
                     omission={"kind": "omission", "section_id": "key_capabilities",
                               "missing_ids": ["format:png"], "missing_quotes": []})
    reply = raw_reply("REJECT_FACTUAL", [omission])
    assert _run(reply) == []
    assert reply["findings"][0]["fact_ids"] == ["format:png"]


def test_a_typed_field_on_an_untyped_kind_is_cleared_and_a_mislabelled_kind_relabelled() -> None:
    typed = cited("quality", FIRST, absent=["Capability 99"])
    relabel = cited("absence", FIRST + 1, absent=["Capability 99"], id="F02", unsupported_names=["X"])
    reply = raw_reply("REJECT_PRESENTATION", [typed, relabel])
    assert _run(reply) == []
    assert reply["findings"][0]["absent"] == [] and reply["findings"][0]["claim_kind"] == "quality"
    assert reply["findings"][1]["claim_kind"] == "absence"


def test_a_typed_kind_with_an_empty_typed_field_is_dropped() -> None:
    reply = raw_reply("REJECT_PRESENTATION", [cited("absence", FIRST), cited("quality", FIRST + 1, id="F02")])
    assert _run(reply) == []
    assert [f["id"] for f in reply["findings"]] == ["F02"]
    assert _notes(reply, "dropped")[0]["class"] == "typed_field"


def test_an_absence_the_findings_own_quote_shows_present_is_dropped() -> None:
    present = cited("absence", FIRST, absent=["Capability 1"], section_id="key_capabilities")
    reply = raw_reply("REJECT_PRESENTATION", [present, cited("quality", FIRST + 1, id="F02")])
    # an absence cites a whole section and leaves quote empty, so use an explicit quote
    present.pop("lines")
    present["quote"] = "Capability 1. It exports vector output through `SvgExporter`, number 1."
    present["absent"] = ["Capability 1"]
    assert _run(reply) == []
    assert _notes(reply, "dropped")[0]["class"] == "absence_contradicted_by_quote"


def test_lines_the_unit_did_not_show_and_unusable_spans_are_dropped() -> None:
    hidden = cited("contradiction", at("pip install"), fact_ids=["public_symbol:legacyexport"])
    long_span = cited("contradiction", FIRST, FIRST + 14, fact_ids=["public_symbol:legacyexport"], id="F02")
    cross = cited("contradiction", OPENING, FIRST, fact_ids=["public_symbol:legacyexport"], id="F03")
    keep = cited("quality", FIRST + 2, id="F04")
    reply = raw_reply("REJECT_FACTUAL", [hidden, long_span, cross, keep])
    unit = scope("opening", "key_capabilities")
    assert _run(reply, unit) == []
    assert [f["id"] for f in reply["findings"]] == ["F04"]
    assert [n["class"] for n in _notes(reply, "dropped")] == ["unshown_lines", "span_too_long", "unshown_lines"]


def test_a_quote_that_is_not_the_candidate_and_a_missing_quote_are_dropped() -> None:
    fake = raw_finding("contradiction", quote="text the candidate never printed", fact_ids=["public_symbol:legacyexport"])
    bare = raw_finding("contradiction", id="F02", quote="", fact_ids=["public_symbol:legacyexport"])
    reply = raw_reply("REJECT_FACTUAL", [fake, bare, cited("quality", FIRST, id="F03")])
    assert _run(reply) == []
    assert [f["id"] for f in reply["findings"]] == ["F03"]
    assert [n["class"] for n in _notes(reply, "dropped")] == ["unlocatable_quote", "missing_quote"]


def test_a_quality_finding_on_a_renderer_owned_section_is_dropped() -> None:
    unit = scope("installation", "key_capabilities")
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", at("pip install"), section_id="installation"),
                                                cited("quality", FIRST, id="F02")])
    # the installation block is renderer text and not shown; a shown renderer-owned section is the case
    shown = ReviewScope(unit.sections, unit.lines | {at("pip install")})
    assert _run(reply, shown) == []
    assert _notes(reply, "dropped")[0]["class"] == "renderer_owned_quality"


def test_malformed_lines_and_a_non_object_finding_are_dropped() -> None:
    bad = cited("quality", FIRST)
    bad["lines"] = ["x"]
    reply = raw_reply("REJECT_PRESENTATION", [bad, "oops", cited("quality", FIRST + 1, id="F02")])
    assert _run(reply) == []
    assert [f["id"] for f in reply["findings"]] == ["F02"]
    assert {n["class"] for n in _notes(reply, "dropped")} == {"malformed_lines", "not_an_object"}


def test_malformed_or_repeated_ids_are_renumbered_and_too_many_findings_keep_the_first() -> None:
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST, id="x"),
                                                cited("quality", FIRST + 1, id="F01"),
                                                cited("quality", FIRST + 2, id="F01")])
    assert _run(reply) == []
    assert sorted(f["id"] for f in reply["findings"]) == ["F01", "F02", "F03"]
    many = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST + n, id=f"F{n + 1:02d}") for n in range(4)])
    set_aside_void_findings(many, CANDIDATE, FACTS, {}, scope("key_capabilities"), max_findings=3)
    assert len(many["findings"]) == 3 and _notes(many, "dropped")[0]["class"] == "too_many_findings"


# --- negative controls: nothing valid is cleared, nothing is hidden ---------------------------------------


def test_a_valid_contradiction_and_a_valid_typed_finding_are_kept_and_block() -> None:
    reply = raw_reply("REJECT_FACTUAL", [
        cited("contradiction", FIRST, fact_ids=["public_symbol:legacyexport"]),
        cited("absence", FIRST + 1, absent=["Capability 99"], id="F02", quote="") if False else
        cited("quality", FIRST + 1, id="F02"),
    ])
    assert _run(reply) == []
    assert len(reply["findings"]) == 2 and reply["verdict"] == "REJECT_FACTUAL"
    assert CONTRACT_NOTES_KEY not in reply


def test_a_drop_never_turns_a_remaining_reject_into_accept_and_insufficient_stays() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=[]),
                                           cited("quality", FIRST + 1, id="F02")])
    _run(reply)
    assert reply["verdict"] == "REJECT_FACTUAL"
    insufficient = raw_reply("INSUFFICIENT_EVIDENCE", [cited("contradiction", FIRST, fact_ids=[])])
    _run(insufficient)
    assert insufficient["verdict"] == "INSUFFICIENT_EVIDENCE" and insufficient["findings"] == []


def test_reply_level_errors_are_still_errors() -> None:
    assert _run({"verdict": "MAYBE", "findings": [], "preserve": []})
    assert _run(raw_reply("REJECT_FACTUAL", []))  # a reject with no finding to begin with
    assert _run(raw_reply("ACCEPT", [cited("quality", FIRST)]))
    assert _run({"verdict": "ACCEPT", "findings": "none", "preserve": []})


def test_lane_l_edit_reviews_keep_the_strict_contract() -> None:
    reply = raw_reply("REJECT_FACTUAL", [cited("contradiction", FIRST, fact_ids=[])])
    errors = _run(reply, changed=frozenset({FIRST}))
    assert any("product fact" in e for e in errors)
    assert CONTRACT_NOTES_KEY not in reply


def test_the_helper_leaves_a_reply_whose_verdict_is_invalid_alone() -> None:
    reply = {"verdict": "MAYBE", "findings": [cited("contradiction", FIRST, fact_ids=[])], "preserve": []}
    assert set_aside_void_findings(reply, CANDIDATE, FACTS, {}, scope("key_capabilities")) == []
    assert len(reply["findings"]) == 1


@pytest.mark.parametrize("kind", ["contradiction", "unsupported_claim", "quality", "omission", "absence", "name_denial"])
def test_every_claim_kind_can_not_leave_a_reply_the_validator_rejects_per_finding(kind: str) -> None:
    """Whatever the finding, after the repair the validator reports no per-finding error."""
    junk = cited(kind, FIRST, fact_ids=["bogus:1"], criterion="factuality", causal_stage="S0", text="", repair="",
                 id="zz")
    reply = raw_reply("REJECT_FACTUAL", [junk, cited("quality", FIRST + 1, id="F02")])
    assert _run(reply) == []
    assert validate_review_reply(reply, candidate_readme=CANDIDATE, facts=FACTS, plan={},
                                 scope=scope("key_capabilities")) == []
