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


#: Measured over every sealed Lane R bundle on the state remote (2026-11-13, 18 bundles: 623
#: authored non-type units, 626 omitted entries): the 95th-percentile JSON size of one authored
#: unit and of one ``omitted`` entry, in characters.
UNIT_P95_CHARS = 923
OMITTED_P95_CHARS = 218
#: Characters per completion token assumed for a JSON reply (conservative: English prose with long
#: fact ids tokenises at about 3-4), and the share of ``max_output_tokens`` a reply is planned to
#: use. Measured: the largest successful section_authoring reply on record used 5833 of 8000
#: tokens (73%); 743 calls, 99th percentile 4832.
CHARS_PER_TOKEN = 3.0
PLANNED_SHARE = 0.75


def omitted_cap(task: SectionTask, max_output_tokens: int) -> int | None:
    """The most ``omitted`` entries a reply over ``task`` may hold so that the reply, at measured
    95th-percentile sizes, fits ``PLANNED_SHARE`` of ``max_output_tokens``; ``None`` when the
    uncapped list already fits (the schema is then unchanged) or when ``task`` is a type batch
    (bounded by its own batch size, ``authoring._TYPE_BATCH``). Never below the inherited units
    the section must carry: those are the omissions a check reads (``carried_unit_errors``).

    Decision (BL-082, 2026-11-13): bound the output, do not raise the budget. Hosted run
    43516334907 (Aspose.Cells-FOSS-for-Rust, Lane R) failed with "section_authoring: output
    truncated at the manifest's max_output_tokens (8000)". The api_reference task there has 13
    slots and 88 accepted facts, and the prompt asks for every accepted fact a unit does not cite
    to be listed in ``omitted`` with a reason: 13 x 923 + ~58 x 218 chars is about 24,600 chars,
    about 8,200 tokens. The part that grows with the input is ``omitted`` (internal accounting,
    never README text). Raising ``max_output_tokens`` would change the section_authoring manifest
    and so every section call's request hash and every candidate's version set portfolio-wide;
    this cap changes only the requests of tasks that do not fit."""
    if task.key.startswith(f"{task.section_id}#types-"):
        return None
    full = omittable_count([task])
    room = int(max_output_tokens * CHARS_PER_TOKEN * PLANNED_SHARE) - len(task.slots) * UNIT_P95_CHARS
    fits = max(room // OMITTED_P95_CHARS, 0)
    if fits >= full:
        return None
    return max(fits, len(task.must_carry))


def bound_authoring_citations(
    schema: dict[str, Any], task: SectionTask, max_output_tokens: int | None = None
) -> dict[str, Any]:
    """``schema`` (``authoring_schema``'s output for ``task``) with every unit's ``fact_ids`` and
    the ``omitted`` list capped at the number of distinct facts they can legitimately hold, and,
    given the job's ``max_output_tokens``, ``omitted`` further capped so the reply fits it
    (``omitted_cap``)."""
    bounded = copy.deepcopy(schema)
    properties = bounded["properties"]
    positional = properties["units"].get("prefixItems")
    if positional is not None:
        for slot, item in zip(task.slots, positional, strict=True):
            item["properties"]["fact_ids"]["maxItems"] = max(len(citable(task, slot)), 1)
    if "omitted" in properties:
        properties["omitted"]["maxItems"] = omittable_count([task])
        cap = None if max_output_tokens is None else omitted_cap(task, max_output_tokens)
        if cap is not None:
            properties["omitted"]["maxItems"] = cap
    return bounded
