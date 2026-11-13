"""An At a Glance diagram too wide to read at a glance, laid out again with its content unchanged.

Owner feedback (2026-11-13, on the certified Lane L candidate Cells Java @ c65329e7257b, and in
chat as a portfolio-wide requirement): "Right now At a Glance is too much to absorb and needs a lot
of horizontal scrolling in browser ... At a Glance should practically be At a Glance". The live
READMEs carry the earlier repository-presenter's diagram: ``flowchart TD`` whose groups list their
nodes with no links between them. Mermaid ranks unlinked siblings together, so each group draws as
ONE row whatever its ``direction`` says, and with unwrapped labels the diagram measured up to
3054 px wide under the real Mermaid 10.9.1 (19 of the 21 certified Lane L diagrams over 800 px).

The fix is layout only, never content. The detector fires only when the diagram is entirely in the
presenter's own grammar (``glance.parse_glance``: one product node, titled groups of labelled nodes,
one chain -- anything else is left alone) AND its estimated natural width exceeds
``glance.GLANCE_WIDTH_BUDGET``. The replacement is ``glance.layout_glance`` of the very same parsed
content, and it is emitted only after proving that re-parsing it yields exactly that content (every
node id, label text, group title and the chain; a label gains ``<br/>`` line breaks only) and that
it fits the budget. Evidence is the README's own fence (a ``README.md:<line>`` locator), as for
every ``DIAGRAM_FIX``.

The owner named the sprawl a defect and a portfolio-wide requirement, so the redraw is an evidenced
Lane L edit in its own right (measured: the estimate is calibrated on the real renders), on a
no-change candidate too -- Cells Java, the candidate the feedback was given on, is one. It is not,
though, the defect R21 lets a run carry residual content defects on: ``lane_l_review.
net_improvement`` needs a content edit for that (``LAYOUT_ONLY_DETECTORS``), so a redrawn diagram
never certifies a README that still states something a verified fact contradicts.
"""

from __future__ import annotations

import re

from repo_presenter.readme.composition.components.glance import (
    GLANCE_WIDTH_BUDGET,
    estimated_width,
    layout_glance,
    parse_glance,
)
from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.fence_scan import scan
from repo_presenter.readme.correction.model import (
    DIAGRAM_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
)

NAME = "glance_layout"
#: Detectors whose edits change how the README looks, never what it says.
LAYOUT_ONLY_DETECTORS: frozenset[str] = frozenset({NAME})
_OPEN = re.compile(r"^[ \t]{0,3}```[ \t]*mermaid[ \t]*$", re.IGNORECASE)
_CLOSE = re.compile(r"^[ \t]{0,3}```[ \t]*$")


@detector(NAME)
def glance_layout(ctx: Context) -> DetectorResult:
    edits: list[Edit] = []
    findings: list[Finding] = []
    lines = ctx.lines
    openers = {line.number for line in scan(ctx.readme) if line.opener}
    index = 0
    while index < len(lines):
        opener = lines[index]
        if opener.number not in openers or not _OPEN.match(opener.text):
            index += 1
            continue
        closer = next(
            (j for j in range(index + 1, len(lines)) if _CLOSE.match(lines[j].text)), None
        )
        if closer is None or closer == index + 1:
            break
        start, end = lines[index + 1].start, lines[closer].start
        body = ctx.readme[start:end]
        index = closer + 1
        glance = parse_glance(body)
        if glance is None:
            continue
        before = estimated_width(body)
        if before <= GLANCE_WIDTH_BUDGET:
            continue
        locator = f"{ctx.readme_path}:{opener.number}"
        newline = "\r\n" if "\r\n" in body else "\n"
        replacement = newline.join(layout_glance(glance)) + newline
        after = estimated_width(replacement)
        again = parse_glance(replacement)
        if again is None or again.content() != glance.content() or after > GLANCE_WIDTH_BUDGET:
            findings.append(
                Finding(
                    NAME,
                    opener.number,
                    "",
                    f"the At a Glance diagram is about {before:.0f} px wide and its re-layout "
                    "would not keep its content or fit; not redrawn",
                    report_only_reason="DIAGRAM_CONTRACT_FAILS",
                    candidate=replacement,
                    locators=(locator,),
                )
            )
            continue
        if replacement == body:
            continue
        edits.append(
            Edit(
                DIAGRAM_FIX,
                NAME,
                start,
                end,
                body,
                replacement,
                (),
                f"the At a Glance diagram draws about {before:.0f} px wide (budget "
                f"{GLANCE_WIDTH_BUDGET} px): its groups laid out top to bottom, at most three "
                f"nodes to a row, labels wrapped -- about {after:.0f} px; every label, group title "
                "and the chain unchanged",
                locators=(locator,),
            )
        )
    return DetectorResult(tuple(edits), tuple(findings))
