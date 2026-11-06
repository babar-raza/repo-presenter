"""A unit failed because superseding it loses content cannot be repaired by superseding it again."""

from __future__ import annotations

from repo_presenter.readme.composition.references import positional_only
from repo_presenter.readme.reconciliation.patch import (
    PatchScope,
    _loss_units,
    patch_checks,
)
from repo_presenter.readme.validation.supersession import LOSS_MARKER

UNIT = "inherited_unit:004.paragraph"


def _scope() -> PatchScope:
    return PatchScope(
        batch_id="b1", unit_ids=(UNIT,), shown={}, contract={}, deferred=frozenset(),
        holdable=("opening", "scope_limitations"), superseded=frozenset({UNIT}),
    )


def _reply(disposition: str) -> dict:
    return {"dispositions": [{"unit_id": UNIT, "disposition": disposition}]}


def test_handing_back_supersede_redundant_is_refused() -> None:
    errors = patch_checks(_scope(), None)(_reply("SUPERSEDE_REDUNDANT"))
    assert errors and "still SUPERSEDE_REDUNDANT" in errors[0]


def test_deferring_it_instead_is_refused_too() -> None:
    assert patch_checks(_scope(), None)(_reply("DEFER_UNRESOLVED"))


def test_keeping_or_attributing_it_passes_this_rule() -> None:
    for disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE", "PRESERVE_ATTRIBUTED"):
        assert patch_checks(_scope(), None)(_reply(disposition)) == []


def test_only_supersession_failures_mark_a_unit() -> None:
    record = {
        "failures": [
            {"unit_id": UNIT, "detail": f"{UNIT} {LOSS_MARKER} 1 piece(s) of it"},
            {"unit_id": "inherited_unit:009.paragraph", "detail": "has 2 dispositions"},
        ]
    }
    assert _loss_units(record) == {UNIT}


def test_a_positional_sentence_is_navigation_not_content() -> None:
    assert positional_only("A few more real, runnable patterns beyond the Quick Start example above.")
    assert not positional_only("The library runs on Windows, Linux and macOS.")


def test_a_keep_the_normaliser_turns_back_into_a_supersession_is_refused() -> None:
    def normaliser(revised: dict) -> list[str]:
        for entry in revised["dispositions"]:
            if entry.get("destination_section") == "opening":
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
        return []

    reply = {"dispositions": [{"unit_id": UNIT, "disposition": "VERIFIED_PRESERVE", "destination_section": "opening"}]}
    errors = patch_checks(_scope(), normaliser)(reply)
    assert errors and "you answered VERIFIED_PRESERVE into opening" in errors[0]
    assert "scope_limitations" in errors[0]
