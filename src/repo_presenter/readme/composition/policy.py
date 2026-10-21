"""The presentation policy: ceilings and budgets the plan must respect and the renderer enforces.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/policy.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from repo_presenter.readme.composition.link_budget import AUTOMATIC_TOTAL_CAP, LinkAllocationPolicy

POLICY_VERSION = "1"


@dataclass(frozen=True)
class PlanningPolicy:
    capabilities_min: int = 3
    capabilities_max: int = 8
    api_hubs_max: int = 12
    aspose_links_max: int = AUTOMATIC_TOTAL_CAP
    visible_lines_budget: int = 300
    total_lines_budget: int = 600
    enterprise_target_url: str | None = None
    link_allocation: LinkAllocationPolicy | None = None


DEFAULT_POLICY = PlanningPolicy()


def policy_packet(policy: PlanningPolicy = DEFAULT_POLICY) -> dict[str, Any]:
    """The policy as the planner and the bundle see it."""
    packet = {"version": POLICY_VERSION, **asdict(policy)}
    configured = packet.pop("link_allocation")
    if configured is not None:
        packet["link_allocation"] = configured
        packet["aspose_links_max"] = configured["max_total"]
    return packet
