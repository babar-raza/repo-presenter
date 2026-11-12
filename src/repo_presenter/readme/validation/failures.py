"""The shape every blocking check returns: one ``Failure`` per reason, routed by its fields.

Ported (ADAPT, import paths only) from the old repository-presenter project's
``components/readme/validation/registry.py``: ``Failure``, ``Candidate``, ``CausalStage``,
``STAGE_ORDER`` and the earliest-stage reduction. The causal stages are the repair loop's own
routing vocabulary (``readme/repair/targeted.py``), unchanged.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy

CausalStage = Literal[
    "EXTRACTING", "INVESTIGATING", "RECONCILING", "PLANNING", "COMPOSING"
]
STAGE_ORDER: tuple[CausalStage, ...] = (
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
)


@dataclass(frozen=True)
class Failure:
    """One reason a blocking check failed, with the fields that route it.

    ``section`` is the shell section the failure is about. ``unit`` is the inherited unit a
    reconciliation failure is about. Both are fields, never prose parsed back out of ``detail``.
    """

    stage: CausalStage | None
    detail: str
    section: str | None = None
    unit: str | None = None
    #: Set only by a check that owes a specific correction (BC-18): the exact README text that is
    #: wrong and the one-sentence instruction a repair is handed. Carried as fields so the repair
    #: loop never parses ``detail``.
    quote: str | None = None
    instruction: str | None = None


@dataclass(frozen=True)
class Candidate:
    """Everything the blocking checks read: the artifacts, the facts they must agree with, the tasks."""

    entry: RegistryEntry
    facts: FactsDocument
    plan: dict[str, Any]
    units: dict[str, Any]
    dispositions: dict[str, Any]
    readme: str
    original_readme: bytes | None
    source_revision: str
    readme_sha256: str | None
    tree_paths: Sequence[str]
    tasks: Sequence[SectionTask]
    policy: PlanningPolicy = DEFAULT_POLICY
    #: The published README this candidate replaces (the live upstream README the run read), the
    #: R2 floor BC-17 (``validation/parity.py``) measures content loss against. ``None`` when not
    #: handed over (a calibration source); unlike ``original_readme`` it is never digest-checked.
    benchmark_readme: str | None = None
    #: Which lane the candidate belongs to. ``"R"`` (the default; every Candidate this module has
    #: ever been handed is a Lane R composition) or ``"L"``. BC-18 owes corrections to Lane R only.
    lane: str = "R"
    #: The findings register BC-18 reads; ``None`` is ``readme_findings.DEFAULT_FINDINGS_PATH``.
    findings_path: Path | None = None


def earliest(failures: Sequence[Failure]) -> CausalStage | None:
    """The earliest causal stage any failure names: the stage a repair must reopen first."""
    stages = [failure.stage for failure in failures if failure.stage is not None]
    if not stages:
        return None
    return min(stages, key=STAGE_ORDER.index)
