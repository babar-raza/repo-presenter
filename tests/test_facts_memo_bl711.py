"""BL-711: values derived only from one immutable document are built once per document. Hosted Words Java
(45,838 facts): ``allowed_identifiers`` alone was recomputed for every unit check of every model call and every
render (0.27 s per call at 20,000 facts in a profile of the cascade fixture; 18.4 s -> 5.9 s for the whole
fixture after the memos), and a fresh ``canonical()`` copy per render discarded every index."""

from __future__ import annotations

import time

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    allowed_identifiers,
    mask_allowed_values,
    prose_nouns,
    surface_members,
    verified_members,
)
from repo_presenter.readme.validation.surface_claims import _surface_names


def _document(count: int = 300) -> FactsDocument:
    facts = tuple(
        Fact(f"public_symbol:s{i}", "public_symbol", f"com.acme.pkg{i % 7}.Type{i}", (Evidence("A.java"),), "SUPPORTED")
        for i in range(count)
    ) + (Fact("package:name", "package", "acme-lib", (Evidence("pom.xml"),), "SUPPORTED"),)
    return FactsDocument("acme/lib", "r" * 40, facts)


def test_each_derived_value_is_the_same_object_per_document_and_equal_to_a_fresh_build() -> None:
    doc = _document()
    first = allowed_identifiers(doc, "Acme Lib")
    assert allowed_identifiers(doc, "Acme Lib") is first
    assert first == allowed_identifiers(_document(), "Acme Lib")  # a different instance builds the same value
    assert prose_nouns(doc, "Acme Lib") is prose_nouns(doc, "Acme Lib")
    assert verified_members(doc) is verified_members(doc)
    assert surface_members(doc) is surface_members(doc)
    assert _surface_names(doc) is _surface_names(doc)


def test_the_memo_is_keyed_by_name_and_never_shared_across_documents() -> None:
    doc, other = _document(), _document(10)
    assert allowed_identifiers(doc, "Acme Lib") is not allowed_identifiers(doc, "Other Product")
    assert allowed_identifiers(doc, "Acme Lib") != allowed_identifiers(other, "Acme Lib")


def test_the_memo_is_not_part_of_equality_hashing_or_serialisation() -> None:
    doc, twin = _document(), _document()
    allowed_identifiers(doc, "Acme Lib")
    assert doc == twin and hash(doc.facts) == hash(twin.facts)
    assert doc.to_json() == twin.to_json()


def test_canonical_is_built_once_and_is_itself_canonical() -> None:
    doc = _document()
    canonical = doc.canonical()
    assert doc.canonical() is canonical and canonical.canonical() is canonical
    assert [f.id for f in canonical.facts] == sorted(f.id for f in doc.facts)
    assert canonical == FactsDocument(doc.repository, doc.source_revision, canonical.facts, doc.schema_version)


def test_masking_is_unchanged_whether_the_allowed_set_is_cached_or_not() -> None:
    allowed = allowed_identifiers(_document(), "Acme Lib")
    text = "Use com.acme.pkg1.Type8 and acme-lib with Foo.Bar."
    assert mask_allowed_values(text, allowed) == mask_allowed_values(text, set(allowed))
    assert "com.acme.pkg1.Type8" not in mask_allowed_values(text, allowed)


def test_a_second_unit_check_costs_far_less_than_the_first_on_a_large_document() -> None:
    doc = _document(20_000)
    started = time.perf_counter()
    allowed_identifiers(doc, "Acme Lib")
    first = time.perf_counter() - started
    started = time.perf_counter()
    for _ in range(200):
        allowed_identifiers(doc, "Acme Lib")
    repeated = (time.perf_counter() - started) / 200
    assert repeated < first / 50
