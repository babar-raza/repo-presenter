"""BL-660: a FactsDocument of Words Java's size (45,838 facts) must build in well under a second. The duplicate
check was ``ids.count(i)`` per fact: 22 s per construction, and a cascade round builds dozens of documents, so the
hosted Lane R job spent its 90 minutes there (runs 44943578461, 44952689353)."""

from __future__ import annotations

import time

import pytest

from repo_presenter.core.facts import Fact, FactsDocument


def _facts(n: int) -> tuple[Fact, ...]:
    return tuple(
        Fact(
            id=f"{'public_symbol' if i % 3 else 'implementation'}:{i}",
            kind="public_symbol" if i % 3 else "implementation",
            value=f"v{i}", polarity="SUPPORTED", confidence=1.0, attributes=None,
            evidence=({"path": "a.java", "detail": "x"},),
        )
        for i in range(n)
    )


def test_a_large_document_builds_in_linear_time() -> None:
    facts = _facts(60_000)
    started = time.monotonic()
    document = FactsDocument("o/n", "a" * 40, facts)
    document.canonical()
    assert time.monotonic() - started < 5.0  # was ~40 s at 60k facts


def test_duplicate_ids_are_still_refused_and_sorted() -> None:
    facts = _facts(10)
    twice = (*facts, facts[7], facts[2], facts[7])
    with pytest.raises(ValueError, match=r"duplicate fact IDs: \['public_symbol:2', 'public_symbol:7'\]"):
        FactsDocument("o/n", "a" * 40, twice)


def test_by_kind_index_equals_the_scan_and_survives_replace() -> None:
    import dataclasses

    document = FactsDocument("o/n", "a" * 40, _facts(30))
    for kind in ("public_symbol", "implementation", "example"):
        assert document.by_kind(kind) == tuple(f for f in document.facts if f.kind == kind)
    assert document.by_kind("public_symbol") is document.by_kind("public_symbol")
    smaller = dataclasses.replace(document, facts=document.facts[:5])
    assert smaller.by_kind("public_symbol") == tuple(f for f in smaller.facts if f.kind == "public_symbol")
    assert document == FactsDocument("o/n", "a" * 40, document.facts)  # the index is not part of equality
