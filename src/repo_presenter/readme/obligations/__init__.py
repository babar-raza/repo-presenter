"""TC-018: the pre-generation obligations inventory, generalizing the R14 drop-inventory rule
table (``docs/investigations/2026-11-06-drop-inventory.md``) from DROPPED items only to every
inherited unit a candidate's reconciliation touches.

``classify.py`` decides, from mechanical facts alone, whether a unit is ``must_carry``,
``may_drop`` or ``undecided`` -- before or independent of any particular candidate.
``ledger.py`` builds the byte-computed content ledger: one record per live-README item, its
obligation, its actual disposition in a candidate, and the evidence for that outcome.

This package does not itself wire a verification check into the candidate pipeline's own blocking
checks; ``readme/validation/supersession.py``'s ``obligation_failures`` (called from
``readme/validation/units.py``'s ``disposition_failures``) does that, importing from here.
"""

from __future__ import annotations

from repo_presenter.readme.obligations.classify import (
    FILLER_DESCRIPTION,
    UNIT_KINDS,
    Obligation,
    Unit,
    UnitFacts,
    classify_unit,
)
from repo_presenter.readme.obligations.ledger import (
    LedgerEntry,
    build_ledger,
    ledger_from_candidate,
)

__all__ = [
    "FILLER_DESCRIPTION",
    "UNIT_KINDS",
    "LedgerEntry",
    "Obligation",
    "Unit",
    "UnitFacts",
    "build_ledger",
    "classify_unit",
    "ledger_from_candidate",
]
