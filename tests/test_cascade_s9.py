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
from repo_presenter.cascade import _run_reconciliation, _settle_defects, run_cascade
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger, load_records
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import merge_units
from repo_presenter.readme.repair.targeted import (
    REPAIRS_FILENAME,
    RepairLedger,
    validation_defects,
)
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


def test_an_uncited_omit_on_a_paragraph_is_rejected_and_reasked_not_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Java, hosted run 40723588078): S4's
    own job checks ran ``normalize`` alone, which has no quarrel with an OMIT_UNSUPPORTED that
    cites no fact (its whole claim is that none exists), so the reply was accepted unchanged. The
    content then surfaced three stages later as a deterministic "live content lost" block
    (independent_reviewer.live_readme_loss_rule), the one check built to catch this having never
    run. The job's checks must be reconcile_checks (normalize + placement_errors), which rejects
    an uncited OMIT_UNSUPPORTED on a paragraph and forces a real re-ask."""
    paragraph = "inherited_unit:001.paragraph"
    base = make_facts()
    facts = FactsDocument(
        base.repository,
        base.source_revision,
        (
            *(f for f in base.facts if f.kind != "inherited_unit"),
            Fact(
                paragraph,
                "inherited_unit",
                "The project layout follows a conventional Maven directory structure.",
                (Evidence("README.md", "section 'Widget > Project Structure'"),),
            ),
        ),
    )
    bad_reply = {
        "dispositions": [
            {
                "unit_id": paragraph,
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "The project layout is unsupported; no such fact exists.",
            }
        ]
    }
    fixed_reply = {
        "dispositions": [
            {
                "unit_id": paragraph,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "scope_limitations",
                "fact_ids": [],
                "rationale": "Kept as written; no fact contradicts it.",
            }
        ]
    }
    ledger = Ledger(tmp_path / "ledger.jsonl")
    store = CallStore(tmp_path / "calls")
    prompts = load_manifests(PROMPTS_PATH)
    client = _FakeClient([_completion(bad_reply), _completion(fixed_reply)])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
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
    # The bad reply was rejected and a second completion consumed: the final output is the FIXED
    # reply's disposition, not the unrepaired OMIT_UNSUPPORTED the model first returned.
    assert client.chat.completions.replies == []
    [entry] = stage["dispositions"]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "scope_limitations"


def test_a_moved_lead_in_follows_its_omitted_payload_not_left_stranded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Java, run 41068618078):
    coordinate_neighbor_promises exists, is correct and tested, but was never called from this
    orchestrator at all -- a lead-in paragraph ("Gradle (Groovy DSL):") was VERIFIED_MOVE into
    quick_start while the code block it introduces was independently OMIT_UNSUPPORTED with no
    destination, leaving the lead-in's colon with nothing following it in quick_start. BC-07's
    own dangling-colon check then blocked the candidate before it ever reached review."""
    lead = "inherited_unit:040.paragraph"
    payload = "inherited_unit:041.code_block"
    base = make_facts()
    facts = FactsDocument(
        base.repository,
        base.source_revision,
        (
            *(f for f in base.facts if f.kind != "inherited_unit"),
            Fact(
                lead, "inherited_unit", "Gradle (Groovy DSL):",
                (Evidence("README.md", "section 'Widget > Installation'"),),
            ),
            Fact(
                payload, "inherited_unit", "```groovy\nimplementation 'x:y:1.0'\n```",
                (Evidence("README.md", "section 'Widget > Installation'"),),
            ),
        ),
    )
    reply = {
        "dispositions": [
            {
                "unit_id": lead,
                "disposition": "VERIFIED_MOVE",
                "destination_section": "quick_start",
                "fact_ids": [],
                "rationale": "Introduces the Gradle example in quick_start.",
            },
            {
                "unit_id": payload,
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": ["package:name"],
                "rationale": "Redundant with the verified package fact.",
            },
        ]
    }
    ledger = Ledger(tmp_path / "ledger.jsonl")
    store = CallStore(tmp_path / "calls")
    prompts = load_manifests(PROMPTS_PATH)
    client = _FakeClient([_completion(reply)])
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
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
    by_unit = {entry["unit_id"]: entry for entry in stage["dispositions"]}
    # The lead-in follows its payload into omission rather than being left moved alone.
    assert by_unit[lead]["disposition"] == "OMIT_UNSUPPORTED"
    assert by_unit[lead]["destination_section"] is None


# --- S9: the render's unprinted kept units are accounted --------------------------------------

README_WITH_SUBHEADING = README + "\n### Main\n"
SUBHEADING = "inherited_unit:007.heading"


def _reply_keeping_code_without_an_example() -> dict[str, Any]:
    """The fixture's reconciliation, except the quick-start code block is kept citing no example.
    The renderer prints no such block, and with no SUPPORTED example to cite the accounting cannot
    say it is redundant: it stays a defect for the S4 repair, which is what these tests drive."""
    dispositions = [dict(entry) for entry in _RECONCILIATION_REPLY["dispositions"]]
    for entry in dispositions:
        if entry["unit_id"] == CODE:
            entry["fact_ids"] = []
    return {"dispositions": dispositions}


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

    # The fixture's quick-start code block cites the SUPPORTED example the renderer prints it from,
    # so it is accounted too; the sub-heading is the case under test.
    assert [item.unit_id for item in result.accounted] == [CODE, SUBHEADING]
    entry = _by_unit(run.json("dispositions.json"))[SUBHEADING]
    assert (entry["disposition"], entry["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "api_reference",
    )
    assert entry["fact_ids"] == ["public_symbol:aspose_widget_foss.widget"]
    assert [a["unit_id"] for a in run.json("accounting.json")["accounted"]] == [
        CODE,
        SUBHEADING,
    ]
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
    first = run.first_pass(_first_replies(_reply_keeping_code_without_an_example()))
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
    first = run.first_pass(_first_replies(_reply_keeping_code_without_an_example()))
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


def test_a_failure_routed_to_any_of_s4_s5_s6_reaches_the_settle_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real hosted gap (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, runs 40571540396 and
    40679621466): BC-12 failed identically both runs with causal_stage COMPOSING on
    'development_testing', an LLM-owned section -- ``validation_defects`` routes that to S6, the
    same stage ``repair_defect`` already revises a reviewer's own S6 finding by, yet the settle
    loop discarded every non-S4 defect before a repair was ever attempted. A BC-07 failure naming
    no section (``section_id: None``) still cannot be routed to any LLM-owned section and so still
    falls out -- this proves the fix widens which *repairable* stage reaches the loop, not that
    everything now repairs."""
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
            {
                "id": "BC-12",
                "name": "Every product-name position spells the registry's canonical "
                "product name",
                "verdict": "FAIL",
                "causal_stage": "COMPOSING",
                "details": ["product name 'Widget FOSS' is not the canonical name"],
                "failures": [
                    {
                        "section_id": "opening",
                        "causal_stage": "COMPOSING",
                        "detail": "product name 'Widget FOSS' is not the canonical name",
                    }
                ],
            },
        ],
    }
    no_findings = ReviewVerdict(verdict="ACCEPT", findings=())
    defects = _settle_defects(
        composed=composed,
        validation=validation,
        verdict=no_findings,
        entry=run.entry,
        document=first.document,
        prompts=load_manifests(PROMPTS_PATH),
    )
    assert [(d.source, d.label, d.stage) for d in defects] == [
        ("validation", "BC-05", "S4"),
        ("validation", "BC-12", "S6"),
    ]


# --- S9: a BC-12 structural defect now gets the same bounded repair chance as S4 -----------------

# scope_limitations, not opening: the opening paragraph sits before the shell's first "## "
# heading, so ``validation/text.py::located`` can never attribute a failure in it to a section
# (always None, by this shell's own design) -- not an LLM-owned section ``validation_defects`` can
# route to, regardless of this fix. scope_limitations has a real heading, exactly like the real
# hosted finding's own section ('development_testing').
_SCOPE_SLOT_INDEX = 4
_BC12_TEXT = "Aspose.Widget FOSS for Py avoids any native build dependency for the reader."
_BC12_FIXED_TEXT = "The library avoids any native build dependency for the reader."
_BC12_STILL_WRONG_TEXT = "Aspose.Widget FOSS for Py requires no native build dependency at all."


def _scope_reply_with_text(text: str) -> dict[str, Any]:
    reply = json.loads(json.dumps(_AUTHORING_REPLIES[_SCOPE_SLOT_INDEX]))
    reply["units"][0]["text"] = text
    return reply


def _replies_with_scope_text(text: str) -> list[dict[str, Any]]:
    """The fixture's 9 replies, with the scope_limitations unit's text replaced and the coherence
    batch's own echo rebuilt from that same text -- the violation must survive coherence
    unchanged, or it would never reach BC-12 at all."""
    replies = _first_replies()
    scope = _scope_reply_with_text(text)
    replies[3 + _SCOPE_SLOT_INDEX] = scope
    authoring = [*replies[3:7], scope]
    merged = merge_units(dict(zip(LABELS, authoring, strict=True)))
    replies[8] = {"units": merged["units"], "omitted": []}
    return replies


def _bc12_defect(run: _Run) -> Any:
    validation = run.json("validation.json")
    units = run.json("content_units.coherent.json")["units"]
    llm_sections = {str(unit["section"]) for unit in units if unit.get("section")}
    prompts = load_manifests(PROMPTS_PATH)
    [defect] = [
        d
        for d in validation_defects(validation, llm_sections, prompts["targeted_repair"].sha256)
        if d.label == "BC-12"
    ]
    return defect


def _bc12_repair_reply(fingerprint: str, before: str, after: str) -> dict[str, Any]:
    scope = _scope_reply_with_text(after)["units"]
    return {
        "causal_stage": "S6",
        "fingerprint": fingerprint,
        "revised_output": {"units": scope, "omitted": []},
        "changes": [
            {"id": "R01", "path": "units[0].text", "before": before, "after": after, "fact_ids": []}
        ],
    }


def _bc12_coherence_echo(text: str) -> dict[str, Any]:
    authoring = [*_AUTHORING_REPLIES[:_SCOPE_SLOT_INDEX], _scope_reply_with_text(text)]
    merged = merge_units(dict(zip(LABELS, authoring, strict=True)))
    return {"units": merged["units"], "omitted": []}


def test_a_structural_defect_is_now_repaired_the_same_way_an_s4_defect_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The falsifier for the real hosted gap: before this fix, a BC-12 structural failure got no
    repair attempt at all (``_s4_defects`` dropped every non-S4 stage), so ``repairs.json`` stayed
    empty and the candidate was permanently BLOCKED on the first pass, exactly as both hosted
    Aspose.Cells-FOSS-for-Cpp runs (40571540396, 40679621466) show. After the fix the same
    structural finding gets ONE bounded repair attempt, by the same ``S6`` section-authoring
    mechanism a reviewer's own finding already used -- never loosening BC-12 itself, which still
    judges the recomposed README on its own next pass."""
    run = _Run(tmp_path, monkeypatch)
    first = run.first_pass(_replies_with_scope_text(_BC12_TEXT))
    bc12 = next(c for c in run.json("validation.json")["checks"] if c["id"] == "BC-12")
    assert bc12["verdict"] == "FAIL"
    assert first.rounds == 1
    assert not (run.out / REPAIRS_FILENAME).exists()  # max_rounds=1: no attempt is made yet
    defect = _bc12_defect(run)
    assert defect.stage == "S6"

    client = run.script(
        [
            _bc12_repair_reply(defect.fingerprint, _BC12_TEXT, _BC12_FIXED_TEXT),
            _bc12_coherence_echo(_BC12_FIXED_TEXT),
        ]
    )
    second = run.cascade()

    assert client.chat.completions.replies == []
    assert second.rounds == 2
    attempt = RepairLedger(run.out / REPAIRS_FILENAME).attempts[defect.fingerprint]
    assert (attempt["outcome"], attempt["stage"]) == ("repaired", "S6")
    written = run.json("validation.json")
    assert next(c for c in written["checks"] if c["id"] == "BC-12")["verdict"] == "PASS"
    assert _BC12_FIXED_TEXT in (run.out / "README.coherent.md").read_text(encoding="utf-8")




def test_a_repair_that_still_fails_bc12_blocks_again_and_is_never_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: BC-12 is never loosened to make the repair's own acceptance easier. The
    repair's checks (``unit_checks``, same as authoring) do not re-run BC-12 -- that is
    ``validate_candidate``'s job, on the README the NEXT pass recomposes from the repaired text.
    A reworded reply that still spells the name wrong genuinely changes the text (so it is not a
    no-op) and satisfies ``unit_checks``, so the repair ledger truthfully records it as
    'repaired' -- but BC-12 itself still fails on the recomposed README, the defect is re-raised,
    and its one spent fingerprint is never given a second attempt."""
    run = _Run(tmp_path, monkeypatch)
    first = run.first_pass(_replies_with_scope_text(_BC12_TEXT))
    defect = _bc12_defect(run)

    client = run.script(
        [
            _bc12_repair_reply(defect.fingerprint, _BC12_TEXT, _BC12_STILL_WRONG_TEXT),
            _bc12_coherence_echo(_BC12_STILL_WRONG_TEXT),
        ]
    )
    second = run.cascade()

    assert client.chat.completions.replies == []
    assert second.rounds == 2
    attempt = RepairLedger(run.out / REPAIRS_FILENAME).attempts[defect.fingerprint]
    assert attempt["outcome"] == "repaired"  # the repair's own checks do not judge BC-12
    assert attempt["re_raised"] == [defect.label]  # but it blocks again the very next pass
    bc12 = next(c for c in run.json("validation.json")["checks"] if c["id"] == "BC-12")
    assert bc12["verdict"] == "FAIL"  # validate_candidate's own BC-12 was never weakened
