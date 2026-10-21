"""Dependency evaluation: each changed class names the state it reopens; nothing changed is NONE.

Adapted from the old repository-presenter project's
``tests/components/readme/bundle/test_evaluation.py``. Ported: every test built on the hand-typed
``SEALED`` fixture (pure dict comparisons, no fixtures of their own) -- including the full
consumed-scope subsetting section, the part of mission §8's contract this component exists to
prove. Dropped: ``_real_dependency_record``-based tests (need
``components/readme/bundle/seal.py``'s ``upstream_dependencies`` + ``core/llm/prompts.py``) and
the toolchain tests (need ``core/toolchains.py``) -- neither pulled into this repository yet (see
``repo_presenter.readme.bundle.recheck``'s module docstring for the same gap).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from repo_presenter.readme.bundle.evaluation import (
    Change,
    evaluate,
    evaluation_document,
    summarize_evaluation,
    write_evaluation,
)

SEALED: dict[str, Any] = {
    "schema_version": 1,
    "source": {"revision": "a" * 40, "tree_sha256": "t" * 64},
    "environment": {
        "python_version": "3.13.2",
        "os": "Windows",
        "extractor_version": "1",
        "inherited_units_version": "1",
        "presenter_site_manifest": "e" * 64,
    },
    "facts": {"identity:repository": "1" * 64, "format:output.glb": "2" * 64},
    "prompts": {
        "repository_investigation": {
            "sha256": "i" * 64,
            "version": "1",
            "model_route": "qwen3-next",
        },
        "source_reconciliation": {"sha256": "r" * 64, "version": "1", "model_route": "qwen3-next"},
        "presentation_planning": {"sha256": "p" * 64, "version": "1", "model_route": "qwen3-next"},
        "section_authoring": {"sha256": "s" * 64, "version": "1", "model_route": "qwen3-next"},
        "independent_review": {"sha256": "v" * 64, "version": "2", "model_route": "qwen3-next"},
        "targeted_repair": {"sha256": "x" * 64, "version": "2", "model_route": "qwen3-next"},
    },
    "contract_version": "readme-contract-v1-draft",
    "components": {"shell": "1", "renderer": "1", "normalisation": "1", "reviewer_logic": "1"},
    "validators": {"BC-01": "1", "BC-02": "1"},
    "validator_version": "1",
    "acceptance_profile_version": None,
    "policy": {"version": "1", "sha256": "y" * 64},
    "protected_content_fingerprint": "f" * 64,
}


def _current(**overrides: Any) -> dict[str, Any]:
    current = copy.deepcopy(SEALED)
    del current["protected_content_fingerprint"]
    for path, value in overrides.items():
        target = current
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return current


def test_an_unchanged_input_set_is_none() -> None:
    evaluation = evaluate(SEALED, _current())
    assert evaluation.changes == () and evaluation.earliest == "NONE"
    document = evaluation_document("a" * 40, evaluation)
    assert document["earliest_affected_stage"] == "NONE" and document["changes"] == []
    assert summarize_evaluation(document) == "earliest affected stage NONE; 0 changes"


def test_each_dependency_class_names_the_state_it_reopens() -> None:
    cases = {
        "source__revision": ("source", "EXTRACTING"),
        "environment__python_version": ("environment.python_version", "EXTRACTING"),
        "environment__extractor_version": ("environment.extractor_version", "EXTRACTING"),
        "environment__inherited_units_version": (
            "environment.inherited_units_version",
            "EXTRACTING",
        ),
        "facts__format:output.glb": ("facts", "EXTRACTING"),
        "prompts__repository_investigation__sha256": (
            "prompts.repository_investigation",
            "INVESTIGATING",
        ),
        "prompts__source_reconciliation__version": ("prompts.source_reconciliation", "RECONCILING"),
        "prompts__presentation_planning__model_route": (
            "prompts.presentation_planning",
            "PLANNING",
        ),
        "prompts__section_authoring__sha256": ("prompts.section_authoring", "COMPOSING"),
        "prompts__independent_review__sha256": ("prompts.independent_review", "REVIEWING"),
        "prompts__targeted_repair__sha256": ("prompts.targeted_repair", "REVIEWING"),
        "contract_version": ("contract_version", "VALIDATING"),
        "components__shell": ("components.shell", "RECONCILING"),
        "components__renderer": ("components.renderer", "RECONCILING"),
        "components__normalisation": ("components.normalisation", "COMPOSING"),
        "components__reviewer_logic": ("components.reviewer_logic", "COMPOSING"),
        "validators__BC-02": ("validators", "VALIDATING"),
        "validator_version": ("validators", "VALIDATING"),
        "acceptance_profile_version": ("acceptance_profile_version", "REVIEWING"),
        "policy__sha256": ("policy", "PLANNING"),
    }
    scopes = {
        "source": "facts",
        "environment.python_version": "facts",
        "environment.extractor_version": "facts",
        "environment.inherited_units_version": "facts",
        "facts": "facts",
        "prompts.repository_investigation": "evidence",
        "prompts.source_reconciliation": "reconciliation",
        "prompts.presentation_planning": "planning",
        "prompts.section_authoring": "authoring",
        "prompts.independent_review": "reviewer",
        "prompts.targeted_repair": "reviewer",
        "contract_version": "validator",
        "components.shell": "presentation",
        "components.renderer": "presentation",
        "components.normalisation": "authoring",
        "components.reviewer_logic": "reviewer",
        "validators": "validator",
        "acceptance_profile_version": "reviewer",
        "policy": "planning",
    }
    for path, (dependency, state) in cases.items():
        evaluation = evaluate(SEALED, _current(**{path: "changed"}))
        assert [c.dependency for c in evaluation.changes] == [dependency], path
        assert evaluation.earliest == state, path
        assert [c.scope for c in evaluation.changes] == [scopes[dependency]], path
    added = _current()
    added["facts"]["format:input.obj"] = "3" * 64
    del added["facts"]["identity:repository"]
    evaluation = evaluate(SEALED, added)
    assert evaluation.changes == (
        Change("facts", "1 fact records added, 1 removed, 0 altered", "EXTRACTING", "facts"),
    )
    new_prompt = _current()
    new_prompt["prompts"]["extra_job"] = {"sha256": "z" * 64, "version": "1", "model_route": "m"}
    assert evaluate(SEALED, new_prompt).changes == (
        Change("prompts.extra_job", "prompt added", "INVESTIGATING", "evidence"),
    )


def test_changes_order_by_state_and_the_earliest_wins(tmp_path: Path) -> None:
    current = _current(**{"prompts__section_authoring__sha256": "c", "policy__sha256": "d"})
    current["validators"]["BC-01"] = "2"
    evaluation = evaluate(SEALED, current)
    assert [(c.dependency, c.reopens) for c in evaluation.changes] == [
        ("policy", "PLANNING"),
        ("prompts.section_authoring", "COMPOSING"),
        ("validators", "VALIDATING"),
    ]
    assert evaluation.earliest == "PLANNING"
    document = evaluation_document("a" * 40, evaluation)
    assert summarize_evaluation(document) == (
        "earliest affected stage PLANNING; 3 changes (policy -> PLANNING, "
        "prompts.section_authoring -> COMPOSING, validators -> VALIDATING)"
    )
    digest = write_evaluation(document, tmp_path / "evaluation.json")
    assert write_evaluation(document, tmp_path / "evaluation.json") == digest
    assert json.loads((tmp_path / "evaluation.json").read_text("utf-8")) == document
    unsealed = evaluation_document(None, None)
    assert unsealed["sealed_bundle"] is None and unsealed["earliest_affected_stage"] == "EXTRACTING"
    assert summarize_evaluation(unsealed) == "no sealed bundle for this revision; every stage runs"


# --- consumed-scope subsetting: mission §8's own contract ----------------------------------
# TC-INV-01 / G7-W25: a candidate is invalidated only through a fact record it cited
# (AGENTS.md: invalidate a candidate only through an input it consumed). dependencies.json keeps
# the digest of every fact (additive ``consumed_fact_ids`` names the cited subset) and
# ``evaluate`` compares only that subset when the field is present.


def _with_consumed(consumed: list[str]) -> dict[str, Any]:
    sealed = copy.deepcopy(SEALED)
    sealed["consumed_fact_ids"] = consumed
    return sealed


def test_an_added_unconsumed_fact_reopens_nothing() -> None:
    sealed = _with_consumed(["identity:repository"])
    current = copy.deepcopy(sealed)
    current["facts"]["public_symbol:new.Api"] = "9" * 64
    assert evaluate(sealed, current).changes == ()


def test_a_changed_unconsumed_fact_reopens_nothing() -> None:
    sealed = _with_consumed(["identity:repository"])
    current = copy.deepcopy(sealed)
    current["facts"]["format:output.glb"] = "changed"
    assert evaluate(sealed, current).earliest == "NONE"


def test_a_removed_unconsumed_fact_reopens_nothing() -> None:
    sealed = _with_consumed(["identity:repository"])
    current = copy.deepcopy(sealed)
    del current["facts"]["format:output.glb"]
    assert evaluate(sealed, current).earliest == "NONE"


def test_a_changed_consumed_fact_reopens_extracting() -> None:
    sealed = _with_consumed(["identity:repository"])
    current = copy.deepcopy(sealed)
    current["facts"]["identity:repository"] = "changed"
    evaluation = evaluate(sealed, current)
    assert evaluation.earliest == "EXTRACTING"
    assert [change.dependency for change in evaluation.changes] == ["facts"]
    assert evaluation.changes[0].detail == "0 fact records added, 0 removed, 1 altered"


def test_a_removed_consumed_fact_reopens_extracting() -> None:
    sealed = _with_consumed(["identity:repository", "format:output.glb"])
    current = copy.deepcopy(sealed)
    del current["facts"]["format:output.glb"]
    evaluation = evaluate(sealed, current)
    assert evaluation.earliest == "EXTRACTING"
    assert evaluation.changes[0].detail == "0 fact records added, 1 removed, 0 altered"


def test_a_record_without_consumed_fact_ids_compares_every_fact_as_before() -> None:
    """An old bundle names no subset, so an unconsumed-looking change still reopens EXTRACTING."""
    assert "consumed_fact_ids" not in SEALED
    added = copy.deepcopy(SEALED)
    added["facts"]["public_symbol:new.Api"] = "9" * 64
    assert evaluate(SEALED, added).earliest == "EXTRACTING"
    altered = copy.deepcopy(SEALED)
    altered["facts"]["format:output.glb"] = "changed"
    assert evaluate(SEALED, altered).earliest == "EXTRACTING"


def test_an_empty_consumed_set_means_no_fact_was_consumed_not_every_fact() -> None:
    sealed = _with_consumed([])
    current = copy.deepcopy(sealed)
    current["facts"]["identity:repository"] = "changed"
    assert evaluate(sealed, current).earliest == "NONE"


def test_other_classes_still_reopen_when_the_fact_subset_is_unchanged() -> None:
    sealed = _with_consumed(["identity:repository"])
    current = copy.deepcopy(sealed)
    current["facts"]["format:output.glb"] = "changed"
    current["source"]["revision"] = "b" * 40
    assert [c.dependency for c in evaluate(sealed, current).changes] == ["source"]
