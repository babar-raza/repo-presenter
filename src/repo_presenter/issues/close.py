"""Close / re-detection: transition a ``FILED`` handoff to ``RESOLVED_UPSTREAM`` only when
independent re-detection confirms the defect no longer reproduces -- never on say-so alone.

2026-11-04 (TC-010). ``file.py``'s own comment states this step was "NOT ported this pass,
deliberately" from the legacy repository -- confirmed absent. This is new code on the same
``Handoff`` model; it reuses ``model.write_handoff`` for persistence rather than inventing a
second writer, and refuses exactly the two cases a close must never allow: closing something
that was never filed, and closing as "completed" (a genuine upstream fix) when re-detection
still finds the exact fact that triggered the handoff contradicted.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from repo_presenter.core.facts import Fact
from repo_presenter.issues.model import CloseReason, Handoff, write_handoff


class CloseRefusal(ValueError):
    """A close was requested but the evidence does not support it."""


def redetect(handoff: Handoff, current_facts_by_id: dict[str, Fact]) -> bool:
    """True if the exact fact that triggered this handoff no longer reproduces as
    ``CONTRADICTED`` against a fresh facts document -- i.e. the defect appears fixed. A fact
    that no longer exists at all (removed, renamed) can no longer be contradicted, so this
    also returns True; a fact still present and still CONTRADICTED returns False.

    Looked up by ``handoff.triggering_check.id`` (the real, readable fact id discovery.py
    preserved there) -- never by ``defect_fingerprint``, which is a one-way sha256 digest
    (approval.py's own handoff_id() contract) and cannot be used to look anything back up."""
    current = current_facts_by_id.get(handoff.triggering_check.id)
    if current is None:
        return True
    return current.polarity != "CONTRADICTED"


def close_handoff(
    handoff: Handoff,
    *,
    current_facts_by_id: dict[str, Fact],
    reason: CloseReason,
    path: Path,
) -> Handoff:
    """Transition ``FILED`` -> ``RESOLVED_UPSTREAM``. Only a ``FILED`` handoff may be closed
    (nothing was ever opened upstream for ``HANDOFF_PENDING``/``HANDOFF_ACKNOWLEDGED`` to
    close). ``reason="completed"`` additionally requires re-detection to confirm the defect no
    longer reproduces; ``reason="not planned"`` (a check-version change or a false positive)
    does not, since there is nothing left to re-detect against by definition."""
    if handoff.status != "FILED":
        raise CloseRefusal(f"cannot close a handoff in status {handoff.status!r}; only FILED")
    if reason == "completed" and not redetect(handoff, current_facts_by_id):
        raise CloseRefusal(
            "reason='completed' requires re-detection to confirm the defect no longer "
            "reproduces, but the triggering fact is still CONTRADICTED"
        )
    resolved = replace(handoff, status="RESOLVED_UPSTREAM", close_reason=reason)
    write_handoff(resolved, path)
    return resolved
