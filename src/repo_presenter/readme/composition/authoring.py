"""Stage S6: the section_authoring job wiring - one packet per LLM-owned section, one guard.

Ported (ADAPT, near-complete) from the old repository-presenter project's ``components/readme/
composition/authoring.py`` (2957 lines) per migration/reuse-manifest.yaml ("readme/composition/"
entry). Read in full as part of this taskcard. Despite the module's own name, NOTHING in this file
calls an LLM: every function here is a pure, deterministic transformation over dicts and
``FactsDocument`` -- packet/schema construction, the ``unit_checks`` validation guard, and a family
of deterministic last-resort ``recover=`` corrections for ``core.llm.jobs.run_job``. The actual
network call happens one layer up, in an orchestrator (the old repo's ``repair/rounds.py``, not
part of this taskcard's file list and not ported) that calls ``run_job(manifest, packet, schema,
checks=unit_checks, recover=...)``.

**Deferred** (not ported): ``reconstructed_task_output``, ``_reconstruction_lineage_holds`` and
``write_raw_calls`` -- a sealed-bundle replay mechanism (rebuild a task's accepted output from a
previous run's ``content_units.json`` without a fresh provider call) that depends on
``core/llm/ledger.canonical_hash`` AND a bundle/seal directory layout this repository does not
have yet (no ``bundle/seal.py`` equivalent exists here). Everything else -- every packet builder,
every schema specialiser, ``unit_checks`` itself, and every ``recover_*`` function -- is ported.
"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import os
import re
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from repo_presenter.core.facts import REPOSITORY_FILES_ATTRIBUTE, Fact, FactsDocument, bounded_records
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.audience import audience_errors, support_texts
from repo_presenter.readme.composition.components.ecosystems import REGISTRY_NAMES, host_names
from repo_presenter.readme.composition.components.identity import (
    canonicalise_name_variants,
    product_name,
    product_name_tokens,
    spells_the_product,
)
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL, section_ids
from repo_presenter.readme.composition.components.terminology import canonical_forms
from repo_presenter.readme.composition.coverage import Destinations, states_all, uncovered
from repo_presenter.readme.composition.list_coverage import OWED_SECTIONS, kept_lists, list_items
from repo_presenter.readme.composition.placement import placements
from repo_presenter.readme.composition.text_hygiene import hygiene_errors
from repo_presenter.readme.evidence.facts.links import link_text

CONTENT_UNITS_FILENAME = "content_units.json"
# Filename only (ADD, 2026-10-25): a future seal.py port checks this as an optional bundle
# artifact. write_raw_calls itself depends on repair/rounds.py's batch-call machinery, not ported.
RAW_CALLS_FILENAME = "raw_calls.json"
AUTHORED_SECTIONS: tuple[str, ...] = tuple(
    section.id for section in SEMANTIC_SHELL if section.owner != "D" and section.id != "at_a_glance"
)
_COMPOSITE_VALUE = re.compile(r"(?=\S+\Z)\S*[-/.]\S*")
_DOTTED = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
_SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")
_CALL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\(\)")
_COORDINATE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z0-9_.-]+\b")
_MODULE_PATH = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+(?:/[A-Za-z0-9_.-]+)+\b"
)
_URL = re.compile(r"<?https?://\S+")
_NOT_PROSE = (
    re.compile(r"```.*?```", re.DOTALL),
    re.compile(r"`[^`]*`"),
    re.compile(r"\]\([^)]*\)"),
    re.compile(r"<?https?://\S+"),
    re.compile(r"<[^>]+>"),
)
_CODE_SPAN = re.compile(r"`([^`\n]*)`")
_FENCED_BLOCK = re.compile(r"^[ \t]*```([^\n`]*)\n(.*?)^[ \t]*```", re.DOTALL | re.MULTILINE)
_COMMAND_FENCES = frozenset({"bash", "sh", "shell", "console", "zsh", "powershell", "pwsh", "cmd"})
_MEMBER_CAP = 60
_TYPE_BATCH = 40
_TYPE_OBJECTIVE = (
    "One sentence per public type in this batch, from its verified signature (its bases) and "
    "its name: what it represents or does for a visitor. Never mechanical filler such as a "
    "member count or 'extends X', never a count, never a claim the signature does not carry."
)
NORMALISATION_VERSION = "36"
_EXCEPTION_SUFFIXES = ("Error", "Exception", "Warning")
EDITION_SUBSTITUTE = re.compile(
    r"(?i)\b(?:commercial|on[- ]?premises?|premium|paid|full|licensed|proprietary)[\s-]+"
    r"(?:edition|version)s?\b"
)


def edition_substitutes(text: str) -> list[str]:
    """The forbidden edition substitutes ``text`` names, each as written, in order."""
    return [match.group(0) for match in EDITION_SUBSTITUTE.finditer(text)]


_TITLE_WORD = re.compile(r"[A-Za-z0-9.]+")
_FORBIDDEN = (
    ("```", "a code fence"),
    ("http://", "a URL"),
    ("https://", "a URL"),
    ("www.", "a URL"),
    ("](", "a Markdown link"),
    ("# ", "a Markdown heading"),
    ("* ", "a Markdown list"),
    ("- ", "a Markdown list"),
    ("|", "a Markdown table"),
    ("<", "HTML"),
    ("\n", "a line break; a unit is one paragraph"),
    ("pip install", "a command"),
    ("$ ", "a command"),
)
_ANCHORED_ONLY = frozenset({"- ", "* "})
_MARKUP_OPENER = re.compile(r"<[A-Za-z_/!?]")


def _bare_angle_bracket(raw_text: str) -> bool:
    """Whether ``raw_text`` carries a ``<`` outside any code span - real HTML in running prose."""
    return _MARKUP_OPENER.search(_CODE_SPAN.sub("", raw_text)) is not None


_ANGLE_QUOTED = 3
_ANGLE_SPAN = 40


def angle_markup(raw_text: str) -> list[str]:
    """The distinct markup fragments ``_bare_angle_bracket`` found in ``raw_text``, in order."""
    outside = _CODE_SPAN.sub("", raw_text)
    quoted: list[str] = []
    for opener in _MARKUP_OPENER.finditer(outside):
        close = outside.find(">", opener.start())
        end = close + 1 if 0 <= close - opener.start() < _ANGLE_SPAN else opener.start() + 20
        fragment = outside[opener.start() : end]
        if fragment not in quoted:
            quoted.append(fragment)
        if len(quoted) == _ANGLE_QUOTED:
            break
    return quoted


_BRACKETED_LIST = re.compile(r"\s*\[([^\[\]]*)\]")


def _strip_echoed_fact_ids(text: str, fact_ids: Any) -> str | None:
    """``text`` with a bracketed echo of the unit's own ``fact_ids`` removed, or ``None``."""
    ids = {str(fact_id) for fact_id in fact_ids if isinstance(fact_id, str)}
    if not ids:
        return None

    def _drop(match: re.Match[str]) -> str:
        items = [item.strip() for item in match.group(1).split(",")]
        return "" if items and all(item in ids for item in items) else match.group(0)

    stripped = _BRACKETED_LIST.sub(_drop, text)
    return stripped if stripped != text else None


_OBJECTIVES: dict[str, tuple[str, str]] = {
    "opening": (
        "Two to four sentences that state what the product is and does, as its own actions "
        "('it reads ...', 'it writes ...', 'it converts ...'), from the accepted facts alone: the "
        "formats, capabilities and runtime they carry, and the problem it solves only where a "
        "fact states it. State no audience, use case or benefit - not who uses it, what it is "
        "used for, what it is suitable for, or what it spares the reader ('developers use it "
        "to ...', 'enables developers to ...', 'ideal for ...', 'used by ...', 'without "
        "requiring a license') - unless an accepted fact, or an inherited unit among them, says "
        "so in those words. A format fact's own `direction` field says whether the product reads "
        "that extension as input or writes it as output; when the opening names a format, state "
        "exactly that direction, never the opposite and never a direction the fact does not "
        "carry.",
        "one unit of two to four sentences",
    ),
    "key_capabilities": (
        "One sentence per core capability that adds concrete visitor detail beyond its title.",
        "one unit per capability, one sentence each",
    ),
    "quick_start": (
        "One lead-in sentence per minimal example the renderer shows next, each about the "
        "example its own slot's `renders` prints directly beneath it - what that code does and "
        "why a visitor runs it first - and never about the other slot's example.",
        "one unit of one sentence per example",
    ),
    "additional_examples": (
        "A short preview naming the workflows, then one meaningful task name per example.",
        "one preview unit of one or two sentences, then one unit of at most eight words per "
        "example",
    ),
    "api_reference": (
        "One or two intro sentences naming the real entry-point classes and how they relate "
        "(never a count, which the renderer states), then one evidence-backed sentence per "
        "hub API a visitor starts from.",
        "one intro unit of one or two sentences, then one unit per hub, one sentence each",
    ),
    "documentation_resources": (
        "One sentence per verified target on what it covers, in the reader's terms; never a "
        "count of types or members, which the renderer states from the facts.",
        "one unit per link, one sentence each",
    ),
    "scope_limitations": (
        "One honest scope statement, then one sentence per material limitation.",
        "one scope unit, then one unit per limitation, one sentence each",
    ),
    "development_testing": (
        "Two to four sentences on the toolchain and requirements to build and test from the "
        "repository's own assets (for example, the runtime/JDK version and the build tool). "
        "Where the objective names inherited units this section must carry, state their "
        "substance in your own words - where the test suites live and what they assert, the "
        "rules a contributor must follow, and never describe what a placed command accomplishes - "
        "compiling, testing, packaging, generating docs - since the renderer prints that command "
        "verbatim right after this unit, and a sentence that says what it does duplicates it in "
        "substance even when no word of the command itself is repeated; never a file count or a "
        "release statement, which the renderer states from the facts.",
        "one unit of two to four sentences",
    ),
    "enterprise_relationship": (
        "At most one sentence on what the commercial product adds beyond this package, only "
        "from the accepted facts (the existing README's own statements). The renderer prints a "
        "sentence naming the Enterprise Edition directly before this one, so refer back to it "
        "as 'it' or 'that product'; never write an edition or version label for it, "
        "the proper name included, since the renderer prints the only permitted one; "
        "empty when no fact says.",
        "one unit of at most one sentence",
    ),
}


def slots_clause(slots: Iterable[str]) -> str:
    """The sentence of a section_authoring objective that names the slots a call fills."""
    return f"Slots to fill, each exactly once: {', '.join(slots)}."


@dataclass(frozen=True)
class SectionTask:
    """Everything one authoring call needs and everything its guard checks."""

    section_id: str
    packet: dict[str, Any]
    accepted_ids: frozenset[str]
    slots: tuple[str, ...]
    key: str = ""
    slot_facts: Mapping[str, frozenset[str]] = field(default_factory=dict)
    slot_titles: Mapping[str, str] = field(default_factory=dict)
    slot_render_lines: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    must_carry: frozenset[str] = frozenset()
    must_carry_text: Mapping[str, str] = field(default_factory=dict)
    owed_lists: frozenset[str] = frozenset()

    @property
    def label(self) -> str:
        return self.key or self.section_id

    @property
    def is_batch(self) -> bool:
        return bool(self.key) and self.key != self.section_id


def _cited(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        found: list[str] = []
        for key, value in payload.items():
            if key == "fact_ids" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                found.extend(_cited(value))
        return found
    if isinstance(payload, list):
        return [item for element in payload for item in _cited(element)]
    return []


def _placed_units(dispositions: dict[str, Any], section: str) -> list[str]:
    return [
        entry["unit_id"]
        for entry in dispositions.get("dispositions", [])
        if entry.get("destination_section") == section
        and entry.get("disposition") in {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE"}
    ]


_CARRIABLE_SUFFIXES = (".paragraph", ".list")
_CARRY_SECTIONS = frozenset({"development_testing", "scope_limitations", "enterprise_relationship"})


def carried_units(dispositions: dict[str, Any], section: str, facts: FactsDocument) -> list[str]:
    """Inherited prose units reconciliation superseded INTO ``section``, which the section's own
    authored units must carry."""
    if section not in _CARRY_SECTIONS:
        return []
    texts = {fact.id: fact.value for fact in facts.facts if fact.kind == "inherited_unit"}
    kept = "\n\n".join(
        texts[entry["unit_id"]]
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
        and entry.get("destination_section") == section
        and entry.get("unit_id") in texts
        and str(entry.get("unit_id")).endswith(_CARRIABLE_SUFFIXES)
    )
    return [
        entry["unit_id"]
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") == "SUPERSEDE_REDUNDANT"
        and entry.get("destination_section") == section
        and entry.get("unit_id") in texts
        and str(entry.get("unit_id")).endswith(_CARRIABLE_SUFFIXES)
        and not (kept and states_all(kept, texts[entry["unit_id"]]))
    ]


_VERBATIM_PRESERVED_DISPOSITIONS = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})


def preserved_section_text(
    dispositions: Mapping[str, Any], facts: FactsDocument, section: str
) -> str:
    """The inherited prose reconciliation dispositioned straight into ``section`` -- the text the
    renderer prints verbatim right beside that section's own freshly authored units. Empty when
    no such unit exists, which is the common case outside a duplicate-preserved defect.

    Only VERIFIED_PRESERVE/VERIFIED_MOVE qualify (never VERIFIED_REWRITE, whose rendered text is
    the MODEL's own corrected rewrite, not the raw inherited text this reads) -- confirmed live
    the hard way (aspose-slides-foss/Aspose.Slides-FOSS-for-Python, run 41162835931; aspose-
    email-foss/Aspose.Email-FOSS-for-Cpp, run 41162828042): first using ``_placed_units``'s
    wider set (which also admits VERIFIED_REWRITE) spuriously rejected every "key_capabilities"
    unit in both runs, because inherited_unit:010.list there is VERIFIED_REWRITE -- its RAW,
    pre-rewrite text is a long enumeration, and every capability's own authored sentence,
    elaborating on one item of it, trivially "states" something already in that raw enumeration,
    though the text actually rendered (the model's rewritten list) is never compared at all.
    Narrowed to the same two dispositions placement.py's own ``_RENDERED_ELSEWHERE``-adjacent
    ``KEPT_DISPOSITIONS`` already treats as "renders verbatim, unchanged" -- the only two for
    which the raw inherited text IS what the renderer actually prints.

    Measured live (aspose-email-foss/Aspose.Email-FOSS-for-Cpp, run 41142584634): the same
    defect this module already caught for "opening" (``preserved_opening_text``, below) recurs
    in "api_reference" -- inherited_unit:043.paragraph is VERIFIED_PRESERVE into api_reference,
    and S6's own "intro" unit there cites it and restates its substance nearly verbatim, so the
    renderer prints it twice: once as the preserved paragraph, once as the authored intro. The
    check was hard-coded to "opening" alone; this generalizes it to any section.
    """
    texts = {fact.id: fact.value for fact in facts.facts if fact.kind == "inherited_unit"}
    return "\n\n".join(
        texts[entry["unit_id"]]
        for entry in dispositions.get("dispositions", [])
        if entry.get("destination_section") == section
        and entry.get("disposition") in _VERBATIM_PRESERVED_DISPOSITIONS
        and entry.get("unit_id") in texts
        and str(entry.get("unit_id")).endswith(_CARRIABLE_SUFFIXES)
    )


def preserved_opening_text(dispositions: Mapping[str, Any], facts: FactsDocument) -> str:
    """The inherited prose reconciliation dispositioned straight into "opening" -- the text the
    renderer prints verbatim right beside this section's own freshly authored unit. Empty when
    no such unit exists, which is the common case outside the known duplicate-opening defect."""
    return preserved_section_text(dispositions, facts, "opening")


def carried_substance(must_carry: Iterable[str], facts: FactsDocument) -> dict[str, str]:
    """The inherited text of each must-carry unit, keyed by its ID, in one line each."""
    wanted = set(must_carry)
    return {
        fact.id: " ".join(fact.value.split())
        for fact in facts.facts
        if fact.id in wanted and fact.value.strip()
    }


def capability_titles(plan: dict[str, Any]) -> dict[str, str]:
    """The title the plan gave each capability slot: the subject that slot's unit is about."""
    return {
        f"capability:{index}": title
        for index, item in enumerate(plan.get("core_capabilities", []), start=1)
        if (title := str(item.get("title", "")).strip())
    }


def slot_records(
    slots: Sequence[str],
    slot_facts: Mapping[str, frozenset[str]],
    titles: Mapping[str, str],
    renders: Mapping[str, str] = MappingProxyType({}),
) -> list[dict[str, Any]]:
    """Each slot as the author is shown it."""
    records: list[dict[str, Any]] = []
    for slot in slots:
        record: dict[str, Any] = {"slot": slot}
        if titles.get(slot):
            record["title"] = titles[slot]
        if slot_facts.get(slot):
            record["fact_ids"] = sorted(slot_facts[slot])
        if renders.get(slot):
            record["renders"] = renders[slot]
        records.append(record)
    return records


def slot_rendering(
    section: str,
    slots: Sequence[str],
    facts: FactsDocument,
    dispositions: dict[str, Any],
    slot_facts: Mapping[str, frozenset[str]] = MappingProxyType({}),
) -> dict[str, str]:
    """What the renderer prints around a slot's unit, verbatim, for the slots that have such a
    neighbour."""
    by_id = {fact.id: fact for fact in facts.facts}
    rendered: dict[str, str] = {}
    if section == "documentation_resources":
        for slot in slots:
            target = by_id.get(slot.removeprefix("link:"))
            if slot.startswith("link:") and target is not None:
                rendered[slot] = (
                    f"- **[{link_text(target)}]({target.value})** - before your sentence"
                )
    elif section == "quick_start":
        for slot in slots:
            bound = sorted(slot_facts.get(slot, frozenset()))
            example = by_id.get(bound[0]) if bound else None
            if example is not None:
                code = " ".join(example.value.split())
                rendered[slot] = f"as a fenced code block after your sentence: {code}"
    elif section == "development_testing":
        blocks = _development_testing_blocks(dispositions, by_id)
        if blocks and slots:
            joined = "; ".join(" ".join(block.split()) for block in blocks)
            rendered[slots[0]] = f"as fenced blocks after your sentence: {joined}"
    return rendered


def _development_testing_blocks(
    dispositions: dict[str, Any], by_id: Mapping[str, Fact]
) -> list[str]:
    """The raw text of every placed ``development_testing`` command block, in disposition order."""
    return [
        by_id[unit_id].value
        for unit_id in _placed_units(dispositions, "development_testing")
        if unit_id.endswith(".code_block") and unit_id in by_id
    ]


_FENCE_LINE = re.compile(r"^```.*$")
_TRAILING_COMMENT = re.compile(r"\s+#.*$")


def command_lines(blocks: Iterable[str]) -> tuple[str, ...]:
    """Every non-empty, non-fence command inside ``blocks``, one per source line."""
    lines: list[str] = []
    for block in blocks:
        for raw_line in block.splitlines():
            line = _TRAILING_COMMENT.sub("", " ".join(raw_line.split())).strip()
            if not line or _FENCE_LINE.match(line) or line.startswith("#"):
                continue
            lines.append(line)
    return tuple(dict.fromkeys(lines))


def title_terms(title: str, facts: FactsDocument) -> set[str]:
    """The concrete things a capability title names: identifiers, and this repository's own
    format names."""
    terms = identifier_tokens(title)
    formats = {fact.value.lstrip(".").lower(): fact.value for fact in facts.by_kind("format")}
    for word in _TITLE_WORD.findall(title):
        recorded = formats.get(word.lstrip(".").lower())
        if recorded:
            terms.add(recorded)
    return terms


_SUPPORTING_FACTS_NAMED = 3


def supporting_fact_ids(
    term: str, facts: FactsDocument, limit: int = _SUPPORTING_FACTS_NAMED
) -> list[str]:
    """A few SUPPORTED fact IDs whose own value literally carries ``term``, in document order."""
    needle = term.lstrip(".").lower()
    if not needle:
        return []
    return sorted(
        fact.id
        for fact in facts.facts
        if fact.polarity == "SUPPORTED" and needle in fact.value.lower()
    )[:limit]


def slot_fact_sets(section: str, plan: dict[str, Any]) -> dict[str, frozenset[str]]:
    """The fact set the plan assigned to each slot of the section that has one."""
    bound: dict[str, frozenset[str]] = {}
    if section == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            bound[f"capability:{index}"] = frozenset(item.get("fact_ids", []))
    elif section == "quick_start":
        quick = plan.get("quick_start_example_id")
        if quick:
            bound["lead_in"] = frozenset({quick})
        second = plan.get("second_quick_start_example_id")
        if second:
            bound["lead_in:2"] = frozenset({second})
    elif section == "additional_examples":
        for example in plan.get("additional_example_ids", []):
            bound[f"workflow:{example}"] = frozenset({example})
    elif section == "api_reference":
        for hub in plan.get("api_hubs", []):
            symbol = hub.get("symbol_fact_id", "")
            bound[f"hub:{symbol}"] = frozenset({symbol, *hub.get("fact_ids", [])})
    elif section == "documentation_resources":
        for link in plan.get("links", []):
            if link.get("section_id") == section:
                target = link.get("link_fact_id", "")
                bound[f"link:{target}"] = frozenset({target})
    elif section == "scope_limitations":
        for index, item in enumerate(plan.get("material_limitations", []), start=1):
            bound[f"limitation:{index}"] = frozenset(
                [*item.get("fact_ids", []), *item.get("unit_ids", [])]
            )
    return bound


def section_selections(
    section: str,
    plan: dict[str, Any],
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    facts: FactsDocument,
) -> tuple[list[str], tuple[str, ...]]:
    """The fact IDs a section may cite and the slots it must fill, from the plan."""
    ids: list[str] = [fact.id for fact in facts.facts if fact.kind in {"identity", "package"}]
    slots: list[str] = []
    if section == "opening":
        for key in ("product_summary", "audience", "problems_solved"):
            ids.extend(_cited(investigation.get(key)))
        ids.extend(_cited(plan.get("core_capabilities")))
        ids.extend(fact.id for fact in facts.by_kind("format"))
        slots = ["opening"]
    elif section == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            ids.extend(item.get("fact_ids", []))
            slots.append(f"capability:{index}")
    elif section == "quick_start":
        ids.append(plan.get("quick_start_example_id", ""))
        slots = ["lead_in"]
        second = plan.get("second_quick_start_example_id")
        if second:
            ids.append(second)
            slots.append("lead_in:2")
    elif section == "additional_examples":
        additional = plan.get("additional_example_ids", [])
        ids.extend(additional)
        slots = ["preview", *(f"workflow:{example}" for example in additional)]
    elif section == "api_reference":
        slots = ["intro"]
        for hub in plan.get("api_hubs", []):
            ids.append(hub.get("symbol_fact_id", ""))
            ids.extend(hub.get("fact_ids", []))
            slots.append(f"hub:{hub.get('symbol_fact_id', '')}")
    elif section == "documentation_resources":
        for link in plan.get("links", []):
            if link.get("section_id") == section:
                ids.append(link.get("link_fact_id", ""))
                slots.append(f"link:{link.get('link_fact_id', '')}")
    elif section == "scope_limitations":
        slots = ["scope"]
        material = plan.get("material_limitations", [])
        for item in material:
            ids.extend(item.get("fact_ids", []))
            ids.extend(item.get("unit_ids", []))
        found = investigation.get("limitations") or []
        count = max(len(material), len(found) if isinstance(found, list) else 0)
        slots.extend(f"limitation:{index}" for index in range(1, count + 1))
        ids.extend(_cited(investigation.get("limitations")))
        ids.extend(carried_units(dispositions, section, facts))
    elif section == "development_testing":
        ids.extend(fact.id for fact in facts.by_kind("build_test_asset"))
        ids.extend(carried_units(dispositions, section, facts))
        slots = ["summary"]
    elif section == "enterprise_relationship":
        slots = ["context"]
        ids.extend(carried_units(dispositions, section, facts))
    ids.extend(_placed_units(dispositions, section))
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    ordered = [fact_id for fact_id in dict.fromkeys(ids) if fact_id in supported]
    return ordered, tuple(slots)


def undocumented_types(facts: FactsDocument) -> list[Fact]:
    """SUPPORTED public types (classes and enums) whose source carries no docstring, in value
    order."""
    return sorted(
        (
            fact
            for fact in facts.by_kind("public_symbol")
            if fact.polarity == "SUPPORTED"
            and (fact.attributes or {}).get("symbol_kind") in {"class", "enum"}
            and not (fact.attributes or {}).get("docstring")
        ),
        key=lambda fact: fact.value,
    )


def _type_batches(
    entry: RegistryEntry, facts: FactsDocument, do_not_claim: list[dict[str, str]]
) -> list[SectionTask]:
    """One bounded task per batch of undocumented types."""
    types = undocumented_types(facts)
    name = product_name(entry)
    tasks: list[SectionTask] = []
    for index in range(0, len(types), _TYPE_BATCH):
        batch = types[index : index + _TYPE_BATCH]
        ids = [fact.id for fact in batch]
        slots = tuple(f"type:{fact.id}" for fact in batch)
        slot_facts = {f"type:{fact.id}": frozenset({fact.id}) for fact in batch}
        accepted = [
            {
                "id": fact.id,
                "kind": fact.kind,
                "value": fact.value,
                **(
                    {"signature": (fact.attributes or {})["signature"]}
                    if (fact.attributes or {}).get("signature")
                    else {}
                ),
            }
            for fact in batch
        ]
        spellings = section_spellings(ids, facts)
        packet = {
            "repository": entry.repository,
            "product_name": name,
            "mode": "author",
            "section_id": "api_reference",
            "objective": (
                f"{_TYPE_OBJECTIVE} {slots_clause(slots)} "
                f"Identifiers the prose may spell, exactly as written: {', '.join(spellings)}; "
                "any other API name, member, attribute, or parameter is rejected."
            ),
            "slots": slot_records(slots, slot_facts, {}),
            "accepted_facts": accepted,
            "do_not_claim": do_not_claim,
            "length_budget": "one unit per type, one sentence each",
            "rendered_document": "",
            "existing_units": [],
        }
        number = index // _TYPE_BATCH + 1
        tasks.append(
            SectionTask(
                "api_reference",
                packet,
                frozenset(ids),
                slots,
                key=f"api_reference#types-{number}",
                slot_facts=slot_facts,
            )
        )
    return tasks


def authoring_schema(manifest: LoadedManifest, task: SectionTask) -> dict[str, Any]:
    """The authoring schema specialised for one task: its section and exactly its slots."""
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    if not task.slots:
        return schema
    units = schema["properties"]["units"]
    units["minItems"] = len(task.slots)
    units["maxItems"] = len(task.slots)
    item = units["items"]

    def _fact_id_items(slot: str) -> dict[str, Any]:
        allowed = citable(task, slot)
        if allowed:
            return {"type": "string", "enum": allowed}
        return {"type": "string", "maxLength": 0}

    units["prefixItems"] = [
        {
            **item,
            "properties": {
                **item["properties"],
                "section": {"const": task.section_id},
                "slot": {"const": slot},
                "fact_ids": {
                    **item["properties"]["fact_ids"],
                    "items": _fact_id_items(slot),
                },
            },
        }
        for slot in task.slots
    ]
    del units["items"]
    return schema


def citable(task: SectionTask, slot: str) -> list[str]:
    """The fact IDs a slot's unit may cite: the set the plan assigned it, or the section's own
    when the plan assigned none, plus the neutral facts every unit may rest on."""
    bound = task.slot_facts.get(slot)
    allowed = set(task.accepted_ids if bound is None else bound)
    allowed.update(i for i in task.accepted_ids if i.startswith(_NEUTRAL_KINDS))
    return sorted(allowed)


_NEUTRAL_KINDS = ("identity:", "package:")


def owed_list_units(
    entry: RegistryEntry,
    facts: FactsDocument,
    dispositions: dict[str, Any],
    plan: dict[str, Any],
    section: str,
    slot_facts: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    """The list units kept as written that placement drops from ``section`` as covered by its own
    content, in a section whose slots the plan does not bind."""
    if section not in OWED_SECTIONS or slot_facts:
        return frozenset()
    kept = {
        str(item.get("unit_id"))
        for item in dispositions.get("dispositions", [])
        if item.get("destination_section") == section
        and item.get("disposition") in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
        and str(item.get("unit_id", "")).endswith(".list")
    }
    if not kept:
        return frozenset()
    return frozenset(
        decision.unit_id
        for decision in placements(plan, dispositions, facts, entry.ecosystem)
        if decision.unit_id in kept
        and decision.destination == section
        and decision.outcome == "overlap"
    )


def authoring_tasks(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    plan: dict[str, Any],
) -> list[SectionTask]:
    """One task per included section the LLM authors, in shell order."""
    included = {item["section_id"] for item in plan.get("sections", []) if item.get("include")}
    name = product_name(entry)
    by_id = {fact.id: fact for fact in facts.facts}
    do_not_claim = bounded_records(
        facts,
        ["format", "install_command", "link_target", "example"],
        ("CONTRADICTED", "UNRESOLVED"),
    )
    tasks: list[SectionTask] = []
    for section in AUTHORED_SECTIONS:
        if section not in included:
            continue
        ids, slots = section_selections(section, plan, investigation, dispositions, facts)
        objective, budget = _OBJECTIVES[section]
        must_carry = frozenset(carried_units(dispositions, section, facts))
        accepted = [
            {
                "id": fact_id,
                "kind": by_id[fact_id].kind,
                "value": by_id[fact_id].value,
                **(
                    {"direction": direction}
                    if (direction := _fact_direction(fact_id)) is not None
                    else {}
                ),
            }
            for fact_id in ids
        ]
        spellings = section_spellings(ids, facts)
        slot_facts = slot_fact_sets(section, plan)
        titles = capability_titles(plan) if section == "key_capabilities" else {}
        renders = slot_rendering(section, slots, facts, dispositions, slot_facts)
        records = slot_records(slots, slot_facts, titles, renders)
        render_lines = (
            {slots[0]: command_lines(_development_testing_blocks(dispositions, by_id))}
            if section == "development_testing"
            and slots
            and _development_testing_blocks(dispositions, by_id)
            else {}
        )
        renders_rule = (
            "A slot's `renders` is what the renderer prints there from the same facts; write "
            "only what it does not already say, and never repeat its link, label, or command. "
            "It is shown so you do not repeat it, never as a source of spellings: an identifier "
            "that appears only there, such as a module inside a command, is not yours to write. "
            if any(record.get("renders") for record in records)
            else ""
        )
        bound_rule = (
            "Each slot below gives the subject its unit is about and the only facts that unit "
            "may cite; a unit describes its own slot, never another's. "
            if any(len(record) > 1 for record in records)
            else ""
        )
        title_rule = (
            "A slot's title is printed immediately before its unit, so the unit never restates "
            "it and never opens with the product name; it adds what the title does not say. "
            if any(record.get("title") for record in records)
            else ""
        )
        carry_rule = (
            "Inherited units this section must carry (state their substance in your units, or "
            f"list each in omitted with a reason): {', '.join(sorted(must_carry))}. "
            if must_carry
            else ""
        )
        owed = owed_list_units(entry, facts, dispositions, plan, section, slot_facts)
        kept_lists_owed = kept_lists(
            dispositions,
            section,
            set().union(*slot_facts.values()) | owed if slot_facts else owed,
            facts,
        )
        carry_rule += (
            "Lists kept as written, whose items your units may fold into plain words where they "
            "fit (cite the list in that unit); any item you leave out is printed as written "
            "after your units, so never spell an identifier you were not given just to cover an "
            "item: "
            + ", ".join(
                f"{unit} ({len(list_items(text))} items)" for unit, text in kept_lists_owed.items()
            )
            + ". "
            if kept_lists_owed
            else ""
        )
        if must_carry and section == "enterprise_relationship":
            carry_rule += (
                "Here the substance is what the commercial product adds: say it in this one "
                "sentence as 'it adds ...', without the product or edition name, a label for "
                "it, or its link, which the renderer prints in the sentence before yours. "
            )
        packet = {
            "repository": entry.repository,
            "product_name": name,
            "mode": "author",
            "section_id": section,
            "objective": (
                f"{objective} {slots_clause(slots)} "
                f"{bound_rule}{title_rule}{renders_rule}{carry_rule}"
                f"Identifiers the prose may spell, exactly as written: {', '.join(spellings)}; "
                "any other API name, member, attribute, or parameter is rejected."
            ),
            "slots": records,
            "accepted_facts": accepted,
            "do_not_claim": do_not_claim,
            "length_budget": budget,
            "rendered_document": "",
            "existing_units": [],
        }
        tasks.append(
            SectionTask(
                section,
                packet,
                frozenset(ids),
                slots,
                slot_facts=slot_facts,
                slot_titles=titles,
                slot_render_lines=render_lines,
                must_carry=must_carry,
                must_carry_text=carried_substance(must_carry, facts),
                owed_lists=owed,
            )
        )
        if section == "api_reference":
            tasks.extend(_type_batches(entry, facts, do_not_claim))
    return tasks


def verified_members(facts: FactsDocument) -> frozenset[str]:
    """Attribute names a SUPPORTED example calls or reads, from its syntax tree."""
    members: set[str] = set()
    for fact in facts.by_kind("example"):
        if fact.polarity != "SUPPORTED":
            continue
        try:
            tree = ast.parse(fact.value)
        except SyntaxError:
            continue
        members.update(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))
    return frozenset(members)


def surface_members(facts: FactsDocument) -> dict[str, frozenset[str]]:
    """Public methods per class, from the surface facts recorded as ``module.Class.method``."""
    members: dict[str, set[str]] = {}
    for fact in facts.by_kind("public_symbol"):
        detail = fact.evidence[0].detail or "" if fact.evidence else ""
        if fact.polarity != "SUPPORTED" or "; method;" not in detail:
            continue
        parts = fact.value.split(".")
        if len(parts) >= 3:
            members.setdefault(parts[-2], set()).add(parts[-1])
    return {name: frozenset(found) for name, found in members.items()}


def section_spellings(accepted_ids: list[str], facts: FactsDocument) -> list[str]:
    """The identifiers a section may spell, told to the job."""
    by_id = {fact.id: fact for fact in facts.facts}
    methods = surface_members(facts)
    spellings: list[str] = []
    class_methods: list[str] = []
    for fact_id in accepted_ids:
        fact = by_id.get(fact_id)
        if fact is None or fact.kind not in {"public_symbol", "import_path", "package", "format"}:
            continue
        spellings.append(fact.value)
        if fact.kind in {"public_symbol", "import_path"} and "." in fact.value:
            last = fact.value.rsplit(".", 1)[-1]
            spellings.append(last)
            class_methods.extend(f"{last}.{method}" for method in sorted(methods.get(last, ())))
    verified = sorted(verified_members(facts))
    listed = list(dict.fromkeys(spellings)) + list(dict.fromkeys(class_methods))[:_MEMBER_CAP]
    return listed + [f"member {name}" for name in verified[:_MEMBER_CAP]]


def identifier_allowed(
    token: str,
    allowed: frozenset[str],
    members: frozenset[str],
    methods: dict[str, frozenset[str]] | None = None,
) -> bool:
    """A token is allowed as a fact value, a call of one, a verified member, a public method
    (bare, or as Class.method), or Class.member for a member a verified example uses."""
    methods = methods or {}
    every_method = frozenset(name for found in methods.values() for name in found)
    bare = token[:-2] if token.endswith("()") else token
    if token in allowed or bare in allowed or bare in members or bare in every_method:
        return True
    if "." in bare:
        head, tail = bare.rsplit(".", 1)
        return head in allowed and (tail in members or tail in methods.get(head, frozenset()))
    return False


_SPELLABLE = re.compile(r"[A-Za-z_][\w.\-]*(?:\(\))?")
_NEAREST_LIMIT = 4
_NEAREST_RATIO = 0.8
_NEAREST_PREFIX_SHARE = 0.75
_NEAREST_MIN_PREFIX = 5


def nearest_accepted_identifiers(
    token: str, accepted: Iterable[str], limit: int = _NEAREST_LIMIT
) -> list[str]:
    """The few accepted spellings a rejected identifier most plausibly meant, best first."""
    bare = token[:-2] if token.endswith("()") else token
    lowered = bare.lower()
    if len(lowered) < _NEAREST_MIN_PREFIX:
        return []
    need = max(_NEAREST_MIN_PREFIX, int(_NEAREST_PREFIX_SHARE * len(lowered)))
    scored: list[tuple[float, str]] = []
    for candidate in set(accepted):
        if candidate in (bare, token) or not _SPELLABLE.fullmatch(candidate):
            continue
        base = candidate[:-2] if candidate.endswith("()") else candidate
        other = base.lower()
        if abs(len(other) - len(lowered)) > max(len(lowered), len(other)) * 0.6:
            continue
        shared = len(os.path.commonprefix([lowered, other]))
        matcher = difflib.SequenceMatcher(None, lowered, other)
        ratio = matcher.ratio() if shared >= 2 else 0.0
        if shared >= need or ratio >= _NEAREST_RATIO:
            scored.append((ratio, base))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    nearest: list[str] = []
    for _, spelling in scored:
        if spelling not in nearest:
            nearest.append(spelling)
        if len(nearest) == limit:
            break
    return nearest


def identifier_tokens(text: str) -> set[str]:
    """Tokens the renderer would have to wrap in a code span."""
    found: set[str] = set()
    for pattern in (_DOTTED, _SNAKE, _CAMEL, _CALL, _COORDINATE):
        found.update(match.group(0) for match in pattern.finditer(text))
    found.update(match.group(0) for match in _MODULE_PATH.finditer(_URL.sub(" ", text)))
    return {token for token in found if not (token.isupper() and token.isalnum())}


_FILE_SUFFIXES = frozenset(
    {"cs", "csproj", "sln", "md", "txt", "json", "yml", "yaml", "xml", "toml", "cfg", "ini", "lock"}
    | {"gradle", "kts", "java", "py", "js", "ts", "go", "rs", "cpp", "h", "hpp", "html", "css"}
    | {"sh", "mod", "sum", "pom", "dat", "csv"}
)
_BARE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DOTTED_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\Z")


def slash_alternatives(token: str) -> list[tuple[str, str]] | None:
    """The names a slash-joined shorthand stands for, each as ``(judged, shown)``; ``None`` when
    ``token`` is a path instead."""
    parts = token.split("/")
    if len(parts) < 2 or not all(parts) or not _DOTTED_NAME.match(parts[0]):
        return None
    namespace = parts[0].rsplit(".", 1)[0]
    names = [(parts[0], parts[0])]
    for part in parts[1:]:
        if _BARE_NAME.match(part):
            names.append((f"{namespace}.{part}", token))
        elif _DOTTED_NAME.match(part):
            names.append((part, part))
        else:
            return None
    if any(judged.rsplit(".", 1)[-1].lower() in _FILE_SUFFIXES for judged, _ in names):
        return None
    return names


def restore_case_variants(text: str, strays: Iterable[str], pool: Iterable[str]) -> str:
    """``text`` with each stray identifier that differs from exactly one accepted spelling only
    in letter case written as that spelling."""
    by_lower: dict[str, set[str]] = {}
    for spelling in pool:
        if _SPELLABLE.fullmatch(spelling):
            bare = spelling[:-2] if spelling.endswith("()") else spelling
            by_lower.setdefault(bare.lower(), set()).add(bare)
    for token in strays:
        bare = token[:-2] if token.endswith("()") else token
        if bare.rsplit(".", 1)[-1].lower() in _FILE_SUFFIXES:
            continue
        matches = by_lower.get(bare.lower(), set()) - {bare}
        if len(matches) == 1:
            (accepted,) = matches
            text = re.sub(rf"(?<![\w.]){re.escape(bare)}(?![\w])", accepted, text)
    return text


def stray_identifiers(tokens: Iterable[str], unaccepted: Callable[[str], bool]) -> list[str]:
    """The identifiers among ``tokens`` that ``unaccepted`` refuses, sorted, each once."""
    found: list[str] = []
    for token in sorted(filter(unaccepted, tokens)):
        names = slash_alternatives(token)
        bad = [shown for judged, shown in names if unaccepted(judged)] if names else []
        found.extend(bad if names and len(bad) < len(names) else [token])
    return sorted(dict.fromkeys(found))


def mask_allowed_values(text: str, allowed: Iterable[str]) -> str:
    """``text`` with each allowed single-token composite value it spells verbatim blanked out."""
    for value in sorted(
        {v for v in allowed if len(v) >= 3 and "://" not in v and _COMPOSITE_VALUE.fullmatch(v)},
        key=len,
        reverse=True,
    ):
        if value in text:
            text = re.sub(rf"(?<![\w/.-]){re.escape(value)}(?![\w/-]|\.\w)", " ", text)
    return text


def command_block_tokens(text: str) -> set[str]:
    """Identifiers spelled inside ``text``'s shell-command fences."""
    found: set[str] = set()
    for match in _FENCED_BLOCK.finditer(text):
        if match.group(1).strip().lower() in _COMMAND_FENCES:
            found.update(identifier_tokens(match.group(2)))
    return found


def command_fact_tokens(fact: Fact) -> set[str]:
    """Identifiers spelled by the command a fact records: a file or target its words name."""
    attributes = fact.attributes or {}
    if fact.kind != "install_command" and not (
        fact.kind == "build_test_asset" and str(attributes.get("role", "")).endswith("command")
    ):
        return set()
    found: set[str] = set()
    for line in fact.value.splitlines():
        for word in line.split():
            word = word.strip("\"'(),;")
            if word and not word.startswith("-") and "://" not in word:
                found.update(identifier_tokens(word))
    return found


def source_prose(text: str) -> str:
    """The running prose of a source unit: no fenced block, code span, link target, URL, or tag."""
    for pattern in _NOT_PROSE:
        text = pattern.sub(" ", text)
    return text


_IRREGULAR_PROPER_NOUNS = frozenset({"Node.js"})


def proper_noun(token: str) -> bool:
    """A name, not a path: every dotted segment capitalised, no underscore, no call parentheses."""
    return token in _IRREGULAR_PROPER_NOUNS or (
        "_" not in token
        and "(" not in token
        and all(part[:1].isupper() for part in token.split("."))
    )


def prose_nouns(facts: FactsDocument, name: str) -> frozenset[str]:
    """Proper nouns this document may spell in plain text, beyond the identifiers it may cite."""
    candidates = {part for token in name.split(" ") for part in token.split(".") if part}
    for fact in facts.by_kind("inherited_unit"):
        if fact.polarity == "SUPPORTED":
            candidates.update(_inherited_unit_tokens(fact.value))
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    return frozenset(
        token
        for token in candidates
        if proper_noun(token) and not identifier_allowed(token, allowed, members, methods)
    )


_SIBLING_SHORTHAND = re.compile(
    r"`?([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*)\.[A-Za-z_]\w*(?:\(\))?`?\s*/\s*`?\.([A-Za-z_]\w*)"
)


def _inherited_unit_tokens(value: str) -> set[str]:
    """Identifier-shaped tokens an inherited unit's own value spells."""
    found = set(identifier_tokens(source_prose(value)))
    without_fences = _NOT_PROSE[0].sub(" ", value)
    for span in _CODE_SPAN.finditer(without_fences):
        found.update(identifier_tokens(span.group(1)))
    found.update(f"{head}.{second}" for head, second in _SIBLING_SHORTHAND.findall(without_fences))
    return found


def cited_inherited_identifiers(facts: FactsDocument, fact_ids: Iterable[str]) -> frozenset[str]:
    """Identifiers spelled verbatim inside a SUPPORTED ``inherited_unit`` fact named in
    ``fact_ids``."""
    ids = set(fact_ids)
    if not ids:
        return frozenset()
    return frozenset(
        token
        for fact in facts.by_kind("inherited_unit")
        if fact.polarity == "SUPPORTED" and fact.id in ids
        for token in _inherited_unit_tokens(fact.value)
    )


def _without_repository_paths(text: str, facts: FactsDocument) -> str:
    """``text`` with every repository path the extractor verified against the pinned tree blanked
    out."""
    paths = {
        name
        for fact in facts.by_kind("inherited_unit")
        if fact.polarity == "SUPPORTED"
        for name in (fact.attributes or {}).get(REPOSITORY_FILES_ATTRIBUTE, "").split(",")
        if "/" in name
    }
    for path in sorted(paths, key=len, reverse=True):
        text = re.sub(rf"(?<![\w/.-]){re.escape(path)}(?![\w/-])", " ", text)
    return text


def inherited_unit_named_symbols(facts: FactsDocument, value: str) -> frozenset[str]:
    """SUPPORTED ``public_symbol``/``import_path`` fact IDs spelled verbatim inside an inherited
    unit's own text."""
    tokens = _inherited_unit_tokens(value)
    if not tokens:
        return frozenset()
    named_outside_paths = _inherited_unit_tokens(_without_repository_paths(value, facts))
    tokens = {token for token in tokens if "/" in token or token in named_outside_paths}
    return frozenset(
        fact.id
        for fact in facts.facts
        if fact.polarity == "SUPPORTED"
        and fact.kind in {"public_symbol", "import_path"}
        and fact.value in tokens
    )


def canonical_abbreviations(facts: FactsDocument) -> dict[str, str]:
    """Lowercase spelling to canonical form, for every abbreviation this document owns."""
    return canonical_forms(fact.value for fact in facts.by_kind("format"))


def forbidden_text_pattern(extra: Sequence[str] = ()) -> str:
    """A regular expression for a unit's text: none of the fragments a unit may not contain."""
    anywhere = [fragment for fragment, _ in _FORBIDDEN if fragment not in _ANCHORED_ONLY]
    anywhere += list(extra)
    anywhere_alternation = "|".join(re.escape(fragment) for fragment in anywhere)
    anchored_alternation = "|".join(re.escape(fragment) for fragment in _ANCHORED_ONLY)
    return f"^(?!(?:{anchored_alternation}))(?!(?:.|\\n)*(?:{anywhere_alternation}))(?:.|\\n)*$"


def allowed_identifiers(facts: FactsDocument, name: str) -> frozenset[str]:
    """Identifiers the prose may spell: every SUPPORTED fact value, each dotted suffix of a
    symbol or import path, its call form, the identifiers an executed example or a shell-command
    fence spells inside itself, and the product name's tokens."""
    allowed: set[str] = set(product_name_tokens(name))
    allowed.update(REGISTRY_NAMES.values())
    allowed.update(host_names(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED"))
    for fact in facts.facts:
        if fact.polarity != "SUPPORTED":
            continue
        allowed.add(fact.value)
        if fact.kind == "example":
            allowed.update(identifier_tokens(fact.value))
        allowed.update(command_block_tokens(fact.value))
        allowed.update(
            token for token in command_fact_tokens(fact) if not spells_the_product(token, name)
        )
        allowed.update(
            file_name
            for file_name in (fact.attributes or {}).get(REPOSITORY_FILES_ATTRIBUTE, "").split(",")
            if file_name and not spells_the_product(file_name, name)
        )
        if fact.kind in {"public_symbol", "import_path"}:
            spellings = [fact.value]
            attributes = fact.attributes or {}
            spellings.extend(
                path.strip()
                for key in ("defined_at", "public_paths")
                for path in attributes.get(key, "").split(",")
                if path.strip()
            )
            for spelling in spellings:
                parts = spelling.split(".")
                for start in range(len(parts)):
                    allowed.add(".".join(parts[start:]))
                allowed.add(parts[-1] + "()")
                allowed.add(spelling + "()")
    return frozenset(allowed)


def merge_repeated_slots(output: dict[str, Any]) -> list[str]:
    """Fold units that repeat one slot into a single unit, in place."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    folded: list[str] = []
    for unit in output.get("units", []):
        key = (str(unit.get("section", "")), str(unit.get("slot", "")))
        first = merged.get(key)
        if first is None:
            merged[key] = unit
            continue
        first["text"] = f"{first.get('text', '')} {unit.get('text', '')}".strip()
        first["fact_ids"] = list(
            dict.fromkeys([*first.get("fact_ids", []), *unit.get("fact_ids", [])])
        )
        if key[1] not in folded:
            folded.append(key[1])
    output["units"] = list(merged.values())
    return folded


_PROSE_EXTENSION = re.compile(r"(?<![\w.])\.[A-Za-z]{2,5}\b")
_PROSE_WORD = re.compile(r"(?<![\w.])[A-Za-z]+(?!\w|\.[A-Za-z_])")
_PROSE_INPUT_WORDS = frozenset(
    {
        "read",
        "reads",
        "reading",
        "load",
        "loads",
        "loading",
        "open",
        "opens",
        "opening",
        "import",
        "imports",
        "importing",
        "parse",
        "parses",
        "parsing",
    }
)
_PROSE_OUTPUT_WORDS = frozenset(
    {
        "write",
        "writes",
        "writing",
        "save",
        "saves",
        "saving",
        "export",
        "exports",
        "exporting",
        "create",
        "creates",
        "creating",
        "produce",
        "produces",
        "producing",
        "generate",
        "generates",
        "generating",
        "emit",
        "emits",
        "emitting",
    }
)


def _prose_direction(text: str) -> str | None:
    """ "input", "output", or None when the text names both or neither direction."""
    words = {word.lower() for word in _PROSE_WORD.findall(text)}
    is_input = bool(words & _PROSE_INPUT_WORDS)
    is_output = bool(words & _PROSE_OUTPUT_WORDS)
    if is_input == is_output:
        return None
    return "input" if is_input else "output"


def _fact_direction(fact_id: str) -> str | None:
    """The "input"/"output" half of a ``format:<direction>.<extension>`` fact ID's own naming
    convention."""
    if not fact_id.startswith("format:"):
        return None
    direction = fact_id.split(":", 1)[-1].split(".", 1)[0]
    return direction if direction in {"input", "output"} else None


def _example_format_claims(facts: FactsDocument, ordinal: str) -> dict[str, frozenset[str]]:
    """The (direction -> extensions) one example already claims for itself, read straight from
    the evidence an extraction stage already recorded for it."""
    marker = f"example {ordinal}:"
    by_direction: dict[str, set[str]] = {"input": set(), "output": set()}
    for fact in facts.by_kind("format"):
        direction = _fact_direction(fact.id)
        if direction is None:
            continue
        if any(marker in (item.detail or "") for item in fact.evidence):
            by_direction[direction].add(fact.value.lower())
    return {direction: frozenset(values) for direction, values in by_direction.items()}


def unit_example_action_mismatches(unit: Mapping[str, Any], facts: FactsDocument) -> list[str]:
    """A unit's prose about a specific cited example, checked against that example's own recorded
    format claims."""
    direction = _prose_direction(str(unit.get("text", "")))
    if direction is None:
        return []
    opposite = "output" if direction == "input" else "input"
    extensions = {ext.lower() for ext in _PROSE_EXTENSION.findall(str(unit.get("text", "")))}
    if not extensions:
        return []
    errors: list[str] = []
    for fact_id in unit.get("fact_ids", []):
        if not str(fact_id).startswith("example:"):
            continue
        digits = str(fact_id).split(":", 1)[-1]
        if not digits.isdigit():
            continue
        ordinal = str(int(digits))
        claims = _example_format_claims(facts, ordinal)
        for extension in sorted(extensions & claims[opposite] - claims[direction]):
            errors.append(
                f"names {extension} as {direction}, but example {ordinal}'s own recorded "
                f"format claims say {opposite}"
            )
    return errors


_MEMBER_NAME = re.compile(
    r"\b(?:[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+|I[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)*)\b"
)


def restates_own_title(text: str, title: str, facts: FactsDocument) -> bool:
    """Whether ``text`` says nothing its slot ``title`` does not."""
    if not re.search(rf"(?<![A-Za-z0-9]){re.escape(title.lower())}(?![A-Za-z0-9])", text.lower()):
        return False
    added = title_terms(text, facts) | set(_MEMBER_NAME.findall(text))
    return not (added - title_terms(title, facts) - set(_MEMBER_NAME.findall(title)))


def restated_command_lines(text: str, lines: Iterable[str]) -> list[str]:
    """The placed command lines ``text`` spells out verbatim (case-insensitive), in the order the
    lines are given."""
    lowered = text.lower()
    return [line for line in lines if line.lower() in lowered]


def unit_checks(
    output: dict[str, Any],
    task: SectionTask,
    facts: FactsDocument,
    name: str,
    elsewhere_cited: Mapping[str, str] = MappingProxyType({}),
    dispositions: Mapping[str, Any] | None = None,
) -> list[str]:
    """Why the section's units may not be used, beyond schema and binding; empty when they hold."""
    errors: list[str] = []
    if dispositions is not None:
        preserved = preserved_section_text(dispositions, facts, task.section_id)
        if preserved:
            for unit in output.get("units", []):
                text = str(unit.get("text", ""))
                if text and (states_all(preserved, text) or states_all(text, preserved)):
                    errors.append(
                        f"unit {unit.get('slot')}: restates the inherited paragraph the "
                        f"renderer already preserves verbatim in this section; state only what "
                        "that paragraph does not already say"
                    )
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    nouns = prose_nouns(facts, name)
    merge_repeated_slots(output)
    expected = list(task.slots)
    output["units"] = [unit for unit in output.get("units", []) if unit.get("slot") in expected]
    slots_seen = [unit.get("slot") for unit in output.get("units", [])]
    if sorted(slots_seen) != sorted(expected):
        errors.append(
            f"units must fill exactly these slots once each: {', '.join(expected)}; "
            f"got {', '.join(str(slot) for slot in slots_seen)}"
        )
    for unit in output.get("units", []):
        text = str(unit.get("text", ""))
        if task.section_id == "enterprise_relationship" and "Enterprise Edition" in text:
            errors.append(
                f"unit {unit.get('slot')}: names the Enterprise Edition; the shell's closing "
                "sentence names it exactly once. Drop the name and any 'see ...' or 'these "
                "limitations don't apply to ...' clause and state only what the product adds, "
                "beginning 'It adds ...'"
            )
        for phrase in edition_substitutes(text):
            errors.append(
                f"unit {unit.get('slot')}: names the edition as {phrase!r}; Enterprise Edition is "
                "the only edition name and the shell prints it, so name no edition"
            )
    for unit in output.get("units", []):
        title = task.slot_titles.get(str(unit.get("slot")))
        text = str(unit.get("text", ""))
        if title and restates_own_title(text, title, facts):
            errors.append(
                f"unit {unit.get('slot')}: restates its own title {title!r}; the title is "
                "printed immediately before the unit, so its text adds what the title does "
                "not already say"
            )
    for unit in output.get("units", []):
        lines = task.slot_render_lines.get(str(unit.get("slot")))
        if not lines:
            continue
        restated = restated_command_lines(str(unit.get("text", "")), lines)
        if restated:
            many = len(restated) > 1
            errors.append(
                f"unit {unit.get('slot')}: restates {', '.join(repr(line) for line in restated)}, "
                f"{'commands' if many else 'a command'} the renderer already prints verbatim in a "
                "fenced block right after this unit; write only what the block does not already "
                f"say, never {'any command' if many else 'the command'} itself"
            )
    neutral = {fact.id for fact in facts.facts if fact.kind in {"identity", "package"}}
    for unit in output.get("units", []):
        bound = task.slot_facts.get(str(unit.get("slot")))
        if bound is None:
            continue
        outside = [i for i in unit.get("fact_ids", []) if i not in bound and i not in neutral]
        if outside:
            errors.append(
                f"unit {unit.get('slot')}: cites facts outside its slot's planned set "
                f"({', '.join(outside)}); a unit describes its own slot's facts, never "
                "another slot's"
            )
    values = {fact.id: fact.value for fact in facts.facts}
    common = " ".join([*(values[i] for i in sorted(neutral) if i in values), name]).lower()
    for unit in output.get("units", []):
        title = task.slot_titles.get(str(unit.get("slot")), "")
        if not title:
            continue
        cited = " ".join(values.get(i, "") for i in unit.get("fact_ids", [])).lower()
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
                f"unit {unit.get('slot')}: its title {title!r} names "
                f"{', '.join(unsupported)}, which the facts it cites do not carry ({suggestions}); "
                "cite one of the named facts that supports this slot's title, or the sentence "
                "belongs to another slot"
            )
    supporting = support_texts(task.accepted_ids, facts)
    recorded = " ".join(supporting)
    for unit in output.get("units", []):
        slot = unit.get("slot", "?")
        if unit.get("section") != task.section_id:
            errors.append(f"unit {slot}: section must be {task.section_id}")
        raw_text = str(unit.get("text", ""))
        text = raw_text
        if "`" in text and "```" not in text:
            text = text.replace("`", "")
            unit["text"] = text
        unstripped = _strip_echoed_fact_ids(text, unit.get("fact_ids", []))
        if unstripped is not None:
            text = unstripped
            unit["text"] = text
        canonicalised = canonicalise_name_variants(text, name)
        if canonicalised != text:
            text = canonicalised
            unit["text"] = text
        forbidden: list[str] = []
        meanings: set[str] = set()
        for marker, meaning in _FORBIDDEN:
            if meaning in meanings:
                continue
            if marker == "<":
                matched = _bare_angle_bracket(raw_text)
            else:
                matched = text.startswith(marker) if marker in _ANCHORED_ONLY else marker in text
            if matched:
                meanings.add(meaning)
                found = f"{meaning} ({marker.strip()!r})"
                if marker == "<":
                    found += f": {', '.join(angle_markup(raw_text))}"
                forbidden.append(found)
        if forbidden:
            errors.append(f"unit {slot}: text contains {', '.join(forbidden)}")
        unit_fact_ids = unit.get("fact_ids", [])
        cited_inherited = cited_inherited_identifiers(
            facts,
            unit_fact_ids
            if task.section_id == "scope_limitations"
            else [fact_id for fact_id in unit_fact_ids if fact_id in task.must_carry],
        )

        def unaccepted(token: str, cited: frozenset[str] = cited_inherited) -> bool:
            return (
                not identifier_allowed(token, allowed, members, methods)
                and token not in nouns
                and token not in cited
                and not (token.endswith(_EXCEPTION_SUFFIXES) and token in recorded)
            )

        strays = stray_identifiers(
            identifier_tokens(mask_allowed_values(text, allowed)), unaccepted
        )
        pool = allowed | members | frozenset(name for found in methods.values() for name in found)
        if strays:
            restored = restore_case_variants(text, strays, pool)
            if restored != text:
                text = restored
                unit["text"] = text
                strays = stray_identifiers(
                    identifier_tokens(mask_allowed_values(text, allowed)), unaccepted
                )
        if strays:
            shown = []
            for token in strays:
                near = nearest_accepted_identifiers(token, pool)
                shown.append(f"{token} (nearest accepted: {', '.join(near)})" if near else token)
            errors.append(
                f"unit {slot}: identifiers that are not accepted fact values: {', '.join(shown)}"
            )
        outside = sorted(set(unit_fact_ids) - task.accepted_ids)
        if outside:
            errors.append(
                f"unit {slot}: cites facts outside this section's set: {', '.join(outside)}"
            )
        errors.extend(
            f"unit {slot}: {mismatch}" for mismatch in unit_example_action_mismatches(unit, facts)
        )
    errors.extend(audience_errors(output.get("units", []), supporting, task.section_id))
    errors.extend(hygiene_errors(output.get("units", []), facts))
    errors.extend(carried_unit_errors(output, task, elsewhere_cited))
    return errors


_CARRY_REASON_MISSING = (
    "superseded into this section by reconciliation, so a unit must cite it and state its "
    "substance, or omitted must list it with a reason"
)


def _carry_dispositions(output: Mapping[str, Any]) -> tuple[set[str], dict[str, str]]:
    cited = {
        fact_id
        for unit in output.get("units", [])
        if isinstance(unit, dict)
        for fact_id in unit.get("fact_ids", [])
    }
    omitted = {
        str(item.get("fact_id")): str(item.get("reason") or "").strip()
        for item in output.get("omitted", [])
        if isinstance(item, dict)
    }
    return cited, omitted


def carried_unit_errors(
    output: Mapping[str, Any],
    task: SectionTask,
    elsewhere_cited: Mapping[str, str] = MappingProxyType({}),
) -> list[str]:
    """Each inherited unit the section must carry is cited by a unit or explicitly omitted with a
    reason - never silently absent."""
    if not task.must_carry:
        return []
    cited, omitted = _carry_dispositions(output)
    errors: list[str] = []
    for fact_id in sorted(task.must_carry):
        if fact_id in cited or omitted.get(fact_id):
            continue
        substance = task.must_carry_text.get(fact_id)
        suffix = f". Substance to carry: {substance}" if substance else ""
        wrong_section = elsewhere_cited.get(fact_id)
        if wrong_section and wrong_section != task.section_id:
            errors.append(
                f"{fact_id}: superseded into this section ({task.section_id}) by "
                f"reconciliation, so a unit here must cite it and state its substance, or "
                f"omitted must list it with a reason; it was instead cited in {wrong_section}, "
                f"which does not carry it for {task.section_id} - move its substance into a "
                f"unit here (or omit it here with a reason), rather than leaving it only in "
                f"{wrong_section}{suffix}"
            )
            continue
        errors.append(f"{fact_id}: {_CARRY_REASON_MISSING}{suffix}")
    return errors


def uncarried_units(output: Mapping[str, Any], must_carry: Collection[str]) -> list[str]:
    """The must-carry units a section output neither cites nor lists omitted, sorted."""
    cited, omitted = _carry_dispositions(output)
    return sorted(
        fact_id for fact_id in must_carry if fact_id not in cited and not omitted.get(fact_id)
    )


_PIP_INSTALL_FRAGMENT = re.compile(r"pip install\s+[^\s,;:.!?)]+")
_SHELL_PROMPT_FRAGMENT = re.compile(r"\$\s+[^\s,;:.!?)]+")
_INSTALLATION_POINTER = "the package as documented in the Installation section above"
_COMMAND_POINTER = "the command shown in the Installation section above"


def _strip_forbidden_command(text: str) -> str | None:
    """``text`` with a literal ``pip install <package>`` or ``$ <token>`` command fragment
    replaced by a fixed generic clause, or ``None`` when neither command marker is present."""
    replaced = text
    if "pip install" in replaced:
        replaced = _PIP_INSTALL_FRAGMENT.sub(_INSTALLATION_POINTER, replaced)
    if "$ " in replaced:
        replaced = _SHELL_PROMPT_FRAGMENT.sub(_COMMAND_POINTER, replaced)
    return replaced if replaced != text else None


def recover_forbidden_command_units(output: dict[str, Any]) -> dict[str, Any] | None:
    """Last-resort correction for ``run_job``'s final rejected attempt only (``recover=``):
    a literal ``pip install``/``$ ...`` command fragment is replaced by a fixed generic clause
    pointing at the Installation section the renderer already places the real command in."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict):
            continue
        text = unit.get("text")
        if not isinstance(text, str):
            continue
        stripped = _strip_forbidden_command(text)
        if stripped is not None:
            unit["text"] = stripped
            changed = True
    return output if changed else None


_ANGLE_MENTION = re.compile(r"<([A-Za-z_][\w.:-]*)/?>")
_ANGLE_MARKUP = re.compile(r"</|<[A-Za-z_][\w.:-]*\s")
_CODE_SPAN_PIECES = re.compile(r"(`[^`\n]*`)")


def _strip_angle_mentions(text: str) -> str | None:
    """``text`` with each ``<name>`` it mentions outside a code span read as the bare name, or
    ``None`` when there is nothing to rewrite or the text carries real markup."""
    outside = _CODE_SPAN.sub("", text)
    if "<" not in outside or _ANGLE_MARKUP.search(outside):
        return None

    def rewrite(piece: str) -> str:
        def read(match: re.Match[str]) -> str:
            before = piece[match.start() - 1 : match.start()]
            after = piece[match.end() : match.end() + 1]
            name = match.group(1)
            if before.isalnum() or before == "_":
                return match.group(0)
            return "{" + name + "}" if "/" in (before, after) else name

        return _ANGLE_MENTION.sub(read, piece)

    pieces = _CODE_SPAN_PIECES.split(text)
    rebuilt = "".join(piece if index % 2 else rewrite(piece) for index, piece in enumerate(pieces))
    return rebuilt if rebuilt != text else None


def recover_angle_bracket_mentions(output: dict[str, Any]) -> dict[str, Any] | None:
    """Last-resort correction: a unit that names an element or a path placeholder in angle
    brackets is rewritten to the bare name."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        rewritten = _strip_angle_mentions(unit["text"])
        if rewritten is not None:
            unit["text"] = rewritten
            changed = True
    return output if changed else None


def _title_verbatim_opening_length(text: str, title: str) -> int | None:
    """How many leading characters of ``text`` are ``title`` restated verbatim as its own opening
    clause, or ``None`` when ``text`` does not open this way."""
    lead = len(text) - len(text.lstrip())
    stripped = text[lead:]
    trimmed_title = title.strip()
    if not trimmed_title or not stripped.lower().startswith(trimmed_title.lower()):
        return None
    remainder = stripped[len(trimmed_title) :]
    if remainder and (remainder[0].isalnum() or remainder[0] == "'"):
        return None
    consumed = 0
    while consumed < len(remainder) and remainder[consumed] in ".:!?":
        consumed += 1
    while consumed < len(remainder) and remainder[consumed].isspace():
        consumed += 1
    return lead + len(trimmed_title) + consumed


def repair_title_verbatim_opening_errors(output: Mapping[str, Any], task: SectionTask) -> list[str]:
    """Independent review's own stricter title-restatement standard, layered onto an S6 repair's
    own checks only."""
    errors: list[str] = []
    for unit in output.get("units", []):
        title = task.slot_titles.get(str(unit.get("slot")))
        text = str(unit.get("text", ""))
        if title and _title_verbatim_opening_length(text, title) is not None:
            errors.append(
                f"unit {unit.get('slot')}: opens with its own title {title!r} restated "
                "verbatim; independent review treats this literal opening clause as generic "
                "regardless of what detail follows it - remove or rewrite the opening clause "
                "itself, never just add detail after it"
            )
    return errors


def _strip_title_verbatim_opening_units(units: list[Any], slot_titles: Mapping[str, str]) -> bool:
    """``units`` mutated in place: strip a unit's literal title-verbatim opening clause, keeping
    whatever real detail follows it."""
    changed = False
    for unit in units:
        if not isinstance(unit, dict):
            continue
        title = slot_titles.get(str(unit.get("slot")))
        text = unit.get("text")
        if not title or not isinstance(text, str):
            continue
        end = _title_verbatim_opening_length(text, title)
        if end is None:
            continue
        remainder = text[end:].strip()
        if not remainder:
            continue
        fixed = remainder[0].upper() + remainder[1:] if remainder[0].isalpha() else remainder
        unit["text"] = fixed
        changed = True
    return changed


def recover_title_verbatim_opening(
    output: dict[str, Any], *, slot_titles: Mapping[str, str]
) -> dict[str, Any] | None:
    """Last-resort correction for a ``targeted_repair`` job's own final rejected attempt only."""
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return None
    units = revised.get("units")
    if not isinstance(units, list):
        return None
    return output if _strip_title_verbatim_opening_units(units, slot_titles) else None


def recover_preserved_duplicates(
    output: dict[str, Any],
    *,
    section: str,
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
) -> dict[str, Any] | None:
    """Last-resort correction for one task's own final rejected attempt: trims a unit of
    ``section`` whose sentences an inherited paragraph the renderer already preserves verbatim
    in the SAME section states just as well, keeping only the sentences that paragraph does not
    already say. Returns ``None`` (never fabricates replacement content) when nothing would be
    left to keep -- the job then fails closed, exactly as it would with no ``recover`` at all.

    Generalizes what was ``recover_opening_duplicates_preserved``, hard-coded to "opening"
    alone; see :func:`preserved_section_text` for the live defect that motivated widening it."""
    preserved = preserved_section_text(dispositions, facts, section)
    if not preserved:
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    shown = Destinations.of({section: preserved})
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        if unit.get("section") not in (section, None):
            continue
        text = unit["text"]
        if not (states_all(preserved, text) or states_all(text, preserved)):
            continue
        remainder = uncovered(f"{section}:revised.paragraph", text, shown, section).strip()
        if remainder and remainder != text:
            unit["text"] = remainder
            changed = True
    return output if changed else None


def recover_opening_duplicates_preserved(
    output: dict[str, Any],
    *,
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
) -> dict[str, Any] | None:
    """Last-resort correction for the "opening" task's own final rejected attempt only: trims a
    unit's sentences that the inherited paragraph already preserved verbatim beside it states
    just as well, keeping only the sentences that paragraph does not already say. Returns
    ``None`` (never fabricates replacement content) when nothing would be left to keep -- the
    job then fails closed, exactly as it would with no ``recover`` at all."""
    return recover_preserved_duplicates(
        output, section="opening", dispositions=dispositions, facts=facts
    )


def recover_section_authoring_output(
    output: dict[str, Any],
    *,
    slot_titles: Mapping[str, str],
) -> dict[str, Any] | None:
    """Last-resort correction for ``section_authoring``'s own INITIAL-DRAFT job: composes the
    known last-resort corrections for this call site, in order."""
    changed = recover_forbidden_command_units(output) is not None
    if recover_angle_bracket_mentions(output) is not None:
        changed = True
    units = output.get("units")
    if isinstance(units, list) and _strip_title_verbatim_opening_units(units, slot_titles):
        changed = True
    return output if changed else None


def merge_units(
    outputs: list[tuple[str, dict[str, Any]]] | dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Every accepted task output merged in shell order into one document."""
    pairs = list(outputs.items()) if isinstance(outputs, dict) else list(outputs)
    order = {section: index for index, section in enumerate(section_ids())}
    units: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    for section, output in sorted(pairs, key=lambda pair: order.get(pair[0], len(order))):
        units.extend(output.get("units", []))
        omitted.extend({"section": section, **item} for item in output.get("omitted", []))
    return {"schema_version": 1, "units": units, "omitted": omitted}


def write_content_units(document: dict[str, Any], path: Path) -> str:
    data = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
