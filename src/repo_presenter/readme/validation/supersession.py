"""BC-05 (supersession): a unit judged SUPERSEDE_REDUNDANT is not printed because its replacement
carries all of its substance -- so the README must state that substance.

Why a check and not only a prompt rule (owner decision 2026-11-06, docs/DECISION_LOG.md): the
source_reconciliation v14 rule ("superseded only when the replacement carries all of its substance:
listed values, conditions, when/why insight") was in force for the 2026-11-06 hosted pilot, and the
new Email .NET candidate still superseded "runs on Windows, Linux, macOS, Docker containers, and
serverless functions" and the ``CfbReader`` note "useful when diagnosing a damaged or non-standard
file"; neither appears in its README. A model's claim that content is carried is tested here the
way an advisory deferral's "nothing lost" is (``validation/deferrals.py``), with
``content_presence.unstated(strict=True)``: a sentence that spells an anchor the README prints
(``.NET 8.0``) must still have its other words carried.

A failure is RECONCILING and names its unit, so the repair loop re-reconciles that one unit with
the missing pieces quoted (keep it, move it, or attribute it), and a candidate that still loses the
content is rejected. Exempt, because the renderer replaces them by design and the reader loses
nothing a maintainer wrote: headings, badge rows, raw HTML wrappers, the mermaid diagram (the
renderer draws At a Glance from verified facts), and a lead-in carried with its block.
"""

from __future__ import annotations

from repo_presenter.readme.composition.references import positional_only
from repo_presenter.readme.validation.content_presence import unstated
from repo_presenter.readme.validation.failures import Candidate, Failure

SUPERSEDED = "SUPERSEDE_REDUNDANT"
# The phrase every failure of this check carries; reconciliation/patch.py reads it to require that a
# repair of such a unit stops superseding it.
LOSS_MARKER = "is SUPERSEDE_REDUNDANT, but the README does not state"
EXEMPT_KINDS = frozenset({"heading", "badge_row", "html_block"})
_LEAD_IN = "lead-in of the block that follows"
_SHOWN = 4


def _kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _diagram(text: str) -> bool:
    return text.lstrip().lstrip("`~").lstrip().lower().startswith("mermaid")


def exempt(unit_id: str, text: str, rationale: str) -> bool:
    """Whether a superseded unit is markup the renderer replaces by design."""
    kind = _kind(unit_id)
    if kind in EXEMPT_KINDS:
        return True
    if kind == "code_block" and _diagram(text):
        return True
    if kind == "paragraph" and positional_only(text):
        # "A few more patterns beyond the Quick Start example above." (Email .NET, 2026-11-06 local
        # pilot): kept by a repair, it became a BC-07 dangling reference.
        return True
    return _LEAD_IN in rationale.lower()


def superseded_failures(candidate: Candidate) -> list[Failure]:
    """One RECONCILING failure per superseded unit whose substance the README does not state."""
    texts = {
        fact.id: str(fact.value or "")
        for fact in candidate.facts.by_kind("inherited_unit")
    }
    failures: list[Failure] = []
    for entry in candidate.dispositions.get("dispositions", []):
        if entry.get("disposition") != SUPERSEDED:
            continue
        unit_id = str(entry.get("unit_id", ""))
        text = texts.get(unit_id, "")
        if not text.strip() or exempt(unit_id, text, str(entry.get("rationale") or "")):
            continue
        missing = unstated(text, candidate.readme, kind=_kind(unit_id), strict=True)
        if not missing:
            continue
        shown = "; ".join(missing[:_SHOWN])
        failures.append(
            Failure(
                "RECONCILING",
                f"{unit_id} {LOSS_MARKER} "
                f"{len(missing)} piece(s) of it ({shown}): a superseded unit's replacement must "
                "carry all of its substance; keep it (VERIFIED_PRESERVE/VERIFIED_MOVE), or "
                "PRESERVE_ATTRIBUTED when no fact confirms it",
                unit=unit_id,
            )
        )
    return failures
