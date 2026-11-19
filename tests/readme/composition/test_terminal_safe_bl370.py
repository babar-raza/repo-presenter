"""BL-370 (R46 robust, universal): three more shapes of one failing slot costing a whole Lane R run
after BL-220, from the hosted pass 3 failure records (2026-11-19, main 4a0d0a5; the job log prints the
rejection text, not the rejected reply, so each reply below is synthesised from that text and the
unit and slot context, on the synthetic product; nothing calls a provider):

* Words Java 44621196631: ``unit opening: text contains a Markdown heading ('#')`` three times on a
  unit with no line break: the refusal matched ``"# "`` anywhere, so ``C# `` inside a sentence was a
  heading;
* PDF TypeScript 44620155157 (and Cells C++ before it): ``unit context: names the Enterprise
  Edition`` after every ask and BL-220's deletion, i.e. a single sentence that names it as its
  subject or in a closing phrase, which the deletion refused to touch;
* PDF Python 44619841642: ``JobError: section_authoring: output truncated at the manifest's
  max_output_tokens (8000); raise the budget or bound the output, never retry``.

Negative controls still fail closed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.errors import JobError
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.readme.composition.authoring import authoring_schema, unit_checks
from repo_presenter.readme.composition.authoring_retry import (
    RECOVERY_NOTES_KEY,
    authoring_narrowing,
    recover_authoring_output,
    recover_opening_output,
)
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from tests.readme.composition.synthetic import make_facts
from tests.readme.composition.test_pipeline import _dispositions
from tests.readme.composition.test_terminal_safe_bl220 import _context, _enterprise_task
from tests.readme.composition.test_value_names_bl170 import (
    CONFIG,
    NAME,
    SECTION_AUTHORING,
    _budget,
    _facts,
    _task,
)

# --- the heading: a '#' inside a sentence is prose -----------------------------------------------

C_SHARP = (
    f"{NAME} reads and writes widget documents from Java, and mirrors the API of the C# port "
    "so code moves between them."
)


def _opening(text: str) -> dict[str, Any]:
    return {"units": [{"section": "opening", "slot": "opening", "text": text,
                       "fact_ids": ["package:name"]}], "omitted": []}


def _heading_errors(text: str) -> list[str]:
    facts = _facts()
    task = _task(facts, "opening")
    errors = unit_checks(copy.deepcopy(_opening(text)), task, facts, NAME,
                         dispositions=_dispositions())
    return [e for e in errors if "Markdown heading" in e]


def test_a_hash_inside_a_sentence_is_not_a_heading() -> None:
    assert _heading_errors(C_SHARP) == []
    assert _heading_errors("It supports F# and C# callers, and issue # 5 is tracked.") == []


@pytest.mark.parametrize("text", ["# Aspose.Widget FOSS", "## It renders widgets.", "  ### It renders."])
def test_a_real_heading_is_still_refused(text: str) -> None:
    assert _heading_errors(text) == [f"unit opening: text contains a Markdown heading ('#')"]


def test_a_leading_heading_marker_is_deleted_and_recorded() -> None:
    facts = _facts()
    task = _task(facts, "opening")
    output = _opening("## It renders widgets to images.")
    recovered = recover_opening_output(
        output, task=task, facts=facts, dispositions=_dispositions(), name=NAME
    )
    assert recovered is not None
    note = recovered.pop(RECOVERY_NOTES_KEY)[0]
    assert note["rule"] == "BL-370" and note["rejected_text"] == "## It renders widgets to images."
    assert recovered["units"][0]["text"] == "It renders widgets to images."
    assert unit_checks(copy.deepcopy(recovered), task, facts, NAME, dispositions=_dispositions()) == []


def test_a_unit_that_is_only_a_heading_marker_fails_closed() -> None:
    facts = _facts()
    task = _task(facts, "opening")
    assert recover_opening_output(
        _opening("# "), task=task, facts=facts, dispositions=_dispositions(), name=NAME
    ) is None


def test_a_passing_unit_with_a_hash_is_never_touched() -> None:
    facts = _facts()
    task = _task(facts, "opening")
    assert recover_opening_output(
        _opening(C_SHARP), task=task, facts=facts, dispositions=_dispositions(), name=NAME
    ) is None


# --- the edition name as the subject or in a closing phrase ---------------------------------------


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("The Enterprise Edition adds batch conversion and PDF signing.",
         "It adds batch conversion and PDF signing."),
        ("Aspose.Widget Enterprise Edition adds batch conversion.", "It adds batch conversion."),
        ("It adds batch conversion and PDF signing in the Enterprise Edition.",
         "It adds batch conversion and PDF signing."),
        ("It adds batch conversion and signing with Aspose.Widget Enterprise Edition.",
         "It adds batch conversion and signing."),
    ],
)
def test_a_single_sentence_naming_the_edition_is_repaired(text: str, kept: str) -> None:
    task = _enterprise_task()
    assert any("names the Enterprise Edition" in e
               for e in unit_checks(copy.deepcopy(_context(text)), task, make_facts(), NAME))
    recovered = recover_authoring_output(_context(text), task=task, facts=make_facts(), name=NAME)
    assert recovered is not None
    assert recovered["units"][0]["text"] == kept
    assert recovered[RECOVERY_NOTES_KEY][0]["rejected_text"] == text
    recovered.pop(RECOVERY_NOTES_KEY)
    assert unit_checks(copy.deepcopy(recovered), task, make_facts(), NAME) == []


@pytest.mark.parametrize(
    "text",
    ["Enterprise Edition.", "It is sold as the Enterprise Edition.", "See the Enterprise Edition."],
)
def test_a_unit_with_nothing_but_the_name_still_fails_closed(text: str) -> None:
    assert recover_authoring_output(
        _context(text), task=_enterprise_task(), facts=make_facts(), name=NAME
    ) is None


# --- truncation: a reply cut at the output limit is narrowed and asked again ----------------------


def _units(task: Any, slots: list[str], prefix: str = "It renders widgets") -> list[dict[str, Any]]:
    return [{"section": task.section_id, "slot": s, "fact_ids": ["package:name"],
             "text": f"{prefix} for case {chr(96 + int(s.split(':')[-1]))}."} for s in slots]


def _raw(content: str, finish: str = "stop") -> Any:
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)],
        model="qwen3-next", id="req-1", usage=usage,
    )


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, task: Any, replies: list[Any],
         *, narrow: bool = True) -> tuple[Any, list[dict[str, Any]]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    facts = _facts()
    requests: list[dict[str, Any]] = []
    queue = list(replies)

    def create(**payload: Any) -> Any:
        requests.append(payload)
        return queue.pop(0)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    def checks(output: dict[str, Any]) -> list[str]:
        return unit_checks(output, task, facts, NAME, dispositions=_dispositions())

    result = run_job(
        SECTION_AUTHORING, task.packet, config=CONFIG, facts=facts,
        ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=bound_authoring_citations(
            authoring_schema(SECTION_AUTHORING, task), task,
            SECTION_AUTHORING.manifest.sampling.max_output_tokens,
        ),
        checks=checks, narrow=authoring_narrowing(task, SECTION_AUTHORING) if narrow else None,
        budget_path=_budget(tmp_path),
    )
    return result, requests


def _cut(task: Any, complete: int) -> str:
    """A reply cut off inside its next unit, after ``complete`` whole units."""
    whole = json.dumps({"units": _units(task, list(task.slots)[:complete])})[:-2]
    return whole + ', {"section": "key_capabilities", "slot": "capab'


def test_completed_units_are_the_whole_ones_only() -> None:
    from repo_presenter.readme.composition.authoring_retry import completed_units

    task = _task(_facts(), "key_capabilities")
    assert len(task.slots) >= 3
    found = completed_units(_cut(task, 2))
    assert [u["slot"] for u in found] == list(task.slots)[:2]
    assert completed_units("") == [] and completed_units('{"units": [{"section": "a", "sl') == []


def test_a_truncated_reply_is_narrowed_to_the_missing_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task(_facts(), "key_capabilities")
    slots = list(task.slots)
    rest = json.dumps({"units": _units(task, slots[2:]), "omitted": []})
    with pytest.raises(JobError, match="output truncated"):
        _run(tmp_path / "before", monkeypatch, task, [_raw(_cut(task, 2), "length")], narrow=False)
    result, requests = _run(
        tmp_path / "after", monkeypatch, task, [_raw(_cut(task, 2), "length"), _raw(rest)]
    )
    assert [u["slot"] for u in result.output["units"]] == slots
    assert len(requests) == 2
    asked = json.dumps(requests[1]["messages"])
    assert slots[2] in asked and f"unit {slots[0]}: " not in asked
    notes = [json.loads(p.read_text())["notes"][0] for p in
             (tmp_path / "after" / "calls").glob("*.repaired-*.json")]
    assert notes[0]["rule"] == "BL-370" and notes[0]["asked"] == slots[2:]


def test_a_reply_cut_before_any_unit_is_asked_again_with_half_the_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task(_facts(), "key_capabilities")
    slots = list(task.slots)
    half = (len(slots) + 1) // 2
    first = json.dumps({"units": _units(task, slots[:half]), "omitted": []})
    second = json.dumps({"units": _units(task, slots[half:]), "omitted": []})
    result, requests = _run(
        tmp_path, monkeypatch, task,
        [_raw('{"units": [{"section": "key_cap', "length"), _raw(first), _raw(second)],
    )
    assert [u["slot"] for u in result.output["units"]] == slots
    assert len(requests) == 3


def test_a_reply_cut_every_time_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task(_facts(), "key_capabilities")
    cuts = [_raw('{"units": [', "length") for _ in range(8)]
    with pytest.raises(JobError, match="output truncated"):
        _run(tmp_path, monkeypatch, task, cuts)


def test_a_complete_reply_is_never_narrowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task(_facts(), "key_capabilities")
    whole = json.dumps({"units": _units(task, list(task.slots)), "omitted": []})
    result, requests = _run(tmp_path, monkeypatch, task, [_raw(whole)])
    assert len(requests) == 1 and result.attempts == 1
