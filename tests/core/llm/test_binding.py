"""Bind a job's output to the facts it cites: an unknown or contradicted ID rejects the output."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.binding import binding_errors, collect_ids, silent_unit_ids

FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "org/repo", (Evidence("x"),)),
        Fact("package:name", "package", "widget", (Evidence("x"),)),
        Fact("example:001", "example", "bad()", (Evidence("x"),), polarity="CONTRADICTED"),
        Fact(
            "inherited_unit:001.paragraph",
            "inherited_unit",
            "Hello.",
            (Evidence("README.md"),),
        ),
        Fact(
            "inherited_unit:002.paragraph",
            "inherited_unit",
            "World.",
            (Evidence("README.md"),),
        ),
    ),
)


def test_collect_ids_finds_every_fact_id_key_shape() -> None:
    payload = {
        "units": [
            {"slot": "a", "fact_ids": ["package:name"]},
            {"slot": "b", "link_fact_id": "identity:repository"},
        ]
    }
    assert collect_ids(payload).fact_ids == ("package:name", "identity:repository")


def test_an_unknown_fact_id_is_rejected() -> None:
    errors = binding_errors({"fact_ids": ["package:nonexistent"]}, FACTS, "fact_ids")
    assert errors == ["unknown fact ID package:nonexistent"]


def test_a_contradicted_fact_is_rejected_under_fact_ids_binding() -> None:
    errors = binding_errors({"fact_ids": ["example:001"]}, FACTS, "fact_ids")
    assert errors == ["fact example:001 is CONTRADICTED, not SUPPORTED"]


def test_a_contradicted_fact_is_fine_under_finding_ids_binding() -> None:
    # A review finding may point at a contradicted fact as its evidence.
    assert binding_errors({"fact_ids": ["example:001"]}, FACTS, "finding_ids") == []


def test_unit_ids_binding_demands_every_inherited_unit_exactly_once() -> None:
    errors = binding_errors({"unit_ids": ["inherited_unit:001.paragraph"]}, FACTS, "unit_ids")
    assert errors == [
        "no disposition for inherited units: inherited_unit:002.paragraph"
    ]


def test_unit_ids_binding_rejects_a_duplicate() -> None:
    errors = binding_errors(
        {
            "unit_ids": [
                "inherited_unit:001.paragraph",
                "inherited_unit:001.paragraph",
                "inherited_unit:002.paragraph",
            ]
        },
        FACTS,
        "unit_ids",
    )
    assert errors == ["more than one disposition for: inherited_unit:001.paragraph"]


def test_silent_unit_ids_names_every_unit_not_cited() -> None:
    output = {"dispositions": [{"unit_id": "inherited_unit:001.paragraph"}]}
    assert silent_unit_ids(output, FACTS) == ["inherited_unit:002.paragraph"]
