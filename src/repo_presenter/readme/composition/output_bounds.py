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


#: presentation_planning (BL-097). Measured over every sealed Lane R bundle on the state remote
#: (2026-11-14, 18 plans, 82 successful planning calls: median 2004 completion tokens, p95 3861,
#: largest 4033 of 6000): the 95th-percentile JSON size of a plan reply without its
#: ``deviations`` (8000 characters; largest 9166), and of one deviation's ``text`` (165; largest
#: 172, 47 deviations). The longest capability title on record is 54 characters, the longest
#: At a Glance capability title 50.
PLAN_PRINTED_P95_CHARS = 8000
DEVIATION_TEXT_P95_CHARS = 165
#: ``{"section_id": "...", "text": "", "fact_ids": []}`` around one deviation's text and ids.
DEVIATION_ENTRY_OVERHEAD_CHARS = 60
#: JSON quoting and separator around one id in an array.
ID_OVERHEAD_CHARS = 4
#: maxLength for every free-text string of a plan reply: about four times the longest on record
#: (the section_authoring item-75 rule: under constrained decoding an unbounded string has no
#: terminating condition, so one runaway string can consume the whole call).
PLAN_TEXT_MAX_LENGTH = 200
DEVIATION_TEXT_MAX_LENGTH = 600
SECTION_REASON_MAX_LENGTH = 300


def _citable_width(schema: dict[str, Any]) -> float:
    """The mean JSON width of one citable fact id of ``schema`` (its ``$defs`` enum)."""
    enum = schema.get("$defs", {}).get("citable_fact_id", {}).get("enum", [])
    if not enum:
        return 20.0 + ID_OVERHEAD_CHARS
    return sum(len(fact_id) for fact_id in enum) / len(enum) + ID_OVERHEAD_CHARS


def deviations_bound(schema: dict[str, Any], max_output_tokens: int) -> tuple[int, int] | None:
    """``(maxItems, fact_ids maxItems)`` for ``deviations`` so that a plan reply - its printed
    selections at measured 95th-percentile size plus every deviation the bound allows, each at
    its p95 text and full ids at this repository's citable-id width - fits ``PLANNED_SHARE`` of
    ``max_output_tokens``; ``None`` when the schema's own bound already fits or it has no
    deviations array. The fact-id cap is lowered first (to 1), then the count.

    Decision (BL-097, 2026-11-14): bound the internal accounting, do not raise the budget. Hosted
    run 43572739220 (Aspose-PDF-FOSS-for-Python, Lane R) failed with "presentation_planning:
    output truncated at the manifest's max_output_tokens (6000)". With every array at its
    maxItems, every planning schema on record (18 sealed, 4 PDF at the failing revisions) allows
    a 21,000-34,500 character reply, above the 18,000 that 6000 tokens hold; the real replies
    stay at or under 10,400. ``deviations`` (10 x 12 ids) is the one part of a reply nothing
    downstream reads -- only ``plan_checks`` checks its section ids; it is never printed and no
    section packet is built from it -- and the largest part of that bound (5,500-9,300
    characters). Raising ``max_output_tokens`` would change the presentation_planning manifest,
    so every candidate's version set, and would still leave the free-text strings without a
    terminating condition."""
    properties = schema.get("properties", {})
    deviations = properties.get("deviations")
    if not isinstance(deviations, dict) or "items" not in deviations:
        return None
    fact_ids = deviations["items"].get("properties", {}).get("fact_ids", {})
    count = int(deviations.get("maxItems", 0))
    per = int(fact_ids.get("maxItems", 0))
    if count <= 0 or per <= 0:
        return None
    width = _citable_width(schema)
    room = int(max_output_tokens * CHARS_PER_TOKEN * PLANNED_SHARE) - PLAN_PRINTED_P95_CHARS
    entry = DEVIATION_ENTRY_OVERHEAD_CHARS + DEVIATION_TEXT_P95_CHARS

    def size(items: int, ids: int) -> float:
        return items * (entry + ids * width)

    if size(count, per) <= room:
        return None
    ids = per
    while ids > 1 and size(count, ids) > room:
        ids -= 1
    items = count
    while items > 1 and size(items, ids) > room:
        items -= 1
    return items, ids


def _limit(node: Any, length: int) -> None:
    if isinstance(node, dict) and node.get("type") == "string":
        node["maxLength"] = min(int(node.get("maxLength", length)), length)


def bound_planning_reply(schema: dict[str, Any], max_output_tokens: int | None) -> dict[str, Any]:
    """``schema`` (``planning.planning_schema``'s specialised schema) with every free-text string
    given a ``maxLength``, the ignored ``sections`` array bounded to the shell, and, given the
    job's ``max_output_tokens``, ``deviations`` bounded so the reply fits it
    (``deviations_bound``). A decoder constraint only: a stored plan is re-judged by
    ``plan_checks``, never against this schema."""
    from repo_presenter.readme.composition.components.shell import section_ids

    bounded = copy.deepcopy(schema)
    properties = bounded.get("properties", {})
    capability = properties.get("core_capabilities", {}).get("items", {}).get("properties", {})
    _limit(capability.get("title"), PLAN_TEXT_MAX_LENGTH)
    glance = properties.get("at_a_glance", {})
    for variant in [glance, *glance.get("oneOf", [])]:
        if isinstance(variant, dict):
            titles = variant.get("properties", {}).get("capability_titles", {})
            _limit(titles.get("items"), PLAN_TEXT_MAX_LENGTH)
    deviation = properties.get("deviations", {}).get("items", {}).get("properties", {})
    _limit(deviation.get("text"), DEVIATION_TEXT_MAX_LENGTH)
    sections = properties.get("sections")
    if isinstance(sections, dict):
        sections["maxItems"] = len(tuple(section_ids()))
        reason = sections.get("items", {}).get("properties", {}).get("reason")
        _limit(reason, SECTION_REASON_MAX_LENGTH)
    if max_output_tokens is not None:
        bound = deviations_bound(bounded, max_output_tokens)
        if bound is not None:
            items, ids = bound
            properties["deviations"]["maxItems"] = items
            properties["deviations"]["items"]["properties"]["fact_ids"]["maxItems"] = ids
    return bounded
