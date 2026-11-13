"""BC-17 (parity, owner ruling R2): a candidate must not lose content of the README it replaces.

R2 (``docs/CONSOLIDATED_GOALS_2026-11-06.md`` Part B): the published README is the minimum
quality floor, so a candidate that drops a benchmark code block, install command, API identifier,
link, version number or section is not a candidate. ``ops/checks/parity_gate.py`` measured that and
the pipeline did not enforce it: Imaging .NET Lane R sealed after the model gave the maintainers'
``<ProjectReference ...csproj />`` block (``inherited_unit:018.code_block``) OMIT_UNSUPPORTED as
"promotional", which the gate reports lost.

One standard, never two: the judgement is ``parity_gate.content_losses`` -- the very function
whose dimensions the parity gate prints -- run over this candidate and its own benchmark, the
original README the run read (``Candidate.benchmark_readme``; no network). Its exemptions are
therefore exactly the gate's: a CONTRADICTED fact, ``NON_CONTENT``/``CORRECT_WITH_EVIDENCE``, an
omission that cites a contradicted fact or states the content obsolete/incorrect, replacement by
the verified install command or published version, and a maintainers' diagram the renderer draws
anew.

A lost item held by an inherited unit fails RECONCILING with that unit's ID, so the per-unit S4
repair re-reconciles it, and ``reconciliation/patch.py`` refuses a reply that keeps it lost
(:data:`PARITY_LOSS_MARKER` marks such a failure). An item no unit holds fails at the stage that
should have carried it (``EXTRACTING`` for a technical item, ``PLANNING`` for a section).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.parity_gate import LANE_R, SealedCandidate, content_losses
from repo_presenter.readme.validation.failures import Candidate, Failure

# The phrase every unit failure of this check carries; reconciliation/patch.py reads it to require
# that a repair of such a unit stops giving it a disposition that loses it.
PARITY_LOSS_MARKER = "which the published README prints and this candidate loses"


def _fact_rows(candidate: Candidate) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "id": fact.id,
            "kind": fact.kind,
            "value": fact.value,
            "polarity": fact.polarity,
            "attributes": fact.attributes,
            # The evidence rows a sealed facts.json carries: the registry reading lives there, and
            # ``unconfirmed_registry_packages`` reads it to exempt the registry install BC-02 forbids
            # printing (Aspose.3D-FOSS-for-Python run 43411932927: without it BC-17 demanded
            # ``python3 -m pip install aspose-3d-foss`` that BC-02 rejects once restored).
            "evidence": [
                {"path": item.path, "detail": item.detail}
                for item in getattr(fact, "evidence", ())
            ],
        }
        for fact in candidate.facts.facts
    )


def sealed_view(candidate: Candidate) -> SealedCandidate:
    """The candidate as the parity gate reads a sealed Lane R revision."""
    rows = candidate.dispositions.get("dispositions", []) if candidate.dispositions else []
    return SealedCandidate(LANE_R, candidate.readme, _fact_rows(candidate), tuple(rows))


def parity_failures(candidate: Candidate) -> list[Failure]:
    """One failure per (lost item, unit holding it); one per lost item no unit holds."""
    benchmark = candidate.benchmark_readme
    if not benchmark:
        return []  # no published README (or none handed over): nothing to fall below
    failures: list[Failure] = []
    for loss in content_losses(sealed_view(candidate), benchmark):
        what = f"{loss.category} '{loss.item}'"
        if not loss.units:
            failures.append(
                Failure(
                    loss.stage,  # type: ignore[arg-type]
                    f"{what} is in the published README and lost from this candidate, and no "
                    f"inherited unit holds it ({loss.dimension})",
                )
            )
            continue
        for unit in loss.units:
            failures.append(
                Failure(
                    "RECONCILING",
                    f"{unit} holds {what}, {PARITY_LOSS_MARKER} ({loss.dimension}): keep it "
                    "(VERIFIED_PRESERVE/VERIFIED_MOVE, or PRESERVE_ATTRIBUTED when no fact "
                    "confirms it), or omit it citing the fact that contradicts it",
                    unit=unit,
                )
            )
    return failures
