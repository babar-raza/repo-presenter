"""TC-018 gate/test requirement 2 (unit-level coverage): ``build_ledger``/``ledger_from_candidate``
account for every decomposed piece of every inherited unit, at zero provider calls, and the
piece-level obligations they compute agree with :mod:`readme.obligations.classify`'s own rules.

The end-to-end "at least 3 real sealed bundles" run is ``scripts/build_content_ledger.py``'s own
job (its ``--self-test`` is this card's automated check; a real run against materialized bundles
is this card's hand-run evidence, documented in the card's closeout) -- this file tests the pure
``build_ledger`` function against small, fully-specified fixtures instead, so it runs in the same
offline, no-network pytest invocation as everything else here.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.readme.obligations.ledger import (
    build_ledger,
    example_polarity_by_unit,
    ledger_from_candidate,
    public_symbol_names,
)

FENCE = "`" * 3


def _fact(fid, kind, value, polarity="SUPPORTED", evidence=()):
    return SimpleNamespace(id=fid, kind=kind, value=value, polarity=polarity, evidence=evidence)


def test_build_ledger_accounts_for_every_piece_of_every_unit():
    inherited = [
        {"id": "inherited_unit:001.heading", "kind": "heading", "text": "# Foo"},
        {
            "id": "inherited_unit:002.table",
            "kind": "table",
            "text": "\n".join(
                [
                    "| Name | Description |",
                    "| --- | --- |",
                    "| `Widget` | Represents a widget. |",
                    "| `_Hidden` | Internal only. |",
                ]
            ),
        },
        {
            "id": "inherited_unit:003.list",
            "kind": "list",
            "text": "- First bullet.\n- Second bullet.\n- Third bullet.",
        },
        {
            "id": "inherited_unit:004.paragraph",
            "kind": "paragraph",
            "text": "First sentence here. Second sentence follows it now.",
        },
        {"id": "inherited_unit:005.code_block", "kind": "code_block", "text": f"{FENCE}\nx = 1\n{FENCE}"},
        {"id": "inherited_unit:006.badge_row", "kind": "badge_row", "text": "[![x](y)](z)"},
    ]
    entries = build_ledger(
        inherited_units=inherited,
        readme="irrelevant",
        public_names=frozenset({"widget"}),
        dispositions={u["id"]: "OMIT_UNSUPPORTED" for u in inherited},
    )
    # One heading piece, two table rows, three list items, two sentences, one code block, one
    # badge row: every byte of every unit is accounted for by some entry.
    assert len(entries) == 1 + 2 + 3 + 2 + 1 + 1
    by_unit = {}
    for entry in entries:
        by_unit.setdefault(entry.unit_id, []).append(entry)
    assert set(by_unit) == {u["id"] for u in inherited}
    for entry in entries:
        assert entry.obligation in ("must_carry", "may_drop", "undecided")
        assert entry.disposition == "OMIT_UNSUPPORTED"


def test_public_table_row_is_must_carry_and_private_is_may_drop():
    inherited = [
        {
            "id": "inherited_unit:010.table",
            "kind": "table",
            "text": "| `Widget` | Represents a widget. |\n| `_Hidden` | Internal only. |",
        }
    ]
    entries = build_ledger(
        inherited_units=inherited, readme="x", public_names=frozenset({"widget"})
    )
    by_text = {e.text: e for e in entries}
    public_row = next(e for e in entries if "Widget" in e.text and "_Hidden" not in e.text)
    private_row = next(e for e in entries if "_Hidden" in e.text)
    assert public_row.obligation == "must_carry"
    assert private_row.obligation == "may_drop"
    assert private_row.carried is None  # may_drop pieces are never presence-checked


def test_must_carry_piece_present_in_readme_is_marked_carried():
    inherited = [
        {
            "id": "inherited_unit:020.table",
            "kind": "table",
            "text": "| `Widget` | Represents a widget and its surface area. |",
        }
    ]
    readme = "## API Reference\n\n| `Widget` | Represents a widget and its surface area. |\n"
    entries = build_ledger(
        inherited_units=inherited, readme=readme, public_names=frozenset({"widget"})
    )
    assert entries[0].obligation == "must_carry"
    assert entries[0].carried is True


def test_must_carry_piece_missing_from_readme_is_marked_not_carried():
    inherited = [
        {
            "id": "inherited_unit:021.table",
            "kind": "table",
            "text": "| `Widget` | Represents a widget and its drawing surface. |",
        }
    ]
    entries = build_ledger(
        inherited_units=inherited, readme="nothing relevant here", public_names=frozenset({"widget"})
    )
    assert entries[0].obligation == "must_carry"
    assert entries[0].carried is False
    assert "missing" in entries[0].evidence


def test_contradicted_example_code_block_is_may_drop():
    inherited = [
        {
            "id": "inherited_unit:030.code_block",
            "kind": "code_block",
            "text": f"{FENCE}python\nraise RuntimeError\n{FENCE}",
        }
    ]
    entries = build_ledger(
        inherited_units=inherited,
        readme="x",
        example_polarity={"inherited_unit:030.code_block": "CONTRADICTED"},
    )
    assert entries[0].obligation == "may_drop"


def test_mermaid_block_defaults_to_must_carry_without_a_candidate_drawn_equivalent():
    inherited = [
        {
            "id": "inherited_unit:040.code_block",
            "kind": "code_block",
            "text": f"{FENCE}mermaid\ngraph TD\nA-->B\n{FENCE}",
        }
    ]
    entries = build_ledger(inherited_units=inherited, readme="no diagram here")
    assert entries[0].obligation == "must_carry"


def test_mermaid_block_is_may_drop_when_the_candidate_draws_its_own():
    inherited = [
        {
            "id": "inherited_unit:041.code_block",
            "kind": "code_block",
            "text": f"{FENCE}mermaid\ngraph TD\nA-->B\n{FENCE}",
        }
    ]
    entries = build_ledger(
        inherited_units=inherited, readme=f"{FENCE}mermaid\ngraph LR\nX-->Y\n{FENCE}"
    )
    assert entries[0].obligation == "may_drop"


def test_probe_public_is_consulted_as_an_additional_signal():
    inherited = [
        {
            "id": "inherited_unit:050.table",
            "kind": "table",
            "text": "| `Thing` | Does a thing. |",
        }
    ]
    # No public_symbol fact names Thing, but the probe independently confirms it is exported.
    entries = build_ledger(
        inherited_units=inherited,
        readme="x",
        public_names=frozenset(),
        probe_public=lambda name: True if name == "Thing" else None,
    )
    assert entries[0].obligation == "must_carry"


def test_probe_disagreement_with_facts_is_undecided_never_guessed():
    inherited = [
        {
            "id": "inherited_unit:051.table",
            "kind": "table",
            "text": "| `Thing` | Does a thing. |",
        }
    ]
    entries = build_ledger(
        inherited_units=inherited,
        readme="x",
        public_names=frozenset({"thing"}),
        probe_public=lambda name: False,  # disagrees with the facts-based signal
    )
    assert entries[0].obligation == "undecided"


def test_public_symbol_names_reads_both_fact_objects_and_dict_rows():
    objs = [_fact("public_symbol:widget", "public_symbol", "Foo.Widget")]
    dicts = [
        {"id": "public_symbol:widget", "kind": "public_symbol", "value": "Foo.Widget", "polarity": "SUPPORTED"}
    ]
    assert public_symbol_names(objs) == public_symbol_names(dicts) == frozenset({"widget"})


def test_example_polarity_by_unit_reads_the_unit_marker():
    facts = [
        _fact(
            "example:001",
            "example",
            "code",
            "CONTRADICTED",
            evidence=(SimpleNamespace(path="README.md", detail="unit inherited_unit:003.code_block"),),
        )
    ]
    assert example_polarity_by_unit(facts) == {"inherited_unit:003.code_block": "CONTRADICTED"}


def test_ledger_from_candidate_adapts_a_real_candidate_shape():
    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:001.table",
            "inherited_unit",
            "| `Widget` | Represents a widget. |",
        ),
    ]

    class FakeFacts:
        def __init__(self, facts):
            self._facts = facts
            self.facts = facts

        def by_kind(self, kind):
            return tuple(f for f in self._facts if f.kind == kind)

    candidate = SimpleNamespace(
        facts=FakeFacts(facts),
        dispositions={"dispositions": [{"unit_id": "inherited_unit:001.table", "disposition": "OMIT_UNSUPPORTED"}]},
        readme="nothing relevant stated here",
        tree_paths=[],
    )
    entries = ledger_from_candidate(candidate)
    assert len(entries) == 1
    assert entries[0].obligation == "must_carry"
    assert entries[0].carried is False
    assert entries[0].disposition == "OMIT_UNSUPPORTED"
