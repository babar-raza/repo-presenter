"""TC-018: ``readme/validation/supersession.py``'s ``obligation_failures`` -- the generalization
of ``superseded_failures`` from SUPERSEDE_REDUNDANT-only to every disposition, via
``readme/obligations/classify.py``'s mechanical rule table."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.readme.validation.supersession import (
    OBLIGATION_LOSS_MARKER,
    obligation_failures,
)

FENCE = "`" * 3


class FakeFacts:
    def __init__(self, facts):
        self._facts = list(facts)
        self.facts = tuple(self._facts)

    def by_kind(self, kind):
        return tuple(f for f in self._facts if f.kind == kind)


def _fact(fid, kind, value, polarity="SUPPORTED", evidence=()):
    return SimpleNamespace(id=fid, kind=kind, value=value, polarity=polarity, evidence=evidence)


def _candidate(facts, dispositions, readme, tree_paths=()):
    return SimpleNamespace(
        facts=FakeFacts(facts),
        dispositions={"dispositions": dispositions},
        readme=readme,
        tree_paths=list(tree_paths),
    )


def _row(unit_id, disposition):
    return {"unit_id": unit_id, "disposition": disposition, "fact_ids": [], "rationale": ""}


def test_public_api_row_omitted_under_verified_rewrite_is_a_loss():
    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:001.table",
            "inherited_unit",
            "| `Widget` | Represents a widget and its drawing surface. |",
        ),
    ]
    candidate = _candidate(
        facts,
        [_row("inherited_unit:001.table", "VERIFIED_REWRITE")],
        readme="nothing relevant here",
    )
    failures = obligation_failures(candidate)
    assert len(failures) == 1
    assert failures[0].stage == "RECONCILING"
    assert failures[0].unit == "inherited_unit:001.table"
    assert OBLIGATION_LOSS_MARKER in failures[0].detail


def test_public_api_row_omitted_under_defer_unresolved_is_a_loss():
    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:002.table",
            "inherited_unit",
            "| `Widget` | Represents a widget and its drawing surface. |",
        ),
    ]
    candidate = _candidate(
        facts,
        [_row("inherited_unit:002.table", "DEFER_UNRESOLVED")],
        readme="nothing relevant here",
    )
    failures = obligation_failures(candidate)
    assert [f.unit for f in failures] == ["inherited_unit:002.table"]


def test_private_api_row_omitted_is_not_a_loss():
    facts = [
        _fact(
            "inherited_unit:003.table",
            "inherited_unit",
            "| `_Hidden` | Internal helper, not part of the public API. |",
        ),
    ]
    candidate = _candidate(
        facts,
        [_row("inherited_unit:003.table", "OMIT_UNSUPPORTED")],
        readme="nothing relevant here",
    )
    assert obligation_failures(candidate) == []


def test_filler_description_row_omitted_is_not_a_loss():
    facts = [
        _fact("public_symbol:cellvalue", "public_symbol", "Foo.CellValue"),
        _fact(
            "inherited_unit:004.table",
            "inherited_unit",
            "| `CellValue` | Enum with 8 methods and 7 members. |",
        ),
    ]
    candidate = _candidate(
        facts,
        [_row("inherited_unit:004.table", "OMIT_UNSUPPORTED")],
        readme="nothing relevant here",
    )
    assert obligation_failures(candidate) == []


def test_superseded_unit_is_left_to_superseded_failures_not_double_flagged():
    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:005.table",
            "inherited_unit",
            "| `Widget` | Represents a widget and its drawing surface. |",
        ),
    ]
    candidate = _candidate(
        facts,
        [_row("inherited_unit:005.table", "SUPERSEDE_REDUNDANT")],
        readme="nothing relevant here",
    )
    assert obligation_failures(candidate) == []


def test_public_row_actually_stated_is_not_a_loss():
    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:006.table",
            "inherited_unit",
            "| `Widget` | Represents a widget and its drawing surface. |",
        ),
    ]
    readme = "## API Reference\n\n| `Widget` | Represents a widget and its drawing surface. |\n"
    candidate = _candidate(
        facts, [_row("inherited_unit:006.table", "VERIFIED_REWRITE")], readme=readme
    )
    assert obligation_failures(candidate) == []


def test_requalified_name_counts_as_carried_not_re_flagged():
    """R-API-REQUALIFIED (the drop inventory's own "over-flag" finding): a candidate that prints
    the same name package-qualified must not be flagged as having lost it."""
    facts = [
        _fact("public_symbol:diagnosticseverity", "public_symbol", "Foo.DiagnosticSeverity"),
        _fact(
            "inherited_unit:007.table",
            "inherited_unit",
            "| `DiagnosticSeverity-core` | Specifies diagnostic severity. |",
        ),
    ]
    readme = "## API Reference\n\n| `core.DiagnosticSeverity` | Specifies diagnostic severity. |\n"
    candidate = _candidate(
        facts, [_row("inherited_unit:007.table", "OMIT_UNSUPPORTED")], readme=readme
    )
    assert obligation_failures(candidate) == []


def test_contradicted_example_code_block_is_not_a_loss():
    facts = [
        _fact(
            "inherited_unit:008.code_block",
            "inherited_unit",
            f"{FENCE}python\nraise RuntimeError\n{FENCE}",
        ),
        _fact(
            "example:001",
            "example",
            "code",
            "CONTRADICTED",
            evidence=(SimpleNamespace(path="README.md", detail="unit inherited_unit:008.code_block"),),
        ),
    ]
    candidate = _candidate(
        facts, [_row("inherited_unit:008.code_block", "OMIT_UNSUPPORTED")], readme="x"
    )
    assert obligation_failures(candidate) == []


def test_unverified_code_block_missing_from_the_candidate_is_a_loss():
    facts = [
        _fact(
            "inherited_unit:009.code_block",
            "inherited_unit",
            f"{FENCE}csharp\nvar x = Scene.FromFile(\"input.gltf\");\n{FENCE}",
        ),
        _fact(
            "example:001",
            "example",
            "code",
            "UNRESOLVED",
            evidence=(SimpleNamespace(path="README.md", detail="unit inherited_unit:009.code_block"),),
        ),
    ]
    candidate = _candidate(
        facts, [_row("inherited_unit:009.code_block", "OMIT_UNSUPPORTED")], readme="no code here"
    )
    failures = obligation_failures(candidate)
    assert [f.unit for f in failures] == ["inherited_unit:009.code_block"]
