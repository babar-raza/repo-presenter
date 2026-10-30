"""reconciliation_narrowing's own parsing/merge helpers, tested directly (the integration-level
behavior -- a real narrowed third ask through run_job -- is tested in tests/test_cascade_s9.py,
where it was found and fixed: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41090058316)."""

from __future__ import annotations

import json
from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.reconciliation.dispositions import (
    DANGLING_POINTER,
    UNCITED_REDUNDANT_DIAGRAM,
    _reconciliation_ask,
    _reconciliation_merge,
    _reconciliation_repeated,
    _rejected_unit_ids,
)
from tests.readme.composition.synthetic import make_entry, make_facts

A = "inherited_unit:001.paragraph"
B = "inherited_unit:002.code_block"

PROMPTS_PATH = Path(__file__).resolve().parents[3] / "prompts"


def test_a_units_own_prefixed_rejection_line_names_it() -> None:
    assert _rejected_unit_ids([f"{B}: uncited_redundant_defer: DEFER_UNRESOLVED ..."]) == [B]


def test_several_prefixed_lines_name_each_unit_once_in_first_seen_order() -> None:
    rejection = [f"{B}: reason one", f"{A}: reason two", f"{B}: reason three"]
    assert _rejected_unit_ids(rejection) == [B, A]


def test_the_missing_units_line_names_every_unit_it_lists() -> None:
    rejection = [f"no disposition for inherited units: {A}, {B}"]
    assert _rejected_unit_ids(rejection) == [A, B]


def test_the_duplicated_units_line_names_every_unit_it_lists() -> None:
    rejection = [f"more than one disposition for: {A}"]
    assert _rejected_unit_ids(rejection) == [A]


def test_a_line_naming_no_unit_at_all_empties_the_whole_result() -> None:
    """A schema error or an unknown-fact-ID line names no unit a narrowed ask could address --
    the same conservative bail authoring_retry.py's own failing_slots uses: narrow nothing rather
    than guess, and the job fails exactly as it did before this mechanism existed."""
    rejection = [f"{B}: a real reason", "unknown fact ID package:nope"]
    assert _rejected_unit_ids(rejection) == []


def test_no_rejection_at_all_is_nothing_to_narrow() -> None:
    assert _rejected_unit_ids([]) == []


def _entry(unit_id: str, disposition: str = "VERIFIED_PRESERVE", **extra: object) -> dict:
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": extra.get("destination_section"),
        "fact_ids": extra.get("fact_ids", []),
        "rationale": extra.get("rationale", "because"),
    }


def test_merge_replaces_the_named_unit_in_place_and_keeps_order() -> None:
    merged = json.dumps({"dispositions": [_entry(A), _entry(B, "DEFER_UNRESOLVED")]})
    fixed = _entry(B, "VERIFIED_MOVE", destination_section="scope_limitations")
    narrowed = json.dumps({"dispositions": [fixed]})
    result = json.loads(_reconciliation_merge(merged, narrowed, [B]))
    assert [entry["unit_id"] for entry in result["dispositions"]] == [A, B]
    assert result["dispositions"][1]["disposition"] == "VERIFIED_MOVE"


def test_merge_appends_a_unit_the_base_never_had_at_all() -> None:
    merged = json.dumps({"dispositions": [_entry(A)]})
    narrowed = json.dumps({"dispositions": [_entry(B)]})
    result = json.loads(_reconciliation_merge(merged, narrowed, [B]))
    assert {entry["unit_id"] for entry in result["dispositions"]} == {A, B}


def test_merge_refuses_a_narrowed_reply_that_does_not_cover_exactly_what_was_asked() -> None:
    """A narrowed reply naming a different unit than it was asked about is returned unchanged,
    to be refused by the ordinary schema/binding checks rather than quietly repaired."""
    merged = json.dumps({"dispositions": [_entry(A), _entry(B, "DEFER_UNRESOLVED")]})
    narrowed = json.dumps({"dispositions": [_entry(A)]})  # asked for B, answered about A
    result = _reconciliation_merge(merged, narrowed, [B])
    assert result == narrowed


def test_repeated_names_a_unit_whose_two_replies_are_byte_identical() -> None:
    first = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    second = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    assert _reconciliation_repeated(first, second, [B]) == [B]


def test_repeated_is_empty_when_the_second_reply_actually_changed() -> None:
    first = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    second = json.dumps({"dispositions": [_entry(B, "VERIFIED_PRESERVE")]})
    assert _reconciliation_repeated(first, second, [B]) == []


# Measured live, twice (aspose-slides-foss/Java run 41112860184, aspose-words-foss/.NET run
# 41121235240): told a disposition was rejected as dangling_pointer, both narrowed-ask replies
# chose OMIT_UNSUPPORTED uncited instead of the VERIFIED_REWRITE the rejection message already
# names, failing a second, different check on this same, final ask.
def test_the_narrowed_ask_steers_explicitly_toward_verified_rewrite_on_a_dangling_pointer() -> (
    None
):
    unit = "inherited_unit:046.paragraph"
    facts = FactsDocument(
        make_facts().repository,
        make_facts().source_revision,
        (
            *(f for f in make_facts().facts if f.kind != "inherited_unit"),
            Fact(
                unit,
                "inherited_unit",
                "The table below covers the full API.",
                (Evidence("README.md", None),),
            ),
        ),
    )
    manifest = load_manifests(PROMPTS_PATH)["source_reconciliation"]
    rejection = [
        f"{unit}: {DANGLING_POINTER}: VERIFIED_MOVE keeps it as written in api_reference, but "
        "its sentence \"The table below covers the full API.\" says 'below' but no table "
        "follows it in this section. Kept units print after the section's own content, so a "
        "pointer to what follows is answered only by a unit kept right after it in the same "
        "section: keep that unit there too, or choose VERIFIED_REWRITE (the wording is "
        "re-authored from facts, without the pointer), or OMIT_UNSUPPORTED citing the fact that "
        "shows the claim unsupported"
    ]
    packet, _schema = _reconciliation_ask(
        [unit],
        "",
        rejection,
        [],
        entry=make_entry(),
        batch_units=[fact for fact in facts.facts if fact.kind == "inherited_unit"],
        batch_facts=facts,
        investigation={},
        manifest=manifest,
    )
    (record,) = packet["inherited_units"]
    assert "VERIFIED_REWRITE needs no cited fact at all" in record["text"]
    assert "This is the last ask for this unit" in record["text"]


def test_the_narrowed_ask_adds_no_extra_steer_for_an_unrelated_rejection() -> None:
    unit = "inherited_unit:050.paragraph"
    facts = FactsDocument(
        make_facts().repository,
        make_facts().source_revision,
        (
            *(f for f in make_facts().facts if f.kind != "inherited_unit"),
            Fact(unit, "inherited_unit", "A plain paragraph.", (Evidence("README.md", None),)),
        ),
    )
    manifest = load_manifests(PROMPTS_PATH)["source_reconciliation"]
    rejection = [f"{unit}: uncited_prose_omit: OMIT_UNSUPPORTED on a paragraph needs a fact ID"]
    packet, _schema = _reconciliation_ask(
        [unit],
        "",
        rejection,
        [],
        entry=make_entry(),
        batch_units=[fact for fact in facts.facts if fact.kind == "inherited_unit"],
        batch_facts=facts,
        investigation={},
        manifest=manifest,
    )
    (record,) = packet["inherited_units"]
    assert "VERIFIED_REWRITE needs no cited fact at all" not in record["text"]


# Measured live, three times in one batch (aspose-3d-foss/Java run 41133510789, aspose-3d-foss/
# TypeScript run 41133521004, aspose-page-foss/Python's own unit 008): told SUPERSEDE_REDUNDANT
# on a diagram code_block needed a fact ID, every reply left fact_ids empty, byte-identical
# across all three asks -- at_a_glance's own content is an S5 planning choice that does not
# exist yet at S4, so there is no fixed content fact to cite; the identity fact is.
def test_the_narrowed_ask_names_a_real_identity_fact_on_an_uncited_redundant_diagram() -> None:
    unit = "inherited_unit:008.code_block"
    facts = FactsDocument(
        make_facts().repository,
        make_facts().source_revision,
        (
            *(f for f in make_facts().facts if f.kind != "inherited_unit"),
            Fact(unit, "inherited_unit", "```mermaid\nflowchart LR\n```", (Evidence("README.md", None),)),
        ),
    )
    manifest = load_manifests(PROMPTS_PATH)["source_reconciliation"]
    rejection = [
        f"{unit}: {UNCITED_REDUNDANT_DIAGRAM}: SUPERSEDE_REDUNDANT on a code_block needs at "
        "least one fact ID showing what the destination section regenerates it from"
    ]
    packet, _schema = _reconciliation_ask(
        [unit],
        "",
        rejection,
        [],
        entry=make_entry(),
        batch_units=[fact for fact in facts.facts if fact.kind == "inherited_unit"],
        batch_facts=facts,
        investigation={},
        manifest=manifest,
    )
    (record,) = packet["inherited_units"]
    assert "Cite 'identity:repository'" in record["text"]


def test_the_narrowed_ask_adds_no_diagram_steer_for_an_unrelated_rejection() -> None:
    unit = "inherited_unit:009.code_block"
    facts = FactsDocument(
        make_facts().repository,
        make_facts().source_revision,
        (
            *(f for f in make_facts().facts if f.kind != "inherited_unit"),
            Fact(unit, "inherited_unit", "```bash\necho hi\n```", (Evidence("README.md", None),)),
        ),
    )
    manifest = load_manifests(PROMPTS_PATH)["source_reconciliation"]
    rejection = [f"{unit}: uncited_prose_omit: OMIT_UNSUPPORTED on a paragraph needs a fact ID"]
    packet, _schema = _reconciliation_ask(
        [unit],
        "",
        rejection,
        [],
        entry=make_entry(),
        batch_units=[fact for fact in facts.facts if fact.kind == "inherited_unit"],
        batch_facts=facts,
        investigation={},
        manifest=manifest,
    )
    (record,) = packet["inherited_units"]
    assert "Cite 'identity:repository'" not in record["text"]
