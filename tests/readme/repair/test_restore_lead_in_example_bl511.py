"""BL-511: a restored lead-in does not drag the example fence it introduces out of the examples renderer.

Hosted PDF TypeScript Lane R (run 44717025933): the restore re-dispositioned 15 units (the framing
paragraphs ``240``/``303``/``409`` lost API identifiers). ``_with_lead_in_payloads`` pulled the code block
each colon-ending lead-in introduces (``241``/``304``/``410``) along, and a code block in an example
fence is printed by the examples renderer while its unit stays ``SUPERSEDE_REDUNDANT`` citing the
example (``reconciliation.retained_examples``). Re-dispositioned to "kept as written" it became
``placement``'s "owned elsewhere" and printed nothing: three new BC-17 losses, and the strictly-fewer
guard discarded the whole restore, 102 recoverable losses with it.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.restore_units import owned_elsewhere, restore_lost_units

LEAD = "inherited_unit:240.paragraph"
BLOCK = "inherited_unit:241.code_block"
_EV = (Evidence("README.md", "lines 1-1"),)
LEAD_TEXT = (
    "An annotation also **carries** text it never draws. The same reducer is exported as "
    "`richTextToPlain`:"
)


def _facts(fence: str) -> FactsDocument:
    code = f"```{fence}\nprint(richTextToPlain(rc))\n```"
    return FactsDocument(
        "aspose-pdf-foss/Aspose.PDF-FOSS-for-Python",
        "0" * 40,
        (
            Fact("identity:ecosystem", "identity", "python", _EV),
            Fact(LEAD, "inherited_unit", LEAD_TEXT, _EV, attributes={"section": "Examples"}),
            Fact(BLOCK, "inherited_unit", code, _EV, attributes={"section": "Examples"}),
        ),
    )


def _dispositions() -> dict:
    return {
        "dispositions": [
            {"unit_id": LEAD, "disposition": "SUPERSEDE_REDUNDANT",
             "destination_section": "additional_examples", "fact_ids": [],
             "rationale": "Reprinted verbatim in Additional Examples beside the unverified example."},
            {"unit_id": BLOCK, "disposition": "SUPERSEDE_REDUNDANT",
             "destination_section": "additional_examples", "fact_ids": ["example:001"],
             "rationale": "Reprinted verbatim in Additional Examples with a not-verified note."},
        ]
    }


HOLDABLE = {"additional_examples", "quick_start", "api_reference"}


def _row(dispositions: dict, unit: str) -> dict:
    return next(r for r in dispositions["dispositions"] if r["unit_id"] == unit)


def test_an_example_fence_payload_is_not_restored_with_its_lead_in() -> None:
    restored, changes = restore_lost_units(_dispositions(), _facts("python"), [LEAD], HOLDABLE, HOLDABLE)
    assert [c["unit_id"] for c in changes] == [LEAD]
    assert _row(restored, LEAD)["disposition"] == "PRESERVE_ATTRIBUTED"  # kept as written (no fact confirms it)
    # The example stays with the examples renderer: same disposition, citation and rationale (R14).
    assert _row(restored, BLOCK) == _row(_dispositions(), BLOCK)


def test_negative_control_a_payload_placement_prints_is_still_restored_with_its_lead_in() -> None:
    restored, changes = restore_lost_units(_dispositions(), _facts("bash"), [LEAD], HOLDABLE, HOLDABLE)
    assert sorted(c["unit_id"] for c in changes) == [LEAD, BLOCK]
    assert _row(restored, BLOCK)["disposition"] in {"VERIFIED_PRESERVE", "PRESERVE_ATTRIBUTED"}


def test_owned_elsewhere_names_example_fences_and_diagrams_only() -> None:
    units = {f.id: f for f in _facts("python").by_kind("inherited_unit")}
    assert owned_elsewhere(BLOCK, units, "python") is True
    assert owned_elsewhere(LEAD, units, "python") is False  # not a code block
    bash = {f.id: f for f in _facts("bash").by_kind("inherited_unit")}
    assert owned_elsewhere(BLOCK, bash, "python") is False
    assert owned_elsewhere(BLOCK, units, "no-such-ecosystem") is False  # unknown spec: old behaviour


def test_negative_control_without_the_guard_the_example_fence_is_restored_and_prints_nowhere(
    monkeypatch,
) -> None:
    import repo_presenter.readme.repair.restore_units as module

    monkeypatch.setattr(module, "owned_elsewhere", lambda *a, **k: False)
    _, changes = restore_lost_units(_dispositions(), _facts("python"), [LEAD], HOLDABLE, HOLDABLE)
    assert [c["unit_id"] for c in changes] == [LEAD, BLOCK]  # the shape that lost the example
