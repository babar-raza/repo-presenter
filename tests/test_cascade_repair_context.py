"""The repair context the cascade builds must carry the dispositions the S5-S8 calls were MADE from,
not the S9-accounted ones the README was finally rendered with.

Measured 2026-11-04 (aspose-font-foss/Aspose.Font-FOSS-for-Python, Lane R): the BC-07
visible-line-budget defect routes to an S5 plan repair. ``repair.loop._repair_plan`` rebuilds the
planning request hash from ``rc.dispositions`` and looks the plan up in the call store. The cascade
built ``rc`` from ``_Composition.dispositions`` - the accounted set - so whenever S9 accounting had
added a disposition the hash missed ("the causing plan is not in the call store"), the repair was
recorded unrepairable, and a candidate that merely needed to be trimmed could never seal. The
disk-based path (``repair.loop._load_context``) already reads ``dispositions.composed.json``, the
pre-accounting set, for the same reason."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter import cascade
from repo_presenter.readme.repair import loop
from tests.readme.composition.synthetic import make_entry, make_facts

PLANNED = {"dispositions": [{"unit_id": "inherited_unit:001.heading", "disposition": "VERIFIED_PRESERVE"}]}
ACCOUNTED = {
    "dispositions": [
        *PLANNED["dispositions"],
        {"unit_id": "inherited_unit:002.paragraph", "disposition": "SUPERSEDE_REDUNDANT"},
    ]
}


def _composition(**overrides):
    base = {
        "dispositions": ACCOUNTED,
        "plan": {},
        "units_document": {},
        "coherent_units": {},
        "readme": "",
        "tasks": [],
        "accounted": [],
    }
    base.update(overrides)
    return cascade._Composition(**base)


def _captured(monkeypatch, composed):
    seen = []
    monkeypatch.setattr(loop, "repair_defect", lambda rc, defect, repairs: seen.append(rc) or False)
    repairs = SimpleNamespace(attempted=lambda fingerprint: False, note_re_raised=lambda d: None)
    defect = SimpleNamespace(fingerprint="f", stage="S5", label="BC-07", record={}, source="validation")
    monkeypatch.setattr(cascade, "merge_equivalent", lambda defects: defects)
    cascade._repair_defects(
        defects=[defect], composed=composed, investigation={}, entry=make_entry(),
        document=make_facts(), prompts={}, config=None, ledger=None, store=None, context=None,
        repairs=repairs,
    )
    return seen


def test_the_repair_context_uses_the_dispositions_the_calls_were_made_from(monkeypatch):
    (rc,) = _captured(monkeypatch, _composition(planned_dispositions=PLANNED))
    assert rc.dispositions == PLANNED
    assert rc.dispositions != ACCOUNTED


def test_without_a_separate_planned_set_the_context_falls_back_to_the_composition_dispositions(
    monkeypatch,
):
    (rc,) = _captured(monkeypatch, _composition())
    assert rc.dispositions == ACCOUNTED
