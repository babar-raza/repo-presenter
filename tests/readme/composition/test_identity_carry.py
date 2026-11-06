"""A kept unit is not "stated" by a destination that lacks a verified API identifier or a release
number it names (coverage.carries_identity_tokens, placement.supported_api_names).

Parity-gate losses (R2 benchmark floor, 2026-11-06): a VERIFIED_PRESERVE Key Capabilities list had
two items dropped by placement because the authored capabilities shared most of their words, losing
the qualified identifiers ``Reader.FromStream()`` / ``Writer.ToBytes()`` the facts SUPPORT; a
VERIFIED_PRESERVE development-dependency list lost its ``coverage.tool`` 6.0.2 item because the
authored paragraph said "code coverage" -- the version number was printed nowhere.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.coverage import (
    Destinations,
    api_identifiers,
    carries_identity_tokens,
    uncovered,
)
from repo_presenter.readme.composition.placement import supported_api_names

CAPABILITIES = (
    "- **Open containers** from a file or stream via `Reader.FromFile()` or "
    "`Reader.FromStream()`, then walk the tree with `IterTree()`.\n"
    "- **Build containers** with `Document` and serialize them with `Writer.ToBytes()`.\n"
)
AUTHORED = (
    "- **Inspect containers.** It opens containers with `Reader.FromFile`, and walks the tree "
    "with `IterTree` to inspect nested storages; build a `Document` and serialize containers.\n"
)
API = frozenset({"FromFile", "FromStream", "IterTree", "ToBytes", "Document", "Reader", "Writer"})


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("src/x.cs"),), polarity=polarity)  # type: ignore[arg-type]


def test_supported_api_names_are_the_simple_names_of_supported_symbols_only() -> None:
    facts = FactsDocument(
        "o/r",
        "a" * 40,
        (
            _fact("public_symbol:a", "public_symbol", "Ns.Cfb.Reader.FromStream"),
            _fact("public_symbol:b", "public_symbol", "crate::Writer"),
            _fact("enum_member:c", "enum_member", "Ns.Kind.Large"),
            _fact("public_symbol:d", "public_symbol", "Ns.Gone", polarity="CONTRADICTED"),
        ),
    )
    assert supported_api_names(facts) == frozenset({"FromStream", "Writer", "Large"})


def test_api_identifiers_are_code_spans_naming_a_supported_symbol() -> None:
    assert api_identifiers(CAPABILITIES, API) == [
        "Reader.FromFile",
        "Reader.FromStream",
        "IterTree",
        "Document",
        "Writer.ToBytes",
    ]
    assert api_identifiers("`pip install x` and `NotASymbol()`", API) == []
    assert api_identifiers(CAPABILITIES, ()) == []


def test_a_list_item_naming_an_identifier_the_document_lacks_is_kept() -> None:
    shown = Destinations.of({"key_capabilities": AUTHORED})
    remainder = uncovered(
        "inherited_unit:010.list", CAPABILITIES, shown, "key_capabilities", api_names=API
    )
    assert "`Reader.FromStream()`" in remainder
    assert "`Writer.ToBytes()`" in remainder


def test_the_same_items_are_trimmed_once_the_document_names_every_identifier() -> None:
    authored = AUTHORED + "- Also `Reader.FromStream` and `Writer.ToBytes` with `Reader.FromFile`.\n"
    assert carries_identity_tokens(CAPABILITIES, authored, API)
    # Without the API names (every caller before this fix) the identifiers were never asked about.
    assert carries_identity_tokens(CAPABILITIES, AUTHORED, ())
    assert not carries_identity_tokens(CAPABILITIES, AUTHORED, API)
    # An unqualified `IterTree()` is carried by the bare word, as the parity gate reads it.
    assert carries_identity_tokens("- Walk with `IterTree()`.", "walks `IterTree` nodes", API)


DEV_DEPENDENCIES = (
    "- `test.sdk` 17.12.0 and `xunit` 2.9.2 -- the test host used only by the test project.\n"
    "- `coverage.tool` 6.0.2 -- code-coverage collection for the test suite.\n"
)


def test_a_list_item_whose_release_number_the_document_prints_nowhere_is_kept() -> None:
    authored = (
        "The test project uses xUnit and related tooling for test execution and code coverage "
        "collection for the test suite.\n\n" + DEV_DEPENDENCIES.splitlines()[0] + "\n"
    )
    shown = Destinations.of({"development_testing": authored})
    remainder = uncovered("inherited_unit:026.list", DEV_DEPENDENCIES, shown, "development_testing")
    assert "6.0.2" in remainder


def test_a_release_restated_in_the_same_words_with_another_version_is_an_update() -> None:
    item = "- `coverage.tool` 6.0.2 -- code-coverage collection for the test suite.\n"
    assert carries_identity_tokens(item, "Uses `coverage.tool` 6.0.2 for coverage.")
    assert carries_identity_tokens(
        item, "- `coverage.tool` 6.1.0 -- code-coverage collection for the test suite."
    )
    assert not carries_identity_tokens(item, "Uses coverage tooling for the test suite.")
