"""Structure and size parity between one of our READMEs and the aspose.org candidate for the same
product, as numbers.

The reference text is read at run time from the sibling ``aspose.org`` checkout and is never copied,
stored or returned: only counts and heading names come out. This is a measurement, not a gate: it
says how close a candidate is to the reference, and the calibrated reviewer remains the acceptance
authority.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

CANDIDATE_STORE = Path("reports") / "repo-presenter-regen-full"
_HEADING = re.compile(r"^(#{1,3}) +(.+?) *#*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_LINK = re.compile(r"\]\((https?://[^)\s]+)")
_ASPOSE_LINK = re.compile(r"https?://[^)\s\"']*aspose\.(?:org|com)", re.IGNORECASE)


@dataclass(frozen=True)
class Shape:
    lines: int
    code_fences: int
    details_blocks: int
    links: int
    aspose_links: int
    mermaid_diagrams: int
    headings: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class Parity:
    ours: Shape
    reference: Shape
    missing_headings: tuple[str, ...]
    extra_headings: tuple[str, ...]
    shared_order_agrees: bool

    @property
    def missing_h2(self) -> tuple[str, ...]:
        wanted = {name for level, name in self.reference.headings if level == 2}
        return tuple(name for name in self.missing_headings if name in wanted)

    @property
    def line_ratio(self) -> float:
        return round(self.ours.lines / self.reference.lines, 2) if self.reference.lines else 0.0


def _normal(name: str) -> str:
    return " ".join(re.sub(r"[`*_]", "", name).lower().split())


def measure(markdown: str) -> Shape:
    headings: list[tuple[int, str]] = []
    fences = 0
    in_fence = False
    mermaid = 0
    for line in markdown.splitlines():
        if _FENCE.match(line):
            if not in_fence:
                fences += 1
                if "mermaid" in line.lower():
                    mermaid += 1
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        found = _HEADING.match(line)
        if found:
            headings.append((len(found.group(1)), _normal(found.group(2))))
    return Shape(
        lines=len(markdown.splitlines()),
        code_fences=fences,
        details_blocks=len(re.findall(r"(?i)<details\b", markdown)),
        links=len(_LINK.findall(markdown)),
        aspose_links=len(_ASPOSE_LINK.findall(markdown)),
        mermaid_diagrams=mermaid,
        headings=tuple(headings),
    )


def compare(ours: str, reference: str) -> Parity:
    mine, theirs = measure(ours), measure(reference)
    ours_names = [name for _, name in mine.headings]
    their_names = [name for _, name in theirs.headings]
    shared_ours = [name for name in ours_names if name in set(their_names)]
    shared_theirs = [name for name in their_names if name in set(ours_names)]
    return Parity(
        ours=mine,
        reference=theirs,
        missing_headings=tuple(name for name in their_names if name not in set(ours_names)),
        extra_headings=tuple(name for name in ours_names if name not in set(their_names)),
        shared_order_agrees=shared_ours == shared_theirs,
    )


def reference_path(aspose_root: Path, family: str, platform: str) -> Path:
    return aspose_root / CANDIDATE_STORE / family / platform / "readme.md"


def render(label: str, parity: Parity) -> str:
    o, r = parity.ours, parity.reference
    rows: Sequence[tuple[str, object, object]] = (
        ("lines", o.lines, r.lines),
        ("code fences", o.code_fences, r.code_fences),
        ("<details>", o.details_blocks, r.details_blocks),
        ("links", o.links, r.links),
        ("aspose links", o.aspose_links, r.aspose_links),
        ("mermaid", o.mermaid_diagrams, r.mermaid_diagrams),
    )
    out = [f"{label}", f"  {'':<14}{'ours':>8}{'reference':>12}"]
    out += [f"  {name:<14}{ours:>8}{ref:>12}" for name, ours, ref in rows]
    out.append(f"  line ratio {parity.line_ratio}; shared headings in the same order: "
               f"{parity.shared_order_agrees}")
    out.append(f"  missing H2 sections : {list(parity.missing_h2) or 'none'}")
    out.append(f"  other missing       : {[h for h in parity.missing_headings if h not in parity.missing_h2]}")
    out.append(f"  only in ours        : {list(parity.extra_headings)}")
    return "\n".join(out)
