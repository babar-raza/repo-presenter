"""An S4 defect naming no inherited unit, whose quote an authored section prints, is repaired there.

Regression for aspose-email-foss/Aspose.Email-FOSS-for-.Net, hosted Lane R run 43405254498: BC-18's
earliest causal stage was RECONCILING (two register quotes were printed by inherited units), so its
unit-less failures -- quotes in generated text -- became one S4 defect naming no unit, and
``_repair_reconciliation`` recorded it "unrepairable: no stored disposition of an inherited unit is
named by this defect; a whole-batch revision would regenerate unrelated units". The authoring task
whose stored units print the quote is the one a repair may revise (the S6 path).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.repair import loop as loop_module
from repo_presenter.readme.repair.targeted import Defect, RepairLedger, validation_defects

QUOTE = "provides formula calculation for SUM, AVERAGE, MAX, and MIN"
AUTHORED = (
    "Aspose.Cells FOSS for Go reads and writes .xlsx workbooks and\n"
    "provides formula calculation for SUM, AVERAGE, MAX, and MIN."
)
OVERVIEW = SectionTask("overview", {}, frozenset(), ("intro",))
FEATURES = SectionTask("key_capabilities", {}, frozenset(), ("intro",))
STORED = {
    OVERVIEW.label: {"units": [{"slot": "intro", "text": AUTHORED}]},
    FEATURES.label: {"units": [{"slot": "intro", "text": "Reads and writes cells."}]},
}


class _Store:
    def get(self, key: str) -> dict[str, Any] | None:
        return STORED.get(key)


def _bc18_defect() -> Defect:
    """The unit-less S4 defect ``validation_defects`` builds from a BC-18 check whose earliest
    stage is RECONCILING: one failure printed by a unit, one in an authored section."""
    validation = {
        "validator_version": "v",
        "checks": [
            {
                "id": "BC-18",
                "name": "must-correct",
                "verdict": "FAIL",
                "causal_stage": "RECONCILING",
                "details": ["a", "b"],
                "failures": [
                    {
                        "section_id": None,
                        "causal_stage": "RECONCILING",
                        "detail": "a",
                        "unit_id": "inherited_unit:015.code_block",
                        "quote": "Version=\"9.9.9\"",
                        "instruction": "fix the version",
                    },
                    {
                        "section_id": "overview",
                        "causal_stage": "COMPOSING",
                        "detail": "b",
                        "quote": QUOTE,
                        "instruction": "the engine supports about 19 functions",
                    },
                ],
            }
        ],
    }
    defects = validation_defects(validation, {"overview", "key_capabilities"})
    (unitless,) = [d for d in defects if not any(f.get("unit_id") for f in d.record["failures"])]
    assert unitless.stage == "S4" and unitless.record["quote"] == QUOTE
    return unitless


@pytest.fixture()
def rc(monkeypatch: pytest.MonkeyPatch) -> Any:
    # No inherited unit prints the quote: there is no batch to patch and no placement to name.
    monkeypatch.setattr(loop_module, "reconciliation_batches", lambda facts, tokens: {})
    monkeypatch.setattr(loop_module, "placements", lambda *args, **kwargs: [])
    monkeypatch.setattr(loop_module, "patch_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(loop_module, "_task_key", lambda rc, loaded, task: task.label)
    manifest = SimpleNamespace(sampling=SimpleNamespace(max_output_tokens=1000))
    prompts = {
        "source_reconciliation": SimpleNamespace(manifest=manifest),
        "targeted_repair": SimpleNamespace(manifest=manifest),
        "section_authoring": None,
    }
    return SimpleNamespace(
        tasks=[FEATURES, OVERVIEW],
        store=_Store(),
        facts=None,
        plan={},
        dispositions={},
        investigation={},
        entry=SimpleNamespace(ecosystem="go"),
        prompts=prompts,
    )


def test_an_authored_quote_routes_to_the_task_that_prints_it(
    rc: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, str | None, str | None, str]] = []

    def fake_repair(rc: Any, defect: Defect, task: SectionTask, repairs: Any, named: Any) -> bool:
        seen.append((task.label, defect.stage, defect.section_id, defect.record["quote"]))
        repairs.record(defect, "repaired", changes=[{"slot": "intro"}])
        return True

    monkeypatch.setattr(loop_module, "_repair_task", fake_repair)
    repairs = RepairLedger(tmp_path / "repairs.json")
    defect = _bc18_defect()

    assert loop_module.repair_defect(rc, defect, repairs) is True
    # The wrapped line in the stored unit still holds the quote once whitespace is squashed.
    assert seen == [(OVERVIEW.label, "S6", "overview", QUOTE)]
    assert repairs.attempts[defect.fingerprint]["outcome"] == "repaired"


def test_a_quote_no_task_prints_stays_unrepairable(rc: Any, tmp_path: Any) -> None:
    repairs = RepairLedger(tmp_path / "repairs.json")
    defect = _bc18_defect()
    defect = Defect(
        defect.fingerprint,
        defect.source,
        defect.label,
        defect.section_id,
        defect.stage,
        {**defect.record, "quote": "text only the renderer prints"},
    )
    assert loop_module.repair_defect(rc, defect, repairs) is False
    entry = repairs.attempts[defect.fingerprint]
    assert entry["outcome"] == "unrepairable"
    assert "no stored disposition" in entry["reason"]
