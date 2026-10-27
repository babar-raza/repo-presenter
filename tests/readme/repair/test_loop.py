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
    keep_unflagged_units,
    refuse_noop,
    settle_candidate,
)
from repo_presenter.readme.repair.targeted import REPAIRS_FILENAME, RepairLedger
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import (
    Finding,
    Refutation,
    ReviewVerdict,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import (
    _AUTHORING_REPLIES,
    _AUTHORING_TEXT,
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
        kind="deterministic",
        message="injected by the test: the quoted sentence must be repaired",
        refuted_by=Refutation(rule="claim_contradiction", evidence="test fixture"),
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
    # The fixture's own real verdict is REJECT, for heading and code-block losses no repair here
    # can touch (deterministic sections). Those stay, unrepairable, after the settle as well.
    real_rules = {finding.rule for finding in first.review_verdict.findings}
    assert real_rules == {"disposition_coverage", "live_readme_loss"}
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
