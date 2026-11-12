"""``example_facts`` turns a verification outcome into a fact whose polarity states what
actually happened -- never more and never less than the evidence supports.

TC-016: ``TIMED_OUT`` must map to ``UNRESOLVED`` at confidence 0.5, exactly like ``NEEDS_INPUT``
and ``NOT_VERIFIED`` -- never ``CONTRADICTED`` at confidence 1.0, since a timeout proves only
that verification could not finish in time, never that the example is wrong. "We could not
check" is not "we checked and it is false".
"""

from __future__ import annotations

import pytest

from repo_presenter.core.examples import ExampleCandidate, ExampleOutcome, ExampleReceipt
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.registry_entry_stub import RegistryEntryStub
from repo_presenter.readme.correction.detectors.examples import failing_example
from repo_presenter.readme.correction.model import Context
from repo_presenter.readme.evidence.facts.examples import example_facts


def _candidate(ordinal: int = 1, code: str = "print('hi')\n") -> ExampleCandidate:
    return ExampleCandidate(
        ordinal, "python", code, "README.md", 10, 12, f"inherited_unit:{ordinal:03d}.code_block"
    )


def _receipt(outcome: ExampleOutcome, ordinal: int = 1, detail: str = "detail") -> ExampleReceipt:
    return ExampleReceipt(
        ordinal=ordinal,
        outcome=outcome,
        return_code=None,
        stdout="",
        stderr="",
        detail=detail,
    )


@pytest.mark.parametrize(
    ("outcome", "polarity", "confidence"),
    [
        ("EXECUTED", "SUPPORTED", 1.0),
        ("FAILED", "CONTRADICTED", 1.0),
        ("TIMED_OUT", "UNRESOLVED", 0.5),
        ("NEEDS_INPUT", "UNRESOLVED", 0.5),
        ("NOT_VERIFIED", "UNRESOLVED", 0.5),
    ],
)
def test_each_outcome_maps_to_its_own_polarity_and_confidence(
    outcome: ExampleOutcome, polarity: str, confidence: float
) -> None:
    candidate = _candidate()
    receipt = _receipt(outcome)
    (fact,) = example_facts([candidate], [receipt], "examples.json")
    assert fact.polarity == polarity
    assert fact.confidence == confidence


def test_a_timeout_is_never_as_certain_as_a_genuine_failure() -> None:
    """The one confirmed defect this card fixes: a timeout proves only that the harness could
    not finish checking the example in time, not that the example is wrong -- so it must never
    be recorded at the same confidence as a real, executed failure."""
    candidate = _candidate()
    timed_out = example_facts([candidate], [_receipt("TIMED_OUT")], "examples.json")[0]
    failed = example_facts([candidate], [_receipt("FAILED")], "examples.json")[0]
    assert timed_out.polarity == "UNRESOLVED"
    assert failed.polarity == "CONTRADICTED"
    assert timed_out.confidence < failed.confidence


def test_a_missing_receipt_is_not_verified_and_unresolved() -> None:
    candidate = _candidate()
    (fact,) = example_facts([candidate], [], "examples.json")
    assert fact.polarity == "UNRESOLVED"
    assert fact.confidence == 0.5
    assert "no verification receipt" in (fact.evidence[1].detail or "")


def _context(fact: object) -> Context:
    entry = RegistryEntryStub(repository="owner/repo", ecosystem="python")
    document = FactsDocument("owner/repo", "a" * 40, (fact,))  # type: ignore[arg-type]
    return Context(entry, document, "irrelevant readme text\n", ("README.md",))


def test_a_timed_out_example_never_becomes_a_lane_l_finding() -> None:
    """Downstream check (TC-016): an UNRESOLVED example-fact polarity -- including one that
    started life as TIMED_OUT -- must never reach the correction detector as a reported defect.
    Only CONTRADICTED ever does (``readme/correction/detectors/examples.py``'s own
    ``fact.polarity != "CONTRADICTED"`` guard)."""
    candidate = _candidate()
    (timed_out_fact,) = example_facts([candidate], [_receipt("TIMED_OUT")], "examples.json")
    assert timed_out_fact.polarity == "UNRESOLVED"
    result = failing_example(_context(timed_out_fact))
    assert result.findings == ()
    assert result.edits == ()


def test_a_failed_example_still_becomes_a_lane_l_finding() -> None:
    """The negative control for the test above: a genuinely CONTRADICTED example must still be
    caught -- the fix narrows what counts as certain, it never widens what counts as fine."""
    candidate = _candidate()
    (failed_fact,) = example_facts(
        [candidate], [_receipt("FAILED", detail="boom")], "examples.json"
    )
    assert failed_fact.polarity == "CONTRADICTED"
    result = failing_example(_context(failed_fact))
    assert len(result.findings) == 1
