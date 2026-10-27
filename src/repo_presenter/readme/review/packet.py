"""The independent reviewer's packet and call schema (``prompts/independent_review.yaml`` v15).

Evidence only (plan D6c): the packet carries the repository coordinates, the two READMEs, the facts,
the plan, the dispositions and the deterministic validation result, and nothing the authoring side
wrote to persuade -- the author's prompts never enter, and every free-text ``rationale`` / ``reason``
the planner and reconciler attached to a decision is dropped. The reviewer judges the candidate
against the facts, not against the case its author made for it.

The two README texts are untrusted data (plan D6d). Each is wrapped in a begin/end pair whose label
embeds the SHA-256 of the README, so the text cannot contain its own closing line, and nothing in a
README can close the region early. The original is wrapped byte for byte. The candidate's lines are
shown with their numbers (``0007| text``): a reviewer cites lines, never retypes text, and
``reply.resolve_cited_lines`` derives the quote and the section from the raw candidate, so the
number prefix is not part of any quote.

The call schema narrows the manifest's finding to the amendment of plan D2 (a finding carries ONE
typed claim): ``claim_kind`` plus exactly the typed field that kind needs, and nothing else.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from typing import Any

from repo_presenter.core.facts import (
    FACT_KINDS,
    POLARITIES,
    FactsDocument,
    bounded_records,
)
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.readme.review.findings import CLAIM_KINDS
from repo_presenter.readme.review.reply import valid_section_ids

#: Free text the authoring side attached to its own decisions. A reviewer weighs the decision, not
#: the argument for it.
AUTHOR_NARRATIVE_KEYS = frozenset({"rationale", "reason", "reasoning", "justification"})
#: Most public-symbol values ``symbol_index`` lists; one more line says how many it left out.
SYMBOL_INDEX_CAP = 1500
#: The typed field each typed claim kind fills (and no other kind may).
TYPED_FIELD: Mapping[str, str] = {
    "absence": "absent",
    "name_denial": "unsupported_names",
    "omission": "omission",
}


def numbered(text: str) -> str:
    """``text``'s lines, each prefixed with its 1-based number, as ``resolve_cited_lines`` counts."""
    return "\n".join(f"{n:04d}| {row}" for n, row in enumerate(text.splitlines(), 1))


def delimited(name: str, text: str, *, shown: str | None = None) -> str:
    """``text`` (or ``shown``, its display form) between a begin and an end line that carry the
    digest of ``text`` itself."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return (
        f"<<<BEGIN UNTRUSTED {name} sha256:{digest}>>>\n"
        f"{text if shown is None else shown}\n"
        f"<<<END UNTRUSTED {name} sha256:{digest}>>>"
    )


def _without_narrative(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {
            key: _without_narrative(value)
            for key, value in node.items()
            if key not in AUTHOR_NARRATIVE_KEYS
        }
    if isinstance(node, list):
        return [_without_narrative(item) for item in node]
    return node


def symbol_index(facts: FactsDocument, shown_ids: frozenset[str]) -> str:
    """The values of the SUPPORTED ``public_symbol`` facts that ``facts`` leaves out (its depth and
    count bounds), one per line, sorted; every one is a fact."""
    values = sorted(
        {
            fact.value
            for fact in facts.facts
            if fact.kind == "public_symbol"
            and fact.polarity == "SUPPORTED"
            and fact.id not in shown_ids
        }
    )
    if not values:
        return "(none: every SUPPORTED public symbol is already in `facts`)"
    lines = values[:SYMBOL_INDEX_CAP]
    if len(values) > len(lines):
        lines.append(
            f"(and {len(values) - len(lines)} more SUPPORTED public symbols not listed here; "
            "a name you cannot find in `facts` or here may still be one of them, so do not "
            "deny it for that reason alone)"
        )
    return "\n".join(lines)


def validation_context(validation: Mapping[str, Any]) -> dict[str, Any]:
    """The deterministic validation result as context: each check's verdict, and the details of
    the ones that failed."""
    checks = []
    for check in validation.get("checks", []):
        record: dict[str, Any] = {
            "id": check.get("id"),
            "name": check.get("name"),
            "verdict": check.get("verdict"),
        }
        if check.get("verdict") == "FAIL":
            record["details"] = list(check.get("details", []))
        checks.append(record)
    return {"summary": dict(validation.get("summary", {})), "checks": checks}


def review_packet(
    *,
    repository: str,
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    """The packet ``prompts/independent_review.yaml`` declares, field for field."""
    records = bounded_records(facts, FACT_KINDS, POLARITIES)
    shown = frozenset(record["id"] for record in records)
    return {
        "repository": repository,
        "candidate_readme": delimited(
            "candidate_readme", candidate_readme, shown=numbered(candidate_readme)
        ),
        "original_readme": delimited("original_readme", original_readme),
        "facts": records,
        "symbol_index": symbol_index(facts, shown),
        "plan": _without_narrative(dict(plan)),
        "dispositions": _without_narrative(dict(dispositions)),
        "validation": validation_context(validation),
    }


def _finding_variant(base: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """The finding shape for one ``claim_kind``: the common fields plus exactly its typed field."""
    variant = copy.deepcopy(dict(base))
    properties = variant["properties"]
    wanted = TYPED_FIELD.get(kind)
    for field in TYPED_FIELD.values():
        if field != wanted:
            properties.pop(field, None)
    properties["claim_kind"] = {"enum": [kind]}
    # The model cites lines; code derives the quote (reply.resolve_cited_lines).
    properties.pop("quote", None)
    required = [
        name
        for name in variant["required"]
        if name not in TYPED_FIELD.values() and name != "quote"
    ]
    required.append("lines")
    if wanted is not None:
        required.append(wanted)
        if wanted == "omission":
            properties["omission"] = next(
                option
                for option in properties["omission"]["oneOf"]
                if option.get("type") == "object"
            )
        else:
            properties[wanted] = {**properties[wanted], "minItems": 1}
    variant["required"] = required
    variant["additionalProperties"] = False
    return variant


def review_schema(loaded: LoadedManifest, plan: Mapping[str, Any]) -> dict[str, Any]:
    """The manifest's output schema specialised for this candidate: each finding is one of the six
    claim kinds' own shapes, and its ``section_id`` is one of the ids the contract accepts."""
    schema = copy.deepcopy(loaded.manifest.output.schema_)
    items = schema["properties"]["findings"]["items"]
    items["properties"]["section_id"] = {
        "type": "string",
        "enum": sorted(valid_section_ids(plan)),
    }
    declared = tuple(items["properties"]["claim_kind"]["enum"])
    if declared != CLAIM_KINDS:
        raise ValueError(
            f"independent_review declares claim kinds {declared}, but the reviewer contract "
            f"recognises {CLAIM_KINDS}"
        )
    schema["properties"]["findings"]["items"] = {
        "oneOf": [_finding_variant(items, kind) for kind in CLAIM_KINDS]
    }
    return schema
