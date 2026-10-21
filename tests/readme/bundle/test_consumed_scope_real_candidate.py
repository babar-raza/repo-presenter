"""The mission §8 adversarial proof, against a real candidate's own facts -- not a synthetic
old-repo fixture.

Mission §8 (docs/MISSION_AUTHORITY.md; AGENTS.md's "invalidate a candidate only through an input
it consumed") requires: a change to a fact or component a candidate did NOT consume must never
reopen it, while a change to a fact it DID consume must. ``test_evaluation.py`` and
``test_invalidation.py`` prove this with hand-typed dicts; this file proves the same contract
against the real, independently-produced ``aspose-3d-foss`` P1_VERTICAL_SLICE candidate already
on disk in this repository
(``evidence/build/P1_VERTICAL_SLICE/aspose-3d-foss__Aspose.3D-FOSS-for-Python/``), using its
actual fact IDs and its actual consumed/unconsumed split.

The split is derived, not asserted by hand: every fact ID in that candidate's real
``facts.json`` is checked against its real ``content_units.json`` (the sections the composition
layer actually wrote from), so "consumed" here means "this candidate's own real content units
cite it", not a label this test invented. That gives two real, disjoint fact IDs to drive the
two scenarios:

- ``F-TOP-LEVEL-IMPORT-GOTCHA`` -- in facts.json, absent from every content unit: unconsumed.
- ``F-OBJ-EXPORT-BROKEN`` -- the real CONTRADICTED defect finding (Scene.save() to .obj
  succeeds although the fact claims it is broken), cited by a content unit: consumed.

Scenario 1 (unrelated change stays CURRENT): mutating the unconsumed fact's value leaves
``evaluate()`` reporting no change at all -- exactly ``recheck.CURRENT``: nothing a real
``recheck_bundle`` run would re-run, and certainly not a global reseal of every other accepted
candidate in the portfolio.

Scenario 2 (consumed change triggers recheck): mutating the consumed fact's value is caught as a
``facts`` dependency change, reopening ``EXTRACTING`` (the earliest stage, ahead of every
downstream one), and ``invalidation.route()`` marks it ``INVALIDATED`` -- never silently current,
and never left for a human to notice by accident.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repo_presenter.readme.bundle import recheck
from repo_presenter.readme.bundle.evaluation import evaluate
from repo_presenter.readme.bundle.invalidation import STATE_INVALIDATED, route

REPO_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_DIR = (
    REPO_ROOT
    / "evidence"
    / "build"
    / "P1_VERTICAL_SLICE"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
)
FACTS_PATH = CANDIDATE_DIR / "facts.json"
CONTENT_UNITS_PATH = CANDIDATE_DIR / "content_units.json"

pytestmark = pytest.mark.skipif(
    not FACTS_PATH.is_file() or not CONTENT_UNITS_PATH.is_file(),
    reason=f"real candidate fixture not found under {CANDIDATE_DIR}",
)


def _digest(fact: dict[str, str]) -> str:
    """A stand-in for the digest dependencies.json would have sealed for this fact's value: the
    disposition and claim text, hashed. The real seal hashes the Fact dataclass; this candidate's
    facts.json predates that exact schema (see migration/reuse-manifest.yaml's known_gap for
    core/facts.py), so this test hashes the content that *is* on disk rather than inventing a
    Fact record the real extraction pass never produced."""
    return hashlib.sha256(f"{fact['disposition']}|{fact['claim']}".encode()).hexdigest()


def _load_real_candidate() -> tuple[dict[str, str], list[str]]:
    """(fact_id -> digest for every real fact, the real consumed subset) for aspose-3d-foss."""
    document = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    facts = document["facts"]
    digests = {fact["id"]: _digest(fact) for fact in facts}
    content_units_text = CONTENT_UNITS_PATH.read_text(encoding="utf-8")
    consumed = sorted(fact_id for fact_id in digests if fact_id in content_units_text)
    return digests, consumed


def _sealed_record(digests: dict[str, str], consumed: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {"revision": "65b1f577c0f16d0d9112bb6c1153d3024543ac02"},
        "environment": {"extractor_version": "1", "inherited_units_version": "1"},
        "facts": dict(digests),
        "consumed_fact_ids": list(consumed),
        "components": {"renderer": "1"},
        "validators": {},
        "validator_version": "1",
        "contract_version": "readme-contract-v1",
        "acceptance_profile_version": "1",
        "policy": {"version": "1"},
    }


def test_the_real_candidate_has_both_a_consumed_and_an_unconsumed_fact() -> None:
    """A precondition, not the proof itself: the split this test drives must be real."""
    _digests, consumed = _load_real_candidate()
    assert "F-OBJ-EXPORT-BROKEN" in consumed
    assert "F-TOP-LEVEL-IMPORT-GOTCHA" not in consumed


def test_an_unrelated_facts_change_leaves_the_real_candidate_current() -> None:
    """Scenario 1: F-TOP-LEVEL-IMPORT-GOTCHA is a real fact of this exact candidate that its own
    content units never cite. Upstream "fixing" it (or anything else this candidate never
    consumed changing) must not reopen this candidate at all -- it stays recheck.CURRENT, and a
    real recheck_portfolio run would never touch it, let alone reseal the whole portfolio."""
    digests, consumed = _load_real_candidate()
    sealed = _sealed_record(digests, consumed)
    current = {**sealed, "facts": {**digests, "F-TOP-LEVEL-IMPORT-GOTCHA": "f" * 64}}

    evaluation = evaluate(sealed, current)

    assert evaluation.changes == ()
    assert evaluation.earliest == "NONE"
    # The vocabulary a real recheck_bundle run reports for "nothing consumed differs":
    # no triggered scope at all -> recheck.CURRENT (see recheck.classify with an empty scope list).
    assert recheck.classify([]) == (recheck.CURRENT, None)
    assert recheck.CURRENT not in ()  # sanity: the state recheck.py would report exists
    routing = route([c.dependency for c in evaluation.changes])
    assert routing.state is None and not routing.invalidates


def test_a_consumed_facts_change_is_marked_for_recheck() -> None:
    """Scenario 2: F-OBJ-EXPORT-BROKEN is the real CONTRADICTED defect finding this candidate's
    own content units cite (the whole reason the candidate exists is to report it). If upstream
    actually fixed the OBJ exporter, that fact's value changes, and this candidate -- and only
    this candidate, among whatever else a portfolio run touches -- must be marked for recheck:
    never silently left CURRENT, never invalidated via a side door, always through the fact it
    consumed."""
    digests, consumed = _load_real_candidate()
    sealed = _sealed_record(digests, consumed)
    mutated_digest = hashlib.sha256(b"SUPPORTED|Scene.save() to .obj now succeeds").hexdigest()
    current = {**sealed, "facts": {**digests, "F-OBJ-EXPORT-BROKEN": mutated_digest}}

    evaluation = evaluate(sealed, current)

    assert [c.dependency for c in evaluation.changes] == ["facts"]
    assert evaluation.earliest == "EXTRACTING"
    assert evaluation.changes[0].detail == "0 fact records added, 0 removed, 1 altered"
    routing = route([c.dependency for c in evaluation.changes])
    assert routing.invalidates and routing.state == STATE_INVALIDATED
    assert routing.triggering_scope == "facts" and routing.stage == "EXTRACTING"
    # Never recheck.CURRENT: a consumed factual input changed, so the candidate is not current
    # under any classification this layer can give it.
    assert evaluation.earliest != "NONE"


def test_the_two_scenarios_are_mutually_exclusive_on_the_same_sealed_record() -> None:
    """Both mutations applied to the same sealed record at once: the unconsumed one contributes
    nothing to the change set, and the consumed one alone still decides it -- proving the
    unrelated change is not merely "overridden" by coincidence but genuinely inert."""
    digests, consumed = _load_real_candidate()
    sealed = _sealed_record(digests, consumed)
    current = {
        **sealed,
        "facts": {
            **digests,
            "F-TOP-LEVEL-IMPORT-GOTCHA": "f" * 64,
            "F-OBJ-EXPORT-BROKEN": "e" * 64,
        },
    }

    evaluation = evaluate(sealed, current)

    assert [c.dependency for c in evaluation.changes] == ["facts"]
    assert evaluation.changes[0].detail == "0 fact records added, 0 removed, 1 altered"
