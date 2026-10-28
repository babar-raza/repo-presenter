"""A Rust/C++ ``Namespace::Member`` compound in authored prose must never render as a broken
partial code span.

Reproduces, with a minimal synthetic fixture, the real defect measured live on a hosted run of
aspose-cells-foss/Aspose.Cells-FOSS-for-Rust (independent review finding F01, project/state.yaml):
the authored text named the public symbol ``CellsError`` immediately followed by ``::Unsupported``
(the real enum-variant path). ``CellsError`` alone is a registered, SUPPORTED ``public_symbol``;
``Unsupported`` is not separately tracked as one of its members. The renderer's code-span wrapper
(``RenderContext.prose``) already refuses to wrap only the tail of a dotted compound it does not
fully recognize (a boundary check excluding a preceding ``.``) -- it had no matching exclusion for
``::``, so it wrapped the known half alone and left the rest bare: `` `CellsError`::Unsupported ``,
a broken span rather than plain, readable text.
"""

from __future__ import annotations

import repo_presenter.extractors.platforms.rust  # noqa: F401  (registers the "rust" ecosystem spec)
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repo_presenter.readme.composition.renderer import render_readme

_ENTRY = RegistryEntry(
    repository="aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    family="cells",
    platform="rust",
    ecosystem="rust",
    mode="full",
    policy_profile="default",
    active=True,
    provider_identity=ProviderIdentity(repository_id=1, node_id="MDEwOlJlcG9zaXRvcnkx"),
)


def _facts() -> FactsDocument:
    facts = (
        Fact("identity:repository", "identity", _ENTRY.repository, (Evidence("data/registry.json"),)),
        Fact("identity:ecosystem", "identity", "rust", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "aspose-cells-foss", (Evidence("Cargo.toml"),)),
        Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
        Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
        Fact(
            "public_symbol:cellserror",
            "public_symbol",
            "CellsError",
            (Evidence("src/lib.rs", "; enum; "),),
            attributes={"symbol_kind": "enum"},
        ),
        Fact(
            "public_symbol:worksheetsmut.remove_at",
            "public_symbol",
            "WorksheetsMut.remove_at",
            (Evidence("src/lib.rs", "; method; "),),
        ),
    )
    return FactsDocument(_ENTRY.repository, "f" * 40, facts)


def _plan() -> dict:
    return {"sections": [{"section_id": "scope_limitations", "include": True}]}


def _units() -> dict:
    return {
        "units": [
            {
                "section": "scope_limitations",
                "slot": "scope",
                "text": "The library has some real limits.",
                "fact_ids": [],
            },
            {
                "section": "scope_limitations",
                "slot": "limitation:1",
                "text": (
                    "A workbook must always keep at least one worksheet, as "
                    "WorksheetsMut.remove_at returns a CellsError::Unsupported error when asked "
                    "to remove the last remaining worksheet."
                ),
                "fact_ids": [
                    "public_symbol:worksheetsmut.remove_at",
                    "public_symbol:cellserror",
                ],
            },
        ],
        "omitted": [],
    }


def _dispositions() -> dict:
    return {"dispositions": []}


def test_an_unknown_scoped_compound_renders_fully_plain_not_half_wrapped() -> None:
    readme = render_readme(_ENTRY, _facts(), _plan(), _units(), _dispositions())
    assert "`CellsError`::Unsupported" not in readme
    assert "CellsError::Unsupported" in readme


def test_a_fully_known_dotted_compound_still_renders_as_one_code_span() -> None:
    readme = render_readme(_ENTRY, _facts(), _plan(), _units(), _dispositions())
    assert "`WorksheetsMut.remove_at`" in readme
    assert "`WorksheetsMut`.remove_at" not in readme
