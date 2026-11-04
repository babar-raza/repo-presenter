"""Real tests for issues/discovery.py (2026-11-04, TC-010): constructs Handoff objects from
real CONTRADICTED facts, never invents evidence, never guesses an unmapped kind into a class."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repo_presenter.issues.discovery import discover_handoffs  # noqa: E402
from repo_presenter.issues.model import DEFECT_CLASSES  # noqa: E402


def _doc(*facts: Fact) -> FactsDocument:
    return FactsDocument(repository="o/r", source_revision="a" * 40, facts=tuple(facts))


def test_a_contradicted_example_fact_becomes_a_real_handoff():
    fact = Fact(
        id="example:readme-snippet-1",
        kind="example",
        value="the README's first example does not compile",
        evidence=(Evidence(path="README.md", detail="line 42"),),
        polarity="CONTRADICTED",
    )
    handoffs = discover_handoffs(_doc(fact), extractor_version="1")
    assert len(handoffs) == 1
    h = handoffs[0]
    assert h.repository == "o/r"
    assert h.source_revision == "a" * 40
    # defect_fingerprint is a sha256 hex digest (approval.py's own handoff_id() contract), not
    # the readable fact id -- that is preserved separately in triggering_check.id.
    assert len(h.defect_fingerprint) == 64 and all(c in "0123456789abcdef" for c in h.defect_fingerprint)
    assert h.triggering_check.id == "example:readme-snippet-1"
    assert h.defect_class == "EXAMPLE_FAILS"
    assert h.status == "HANDOFF_PENDING"
    assert h.issue_ref is None and h.close_reason is None
    assert h.evidence[0].path == "README.md" and h.evidence[0].detail == "line 42"
    assert h.claim == fact.value


def test_a_supported_fact_never_becomes_a_handoff():
    fact = Fact(
        id="example:readme-snippet-1",
        kind="example",
        value="compiles fine",
        evidence=(Evidence(path="README.md"),),
        polarity="SUPPORTED",
    )
    assert discover_handoffs(_doc(fact), extractor_version="1") == []


def test_an_unresolved_fact_never_becomes_a_handoff():
    fact = Fact(
        id="example:readme-snippet-1",
        kind="example",
        value="could not verify",
        evidence=(Evidence(path="README.md"),),
        polarity="UNRESOLVED",
    )
    assert discover_handoffs(_doc(fact), extractor_version="1") == []


def test_a_contradicted_fact_of_an_unmapped_kind_is_skipped_not_guessed():
    """'identity' has no defect-class counterpart -- it must never be forced into the nearest
    class; this is the module's own stated discipline, tested directly."""
    fact = Fact(
        id="identity:package-name",
        kind="identity",
        value="wrong name claimed",
        evidence=(Evidence(path="README.md"),),
        polarity="CONTRADICTED",
    )
    assert discover_handoffs(_doc(fact), extractor_version="1") == []


def test_every_discovered_defect_class_is_one_model_py_actually_recognizes():
    facts = [
        Fact(id=f"{kind}:x", kind=kind, value="bad", evidence=(Evidence(path="p"),),
             polarity="CONTRADICTED")
        for kind in ("license", "example", "install_command", "build_test_asset")
    ]
    handoffs = discover_handoffs(_doc(*facts), extractor_version="1")
    assert len(handoffs) == 4
    for h in handoffs:
        assert h.defect_class in DEFECT_CLASSES


def test_discovery_is_deterministic():
    fact = Fact(
        id="example:x", kind="example", value="bad", evidence=(Evidence(path="p"),),
        polarity="CONTRADICTED",
    )
    doc = _doc(fact)
    assert discover_handoffs(doc, extractor_version="1") == discover_handoffs(doc, extractor_version="1")
