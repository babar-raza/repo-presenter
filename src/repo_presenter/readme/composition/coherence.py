"""Stage S8: the coherence pass - revise LLM-owned units only, once, then re-render.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/coherence.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

The pass is one or more section_authoring calls in coherence mode: each call sees the rendered
document and every authored unit for context, and returns exactly one batch's own units with their
section and slot unchanged and their text possibly revised. The guard holds each returned unit to
its own section's rules, so the pass can only change prose the LLM already owned. Deterministic
blocks are untouched by construction: the renderer is a pure function and only unit texts change.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import Fact, FactsDocument, bounded_records
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.audience import (
    AUDIENCE_SECTIONS,
    strip_audience_claims,
    support_texts,
    unsupported_audience_sentences,
)
from repo_presenter.readme.composition.authoring import (
    SectionTask,
    recover_opening_duplicates_preserved,
    restates_own_title,
    section_spellings,
    slot_records,
    uncarried_units,
    unit_checks,
)
from repo_presenter.readme.composition.components.identity import product_name
from repo_presenter.readme.composition.output_bounds import (
    largest_slot_citation_count,
    omittable_count,
)

COHERENCE_SECTION = "all"
_SPELLING_CAP = 120
_COHERENCE_BATCH_UNITS = 16


def coherence_packet(
    entry: RegistryEntry,
    readme: str,
    units_document: dict[str, Any],
    tasks: list[SectionTask],
    facts: FactsDocument,
) -> dict[str, Any]:
    """The packet for the one coherence call: the document, the units, and their closed facts."""
    by_id = {fact.id: fact for fact in facts.facts}
    tasks = [task for task in tasks if not task.is_batch]
    accepted_ids = coherence_citable_ids(tasks)
    slots = [f"{task.section_id}/{slot}" for task in tasks for slot in task.slots]
    spellings = section_spellings(accepted_ids, facts)[:_SPELLING_CAP]
    return {
        "repository": entry.repository,
        "product_name": product_name(entry),
        "mode": "coherence",
        "section_id": COHERENCE_SECTION,
        "objective": (
            "Revise the LLM-owned units, once, so the whole document reads as one coherent "
            "developer journey: no repetition across sections, one voice, each unit still true to "
            "its facts. Return every unit with its section and slot exactly as given, revised or "
            f"not. Units to return, each exactly once: {', '.join(slots)}. Identifiers the prose "
            f"may spell, exactly as written: {', '.join(spellings)}; any other API name, member, "
            "attribute, or parameter is rejected."
        ),
        "slots": [
            record
            for task in tasks
            for record in slot_records(task.slots, task.slot_facts, task.slot_titles)
        ],
        "accepted_facts": [
            {"id": fact_id, "kind": by_id[fact_id].kind, "value": by_id[fact_id].value}
            for fact_id in accepted_ids
            if fact_id in by_id
        ],
        "do_not_claim": bounded_records(
            facts,
            ["format", "install_command", "link_target", "example"],
            ("CONTRADICTED", "UNRESOLVED"),
        ),
        "length_budget": "each unit within its own section's budget; never longer than before",
        "rendered_document": readme,
        "existing_units": [
            unit
            for unit in units_document.get("units", [])
            if not str(unit.get("slot", "")).startswith("type:")
        ],
    }


def coherence_citable_ids(tasks: list[SectionTask]) -> list[str]:
    """Every fact ID any unit the coherence call returns may legitimately cite."""
    tasks = [task for task in tasks if not task.is_batch]
    ids: list[str] = []
    for task in tasks:
        ids.extend(fact_id for fact_id in sorted(task.accepted_ids))
    return list(dict.fromkeys(ids))


def coherence_batches(tasks: list[SectionTask]) -> list[tuple[str, list[SectionTask]]]:
    """Every LLM-owned section, grouped into fixed-size coherence batches in document (task)
    order - one ``(batch_id, group)`` pair per coherence call this round makes."""
    tasks = [task for task in tasks if not task.is_batch]
    batches: list[list[SectionTask]] = []
    current: list[SectionTask] = []
    current_units = 0
    for task in tasks:
        if current and current_units + len(task.slots) > _COHERENCE_BATCH_UNITS:
            batches.append(current)
            current = []
            current_units = 0
        current.append(task)
        current_units += len(task.slots)
    if current:
        batches.append(current)
    return [(f"coherence#{index + 1}", group) for index, group in enumerate(batches)]


def coherence_batch_units(
    existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> list[dict[str, Any]]:
    """The subset of ``existing_units`` one batch's own ``tasks`` own."""
    slots = {(task.section_id, slot) for task in tasks for slot in task.slots}
    return [unit for unit in existing_units if (unit.get("section"), unit.get("slot")) in slots]


def coherence_schema(
    manifest: LoadedManifest, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any]:
    """The section_authoring schema specialised for the one coherence call."""
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    units = schema["properties"]["units"]
    citable = coherence_citable_ids(tasks)
    if citable:
        units["items"]["properties"]["fact_ids"]["items"] = {"type": "string", "enum": citable}
        scoped = [task for task in tasks if not task.is_batch]
        units["items"]["properties"]["fact_ids"]["maxItems"] = largest_slot_citation_count(scoped)
        schema["properties"]["omitted"]["maxItems"] = omittable_count(scoped)
    else:
        units["items"]["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
    count = len(existing_units)
    if count:
        units["minItems"] = count
        units["maxItems"] = count
    return schema


def coherence_checks(
    output: dict[str, Any],
    tasks: list[SectionTask],
    facts: FactsDocument,
    name: str,
    existing_units: list[dict[str, Any]] | None = None,
    prior_omitted: Sequence[Mapping[str, Any]] = (),
    dispositions: Mapping[str, Any] | None = None,
) -> list[str]:
    """Every section's rules, applied to the units the pass returned for that section, plus a
    check that the revision did not silently drop named content the pre-coherence unit carried."""
    errors: list[str] = []
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in output.get("units", []):
        by_section.setdefault(str(unit.get("section", "")), []).append(unit)
    tasks = [task for task in tasks if not task.is_batch]
    known = {task.section_id for task in tasks}
    for section in sorted(set(by_section) - known):
        errors.append(f"units name a section the plan did not author: {section}")
    cited_elsewhere: dict[str, str] = {}
    for section, section_units in by_section.items():
        for unit in section_units:
            for fact_id in unit.get("fact_ids", []):
                cited_elsewhere.setdefault(fact_id, section)
    for task in tasks:
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        omitted = [
            item
            for item in prior_omitted
            if isinstance(item, Mapping) and item.get("section") == task.section_id
        ]
        errors.extend(
            unit_checks(
                {"units": owned, "omitted": omitted},
                task,
                facts,
                name,
                elsewhere_cited=cited_elsewhere,
                dispositions=dispositions,
            )
        )
    if existing_units is not None:
        errors.extend(coherence_content_loss_errors(output.get("units", []), existing_units, facts))
    return errors


_CONTENT_TOKEN = re.compile(r"[a-z0-9][a-z0-9+./_-]{2,}")
_NEUTRAL_FACT_KINDS = frozenset({"identity", "package"})


def _printed_command(fact: Fact) -> bool:
    """Whether ``fact`` records a command the renderer prints verbatim in a fenced block."""
    return fact.kind == "install_command" or (
        fact.kind == "build_test_asset"
        and str((fact.attributes or {}).get("role", "")).endswith("command")
    )


def _content_tokens(text: str) -> frozenset[str]:
    """The lower-cased, three-or-more-character tokens ``text`` spells."""
    return frozenset(_CONTENT_TOKEN.findall(text.lower()))


def _dropped_untraced_fact_ids(
    unit: dict[str, Any], existing: dict[str, Any], facts: FactsDocument
) -> list[str]:
    """The pre-coherence fact IDs ``unit`` no longer cites whose own SUPPORTED value has left no
    trace in ``unit``'s revised text."""
    by_id = {fact.id: fact for fact in facts.facts}
    existing_ids = {str(i) for i in existing.get("fact_ids", [])}
    revised_ids = {str(i) for i in unit.get("fact_ids", [])}
    dropped = sorted(existing_ids - revised_ids)
    if not dropped:
        return []
    revised_tokens = _content_tokens(str(unit.get("text", "")))
    untraced: list[str] = []
    for fact_id in dropped:
        fact = by_id.get(fact_id)
        if (
            fact is None
            or fact.polarity != "SUPPORTED"
            or fact.kind in _NEUTRAL_FACT_KINDS
            or _printed_command(fact)
        ):
            continue
        value_tokens = _content_tokens(fact.value)
        if value_tokens and value_tokens & revised_tokens:
            continue
        untraced.append(fact_id)
    return untraced


def coherence_content_loss_errors(
    output_units: list[dict[str, Any]],
    existing_units: list[dict[str, Any]],
    facts: FactsDocument,
) -> list[str]:
    """A coherence revision that drops a previously-cited fact with none of its own content left
    in the revised text, per unit."""
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    by_id = {fact.id: fact for fact in facts.facts}
    errors: list[str] = []
    for unit in output_units:
        key = (str(unit.get("section")), str(unit.get("slot")))
        existing = existing_by_key.get(key)
        if existing is None:
            continue
        for fact_id in _dropped_untraced_fact_ids(unit, existing, facts):
            fact = by_id.get(fact_id)
            value = fact.value if fact is not None else fact_id
            kind = fact.kind if fact is not None else "fact"
            errors.append(
                f"{key[0]}/{key[1]}: coherence revision drops the previously-cited {kind} "
                f"{fact_id!r} and none of its own content ({value!r}) remains in the revised "
                "text - a named capability, format, or structural detail the prior version "
                "carried must not be silently dropped during coherence"
            )
    return errors


def recover_coherence_content_loss(
    output: dict[str, Any], *, existing_units: list[dict[str, Any]], facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call: a unit whose own revision
    dropped a previously-cited fact with no trace of its value left in the text is reverted, in
    full, to its own pre-coherence text and fact_ids."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    changed = False
    for unit in units:
        if not isinstance(unit, dict):
            continue
        key = (str(unit.get("section")), str(unit.get("slot")))
        existing = existing_by_key.get(key)
        if existing is None:
            continue
        if _dropped_untraced_fact_ids(unit, existing, facts):
            unit["text"] = existing.get("text", unit.get("text"))
            existing_fact_ids = existing.get("fact_ids")
            unit["fact_ids"] = (
                list(existing_fact_ids)
                if isinstance(existing_fact_ids, list)
                else unit.get("fact_ids", [])
            )
            changed = True
    return output if changed else None


def recover_coherence_carried_units(
    output: dict[str, Any], *, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call, alongside
    ``recover_coherence_content_loss``: a must-carry fact_id that the pre-coherence document
    already carried correctly in its own disposed section, but this revision no longer carries
    there."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        if isinstance(unit, dict):
            by_section.setdefault(str(unit.get("section", "")), []).append(unit)
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    carry_owners: dict[str, str] = {}
    for task in tasks:
        for fact_id in task.must_carry:
            carry_owners[fact_id] = task.section_id
    changed = False
    for task in tasks:
        if not task.must_carry:
            continue
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        missing = uncarried_units({"units": owned, "omitted": []}, task.must_carry)
        for fact_id in missing:
            for unit in owned:
                key = (task.section_id, str(unit.get("slot")))
                existing = existing_by_key.get(key)
                if existing is None or fact_id not in existing.get("fact_ids", []):
                    continue
                unit["text"] = existing.get("text", unit.get("text"))
                existing_fact_ids = existing.get("fact_ids")
                unit["fact_ids"] = (
                    list(existing_fact_ids)
                    if isinstance(existing_fact_ids, list)
                    else unit.get("fact_ids", [])
                )
                changed = True
    for task in tasks:
        for unit in by_section.get(task.section_id, []):
            if unit.get("slot") not in task.slots:
                continue
            fact_ids = unit.get("fact_ids")
            if not isinstance(fact_ids, list):
                continue
            stray = [
                fact_id
                for fact_id in fact_ids
                if fact_id not in task.accepted_ids
                and carry_owners.get(fact_id) not in (None, task.section_id)
            ]
            if not stray:
                continue
            remaining = [fact_id for fact_id in fact_ids if fact_id not in stray]
            if remaining:
                unit["fact_ids"] = remaining
                changed = True
                continue
            key = (task.section_id, str(unit.get("slot")))
            existing = existing_by_key.get(key)
            existing_fact_ids = existing.get("fact_ids") if existing else None
            if existing is not None and isinstance(existing_fact_ids, list) and existing_fact_ids:
                unit["text"] = existing.get("text", unit.get("text"))
                unit["fact_ids"] = list(existing_fact_ids)
                changed = True
    return output if changed else None


def recover_coherence_title_restatements(
    output: dict[str, Any],
    *,
    existing_units: list[dict[str, Any]],
    tasks: list[SectionTask],
    facts: FactsDocument,
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call, alongside
    ``recover_coherence_content_loss``: a unit whose coherence revision now restates its own slot
    title is reverted, in full, to the pre-coherence text and fact_ids."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    changed = False
    for task in tasks:
        for unit in units:
            if not isinstance(unit, dict) or unit.get("section") != task.section_id:
                continue
            slot = str(unit.get("slot"))
            title = task.slot_titles.get(slot)
            existing = existing_by_key.get((task.section_id, slot))
            if not title or existing is None:
                continue
            if not restates_own_title(str(unit.get("text", "")), title, facts):
                continue
            if restates_own_title(str(existing.get("text", "")), title, facts):
                continue
            unit["text"] = existing.get("text", unit.get("text"))
            existing_fact_ids = existing.get("fact_ids")
            if isinstance(existing_fact_ids, list) and existing_fact_ids:
                unit["fact_ids"] = list(existing_fact_ids)
            changed = True
    return output if changed else None


def recover_coherence_audience_claims(
    output: dict[str, Any],
    *,
    existing_units: list[dict[str, Any]],
    tasks: list[SectionTask],
    facts: FactsDocument,
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call, alongside
    ``recover_coherence_title_restatements``: an opening the coherence pass rewrote so that it now
    states an audience, use case, or spared cost no accepted fact states is reverted."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    changed = False
    for task in tasks:
        if task.section_id not in AUDIENCE_SECTIONS:
            continue
        support = support_texts(task.accepted_ids, facts)
        for unit in units:
            if not isinstance(unit, dict) or unit.get("section") != task.section_id:
                continue
            text = str(unit.get("text", ""))
            if not unsupported_audience_sentences(text, support):
                continue
            existing = existing_by_key.get((task.section_id, str(unit.get("slot"))))
            if existing is not None and not unsupported_audience_sentences(
                str(existing.get("text", "")), support
            ):
                unit["text"] = existing.get("text", text)
                existing_fact_ids = existing.get("fact_ids")
                if isinstance(existing_fact_ids, list) and existing_fact_ids:
                    unit["fact_ids"] = list(existing_fact_ids)
                changed = True
                continue
            stripped = strip_audience_claims(text, support)
            if stripped is not None:
                unit["text"] = stripped
                changed = True
    return output if changed else None


def recover_coherence_missing_units(
    output: dict[str, Any], *, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call, alongside
    ``recover_coherence_content_loss``: a unit the pass was given and did not return is restored,
    whole, from the accepted S6 unit it was given as."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    returned = {
        (str(unit.get("section")), str(unit.get("slot")))
        for unit in units
        if isinstance(unit, dict)
    }
    owed = {(task.section_id, slot) for task in tasks if not task.is_batch for slot in task.slots}
    restored = [
        {key: value for key, value in unit.items()}
        for unit in existing_units
        if (str(unit.get("section")), str(unit.get("slot"))) in owed
        and (str(unit.get("section")), str(unit.get("slot"))) not in returned
    ]
    if not restored:
        return None
    order = {
        (str(unit.get("section")), str(unit.get("slot"))): index
        for index, unit in enumerate(existing_units)
    }
    units.extend(restored)
    units.sort(
        key=lambda unit: order.get(
            (str(unit.get("section")), str(unit.get("slot")))
            if isinstance(unit, dict)
            else ("", ""),
            len(order),
        )
    )
    return output


def recover_coherence_regressions(
    output: dict[str, Any],
    *,
    existing_units: list[dict[str, Any]],
    facts: FactsDocument,
    tasks: list[SectionTask],
    dispositions: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """The one ``recover=`` callable ``repair/rounds.py``'s S8 call site passes: all of S8
    coherence's own last-resort corrections, composed in order."""
    changed = False
    if dispositions is not None:
        opening_fixed = recover_opening_duplicates_preserved(
            output, dispositions=dispositions, facts=facts
        )
        if opening_fixed is not None:
            output = opening_fixed
            changed = True
    missing_fixed = recover_coherence_missing_units(
        output, existing_units=existing_units, tasks=tasks
    )
    if missing_fixed is not None:
        output = missing_fixed
        changed = True
    content_fixed = recover_coherence_content_loss(
        output, existing_units=existing_units, facts=facts
    )
    if content_fixed is not None:
        output = content_fixed
        changed = True
    carry_fixed = recover_coherence_carried_units(
        output, existing_units=existing_units, tasks=tasks
    )
    if carry_fixed is not None:
        output = carry_fixed
        changed = True
    title_fixed = recover_coherence_title_restatements(
        output, existing_units=existing_units, tasks=tasks, facts=facts
    )
    if title_fixed is not None:
        output = title_fixed
        changed = True
    audience_fixed = recover_coherence_audience_claims(
        output, existing_units=existing_units, tasks=tasks, facts=facts
    )
    if audience_fixed is not None:
        output = audience_fixed
        changed = True
    return output if changed else None


def apply_coherence(
    units_document: dict[str, Any], output: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """The units document with revised texts, and the section/slot names whose text changed."""
    revised_text = {
        (unit["section"], unit["slot"]): unit["text"] for unit in output.get("units", [])
    }
    revised: list[str] = []
    units: list[dict[str, Any]] = []
    for unit in units_document.get("units", []):
        key = (unit["section"], unit["slot"])
        text = revised_text.get(key, unit["text"])
        fact_ids = next(
            (
                item.get("fact_ids", unit["fact_ids"])
                for item in output.get("units", [])
                if (item.get("section"), item.get("slot")) == key
            ),
            unit["fact_ids"],
        )
        if text != unit["text"]:
            revised.append(f"{key[0]}/{key[1]}")
        units.append({**unit, "text": text, "fact_ids": fact_ids})
    document = {
        **units_document,
        "units": units,
        "coherence": {"applied": True, "revised": revised},
    }
    return document, revised
