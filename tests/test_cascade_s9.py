"""S4 normalisation, S9 accounting and the bounded S4 repair inside ``run_cascade``, offline.

The measured case is the hosted run of aspose-3d-foss/Aspose.3D-FOSS-for-.NET: the cascade ran S4
without ``dispositions.normalize`` and had no S9 stage, so a kept unit the renderer could not print
stood as kept and the reviewer REJECTed it. Each test here drives the real cascade over the
fixture ``tests/test_cascade.py`` defines, through a fake client with scripted replies, and holds a
negative control beside the behaviour it proves.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.cascade import _run_reconciliation, _s4_defects, run_cascade
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger, load_records
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import merge_units
from repo_presenter.readme.repair.targeted import REPAIRS_FILENAME, RepairLedger
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import (
    ReviewVerdict,
    live_readme_loss_rule,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import (
    _AUTHORING_REPLIES,
    _PLANNING_REPLY,
    _RECONCILIATION_REPLY,
    CONFIG,
    README,
    _completion,
    _FakeClient,
    _scripted_replies,
    _write_registry,
)

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "prompts"
CODE = "inherited_unit:004.code_block"
LABELS = [
    "opening",
    "key_capabilities",
    "quick_start",
    "api_reference",
    "scope_limitations",
]


@pytest.fixture(autouse=True)
def _fixed_git_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cascade_module,
        "run_git",
        lambda *a, **k: SimpleNamespace(stdout="f" * 40 + "\n"),
    )


class _Run:
    """One output directory, one registry, one clone: the arguments every run shares."""

    def __init__(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, readme: str = README
    ) -> None:
        plugin_for("python")
        self.entry = make_entry()
        self.monkeypatch = monkeypatch
        self.clone = tmp_path / "clone"
        self.clone.mkdir(parents=True)
        (self.clone / "README.md").write_text(readme, encoding="utf-8", newline="\n")
        self.facts_path = tmp_path / "facts.json"
        write_facts(make_facts(), self.facts_path)
        self.registry = tmp_path / "registry.json"
        _write_registry(self.registry, self.entry)
        self.out = tmp_path / "out"

    def script(self, replies: list[dict[str, Any]]) -> _FakeClient:
        client = _FakeClient([_completion(reply) for reply in replies])
        self.monkeypatch.setattr(
            jobs_module.transport, "build_client", lambda config: client
        )
        return client

    def cascade(self, **kwargs: Any) -> Any:
        return run_cascade(
            self.entry.repository,
            "python",
            self.clone,
            facts_path=self.facts_path,
            out_dir=self.out,
            config=CONFIG,
            registry_path=self.registry,
            **kwargs,
        )

    def first_pass(self, replies: list[dict[str, Any]] | None = None) -> Any:
        client = self.script(replies if replies is not None else _first_replies())
        result = self.cascade(max_rounds=1)
        assert client.chat.completions.replies == []
        return result

    def json(self, name: str) -> dict[str, Any]:
        return json.loads((self.out / name).read_text(encoding="utf-8"))


def _first_replies(
    reconciliation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """The nine replies of ``tests/test_cascade.py``'s fixture, as the dicts they carry."""
    replies = [
        json.loads(reply.choices[0].message.content) for reply in _scripted_replies()
    ]
    if reconciliation is not None:
        replies[1] = reconciliation
    return replies


def _by_unit(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in document["dispositions"]}


def _rules(result: Any) -> list[str]:
    return [finding.rule for finding in result.review_verdict.findings]


# --- S4: dispositions.normalize runs on the hosted path ---------------------------------------


def test_the_s4_stage_normalizes_what_the_model_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The model keeps the lead paragraph as written in the opening; the opening is authored from
    facts and replaces the lead paragraph, which ``normalize`` knows and the model was not asked."""
    run = _Run(tmp_path, monkeypatch)
    raw = _by_unit(_RECONCILIATION_REPLY)["inherited_unit:002.paragraph"]
    assert raw["disposition"] == "VERIFIED_PRESERVE"
    run.first_pass()
    stored = _by_unit(run.json("dispositions.json"))
    assert (
        stored["inherited_unit:002.paragraph"]["disposition"] == "SUPERSEDE_REDUNDANT"
    )
    # negative control: a disposition normalize has no quarrel with is the model's, unchanged
    assert (
        stored["inherited_unit:006.paragraph"]
        == _by_unit(_RECONCILIATION_REPLY)["inherited_unit:006.paragraph"]
    )


def test_a_superseded_dependency_heading_gains_the_fact_that_accounts_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The measured 'Development Dependencies' finding: S4 superseded the heading into the
    Dependencies section but cited no fact, and the reviewer's loss rule accepts an accounting
    disposition only with a fact and a rationale."""
    heading = "inherited_unit:001.heading"
    base = make_facts()
    facts = FactsDocument(
        base.repository,
        base.source_revision,
        (
            *(f for f in base.facts if f.kind != "inherited_unit"),
            Fact("dependency:none", "dependency", "none", (Evidence("setup.py"),)),
            Fact(
                heading,
                "inherited_unit",
                "### Development Dependencies",
                (Evidence("README.md", "section 'Widget > Development Dependencies'"),),
            ),
        ),
    )
    reply = {
        "dispositions": [
            {
                "unit_id": heading,
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "dependencies",
                "fact_ids": [],
                "rationale": "The Dependencies section renders this heading.",
            }
        ]
    }
    ledger = Ledger(tmp_path / "ledger.jsonl")
    store = CallStore(tmp_path / "calls")
    prompts = load_manifests(PROMPTS_PATH)
    monkeypatch.setattr(
        jobs_module.transport,
        "build_client",
        lambda config: _FakeClient([_completion(reply)]),
    )
    stage = _run_reconciliation(
        entry=make_entry(),
        document=facts,
        investigation={},
        prompts=prompts,
        config=CONFIG,
        ledger=ledger,
        store=store,
        context=JobContext(make_entry().repository, facts.source_revision),
    )
    [entry] = stage["dispositions"]
    assert entry["fact_ids"] == ["dependency:none"]
    original = "### Development Dependencies\n"
    lost_before = live_readme_loss_rule(
        original, "# Widget\n", facts=facts, dispositions=reply
    )
    lost_after = live_readme_loss_rule(
        original, "# Widget\n", facts=facts, dispositions=stage
    )
    assert [f.quote for f in lost_before] == ["Development Dependencies"]
    assert lost_after == []


# --- S9: the render's unprinted kept units are accounted --------------------------------------

README_WITH_SUBHEADING = README + "\n### Main\n"
SUBHEADING = "inherited_unit:007.heading"


def _reply_keeping_a_subheading() -> dict[str, Any]:
    dispositions = [dict(entry) for entry in _RECONCILIATION_REPLY["dispositions"]]
    dispositions.append(
        {
            "unit_id": SUBHEADING,
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "api_reference",
            "fact_ids": [],
            "rationale": "the API sub-heading",
        }
    )
    return {"dispositions": dispositions}


def test_a_kept_subheading_the_renderer_does_not_print_is_accounted_by_the_cascade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch, README_WITH_SUBHEADING)
    result = run.first_pass(_first_replies(_reply_keeping_a_subheading()))

    assert [item.unit_id for item in result.accounted] == [SUBHEADING]
    entry = _by_unit(run.json("dispositions.json"))[SUBHEADING]
    assert (entry["disposition"], entry["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "api_reference",
    )
    assert entry["fact_ids"] == ["public_symbol:aspose_widget_foss.widget"]
    assert run.json("accounting.json")["accounted"][0]["unit_id"] == SUBHEADING
    assert not any("'Main'" in f.message for f in result.review_verdict.findings)
    assert "Main" not in (run.out / "README.coherent.md").read_text(encoding="utf-8")


def test_without_the_accounting_stage_the_same_run_is_rejected_for_the_subheading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The falsifier: stub the stage out and the reviewer's two findings on the sub-heading return
    (``disposition_coverage`` and ``live_readme_loss``) with the README unchanged."""
    run = _Run(tmp_path, monkeypatch, README_WITH_SUBHEADING)
    with_accounting = run.first_pass(_first_replies(_reply_keeping_a_subheading()))
    readme = (run.out / "README.coherent.md").read_text(encoding="utf-8")

    other = _Run(tmp_path / "other", monkeypatch, README_WITH_SUBHEADING)
    monkeypatch.setattr(
        cascade_module,
        "account_unprinted_units",
        lambda candidate: (candidate.dispositions, []),
    )
    without = other.first_pass(_first_replies(_reply_keeping_a_subheading()))

    assert (other.out / "README.coherent.md").read_text(encoding="utf-8") == readme
    messages = [f.message for f in without.review_verdict.findings]
    assert any(SUBHEADING in m for m in messages)
    assert any("heading 'Main'" in m for m in messages)
    assert not any(
        SUBHEADING in f.message for f in with_accounting.review_verdict.findings
    )


def test_the_cascade_writes_the_blocking_checks_it_ran(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch)
    result = run.first_pass()
    written = run.json("validation.json")
    assert written == result.validation
    assert {check["id"] for check in written["checks"]} >= {
        "BC-01",
        "BC-05",
        "BC-07",
        "BC-12",
    }
    assert next(c for c in written["checks"] if c["id"] == "BC-01")["verdict"] == "PASS"


# --- S9: a failure whose cause is S4 is repaired as a bounded patch ----------------------------


def _s4_defect(run: _Run, result: Any) -> Any:
    prompts = load_manifests(PROMPTS_PATH)
    [defect] = [
        d
        for d in build_defects(
            result.review_verdict,
            units=run.json("content_units.coherent.json")["units"],
            plan=run.json("plan.json"),
            dispositions=run.json("dispositions.json"),
            facts=result.document,
            ecosystem="python",
            repairer=prompts["targeted_repair"].sha256,
        )
        if d.stage == "S4"
    ]
    return defect


def _rewrite_reply(fingerprint: str) -> dict[str, Any]:
    return {
        "causal_stage": "S4",
        "fingerprint": fingerprint,
        "revised_output": {
            "dispositions": [
                {
                    "unit_id": CODE,
                    "disposition": "VERIFIED_REWRITE",
                    "destination_section": "quick_start",
                    "fact_ids": ["example:001"],
                    "rationale": "The Quick Start section prints this verified example.",
                }
            ]
        },
        "changes": [
            {
                "id": "R01",
                "path": "dispositions.3",
                "before": "",
                "after": "",
                "fact_ids": [],
            }
        ],
    }


def _second_round_replies() -> list[dict[str, Any]]:
    merged = merge_units(dict(zip(LABELS, _AUTHORING_REPLIES, strict=True)))
    return [
        _PLANNING_REPLY,
        *_AUTHORING_REPLIES,
        {"units": merged["units"], "omitted": []},
    ]


def test_a_kept_unit_the_render_cannot_print_is_repaired_once_and_the_cascade_runs_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch)
    first = run.first_pass()
    assert "disposition_coverage" in _rules(first)
    assert first.rounds == 1
    defect = _s4_defect(run, first)

    client = run.script([_rewrite_reply(defect.fingerprint), *_second_round_replies()])
    second = run.cascade()

    assert second.rounds == 2
    assert "disposition_coverage" not in _rules(second)
    attempt = RepairLedger(run.out / REPAIRS_FILENAME).attempts[defect.fingerprint]
    assert (attempt["outcome"], attempt["stage"]) == ("repaired", "S4")
    # only the repair and what it changed were asked: the plan is asked again, nothing else is
    assert second.provider_calls == 2
    assert len(client.chat.completions.replies) == len(_second_round_replies()) - 1
    # one invocation made every call of the second run, the repair included
    records = [
        r
        for r in load_records(run.out / "llm_cache" / "ledger.jsonl")
        if r.invocation_id == second.invocation.invocation_id
    ]
    assert sorted(r.job for r in records if r.disposition != "cache_reuse") == [
        "presentation_planning",
        "targeted_repair",
    ]
    assert (
        _by_unit(run.json("dispositions.json"))[CODE]["disposition"]
        == "VERIFIED_REWRITE"
    )


def test_the_repair_is_not_made_when_the_caller_allows_one_round(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch)
    run.first_pass()
    client = run.script([])
    again = run.cascade(max_rounds=1)
    assert again.provider_calls == 0 and again.rounds == 1
    assert client.chat.completions.replies == []
    assert not (run.out / REPAIRS_FILENAME).exists()


def test_a_defect_is_attempted_once_and_a_refused_repair_is_never_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch)
    first = run.first_pass()
    defect = _s4_defect(run, first)
    # the reply keeps the unit as written, which prints the quoted text: refused, twice
    kept = _rewrite_reply(defect.fingerprint)
    kept["revised_output"]["dispositions"][0]["disposition"] = "VERIFIED_PRESERVE"

    client = run.script([kept, kept])
    second = run.cascade()
    assert second.rounds == 1  # nothing was repaired, so no second pass
    assert client.chat.completions.replies == []
    attempt = RepairLedger(run.out / REPAIRS_FILENAME).attempts[defect.fingerprint]
    assert attempt["outcome"] == "unrepairable"

    third_client = run.script([])
    third = run.cascade()
    assert third.provider_calls == 0
    assert third_client.chat.completions.replies == []
    assert (
        "re_raised"
        in RepairLedger(run.out / REPAIRS_FILENAME).attempts[defect.fingerprint]
    )


def test_only_a_failure_whose_cause_is_reconciliation_reaches_the_s4_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _Run(tmp_path, monkeypatch)
    first = run.first_pass()
    composed = SimpleNamespace(
        coherent_units=run.json("content_units.coherent.json"),
        plan=run.json("plan.json"),
        dispositions=run.json("dispositions.json"),
    )
    validation = {
        "validator_version": "",
        "checks": [
            {
                "id": "BC-05",
                "name": "dispositions",
                "verdict": "FAIL",
                "causal_stage": "RECONCILING",
                "details": ["x"],
                "failures": [
                    {
                        "section_id": None,
                        "causal_stage": "RECONCILING",
                        "detail": "x",
                        "unit_id": CODE,
                    }
                ],
            },
            {
                "id": "BC-07",
                "name": "structure",
                "verdict": "FAIL",
                "causal_stage": "COMPOSING",
                "details": ["y"],
                "failures": [
                    {"section_id": None, "causal_stage": "COMPOSING", "detail": "y"}
                ],
            },
        ],
    }
    no_findings = ReviewVerdict(verdict="ACCEPT", findings=())
    defects = _s4_defects(
        composed=composed,
        validation=validation,
        verdict=no_findings,
        entry=run.entry,
        document=first.document,
        prompts=load_manifests(PROMPTS_PATH),
    )
    assert [(d.source, d.label, d.stage) for d in defects] == [
        ("validation", "BC-05", "S4")
    ]
