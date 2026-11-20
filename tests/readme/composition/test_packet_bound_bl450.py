"""BL-450 (R46 robust, universal): an authoring request that grows with the repository is bounded.

PDF TypeScript, hosted run 44673623844 (2026-11-20, main 3b07ba8): ``section_authoring: gateway
answered HTTP 400: ContextWindowExceededError ... your request has 258818 input tokens (8000 >
262144 - 258818)``. The cause is the packet: every inherited README unit a section may cite is sent
with its full text, and that repository's README is 554k characters. Nothing here calls a provider.

* a request that fits is byte-identical to what it was (negative control: no sealed cell changes);
* one that does not has only the text of facts the section merely sees shortened, with a marker and
  an R14 record; never a slot-bound fact, a must-carry unit, or an id;
* a batch of types is split instead of shortened;
* the gateway's refusal is a ``ContextWindowError`` carrying the measured size, and the authoring
  stage re-asks with a packet sized from it.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIStatusError

from repo_presenter import cascade
from repo_presenter.core.errors import JobError
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import (
    CallStore,
    ContextWindowError,
    JobContext,
    run_job,
)
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.readme.composition import authoring as authoring_module
from repo_presenter.readme.composition.authoring import (
    REQUEST_CHAR_CEILING,
    authoring_schema,
    authoring_tasks,
    bound_task,
    estimated_request_chars,
)
from repo_presenter.readme.composition.coherence import (
    _bounded_document,
    bound_coherence_packet,
    coherence_batches,
    coherence_packet,
)
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from repo_presenter.readme.composition.planning import plan_checks
from tests.readme.composition.synthetic import make_entry
from tests.readme.composition.test_pipeline import _dispositions, _plan
from tests.readme.composition.test_value_names_bl170 import (
    CONFIG,
    SECTION_AUTHORING,
    _budget,
    _facts,
)

BIG = 30_000  # one inherited README table: PDF Java 070.table is 37k, PDF TypeScript 526.table 47k


def _big_unit(number: int, size: int = BIG) -> Fact:
    rows = "\n".join(f"| `Class{number}_{i}` | Describes item {i} of table {number}. |" for i in range(size // 50))
    return Fact(
        f"inherited_unit:9{number:02d}.table", "inherited_unit", "| Class | Description |\n|---|---|\n" + rows,
        (Evidence("README.md", "line 1"),),
    )


def _world(units: int = 4, *, section: str = "api_reference") -> tuple[FactsDocument, dict[str, Any]]:
    base = _facts()
    extra = tuple(_big_unit(n) for n in range(units))
    facts = replace(base, facts=(*base.facts, *extra))
    dispositions = _dispositions()
    dispositions = {
        "dispositions": [
            *dispositions["dispositions"],
            *(
                {
                    "unit_id": unit.id, "disposition": "VERIFIED_PRESERVE",
                    "destination_section": section, "fact_ids": [], "rationale": "kept",
                }
                for unit in extra
            ),
        ]
    }
    return facts, dispositions


def _tasks(facts: FactsDocument, dispositions: dict[str, Any], **kwargs: Any) -> list[Any]:
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=dispositions) == []  # also fills plan["sections"]
    return authoring_tasks(make_entry(), facts, {}, dispositions, plan, **kwargs)


def _request_chars(task: Any) -> int:
    from repo_presenter.core.llm.jobs import render_messages, request_payload

    schema = bound_authoring_citations(
        authoring_schema(SECTION_AUTHORING, task), task,
        SECTION_AUTHORING.manifest.sampling.max_output_tokens,
    )
    payload = request_payload(
        SECTION_AUTHORING, render_messages(SECTION_AUTHORING, task.packet, schema), schema
    )
    return len(json.dumps(payload, ensure_ascii=False))


# --- a request that fits is untouched ----------------------------------------------------------


def test_a_request_that_fits_is_byte_identical_to_the_unbounded_one() -> None:
    facts, dispositions = _world()
    unbounded = _tasks(facts, dispositions, ceiling=10**9)
    default = _tasks(facts, dispositions)
    assert all(not task.bounded for task in unbounded)
    # four 30k units placed in api_reference: 120k characters, under the 360k ceiling
    assert [t.packet for t in default] == [t.packet for t in unbounded]
    assert all(bound_task(task) is task for task in unbounded)


def test_the_synthetic_small_product_is_unchanged() -> None:
    facts = _facts()
    assert [t.packet for t in _tasks(facts, _dispositions())] == [
        t.packet for t in _tasks(facts, _dispositions(), ceiling=10**9)
    ]


# --- a request that does not fit is bounded, and only what the section merely sees -------------


def test_an_oversize_placed_unit_is_shortened_with_a_marker_and_a_record() -> None:
    facts, dispositions = _world()
    full = next(t for t in _tasks(facts, dispositions, ceiling=10**9) if t.label == "api_reference")
    ceiling = 60_000
    assert estimated_request_chars(full) > ceiling
    task = next(t for t in _tasks(facts, dispositions, ceiling=ceiling) if t.label == "api_reference")
    assert estimated_request_chars(task) <= ceiling
    assert _request_chars(task) <= ceiling
    assert task.accepted_ids == full.accepted_ids  # the closed set it may cite is the same
    assert [f["id"] for f in task.packet["accepted_facts"]] == [f["id"] for f in full.packet["accepted_facts"]]
    shown = {f["id"]: f["value"] for f in task.packet["accepted_facts"]}
    unit = next(f for f in facts.facts if f.id == "inherited_unit:900.table")
    assert len(shown[unit.id]) < len(unit.value)
    assert shown[unit.id].startswith("| Class | Description |")
    assert "more characters are not shown]" in shown[unit.id]
    notes = [n for n in task.bounded if n["fact_id"] == unit.id]
    assert notes and notes[0]["rule"] == "BL-450" and notes[0]["characters"] == len(unit.value)
    assert not any(n.get("still_over") for n in task.bounded)


def test_a_fact_the_section_is_bound_to_is_never_shortened() -> None:
    facts, dispositions = _world()
    full = next(t for t in _tasks(facts, dispositions, ceiling=10**9) if t.label == "api_reference")
    owned = "inherited_unit:900.table"
    bound = replace(
        full, slot_facts={**full.slot_facts, "hub:owned": frozenset({owned})}
    )
    out = bound_task(bound, 60_000)
    kept = {f["id"]: f["value"] for f in out.packet["accepted_facts"]}
    original = {f["id"]: f["value"] for f in full.packet["accepted_facts"]}
    assert kept[owned] == original[owned]
    assert owned not in {n["fact_id"] for n in out.bounded}
    assert any(kept[i] != original[i] for i in original)  # the others were


def test_a_must_carry_unit_and_identity_facts_are_never_shortened() -> None:
    facts, dispositions = _world()
    full = next(t for t in _tasks(facts, dispositions, ceiling=10**9) if t.label == "api_reference")
    carried = "inherited_unit:901.table"
    marked = replace(full, must_carry=frozenset({carried}))
    out = bound_task(marked, 60_000)
    kept = {f["id"]: f["value"] for f in out.packet["accepted_facts"]}
    original = {f["id"]: f["value"] for f in full.packet["accepted_facts"]}
    assert kept[carried] == original[carried]
    for fact_id, value in original.items():
        if fact_id.startswith(("identity:", "package:")):
            assert kept[fact_id] == value


def test_a_request_that_cannot_fit_is_flagged_never_silent() -> None:
    facts, dispositions = _world()
    full = next(t for t in _tasks(facts, dispositions, ceiling=10**9) if t.label == "api_reference")
    out = bound_task(full, 1_000)
    assert out.bounded and out.bounded[0].get("still_over") is True
    assert all(n["cap"] == 250 for n in out.bounded)  # the shortest cap was tried


def test_bounding_is_deterministic() -> None:
    facts, dispositions = _world()
    a = _tasks(facts, dispositions, ceiling=60_000)
    b = _tasks(facts, dispositions, ceiling=60_000)
    assert [t.packet for t in a] == [t.packet for t in b]
    assert [t.bounded for t in a] == [t.bounded for t in b]


# --- a batch of types is split, never shortened ------------------------------------------------


def _typed(count: int) -> FactsDocument:
    base = _facts()
    types = tuple(
        Fact(
            f"public_symbol:widget.type{i:03d}", "public_symbol", f"Widget.Type{i:03d}",
            (Evidence("src/w.py", f"line {i}"),),
            attributes={"symbol_kind": "class"},
        )
        for i in range(count)
    )
    return replace(base, facts=(*base.facts, *types))


def test_a_batch_of_types_over_the_ceiling_is_split_with_every_type_kept() -> None:
    facts = _typed(30)
    whole = [t for t in _tasks(facts, _dispositions(), ceiling=10**9) if t.is_batch]
    split = [t for t in _tasks(facts, _dispositions(), ceiling=40_000) if t.is_batch]
    assert len(whole) == 1 and len(split) > 1
    assert [s for t in split for s in t.slots] == list(whole[0].slots)  # same types, same order
    assert [t.label for t in split] == [f"api_reference#types-{i}" for i in range(1, len(split) + 1)]
    assert all(not t.bounded for t in split)
    assert all(estimated_request_chars(t) <= 40_000 for t in split)


def test_a_batch_that_fits_keeps_its_key_and_packet() -> None:
    facts = _typed(30)
    a = [t for t in _tasks(facts, _dispositions()) if t.is_batch]
    b = [t for t in _tasks(facts, _dispositions(), ceiling=10**9) if t.is_batch]
    assert [t.packet for t in a] == [t.packet for t in b] and a[0].label == "api_reference#types-1"


# --- the coherence call carries the whole document and every fact: bounded the same way --------


def _coherence(document_size: int, units: int = 4) -> tuple[dict[str, Any], list[Any], FactsDocument]:
    facts, dispositions = _world(units)
    tasks = [t for t in _tasks(facts, dispositions, ceiling=10**9) if not t.is_batch]
    block = "```\n" + "\n".join(f"line {i}" for i in range(document_size // 10)) + "\n```"
    rendered = "# Title\n\nIntro paragraph.\n\n" + block + "\n\nClosing paragraph."
    packet = coherence_packet(make_entry(), rendered, {"units": []}, tasks, facts)
    return packet, tasks, facts


def test_a_coherence_packet_that_fits_is_returned_as_it_was() -> None:
    packet, tasks, _facts_doc = _coherence(2_000)
    out, notes = bound_coherence_packet(packet, tasks)
    assert out is packet and notes == ()


def test_an_oversize_coherence_packet_is_bounded_in_document_and_facts() -> None:
    packet, tasks, _facts_doc = _coherence(200_000)
    assert packet_chars_of(packet) > 200_000
    out, notes = bound_coherence_packet(packet, tasks, 100_000)
    assert packet_chars_of(out) <= 100_000
    assert [f["id"] for f in out["accepted_facts"]] == [f["id"] for f in packet["accepted_facts"]]
    assert out["slots"] == packet["slots"] and out["existing_units"] == packet["existing_units"]
    assert out["objective"] == packet["objective"] and out["do_not_claim"] == packet["do_not_claim"]
    document = out["rendered_document"]
    assert document.startswith("# Title\n\nIntro paragraph.") and document.endswith("Closing paragraph.")
    assert "more characters are not shown]" in document
    assert document.count("```") % 2 == 0  # the cut code block is closed
    kinds = {n["fallback"] for n in notes}
    assert kinds == {"packet_value_bounded", "packet_document_bounded"}
    assert all(n["rule"] == "BL-450" for n in notes)


def test_a_coherence_packet_that_cannot_fit_is_flagged() -> None:
    packet, tasks, _facts_doc = _coherence(200_000)
    _out, notes = bound_coherence_packet(packet, tasks, 1_000)
    assert notes[0].get("still_over") is True


def test_short_blocks_of_the_document_are_never_cut() -> None:
    document = "# A\n\nshort\n\n" + "x" * 5_000 + "\n\nend"
    cut, blocks = _bounded_document(document, 1_000)
    assert blocks == 1 and cut.startswith("# A\n\nshort\n\n") and cut.endswith("\n\nend")
    assert _bounded_document("# A\n\nshort", 1_000) == ("# A\n\nshort", 0)


def packet_chars_of(packet: dict[str, Any]) -> int:
    from repo_presenter.readme.composition.authoring import packet_chars, schema_chars
    from repo_presenter.readme.composition.coherence import coherence_citable_ids

    return packet_chars(packet)


# --- the gateway's refusal is recognised and measured ------------------------------------------

REFUSAL = (
    '{"error":{"message":"litellm.ContextWindowExceededError: Hosted_vllmException - {\\"error\\":'
    '{\\"message\\":\\"\'max_tokens\' or \'max_completion_tokens\' is too large: 8000. This model\'s '
    "maximum context length is 262144 tokens and your request has 258818 input tokens "
    '(8000 > 262144 - 258818).\\"}}"}}'
)


def _status_error(status: int, body: str) -> APIStatusError:
    request = httpx.Request("POST", "https://gw.example/v1/chat/completions")
    return APIStatusError(
        "refused", response=httpx.Response(status, text=body, request=request), body=None
    )


def _run_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, body: str) -> None:
    facts = _facts()
    task = next(t for t in _tasks(facts, _dispositions()) if t.label == "opening")

    def create(**_payload: Any) -> Any:
        raise _status_error(status, body)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    run_job(
        SECTION_AUTHORING, task.packet, config=CONFIG, facts=facts,
        ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task, 8000),
        budget_path=_budget(tmp_path),
    )


def test_the_context_window_refusal_carries_the_measured_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ContextWindowError) as caught:
        _run_refused(tmp_path, monkeypatch, 400, REFUSAL)
    error = caught.value
    assert isinstance(error, JobError)  # every caller that handles JobError still does
    assert (error.context_tokens, error.input_tokens) == (262144, 258818)
    assert error.request_chars > 1000
    assert "ContextWindowExceededError" in str(error)


@pytest.mark.parametrize(
    ("status", "body"),
    [(400, '{"error":{"message":"schema is invalid"}}'), (401, REFUSAL), (404, "not found")],
)
def test_any_other_refusal_is_the_plain_job_error_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, body: str
) -> None:
    with pytest.raises(JobError) as caught:
        _run_refused(tmp_path, monkeypatch, status, body)
    assert not isinstance(caught.value, ContextWindowError)


# --- the authoring stage asks again with a packet sized from the measurement --------------------


def test_the_tighter_ceiling_is_sized_from_the_refused_requests_own_density() -> None:
    # a bounded request of 360k characters that still measured 258818 tokens: 1.39 characters/token
    error = ContextWindowError(
        "x", context_tokens=262_144, input_tokens=258_818, request_chars=360_000
    )
    ceiling = cascade._tighter_ceiling(error, 8000)
    density = 360_000 / 258_818
    # the window beside the output and the margin, at 80%
    assert ceiling == int(density * (262_144 - 8000 - cascade.CONTEXT_MARGIN_TOKENS) * 0.8)
    assert ceiling < REQUEST_CHAR_CEILING
    assert cascade._tighter_ceiling(
        ContextWindowError("x", context_tokens=10, input_tokens=9, request_chars=1), 8000
    ) == 20_000  # never below a floor that would drop every value to the marker


def test_authoring_asks_again_with_a_smaller_packet_and_gives_up_after_the_retries(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    ceilings: list[int] = []
    refusal = ContextWindowError(
        "refused", context_tokens=262_144, input_tokens=258_818, request_chars=655_330
    )

    def fake_tasks(*_args: Any, ceiling: int, **_kwargs: Any) -> list[Any]:
        ceilings.append(ceiling)
        return []

    calls = {"n": 0}

    def fake_author(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] <= 1:
            raise refusal
        return {"units": []}

    monkeypatch.setattr(cascade, "authoring_tasks", fake_tasks)
    monkeypatch.setattr(cascade, "_author_sections", fake_author)
    prompts = {"section_authoring": SECTION_AUTHORING}
    kwargs = dict(
        entry=make_entry(), document=_facts(), investigation={}, dispositions={}, plan={},
        prompts=prompts, config=CONFIG, ledger=None, store=None, context=None,
    )
    assert cascade._run_authoring(**kwargs) == {"units": []}
    assert ceilings[0] == REQUEST_CHAR_CEILING and ceilings[1] < ceilings[0] and len(ceilings) == 2

    ceilings.clear()
    calls["n"] = -10  # never succeeds
    with pytest.raises(ContextWindowError):
        cascade._run_authoring(**kwargs)
    assert len(ceilings) == cascade.CONTEXT_RETRIES + 1
    assert ceilings == sorted(ceilings, reverse=True) and len(set(ceilings)) == len(ceilings)


def test_the_module_exposes_one_ceiling_below_the_context_window() -> None:
    # at 2 characters per token (denser than any measured request) the ceiling is still inside the
    # 262144-token window beside the 8000 output tokens
    assert REQUEST_CHAR_CEILING / 2 < 262_144 - 8000
    assert authoring_module.REQUEST_CHAR_CEILING == REQUEST_CHAR_CEILING


def test_coherence_asks_again_with_a_smaller_packet_after_a_context_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts, dispositions = _world(1)
    sent: list[int] = []
    refusal = ContextWindowError(
        "refused", context_tokens=262_144, input_tokens=258_818, request_chars=300_000
    )

    def fake_run_job(_loaded: Any, packet: dict[str, Any], **_kwargs: Any) -> Any:
        sent.append(packet_chars_of(packet))
        if len(sent) == 1:
            raise refusal
        return SimpleNamespace(output={"units": [], "omitted": []}, request_sha256="r" * 64)

    monkeypatch.setattr(cascade, "run_job", fake_run_job)
    monkeypatch.setattr(cascade, "apply_coherence", lambda current, _output: (current, []))
    monkeypatch.setattr(cascade, "coherence_checks", lambda *a, **k: [])
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=dispositions) == []
    huge = "# Title\n\n" + "\n\n".join("x" * 4_000 for _ in range(150))
    cascade._run_coherence(
        entry=make_entry(), document=facts, investigation={}, dispositions=dispositions, plan=plan,
        units_document={"units": []}, pre_coherence_readme=huge,
        prompts={"section_authoring": SECTION_AUTHORING}, config=CONFIG,
        ledger=None, store=SimpleNamespace(record_repairs=lambda *a, **k: None), context=None,
    )
    assert len(sent) >= 2 and sent[1] < sent[0]
    assert sent[1] <= int(300_000 / 258_818 * (262_144 - 8000 - cascade.CONTEXT_MARGIN_TOKENS) * 0.8)
