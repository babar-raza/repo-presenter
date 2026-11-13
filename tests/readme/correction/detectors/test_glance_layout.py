"""The live At a Glance diagram, too wide to read at a glance, laid out again -- content unchanged.

Inputs are the live diagram the certified Lane L candidate Cells Java (c65329e7257b) carries
(owner feedback, 2026-11-13: "needs a lot of horizontal scrolling ... At a Glance should
practically be At a Glance") and narrow / foreign diagrams the detector must leave alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_presenter.readme.composition.components.glance import (
    GLANCE_WIDTH_BUDGET,
    estimated_width,
    parse_glance,
)
from repo_presenter.readme.correction.apply import apply_edits, confinement_violations, order_edits
from repo_presenter.readme.correction.detectors.glance_layout import glance_layout
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.model import DIAGRAM_FIX
from repo_presenter.readme.correction.report import unrepaired_defects

CELLS_JAVA_LIVE = (
    Path(__file__).resolve().parents[3] / "fixtures" / "glance" / "cells_java_live.mmd"
).read_text(encoding="utf-8")
NARROW = """flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction TB
    i1["PSD file"]
  end
  PRODUCT["Widget"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Read"]
    c2["Write"]
  end
  StartingPoints --> PRODUCT --> Capabilities
"""


def _readme(body: str, newline: str = "\n") -> str:
    text = f"# Widget\n\n## At a Glance\n\n```mermaid\n{body}```\n\n## Installation\n\ntext\n"
    return text.replace("\n", newline)


def _applied(readme: str, edits: Any) -> str:
    kept, _ = order_edits(edits)
    corrected, spans = apply_edits(readme, kept)
    assert confinement_violations(readme, corrected, kept, spans) == []
    return corrected


def test_a_sprawling_live_diagram_is_redrawn_inside_its_fence(make_context: Any) -> None:
    readme = _readme(CELLS_JAVA_LIVE)
    result = glance_layout(make_context(readme))
    (edit,) = result.edits
    assert edit.kind == DIAGRAM_FIX and edit.locators == ("README.md:5",)
    assert edit.original == CELLS_JAVA_LIVE
    corrected = _applied(readme, result.edits)
    # Only the fence body changed; everything around it is byte-identical.
    assert corrected.startswith("# Widget\n\n## At a Glance\n\n```mermaid\nflowchart TB\n")
    assert corrected.endswith("```\n\n## Installation\n\ntext\n")
    before, after = parse_glance(CELLS_JAVA_LIVE), parse_glance(edit.replacement)
    assert before is not None and after is not None and after.content() == before.content()
    assert estimated_width(edit.replacement) <= GLANCE_WIDTH_BUDGET
    # Idempotent: the redrawn diagram is not redrawn again.
    assert glance_layout(make_context(corrected)).edits == ()


def test_a_crlf_readme_keeps_its_line_endings(make_context: Any) -> None:
    readme = _readme(CELLS_JAVA_LIVE, "\r\n")
    (edit,) = glance_layout(make_context(readme)).edits
    assert "\r\n" in edit.replacement and "\n" not in edit.replacement.replace("\r\n", "")


def test_a_diagram_that_already_fits_is_left_alone(make_context: Any) -> None:
    result = glance_layout(make_context(_readme(NARROW)))
    assert result.edits == () and result.findings == ()


def test_a_diagram_outside_the_presenter_grammar_is_left_alone(make_context: Any) -> None:
    foreign = CELLS_JAVA_LIVE + '  click PRODUCT href "https://example.com"\n'
    result = glance_layout(make_context(_readme(foreign)))
    assert result.edits == () and result.findings == ()


def test_a_mermaid_block_shown_inside_another_fence_is_not_a_diagram(make_context: Any) -> None:
    readme = "# W\n\n````markdown\n```mermaid\n" + CELLS_JAVA_LIVE + "```\n````\n"
    assert glance_layout(make_context(readme)).edits == ()


def test_the_engine_applies_the_redraw_and_reports_no_defect(make_context: Any) -> None:
    """The owner's own feedback was given on a no-change candidate (Cells Java): the redraw is an
    edit in its own right, and a diagram it declines is never a defect that refuses the run."""
    readme = _readme(CELLS_JAVA_LIVE)
    ctx = make_context(readme)
    result = correct(ctx)
    assert [e.detector for e in result.edits] == ["glance_layout"]
    assert "flowchart TB" in result.corrected
    assert not [f for f in unrepaired_defects(result) if f.detector == "glance_layout"]
    deterministic, idempotent = is_stable(ctx, result)
    assert deterministic and idempotent


def test_a_layout_fix_rides_with_a_content_correction(make_context: Any) -> None:
    # A second H1 is a real defect (structure.second_h1): with it, the diagram is redrawn too.
    readme = _readme(CELLS_JAVA_LIVE) + "\n# Requires Java 17\n"
    ctx = make_context(readme)
    result = correct(ctx)
    assert sorted(e.detector for e in result.edits) == ["glance_layout", "second_h1"]
    assert "flowchart TB" in result.corrected and "\n## Requires Java 17" in result.corrected
    deterministic, idempotent = is_stable(ctx, result)
    assert deterministic and idempotent
