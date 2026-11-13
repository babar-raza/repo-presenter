"""BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR (project/state.yaml): one process runs the whole S3-S8
cascade under one Invocation/Ledger. The one property no per-script test could ever prove is
exercised directly here: every one of the 9 real provider calls this test makes (investigation,
reconciliation, planning, 5 authoring tasks, 1 coherence batch) lands in the SAME ledger file
under the SAME invocation_id -- the exact thing seal.py's no-op proof needs and the six separate
scripts could never give it.

No network call is made: ``repo_presenter.core.llm.jobs.transport.build_client`` is monkeypatched
to a fake client returning scripted completions, following tests/core/llm/test_jobs.py's own
pattern. Every scripted reply is schema-and-check-valid against this repository's REAL prompt
manifests (loaded from the real prompts/ directory) and REAL stage logic (investigation_schema,
reconciliation_schema, planning_schema + plan_checks, authoring_schema + unit_checks,
coherence_schema + coherence_checks) -- derived by actually running each stage against this
fixture first, not guessed, so this proves the orchestrator's wiring, not a relaxed stand-in.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.cascade import run_cascade
from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.facts import read_facts, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.ledger import load_records
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.review.independent_reviewer import load_review_verdict
from tests.readme.composition.synthetic import make_entry, make_facts

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")

README = """# Aspose Widget

A widget you can render.

## Usage

```python
import aspose_widget_foss
```

## Limitations

Only PNG output is currently supported.
"""


def _completion(content: dict[str, Any], model: str = "qwen3-next") -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model=model, id="req", usage=usage)


class _FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = replies

    def create(self, **payload: Any) -> Any:
        return self.replies.pop(0)


class _FakeClient:
    def __init__(self, replies: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(replies))


# Every reply below was confirmed, by actually running it through run_job against this exact
# fixture, to be accepted on the FIRST attempt (zero retries, zero narrowed re-asks) -- so this
# test's own expected provider-call count (9) is a measured fact, not an estimate.
_INVESTIGATION_REPLY = {
    "product_summary": {"text": "A widget library.", "fact_ids": ["package:name"]},
    "audience": {"text": "Python developers.", "fact_ids": ["identity:ecosystem"]},
    "problems_solved": [{"text": "Rendering widgets is tedious.", "fact_ids": ["package:name"]}],
    "workflows": [],
    "capabilities": [
        {
            "title": "Render",
            "text": "Build and render a widget.",
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        },
        {"title": "Install", "text": "Install from PyPI.", "fact_ids": ["install_command:pip"]},
        {"title": "License", "text": "MIT licensed.", "fact_ids": ["license:spdx"]},
    ],
    "limitations": [
        {"text": "Only PNG output is currently supported.", "fact_ids": ["package:name"]}
    ],
    "uncertainties": [],
}

_RECONCILIATION_REPLY = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:001.heading", "disposition": "NON_CONTENT",
            "destination_section": None, "fact_ids": [], "rationale": "heading, not content",
        },
        {
            "unit_id": "inherited_unit:002.paragraph", "disposition": "VERIFIED_PRESERVE",
            "destination_section": "opening", "fact_ids": ["package:name"],
            "rationale": "accurate opening",
        },
        {
            "unit_id": "inherited_unit:003.heading", "disposition": "NON_CONTENT",
            "destination_section": None, "fact_ids": [], "rationale": "heading, not content",
        },
        {
            "unit_id": "inherited_unit:004.code_block", "disposition": "VERIFIED_PRESERVE",
            "destination_section": "quick_start", "fact_ids": ["example:001"],
            "rationale": "matches example",
        },
        {
            "unit_id": "inherited_unit:005.heading", "disposition": "NON_CONTENT",
            "destination_section": None, "fact_ids": [], "rationale": "heading, not content",
        },
        {
            "unit_id": "inherited_unit:006.paragraph", "disposition": "VERIFIED_PRESERVE",
            "destination_section": "scope_limitations", "fact_ids": ["package:name"],
            "rationale": "real limitation",
        },
    ]
}

_PLANNING_REPLY = {
    "core_capabilities": [
        {
            "title": "Render widgets",
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"], "shared_fact_ids": [],
        },
        {"title": "Install with pip", "fact_ids": ["install_command:pip"], "shared_fact_ids": []},
        {"title": "MIT licensed", "fact_ids": ["license:spdx"], "shared_fact_ids": []},
    ],
    "quick_start_example_id": "example:001",
    "second_quick_start_example_id": None,
    "additional_example_ids": [],
    "flagship_example_id": None,
    "api_hubs": [
        {
            "symbol_fact_id": "public_symbol:aspose_widget_foss.widget",
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        }
    ],
    "material_limitations": [],
    "links": [],
    "deviations": [],
    "at_a_glance": {
        "input_format_ids": [], "output_format_ids": [],
        "capability_titles": ["Render widgets", "Install with pip", "MIT licensed"],
    },
}

_AUTHORING_TEXT = "This writes plain prose for a real reader with no jargon or internal names."


def _authoring_reply(slots_and_fact_ids: list[tuple[str, str, list[str]]]) -> dict[str, Any]:
    return {
        "units": [
            {"section": section, "slot": slot, "text": _AUTHORING_TEXT, "fact_ids": fact_ids}
            for section, slot, fact_ids in slots_and_fact_ids
        ],
        "omitted": [],
    }


# One reply per authoring task, in authoring_tasks()'s own order for this fixture's real plan.
_AUTHORING_REPLIES = [
    _authoring_reply([("opening", "opening", ["package:name"])]),
    _authoring_reply(
        [
            ("key_capabilities", "capability:1", ["public_symbol:aspose_widget_foss.widget"]),
            ("key_capabilities", "capability:2", ["install_command:pip"]),
            ("key_capabilities", "capability:3", ["license:spdx"]),
        ]
    ),
    _authoring_reply([("quick_start", "lead_in", ["example:001"])]),
    _authoring_reply(
        [
            ("api_reference", "intro", ["public_symbol:aspose_widget_foss.widget"]),
            (
                "api_reference",
                "hub:public_symbol:aspose_widget_foss.widget",
                ["public_symbol:aspose_widget_foss.widget"],
            ),
        ]
    ),
    _authoring_reply(
        [
            ("scope_limitations", "scope", ["package:name"]),
            ("scope_limitations", "limitation:1", ["inherited_unit:006.paragraph"]),
        ]
    ),
]


@pytest.fixture
def clone_path(tmp_path: Path) -> Path:
    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "README.md").write_text(README, encoding="utf-8", newline="\n")
    return clone


@pytest.fixture(autouse=True)
def _fixed_git_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_cascade reads the source revision via run_git; the fixture clone is never a real git
    repository, so stand in with a fixed revision rather than needing a real `git init`."""
    import repo_presenter.cascade as cascade_module

    monkeypatch.setattr(
        cascade_module, "run_git", lambda *a, **k: SimpleNamespace(stdout="f" * 40 + "\n")
    )


def _scripted_replies() -> list[Any]:
    """The 9 real calls this fixture makes, in authoring_tasks()'s own order. Coherence echoes
    the authored units back unchanged -- a trivially valid no-op revision against
    coherence_schema's own minItems=maxItems=len(existing) shape."""
    from repo_presenter.readme.composition.authoring import merge_units

    labels = ["opening", "key_capabilities", "quick_start", "api_reference", "scope_limitations"]
    merged_units = merge_units(dict(zip(labels, _AUTHORING_REPLIES)))
    return [
        _completion(_INVESTIGATION_REPLY),
        _completion(_RECONCILIATION_REPLY),
        _completion(_PLANNING_REPLY),
        *[_completion(r) for r in _AUTHORING_REPLIES],
        _completion({"units": merged_units["units"], "omitted": []}),
    ]


def _write_registry(path: Path, *entries) -> None:
    from repo_presenter.core.registry.models import Registry

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(Registry(entries=tuple(entries)).model_dump_json(), encoding="utf-8")


def test_run_cascade_produces_every_artifact_under_one_shared_invocation(
    tmp_path: Path, clone_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = tmp_path / "registry.json"
    _write_registry(registry_path, entry)
    out_dir = tmp_path / "out"

    client = _FakeClient(_scripted_replies())
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    result = run_cascade(
        entry.repository, "python", clone_path, facts_path=facts_path, out_dir=out_dir,
        config=CONFIG, registry_path=registry_path, max_rounds=1,
    )

    assert result.repository == entry.repository
    assert result.provider_calls == 9

    for name in (
        "investigation.json", "dispositions.json", "plan.json", "content_units.json",
        "content_units.coherent.json", "README.rendered.md", "README.coherent.md",
        "README.patch.diff", "review_verdict.json",
    ):
        assert (out_dir / name).is_file(), f"missing {name}"

    # The one property only a real orchestrator can give: every call this run made is in the
    # SAME ledger file, under the SAME invocation_id -- never five separate ledgers.
    ledger_path = out_dir / "llm_cache" / "ledger.jsonl"
    records = load_records(ledger_path)
    assert len(records) == 9
    assert {record.invocation_id for record in records} == {result.invocation.invocation_id}

    invocation_record_path = (
        out_dir / "llm_cache" / "invocations" / f"{result.invocation.invocation_id}.json"
    )
    assert invocation_record_path.is_file()

    updated_facts = read_facts(facts_path)
    assert any(f.kind == "inherited_unit" for f in updated_facts.facts)

    verdict = load_review_verdict(out_dir / "review_verdict.json")
    assert verdict.verdict in ("ACCEPT", "REJECT")
