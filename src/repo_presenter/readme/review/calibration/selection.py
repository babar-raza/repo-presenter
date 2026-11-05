"""Which cases a measurement asks, decided before any reviewer output exists.

Every choice here ranks cases by the SHA-256 of their id, so the selection is reproducible and no
verdict can influence which cases are asked or repeated.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from repo_presenter.readme.review.calibration.corpus import Case


def rank(case: Case) -> str:
    return hashlib.sha256(case.case_id.encode("utf-8")).hexdigest()


def cap_real_defects(cases: Sequence[Case], per_base: int) -> list[Case]:
    """``cases`` with at most ``per_base`` real-defect cases of each base (hash-ranked); every other
    case is kept in its order. ``per_base`` < 0 keeps them all."""
    if per_base < 0:
        return list(cases)
    kept: set[str] = set()
    by_base: dict[str, list[Case]] = {}
    for case in cases:
        if case.role == "real_defect":
            by_base.setdefault(case.base, []).append(case)
    for members in by_base.values():
        kept.update(c.case_id for c in sorted(members, key=rank)[:per_base])
    return [c for c in cases if c.role != "real_defect" or c.case_id in kept]


def stability_subset(cases: Sequence[Case], size: int) -> list[Case]:
    """Half scored clean twins, half defect cases (mutants and real defects), each half
    hash-ranked."""
    clean = sorted((c for c in cases if c.role == "clean"), key=rank)
    defects = sorted(
        (c for c in cases if c.role in {"mutant", "real_defect"}), key=rank
    )
    return clean[: size - size // 2] + defects[: size // 2]
