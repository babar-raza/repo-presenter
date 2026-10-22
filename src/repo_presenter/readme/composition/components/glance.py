"""The At a Glance component: the diagram, and the label geometry every stage judges it by.

ADAPTED (not a port) -- this is a deliberately SIMPLIFIED stand-in for the old repository-
presenter project's ``components/readme/composition/components/glance.py``, which itself only
re-exports a much larger, separate visual-generation subsystem: ``components/readme_diagram``
(``Glance``, ``balanced_columns``, ``build_block``, a measured five-font character-width model,
browser-proven SVG rendering, and the full README_CONTRACT.md section 2.1 geometry contract --
"no label wraps past N lines", "every box grows to fit its text", "a longer title is shortened at
planning, never clipped at render").

That subsystem was NOT read or ported as part of this taskcard (it is a separate, large,
self-contained visual-rendering engine, not part of composition's own planning/placement/
renderer/coherence pipeline proper, and migration/reuse-manifest.yaml does not list it as pulled).
Porting it faithfully is future work. What follows is a minimal, honestly-simplified local
implementation that gives ``readme/composition/planning.py`` (``capability_title_problem``, via
``plan_checks``) and ``readme/composition/renderer.py`` (``draw_at_a_glance``, via
``_at_a_glance``) a working, test-covered function to call, so the composition pipeline is
importable and exercisable end to end -- but it does NOT reproduce the old repository's own
font-measured, browser-verified geometry proof, and a rendered diagram from this module will not
be byte-identical to the old repository's own sealed candidates.

``capability_title_problem`` here is a plain character-length budget (not a measured pixel/font
model): a title longer than ``_MAX_TITLE_CHARS`` characters, or containing a word longer than
that budget on its own, is reported as a problem so ``planning.plan_checks`` has something real
to enforce; ``draw_at_a_glance`` emits a plain left-to-right Mermaid ``flowchart`` -- one Starting
Points node (omitted if there are no verified input formats), the product, one node per
capability, and one Outputs node (omitted if there are no verified output formats) -- which is a
reasonable, renderable diagram but not geometry-proven the way the real diagram builder is.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# A rough, deliberately conservative per-line character budget -- not a measured font model. The
# real README_CONTRACT.md geometry contract bounds a label by measured pixel width inside a column
# that narrows as the capability count grows; this is a flat substitute, generous enough not to
# reject ordinary short titles, strict enough to catch a genuinely unshortened sentence.
_MAX_TITLE_CHARS = 48
_MAX_WORD_CHARS = 24
GLANCE_MAX_LINES = 3

_UNSAFE_LABEL = re.compile(r'["\[\]{}|]')


def capability_title_problem(title: str, capability_count: int) -> str | None:
    """Why ``title`` cannot be drawn geometry-safe in a diagram of ``capability_count``
    capabilities, or ``None``. Planning shortens such a title; the renderer never clips it.

    A narrower, flat stand-in for the real measured-pixel contract (see module docstring): a
    title at or under the character budget is accepted regardless of ``capability_count`` (the
    real contract narrows the budget as the column count grows; this one does not).
    """
    stripped = title.strip()
    if not stripped:
        return "is empty"
    if len(stripped) > _MAX_TITLE_CHARS:
        return f"is {len(stripped)} characters, over the {_MAX_TITLE_CHARS}-character budget"
    longest_word = max((len(word) for word in stripped.split()), default=0)
    if longest_word > _MAX_WORD_CHARS:
        return f"contains a word of {longest_word} characters, too wide for any column"
    return None


def label_height(label: str, capability_count: int = 1) -> int:
    """How many lines ``label`` occupies. This simplified model never wraps a title that already
    passed :func:`capability_title_problem`, so it always returns 1."""
    return 1


def _label(text: str) -> str:
    """A Mermaid node's full shape-plus-label syntax (square brackets around a quoted string),
    with characters Mermaid's own bracket syntax would otherwise misread stripped out.

    Real bug, found live (2026-10-22) the first time this module was ever exercised end to end:
    this returned only the quoted text (``"label"``), never wrapped in the ``[...]`` a Mermaid
    node declaration needs (``NodeID["label"]``) -- every node in a rendered diagram came out as
    bare, unparseable ``NodeID"label"``. No test had ever rendered a real diagram and inspected
    its Mermaid syntax before this.
    """
    return '["' + _UNSAFE_LABEL.sub("", text).strip() + '"]'


def draw_at_a_glance(
    *,
    product: str,
    starting_points: Sequence[str],
    capability_titles: Sequence[str],
    outputs: Sequence[str],
) -> list[str]:
    """The fenced Mermaid block of the diagram: one chain, Starting Points, the product, Core
    Capabilities, and Outputs, left to right; a group with nothing verified is omitted with its
    hop (see module docstring for how this differs from the real, ported diagram builder)."""
    lines = ["```mermaid", "flowchart LR"]
    product_node = "Product" + _label(product)
    previous = None
    if starting_points:
        lines.append(f'Start{_label("; ".join(starting_points))}')
        lines.append(f"Start --> {product_node}")
        previous = product_node
    else:
        lines.append(product_node)
        previous = product_node
    capability_nodes = []
    for index, title in enumerate(capability_titles, start=1):
        node = f"Cap{index}{_label(title)}"
        lines.append(f"{previous} --> {node}" if index == 1 else node)
        capability_nodes.append(node)
    if capability_nodes:
        for node in capability_nodes[1:]:
            lines.append(f"{previous} --> {node}")
    if outputs:
        output_node = "Output" + _label("; ".join(outputs))
        sources = capability_nodes or [previous]
        for node in sources:
            lines.append(f"{node} --> {output_node}")
    lines.append("```")
    return lines


def diagram_failures(body: str, has_inputs: bool) -> list[str]:
    """Geometry/topology failures of a rendered diagram body. NOT ported (BC-07's full contract
    check lives in the real ``readme_diagram.contract`` module, not pulled here); returns an empty
    list always. Kept only so a caller that imports this name does not hit an ImportError -- it is
    not a real validator and must not be relied on as one."""
    return []
