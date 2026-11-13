"""A kept unit printed with an intra-document link unlinked is printed (class C4).

Aspose.Email-FOSS-for-Cpp, hosted Lane R run 43419173061 (reproduced from its sealed bundle with
``030.paragraph`` restored as PRESERVE_ATTRIBUTED into development_testing): the renderer printed
the unit, but placement unlinks "[Additional Examples](#additional-examples)" because the plan
does not render that section (``placement.resolve_intra_document_anchors``), while the reviewer
judged the raw text, so ``disposition_coverage`` reported "inherited_unit:030.paragraph is kept
(PRESERVE_ATTRIBUTED) but its text is not printed in the README". The repair then could not route
the finding ("no stored disposition of an inherited unit is named by this defect"): its quote is
the raw unit text, which no placed text contains. Attribution wording is never printed (R9);
that was not the cause.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.loop import _named_units
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units

UNIT = "inherited_unit:030.paragraph"
RAW = (
    "For a full command-line workflow, see\n"
    "[`examples/msg_reader.cpp`](examples/msg_reader.cpp) under\n"
    "[Additional Examples](#additional-examples) below."
)
PRINTED = (
    "For a full command-line workflow, see\n"
    "[`examples/msg_reader.cpp`](examples/msg_reader.cpp) under\n"
    "Additional Examples below."
)
ROW = {
    "unit_id": UNIT,
    "disposition": "PRESERVE_ATTRIBUTED",
    "destination_section": "development_testing",
    "fact_ids": [],
    "rationale": "kept as the maintainers wrote it",
}


def _facts() -> FactsDocument:
    return FactsDocument(
        "org/cpp",
        "0" * 40,
        (Fact(UNIT, "inherited_unit", RAW, (Evidence("README.md", None),)),),
    )


def test_a_kept_unit_printed_with_its_dead_anchor_unlinked_is_printed() -> None:
    readme = f"## Development and Testing\n\n{PRINTED}\n"
    assert unprinted_kept_units(readme, facts=_facts(), dispositions={"dispositions": [ROW]}) == []


def test_a_kept_unit_whose_words_are_missing_is_still_unprinted() -> None:
    readme = "## Development and Testing\n\nFor a full command-line workflow, see the examples.\n"
    assert unprinted_kept_units(
        readme, facts=_facts(), dispositions={"dispositions": [ROW]}
    ) == [(UNIT, "PRESERVE_ATTRIBUTED")]


def test_a_coverage_finding_quoting_the_raw_unit_names_its_stored_disposition() -> None:
    rc = SimpleNamespace(
        plan={"sections": [{"section_id": "development_testing", "include": True}]},
        dispositions={"dispositions": [ROW]},
        facts=_facts(),
        entry=SimpleNamespace(ecosystem="python"),
    )
    defect = SimpleNamespace(
        record={"rule": "disposition_coverage", "quote": RAW, "message": "not printed"}
    )
    assert _named_units(rc, defect) == [UNIT]  # type: ignore[arg-type]
