"""Bounds on the length of a section_authoring reply, applied to the schema it is decoded under.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/output_bounds.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). A decoder constraint, never a judgment: a stored output is re-judged under
the manifest's static schema and the checks, so no sealed output and no governed version is
touched by this module.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import Any

from repo_presenter.readme.composition.authoring import SectionTask, citable


def omittable_count(tasks: Iterable[SectionTask]) -> int:
    """How many distinct facts a reply over ``tasks`` could list in ``omitted`` (each once)."""
    ids: set[str] = set()
    for task in tasks:
        ids |= set(task.accepted_ids) | set(task.must_carry)
        for facts in task.slot_facts.values():
            ids |= set(facts)
    return len(ids)


def largest_slot_citation_count(tasks: Iterable[SectionTask]) -> int:
    """The most distinct facts any one unit of ``tasks`` may cite: its slot's own set."""
    return max((len(citable(task, slot)) for task in tasks for slot in task.slots), default=1)


def bound_authoring_citations(schema: dict[str, Any], task: SectionTask) -> dict[str, Any]:
    """``schema`` (``authoring_schema``'s output for ``task``) with every unit's ``fact_ids`` and
    the ``omitted`` list capped at the number of distinct facts they can legitimately hold."""
    bounded = copy.deepcopy(schema)
    properties = bounded["properties"]
    positional = properties["units"].get("prefixItems")
    if positional is not None:
        for slot, item in zip(task.slots, positional, strict=True):
            item["properties"]["fact_ids"]["maxItems"] = max(len(citable(task, slot)), 1)
    if "omitted" in properties:
        properties["omitted"]["maxItems"] = omittable_count([task])
    return bounded
