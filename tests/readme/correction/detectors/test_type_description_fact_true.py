"""BL-080: a maintainers' API table cell a SUPPORTED fact refutes is made fact-true by Lane L.

Hosted Lane L run 43513031042 (Aspose.3D-FOSS-for-.NET at 52b0f00e) was REJECTed with 18 blocking
findings, every one maintainer text the run left in place: the run made no content edit, so R21's
net improvement did not hold and no pre-existing defect could be carried as a residual. Five of the
18 are cells the facts refute as a whole; the rows below are verbatim from that live README (lines
287, 295, 318, 319 and 451) and the facts are the extractor's shapes (``implementation`` aspect
``never_thrown``; the maintainers' own Scope and Limitations list, ``inherited_unit:061.list``,
which says ``Watermark`` only throws). The cells now read what the Lane R renderer prints for the
same types, which the rule accepts; a cell the facts do not refute is left as written.
"""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.detectors.type_description import (
    STUB_DESCRIPTION,
    type_description,
)
from repo_presenter.readme.correction.model import FALSE_CLAIM_FIX
from repo_presenter.readme.validation.code_path_claims import NOT_THROWN_DESCRIPTION
from repo_presenter.readme.validation.claims import claim_findings

ROWS = {
    "DriverException": "Exception raised by internal rendering drivers.",
    "ExportException": "Exception raised on export failure.",
    "ImportException": "Exception raised on import failure.",
    "InitializationException": "Exception raised on initialization failure.",
}
WATERMARK = "Embeds and extracts text watermarks in 3D files, with optional password protection."
KEPT = "Per-vertex blend weight."
TABLE = (
    "### Core API\n\n| Class | Description |\n|---|---|\n"
    + "".join(f"| `{name}` | {text} |\n" for name, text in ROWS.items())
    + f"| `VertexElementWeight` | {KEPT} |\n"
    + f"| `Watermark` | {WATERMARK} |\n"
    + "| `RenderFactory` | Creates renderers for a scene. |\n"
)
LIMITATIONS = (
    "- Rendering is not implemented in this FOSS build — `Scene.Render`, `RenderFactory`, and the\n"
    "  `IRenderTarget`/`IRenderWindow` rendering pipeline all throw `NotImplementedException`.\n"
    "- `Watermark` (`EncodeWatermark`/`DecodeWatermark`) throws `NotImplementedException`."
)
NAMESPACES = {
    "DriverException": "Aspose.ThreeD.Render",
    "ExportException": "Aspose.ThreeD",
    "ImportException": "Aspose.ThreeD",
    "InitializationException": "Aspose.ThreeD.Render",
    "VertexElementWeight": "Aspose.ThreeD.Entities",
    "Watermark": "Aspose.ThreeD.Utilities",
    "RenderFactory": "Aspose.ThreeD.Render",
}


def _symbol(value: str, kind: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/main/Aspose.ThreeD/x.cs", f"line 6; {kind}; public by declaration"),),
        attributes={"symbol_kind": kind, **attributes},
    )


def _facts(make_facts: Any, *, never_thrown: bool = True) -> Any:
    extra: list[Fact] = []
    for name, namespace in NAMESPACES.items():
        extra.append(_symbol(f"{namespace}.{name}", "class", declaration=f"public class {name}"))
    extra.append(
        _symbol("Aspose.ThreeD.Render.RenderFactory.CreateRenderer", "method", body_throws="no")
    )
    extra.append(
        Fact(
            "inherited_unit:061.list",
            "inherited_unit",
            LIMITATIONS,
            (Evidence("README.md", "lines 576-602; list; under Scope and Limitations"),),
            attributes={"section": "Scope and Limitations"},
        )
    )
    if never_thrown:
        for name in ROWS:
            member = f"{NAMESPACES[name]}.{name}"
            extra.append(
                Fact(
                    f"implementation:never_thrown.{member.lower()}",
                    "implementation",
                    f"{member} is never thrown or constructed by the library's own code "
                    "(declared only)",
                    (Evidence("src/main/Aspose.ThreeD/x.cs", "line 9; declared only"),),
                    attributes={"aspect": "never_thrown", "member": member, "type": name},
                )
            )
    return make_facts(*extra)


def test_the_refuted_cells_become_fact_true(make_context: Any, make_facts: Any) -> None:
    facts = _facts(make_facts)
    ctx = make_context(TABLE, facts)
    result = type_description(ctx)
    replaced = {edit.original: edit.replacement for edit in result.edits}
    assert replaced == {
        **{text: NOT_THROWN_DESCRIPTION for text in ROWS.values()},
        WATERMARK: STUB_DESCRIPTION,
    }
    assert all(edit.kind == FALSE_CLAIM_FIX and len(edit.fact_ids) == 2 for edit in result.edits)
    corrected, _ = apply_edits(TABLE, result.edits)
    assert KEPT in corrected
    assert "| `RenderFactory` | Creates renderers for a scene. |" in corrected
    before = [f.detail for f in claim_findings(TABLE, ctx.facts)]
    after = [f.detail for f in claim_findings(corrected, ctx.facts)]
    assert any("`DriverException` is thrown" in d for d in before)
    assert any("`Watermark` as working" in d for d in before)
    assert not any(" is thrown, but " in d or "`Watermark` as working" in d for d in after)
    # ``RenderFactory``'s body returns a value, so the limitation statement calling it a stub is
    # the false one: the cell is not rewritten to "Not implemented." (the rule's pre-existing
    # finding on it is the maintainers', carried unchanged, never one this edit creates).
    assert [d for d in after if d not in before] == []
    again = type_description(make_context(corrected, facts))
    assert not again.edits


@pytest.mark.parametrize("name", sorted(ROWS))
def test_negative_control_without_the_fact_the_exception_cell_stays(
    name: str, make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(TABLE, _facts(make_facts, never_thrown=False))
    originals = {edit.original for edit in type_description(ctx).edits}
    assert ROWS[name] not in originals
