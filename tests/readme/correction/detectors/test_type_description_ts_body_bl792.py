"""BL-792 (hosted Lane L PDF TypeScript, run 44993692981: REJECT with 16 blocking findings of 16).

The real shape, from the pinned source (aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript @ 5fa1775):
the public surface records the whole declaration of an interface, body included --
``export interface MdBlockQuote { type: 'block_quote'; children: MdBlock[]; }``. ``_base_names`` took
the first colon for a C# or C++ base list, so the member types' tail ``}`` became the base and the
correction wrote ``Interface that inherits from } and declares the members children and type.`` into
fifteen rows; no deterministic holdout saw it and the independent review rejected the candidate.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.detectors.type_description import type_description
from repo_presenter.readme.validation.surface_claims import _base_names

PACKAGE = "aspose_pdf"


def _type(name: str, declaration: str, kind: str = "class") -> Fact:
    return Fact(
        f"public_symbol:{name}".lower(), "public_symbol", name,
        (Evidence("src/mdast.ts", "line 61; class; re-exported by the package entry point `src/index.ts`"),),
        attributes={"symbol_kind": kind, "declaration": declaration},
    )


def _field(owner: str, name: str, signature: str) -> Fact:
    # The real extractor records an interface property as a ``method`` whose signature is its type.
    return Fact(
        f"public_symbol:{owner}.{name}".lower(), "public_symbol", f"{owner}.{name}",
        (Evidence("src/mdast.ts", "line 61; method; re-exported by the package entry point `src/index.ts`"),),
        attributes={"symbol_kind": "method", "signature": signature},
    )


def test_a_typescript_body_is_never_read_as_a_base_list() -> None:
    body = _type("MdBlockQuote", "export interface MdBlockQuote { type: 'block_quote'; children: MdBlock[]; }")
    assert _base_names(body) == []
    nested = _type("Options", "export interface Options { retry: { max: number; wait: number }; mode: string }")
    assert _base_names(nested) == []


def test_the_real_base_list_shapes_still_read() -> None:
    cs = _type("PngDevice", "public class PngDevice : ImageDevice, IDisposable")
    assert _base_names(cs) == ["ImageDevice", "IDisposable"]
    cpp = _type("PngDevice", "class PngDevice : public ImageDevice {")
    assert _base_names(cpp) == ["ImageDevice"]
    explicit = Fact(
        "public_symbol:aspose_pdf.x", "public_symbol", "aspose_pdf.X", (Evidence("x.py", "line 1"),),
        attributes={"symbol_kind": "class", "bases": "Base, Mixin"},
    )
    assert _base_names(explicit) == ["Base", "Mixin"]


def test_the_corrected_rows_name_no_base_and_list_the_members(make_context: Any) -> None:
    facts = [
        _type("MdBlockQuote", "export interface MdBlockQuote { type: 'block_quote'; children: MdBlock[]; }"),
        _field("MdBlockQuote", "type", ": 'block_quote'"),
        _field("MdBlockQuote", "children", ": MdBlock[]"),
        _type("MdCode", "export interface MdCode { type: 'code'; value: string; }"),
        _field("MdCode", "type", ": 'code'"),
        _field("MdCode", "value", ": string"),
    ]
    table = (
        "| Interface | Description |\n|---|---|\n"
        "| `MdBlockQuote` | Interface with 2 properties. |\n"
        "| `MdCode` | Interface with 2 properties. |\n"
    )
    result = type_description(make_context(table, facts))
    corrected = apply_edits(table, list(result.edits))[0]
    assert "inherits from" not in corrected and "}" not in corrected
    assert "| `MdCode` | Interface that declares the members type and value. |" in corrected
