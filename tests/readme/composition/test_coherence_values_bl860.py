"""BL-860: the S8 coherence pass re-introduced a version into an opening authoring had accepted
value-free, and had no ``recover`` for R43(2)'s no-values rule. Hosted BarCode Python Lane R refresh
runs 45002500775 and 45004811070 each spent 16 provider calls and failed on ``unit opening: spells
'3.12', '10.1.0'``: the model read ``Python >=3.12`` / ``Pillow>=10.1.0`` from the rendered
Installation section into a closing sentence of the opening and repeated it after the re-ask. The
text below is the model's own reply (hosted log, rejected unit), transposed onto the synthetic
product. Nothing calls a provider; replayed requests are byte-identical (only ``recover`` changed).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.errors import OutputRejectedError
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.readme.composition.authoring import product_name, value_tokens
from repo_presenter.readme.composition.coherence import (
    coherence_batches,
    coherence_checks,
    coherence_packet,
    coherence_schema,
    recover_coherence_regressions,
    recover_coherence_value_units,
)
from repo_presenter.readme.composition.authoring import authoring_tasks
from repo_presenter.readme.composition.planning import plan_checks
from tests.readme.composition.synthetic import make_entry
from tests.readme.composition.test_pipeline import _dispositions, _plan
from tests.readme.composition.test_value_names_bl170 import (
    CONFIG, NAME, SECTION_AUTHORING, _budget, _completion, _facts,
)

BEFORE = (
    "Aspose.Widget FOSS for Python generates barcodes in Code 128, Code 39, EAN-13, EAN-8, "
    "UPC-A, UPC-E, and QR formats. It renders barcodes to SVG strings and PNG image bytes."
)
VALUE_SENTENCE = (
    " It requires Python >=3.12 and depends on Pillow>=10.1.0."
)
NEW_CONTENT = " It accepts render options to control output scale, DPI, module width, and text visibility."


def _setup() -> tuple[Any, Any, list[Any], dict[str, Any]]:
    facts = _facts()
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=_dispositions()) == []
    tasks = authoring_tasks(make_entry(), facts, {}, _dispositions(), plan)
    task = next(t for t in tasks if t.section_id == "opening")
    existing = [{"section": "opening", "slot": "opening", "text": BEFORE, "fact_ids": ["package:name"]}]
    return facts, task, tasks, {"existing": existing}


def _output(text: str) -> dict[str, Any]:
    return {"units": [{"section": "opening", "slot": "opening", "text": text,
                       "fact_ids": ["package:name"]}], "omitted": []}


def test_the_real_opening_spells_the_two_values() -> None:
    facts, task, tasks, _ = _setup()
    assert value_tokens(BEFORE + NEW_CONTENT + VALUE_SENTENCE, NAME, facts) == ["3.12", "10.1.0"]
    assert value_tokens(BEFORE + NEW_CONTENT, NAME, facts) == []


def test_only_the_value_sentence_goes_and_new_genuine_content_stays() -> None:
    facts, task, tasks, ctx = _setup()
    out = _output(BEFORE + NEW_CONTENT + VALUE_SENTENCE)
    fixed = recover_coherence_value_units(
        out, existing_units=ctx["existing"], tasks=[task], facts=facts, name=NAME
    )
    assert fixed is not None
    assert fixed["units"][0]["text"] == BEFORE + NEW_CONTENT
    note = fixed["_recovery_notes"][0]
    assert note["rule"] == "BL-860" and note["fallback"] == "coherence_value_sentence_removed"
    assert note["rejected_text"].endswith("Pillow>=10.1.0.")
    # Composed recover (what cascade passes) reaches it too.
    again = recover_coherence_regressions(
        _output(BEFORE + NEW_CONTENT + VALUE_SENTENCE),
        existing_units=ctx["existing"], facts=facts, tasks=[task], name=NAME,
    )
    assert again is not None and again["units"][0]["text"] == BEFORE + NEW_CONTENT


def test_a_unit_with_no_value_is_untouched() -> None:
    facts, task, tasks, ctx = _setup()
    revised = BEFORE + NEW_CONTENT
    out = _output(revised)
    snapshot = copy.deepcopy(out)
    assert recover_coherence_value_units(
        out, existing_units=ctx["existing"], tasks=[task], facts=facts, name=NAME
    ) is None
    assert out == snapshot


def test_a_single_sentence_that_is_all_value_reverts_to_the_pre_coherence_unit() -> None:
    facts, task, tasks, ctx = _setup()
    out = _output("It requires Python >=3.12 and Pillow>=10.1.0.")
    fixed = recover_coherence_value_units(
        out, existing_units=ctx["existing"], tasks=[task], facts=facts, name=NAME
    )
    assert fixed is not None
    assert fixed["units"][0]["text"] == BEFORE
    assert fixed["_recovery_notes"][0]["fallback"] == "coherence_value_unit_reverted"


def test_fails_closed_when_the_pre_coherence_unit_spells_a_value_too() -> None:
    facts, task, tasks, ctx = _setup()
    existing = [{**ctx["existing"][0], "text": "It needs Python >=3.12."}]
    out = _output("It requires Python >=3.12 and Pillow>=10.1.0.")
    assert recover_coherence_value_units(
        out, existing_units=existing, tasks=[task], facts=facts, name=NAME
    ) is None


def test_other_sections_are_never_touched() -> None:
    facts, task, tasks, ctx = _setup()
    other = next(t for t in tasks if t.section_id == "quick_start")
    out = {"units": [{"section": "quick_start", "slot": other.slots[0],
                      "text": "Run it with Python >=3.12. It prints 12 widgets.", "fact_ids": []}],
           "omitted": []}
    assert recover_coherence_value_units(
        out, existing_units=[], tasks=[other], facts=facts, name=NAME
    ) is None


def _run_coherence_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, recovery: bool) -> Any:
    tmp_path.mkdir(parents=True, exist_ok=True)
    facts, task, tasks, ctx = _setup()
    existing = ctx["existing"]
    reply = _output(BEFORE + NEW_CONTENT + VALUE_SENTENCE)
    replies = [_completion(reply) for _ in range(3)]
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_p: replies.pop(0)))
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    name = product_name(make_entry())

    def checks(output: dict[str, Any]) -> list[str]:
        return coherence_checks(
            output, [task], facts, name, existing_units=existing, prior_omitted=[],
            dispositions=_dispositions(),
        )

    def recover(output: dict[str, Any]) -> dict[str, Any] | None:
        if not recovery:
            return None
        return recover_coherence_regressions(
            output, existing_units=existing, facts=facts, tasks=[task], name=name,
            dispositions=_dispositions(),
        )

    return run_job(
        SECTION_AUTHORING,
        coherence_packet(make_entry(), "# README\n", {"units": existing}, [task], facts),
        config=CONFIG, facts=facts, ledger=Ledger(tmp_path / "ledger.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=coherence_schema(SECTION_AUTHORING, existing, [task]),
        checks=checks, recover=recover, budget_path=_budget(tmp_path),
    )


def test_the_whole_coherence_job_fails_before_and_completes_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(OutputRejectedError, match="spells '3.12', '10.1.0'"):
        _run_coherence_job(tmp_path / "before", monkeypatch, recovery=False)
    result = _run_coherence_job(tmp_path / "after", monkeypatch, recovery=True)
    assert result.output["units"][0]["text"] == BEFORE + NEW_CONTENT
    repaired = list((tmp_path / "after" / "calls").glob("*.repaired-*.json"))
    assert repaired
    assert "BL-860" in repaired[0].read_text(encoding="utf-8")
