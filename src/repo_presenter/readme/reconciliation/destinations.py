"""Where a kept inherited unit can go: the sections that can hold it, and the nearest one.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/reconciliation/destinations.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry) -- needed by ``reconciliation/dispositions.py``'s ``normalize()``
(``_rehome_misfiled_units``).

Reconciliation (S4) offers every section of the shell as a destination for a kept unit, and four
of them cannot hold one. The renderer owns Installation, Dependencies, the identity and badge
rows, the Navigation list, Third-Party Notices and License: they print from facts and have no
place for an inherited paragraph or code block. At a Glance holds one diagram and nothing else. A
section whose condition does not hold at this revision is not in the document at all.
"""

from __future__ import annotations

import copy
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL, section_ids
from repo_presenter.readme.composition.planning import section_conditions
from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy
from repo_presenter.readme.composition.source_topics import (
    heading_parts,
    path_topic,
    root_heading,
    source_heading,
    topic_of,
)

PLACING_DISPOSITIONS = (
    "VERIFIED_PRESERVE",
    "VERIFIED_REWRITE",
    "VERIFIED_MOVE",
    "CORRECT_WITH_EVIDENCE",
)

_DIAGRAM_ONLY = frozenset({"at_a_glance"})
_NEVER_AUTOMATIC = frozenset({"opening"})
_PRINTS = {
    "enterprise_relationship": frozenset({"paragraph", "heading"}),
    "documentation_resources": frozenset({"paragraph", "list", "blockquote"}),
    "key_capabilities": frozenset({"paragraph", "list", "blockquote"}),
    "scope_limitations": frozenset({"paragraph", "list", "table", "blockquote"}),
}

_HOMES: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "build": (
        ("development_testing", "additional_examples", "quick_start"),
        ("development_testing", "scope_limitations"),
    ),
    "example": (
        ("additional_examples", "quick_start", "development_testing"),
        ("additional_examples", "quick_start", "scope_limitations"),
    ),
    "install": (
        ("development_testing", "quick_start", "additional_examples"),
        ("development_testing", "quick_start", "documentation_resources", "scope_limitations"),
    ),
    "setup": (
        ("quick_start", "development_testing", "additional_examples"),
        ("quick_start", "development_testing", "documentation_resources", "scope_limitations"),
    ),
    "api": (("api_reference",), ("api_reference",)),
    "limits": (("scope_limitations",), ("scope_limitations",)),
    "capabilities": (
        ("additional_examples", "quick_start"),
        ("key_capabilities", "scope_limitations"),
    ),
    "resources": (
        ("additional_examples", "development_testing"),
        ("documentation_resources", "scope_limitations"),
    ),
}
_MISFILED: Mapping[str, frozenset[str]] = {
    "install": frozenset(
        {
            "scope_limitations",
            "documentation_resources",
            "key_capabilities",
            "api_reference",
            "additional_examples",
        }
    ),
    "build": frozenset({"scope_limitations", "key_capabilities", "api_reference"}),
    "api": frozenset({"key_capabilities", "scope_limitations"}),
}
_SHELL_KINDS = frozenset({"heading", "badge_row", "html_block"})
_KIND_HOMES: tuple[tuple[str, ...], tuple[str, ...]] = (
    ("development_testing", "additional_examples", "quick_start"),
    ("scope_limitations", "documentation_resources", "key_capabilities"),
)


def holdable_sections(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> tuple[str, ...]:
    """The sections a placing disposition may name for this repository, in shell order."""
    absent = {
        section for section, holds in section_conditions(facts, policy).items() if holds is False
    }
    return tuple(
        section.id
        for section in SEMANTIC_SHELL
        if section.owner != "D" and section.id not in absent and section.id not in _DIAGRAM_ONLY
    )


def nearest_holdable(
    unit_id: str, heading_path: str | None, holdable: Collection[str], root: str | None = None
) -> str | None:
    """The holdable section nearest to one unit, or ``None`` when none of them suits it."""
    kind = unit_id.rsplit(".", 1)[-1]
    code = kind == "code_block"
    parts = heading_parts(heading_path) if heading_path else []
    if parts and root is not None and parts[0] == root:
        parts = parts[1:]
        if not parts:
            return None
    topic = topic_of(parts)
    if topic == "furniture":
        return None
    candidates = _HOMES[topic][0 if code else 1] if topic is not None else ()
    for pool in (candidates, _KIND_HOMES[0 if code else 1]):
        for section in pool:
            if section in holdable and section not in _NEVER_AUTOMATIC and kind in _kinds(section):
                return section
    return None


def rehomed(
    unit_id: str,
    heading_path: str | None,
    destination: str | None,
    holdable: Collection[str],
    root: str | None = None,
) -> str | None:
    """The section a kept unit belongs in when the reply filed it somewhere else, or ``None`` when
    it stays where it is."""
    if unit_id.rsplit(".", 1)[-1] in _SHELL_KINDS or destination is None:
        return None
    topic = path_topic(heading_path, root)
    if topic is None or destination not in _MISFILED.get(topic, frozenset()):
        return None
    home = nearest_holdable(unit_id, heading_path, holdable, root)
    return home if home is not None and home != destination else None


def _kinds(section: str) -> Collection[str]:
    """The unit kinds ``section`` prints as written (all of them for a section not listed)."""
    return _PRINTS.get(
        section, frozenset({"paragraph", "list", "table", "code_block", "blockquote"})
    )


def nearest_for_units(
    units: Sequence[Fact], holdable: Collection[str], context: Sequence[Fact] | None = None
) -> dict[str, str | None]:
    """:func:`nearest_holdable` for each of ``units``, keyed by unit ID."""
    root = root_heading(context if context is not None else units)
    return {
        unit.id: nearest_holdable(unit.id, source_heading(unit), holdable, root) for unit in units
    }


def disposition_variants(item: Mapping[str, Any], holdable: Sequence[str]) -> list[dict[str, Any]]:
    """The S4 schema's two complete object shapes, from the manifest's one."""
    placing = copy.deepcopy(dict(item))
    placing["properties"]["disposition"] = {"enum": list(PLACING_DISPOSITIONS)}
    placing["properties"]["destination_section"] = {"type": "string", "enum": list(holdable)}
    other = copy.deepcopy(dict(item))
    other["properties"]["disposition"] = {
        "enum": [
            name
            for name in item["properties"]["disposition"]["enum"]
            if name not in PLACING_DISPOSITIONS
        ]
    }
    other["properties"]["destination_section"] = {
        "oneOf": [{"type": "null"}, {"type": "string", "enum": list(section_ids())}]
    }
    return [placing, other] if holdable else [other]
