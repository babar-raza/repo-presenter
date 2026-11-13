"""An S6 defect is repaired in the authoring task whose units its findings are about.

Regression for Aspose.BarCode-FOSS-for-Python, hosted run 43394959529: seventeen
``unsupported_claim`` findings about API Reference type rows shared one fingerprint and merged
into one defect; ``_repair_section`` picked the first ``api_reference`` task (intro and hubs), not
the ``api_reference#types-N`` batch that holds the flagged rows, the model returned it unchanged
and the no-op refusal recorded the whole finding unrepairable.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.repair import loop as loop_module
from repo_presenter.readme.repair.loop import _route_section_defect, keep_unflagged_units
from repo_presenter.readme.repair.targeted import Defect, RepairLedger, merge_equivalent

OPTIONS = "public_symbol:pkg.options.code128options"
RENDERER = "public_symbol:pkg.pdfrenderer"
HUB = "public_symbol:pkg.generator"
HUB_TEXT = "The generator builds a barcode from a value and a symbology."
OPTIONS_TEXT = "Provides configuration options for Code 128 barcodes."
RENDERER_TEXT = "Renders barcodes to PDF documents."


def _symbol(fact_id: str, value: str) -> Fact:
    return Fact(
        fact_id,
        "public_symbol",
        value,
        (Evidence("pkg/x.py", "; class; "),),
        attributes={"symbol_kind": "class"},
    )


FACTS = FactsDocument(
    "org/Aspose.BarCode-FOSS-for-Python",
    "f" * 40,
    (
        _symbol(HUB, "pkg.Generator"),
        _symbol(OPTIONS, "pkg.options.Code128Options"),
        _symbol(RENDERER, "pkg.PdfRenderer"),
    ),
)

HUBS = SectionTask(
    "api_reference", {}, frozenset({HUB}), ("intro", f"hub:{HUB}")
)
TYPES = SectionTask(
    "api_reference",
    {},
    frozenset({OPTIONS, RENDERER}),
    (f"type:{OPTIONS}", f"type:{RENDERER}"),
    key="api_reference#types-1",
)
STORED = {
    HUBS.label: {
        "units": [
            {"slot": "intro", "text": "The main entry points."},
            {"slot": f"hub:{HUB}", "text": HUB_TEXT},
        ]
    },
    TYPES.label: {
        "units": [
            {"slot": f"type:{OPTIONS}", "text": OPTIONS_TEXT},
            {"slot": f"type:{RENDERER}", "text": RENDERER_TEXT},
        ]
    },
}


class _Store:
    def __init__(self, stored: dict[str, Any]) -> None:
        self.stored = stored

    def get(self, key: str) -> dict[str, Any] | None:
        return self.stored.get(key)


def _rc(stored: dict[str, Any] = STORED) -> Any:
    return SimpleNamespace(tasks=[HUBS, TYPES], store=_Store(stored), facts=FACTS)


@pytest.fixture(autouse=True)
def _label_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    # The store key is the real request hash in production; here each task's label stands in.
    monkeypatch.setattr(loop_module, "_task_key", lambda rc, loaded, task: task.label)


def _merged(*quotes: str) -> Defect:
    defects = [
        Defect("fp", "review", f"F{index:02d}", "api_reference", "S6", {"quote": quote})
        for index, quote in enumerate(quotes, start=1)
    ]
    (merged,) = merge_equivalent(defects)
    return merged


def _quotes(defect: Defect) -> list[str]:
    return [
        str(finding["quote"])
        for finding in [defect.record, *defect.record.get("equivalent_findings", [])]
    ]


def test_merged_type_row_findings_route_to_the_type_batch_not_the_first_task() -> None:
    defect = _merged(
        "options.Code128Options provides configuration options for Code 128 barcodes",
        "PdfRenderer renders barcodes to PDF",
    )
    (route,) = _route_section_defect(_rc(), defect, None)
    assert route.task is TYPES
    assert route.named_slots == {f"type:{OPTIONS}", f"type:{RENDERER}"}
    assert _quotes(route.defect) == _quotes(defect)


def test_a_quote_found_in_a_stored_unit_routes_by_text() -> None:
    (route,) = _route_section_defect(_rc(), _merged(RENDERER_TEXT), None)
    assert route.task is TYPES
    assert route.named_slots == frozenset()


def test_findings_about_two_tasks_are_split_between_them() -> None:
    defect = _merged(HUB_TEXT, "PdfRenderer renders barcodes to PDF")
    routes = _route_section_defect(_rc(), defect, None)
    assert [route.task for route in routes] == [HUBS, TYPES]
    assert _quotes(routes[0].defect) == [HUB_TEXT]
    assert _quotes(routes[1].defect) == ["PdfRenderer renders barcodes to PDF"]
    assert all(route.defect.fingerprint == "fp" for route in routes)


def test_a_type_batch_is_found_by_name_when_the_store_has_no_original() -> None:
    (route,) = _route_section_defect(_rc({}), _merged("PdfRenderer renders to PDF"), None)
    assert route.task is TYPES
    assert route.named_slots == {f"type:{RENDERER}"}


def test_a_defect_no_finding_locates_keeps_the_first_task_unchanged() -> None:
    defect = _merged("nothing any unit says")
    (route,) = _route_section_defect(_rc(), defect, None)
    assert route.task is HUBS
    assert route.defect == defect


def test_every_merged_findings_unit_may_change_and_no_other() -> None:
    original = STORED[TYPES.label]
    guarded = keep_unflagged_units(
        lambda revised: [], original, ["absent", "also absent"], {f"type:{RENDERER}"}
    )
    renderer_fixed = {
        "units": [
            {"slot": f"type:{OPTIONS}", "text": OPTIONS_TEXT},
            {"slot": f"type:{RENDERER}", "text": "A placeholder; render is not implemented."},
        ]
    }
    assert guarded(renderer_fixed) == []
    both_changed = {
        "units": [
            {"slot": f"type:{OPTIONS}", "text": "Something else."},
            {"slot": f"type:{RENDERER}", "text": "A placeholder; render is not implemented."},
        ]
    }
    errors = guarded(both_changed)
    assert len(errors) == 1 and OPTIONS in errors[0]

    by_quotes = keep_unflagged_units(lambda revised: [], original, [OPTIONS_TEXT, RENDERER_TEXT])
    assert by_quotes(both_changed) == []


def test_a_split_defect_keeps_one_ledger_entry_naming_each_task(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcomes = {HUBS.label: "unrepairable", TYPES.label: "repaired"}
    seen: list[tuple[str, list[str]]] = []

    def fake_repair(rc: Any, defect: Defect, task: SectionTask, repairs: Any, named: Any) -> bool:
        seen.append((task.label, _quotes(defect)))
        repairs.record(
            defect,
            outcomes[task.label],
            changes=[{"slot": task.label}] if outcomes[task.label] == "repaired" else (),
        )
        return outcomes[task.label] == "repaired"

    monkeypatch.setattr(loop_module, "_repair_task", fake_repair)
    rc = SimpleNamespace(
        tasks=[HUBS, TYPES],
        store=_Store(STORED),
        facts=FACTS,
        prompts={"section_authoring": None},
    )
    repairs = RepairLedger(tmp_path / "repairs.json")
    defect = _merged(HUB_TEXT, RENDERER_TEXT)

    assert loop_module._repair_section(rc, defect, repairs) is True
    assert seen == [(HUBS.label, [HUB_TEXT]), (TYPES.label, [RENDERER_TEXT])]
    entry = repairs.attempts["fp"]
    assert entry["outcome"] == "repaired"
    assert entry["tasks"] == [HUBS.label, TYPES.label]
    assert entry["changes"] == [{"slot": TYPES.label}]
    assert "api_reference: unrepairable" in entry["reason"]
    assert "api_reference#types-1: repaired" in entry["reason"]
