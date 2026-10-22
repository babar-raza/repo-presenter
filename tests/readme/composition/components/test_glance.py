"""The At a Glance diagram: a Mermaid node needs its label wrapped in square brackets.

Real bug, found live (2026-10-22) the first time this module was ever exercised end to end
(scripts/run_lane_r_render.py against aspose-3d-foss/Aspose.3D-FOSS-for-Python's real S3-S6
cascade): every node came out as bare, unparseable ``NodeID"label"`` -- ``_label()`` returned
only the quoted text, never wrapped in the ``[...]`` a Mermaid node declaration needs. No test had
ever rendered a real diagram and inspected its Mermaid syntax before this.
"""

from __future__ import annotations

import re

from repo_presenter.readme.composition.components.glance import draw_at_a_glance

# A Mermaid node declaration: an identifier immediately followed by `["..."]` -- the exact shape
# the real bug broke (it produced `Product"..."`, no brackets at all).
_NODE_DECLARATION = re.compile(r'\b([A-Za-z][A-Za-z0-9]*)\["([^"]*)"\]')


def _lines(**kwargs: object) -> list[str]:
    return draw_at_a_glance(**kwargs)  # type: ignore[arg-type]


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
    assert _NODE_DECLARATION.search('Product["Aspose.3D FOSS for Python"]')
    for node_id in ("Start", "Product", "Cap1", "Cap2", "Output"):
        assert re.search(rf'{node_id}\["[^"]+"\]', body), (node_id, body)


def test_the_product_node_chains_from_the_starting_points_node() -> None:
    lines = _lines(
        product="Widget",
        starting_points=["An existing .widget file"],
        capability_titles=["Do a thing"],
        outputs=["A .widget file"],
    )
    assert any(line.startswith("Start[") for line in lines)
    assert any(re.match(r"Start --> Product\[", line) for line in lines)


def test_no_starting_points_omits_the_start_node_and_its_hop() -> None:
    lines = _lines(
        product="Widget",
        starting_points=[],
        capability_titles=["Do a thing"],
        outputs=["A .widget file"],
    )
    assert not any(line.startswith("Start") for line in lines)
    assert any(line.startswith("Product[") for line in lines)


def test_no_outputs_omits_the_output_node_and_its_hop() -> None:
    lines = _lines(
        product="Widget",
        starting_points=["An existing .widget file"],
        capability_titles=["Do a thing"],
        outputs=[],
    )
    assert not any("Output[" in line for line in lines)


def test_every_capability_connects_from_the_product_node() -> None:
    lines = _lines(
        product="Widget",
        starting_points=[],
        capability_titles=["A", "B", "C"],
        outputs=[],
    )
    body = "\n".join(lines)
    for index in range(1, 4):
        assert re.search(rf"Product\[[^\]]*\] --> Cap{index}\[", body)


def test_the_fence_opens_and_closes_as_a_mermaid_flowchart() -> None:
    lines = _lines(
        product="Widget", starting_points=[], capability_titles=["A"], outputs=[]
    )
    assert lines[0] == "```mermaid"
    assert lines[1] == "flowchart LR"
    assert lines[-1] == "```"


def test_unsafe_label_characters_are_stripped_not_left_to_break_the_syntax() -> None:
    lines = _lines(
        product='Widget "Pro" [Edition]',
        starting_points=[],
        capability_titles=["A"],
        outputs=[],
    )
    body = "\n".join(lines)
    assert "Widget Pro Edition" in body
    # No stray quote or bracket from the title survives inside the label's own quotes.
    match = re.search(r'Product\["([^\]]*)"\]', body)
    assert match is not None
    assert '"' not in match.group(1) and "[" not in match.group(1)
