"""The At a Glance diagram: valid Mermaid node syntax, and a layout that reads at a glance.

Real bug, found live (2026-10-22) the first time this module was ever exercised end to end
(scripts/run_lane_r_render.py against aspose-3d-foss/Aspose.3D-FOSS-for-Python's real S3-S6
cascade): every node came out as bare, unparseable ``NodeID"label"`` -- ``_label()`` returned
only the quoted text, never wrapped in the ``[...]`` a Mermaid node declaration needs.

Owner feedback (2026-11-13, Cells Java Lane L, and portfolio-wide): the diagram needed "a lot of
horizontal scrolling" -- "At a Glance should practically be At a Glance". Measured with the real
Mermaid 10.9.1 at an 800 px container, the 26 certified diagrams drew 509-3054 px wide (19 of 26
over 800 px): a ``flowchart LR`` chain of long labels (Lane R), or groups of UNLINKED sibling nodes,
which Mermaid ranks together and so draws as one row whatever the group's ``direction`` says (the
live READMEs). The layout tests below pin the shape that fixed it: top to bottom, at most three
nodes to a row, labels wrapped, content unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.readme.composition.components.glance import (
    GLANCE_COLUMNS,
    GLANCE_WIDTH_BUDGET,
    GLANCE_WRAP,
    draw_at_a_glance,
    estimated_width,
    layout_glance,
    parse_glance,
    plain_label,
    wrap_label,
)

# A Mermaid node declaration: an identifier immediately followed by `["..."]` -- the exact shape
# the real bug broke (it produced `Product"..."`, no brackets at all).
_NODE_DECLARATION = re.compile(r'\b([A-Za-z][A-Za-z0-9]*)\["([^"]*)"\]')

#: The live Cells Java diagram exactly as the certified Lane L candidate (c65329e7257b) carries it:
#: measured 3054 px wide under Mermaid 10.9.1 (its labels at 4.2 px when fitted to 800 px).
CELLS_JAVA_LIVE = (
    Path(__file__).resolve().parents[3] / "fixtures" / "glance" / "cells_java_live.mmd"
).read_text(encoding="utf-8")


def _lines(**kwargs: object) -> list[str]:
    return draw_at_a_glance(**kwargs)  # type: ignore[arg-type]


def _rows(body: str, group: str) -> list[list[str]]:
    """The rows a group's grid holds: node ids by rank, from its invisible links."""
    inside = body.split(f"subgraph {group}[", 1)[1].split("\n  end", 1)[0]
    ids = [m.group(1) for m in re.finditer(r"^\s+(\w+)\[\"", inside, re.MULTILINE)]
    links = re.findall(r"^\s+(\w+) ~~~ (\w+)$", inside, re.MULTILINE)
    rank = dict.fromkeys(ids, 0)
    for _ in ids:
        for upper, lower in links:
            rank[lower] = max(rank[lower], rank[upper] + 1)
    rows: dict[int, list[str]] = {}
    for node_id in ids:
        rows.setdefault(rank[node_id], []).append(node_id)
    return [rows[r] for r in sorted(rows)]


def test_every_node_label_is_wrapped_in_square_brackets() -> None:
    lines = _lines(
        product="Aspose.3D FOSS for Python",
        starting_points=["An existing OBJ or STL file"],
        capability_titles=["Load multiple 3D formats", "Export to multiple 3D formats"],
        outputs=["OBJ or STL file"],
    )
    body = "\n".join(lines)
    # Negative control first: the real bug's exact shape must not appear anywhere.
    assert not re.search(r'\b[A-Za-z][A-Za-z0-9]*"[^[\]]', body)
    assert _NODE_DECLARATION.search('PRODUCT["Aspose.3D FOSS for Python"]')
    for node_id in ("i1", "PRODUCT", "c1", "c2", "o1"):
        assert re.search(rf'{node_id}\["[^"]+"\]', body), (node_id, body)


def test_the_fence_opens_a_top_to_bottom_flowchart_and_the_groups_chain_in_order() -> None:
    lines = _lines(
        product="Widget",
        starting_points=["An existing .widget file"],
        capability_titles=["Do a thing"],
        outputs=["A .widget file"],
    )
    assert lines[0] == "```mermaid"
    assert lines[1] == "flowchart TB"
    assert lines[-1] == "```"
    assert "  StartingPoints --> PRODUCT --> Capabilities --> Outputs" in lines
    for title in ("Starting Points", "Core Capabilities", "Outputs"):
        assert any(f'["{title}"]' in line for line in lines if "subgraph" in line)


def test_a_group_with_nothing_verified_is_omitted_with_its_hop() -> None:
    no_inputs = _lines(
        product="Widget", starting_points=[], capability_titles=["Do a thing"], outputs=["Out"]
    )
    assert not any("StartingPoints" in line for line in no_inputs)
    assert "  PRODUCT --> Capabilities --> Outputs" in no_inputs
    no_outputs = _lines(
        product="Widget", starting_points=["In"], capability_titles=["Do a thing"], outputs=[]
    )
    assert not any("Outputs" in line for line in no_outputs)
    assert "  StartingPoints --> PRODUCT --> Capabilities" in no_outputs


def test_capabilities_sit_at_most_three_to_a_row_in_their_order() -> None:
    titles = [f"Capability {n}" for n in range(1, 8)]
    body = "\n".join(
        _lines(product="Widget", starting_points=[], capability_titles=titles, outputs=[])
    )
    rows = _rows(body, "Capabilities")
    assert rows == [["c1", "c2", "c3"], ["c4", "c5", "c6"], ["c7"]]
    assert all(len(row) <= GLANCE_COLUMNS for row in rows)
    # Every node of a non-last row is linked: an unlinked node is free to sink to any row.
    for row in rows[:-1]:
        for node_id in row:
            assert re.search(rf"^\s+{node_id} ~~~ \w+$", body, re.MULTILINE), node_id


def test_four_make_a_square_and_two_one_row() -> None:
    four = "\n".join(
        _lines(product="W", starting_points=[], capability_titles=list("ABCD"), outputs=[])
    )
    assert _rows(four, "Capabilities") == [["c1", "c2"], ["c3", "c4"]]
    two = "\n".join(
        _lines(product="W", starting_points=[], capability_titles=list("AB"), outputs=[])
    )
    assert _rows(two, "Capabilities") == [["c1", "c2"]]


def test_long_labels_wrap_at_word_boundaries_and_keep_every_word() -> None:
    text = "An existing 3DS, 3MF, COLLADA, FBX, glTF, OBJ, PLY, or STL file"
    wrapped = wrap_label(text)
    assert "<br/>" in wrapped
    assert all(len(line) <= GLANCE_WRAP for line in wrapped.split("<br/>"))
    assert plain_label(wrapped) == text
    # A label holding & < or > is never touched: Mermaid releases disagree on drawing those.
    odd = ".xlsx workbook (file path, binary stream, or in-memory Vec<u8>)"
    assert wrap_label(odd) == odd


def test_unsafe_label_characters_are_stripped_not_left_to_break_the_syntax() -> None:
    lines = _lines(
        product='Widget "Pro" [Edition]',
        starting_points=[],
        capability_titles=["A"],
        outputs=[],
    )
    body = "\n".join(lines)
    assert 'PRODUCT["Widget Pro Edition"]' in body


def test_a_drawn_diagram_parses_back_to_its_own_content() -> None:
    lines = _lines(
        product="Aspose.3D FOSS for .NET",
        starting_points=["An existing 3DS, 3MF, COLLADA, FBX, glTF, OBJ, PLY, or STL file"],
        capability_titles=["Scene graph construction", "Format conversion", "Animation support"],
        outputs=["3DS, 3MF, COLLADA, FBX, glTF, OBJ, PLY, or STL file"],
    )
    glance = parse_glance("\n".join(lines[1:-1]))
    assert glance is not None
    assert [g.id for g in glance.groups] == ["StartingPoints", "Capabilities", "Outputs"]
    assert glance.groups[0].nodes == (
        ("i1", "An existing 3DS, 3MF, COLLADA, FBX, glTF, OBJ, PLY, or STL file"),
    )


def test_the_live_cells_java_diagram_is_re_laid_out_with_its_content_unchanged() -> None:
    glance = parse_glance(CELLS_JAVA_LIVE)
    assert glance is not None
    assert [len(g.nodes) for g in glance.groups] == [1, 15, 1]
    redrawn = "\n".join(layout_glance(glance))
    again = parse_glance(redrawn)
    assert again is not None and again.content() == glance.content()
    assert redrawn.splitlines()[0] == "flowchart TB"
    assert "  StartingPoints --> PRODUCT --> Capabilities --> Outputs" in redrawn.splitlines()
    assert [len(row) for row in _rows(redrawn, "Capabilities")] == [3, 3, 3, 3, 3]
    # The estimate that triggers the Lane L fix, calibrated on the real render (3054 -> 704 px).
    assert estimated_width(CELLS_JAVA_LIVE) > 2 * GLANCE_WIDTH_BUDGET
    assert estimated_width(redrawn) <= GLANCE_WIDTH_BUDGET
    # Laid out again, it is already laid out.
    assert layout_glance(again) == redrawn.splitlines()


def test_a_diagram_outside_the_presenter_grammar_is_not_understood() -> None:
    assert parse_glance("flowchart LR\nA --> B\nB --> C\n") is None
    assert parse_glance(CELLS_JAVA_LIVE + "  click PRODUCT href \"https://x\"\n") is None
    titled = CELLS_JAVA_LIVE.replace('subgraph capl[" "]', 'subgraph capl["Basics"]')
    assert parse_glance(titled) is None
    assert parse_glance(CELLS_JAVA_LIVE.replace("  StartingPoints --> PRODUCT", "  PRODUCT")) is None


def test_the_estimate_reads_a_left_to_right_group_as_a_column() -> None:
    # Measured: Aspose.PSD-FOSS-for-Python's `direction LR` group of six unlinked long labels
    # draws them stacked (522 px wide); the same nodes under `direction TB` draw them across.
    nodes = "\n".join(f'    c{n}["{"x" * 50}"]' for n in range(1, 7))
    across = f'flowchart TD\n  subgraph G["G"]\n    direction TB\n{nodes}\n  end\n'
    stacked = across.replace("direction TB", "direction LR")
    assert estimated_width(stacked) < GLANCE_WIDTH_BUDGET < estimated_width(across)
