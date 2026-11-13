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
to enforce; ``draw_at_a_glance`` emits a top-to-bottom Mermaid ``flowchart`` (``layout_glance``)
-- a Starting Points group (omitted if there are no verified input formats), the product, a Core
Capabilities group of at most three nodes to a row, and an Outputs group (omitted if there are no
verified output formats). Its width is bounded by a calibrated estimate (``estimated_width``) and
measured with the real Mermaid 10.9.1 (2026-11-13: all 26 certified diagrams 398-741 px at their
natural size, from 509-3054 px), not by the old builder's font-measured geometry proof.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

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


#: The width (CSS px) an At a Glance diagram must fit at its natural size, so it is read without
#: scaling or horizontal scrolling: a README column on GitHub and on the review page. Owner feedback
#: (2026-11-13, on Cells Java Lane L): "At a Glance should practically be At a Glance"; the earlier
#: shape measured 509-3054 px wide under the real Mermaid 10.9.1.
GLANCE_WIDTH_BUDGET = 800
#: At most this many nodes side by side in one row of a group; further nodes start a new row.
GLANCE_COLUMNS = 3
#: Characters per label line before a ``<br/>`` break (a label is never shortened, only wrapped).
GLANCE_WRAP = 22
#: The product node's emphasis: white on a mid blue reads on both GitHub's light and dark themes.
PRODUCT_STYLE = "classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff"
#: Rough Mermaid default-font geometry (trebuchet 16px, flowchart defaults), calibrated against the
#: 26 certified diagrams rendered with Mermaid 10.9.1 at an 800 px container; an estimate for the
#: Lane L trigger and the regression bound, never a substitute for the browser measurement.
_CHAR_PX = 7.6
_NODE_PAD = 32
_NODE_GAP = 50
_GROUP_PAD = 32

_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_MARKUP = re.compile(r"[&<>]")
_ID = r"[A-Za-z_][A-Za-z0-9_]*"
_SUBGRAPH = re.compile(rf'^subgraph ({_ID})\["([^"]*)"\]$')
_NODE = re.compile(rf'^({_ID})\["([^"]*)"\]$')
_DIRECTION = re.compile(r"^direction (TB|TD|BT|LR|RL)$")
_HEADER = re.compile(r"^(?:flowchart|graph) (TB|TD|BT|LR|RL)$")
_INVISIBLE = re.compile(rf"^({_ID}) ~~~ ({_ID})$")
_CHAIN = re.compile(rf"^{_ID}(?: --> {_ID})+$")
_PRODUCT_CLASS = re.compile(rf"^class {_ID} product$")


@dataclass(frozen=True)
class GlanceGroup:
    """One titled group of the diagram (Starting Points, Core Capabilities, Outputs): its Mermaid
    id, its title, and its nodes as ``(id, plain label)`` in document order."""

    id: str
    title: str
    nodes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Glance:
    """What an At a Glance diagram says, apart from how it is laid out: the product node, the
    groups, and the one chain joining them (group ids and the product id, in order)."""

    product_id: str
    product: str
    groups: tuple[GlanceGroup, ...]
    chain: tuple[str, ...]
    preamble: tuple[str, ...] = ()

    def content(self) -> tuple[object, ...]:
        """Everything a reader sees, layout aside: equal for a diagram and its re-layout."""
        return (
            self.product_id,
            self.product,
            tuple((group.id, group.title, group.nodes) for group in self.groups),
            self.chain,
        )


def plain_label(label: str) -> str:
    """A label as read: line breaks are spaces, runs of white space are one space."""
    return " ".join(_BREAK.sub(" ", label).split())


def wrap_label(text: str, width: int = GLANCE_WRAP) -> str:
    """``text`` broken at word boundaries into lines of at most ``width`` characters (a longer
    single word keeps a line of its own), joined by ``<br/>``. Never shortens, never reorders. A
    label holding ``&``, ``<`` or ``>`` is returned byte for byte: Mermaid releases differ on how
    they draw those, and a break beside them is not this function's to risk."""
    if _MARKUP.search(text):
        return text
    lines: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return "<br/>".join(lines)


def columns_for(count: int) -> int:
    """Nodes per row for a group of ``count``: one row up to two, a square for four, else three."""
    if count <= 2:
        return max(count, 1)
    if count == 4:
        return 2
    return GLANCE_COLUMNS


def _grid(nodes: Sequence[tuple[str, str]], indent: str) -> list[str]:
    """Node declarations, then the invisible links that hold them in rows: every node of a row
    that is not the last links to the node below it (or, under a short last row, to that row's
    last node), so no node is left unlinked -- an unlinked node is free to sink to any row."""
    lines = [f'{indent}{node_id}["{wrap_label(label)}"]' for node_id, label in nodes]
    columns = columns_for(len(nodes))
    ids = [node_id for node_id, _ in nodes]
    rows = [ids[start : start + columns] for start in range(0, len(ids), columns)]
    for upper, lower in itertools.pairwise(rows):
        lines.extend(
            f"{indent}{node_id} ~~~ {lower[min(column, len(lower) - 1)]}"
            for column, node_id in enumerate(upper)
        )
    return lines


def _group_lines(group: GlanceGroup) -> list[str]:
    lines = [f'  subgraph {group.id}["{group.title}"]', "    direction TB"]
    lines.extend(_grid(group.nodes, "    "))
    lines.append("  end")
    return lines


def layout_glance(glance: Glance) -> list[str]:
    """The diagram body (no fence markers), laid out to be read at a glance: top to bottom, each
    group a box whose nodes sit at most :data:`GLANCE_COLUMNS` to a row (invisible ``~~~`` links
    start the next row, so the diagram grows down, never across), every label wrapped at
    :data:`GLANCE_WRAP` characters, the product node emphasised. Labels, titles, ids and the chain are exactly ``glance``'s: only the layout is chosen here."""
    groups = {group.id: group for group in glance.groups}
    lines = [*glance.preamble, "flowchart TB"]
    for part in glance.chain:
        if part == glance.product_id:
            lines.append(f'  {glance.product_id}["{glance.product}"]')
        else:
            lines.extend(_group_lines(groups[part]))
    lines.append("  " + " --> ".join(glance.chain))
    lines.append(f"  {PRODUCT_STYLE}")
    lines.append(f"  class {glance.product_id} product")
    return lines


def parse_glance(body: str) -> Glance | None:
    """The :class:`Glance` an At a Glance body states, or ``None`` when the body holds anything
    beyond the presenter's own diagram grammar (one product node, titled groups of labelled nodes,
    optionally nested in untitled bands, directions, invisible links, one chain, the product
    style): a diagram this does not fully understand is never redrawn."""
    preamble: list[str] = []
    header_seen = False
    stack: list[str] = []
    groups: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    product: tuple[str, str] | None = None
    chain: tuple[str, ...] | None = None
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not header_seen:
            if line.startswith("%%{") and line.endswith("}%%"):
                preamble.append(line)
                continue
            if _HEADER.match(line):
                header_seen = True
                continue
            return None
        if match := _SUBGRAPH.match(line):
            if not stack:
                if match.group(1) in groups:
                    return None
                groups[match.group(1)] = (match.group(2), [])
            elif match.group(2).strip():
                return None  # a titled nested group carries meaning a re-layout would lose
            stack.append(match.group(1))
        elif line == "end":
            if not stack:
                return None
            stack.pop()
        elif _DIRECTION.match(line) or _INVISIBLE.match(line):
            continue
        elif match := _NODE.match(line):
            if stack:
                groups[stack[0]][1].append((match.group(1), plain_label(match.group(2))))
            elif product is None:
                product = (match.group(1), match.group(2))
            else:
                return None
        elif _CHAIN.match(line):
            if chain is not None:
                return None
            chain = tuple(part.strip() for part in line.split("-->"))
        elif line == PRODUCT_STYLE or _PRODUCT_CLASS.match(line):
            continue
        else:
            return None
    if stack or product is None or chain is None or not header_seen:
        return None
    if len(set(chain)) != len(chain) or sorted(chain) != sorted([product[0], *groups]):
        return None
    if any(not nodes for _, nodes in groups.values()):
        return None
    node_ids = [node_id for _, nodes in groups.values() for node_id, _ in nodes]
    if len(set(node_ids)) != len(node_ids) or product[0] in node_ids:
        return None
    return Glance(
        product_id=product[0],
        product=product[1],
        groups=tuple(
            GlanceGroup(group_id, groups[group_id][0], tuple(groups[group_id][1]))
            for group_id in chain
            if group_id in groups
        ),
        chain=chain,
        preamble=tuple(preamble),
    )


def _node_px(label: str) -> float:
    longest = max((len(line) for line in _BREAK.split(label)), default=0)
    return longest * _CHAR_PX + _NODE_PAD


@dataclass
class _Frame:
    """One open group while :func:`estimated_width` reads a body: its id, its layout direction,
    its items (nodes and finished inner groups, each with a width) and its invisible links."""

    id: str
    direction: str
    items: list[tuple[str, float]] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)

    def width(self) -> float:
        if not self.items:
            return 0.0
        # Each item's rank is one past its lowest linked predecessor (links only ever point on).
        rank = {item_id: 0 for item_id, _ in self.items}
        for _ in self.items:
            for upper, lower in self.links:
                if upper in rank and lower in rank:
                    rank[lower] = max(rank[lower], rank[upper] + 1)
        ranks: dict[int, list[float]] = {}
        for item_id, px in self.items:
            ranks.setdefault(rank[item_id], []).append(px)
        if self.direction in {"LR", "RL"}:
            # Ranks run across; the items of one rank stack down.
            inner = sum(max(row) for row in ranks.values()) + _NODE_GAP * (len(ranks) - 1)
        else:
            # Ranks run down; the items of one rank -- every unlinked sibling -- sit side by side.
            inner = max(sum(row) + _NODE_GAP * (len(row) - 1) for row in ranks.values())
        return inner + _GROUP_PAD


def estimated_width(body: str) -> float:
    """The natural width of ``body`` in CSS px, by the calibrated geometry above. A group lays its
    ranks along its direction: in a top-down group every unlinked sibling shares one rank and so
    one row (the shape that made the earlier diagrams sprawl -- ``direction TB`` over a list of
    unlinked nodes draws them ACROSS), invisible links start further rows, and a finished inner
    group counts as one item of its parent. The top level is the widest of its parts."""
    frames = [_Frame("", "TB")]
    widest = 0.0
    for raw in body.splitlines():
        line = raw.strip()
        if match := _HEADER.match(line):
            frames[0].direction = match.group(1)
        elif match := _SUBGRAPH.match(line):
            frames.append(_Frame(match.group(1), frames[-1].direction))
        elif line == "end" and len(frames) > 1:
            frame = frames.pop()
            px = frame.width()
            widest = max(widest, px)
            frames[-1].items.append((frame.id, px))
        elif match := _DIRECTION.match(line):
            frames[-1].direction = match.group(1)
        elif match := _INVISIBLE.match(line):
            frames[-1].links.append((match.group(1), match.group(2)))
        elif match := _NODE.match(line):
            frames[-1].items.append((match.group(1), _node_px(match.group(2))))
    return max([widest, *(px for _, px in frames[0].items)])


def draw_at_a_glance(
    *,
    product: str,
    starting_points: Sequence[str],
    capability_titles: Sequence[str],
    outputs: Sequence[str],
) -> list[str]:
    """The fenced Mermaid block of the diagram: Starting Points, the product, Core Capabilities
    and Outputs, top to bottom (:func:`layout_glance`); a group with nothing verified is omitted
    with its hop. Every node is one verified input, capability title or output, as given."""

    def group(group_id: str, title: str, prefix: str, texts: Sequence[str]) -> GlanceGroup:
        return GlanceGroup(
            group_id,
            title,
            tuple(
                (f"{prefix}{index}", " ".join(_UNSAFE_LABEL.sub("", text).split()))
                for index, text in enumerate(texts, start=1)
            ),
        )

    before = [group("StartingPoints", "Starting Points", "i", starting_points)]
    after = [group("Capabilities", "Core Capabilities", "c", capability_titles)]
    before = before if starting_points else []
    after = after if capability_titles else []
    if outputs:
        after.append(group("Outputs", "Outputs", "o", outputs))
    glance = Glance(
        product_id="PRODUCT",
        product=" ".join(_UNSAFE_LABEL.sub("", product).split()),
        groups=(*before, *after),
        chain=(*(g.id for g in before), "PRODUCT", *(g.id for g in after)),
    )
    return ["```mermaid", *layout_glance(glance), "```"]


def diagram_failures(body: str, has_inputs: bool) -> list[str]:
    """Geometry/topology failures of a rendered diagram body. NOT ported (BC-07's full contract
    check lives in the real ``readme_diagram.contract`` module, not pulled here); returns an empty
    list always. Kept only so a caller that imports this name does not hit an ImportError -- it is
    not a real validator and must not be relied on as one."""
    return []
