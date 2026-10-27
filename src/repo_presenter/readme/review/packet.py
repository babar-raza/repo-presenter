"""The independent reviewer's call schema and the delimiting of untrusted text
(``prompts/independent_review.yaml`` v17).

Evidence only (plan D6c): a unit's packet (``readme.review.sectionwise.unit_packet``) carries the
repository coordinates, the unit's author-written text, the facts it may cite, the part of the
original README it draws on and its plan entries, and nothing the authoring side wrote to persuade:
the author's prompts never enter, and every free-text ``rationale`` / ``reason`` the planner and
reconciler attached to a decision is dropped. The reviewer judges the candidate against the facts,
not against the case its author made for it.

The README texts are untrusted data (plan D6d). Each is wrapped in a begin/end pair whose label
embeds the SHA-256 of the text, so the text cannot contain its own closing line, and nothing in a
README can close the region early. The candidate's lines are shown with their numbers
(``0007| text``): a reviewer cites lines, never retypes text, and ``reply.resolve_cited_lines``
derives the quote and the section from the raw candidate, so the number prefix is not part of any
quote.

The call schema narrows the manifest's finding to the amendment of plan D2 (a finding carries ONE
typed claim): ``claim_kind`` plus exactly the typed field that kind needs, and nothing else.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Collection, Mapping
from typing import Any

from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.readme.review.findings import CLAIM_KINDS
from repo_presenter.readme.review.reply import valid_section_ids

#: Free text the authoring side attached to its own decisions. A reviewer weighs the decision, not
#: the argument for it.
AUTHOR_NARRATIVE_KEYS = frozenset({"rationale", "reason", "reasoning", "justification"})
#: The typed field each typed claim kind fills (and no other kind may).
TYPED_FIELD: Mapping[str, str] = {
    "absence": "absent",
    "name_denial": "unsupported_names",
    "omission": "omission",
}


def delimited(name: str, text: str, *, shown: str | None = None) -> str:
    """``text`` (or ``shown``, its display form) between a begin and an end line that carry the
    digest of ``text`` itself."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return (
        f"<<<BEGIN UNTRUSTED {name} sha256:{digest}>>>\n"
        f"{text if shown is None else shown}\n"
        f"<<<END UNTRUSTED {name} sha256:{digest}>>>"
    )


def without_narrative(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {
            key: without_narrative(value)
            for key, value in node.items()
            if key not in AUTHOR_NARRATIVE_KEYS
        }
    if isinstance(node, list):
        return [without_narrative(item) for item in node]
    return node


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


def review_schema(
    loaded: LoadedManifest,
    plan: Mapping[str, Any],
    *,
    sections: Collection[str] | None = None,
) -> dict[str, Any]:
    """The manifest's output schema specialised for this review: each finding is one of the six
    claim kinds' own shapes, and its ``section_id`` is one of ``sections`` (a unit's own), or, when
    none is given, one of the ids the contract accepts for ``plan``."""
    schema = copy.deepcopy(loaded.manifest.output.schema_)
    items = schema["properties"]["findings"]["items"]
    items["properties"]["section_id"] = {
        "type": "string",
        "enum": sorted(valid_section_ids(plan) if sections is None else sections),
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
