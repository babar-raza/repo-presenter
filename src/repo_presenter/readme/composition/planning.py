"""Stage S5: the presentation_planning job wiring - packet, deterministic guard, and plan.json.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/planning.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

Deterministic code evaluates every shell condition it can from the facts (a verified input
format, dependencies, further verified examples, verified links, build assets, a notices file,
an Enterprise Edition target in policy) and tells the job the result; the job decides only what
a fixed rule cannot: which capabilities are core, which example is minimal, which APIs are hubs,
which limitations are material, which links help which section, and whether the API reference
is useful. The guard then checks every selection against the facts and the policy ceilings
before the plan is used.

One dependency this module imports, ``investigation.dossier.UNIT_CAP``, was NOT separately ported
as a module (the old repo's ``investigation/`` package is PENDING_REVIEW, not this taskcard's
pull) -- only the one constant it defines is inlined below, with the same value and the same
citation to the defect class it closes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from repo_presenter.core.facts import (
    FACT_KINDS,
    POLARITIES,
    FactsDocument,
    bounded_records,
)
from repo_presenter.core.llm.binding import collect_ids
from repo_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import (
    prose_nouns,
    supporting_fact_ids,
    title_terms,
)
from repo_presenter.readme.composition.components.glance import capability_title_problem
from repo_presenter.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    Section,
    section_ids,
    shell_packet,
)
from repo_presenter.readme.composition.link_budget import (
    SlotCounter,
    plan_time_budget,
    slot_violations,
)
from repo_presenter.readme.composition.list_coverage import list_items
from repo_presenter.readme.composition.placement import PLACED, placements
from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy, policy_packet
from repo_presenter.readme.evidence.facts.assets import CI_BADGE_FACT_ID
from repo_presenter.readme.evidence.facts.links import extract_links, heading_slug
from repo_presenter.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)

PLAN_FILENAME = "plan.json"
_ASPOSE_DOMAINS = ("aspose.com", "aspose.org")
_SHELL_OWNED_LINKS = frozenset(
    {BANNER_FACT_ID, HOMEPAGE_FACT_ID, ENTERPRISE_FACT_ID, CI_BADGE_FACT_ID}
)
# investigation/dossier.py's own UNIT_CAP, inlined (see module docstring): the combined
# facts+dispositions budget this packet's own "inherited_unit" field is trimmed against. The old
# repository measured 400 against its own largest observed candidate (83 on
# aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp) with headroom; not re-measured here.
UNIT_CAP = 400


def _unrenderable_anchor_ids(facts: FactsDocument) -> frozenset[str]:
    """SUPPORTED in-page anchor ``link_target`` IDs the candidate cannot resolve."""
    shell = {heading_slug(section.heading) for section in SEMANTIC_SHELL if section.heading}
    return frozenset(
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED"
        and fact.value.startswith("#")
        and unquote(fact.value[1:]).lower() not in shell
    )


def _supported(facts: FactsDocument, kind: str) -> list[str]:
    return [fact.id for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def _product_name(facts: FactsDocument) -> str:
    """The product's own display name, derived from ``facts.repository``."""
    slug = facts.repository.rsplit("/", 1)[-1]
    return " ".join(part for part in slug.split("-") if part)


def _simple_symbol_name(value: str) -> str:
    return value.rsplit(".", 1)[-1].lower().replace("_", "")


def _mis_hubbed_symbol_ids(facts: FactsDocument) -> frozenset[str]:
    """SUPPORTED public_symbol IDs that are module/package-kind but have an available,
    same-named class/enum sibling one path segment deeper."""
    supported = [f for f in facts.by_kind("public_symbol") if f.polarity == "SUPPORTED"]
    class_enum_names = {
        _simple_symbol_name(f.value)
        for f in supported
        if (f.attributes or {}).get("symbol_kind") in ("class", "enum")
    }
    return frozenset(
        f.id
        for f in supported
        if (f.attributes or {}).get("symbol_kind") not in ("class", "enum")
        and _simple_symbol_name(f.value) in class_enum_names
    )


def section_conditions(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> dict[str, bool | None]:
    """Whether each section's condition holds: True, False, or None when the plan decides."""
    links = [
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED"
        and fact.id not in _SHELL_OWNED_LINKS
        and fact.value.startswith(("http://", "https://"))
    ]
    evaluated: dict[str, bool | None] = {
        "banner": banner_target(facts.facts) is not None,
        "at_a_glance": True,
        "dependencies": bool(_supported(facts, "dependency")),
        "quick_start": bool(_supported(facts, "example")),
        "additional_examples": len(_supported(facts, "example")) >= 2,
        "api_reference": True,
        "documentation_resources": bool(links),
        "development_testing": bool(facts.by_kind("build_test_asset")),
        "enterprise_relationship": enterprise_target(facts.facts) is not None,
        "third_party_notices": bool(facts.by_kind("third_party_notices")),
    }
    return {
        section.id: True if section.required else evaluated[section.id]
        for section in SEMANTIC_SHELL
    }


_ID_CHARS = r"A-Za-z0-9_.:\-"


def _uncitable_redaction(facts: FactsDocument) -> Callable[[str], str]:
    """Replace every uncitable fact ID in free text with its polarity and kind, never the ID."""
    labels = {
        fact.id: f"[{fact.polarity} {fact.kind}, not citable]"
        for fact in facts.facts
        if fact.polarity != "SUPPORTED"
    }
    if not labels:
        return lambda text: text
    alternation = "|".join(re.escape(i) for i in sorted(labels, key=len, reverse=True))
    pattern = re.compile(
        rf"(?<![{_ID_CHARS}])(?:{alternation})(?![A-Za-z0-9_\-])(?!\.[A-Za-z0-9_])"
    )
    return lambda text: pattern.sub(lambda match: labels[match.group(0)], text)


def _admitted_inherited_unit_ids(facts: FactsDocument) -> frozenset[str]:
    """The SUPPORTED ``inherited_unit`` fact IDs presentation_planning's packet may show at all,
    in document order, capped at ``UNIT_CAP``."""
    ordered = bounded_records(facts, {"inherited_unit"})
    return frozenset(record["id"] for record in ordered[:UNIT_CAP])


PLANNING_SYMBOL_CAP = 1200


def _admitted_public_symbol_ids(facts: FactsDocument) -> frozenset[str]:
    """The SUPPORTED ``public_symbol`` fact IDs presentation_planning's packet, ``symbol_fact_id``
    enum, and ``citable_fact_id`` enum may show at all, capped at ``PLANNING_SYMBOL_CAP``."""
    ordered = bounded_records(facts, {"public_symbol"})
    return frozenset(record["id"] for record in ordered[:PLANNING_SYMBOL_CAP])


def _capped_facts(facts: FactsDocument, kinds: Iterable[str]) -> list[dict[str, str]]:
    """``bounded_records(facts, kinds)``, with any ``inherited_unit``/``public_symbol`` entries
    further trimmed to the planning-specific admission sets above."""
    admitted_units = _admitted_inherited_unit_ids(facts)
    admitted_symbols = _admitted_public_symbol_ids(facts)
    return [
        record
        for record in bounded_records(facts, kinds)
        if (record["kind"] != "inherited_unit" or record["id"] in admitted_units)
        and (record["kind"] != "public_symbol" or record["id"] in admitted_symbols)
    ]


def _selectable_dispositions(dispositions: dict[str, Any], facts: FactsDocument) -> dict[str, Any]:
    """The dispositions as the planner may act on them: only the fact IDs a plan may cite, and
    only entries for an inherited unit the packet admits."""
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    admitted_units = _admitted_inherited_unit_ids(facts)
    redact = _uncitable_redaction(facts)
    entries = []
    for entry in dispositions.get("dispositions", []):
        if str(entry.get("unit_id")) not in admitted_units:
            continue
        shown: dict[str, Any] = {}
        for key, value in entry.items():
            if key == "fact_ids":
                shown[key] = [i for i in value if i in supported]
            elif key == "rationale" and isinstance(value, str):
                shown[key] = redact(value)
            else:
                shown[key] = value
        entries.append(shown)
    return {**dispositions, "dispositions": entries}


_FORMAT_DIRECTIONS = ("input", "output")


def _verified_formats(facts: FactsDocument) -> dict[str, list[dict[str, str]]]:
    """The SUPPORTED format facts by direction as ``{id, value}`` records."""
    by_direction: dict[str, list[dict[str, str]]] = {d: [] for d in _FORMAT_DIRECTIONS}
    for record in sorted(bounded_records(facts, {"format"}), key=lambda r: r["id"]):
        for direction in _FORMAT_DIRECTIONS:
            if record["id"].startswith(f"format:{direction}."):
                by_direction[direction].append({"id": record["id"], "value": record["value"]})
    return by_direction


def _examples_summary(facts: FactsDocument) -> dict[str, Any]:
    """Which examples a plan may select, and how many were withheld and why - as counts."""
    withheld = {polarity: 0 for polarity in POLARITIES if polarity != "SUPPORTED"}
    for fact in facts.by_kind("example"):
        if fact.polarity != "SUPPORTED":
            withheld[fact.polarity] += 1
    return {
        "verified_ids": sorted(record["id"] for record in bounded_records(facts, {"example"})),
        "withheld": withheld,
    }


def planning_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    manifest: PromptManifest,
    policy: PlanningPolicy = DEFAULT_POLICY,
) -> dict[str, Any]:
    """The planner's bounded view: SUPPORTED facts, the dispositions as it may act on them, the
    shell with its composed decisions, the policy ceilings - and which examples it may select
    with what was withheld, and which formats a title or At a Glance may name."""
    conditions = section_conditions(facts, policy)
    shell = [
        {**section, "condition_holds": conditions[section["id"]]} for section in shell_packet()
    ]
    kinds = manifest.packet.fact_kinds or FACT_KINDS
    return {
        "repository": entry.repository,
        "facts": _capped_facts(facts, kinds),
        "examples": _examples_summary(facts),
        "formats": _verified_formats(facts),
        "investigation": investigation,
        "dispositions": _selectable_dispositions(dispositions, facts),
        "shell": shell,
        "policy": policy_packet(policy),
    }


def _decision(section: Section, holds: bool | None) -> dict[str, Any]:
    """One inclusion decision, composed by code from the shell and the evaluated condition."""
    if section.required:
        return {"section_id": section.id, "include": True, "reason": "the shell requires it"}
    return {
        "section_id": section.id,
        "include": bool(holds),
        "reason": "its condition " + ("holds" if holds else "does not hold"),
    }


_FACT_ID_ARRAYS = (
    ("core_capabilities", "fact_ids"),
    ("core_capabilities", "shared_fact_ids"),
    ("api_hubs", "fact_ids"),
    ("material_limitations", "fact_ids"),
    ("deviations", "fact_ids"),
)
_FACT_ID_ARRAY_CAPS = {
    ("core_capabilities", "fact_ids"): 12,
    ("core_capabilities", "shared_fact_ids"): 4,
    ("api_hubs", "fact_ids"): 12,
    ("material_limitations", "fact_ids"): 6,
    ("deviations", "fact_ids"): 12,
}
_UNIT_ID_ARRAY_CAPS = {("material_limitations", "unit_ids"): 6}
_UNIT_ID_ARRAYS = (("material_limitations", "unit_ids"),)


def citable_fact_ids(
    facts: FactsDocument,
    investigation: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    manifest: PromptManifest,
) -> list[str]:
    """Every fact ID a plan may write, sorted."""
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    kinds = manifest.packet.fact_kinds or FACT_KINDS
    shown = {record["id"] for record in _capped_facts(facts, kinds)}
    shown.update(_examples_summary(facts)["verified_ids"])
    shown.update(r["id"] for records in _verified_formats(facts).values() for r in records)
    shown.update(
        fact_id
        for entry in _selectable_dispositions(dict(dispositions), facts)["dispositions"]
        for fact_id in entry.get("fact_ids", [])
    )
    cited = {fact_id for fact_id in collect_ids(investigation).fact_ids if fact_id in supported}
    return sorted(shown | cited)


def citable_unit_ids(facts: FactsDocument, citable: Sequence[str]) -> list[str]:
    """The IDs a plan may write into a unit array: the citable IDs that are inherited units."""
    units = {fact.id for fact in facts.by_kind("inherited_unit")}
    return [fact_id for fact_id in citable if fact_id in units]


def _pin_unit_id_arrays(schema: dict[str, Any], citable_units: list[str]) -> None:
    """Pin every unit-ID array to ``citable_units`` through its own ``$defs`` enum."""
    if citable_units:
        schema.setdefault("$defs", {})["citable_unit_id"] = {
            "type": "string",
            "enum": citable_units,
        }
    for property_name, field in _UNIT_ID_ARRAYS:
        items = schema["properties"].get(property_name, {}).get("items", {})
        item_properties = items.get("properties", {})
        if field not in item_properties:
            continue
        if citable_units:
            item_properties[field]["items"] = {"$ref": "#/$defs/citable_unit_id"}
            item_properties[field]["maxItems"] = min(
                len(citable_units),
                _UNIT_ID_ARRAY_CAPS.get((property_name, field), len(citable_units)),
            )
        else:
            item_properties[field] = {"type": "array", "maxItems": 0}


def _pin_fact_id_arrays(schema: dict[str, Any], citable: list[str]) -> None:
    """Pin every fact-ID array a plan writes to ``citable``: one ``$defs`` enum referenced from
    each array."""
    if citable:
        schema.setdefault("$defs", {})["citable_fact_id"] = {"type": "string", "enum": citable}
    for property_name, field in _FACT_ID_ARRAYS:
        items = schema["properties"].get(property_name, {}).get("items", {})
        item_properties = items.get("properties", {})
        if field not in item_properties:
            continue
        if citable:
            item_properties[field]["items"] = {"$ref": "#/$defs/citable_fact_id"}
            item_properties[field]["maxItems"] = min(
                len(citable), _FACT_ID_ARRAY_CAPS.get((property_name, field), len(citable))
            )
        else:
            item_properties[field] = {"type": "array", "maxItems": 0}


def planning_schema(
    manifest: LoadedManifest,
    facts: FactsDocument,
    investigation: Mapping[str, Any],
    dispositions: Mapping[str, Any],
) -> dict[str, Any]:
    """The planning schema specialised for this repository."""
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    verified = sorted(record["id"] for record in bounded_records(facts, {"example"}))
    properties = schema["properties"]
    deviations = properties.get("deviations", {}).get("items", {}).get("properties", {})
    if "section_id" in deviations:
        deviations["section_id"] = {"type": "string", "enum": list(section_ids())}
    link_properties = properties.get("links", {}).get("items", {}).get("properties", {})
    if "link_fact_id" in link_properties:
        unrenderable = _unrenderable_anchor_ids(facts)
        assignable = sorted(
            record["id"]
            for record in bounded_records(facts, {"link_target"})
            if record["id"] not in _SHELL_OWNED_LINKS and record["id"] not in unrenderable
        )
        if assignable:
            link_properties["link_fact_id"] = {"type": "string", "enum": assignable}
        else:
            properties["links"] = {"type": "array", "maxItems": 0}
    hub_properties = properties.get("api_hubs", {}).get("items", {}).get("properties", {})
    if "symbol_fact_id" in hub_properties:
        mis_hubbed = _mis_hubbed_symbol_ids(facts)
        visible_symbol_ids = _admitted_public_symbol_ids(facts)
        hubbable = sorted(visible_symbol_ids - mis_hubbed)
        if hubbable:
            hub_properties["symbol_fact_id"] = {"type": "string", "enum": hubbable}
            if section_conditions(facts)["api_reference"]:
                properties["api_hubs"]["minItems"] = 1
        else:
            properties["api_hubs"] = {"type": "array", "maxItems": 0}
    formats = _verified_formats(facts)
    for variant in properties.get("at_a_glance", {}).get("oneOf", []):
        if variant.get("type") != "object":
            continue
        glance_properties = variant.get("properties", {})
        for direction, records in formats.items():
            field = f"{direction}_format_ids"
            if field not in glance_properties:
                continue
            format_ids = [record["id"] for record in records]
            glance_properties[field] = (
                {"type": "array", "items": {"type": "string", "enum": format_ids}}
                if format_ids
                else {"type": "array", "maxItems": 0}
            )
    if section_conditions(facts)["at_a_glance"] is True:
        properties["at_a_glance"] = next(
            variant
            for variant in properties["at_a_glance"]["oneOf"]
            if variant.get("type") == "object"
        )
    citable = citable_fact_ids(facts, investigation, dispositions, manifest.manifest)
    _pin_fact_id_arrays(schema, citable)
    _pin_unit_id_arrays(schema, citable_unit_ids(facts, citable))
    if not verified:
        properties["quick_start_example_id"] = {"type": "null"}
        properties["second_quick_start_example_id"] = {"type": "null"}
        properties["flagship_example_id"] = {"type": "null"}
        properties["additional_example_ids"] = {"type": "array", "maxItems": 0}
        return schema
    properties["quick_start_example_id"]["enum"] = verified
    properties["additional_example_ids"]["items"]["enum"] = verified
    for field in ("second_quick_start_example_id", "flagship_example_id"):
        properties[field]["enum"] = [*verified, None]
    return schema


def _capability_facts_apart(capabilities: list[dict[str, Any]]) -> None:
    """Compose, in place, which facts two capabilities share, from the citations themselves."""
    holders: dict[str, set[int]] = {}
    for index, item in enumerate(capabilities, start=1):
        for fact_id in set(item.get("fact_ids", [])):
            holders.setdefault(fact_id, set()).add(index)
    shared = {fact_id for fact_id, holding in holders.items() if len(holding) > 1}
    for item in capabilities:
        cited = set(item.get("fact_ids", []))
        declared = sorted(cited & shared)
        if declared or item.get("shared_fact_ids"):
            item["shared_fact_ids"] = declared


_BackstopRequired = Callable[[dict[str, Any], FactsDocument, "dict[str, Any] | None"], list[Any]]
_BackstopApply = Callable[[dict[str, Any], list[Any]], None]


def _missing_additional_examples(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[str]:
    verified_examples = sorted(
        fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"
    )
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    additional = [i for i in output.get("additional_example_ids", []) if i not in starts]
    return [i for i in verified_examples if i not in starts and i not in additional]


def _apply_additional_examples(output: dict[str, Any], missing: list[Any]) -> None:
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    additional = [i for i in output.get("additional_example_ids", []) if i not in starts]
    output["additional_example_ids"] = additional + missing


def _required_link_sections(dispositions: dict[str, Any] | None) -> dict[str, str]:
    """Every ``link_target`` fact a ``VERIFIED_REWRITE`` disposition names, mapped to its
    destination section."""
    if dispositions is None:
        return {}
    rewritten_link_sections: dict[str, str] = {}
    for entry in dispositions.get("dispositions", []):
        if entry.get("disposition") != "VERIFIED_REWRITE":
            continue
        destination = entry.get("destination_section")
        if not destination:
            continue
        for fact_id in entry.get("fact_ids") or []:
            fact_id = str(fact_id)
            if fact_id.startswith("link_target:") and fact_id not in _SHELL_OWNED_LINKS:
                rewritten_link_sections[fact_id] = str(destination)
    return rewritten_link_sections


def _missing_links(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[dict[str, str]]:
    rewritten_link_sections = _required_link_sections(dispositions)
    planned_link_ids = {str(link.get("link_fact_id")) for link in output.get("links", [])}
    return [
        {"link_fact_id": fact_id, "section_id": section}
        for fact_id, section in rewritten_link_sections.items()
        if fact_id not in planned_link_ids
    ]


def _apply_links(output: dict[str, Any], missing: list[Any]) -> None:
    output["links"] = [*output.get("links", []), *missing]


def _kept_list_links(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> dict[str, str]:
    """Every ``link_target`` fact a list kept as written in Documentation and Resources cites,
    mapped to that section, when the plan already carries at least one of them there."""
    if dispositions is None:
        return {}
    texts = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    assignable = {
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED"
        and fact.id not in _SHELL_OWNED_LINKS
        and not fact.value.startswith("#")
    }
    planned_here = {
        str(link.get("link_fact_id"))
        for link in output.get("links", [])
        if link.get("section_id") == "documentation_resources"
    }
    required: dict[str, str] = {}
    for entry in dispositions.get("dispositions", []):
        unit = str(entry.get("unit_id", ""))
        if (
            entry.get("disposition") not in PLACED
            or entry.get("destination_section") != "documentation_resources"
            or not unit.endswith(".list")
            or len(list_items(texts.get(unit, ""))) < 2
        ):
            continue
        targets = [str(i) for i in entry.get("fact_ids") or [] if str(i) in assignable]
        if planned_here.intersection(targets):
            required.update(dict.fromkeys(targets, "documentation_resources"))
    return required


def _missing_kept_list_links(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> list[dict[str, str]]:
    planned = {str(link.get("link_fact_id")) for link in output.get("links", [])}
    return [
        {"link_fact_id": fact_id, "section_id": section}
        for fact_id, section in _kept_list_links(output, facts, dispositions).items()
        if fact_id not in planned
    ]


def _hand_off_dropped_lists(
    output: dict[str, Any],
    facts: FactsDocument,
    dispositions: dict[str, Any] | None,
    ecosystem: str,
) -> None:
    """Hand every list kept as written that placement drops from Scope and Limitations to the
    limitation slots, so the section's authored units can state its items."""
    if dispositions is None:
        return
    limitations = output.get("material_limitations") or []
    handed = {str(unit) for item in limitations for unit in item.get("unit_ids") or []}
    dropped = [
        decision.unit_id
        for decision in placements(output, dispositions, facts, ecosystem)
        if decision.destination == "scope_limitations"
        and decision.outcome == "overlap"
        and decision.unit_id.endswith(".list")
        and decision.unit_id not in handed
        and len(list_items(decision.text)) >= 2
    ]
    if not dropped:
        return
    if not limitations:
        limitations = [{"fact_ids": [], "unit_ids": []}]
        output["material_limitations"] = limitations
    for item in limitations:
        item["unit_ids"] = [*dict.fromkeys([*(item.get("unit_ids") or []), *dropped])]


def _placed_into(dispositions: dict[str, Any] | None, section: str) -> bool:
    """Whether reconciliation preserves or moves an inherited unit into ``section``."""
    if dispositions is None:
        return False
    return any(
        entry.get("disposition") in PLACED and entry.get("destination_section") == section
        for entry in dispositions.get("dispositions", [])
    )


def _documentation_resources_holds(
    output: dict[str, Any], facts: FactsDocument, dispositions: dict[str, Any] | None
) -> bool:
    """The section has content only when this plan assigns it a SUPPORTED, non-shell link target,
    or reconciliation places a unit in it."""
    verified = {
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED" and fact.id not in _SHELL_OWNED_LINKS
    }
    return _placed_into(dispositions, "documentation_resources") or any(
        link.get("section_id") == "documentation_resources" and link.get("link_fact_id") in verified
        for link in output.get("links", [])
    )


_BACKSTOPS: tuple[tuple[str, _BackstopRequired, _BackstopApply], ...] = (
    ("additional_example_ids", _missing_additional_examples, _apply_additional_examples),
    ("links", _missing_links, _apply_links),
    ("links", _missing_kept_list_links, _apply_links),
)


def plan_checks(
    output: dict[str, Any],
    facts: FactsDocument,
    policy: PlanningPolicy = DEFAULT_POLICY,
    dispositions: dict[str, Any] | None = None,
    ecosystem: str = "",
) -> list[str]:
    """Why the plan may not be used, beyond schema and binding; empty when every rule holds."""
    errors: list[str] = []
    conditions = section_conditions(facts, policy)
    verified_examples = sorted(
        fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"
    )
    starts = {output.get("quick_start_example_id"), output.get("second_quick_start_example_id")}
    starts -= {None}
    conditions["additional_examples"] = bool(set(verified_examples) - starts)
    for _field_name, required, apply in _BACKSTOPS:
        missing = required(output, facts, dispositions)
        if missing:
            apply(output, missing)
    conditions["documentation_resources"] = _documentation_resources_holds(
        output, facts, dispositions
    )
    output["sections"] = [_decision(section, conditions[section.id]) for section in SEMANTIC_SHELL]
    decisions = {entry["section_id"]: entry for entry in output["sections"]}
    included = {section for section, entry in decisions.items() if entry["include"]}
    _hand_off_dropped_lists(output, facts, dispositions, ecosystem)
    preserved_hrefs: list[str] = []
    if dispositions is not None:
        by_unit_id = {
            str(entry.get("unit_id")): entry for entry in dispositions.get("dispositions", [])
        }
        for placement in placements(output, dispositions, facts, ecosystem):
            if placement.outcome == "excluded":
                entry = by_unit_id.get(placement.unit_id)
                if entry is not None:
                    entry["disposition"] = "DEFER_UNRESOLVED"
                    entry["destination_section"] = None
            elif placement.outcome == "placed":
                preserved_hrefs.extend(
                    target.href
                    for target in extract_links(placement.text)
                    if target.kind == "external"
                    and any(domain in target.href for domain in _ASPOSE_DOMAINS)
                )
    capabilities = output.get("core_capabilities", [])
    if not policy.capabilities_min <= len(capabilities) <= policy.capabilities_max:
        errors.append(
            f"core_capabilities must number {policy.capabilities_min} to "
            f"{policy.capabilities_max}; got {len(capabilities)}"
        )
    titles = [item.get("title", "").strip().lower() for item in capabilities]
    if len(set(titles)) != len(titles):
        errors.append("core_capabilities titles must be distinct")
    _capability_facts_apart(capabilities)
    name = _product_name(facts)
    nouns = prose_nouns(facts, name)
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    for index, item in enumerate(capabilities, start=1):
        title = str(item.get("title", ""))
        cited = " ".join(values.get(i, "") for i in item.get("fact_ids", [])).lower()
        unsupported = sorted(
            term
            for term in title_terms(title, facts)
            if term not in nouns
            and term.lstrip(".").lower() not in cited
            and term.lstrip(".").lower() not in common
        )
        if unsupported:
            candidates = {term: supporting_fact_ids(term, facts) for term in unsupported}
            suggestions = "; ".join(
                f"{term!r} is carried by {', '.join(ids)}"
                if ids
                else f"{term!r} by no SUPPORTED fact"
                for term, ids in candidates.items()
            )
            errors.append(
                f"core_capabilities {index} is titled {item.get('title')!r}, which names "
                f"{', '.join(unsupported)}, which the facts it cites do not carry ({suggestions}); "
                "cite one of the named facts that supports this title, or title the capability by "
                "what it cites"
            )

    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    input_formats = {i for i in supported if i.startswith("format:input.")}
    output_formats = {i for i in supported if i.startswith("format:output.")}
    glance = output.get("at_a_glance")
    if "at_a_glance" in included:
        if glance is None:
            errors.append("at_a_glance is included, so its formats and capabilities are given")
        else:
            bad_inputs = set(glance.get("input_format_ids", [])) - input_formats
            bad_outputs = set(glance.get("output_format_ids", [])) - output_formats
            bad_titles = set(glance.get("capability_titles", [])) - {
                item.get("title", "") for item in capabilities
            }
            if bad_inputs:
                errors.append(
                    f"at_a_glance inputs are not verified input formats: {sorted(bad_inputs)}"
                )
            if bad_outputs:
                errors.append(
                    f"at_a_glance outputs are not verified output formats: {sorted(bad_outputs)}"
                )
            if bad_titles:
                errors.append(
                    f"at_a_glance capabilities are not core capabilities: {sorted(bad_titles)}"
                )
    elif glance is not None:
        errors.append("at_a_glance is omitted, so it is null")
    if glance is not None:
        titles = glance.get("capability_titles", [])
        if len(titles) < 3:
            errors.append("at_a_glance needs at least three capability titles")
        for title in titles:
            problem = capability_title_problem(title, len(titles))
            if problem is not None:
                errors.append(
                    f"at_a_glance capability title {title!r} {problem}; shorten the title"
                )

    examples = {i for i in supported if i.startswith("example:")}
    quick = output.get("quick_start_example_id")
    if "quick_start" in included:
        if quick not in examples:
            errors.append(f"quick_start_example_id must be a SUPPORTED example; got {quick!r}")
    elif quick is not None:
        errors.append(f"quick_start_example_id is null when quick_start is omitted; got {quick!r}")
    second = output.get("second_quick_start_example_id")
    if second is not None and (second not in examples or second == quick):
        errors.append(
            "second_quick_start_example_id must be a SUPPORTED example other than the first; "
            f"got {second!r}"
        )
    additional = output.get("additional_example_ids", [])
    if quick in additional or second in additional or len(set(additional)) != len(additional):
        errors.append("additional_example_ids must be distinct and exclude the quick start")
    if ("additional_examples" in included) != bool(additional):
        errors.append(
            "additional_example_ids are given exactly when additional_examples is included"
        )
    flagship = output.get("flagship_example_id")
    if flagship is not None and flagship not in additional:
        errors.append(
            f"flagship_example_id must be one of additional_example_ids; got {flagship!r}"
        )

    raw_hubs = output.get("api_hubs", [])
    seen_hub_ids: set[Any] = set()
    hubs = []
    for hub in raw_hubs:
        hub_id = hub.get("symbol_fact_id")
        if hub_id in seen_hub_ids:
            continue
        seen_hub_ids.add(hub_id)
        hubs.append(hub)
    if len(hubs) != len(raw_hubs):
        output["api_hubs"] = hubs
    symbols = {i for i in supported if i.startswith("public_symbol:")}
    hub_ids = [hub.get("symbol_fact_id") for hub in hubs]
    if len(hubs) > policy.api_hubs_max:
        errors.append(f"api_hubs exceed the ceiling of {policy.api_hubs_max}")
    if any(hub not in symbols for hub in hub_ids):
        errors.append("api_hubs must each be a supported public_symbol fact")
    mis_hubbed = sorted(hub for hub in hub_ids if hub in _mis_hubbed_symbol_ids(facts))
    if mis_hubbed:
        errors.append(
            "api_hubs name a module/package fact with a same-named class or enum sibling "
            f"available instead: {mis_hubbed}"
        )
    if ("api_reference" in included) != bool(hubs):
        errors.append("api_hubs are given exactly when api_reference is included")

    for item in output.get("material_limitations", []):
        if not item.get("fact_ids") and not item.get("unit_ids"):
            errors.append("a material limitation cites at least one fact or inherited unit")

    link_facts = {
        fact.id: fact.value for fact in facts.by_kind("link_target") if fact.polarity == "SUPPORTED"
    }
    unrenderable_anchors = _unrenderable_anchor_ids(facts)
    required_link_sections = {
        **_required_link_sections(dispositions),
        **_kept_list_links(output, facts, dispositions),
    }
    raw_links = output.get("links", [])
    kept_links: list[dict[str, Any]] = []
    optional_hrefs: list[str] = []
    budget = plan_time_budget(policy.link_allocation, policy.aspose_links_max)
    counter = SlotCounter(budget)
    for href in preserved_hrefs:
        counter.add(href)
    for target in required_link_sections:
        if (
            target not in _SHELL_OWNED_LINKS
            and link_facts.get(target) is not None
            and any(domain in link_facts[target] for domain in _ASPOSE_DOMAINS)
        ):
            counter.add(link_facts[target])
    for link in raw_links:
        target = link.get("link_fact_id")
        value = link_facts.get(target)
        is_aspose = (
            target not in _SHELL_OWNED_LINKS
            and value is not None
            and any(domain in value for domain in _ASPOSE_DOMAINS)
        )
        if is_aspose and value is not None and target not in required_link_sections:
            if not counter.would_fit(value):
                continue
            counter.add(value)
            optional_hrefs.append(value)
        kept_links.append(link)
    if len(kept_links) != len(raw_links):
        output["links"] = kept_links
    if "documentation_resources" in included and not _documentation_resources_holds(
        output, facts, dispositions
    ):
        conditions["documentation_resources"] = False
        output["sections"] = [
            _decision(section, conditions[section.id]) for section in SEMANTIC_SHELL
        ]
        included = {entry["section_id"] for entry in output["sections"] if entry["include"]}
    targets = [link.get("link_fact_id") for link in output.get("links", [])]
    for target in sorted({t for t in targets if targets.count(t) > 1}):
        errors.append(f"link {target!r} is assigned more than once; never the same target twice")
    for link in output.get("links", []):
        target = link.get("link_fact_id")
        section = link.get("section_id")
        if target in _SHELL_OWNED_LINKS:
            errors.append(
                f"link {target!r} renders on its own (the banner or the closing Enterprise "
                "sentence); the same URL has its own numbered link_target fact if a section "
                "needs to reference it directly"
            )
            continue
        if target in unrenderable_anchors and target not in required_link_sections:
            errors.append(
                f"link {target!r} is an in-page anchor to a source README heading this document "
                "does not render; assign a link the candidate can resolve"
            )
        elif target not in link_facts:
            errors.append(f"link {target!r} is not a verified link target")
        if section not in included:
            errors.append(
                f"link {target!r} is assigned to a section that is not included: {section!r}"
            )
    errors.extend(f"Aspose links: {problem}" for problem in slot_violations(budget, optional_hrefs))
    for deviation in output.get("deviations", []):
        if deviation.get("section_id") not in section_ids():
            errors.append(f"deviation names an unknown section {deviation.get('section_id')!r}")
    return errors


def recover_uncited_capability_titles(
    output: dict[str, Any], facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``run_job``'s final rejected attempt only."""
    capabilities = output.get("core_capabilities")
    if not isinstance(capabilities, list):
        return None
    name = _product_name(facts)
    nouns = prose_nouns(facts, name)
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    changed = False
    for item in capabilities:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", ""))
        cited_ids = list(item.get("fact_ids", []))
        cited = " ".join(values.get(i, "") for i in cited_ids).lower()
        unsupported = sorted(
            term
            for term in title_terms(title, facts)
            if term not in nouns
            and term.lstrip(".").lower() not in cited
            and term.lstrip(".").lower() not in common
        )
        if not unsupported:
            continue
        candidates = [supporting_fact_ids(term, facts) for term in unsupported]
        if not all(candidates):
            continue
        item["fact_ids"] = sorted({*cited_ids, *(ids[0] for ids in candidates)})
        changed = True
    return output if changed else None


def recover_duplicate_link_assignments(output: dict[str, Any]) -> dict[str, Any] | None:
    """Last-resort correction for ``run_job``'s final rejected attempt only: keep the FIRST
    assignment the model wrote for each target and drop every later repeat."""
    links = output.get("links")
    if not isinstance(links, list):
        return None
    seen: set[str] = set()
    kept: list[Any] = []
    for link in links:
        target = link.get("link_fact_id") if isinstance(link, dict) else None
        if isinstance(target, str):
            if target in seen:
                continue
            seen.add(target)
        kept.append(link)
    if len(kept) == len(links):
        return None
    return {**output, "links": kept}


def recover_planning_output(output: dict[str, Any], facts: FactsDocument) -> dict[str, Any] | None:
    """The single ``recover=`` combining both deterministic last resorts, in order."""
    deduplicated = recover_duplicate_link_assignments(output)
    base = output if deduplicated is None else deduplicated
    retitled = recover_uncited_capability_titles(base, facts)
    if retitled is not None:
        return retitled
    return deduplicated


def recover_visible_line_overage(
    output: dict[str, Any], *, levers: Mapping[str, int]
) -> dict[str, Any] | None:
    """Last-resort correction for a ``targeted_repair`` job's own final rejected attempt only."""
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return None
    cleared: list[tuple[str, Any]] = []
    for field_name in levers:
        if revised.get(field_name) is not None:
            cleared.append((field_name, revised[field_name]))
            revised[field_name] = None
    if not cleared:
        return None
    corrected = {**output, "revised_output": revised}
    corrected["changes"] = [
        {
            "id": f"R{index:02d}",
            "path": field_name,
            "before": str(before),
            "after": "null",
            "fact_ids": [],
        }
        for index, (field_name, before) in enumerate(cleared, start=1)
    ]
    return corrected


VISIBLE_LINE_RENDER_MARGIN = 4


def bound_visible_line_overage(
    output: Mapping[str, Any], *, overage: int, levers: Mapping[str, int]
) -> dict[str, Any] | None:
    """The deterministic bound on a BC-07 visible-line overage."""
    if overage <= 0 or not levers:
        return None
    if sum(levers.values()) - VISIBLE_LINE_RENDER_MARGIN < overage:
        return None
    return recover_visible_line_overage(
        {"revised_output": copy.deepcopy(dict(output)), "changes": []}, levers=levers
    )


def summarize_plan(output: dict[str, Any]) -> str:
    included = [entry["section_id"] for entry in output.get("sections", []) if entry.get("include")]
    return (
        f"sections {len(included)}/{len(section_ids())}, "
        f"capabilities {len(output.get('core_capabilities', []))}, "
        f"hubs {len(output.get('api_hubs', []))}, "
        f"examples 1+{len(output.get('additional_example_ids', []))}, "
        f"links {len(output.get('links', []))}, "
        f"limitations {len(output.get('material_limitations', []))}"
    )


def write_plan(output: dict[str, Any], path: Path) -> str:
    """Write the accepted plan as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
