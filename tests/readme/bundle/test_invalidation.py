"""Typed invalidation scopes: the table and the routing.

Adapted from the old repository-presenter project's
``tests/components/readme/bundle/test_invalidation.py``. Ported: every test that exercises the
table and ``route()``/``scope_of()``/``scope_of_artifact()`` directly (all pure, no fixtures).
Dropped: the old file's "every dependency class the seal records has a scope" and the whole
"portfolio dry run" section, because both call ``components/readme/bundle/seal.py`` and
``components/readme/bundle/dry_run.py`` (``upstream_dependencies``, ``code_dependencies``,
``portfolio_routing``, ``held_updates``) and ``core/llm/prompts.py`` -- none of which this
repository has pulled yet (see ``repo_presenter.readme.bundle.recheck``'s module docstring for the
same gap). ``test_a_difference_in_the_facts_hash_map_still_invalidates`` is kept because it only
needs ``evaluate`` + ``route`` over a hand-built dict, not the seal/dry_run machinery.
"""

from __future__ import annotations

import pytest

from repo_presenter.readme.bundle.evaluation import evaluate
from repo_presenter.readme.bundle.invalidation import (
    COMPONENT_SCOPES,
    PROMPT_SCOPES,
    SCOPES,
    STAGE_OVERRIDES,
    STATE_INVALIDATED,
    STATE_ORDER,
    STATE_UPDATE_AVAILABLE,
    ScopeError,
    reopening_stage,
    route,
    scope_of,
    scope_of_artifact,
)

# --- the table -----------------------------------------------------------------------------


def test_the_scope_table_maps_each_scope_to_a_stage_and_a_state() -> None:
    assert [scope.name for scope in SCOPES] == [
        "facts",
        "evidence",
        "reconciliation",
        "presentation",
        "planning",
        "authoring",
        "validator",
        "reviewer",
    ]
    stages = [STATE_ORDER.index(scope.stage) for scope in SCOPES]
    assert stages == sorted(stages)  # written in stage order; ties keep table order
    assert {scope.state for scope in SCOPES} <= {STATE_INVALIDATED, STATE_UPDATE_AVAILABLE}


def test_only_the_facts_scope_invalidates() -> None:
    """Negative control: a prompt, template, validator or reviewer input is never itself a factual
    input, so none of those scopes may be mapped to an invalidation (AGENTS.md)."""
    invalidating = [scope.name for scope in SCOPES if scope.state == STATE_INVALIDATED]
    assert invalidating == ["facts"]
    assert all(
        scope.state == STATE_UPDATE_AVAILABLE
        for scope in SCOPES
        if scope.name in {"validator", "reviewer", "presentation", "authoring", "planning"}
    )


def test_a_class_or_artifact_with_no_row_raises_rather_than_guessing() -> None:
    with pytest.raises(ScopeError, match="no invalidation scope for the dependency 'surprise'"):
        scope_of("surprise")
    with pytest.raises(ScopeError, match="no invalidation scope for the sealed artifact"):
        scope_of_artifact("surprise.json")
    # An unknown prompt or component falls to its family's row, as evaluation always defaulted.
    assert scope_of("prompts.a_new_job").name == "evidence"
    assert scope_of("components.a_new_component").name == "presentation"


def test_a_class_reopens_its_scope_stage_except_the_one_documented_override() -> None:
    assert STAGE_OVERRIDES == {"components.reviewer_logic": "COMPOSING"}
    concrete = [
        "source",
        "facts",
        "contract_version",
        "validators",
        "acceptance_profile_version",
        "policy",
        *(f"prompts.{name}" for name in PROMPT_SCOPES),
        *(f"components.{name}" for name in COMPONENT_SCOPES),
        "environment.python_version",
    ]
    for dependency in concrete:
        expected = STAGE_OVERRIDES.get(dependency) or scope_of(dependency).stage
        assert reopening_stage(dependency) == expected
    # The override only ever reopens earlier than its scope, so nothing under-reopens.
    reviewer = scope_of("components.reviewer_logic")
    assert STATE_ORDER.index(reopening_stage("components.reviewer_logic")) <= STATE_ORDER.index(
        reviewer.stage
    )


# --- the routing ---------------------------------------------------------------------------


def test_nothing_changed_routes_nowhere() -> None:
    routing = route([], [])
    assert routing.state is None and routing.scopes == () and not routing.invalidates


@pytest.mark.parametrize(
    ("dependency", "scope", "state", "stage"),
    [
        ("source", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("environment.extractor_version", "facts", STATE_UPDATE_AVAILABLE, "EXTRACTING"),
        (
            "environment.inherited_units_version",
            "facts",
            STATE_UPDATE_AVAILABLE,
            "EXTRACTING",
        ),
        # Negative control: what the host observed answering extraction still invalidates.
        ("environment.python_version", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("environment.toolchains.javac", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("facts", "facts", STATE_INVALIDATED, "EXTRACTING"),
        ("prompts.repository_investigation", "evidence", STATE_UPDATE_AVAILABLE, "INVESTIGATING"),
        ("prompts.source_reconciliation", "reconciliation", STATE_UPDATE_AVAILABLE, "RECONCILING"),
        ("components.shell", "presentation", STATE_UPDATE_AVAILABLE, "RECONCILING"),
        ("prompts.presentation_planning", "planning", STATE_UPDATE_AVAILABLE, "PLANNING"),
        ("policy", "planning", STATE_UPDATE_AVAILABLE, "PLANNING"),
        ("prompts.section_authoring", "authoring", STATE_UPDATE_AVAILABLE, "COMPOSING"),
        ("components.normalisation", "authoring", STATE_UPDATE_AVAILABLE, "COMPOSING"),
        ("validators", "validator", STATE_UPDATE_AVAILABLE, "VALIDATING"),
        ("contract_version", "validator", STATE_UPDATE_AVAILABLE, "VALIDATING"),
        ("prompts.independent_review", "reviewer", STATE_UPDATE_AVAILABLE, "REVIEWING"),
        ("acceptance_profile_version", "reviewer", STATE_UPDATE_AVAILABLE, "REVIEWING"),
        ("components.reviewer_logic", "reviewer", STATE_UPDATE_AVAILABLE, "COMPOSING"),
    ],
)
def test_each_changed_class_routes_to_its_scope_state_and_stage(
    dependency: str, scope: str, state: str, stage: str
) -> None:
    routing = route([dependency])
    assert (routing.triggering_scope, routing.state, routing.stage) == (scope, state, stage)
    assert routing.scopes == (scope,) and routing.basis == "inputs"
    assert routing.invalidates == (state == STATE_INVALIDATED)


def test_an_invalidating_scope_decides_over_earlier_and_later_scopes() -> None:
    routing = route(["validators", "prompts.independent_review", "facts", "components.shell"])
    assert routing.triggering_scope == "facts" and routing.invalidates
    assert routing.scopes == ("facts", "presentation", "validator", "reviewer")
    assert routing.stage == "EXTRACTING"


def test_without_a_facts_change_the_earliest_scope_decides_and_nothing_invalidates() -> None:
    routing = route(["validators", "prompts.independent_review", "prompts.section_authoring"])
    assert routing.triggering_scope == "authoring"
    assert routing.state == STATE_UPDATE_AVAILABLE and not routing.invalidates
    assert routing.stage == "COMPOSING"


def test_changed_inputs_win_over_the_artifacts_they_rewrote() -> None:
    routing = route(["components.renderer"], ["README.md", "facts.json"])
    assert routing.scopes == ("presentation",) and routing.basis == "inputs"
    assert not routing.invalidates


def test_artifact_drift_with_no_changed_input_is_scoped_by_the_stage_that_wrote_it() -> None:
    routing = route([], ["README.md", "review.json"])
    assert routing.scopes == ("authoring", "reviewer") and routing.basis == "artifacts"
    assert routing.state == STATE_UPDATE_AVAILABLE and routing.stage == "COMPOSING"
    assert route([], ["facts.json"]).invalidates


def test_a_difference_in_the_facts_hash_map_still_invalidates() -> None:
    """Negative control: only a different fact record is a factual input."""
    sealed = {
        "source": {"revision": "a" * 40},
        "facts": {"identity:repository": "1" * 64},
        "environment": {"inherited_units_version": "1"},
    }
    import copy

    current = copy.deepcopy(sealed)
    current["facts"]["identity:repository"] = "2" * 64
    changes = evaluate(sealed, current).changes
    assert [c.dependency for c in changes] == ["facts"]
    routing = route([c.dependency for c in changes])
    assert routing.invalidates and routing.triggering_scope == "facts"
    # ... and a version change beside it does not soften that.
    current["environment"]["inherited_units_version"] = "99"
    both = route([c.dependency for c in evaluate(sealed, current).changes])
    assert both.invalidates and both.scopes == ("facts",)
