"""BL-610 (R46 robust/reliable): two model-output classes that failed a whole Lane R run closed.

Truncated coherence batch (hosted PDF TypeScript run 44924813052: "JobError: section_authoring:
output truncated at the manifest's max_output_tokens (8000); raise the budget or bound the output,
never retry" after 48 calls): the coherence call echoes every unit of its batch, so a batch of
large units can overrun the output budget; it is asked again as two smaller batches, and a section
whose own reply is still cut off keeps its authored units. Nothing calls a provider.

Uncitable fact id (hosted PDF Python run 44924772455: ``source_reconciliation: output rejected
twice; last rejection: $.dispositions[13].fact_ids[2]: 'public_symbol:aspose_pdf.document.
registry_lag' is not one of [...] (cite only an offered ID)``, the same invented id at indexes 2, 3
and 4 beside two valid ones): the ids outside the offered enum are deleted, recorded, never guessed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.cascade import _run_reconciliation, run_cascade
from repo_presenter.core.errors import OutputRejectedError
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.reconciliation.dispositions import recover_uncitable_fact_ids
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import (
    CONFIG,
    _AUTHORING_REPLIES,
    _FakeClient,
    _INVESTIGATION_REPLY,
    _PLANNING_REPLY,
    _RECONCILIATION_REPLY,
    _completion,
    _write_registry,
    clone_path,  # noqa: F401  (fixture)
)

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "prompts"


def _length(content: dict[str, Any]) -> Any:
    reply = _completion(content)
    reply.choices[0].finish_reason = "length"
    return reply


# --- coherence ---------------------------------------------------------------------------------


def _coherence_replies(coherence: list[Any]) -> tuple[list[Any], dict[str, Any]]:
    from repo_presenter.readme.composition.authoring import merge_units

    labels = ["opening", "key_capabilities", "quick_start", "api_reference"]
    merged = merge_units(dict(zip(labels, _AUTHORING_REPLIES)))
    head = [
        _completion(_INVESTIGATION_REPLY),
        _completion(_RECONCILIATION_REPLY),
        _completion(_PLANNING_REPLY),
        *[_completion(r) for r in _AUTHORING_REPLIES],
    ]
    return [*head, *coherence], merged


def _run(tmp_path: Path, clone: Path, monkeypatch: pytest.MonkeyPatch, replies: list[Any]) -> tuple[Any, Path, _FakeClient]:
    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry = tmp_path / "registry.json"
    _write_registry(registry, entry)
    out = tmp_path / "out"
    client = _FakeClient(replies)
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    result = run_cascade(
        entry.repository, "python", clone, facts_path=facts_path, out_dir=out,
        config=CONFIG, registry_path=registry, max_rounds=1,
    )
    return result, out, client


def test_a_truncated_coherence_batch_is_asked_again_as_two_smaller_batches(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, merged = _coherence_replies([])
    units = merged["units"]
    sections = list(dict.fromkeys(unit["section"] for unit in units))
    first = [u for u in units if u["section"] in sections[: len(sections) // 2]]
    second = [u for u in units if u["section"] not in sections[: len(sections) // 2]]
    replies, _ = _coherence_replies(
        [
            _length({"units": units, "omitted": []}),
            _completion({"units": first, "omitted": []}),
            _completion({"units": second, "omitted": []}),
        ]
    )
    result, out, client = _run(tmp_path, clone_path, monkeypatch, replies)
    assert client.chat.completions.replies == []  # all three coherence replies consumed
    coherent = json.loads((out / "content_units.coherent.json").read_text(encoding="utf-8"))
    assert [(u["section"], u["slot"]) for u in coherent["units"]] == [
        (u["section"], u["slot"]) for u in units
    ]


def test_a_section_whose_own_coherence_reply_is_cut_off_keeps_its_authored_units(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, merged = _coherence_replies([])
    units = merged["units"]
    sections = list(dict.fromkeys(unit["section"] for unit in units))
    cut = len(sections) // 2
    first = [u for u in units if u["section"] in sections[:cut]]
    second = [u for u in units if u["section"] not in sections[:cut]]
    # the first half is cut off again and then each of its own sections alone
    singles = [_length({"units": [u for u in first if u["section"] == s], "omitted": []}) for s in sections[:cut]]
    replies, _ = _coherence_replies(
        [
            _length({"units": units, "omitted": []}),
            _length({"units": first, "omitted": []}),
            *singles[:1],
            *singles[1:],
            _completion({"units": second, "omitted": []}),
        ]
    )
    result, out, client = _run(tmp_path, clone_path, monkeypatch, replies)
    assert client.chat.completions.replies == []
    coherent = json.loads((out / "content_units.coherent.json").read_text(encoding="utf-8"))
    original = json.loads((out / "content_units.json").read_text(encoding="utf-8"))
    kept = [u for u in coherent["units"] if u["section"] in sections[:cut]]
    assert kept == [u for u in original["units"] if u["section"] in sections[:cut]]
    notes = [
        note
        for path in (out / "llm_cache").rglob("*.repaired-0.json")
        for note in json.loads(path.read_text(encoding="utf-8")).get("notes", [])
        if note.get("fallback") == "coherence_section_left_unrevised"
    ]
    assert {section for note in notes for section in note["sections"]} == set(sections[:cut])


def test_negative_control_only_a_truncation_is_told_from_other_job_errors() -> None:
    """The split answers a cut-off reply alone: any other JobError (and the failure class string
    ``failures.py`` reads, ``JobError: ...``) is exactly what it was."""
    from repo_presenter.core.errors import JobError
    from repo_presenter.core.llm.jobs import is_truncation
    from repo_presenter.failures import job_error_kind

    assert not is_truncation(JobError("section_authoring: gateway answered HTTP 400"))
    assert not is_truncation(OutputRejectedError("section_authoring: output rejected twice"))
    detail = (
        "attempt under version set 75b35954c877: JobError: section_authoring: output truncated at "
        "the manifest's max_output_tokens (8000); raise the budget or bound the output, never retry"
    )
    assert job_error_kind(detail) == ("JobError", "section_authoring_output_truncated_at")


# --- reconciliation ----------------------------------------------------------------------------


def _facts() -> tuple[FactsDocument, str, str]:
    paragraph, heading = "inherited_unit:001.paragraph", "inherited_unit:002.heading"
    base = make_facts()
    facts = FactsDocument(
        base.repository,
        base.source_revision,
        (
            *(f for f in base.facts if f.kind != "inherited_unit"),
            Fact(paragraph, "inherited_unit", "Only PNG output is currently supported.", (Evidence("README.md", "s"),)),
            Fact(heading, "inherited_unit", "## Notes", (Evidence("README.md", "s"),)),
        ),
    )
    return facts, paragraph, heading


INVENTED = "public_symbol:aspose_widget.document.registry_lag"


def _entry(unit: str, disposition: str, ids: list[str], destination: str | None = None) -> dict[str, Any]:
    return {
        "unit_id": unit, "disposition": disposition, "destination_section": destination,
        "fact_ids": ids, "rationale": "recorded",
    }


def _reconcile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, facts: FactsDocument, replies: list[dict]) -> Any:
    client = _FakeClient([_completion(r) for r in replies])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    stage = _run_reconciliation(
        entry=make_entry(), document=facts, investigation={}, prompts=load_manifests(PROMPTS_PATH),
        config=CONFIG, ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
        context=JobContext(make_entry().repository, facts.source_revision),
    )
    assert client.chat.completions.replies == []
    return stage


def _ids_of(facts: FactsDocument) -> list[str]:
    return [f.id for f in facts.facts if f.kind in ("identity", "package")][:2]


def test_an_invented_fact_id_repeated_beside_valid_ones_is_deleted_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts, paragraph, heading = _facts()
    valid = _ids_of(facts)
    bad = {
        "dispositions": [
            _entry(paragraph, "VERIFIED_PRESERVE", [*valid, INVENTED, INVENTED, INVENTED], "scope_limitations"),
            _entry(heading, "SUPERSEDE_REDUNDANT", [], "scope_limitations"),
        ]
    }
    stage = _reconcile(tmp_path, monkeypatch, facts, [bad, bad])  # the first ask and the re-ask
    by_unit = {e["unit_id"]: e for e in stage["dispositions"]}
    assert by_unit[paragraph]["fact_ids"] == valid
    notes = [
        n
        for p in (tmp_path / "calls").glob("*.repaired-*.json")
        for n in json.loads(p.read_text(encoding="utf-8")).get("notes", [])
    ]
    assert notes and notes[0]["dropped"] == [INVENTED] and notes[0]["rule"] == "BL-610"


def test_negative_control_a_preserve_left_with_no_cited_fact_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts, paragraph, heading = _facts()
    bad = {
        "dispositions": [
            _entry(paragraph, "VERIFIED_PRESERVE", [INVENTED, INVENTED], "scope_limitations"),
            _entry(heading, "SUPERSEDE_REDUNDANT", [], "scope_limitations"),
        ]
    }
    with pytest.raises(OutputRejectedError, match="is not one of"):
        _reconcile(tmp_path, monkeypatch, facts, [bad, bad])


def test_recovery_never_substitutes_a_nearest_id_and_names_nothing_when_all_ids_are_offered() -> None:
    offered = ["identity:repository", "package:registry_lag"]
    output = {"dispositions": [_entry("inherited_unit:001.paragraph", "VERIFIED_PRESERVE", ["identity:repository"], "opening")]}
    assert recover_uncitable_fact_ids(output, offered) is None  # nothing outside the enum
    near = {"dispositions": [_entry("inherited_unit:001.paragraph", "VERIFIED_PRESERVE", ["identity:repository", "public_symbol:x.registry_lag"], "opening")]}
    fixed = recover_uncitable_fact_ids(near, offered)
    assert fixed is not None
    assert fixed["dispositions"][0]["fact_ids"] == ["identity:repository"]  # deleted, not swapped for package:registry_lag
