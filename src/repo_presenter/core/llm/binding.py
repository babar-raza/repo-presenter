"""Bind a job's output to the facts it cites: an unknown or contradicted ID rejects the output.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``core/llm/binding.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).

The guard is structural. It walks the output for every key that carries fact or unit IDs and
checks each against the facts document; it never reads prose. What each binding class requires:
``fact_ids`` and ``selection_ids`` cite only SUPPORTED facts; ``revision_ids`` cite only SUPPORTED
facts in the repair's own changes, while its ``revised_output`` is bound by the causal stage's own
binding; ``finding_ids`` cite facts that exist; ``unit_ids`` name every inherited unit exactly once.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from typing import Any

from repo_presenter.core.facts import FactsDocument

Binding = str
_FACT_KEY_SUFFIXES = ("_fact_id", "_fact_ids", "_example_id", "_example_ids", "_format_ids")


@dataclass(frozen=True)
class CitedIds:
    fact_ids: tuple[str, ...]
    unit_ids: tuple[str, ...]


def _walk(payload: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk(item)


def _is_fact_key(key: str) -> bool:
    return key == "fact_ids" or key.endswith(_FACT_KEY_SUFFIXES)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def collect_ids(payload: Any) -> CitedIds:
    """Every fact ID and unit ID the output cites, in document order, duplicates kept."""
    fact_ids: list[str] = []
    unit_ids: list[str] = []
    for key, value in _walk(payload):
        if _is_fact_key(key):
            fact_ids.extend(_strings(value))
        elif key in {"unit_id", "unit_ids"}:
            unit_ids.extend(_strings(value))
    return CitedIds(tuple(fact_ids), tuple(unit_ids))


def resolve_symbol_ids(payload: Any, facts: FactsDocument) -> list[tuple[str, str]]:
    """Rewrite, in place, a cited public_symbol ID the facts do not carry to the shortest
    SUPPORTED public_symbol ID with the same final name segment, and return the rewrites."""
    known = {fact.id for fact in facts.facts}
    by_name: dict[str, list[str]] = {}
    for fact in facts.by_kind("public_symbol"):
        if fact.polarity == "SUPPORTED":
            by_name.setdefault(fact.id.rsplit(".", 1)[-1].lower(), []).append(fact.id)
    rewrites: dict[str, str] = {}

    def resolve(value: str) -> str:
        if value in known or not value.startswith("public_symbol:"):
            return value
        candidates = by_name.get(value.rsplit(".", 1)[-1].lower(), [])
        if not candidates:
            return value
        target = min(candidates, key=lambda i: (len(i), i))
        rewrites[value] = target
        return target

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if _is_fact_key(key) and isinstance(value, str):
                    node[key] = resolve(value)
                elif _is_fact_key(key) and isinstance(value, list):
                    node[key] = [resolve(v) if isinstance(v, str) else v for v in value]
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return sorted(rewrites.items())


def drop_unknown_finding_ids(payload: Any, facts: FactsDocument) -> list[str]:
    """Remove, in place, every cited ID the facts do not carry from a review finding's own
    ``fact_ids``; returns the IDs dropped."""
    known = {fact.id for fact in facts.facts}
    dropped: list[str] = []
    findings = payload.get("findings") if isinstance(payload, dict) else None
    for finding in findings if isinstance(findings, list) else []:
        cited = finding.get("fact_ids") if isinstance(finding, dict) else None
        if not isinstance(cited, list):
            continue
        kept = [item for item in cited if not isinstance(item, str) or item in known]
        dropped.extend(item for item in cited if isinstance(item, str) and item not in known)
        if len(kept) != len(cited):
            finding["fact_ids"] = kept
    return dropped


def fold_duplicate_units(payload: Any) -> None:
    """A repeated ``unit_id`` disposition is dropped in place, keeping the first."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if (
                isinstance(value, list)
                and value
                and all(isinstance(item, dict) and "unit_id" in item for item in value)
            ):
                seen: set[Any] = set()
                kept = []
                for item in value:
                    unit_id = item.get("unit_id")
                    if unit_id in seen:
                        continue
                    seen.add(unit_id)
                    kept.append(item)
                if len(kept) != len(value):
                    payload[key] = kept
            else:
                fold_duplicate_units(value)
    elif isinstance(payload, list):
        for item in payload:
            fold_duplicate_units(item)


def merge_partial_units(revised: Any, original: Any) -> Any:
    """A copy of ``revised`` with each unit-keyed list filled in from ``original`` for any unit
    the reply left silent."""
    if not (isinstance(revised, dict) and isinstance(original, dict)):
        return revised
    merged = dict(revised)
    for key, original_value in original.items():
        if not (
            isinstance(original_value, list)
            and original_value
            and all(isinstance(item, dict) and "unit_id" in item for item in original_value)
        ):
            continue
        declared = merged.get(key)
        if not isinstance(declared, list):
            declared = []
        declared_by_unit = {
            item["unit_id"]: item
            for item in declared
            if isinstance(item, dict) and "unit_id" in item
        }
        merged[key] = [declared_by_unit.get(item["unit_id"], item) for item in original_value]
    return merged


def fill_silent_units(revised: Any, original: Any) -> Any:
    """``revised`` with each unit-keyed list completed from ``original`` for the units it left out."""
    if not (isinstance(revised, dict) and isinstance(original, dict)):
        return revised
    completed = dict(revised)
    for key, original_value in original.items():
        revised_value = completed.get(key)
        if not (
            isinstance(original_value, list)
            and isinstance(revised_value, list)
            and original_value
            and all(isinstance(item, dict) and "unit_id" in item for item in original_value)
            and all(isinstance(item, dict) and "unit_id" in item for item in revised_value)
        ):
            continue
        stated = {item["unit_id"] for item in revised_value}
        silent = [item for item in original_value if item["unit_id"] not in stated]
        if silent:
            completed[key] = [*revised_value, *silent]
    return completed


def silent_unit_ids(output: Any, facts: FactsDocument) -> list[str]:
    """The inherited units ``facts`` holds that ``output`` cites nowhere, in the facts' order."""
    if not isinstance(output, dict):
        return []
    cited = set(collect_ids(output).unit_ids)
    return [fact.id for fact in facts.by_kind("inherited_unit") if fact.id not in cited]


def add_silent_units(base: Any, narrowed: Any, silent: Collection[str]) -> Any:
    """``base`` with each unit-keyed list extended by the ``silent`` units ``narrowed`` answers."""
    if not (isinstance(base, dict) and isinstance(narrowed, dict)):
        return base
    merged = dict(base)
    for key, value in narrowed.items():
        if not (
            isinstance(value, list)
            and all(isinstance(item, dict) and "unit_id" in item for item in value)
        ):
            continue
        wanted = [item for item in value if item["unit_id"] in silent]
        if wanted:
            current = merged.get(key)
            merged[key] = [*(current if isinstance(current, list) else []), *wanted]
    return merged


def binding_errors(payload: Any, facts: FactsDocument, binding: Binding) -> list[str]:
    """Why the output may not be used, or an empty list when every citation holds."""
    known = {fact.id: fact for fact in facts.facts}
    if binding == "revision_ids" and isinstance(payload, dict):
        payload = {key: value for key, value in payload.items() if key != "revised_output"}
    cited = collect_ids(payload)
    errors: list[str] = []
    require_supported = binding in {"fact_ids", "selection_ids", "revision_ids"}
    for fact_id in dict.fromkeys(cited.fact_ids):
        fact = known.get(fact_id)
        if fact is None:
            errors.append(f"unknown fact ID {fact_id}")
        elif require_supported and fact.polarity != "SUPPORTED":
            errors.append(f"fact {fact_id} is {fact.polarity}, not SUPPORTED")
    for unit_id in dict.fromkeys(cited.unit_ids):
        unit = known.get(unit_id)
        if unit is None:
            errors.append(f"unknown inherited unit {unit_id}")
        elif unit.kind != "inherited_unit":
            errors.append(
                f"unknown inherited unit {unit_id}: it is a fact of kind {unit.kind}, not an "
                "inherited_unit; unit_ids take only inherited_unit:... IDs, so cite this one in "
                "fact_ids and leave unit_ids empty when no inherited unit applies"
            )
    if binding == "unit_ids":
        expected = [fact.id for fact in facts.by_kind("inherited_unit")]
        counts = {unit_id: cited.unit_ids.count(unit_id) for unit_id in expected}
        missing = [unit_id for unit_id, count in counts.items() if count == 0]
        duplicated = [unit_id for unit_id, count in counts.items() if count > 1]
        if missing:
            errors.append(f"no disposition for inherited units: {', '.join(missing)}")
        if duplicated:
            errors.append(f"more than one disposition for: {', '.join(duplicated)}")
    return errors
