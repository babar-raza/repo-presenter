"""Reviewer-driven targeted repair (readme/repair/loop.py), offline.

No network call is made: ``core.llm.jobs.transport.build_client`` is replaced by a fake client
that returns scripted completions, the same pattern tests/test_cascade.py uses. The one reviewer
verdict that is not the real one is injected on the first pass only (a REJECT built from a real
``Finding`` shape), so the repair path runs against the real cascade output and the real
``repair_checks``/``unit_checks``; the verdict after the repair is the real reviewer's own.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.cascade import run_cascade
from repo_presenter.core.facts import write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.registry.models import Registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import merge_units
from repo_presenter.readme.repair.loop import (
    _load_context,
    _regenerate_plan,
    _regenerate_section,
    _repair_section,
    keep_unflagged_units,
    refuse_noop,
    settle_candidate,
)
from repo_presenter.readme.repair.targeted import REPAIRS_FILENAME, Defect, RepairLedger
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import (
    Finding,
    ReviewVerdict,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import (
    _AUTHORING_REPLIES,
    _AUTHORING_TEXT,
    _PLANNING_REPLY,
    CONFIG,
    README,
    _completion,
    _FakeClient,
    _scripted_replies,
)

LABELS = [
    "opening",
    "key_capabilities",
    "quick_start",
    "api_reference",
    "scope_limitations",
]
REPAIRED_TEXT = (
    "This shows a reader how the library turns its output into a finished file."
)
QUOTE = _AUTHORING_TEXT


@pytest.fixture(autouse=True)
def _fixed_git_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cascade_module,
        "run_git",
        lambda *a, **k: SimpleNamespace(stdout="f" * 40 + "\n"),
    )


@pytest.fixture
def clone_path(tmp_path: Path) -> Path:
    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "README.md").write_text(README, encoding="utf-8", newline="\n")
    return clone


def _registry(tmp_path: Path) -> Path:
    path = tmp_path / "registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        Registry(entries=(make_entry(),)).model_dump_json(), encoding="utf-8"
    )
    return path


def _injected_reject(*, quote: str) -> ReviewVerdict:
    finding = Finding(
        rule="claim_contradiction",
        source="deterministic",
        message="injected by the test: the quoted sentence must be repaired",
        evidence="test fixture",
        quote=quote,
    )
    return ReviewVerdict(verdict="REJECT", findings=(finding,))


def _opening_repair_reply(
    fingerprint: str, original_text: str, text: str
) -> dict[str, Any]:
    opening = dict(_AUTHORING_REPLIES[0]["units"][0])
    opening["text"] = text
    return {
        "causal_stage": "S6",
        "fingerprint": fingerprint,
        "revised_output": {"units": [opening], "omitted": []},
        "changes": [
            {
                "id": "R01",
                "path": "units[0].text",
                "before": original_text,
                "after": text,
                "fact_ids": [],
            }
        ],
    }


def _coherence_echo(opening_text: str) -> dict[str, Any]:
    replies = list(_AUTHORING_REPLIES)
    opening = dict(replies[0]["units"][0])
    opening["text"] = opening_text
    replies[0] = {"units": [opening], "omitted": []}
    merged = merge_units(dict(zip(LABELS, replies)))
    return {"units": merged["units"], "omitted": []}


def test_a_no_op_revision_is_refused_before_the_stage_checks_run() -> None:
    original = {"units": [{"slot": "opening", "text": "a"}]}
    seen: list[dict[str, Any]] = []

    def checks(revised: dict[str, Any]) -> list[str]:
        seen.append(revised)
        return []

    guarded = refuse_noop(original, checks)
    assert guarded(json.loads(json.dumps(original)))
    assert seen == []
    assert guarded({"units": [{"slot": "opening", "text": "b"}]}) == []
    assert len(seen) == 1


def test_a_targeted_repair_may_not_rewrite_a_unit_the_finding_does_not_name() -> None:
    original = {
        "units": [
            {"slot": "opening", "text": f"Intro. {QUOTE}"},
            {"slot": "capability:1", "text": "Renders output."},
        ]
    }
    never = lambda revised: []
    guarded = keep_unflagged_units(never, original, QUOTE)

    only_flagged = {
        "units": [
            {"slot": "opening", "text": "Intro. Rewritten."},
            {"slot": "capability:1", "text": "Renders output."},
        ]
    }
    assert guarded(only_flagged) == []

    rewrites_other = {
        "units": [
            {"slot": "opening", "text": "Intro. Rewritten."},
            {"slot": "capability:1", "text": "Something else entirely."},
        ]
    }
    errors = guarded(rewrites_other)
    assert len(errors) == 1 and "capability:1" in errors[0]


def test_a_quote_that_names_no_unit_does_not_narrow_the_repair() -> None:
    original = {"units": [{"slot": "opening", "text": "Intro."}]}
    guarded = keep_unflagged_units(
        lambda revised: [], original, "absent from every unit"
    )
    assert guarded({"units": [{"slot": "opening", "text": "Different."}]}) == []


def test_a_rejected_finding_is_repaired_once_through_run_job_and_the_cascade_is_settled(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = _registry(tmp_path)
    out_dir = tmp_path / "out"
    prompts_path = Path(__file__).resolve().parents[3] / "prompts"

    # Phase 1: the real cascade, nine scripted calls, accepted by the real reviewer.
    client = _FakeClient(_scripted_replies())
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    first = run_cascade(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
        max_rounds=1,
    )
    assert first.provider_calls == 9
    # The fixture's own real verdict is REJECT, for heading losses no repair here can touch
    # (deterministic sections). Those stay, unrepairable, after the settle as well. Its kept
    # quick-start code block used to be a second finding; the renderer prints that block from the
    # SUPPORTED example fact it cites, so the S9 accounting now says so and cites that fact.
    real_rules = {finding.rule for finding in first.review_verdict.findings}
    assert real_rules == {"live_readme_loss"}
    accounted = json.loads((out_dir / "accounting.json").read_text(encoding="utf-8"))
    code = [a for a in accounted["accounted"] if a["unit_id"].endswith("004.code_block")]
    assert code and code[0]["now"] == "SUPERSEDE_REDUNDANT"
    assert any(fact.startswith("example:") for fact in code[0]["fact_ids"])
    before = json.loads(
        (out_dir / "content_units.coherent.json").read_text(encoding="utf-8")
    )
    before_texts = {unit["slot"]: unit["text"] for unit in before["units"]}

    # The defect the injected REJECT produces, routed exactly as settle_candidate will route it.
    prompts = load_manifests(prompts_path)
    units = json.loads(
        (out_dir / "content_units.coherent.json").read_text(encoding="utf-8")
    )
    defects = build_defects(
        _injected_reject(quote=QUOTE),
        units=units.get("units", []),
        plan=json.loads((out_dir / "plan.json").read_text(encoding="utf-8")),
        dispositions=json.loads(
            (out_dir / "dispositions.json").read_text(encoding="utf-8")
        ),
        facts=first.document,
        ecosystem="python",
        repairer=prompts["targeted_repair"].sha256,
    )
    assert [(d.stage, d.section_id) for d in defects] == [("S6", "opening")]
    fingerprint = defects[0].fingerprint

    # Phase 2: the first cascade pass of settle_candidate is served entirely from the store (no
    # call); its review is the injected REJECT. The repair is one call, then the coherence pass
    # that reads the repaired unit is asked again. Nothing else is.
    client = _FakeClient(
        [
            _completion(_opening_repair_reply(fingerprint, QUOTE, REPAIRED_TEXT)),
            _completion(_coherence_echo(REPAIRED_TEXT)),
        ]
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    real_review = cascade_module.review_candidate
    reviews: list[ReviewVerdict] = []

    def review_once(**kwargs: Any) -> ReviewVerdict:
        verdict = (
            _injected_reject(quote=QUOTE) if not reviews else real_review(**kwargs)
        )
        reviews.append(verdict)
        return verdict

    monkeypatch.setattr(cascade_module, "review_candidate", review_once)

    settled = settle_candidate(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
        max_rounds=2,
    )

    assert client.chat.completions.replies == []
    assert settled.rounds == 2
    assert settled.result.provider_calls == 1
    final_rules = {finding.rule for finding in settled.result.review_verdict.findings}
    assert final_rules == real_rules  # the repaired claim is no longer contradicted

    ledger = RepairLedger(out_dir / REPAIRS_FILENAME)
    assert ledger.attempts[fingerprint]["outcome"] == "repaired"
    assert ledger.attempts[fingerprint]["stage"] == "S6"

    coherent = json.loads(
        (out_dir / "content_units.coherent.json").read_text(encoding="utf-8")
    )
    after_texts = {unit["slot"]: unit["text"] for unit in coherent["units"]}
    # Targeted: the flagged unit changed; every other unit is byte-identical to the first pass.
    assert after_texts["opening"] == REPAIRED_TEXT
    assert {s: t for s, t in after_texts.items() if s != "opening"} == {
        s: t for s, t in before_texts.items() if s != "opening"
    }
    readme = (out_dir / "README.coherent.md").read_text(encoding="utf-8")
    assert REPAIRED_TEXT in readme


def test_a_repair_that_only_restates_the_input_is_unrepairable_and_not_retried(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = _registry(tmp_path)
    out_dir = tmp_path / "out"
    prompts_path = Path(__file__).resolve().parents[3] / "prompts"

    client = _FakeClient(_scripted_replies())
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    first = run_cascade(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
        max_rounds=1,
    )
    prompts = load_manifests(prompts_path)
    units = json.loads(
        (out_dir / "content_units.coherent.json").read_text(encoding="utf-8")
    )
    fingerprint = build_defects(
        _injected_reject(quote=QUOTE),
        units=units.get("units", []),
        plan=json.loads((out_dir / "plan.json").read_text(encoding="utf-8")),
        dispositions=json.loads(
            (out_dir / "dispositions.json").read_text(encoding="utf-8")
        ),
        facts=first.document,
        ecosystem="python",
        repairer=prompts["targeted_repair"].sha256,
    )[0].fingerprint

    # Both of run_job's asks restate the stored unit unchanged: refused, never recorded repaired.
    unchanged = _opening_repair_reply(fingerprint, QUOTE, QUOTE)
    client = _FakeClient([_completion(unchanged), _completion(unchanged)])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    real_review = cascade_module.review_candidate
    reviews: list[ReviewVerdict] = []

    def review_once(**kwargs: Any) -> ReviewVerdict:
        verdict = (
            _injected_reject(quote=QUOTE) if not reviews else real_review(**kwargs)
        )
        reviews.append(verdict)
        return verdict

    monkeypatch.setattr(cascade_module, "review_candidate", review_once)

    settled = settle_candidate(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
    )

    ledger = RepairLedger(out_dir / REPAIRS_FILENAME)
    assert ledger.attempts[fingerprint]["outcome"] == "unrepairable"
    assert "unchanged" in ledger.attempts[fingerprint]["reason"]
    assert settled.rounds == 1
    assert settled.result.review_verdict.verdict == "REJECT"
    assert client.chat.completions.replies == []


# --- a missing call-store entry (--restore-sealed-bundle) is regenerated, not given up on ------
#
# Aspose.Slides-FOSS-for-Cpp (hosted, two separate runs, 2026-11-11): every S6 review finding
# came back "the causing section is not in the call store" and every S5 one "the causing plan is
# not in the call store" -- the hosted default restores a PREVIOUS seal's call store, so a
# section/plan this run never itself generated has no original to revise. _regenerate_section/
# _regenerate_plan run the SAME job initial generation makes instead of stopping the repair cold.


def _real_repair_context(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, Any]:
    """A real RepairContext from a real cascade run (phase 1, 9 scripted calls), whose ``store``
    is then swapped for a FRESH, EMPTY one -- exactly what the call store looks like for a
    section/plan ``--restore-sealed-bundle`` never re-generated this run. Returns ``(rc, prompts)``."""
    from dataclasses import replace as dc_replace

    from repo_presenter.core.llm.jobs import CallStore

    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = _registry(tmp_path)
    out_dir = tmp_path / "out"
    prompts_path = Path(__file__).resolve().parents[3] / "prompts"

    client = _FakeClient(_scripted_replies())
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    first = run_cascade(
        entry.repository, "python", clone_path,
        facts_path=facts_path, out_dir=out_dir, config=CONFIG,
        registry_path=registry_path, max_rounds=1,
    )
    assert client.chat.completions.replies == []

    prompts = load_manifests(prompts_path)
    from repo_presenter.core.llm.ledger import Ledger

    ledger = Ledger(tmp_path / "ledger2.jsonl", invocation_id="test")
    rc = _load_context(
        first, out_dir=out_dir, registry_path=registry_path, prompts=prompts,
        config=CONFIG, ledger=ledger, benchmark="",
    )
    empty_store = CallStore(tmp_path / "empty_calls")
    return dc_replace(rc, store=empty_store), prompts


def test_regenerate_section_runs_a_fresh_authoring_call_and_the_store_keeps_it(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rc, prompts = _real_repair_context(tmp_path, clone_path, monkeypatch)
    task = next(t for t in rc.tasks if t.section_id == "opening")
    loaded = prompts["section_authoring"]

    fresh_client = _FakeClient([_completion(_AUTHORING_REPLIES[0])])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: fresh_client)

    output = _regenerate_section(rc, task, loaded)

    assert output is not None
    assert output["units"][0]["text"] == _AUTHORING_TEXT
    assert fresh_client.chat.completions.replies == []

    from repo_presenter.core.llm.jobs import effective_model, request_hash
    from repo_presenter.readme.composition.authoring import authoring_schema
    from repo_presenter.readme.composition.output_bounds import bound_authoring_citations

    key = request_hash(
        loaded, task.packet,
        bound_authoring_citations(authoring_schema(loaded, task), task),
        model=effective_model(loaded, rc.context),
    )
    # run_job's own side effect: no extra bookkeeping needed, the previously-empty store now
    # holds this exact output under the same key _repair_section would look it up by.
    assert rc.store.get(key) == output


def test_regenerate_plan_runs_a_fresh_planning_call_and_the_store_keeps_it(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rc, prompts = _real_repair_context(tmp_path, clone_path, monkeypatch)
    loaded = prompts["presentation_planning"]

    fresh_client = _FakeClient([_completion(_PLANNING_REPLY)])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: fresh_client)

    output = _regenerate_plan(rc, loaded)

    assert output is not None
    assert fresh_client.chat.completions.replies == []

    from repo_presenter.core.llm.jobs import effective_model, request_hash
    from repo_presenter.readme.composition.planning import planning_packet, planning_schema

    key = request_hash(
        loaded,
        planning_packet(rc.entry, rc.facts, rc.investigation, rc.dispositions, loaded.manifest),
        planning_schema(loaded, rc.facts, rc.investigation, rc.dispositions),
        model=effective_model(loaded, rc.context),
    )
    assert rc.store.get(key) == output


def test_regenerate_section_returns_none_when_the_fresh_call_is_rejected(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: a fresh call that never clears its own checks falls through to None,
    not a raised exception -- the caller is the one that turns that into "unrepairable"."""
    rc, prompts = _real_repair_context(tmp_path, clone_path, monkeypatch)
    task = next(t for t in rc.tasks if t.section_id == "opening")
    loaded = prompts["section_authoring"]

    broken = {"units": [], "omitted": []}  # fails unit_checks: wrong slot set, every ask
    rejecting_client = _FakeClient([_completion(broken), _completion(broken), _completion(broken)])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: rejecting_client)

    assert _regenerate_section(rc, task, loaded) is None


def test_repair_section_regenerates_and_records_it_distinctly_when_the_store_is_empty(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rc, prompts = _real_repair_context(tmp_path, clone_path, monkeypatch)
    repairs = RepairLedger(tmp_path / "repairs2.json")
    defect = Defect(
        fingerprint="fp-missing-store",
        source="review",
        label="unsupported_claim",
        section_id="opening",
        stage="S6",
        record={"quote": QUOTE},
    )

    fresh_client = _FakeClient([_completion(_AUTHORING_REPLIES[0])])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: fresh_client)

    changed = _repair_section(rc, defect, repairs)

    assert changed is True
    assert fresh_client.chat.completions.replies == []
    attempt = repairs.attempts[defect.fingerprint]
    assert attempt["outcome"] == "repaired"
    assert "restored from a sealed bundle" in attempt["reason"]
    assert attempt["stage"] == "S6"


def test_a_revision_that_changes_the_plans_slot_set_escalates_once_to_the_plan(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repair that re-chooses the section's slot is a planning decision: the S6 finding is
    recorded escalated and the plan gets one plan-level repair, which here restates the stored plan
    and is refused as a no-op. Nothing else is asked."""
    from repo_presenter.readme.repair.targeted import defect_fingerprint

    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = _registry(tmp_path)
    out_dir = tmp_path / "out"
    prompts_path = Path(__file__).resolve().parents[3] / "prompts"

    client = _FakeClient(_scripted_replies())
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    first = run_cascade(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
        max_rounds=1,
    )
    prompts = load_manifests(prompts_path)
    units = json.loads(
        (out_dir / "content_units.coherent.json").read_text(encoding="utf-8")
    )
    plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
    s6 = build_defects(
        _injected_reject(quote=QUOTE),
        units=units.get("units", []),
        plan=plan,
        dispositions=json.loads(
            (out_dir / "dispositions.json").read_text(encoding="utf-8")
        ),
        facts=first.document,
        ecosystem="python",
        repairer=prompts["targeted_repair"].sha256,
    )[0]
    s5_fingerprint = defect_fingerprint("review", None, "S5", s6.label, s6.fingerprint)

    re_slotted = _AUTHORING_REPLIES[0]["units"][0] | {"slot": "opening:alternate"}
    slot_change = {
        "causal_stage": "S6",
        "fingerprint": s6.fingerprint,
        "revised_output": {"units": [re_slotted], "omitted": []},
        "changes": [
            {
                "id": "R01",
                "path": "units[0].slot",
                "before": "opening",
                "after": "opening:alternate",
                "fact_ids": [],
            }
        ],
    }
    restated_plan = {
        "causal_stage": "S5",
        "fingerprint": s5_fingerprint,
        "revised_output": plan,
        "changes": [
            {
                "id": "R01",
                "path": "quick_start_example_id",
                "before": "example:001",
                "after": "example:001",
                "fact_ids": [],
            }
        ],
    }
    client = _FakeClient(
        [
            _completion(slot_change),
            _completion(slot_change),
            _completion(restated_plan),
            _completion(restated_plan),
        ]
    )
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    real_review = cascade_module.review_candidate
    reviews: list[ReviewVerdict] = []

    def review_once(**kwargs: Any) -> ReviewVerdict:
        verdict = (
            _injected_reject(quote=QUOTE) if not reviews else real_review(**kwargs)
        )
        reviews.append(verdict)
        return verdict

    monkeypatch.setattr(cascade_module, "review_candidate", review_once)

    settled = settle_candidate(
        entry.repository,
        "python",
        clone_path,
        facts_path=facts_path,
        out_dir=out_dir,
        config=CONFIG,
        registry_path=registry_path,
    )

    assert client.chat.completions.replies == []
    ledger = RepairLedger(out_dir / REPAIRS_FILENAME)
    assert ledger.attempts[s6.fingerprint]["outcome"] == "escalated"
    assert "planning decision" not in ledger.attempts[s6.fingerprint]["reason"]
    assert (
        "escalated once to a plan-level repair"
        in ledger.attempts[s6.fingerprint]["reason"]
    )
    assert ledger.attempts[s5_fingerprint]["outcome"] == "unrepairable"
    assert "unchanged" in ledger.attempts[s5_fingerprint]["reason"]
    assert settled.rounds == 1
    assert settled.result.review_verdict.verdict == "REJECT"
