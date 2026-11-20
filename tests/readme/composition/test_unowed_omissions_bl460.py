"""BL-460 (R46 robust, universal): an ``omitted`` list the schema refuses cost the whole Lane R run.

Hosted run 44673592648 (2026-11-20, main 3b07ba8, Slides C++, Lane R): section_authoring ended
``output rejected three times ... last rejection: $.omitted: [...] is too long``. The units were
fine; the model, asked to list every accepted fact a unit does not cite, also listed the
``do_not_claim`` records (contradicted examples 001-007, unresolved formats) and so outgrew the
schema's bound, ``omittable_count`` (the facts the task offers). ``REJECTED_OMITTED`` below is that
list, copied from the job log (31 entries, none repeated); the reply around it is synthesised on the
synthetic product. Nothing calls a provider. Negative controls: a reply that fits is untouched, a
must-carry omission is kept, a real violation still fails closed.
"""

from __future__ import annotations

import copy
from dataclasses import replace
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
    recover_unowed_omissions,
)
from repo_presenter.readme.composition.output_bounds import (
    bound_authoring_citations,
    omittable_ids,
)
from tests.readme.composition.test_pipeline import _dispositions
from tests.readme.composition.test_value_names_bl170 import (
    CONFIG,
    NAME,
    SECTION_AUTHORING,
    _budget,
    _completion,
    _facts,
    _task,
)

REJECTED_OMITTED: list[dict[str, str]] = [
    {"fact_id": "identity:ecosystem", "reason": "Not needed for this capability; ecosystem identity is covered elsewhere."},
    {"fact_id": "identity:family", "reason": "Not needed for this capability; family identity is covered elsewhere."},
    {"fact_id": "identity:platform", "reason": "Not needed for this capability; platform identity is covered elsewhere."},
    {"fact_id": "identity:product-knowledge-refresh", "reason": "Not needed for this capability; knowledge refresh metadata is internal."},
    {"fact_id": "identity:repository", "reason": "Not needed for this capability; repository identity is covered elsewhere."},
    {"fact_id": "identity:revision", "reason": "Not needed for this capability; revision metadata is internal."},
    {"fact_id": "package:cxx_standard", "reason": "Not needed for this capability; C++ standard version is covered in other capability slots."},
    {"fact_id": "package:distribution.aspose.slides.cpp.foss", "reason": "Not needed for this capability; distribution name is covered elsewhere."},
    {"fact_id": "package:name", "reason": "Not needed for this capability; package name is covered elsewhere."},
    {"fact_id": "package:version", "reason": "Not needed for this capability; version is printed by the renderer."},
    {"fact_id": "example:001", "reason": "Not needed for this capability; contradicted example is irrelevant."},
    {"fact_id": "example:002", "reason": "Not needed for this capability; unresolved example is irrelevant."},
    {"fact_id": "example:003", "reason": "Not needed for this capability; contradicted example is irrelevant."},
    {"fact_id": "example:004", "reason": "Contradicted example; not used."},
    {"fact_id": "example:005", "reason": "Contradicted example; not used."},
    {"fact_id": "example:006", "reason": "Contradicted example; not used."},
    {"fact_id": "example:007", "reason": "Contradicted example; not used."},
    {"fact_id": "format:output.fodp", "reason": "Unresolved format; not used."},
    {"fact_id": "format:output.gif", "reason": "Unresolved format; not used."},
    {"fact_id": "format:output.html", "reason": "Unresolved format; not used."},
    {"fact_id": "format:output.html5", "reason": "Unresolved format; not used."},
    {"fact_id": "format:output.md", "reason": "Unresolved format; not used."},
    {"fact_id": "example:008", "reason": "Not needed for this capability; example is for a different capability."},
    {"fact_id": "example:009", "reason": "Not needed for this capability; example is for a different capability."},
    {"fact_id": "format:output.pptx", "reason": "Not needed for this capability; output format is covered elsewhere."},
    {"fact_id": "public_symbol:aspose.slides.foss", "reason": "Not needed for this capability; public symbol is covered elsewhere."},
    {"fact_id": "build_test_asset:tests", "reason": "Not needed for this capability; tests directory is covered in another capability."},
    {"fact_id": "build_test_asset:ci", "reason": "Not needed for this capability; CI workflows are covered in another capability."},
    {"fact_id": "inherited_unit:008.code_block", "reason": "Not needed for this capability; flowchart is for another section."},
    {"fact_id": "inherited_unit:010.paragraph", "reason": "Not needed for this capability; features overview is for another section."},
    {"fact_id": "inherited_unit:011.list", "reason": "Not needed for this capability; API examples are for another section."},
]


def _task_kc() -> Any:
    return _task(_facts(), "key_capabilities")


def _reply(task: Any, omitted: list[dict[str, Any]]) -> dict[str, Any]:
    units = [
        {"section": task.section_id, "slot": slot, "fact_ids": ["package:name"],
         "text": f"It renders widgets for case {chr(96 + int(slot.split(':')[-1]))}."}
        for slot in task.slots
    ]
    return {"units": units, "omitted": copy.deepcopy(omitted)}


def _schema(task: Any) -> dict[str, Any]:
    return bound_authoring_citations(
        authoring_schema(SECTION_AUTHORING, task), task,
        SECTION_AUTHORING.manifest.sampling.max_output_tokens,
    )


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, task: Any, reply: Any,
         *, recover: bool = True) -> Any:
    tmp_path.mkdir(parents=True, exist_ok=True)
    facts = _facts()
    replies = [_completion(reply) for _ in range(3)]
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_p: replies.pop(0)))
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    def checks(output: dict[str, Any]) -> list[str]:
        return unit_checks(output, task, facts, NAME, dispositions=_dispositions())

    def recovery(output: dict[str, Any]) -> dict[str, Any] | None:
        if not recover:
            return None
        return recover_authoring_output(output, task=task, facts=facts, checks=checks, name=NAME)

    return run_job(
        SECTION_AUTHORING, task.packet, config=CONFIG, facts=facts,
        ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
        context=JobContext(facts.repository, facts.source_revision),
        call_schema=_schema(task), checks=checks, recover=recovery,
        narrow=authoring_narrowing(task, SECTION_AUTHORING), budget_path=_budget(tmp_path),
    )


def test_the_logged_list_really_outgrows_the_bound() -> None:
    task = _task_kc()
    bound = _schema(task)["properties"]["omitted"]["maxItems"]
    assert len(REJECTED_OMITTED) == 31 and len({i["fact_id"] for i in REJECTED_OMITTED}) == 31
    assert bound == len(omittable_ids(task)) < len(REJECTED_OMITTED)


def test_without_the_recovery_the_logged_reply_fails_the_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(JobError, match=r"\$\.omitted.*is too long"):
        _run(tmp_path, monkeypatch, _task_kc(), _reply(_task_kc(), REJECTED_OMITTED), recover=False)


def test_the_logged_reply_completes_with_only_owed_omissions_and_a_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task_kc()
    offered = omittable_ids(task)
    result = _run(tmp_path, monkeypatch, task, _reply(task, REJECTED_OMITTED))
    kept = [item["fact_id"] for item in result.output["omitted"]]
    assert kept == [i["fact_id"] for i in REJECTED_OMITTED if i["fact_id"] in offered]
    assert kept and len(kept) < len(REJECTED_OMITTED)
    assert result.output["units"] == _reply(task, [])["units"]  # the units are untouched


def test_every_dropped_entry_is_recorded_with_its_reason() -> None:
    task = _task_kc()
    offered = omittable_ids(task)
    recovered = recover_authoring_output(
        _reply(task, REJECTED_OMITTED), task=task, facts=_facts(), name=NAME
    )
    assert recovered is not None
    notes = recovered[RECOVERY_NOTES_KEY]
    dropped = [i for i in REJECTED_OMITTED if i["fact_id"] not in offered]
    assert [n["fact_id"] for n in notes] == [i["fact_id"] for i in dropped]
    assert all(n["rule"] == "BL-460" and n["reason"] for n in notes)


def test_a_repeated_id_keeps_its_first_entry() -> None:
    task = _task_kc()
    first = {"fact_id": "identity:ecosystem", "reason": "first"}
    recovered = recover_authoring_output(
        _reply(task, [first, {"fact_id": "identity:ecosystem", "reason": "second"}]),
        task=task, facts=_facts(), name=NAME,
    )
    assert recovered is not None and recovered["omitted"] == [first]


def test_the_opening_recovery_trims_too() -> None:
    facts = _facts()
    task = _task(facts, "opening")
    reply = {"units": [{"section": "opening", "slot": "opening", "fact_ids": ["package:name"],
                        "text": f"{NAME} renders widgets."}], "omitted": copy.deepcopy(REJECTED_OMITTED)}
    recovered = recover_opening_output(
        reply, task=task, facts=facts, dispositions=_dispositions(), name=NAME
    )
    assert recovered is not None
    assert {i["fact_id"] for i in recovered["omitted"]} <= omittable_ids(task)


# --- negative controls ----------------------------------------------------------------------


def test_a_reply_whose_omissions_are_all_owed_is_left_alone() -> None:
    task = _task_kc()
    owed = [{"fact_id": i, "reason": "not needed"} for i in sorted(omittable_ids(task))]
    reply = _reply(task, owed)
    assert recover_authoring_output(reply, task=task, facts=_facts(), name=NAME) is None
    assert reply["omitted"] == owed and RECOVERY_NOTES_KEY not in reply


def test_a_must_carry_omission_is_kept() -> None:
    task = replace(_task_kc(), must_carry=frozenset({"inherited_unit:099.paragraph"}))
    entry = {"fact_id": "inherited_unit:099.paragraph", "reason": "flowchart is for another section"}
    recovered = recover_authoring_output(
        _reply(task, [*REJECTED_OMITTED, entry]), task=task, facts=_facts(), name=NAME
    )
    assert recovered is not None and entry in recovered["omitted"]


def test_a_real_violation_still_fails_closed_beside_a_long_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The omission trim alone never accepts a reply whose unit is wrong: the job re-judges the
    trimmed reply through the real checks (the other recoveries, BL-220, are not under test here)."""
    task = _task_kc()
    reply = _reply(task, REJECTED_OMITTED)
    reply["units"][0]["text"] = "See https://example.com/docs for more."
    trimmed = recover_unowed_omissions(copy.deepcopy(reply), task=task)
    assert trimmed is not None and len(trimmed["omitted"]) < len(REJECTED_OMITTED)
    trimmed.pop(RECOVERY_NOTES_KEY)
    assert any("URL" in e for e in unit_checks(trimmed, task, _facts(), NAME, dispositions=_dispositions()))
    facts = _facts()
    replies = [_completion(reply) for _ in range(3)]
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_p: replies.pop(0)))
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    with pytest.raises(JobError, match="rejected"):
        run_job(
            SECTION_AUTHORING, task.packet, config=CONFIG, facts=facts,
            ledger=Ledger(tmp_path / "ledger.jsonl"), store=CallStore(tmp_path / "calls"),
            context=JobContext(facts.repository, facts.source_revision),
            call_schema=_schema(task),
            checks=lambda o: unit_checks(o, task, facts, NAME, dispositions=_dispositions()),
            recover=lambda o: recover_unowed_omissions(o, task=task),
            narrow=authoring_narrowing(task, SECTION_AUTHORING), budget_path=_budget(tmp_path),
        )
