"""BL-170: R43(2)'s no-values rule failed five hosted Lane R runs as job errors
(``OutputRejectedError: section_authoring ... spells ...``) - three of them on a number that is part
of a proper name, the other on a stray value in a multi-sentence opening:

* aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python, run 43674580663: ``unit opening: spells
  '128', '39'`` - the symbologies Code 128 and Code 39, the product's whole subject;
* aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET, run 43683719616: ``unit capability:5: spells '1', '7'``
  - the signature standards PKCS#1 and PKCS#7; PDF C++ (43664910650, ``capability:4``) and PDF
  Java (43664908666, ``capability:6``) ``spells '7'`` - PKCS#7;
* aspose-words-foss/Aspose.Words-FOSS-for-Java, run 43672441969: ``unit opening: spells '8',
  '2003'`` - a runtime version and a year, true values.

The rejected units' text was not recoverable (the run artifacts' storage host is not reachable
from here), so each test carries the exact tokens the record names in the sentence the facts
themselves spell them in (the BarCode and PDF inherited units at the failing revision; Words Java's
inherited units 010 and 070). Nothing calls a provider.
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
    authoring_schema,
    authoring_tasks,
    product_name,
    unit_checks,
    value_tokens,
)
from repo_presenter.readme.composition.authoring_retry import (
    authoring_narrowing,
    recover_authoring_output,
    recover_opening_output,
    recover_value_sentences,
)
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from repo_presenter.readme.composition.planning import plan_checks
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan

REPO_ROOT = Path(__file__).resolve().parents[3]
SECTION_AUTHORING = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
NAME = "Aspose.Widget FOSS for Python"

#: The maintainers' own sentences at the failing revisions, transposed onto the synthetic product.
INHERITED = {
    # BarCode Python 004.paragraph / 010.list (06eca5c0)
    "inherited_unit:004.paragraph": (
        "Aspose.Widget FOSS for Python is a pure-Python library for generating barcodes. It encodes "
        "linear and 2D symbologies \N{EM DASH}\nCode 128, Code 39 and QR Code."
    ),
    # PDF Java 010.list (736cedaa), PDF .NET 225.list (10a36383)
    "inherited_unit:010.list": (
        "- Sign documents with PKCS#7 (RSA, DSA, or ECDSA) via `PdfSigner`.\n"
        "- Signing (PKCS#1, PKCS#7, DocMDP certifying) needs a certificate."
    ),
    # Words Java 010.paragraph / 070.paragraph / 071.paragraph (1a062dd8)
    "inherited_unit:011.paragraph": (
        "The library is pure Java with no native code. It runs on Java 8 and later."
    ),
    "inherited_unit:012.paragraph": (
        "A document engine that has processed Word documents in production since 2003. Then came "
        "WordML, the Word 2003 XML dialect."
    ),
    # Imaging .NET / Cells Java capability shapes: counts the facts spell at a sentence start.
    "inherited_unit:013.list": (
        "- Detects 14 image formats from signature bytes.\n- Create 18 of the 25 chart types."
    ),
}

BARCODE_OPENING = (
    "Aspose.Widget FOSS for Python encodes Code 128, Code 39 and QR Code barcodes and renders "
    "them to SVG and PNG."
)
PKCS_CAPABILITY = "It signs documents with PKCS#1 and PKCS#7 detached signatures."
WORDS_OPENING = (
    "Aspose.Widget FOSS for Python reads and writes widget documents. It runs on Java 8 and "
    "later and has processed documents since 2003. It renders widgets."
)


def _facts() -> FactsDocument:
    base = make_facts()
    extra = tuple(
        Fact(fact_id, "inherited_unit", text, (Evidence("README.md", "line 1"),))
        for fact_id, text in INHERITED.items()
    ) + (
        Fact(
            "dependency:runtime.jvm", "dependency", "Jvm 17",
            (Evidence("pom.xml", "line 3"),),
        ),
    )
    return replace(base, facts=(*base.facts, *extra))


def _task(facts: FactsDocument, section: str) -> Any:
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=_dispositions()) == []
    tasks = authoring_tasks(make_entry(), facts, {}, _dispositions(), plan)
    return next(task for task in tasks if task.section_id == section)


def _value_errors(output: dict[str, Any], task: Any, facts: FactsDocument) -> list[str]:
    errors = unit_checks(copy.deepcopy(output), task, facts, NAME, dispositions=_dispositions())
    return [error for error in errors if " spells " in error]


# --- the narrower rule: a number that ends a name the facts spell is part of the name ----------


def test_the_three_real_named_numbers_are_names_not_values() -> None:
    facts = _facts()
    # Without the facts the rule reads exactly as before (origin/main): every token the hosted
    # records name is still found ...
    assert value_tokens(BARCODE_OPENING, NAME) == ["128", "39"]
    assert value_tokens(PKCS_CAPABILITY, NAME) == ["1", "7"]
    assert value_tokens("Sign documents with PKCS#7 signatures.", NAME) == ["7"]
    # ... and with them, the names the facts spell are not values.
    assert value_tokens(BARCODE_OPENING, NAME, facts) == []
    assert value_tokens(PKCS_CAPABILITY, NAME, facts) == []
    assert value_tokens("Sign documents with PKCS#7 signatures.", NAME, facts) == []
    assert value_tokens("It reads the Word 2003 XML dialect.", NAME, facts) == []


def test_versions_dates_counts_and_names_the_facts_do_not_spell_stay_values() -> None:
    facts = _facts()
    # A runtime version stays a value even though the facts spell "Java 8" (Words Java, '8').
    assert value_tokens("It runs on Java 8 and later.", NAME, facts) == ["8"]
    # A year with no name before it (Words Java, '2003').
    assert value_tokens("It has run in production since 2003.", NAME, facts) == ["2003"]
    # A dotted version is never a name.
    assert value_tokens("It reads PDF 1.7 files.", NAME, facts) == ["1.7"]
    # A count the facts spell only at a sentence or list-item start ("Detects 14", "Create 18").
    assert value_tokens("It detects 14 image formats.", NAME, facts) == ["14"]
    assert value_tokens("Detects 14 image formats from bytes.", NAME, facts) == ["14"]
    assert value_tokens("Create 18 of the 25 chart types.", NAME, facts) == ["18", "25"]
    # A name the facts never spell, and a dependency's own name.
    assert value_tokens("It encodes Code 93 barcodes.", NAME, facts) == ["93"]
    assert value_tokens("It needs Jvm 17.", NAME, facts) == ["17"]


@pytest.mark.parametrize(
    ("section", "slot", "text"),
    [
        ("opening", "opening", BARCODE_OPENING),
        ("key_capabilities", "capability:1", PKCS_CAPABILITY),
    ],
)
def test_unit_checks_accept_the_real_named_numbers(section: str, slot: str, text: str) -> None:
    facts = _facts()
    task = _task(facts, section)
    units = [
        {"section": section, "slot": s, "text": text if s == slot else "It renders widgets.",
         "fact_ids": ["package:name"]}
        for s in task.slots
    ]
    output = {"units": units, "omitted": []}
    assert _value_errors(output, task, facts) == []
    bad = copy.deepcopy(output)
    bad["units"][0]["text"] = "It renders 12 widget kinds."
    assert _value_errors(bad, task, facts)


# --- the deterministic deletion: a stray value no longer costs the run ------------------------


def test_the_words_java_opening_loses_only_the_sentence_that_spells_the_values() -> None:
    facts = _facts()
    task = _task(facts, "opening")
    output = {
        "units": [
            {"section": "opening", "slot": "opening", "text": WORDS_OPENING,
             "fact_ids": ["package:name"]}
        ],
        "omitted": [],
    }
    assert any("spells '8', '2003'" in e for e in _value_errors(output, task, facts))
    recovered = recover_opening_output(
        output, task=task, facts=facts, dispositions=_dispositions(), name=NAME
    )
    assert recovered is not None
    assert recovered["units"][0]["text"] == (
        "Aspose.Widget FOSS for Python reads and writes widget documents. It renders widgets."
    )
    assert _value_errors(recovered, task, facts) == []


def test_a_value_in_a_parenthesis_goes_with_the_parenthesis() -> None:
    facts = _facts()
    task = _task(facts, "key_capabilities")
    output = {
        "units": [
            {"section": "key_capabilities", "slot": s, "fact_ids": ["package:name"],
             "text": "It renders widgets (12 kinds) to images." if s == "capability:1"
             else "It renders widgets."}
            for s in task.slots
        ],
        "omitted": [],
    }
    recovered = recover_authoring_output(output, task=task, facts=facts, name=NAME)
    assert recovered is not None
    assert recovered["units"][0]["text"] == "It renders widgets to images."
    assert _value_errors(recovered, task, facts) == []


def test_a_unit_that_is_nothing_but_the_value_is_left_to_fail_closed() -> None:
    facts = _facts()
    task = _task(facts, "key_capabilities")
    output = {
        "units": [
            {"section": "key_capabilities", "slot": s, "fact_ids": ["package:name"],
             "text": "It renders 12 widget kinds." if s == "capability:1" else "It renders widgets."}
            for s in task.slots
        ],
        "omitted": [],
    }
    assert recover_value_sentences(output, task=task, facts=facts, name=NAME) is None
    # And other sections are never touched.
    quick = _task(facts, "quick_start")
    assert recover_value_sentences(
        {"units": [{"slot": "lead_in", "text": "It renders 12 widgets. It is fast."}]},
        task=quick, facts=facts, name=NAME,
    ) is None


# --- the whole job, through run_job: the run that died now completes --------------------------


CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")


def _completion(content: Any) -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model="qwen3-next", id="req-1", usage=usage)


def _budget(tmp_path: Path) -> Path:
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({
        "total_calls_cap": 100, "total_tokens_cap": 100000, "spent": {"calls": 0, "tokens": 0},
        "batches": [{"id": "t", "repositories": [], "calls_cap": 100, "tokens_cap": 100000,
                     "calls_spent": 0, "tokens_spent": 0}],
    }), encoding="utf-8")
    return path


def _run_opening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str, *, with_recovery: bool
) -> Any:
    tmp_path.mkdir(parents=True, exist_ok=True)
    facts = _facts()
    task = _task(facts, "opening")
    reply = {"units": [{"section": "opening", "slot": "opening", "text": text,
                        "fact_ids": ["package:name"]}], "omitted": []}
    replies = [_completion(reply) for _ in range(3)]
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_payload: replies.pop(0)))
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    name = product_name(make_entry())
    assert name == NAME

    def checks(output: dict[str, Any]) -> list[str]:
        return unit_checks(output, task, facts, name, dispositions=_dispositions())

    def recover(output: dict[str, Any]) -> dict[str, Any] | None:
        if not with_recovery:
            return None
        return recover_opening_output(
            output, task=task, facts=facts, dispositions=_dispositions(), name=name
        )

    return run_job(
        SECTION_AUTHORING, task.packet, config=CONFIG, facts=facts,
        ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=bound_authoring_citations(
            authoring_schema(SECTION_AUTHORING, task), task,
            SECTION_AUTHORING.manifest.sampling.max_output_tokens,
        ),
        checks=checks, recover=recover, narrow=authoring_narrowing(task, SECTION_AUTHORING),
        budget_path=_budget(tmp_path),
    )


def test_the_barcode_opening_is_accepted_on_the_first_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run_opening(tmp_path, monkeypatch, BARCODE_OPENING, with_recovery=False)
    assert result.output["units"][0]["text"] == BARCODE_OPENING


def test_the_words_java_opening_no_longer_fails_the_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(OutputRejectedError, match="spells '8', '2003'"):
        _run_opening(tmp_path / "before", monkeypatch, WORDS_OPENING, with_recovery=False)
    result = _run_opening(tmp_path / "after", monkeypatch, WORDS_OPENING, with_recovery=True)
    assert result.output["units"][0]["text"] == (
        "Aspose.Widget FOSS for Python reads and writes widget documents. It renders widgets."
    )
    assert list((tmp_path / "after" / "calls").glob("*.repaired-*.json"))
