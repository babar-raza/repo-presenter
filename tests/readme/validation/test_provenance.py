"""BC-03's `example_failures`: downstream check for TC-016 -- an UNRESOLVED example-fact
polarity, including one that started life as a `TIMED_OUT` receipt, must never be treated as
grounds to drop, repair, or flag README content as defective. An UNRESOLVED example the README
already carried is retained and printed exactly as written (``readme/composition/retained_
examples.py``), never as a planned, verified one -- its unverified status stays internal, in
facts.json/dispositions.json, never a reason for a blocking failure here.
"""

from __future__ import annotations

import dataclasses

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.provenance import example_failures

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1,
            "node_id": "R_1",
        },
    }
)
REVISION = "c" * 40
_CODE = "print('hi')"
_FENCE = f"```python\n{_CODE}\n```"


def _candidate(readme: str, facts: FactsDocument, dispositions: dict[str, object]) -> Candidate:
    return Candidate(
        ENTRY,
        facts,
        {},  # plan: nothing planned -- this example is only retained, never "the" verified one
        {},
        dispositions,
        readme,
        None,
        REVISION,
        None,
        (),
        (),
    )


def _retained_candidate(outcome_evidence: str) -> Candidate:
    """A candidate whose README carries one retained, UNRESOLVED example -- exactly the shape
    `composition/retained_examples.py` already recognises (an inherited code_block unit whose
    body matches an UNRESOLVED example fact, adopted by a SUPERSEDE_REDUNDANT disposition into
    quick_start)."""
    unit = Fact(
        "inherited_unit:001.code_block",
        "inherited_unit",
        _FENCE,
        (Evidence("README.md", "lines 1-3; code_block"),),
    )
    example = Fact(
        "example:001",
        "example",
        _CODE,
        (
            Evidence("README.md", "lines 1-3; python fence; unit inherited_unit:001.code_block"),
            Evidence("examples.json", f"example 1: {outcome_evidence}"),
        ),
        polarity="UNRESOLVED",
        confidence=0.5,
    )
    facts = FactsDocument(ENTRY.repository, REVISION, (unit, example))
    dispositions = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:001.code_block",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "quick_start",
                "fact_ids": ["example:001"],
            }
        ]
    }
    readme = f"# Quick Start\n\n{_FENCE}\n"
    return _candidate(readme, facts, dispositions)


def test_a_retained_example_that_timed_out_is_never_flagged_as_defective() -> None:
    """The exact case TC-016 fixed: an example whose receipt was `TIMED_OUT` is now UNRESOLVED
    (not CONTRADICTED), is retained, and is printed exactly as written -- BC-03 must find nothing
    wrong with it."""
    assert example_failures(_retained_candidate("TIMED_OUT")) == []


def test_a_retained_example_needing_input_is_never_flagged_as_defective() -> None:
    assert example_failures(_retained_candidate("NEEDS_INPUT")) == []


def test_an_edited_retained_example_still_fails_bc03() -> None:
    """The invariant is "printed exactly as written", not "polarity is UNRESOLVED" -- an
    UNRESOLVED example whose code was altered before printing must still be caught."""
    candidate = _retained_candidate("TIMED_OUT")
    # An extra blank line inside the fence does not change the *normalized* body (blank lines are
    # dropped when matching the block to its retained example), so it is still recognised as the
    # same retained block -- but it does change the exact bytes, so printing it this way is not
    # printing it "exactly as written" and must still be caught.
    edited = candidate.readme.replace("print('hi')\n```", "print('hi')\n\n```")
    assert edited != candidate.readme
    broken = dataclasses.replace(candidate, readme=edited)
    failures = example_failures(broken)
    assert any("not printed exactly as the maintainers wrote it" in f.detail for f in failures)


def test_python_declares_the_py_and_python3_fence_aliases_too() -> None:
    assert spec_for("python").example_fences == frozenset({"python", "py", "python3"})
