"""R43(4) / BL-104: a type:/hub: unit that still fails its checks after every ask falls back to the
renderer's fact-true row instead of failing section_authoring.

The rejected shapes are the real ones that failed hosted Lane R runs: enum members the facts do not
list (PDF Java ``Permissions``: "AssembleDocument, ExtractContentWithDisabilities, FillForm,
ModifyTextAnnotations (nearest accepted: ModifyAnnotations), PrintingQuality"; Words .NET
``RevisionType``: "FormatChange, StyleDefinitionChange"), HTML in a summary (HTML Python
``HTMLAnchorElement``: "<a>") and unknown identifiers (Cells C++ ``Workbook`` hub: "uint8_t").
The job runs through the real ``run_job`` with the real section_authoring manifest and scripted
replies; nothing calls a provider.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import OutputRejectedError
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.authoring import (
    API_ROW_FALLBACK_REASON,
    authoring_schema,
    authoring_tasks,
    merge_units,
    product_name,
    unit_checks,
)
from repo_presenter.readme.composition.authoring_retry import (
    authoring_narrowing,
    recover_authoring_output,
    recover_failing_api_rows,
)
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import render_readme
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

REPO_ROOT = Path(__file__).resolve().parents[3]
SECTION_AUTHORING = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
ENUM = "public_symbol:aspose_widget_foss.permissions"
ANCHOR = "public_symbol:aspose_widget_foss.htmlanchorelement"
HUB = "public_symbol:aspose_widget_foss.widget"


def _facts() -> FactsDocument:
    base = make_facts()
    extra = (
        Fact(
            ENUM,
            "public_symbol",
            "aspose_widget_foss.Permissions",
            (Evidence("aspose_widget_foss/permissions.py", "line 3; enum; "),),
            attributes={"symbol_kind": "enum"},
        ),
        *(
            Fact(
                f"enum_member:aspose_widget_foss.permissions.{name.lower()}",
                "enum_member",
                f"aspose_widget_foss.Permissions.{name}",
                (Evidence("aspose_widget_foss/permissions.py"),),
                attributes={"enum": "aspose_widget_foss.Permissions"},
            )
            for name in ("ModifyAnnotations", "PrintDocument")
        ),
        Fact(
            ANCHOR,
            "public_symbol",
            "aspose_widget_foss.HTMLAnchorElement",
            (Evidence("aspose_widget_foss/dom.py", "line 9; class; "),),
            attributes={"symbol_kind": "class", "signature": "class HTMLAnchorElement(HTMLElement)"},
        ),
    )
    return replace(base, facts=(*base.facts, *extra))


def _checked_plan(facts: FactsDocument) -> dict[str, Any]:
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=_dispositions()) == []
    return plan


def _tasks(facts: FactsDocument) -> list[Any]:
    return authoring_tasks(make_entry(), facts, {}, _dispositions(), _checked_plan(facts))


def _task(facts: FactsDocument, slot: str) -> Any:
    return next(task for task in _tasks(facts) if slot in task.slots)


def _checks(task: Any, facts: FactsDocument):
    name = product_name(make_entry())

    def checks(output: dict[str, Any]) -> list[str]:
        return unit_checks(output, task, facts, name, dispositions=_dispositions())

    return checks


#: The real rejected texts, transposed onto the synthetic types.
ENUM_TEXT = (
    "Permissions lists document permissions such as AssembleDocument, FillForm and "
    "PrintingQuality."
)
ANCHOR_TEXT = "HTMLAnchorElement represents the <a> element that creates hyperlinks."
HUB_TEXT = "Widget loads a workbook from a std::vector<std::uint8_t> buffer as uint8_t bytes."


def _type_reply(task: Any) -> dict[str, Any]:
    texts = {f"type:{ENUM}": ENUM_TEXT, f"type:{ANCHOR}": ANCHOR_TEXT}
    return {
        "units": [
            {
                "section": "api_reference",
                "slot": slot,
                "text": texts[slot],
                "fact_ids": [slot.split(":", 1)[1]],
            }
            for slot in task.slots
        ],
        "omitted": [],
    }


def test_the_real_rejected_type_shapes_fail_unit_checks() -> None:
    facts = _facts()
    task = _task(facts, f"type:{ENUM}")
    errors = _checks(task, facts)(_type_reply(task))
    assert any(e.startswith(f"unit type:{ENUM}: identifiers that are not accepted") for e in errors)
    assert any(e.startswith(f"unit type:{ANCHOR}: text contains HTML") for e in errors)


def test_failing_type_rows_are_blanked_and_the_result_passes_the_real_checks() -> None:
    facts = _facts()
    task = _task(facts, f"type:{ENUM}")
    checks = _checks(task, facts)
    recovered = recover_failing_api_rows(_type_reply(task), task=task, facts=facts, checks=checks)
    assert recovered is not None
    # Both rows failed: the class row is left out, the enum row keeps the one unit the output
    # contract requires, as the fact-true sentence the renderer would print.
    assert [unit["text"] for unit in recovered["units"]] == [
        "Enumerates ModifyAnnotations and PrintDocument."
    ]
    assert [item["fact_id"] for item in recovered["omitted"]] == [ANCHOR]
    assert all(item["reason"] == API_ROW_FALLBACK_REASON for item in recovered["omitted"])
    notes = recovered.pop("_recovery_notes")
    assert {note["slot"] for note in notes} == {f"type:{ENUM}", f"type:{ANCHOR}"}
    assert all(note["ruling"] == "R43(4)" and note["rejection"] for note in notes)
    assert checks(copy.deepcopy(recovered)) == []


def test_a_passing_row_is_kept_and_only_the_failing_one_falls_back() -> None:
    facts = _facts()
    task = _task(facts, f"type:{ENUM}")
    reply = _type_reply(task)
    for unit in reply["units"]:
        if unit["slot"] == f"type:{ANCHOR}":
            unit["text"] = "Represents a hyperlink element of the document."
    recovered = recover_failing_api_rows(reply, task=task, facts=facts, checks=_checks(task, facts))
    assert recovered is not None
    assert [unit["slot"] for unit in recovered["units"]] == [f"type:{ANCHOR}"]
    assert [item["fact_id"] for item in recovered["omitted"]] == [ENUM]


def test_no_fallback_while_a_non_api_defect_remains() -> None:
    """A hub unit failing beside a prose slot (the API Reference intro) is not a fallback case: the
    job fails as before, so a fallback never hides another defect."""
    facts = _facts()
    task = _task(facts, f"hub:{HUB}")
    reply = {
        "units": [
            {"section": "api_reference", "slot": "intro", "text": "See uint8_t.", "fact_ids": []},
            {"section": "api_reference", "slot": f"hub:{HUB}", "text": HUB_TEXT, "fact_ids": [HUB]},
        ],
        "omitted": [],
    }
    assert recover_failing_api_rows(reply, task=task, facts=facts, checks=_checks(task, facts)) is None


def test_a_failing_hub_unit_falls_back_and_renders_the_fact_true_description() -> None:
    facts = _facts()
    task = _task(facts, f"hub:{HUB}")
    reply = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": "One entry-point class does the work.",
                "fact_ids": [],
            },
            {"section": "api_reference", "slot": f"hub:{HUB}", "text": HUB_TEXT, "fact_ids": [HUB]},
        ],
        "omitted": [],
    }
    checks = _checks(task, facts)
    assert any(e.startswith(f"unit hub:{HUB}: ") for e in checks(copy.deepcopy(reply)))
    recovered = recover_authoring_output(reply, task=task, facts=facts, checks=checks)
    assert recovered is not None
    recovered.pop("_recovery_notes")
    assert checks(copy.deepcopy(recovered)) == []
    units = _units()
    units["units"] = [u for u in units["units"] if u["slot"] != f"hub:{HUB}"]
    readme = render_readme(make_entry(), facts, _checked_plan(facts), units, _dispositions())
    after_heading = readme.split("### Widget", 1)[1].lstrip("\n").split("\n", 1)[0]
    # The Widget hub prints its docstring, the same fact-true text as its Core API row.
    assert after_heading == "A widget you can render."


def test_the_fallback_rows_render_from_facts() -> None:
    facts = _facts()
    units = _units()
    readme = render_readme(make_entry(), facts, _checked_plan(facts), units, _dispositions())
    assert "| `Permissions` | Enumerates ModifyAnnotations and PrintDocument. |" in readme
    assert "| `HTMLAnchorElement` | Defined as `class HTMLAnchorElement(HTMLElement)`. |" in readme


# --- the whole job, through run_job ------------------------------------------------------------


CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")


def _completion(content: Any) -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model="qwen3-next", id="req-1", usage=usage)


def _budget(tmp_path: Path) -> Path:
    path = tmp_path / "budget.json"
    path.write_text(
        json.dumps(
            {
                "total_calls_cap": 100,
                "total_tokens_cap": 100000,
                "spent": {"calls": 0, "tokens": 0},
                "batches": [
                    {
                        "id": "t",
                        "repositories": [],
                        "calls_cap": 100,
                        "tokens_cap": 100000,
                        "calls_spent": 0,
                        "tokens_spent": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, task: Any, facts: FactsDocument, *, with_checks: bool):
    replies = [_completion(_type_reply(task)) for _ in range(3)]
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_payload: replies.pop(0)))
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    checks = _checks(task, facts)

    def recover(output: dict[str, Any]) -> dict[str, Any] | None:
        return recover_authoring_output(
            output, task=task, facts=facts, checks=checks if with_checks else None
        )

    return run_job(
        SECTION_AUTHORING,
        task.packet,
        config=CONFIG,
        facts=facts,
        ledger=Ledger(tmp_path / "ledger.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=bound_authoring_citations(
            authoring_schema(SECTION_AUTHORING, task),
            task,
            SECTION_AUTHORING.manifest.sampling.max_output_tokens,
        ),
        checks=checks,
        recover=recover,
        narrow=authoring_narrowing(task, SECTION_AUTHORING),
        budget_path=_budget(tmp_path),
    )


def test_without_the_fallback_the_job_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts()
    task = _task(facts, f"type:{ENUM}")
    with pytest.raises(OutputRejectedError):
        _run(tmp_path, monkeypatch, task, facts, with_checks=False)


def test_the_job_accepts_the_fallback_records_it_and_replays_it_from_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = _facts()
    task = _task(facts, f"type:{ENUM}")
    result = _run(tmp_path, monkeypatch, task, facts, with_checks=True)
    # Every row of the batch failed; the contract holds at least one unit, so the enum's row
    # carries the fact-true sentence itself and the class row is left to the renderer.
    assert result.output["units"] == [
        {
            "section": "api_reference",
            "slot": f"type:{ENUM}",
            "text": "Enumerates ModifyAnnotations and PrintDocument.",
            "fact_ids": [ENUM],
        }
    ]
    assert [item["fact_id"] for item in result.output["omitted"]] == [ANCHOR]
    assert "_recovery_notes" not in result.output
    records = [json.loads(p.read_text()) for p in (tmp_path / "calls").glob("*.repaired-*.json")]
    assert len(records) == 1
    assert {note["symbol_fact_id"] for note in records[0]["notes"]} == {ENUM, ANCHOR}
    # The stored output re-validates through the manifest schema and the checks: a later run
    # reuses it with zero calls.
    replay = _run(tmp_path, monkeypatch, task, facts, with_checks=True)
    assert replay.cache_reused is True
    merged = merge_units({task.label: replay.output})
    assert {item["section"] for item in merged["omitted"]} == {"api_reference"}
    readme = render_readme(make_entry(), facts, _checked_plan(facts), _units(), _dispositions())
    assert "| `Permissions` | Enumerates ModifyAnnotations and PrintDocument. |" in readme
