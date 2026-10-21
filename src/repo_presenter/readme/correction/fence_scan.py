"""Which lines of a README lie inside a fenced code block.

Ported (REUSE, verbatim) from the old repository's
``components/readme/review/acceptance/text_checks.py`` -- but only the ``scan``/``Line`` slice of
that module: a low-level, stdlib-only fence-state scanner, not any of its validator predicates
(``single_h1``, ``edition_name``, ``assurance_narration``, ...). Those predicates are the BC-04/
BC-14-adjacent acceptance chain `docs/MISSION_AUTHORITY.md`'s critical-fact section names as having
a demonstrated, owner-confirmed blind spot ("No component from that chain may be pulled with a
REUSE disposition"); ``scan`` itself renders no verdict about a README, it only reports fence
state, so it carries none of that risk and needs none of that scrutiny.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class Line:
    number: int
    text: str
    code: bool
    opener: bool = False
    info: str = ""


def scan(readme: str) -> list[Line]:
    """Every line with its 1-based number, marked as code when it lies inside a fence."""
    lines: list[Line] = []
    fence: tuple[str, int] | None = None
    for number, text in enumerate(readme.splitlines(), start=1):
        match = _FENCE.match(text)
        if fence is None:
            if match:
                fence = (match.group(1)[0], len(match.group(1)))
                lines.append(Line(number, text, True, opener=True, info=match.group(2).strip()))
            else:
                lines.append(Line(number, text, False))
        else:
            closing = (
                match is not None
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and not match.group(2).strip()
            )
            if closing:
                fence = None
            lines.append(Line(number, text, True))
    return lines
