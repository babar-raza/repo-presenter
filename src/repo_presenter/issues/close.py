"""Close / re-detection: transition a ``FILED`` handoff to ``RESOLVED_UPSTREAM`` only when
independent re-detection confirms the defect no longer reproduces -- never on say-so alone, and
never on the mere ABSENCE of contrary evidence.

2026-11-04 (TC-010, corrected 2026-11-04 by the P0 follow-up directive section 7). ``file.py``'s
own comment states this step was "NOT ported this pass, deliberately" from the legacy
repository -- confirmed absent. This is new code on the same ``Handoff`` model; it reuses
``model.write_handoff`` for persistence rather than inventing a second writer.

The directive's own finding: the first version of this module treated a triggering fact that had
disappeared entirely (extraction failure, a renamed check id, incomplete toolchain evidence) as
equivalent to a verified fix, because ``redetect()`` returned a bare ``bool`` with only two
states. Missing evidence is not proof a defect was fixed -- it is exactly as unsafe to close on
as no evidence at all. ``redetect()`` now returns one of three distinct outcomes, and only
``VERIFIED_RESOLVED`` -- the fact still exists and is no longer ``CONTRADICTED`` -- may complete
a ``reason="completed"`` close; both ``STILL_REPRODUCES`` and the new ``NOT_VERIFIABLE`` refuse
it identically.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Literal

from repo_presenter.core.facts import Fact
from repo_presenter.issues.model import CloseReason, Handoff, write_handoff

RedetectionOutcome = Literal["VERIFIED_RESOLVED", "STILL_REPRODUCES", "NOT_VERIFIABLE"]


class CloseRefusal(ValueError):
    """A close was requested but the evidence does not support it."""


def redetect(handoff: Handoff, current_facts_by_id: dict[str, Fact]) -> RedetectionOutcome:
    """Re-run the exact check that originally triggered this handoff against a fresh facts
    document and classify the result:

    - ``VERIFIED_RESOLVED``: the fact still exists and is no longer ``CONTRADICTED`` -- a real,
      positive re-detection that the defect is gone.
    - ``STILL_REPRODUCES``: the fact still exists and is still ``CONTRADICTED`` -- not fixed.
    - ``NOT_VERIFIABLE``: the fact is absent from the current facts document entirely (removed
      check, renamed id, an extraction or toolchain gap). Absence is not evidence of a fix, so
      this is its own distinct, unresolved outcome -- never folded into ``VERIFIED_RESOLVED``.

    Looked up by ``handoff.triggering_check.id`` (the real, readable fact id discovery.py
    preserved there) -- never by ``defect_fingerprint``, which is a one-way sha256 digest
    (approval.py's own handoff_id() contract) and cannot be used to look anything back up."""
    current = current_facts_by_id.get(handoff.triggering_check.id)
    if current is None:
        return "NOT_VERIFIABLE"
    if current.polarity == "CONTRADICTED":
        return "STILL_REPRODUCES"
    return "VERIFIED_RESOLVED"


def close_handoff(
    handoff: Handoff,
    *,
    current_facts_by_id: dict[str, Fact],
    reason: CloseReason,
    path: Path,
) -> Handoff:
    """Transition ``FILED`` -> ``RESOLVED_UPSTREAM``. Only a ``FILED`` handoff may be closed
    (nothing was ever opened upstream for ``HANDOFF_PENDING``/``HANDOFF_ACKNOWLEDGED`` to
    close). ``reason="completed"`` additionally requires re-detection to report
    ``VERIFIED_RESOLVED``; ``reason="not planned"`` (a check-version change, a false positive, or
    an owner-authorized withdrawal) does not, since there is nothing left to re-detect against
    by definition."""
    if handoff.status != "FILED":
        raise CloseRefusal(f"cannot close a handoff in status {handoff.status!r}; only FILED")
    if reason == "completed":
        outcome = redetect(handoff, current_facts_by_id)
        if outcome == "STILL_REPRODUCES":
            raise CloseRefusal(
                "reason='completed' requires re-detection to confirm the defect no longer "
                "reproduces, but the triggering fact is still CONTRADICTED"
            )
        if outcome == "NOT_VERIFIABLE":
            raise CloseRefusal(
                "reason='completed' requires re-detection to report VERIFIED_RESOLVED, but the "
                "triggering check "
                f"{handoff.triggering_check.id!r} is absent from the current facts document "
                "(extraction failure, a renamed check, or incomplete toolchain evidence); "
                "absence of the fact is not proof the defect was fixed"
            )
    resolved = replace(handoff, status="RESOLVED_UPSTREAM", close_reason=reason)
    write_handoff(resolved, path)
    return resolved
