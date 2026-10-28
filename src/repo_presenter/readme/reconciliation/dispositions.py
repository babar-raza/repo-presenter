"""Reconcile the existing README with the facts: one disposition per inherited unit.

Ported (PARTIAL, ADAPT) from the old repository-presenter project's
``components/readme/reconciliation/dispositions.py`` (2859 lines) per migration/
reuse-manifest.yaml ("readme/composition/" entry), which flags this module higher-risk (likely
locus of the historical 389/746-unit defect) and instructs: port ``coverage_findings()`` together
with ``normalize()``, never separately, so the self-audit travels with the logic it checks. Read
in full as part of this taskcard.

**Ported here**: ``normalize()`` (folds a placement deterministic code cannot honour into the
disposition it can -- a placement into a deterministic section becomes a supersession citing the
facts that section renders; a placed code block whose example is UNRESOLVED is deferred; a
contradicted embedded link or a forbidden edition label or an unverified example fence inside a
kept unit is folded to VERIFIED_REWRITE so S6 re-authors it from facts), ``coverage_findings()``
and its own ``_omission_gap()`` (the TC-DSP-01 self-audit: every disposition that claims more than
reconciliation can prove before a plan exists), together with their full, exactly-as-faithful
supporting network (``coverage_context``/``_Coverage``, ``_judge``, ``_supersession_gap``,
``_fold_uncovered``, ``_rehome_misfiled_units``, ``_restates``/``_claim``, ``_prune_incidental_
coverage``, ``code_units_by_polarity``, ``contradicted_code_units``/``contradicted_link_hrefs``/
``contradicted_embedded_links``, ``command_block_units``, ``unpublished_registry_blocks``,
``rendering_fact_ids``, ``is_version_skew_warning``, ``edition_labels``, ``example_fences``, every
constant and gap-reason label these use).

**Ported later** (2026-10-22, once ``core/llm/prompts.py``'s plumbing and the real
``prompts/source_reconciliation.yaml`` content both existed): the S4 job-wiring half --
``reconciliation_packet``/``reconciliation_schema``/``reconciliation_batches``/
``reconciliation_batch_facts``/``units_per_reply``/``merge_dispositions``/``summarize``/
``write_dispositions`` and their own supporting functions (``_packet_fact_records``,
``citable_fact_ids``, ``_sections_packet``, ``output_chars_bound``/``_longest``/``_reply_chars``/
``_variant_chars``/``_batch_size``). This is what builds and fires one real
``source_reconciliation`` call; see ``scripts/run_lane_r_reconciliation.py``.

**Still deferred** (not ported, with the reason): ``reconciliation_narrowing`` (the narrowed
re-ask repair path for a partially-rejected batch), ``placement_errors``, ``dangling_pointers``,
``coordinate_neighbor_promises``, ``recover_uncited_prose_omits`` and their own supporting
functions (the refusal-message/repair half that reacts to what ``coverage_findings`` reports,
rather than the self-audit itself -- these also need ``composition/references.py``'s
``dangling_references``, not ported). This split follows the manifest's own instruction
precisely: the self-audit (what counts as provable) travels with ``normalize`` intact; the
separate refusal-message/repair layer built on top of it does not, and firing one real call does
not need it either.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from repo_presenter.core.ecosystems import EcosystemSpec, spec_for
from repo_presenter.core.errors import ConfigError
from repo_presenter.core.facts import (
    DECLARED_SYMBOL_KINDS,
    REGISTRY_COMMAND_ATTRIBUTE,
    Fact,
    FactsDocument,
    bounded_records,
)
from repo_presenter.core.llm.binding import collect_ids
from repo_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repo_presenter.core.package_registry import (
    DISTRIBUTION_FACT_PREFIX,
    PUBLISHED_VERSION_FACT_ID,
)
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import (
    _CARRY_SECTIONS,
    edition_substitutes,
    inherited_unit_named_symbols,
)
from repo_presenter.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    SUBSECTION_HEADINGS,
    placeable_section_ids,
    section_ids,
    shell_packet,
)
from repo_presenter.readme.composition.coverage import unversioned
from repo_presenter.readme.composition.placement import (
    renderer_fact_ids,
    resolve_intra_document_anchors,
)
from repo_presenter.readme.composition.planning import section_conditions
from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy
from repo_presenter.readme.composition.references import dangling_references
from repo_presenter.readme.composition.source_topics import (
    path_topic,
    root_heading,
    source_heading,
)
from repo_presenter.readme.evidence.facts.links import extract_links, heading_slug
from repo_presenter.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
from repo_presenter.readme.evidence.facts.registry_lag import REGISTRY_LAG_FACT_ID
from repo_presenter.readme.reconciliation.destinations import (
    disposition_variants,
    holdable_sections,
    nearest_holdable,
    rehomed,
)
from repo_presenter.readme.validation.claims import install_identity_findings

DISPOSITIONS_FILENAME = "dispositions.json"
# Ported 2026-10-23 for readme/validation/deferrals.py's NOT_CARRIED_BY_NAMED_SECTION class to
# import from here, matching the old repo's own layout (deferrals.py there imports this constant
# from dispositions.py, not from itself). The old repo's own ``_recover_uncovered`` last-attempt
# fold -- the mechanism that actually PREPENDS this prefix to a rationale, after TC-DSP-01 found a
# disposition claiming a supersession its destination could not provably carry -- is not ported
# here (part of dispositions.py's own refusal/repair half this repository has not pulled in full).
# No live S4 call in this repository can currently produce a rationale carrying this prefix, so
# deferrals.py's NOT_CARRIED_BY_NAMED_SECTION class is correctly registered but dormant until that
# fold exists -- the same honest "ported, not yet exercised by an upstream producer" boundary this
# repository already uses for several other components.
RECOVERED_COVERAGE_RATIONALE = "Not provably carried by the section named; held for the owner. "
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
_SHELL_OWNED = frozenset({"heading", "badge_row"})
_RENDERER_OWNED_LINK_IDS = frozenset({BANNER_FACT_ID, HOMEPAGE_FACT_ID, ENTERPRISE_FACT_ID})
_COMMAND_FENCES = frozenset({"bash", "sh", "shell", "console", "zsh", "powershell", "pwsh", "cmd"})
_INSTALL_COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:python3?\s+-m\s+)?(?:pip3?\s+install|npm\s+install|dotnet\s+add|"
    r"cargo\s+add|go\s+get|git\s+clone)\b",
    re.IGNORECASE | re.MULTILINE,
)

_RECONCILIATION_BATCH = 40
# S4 output budget. A reply is bounded by construction, not by a measured average: the schema
# caps each disposition's fact_ids at RECONCILIATION_FACT_IDS_PER_DISPOSITION, and a batch is
# only as large as the longest reply the schema admits still fits max_output_tokens, counted at
# OUTPUT_CHARS_PER_TOKEN_FLOOR characters per token. The defect this closes (PDF-TypeScript,
# 2026-10-04): one 40-unit reply reached finish_reason length at 32,000 tokens, and the same
# request then answered 4,666. A disposition's citations were bounded only by the batch's citable
# set (739 IDs there), so a repeating list could run to the whole budget. The same class ran away
# on Cells-Go (2026-09-11, 1,047 repeated IDs) and PDF-.NET (F27).
RECONCILIATION_FACT_IDS_PER_DISPOSITION = 16
# The healthy 40-unit reply measured 4.2 characters per token (19,616 characters, 4,666 tokens,
# qwen3-next). Identifier-dense JSON packs fewer, so the bound uses this floor, never that average.
OUTPUT_CHARS_PER_TOKEN_FLOOR = 2.5
# The rationale's maxLength and the disposition enum, as the manifest states them; a test holds
# both to the manifest so the bound below can never drift from the schema it is computed for.
_RATIONALE_MAX_CHARS = 160
_DISPOSITIONS = (
    "VERIFIED_PRESERVE",
    "VERIFIED_REWRITE",
    "VERIFIED_MOVE",
    "CORRECT_WITH_EVIDENCE",
    "SUPERSEDE_REDUNDANT",
    "OMIT_UNSUPPORTED",
    "DEFER_UNRESOLVED",
    "NON_CONTENT",
)


def command_block_units(facts: FactsDocument) -> set[str]:
    """Inherited code blocks fenced as shell commands."""
    found: set[str] = set()
    for fact in facts.by_kind("inherited_unit"):
        first = fact.value.splitlines()[0].strip().lower() if fact.value.strip() else ""
        if fact.id.endswith(".code_block") and first[3:].strip() in _COMMAND_FENCES:
            found.add(fact.id)
    return found


def unpublished_registry_blocks(facts: FactsDocument) -> dict[str, str]:
    """Inherited command blocks that print the registry install of an unpublished package, by
    unit ID, with the install fact that records the package as unpublished."""
    implied = {
        fact.id: set(_command_lines(str((fact.attributes or {}).get(REGISTRY_COMMAND_ATTRIBUTE))))
        for fact in facts.by_kind("install_command")
        if fact.polarity == "SUPPORTED" and (fact.attributes or {}).get(REGISTRY_COMMAND_ATTRIBUTE)
    }
    if not implied:
        return {}
    blocks = command_block_units(facts)
    found: dict[str, str] = {}
    for unit in facts.by_kind("inherited_unit"):
        if unit.id not in blocks:
            continue
        lines = set(_command_lines(unit.value))
        install_id = next(
            (fid for fid, commands in sorted(implied.items()) if lines and lines <= commands), ""
        )
        if install_id:
            found[unit.id] = install_id
    return found


RENDERING_FACT_KINDS: dict[str, tuple[str, ...]] = {
    "identity": ("identity", "package"),
    "badges": ("link_target",),
    "banner": ("link_target",),
    "navigation": ("identity",),
    "installation": ("install_command",),
    "dependencies": ("dependency",),
    "third_party_notices": ("third_party_notices",),
    "license": ("license",),
}
_UNIT_REFERENCE = re.compile(r"unit (inherited_unit:[0-9]+\.[a-z_]+)")
_UNIT_ORDINAL = re.compile(r"^inherited_unit:(\d{3})(?:\.\d{3})?\.[a-z_]+$")


def _unit_ordinal(unit_id: str) -> int | None:
    match = _UNIT_ORDINAL.match(unit_id)
    return int(match.group(1)) if match else None


def code_units_by_polarity(facts: FactsDocument, polarity: str) -> dict[str, str]:
    """Inherited code blocks whose example fact has ``polarity``, by unit ID, from the evidence."""
    units: dict[str, str] = {}
    for fact in facts.by_kind("example"):
        if fact.polarity != polarity:
            continue
        for evidence in fact.evidence:
            match = _UNIT_REFERENCE.search(evidence.detail or "")
            if match:
                units[match.group(1)] = fact.id
    return units


def contradicted_code_units(facts: FactsDocument) -> frozenset[str]:
    """Inherited code blocks whose example fact is CONTRADICTED, read from the example evidence."""
    return frozenset(code_units_by_polarity(facts, "CONTRADICTED"))


def contradicted_link_hrefs(facts: FactsDocument) -> dict[str, str]:
    """CONTRADICTED, non-renderer-owned ``link_target`` facts, by href."""
    return {
        fact.value: fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "CONTRADICTED" and fact.id not in _RENDERER_OWNED_LINK_IDS
    }


def contradicted_embedded_links(unit_text: str, contradicted: Mapping[str, str]) -> set[str]:
    """Fact IDs of ``unit_text``'s own embedded links whose target is CONTRADICTED."""
    if not contradicted:
        return set()
    return {
        contradicted[link.href] for link in extract_links(unit_text) if link.href in contradicted
    }


def rendering_fact_ids(section: str, facts: FactsDocument) -> list[str]:
    """The SUPPORTED facts a deterministic section renders for this repository, by ID."""
    if section == "banner":
        pair = banner_target(facts.facts)
        return sorted(fact.id for fact in pair) if pair is not None else []
    kinds = RENDERING_FACT_KINDS.get(section, ())
    return sorted(
        fact.id for fact in facts.facts if fact.kind in kinds and fact.polarity == "SUPPORTED"
    )


# ---------------------------------------------------------------------------------------------
# TC-DSP-01 / G3-W08: a unit is dropped only when something true takes its place. See module
# docstring for the full account; kept verbatim from the old repository.
# ---------------------------------------------------------------------------------------------
_CONTENT_KINDS = frozenset({"paragraph", "list", "table", "code_block", "blockquote"})
_NEUTRAL_FACT_KINDS = frozenset({"identity", "package", "inherited_unit"})
_SECTION_RENDERS: dict[str, frozenset[str]] = {
    "identity": frozenset({"heading"}),
    "badges": frozenset({"badge_row"}),
    "banner": frozenset({"badge_row"}),
    "navigation": frozenset({"heading", "list"}),
    "installation": frozenset({"heading", "paragraph", "list", "code_block", "blockquote"}),
    "dependencies": frozenset({"heading", "paragraph", "list", "table", "code_block"}),
    "third_party_notices": frozenset({"heading", "paragraph", "list"}),
    "license": frozenset({"heading", "paragraph"}),
}
_NAVIGATION_ITEM = re.compile(r"^\s*[-*+]\s*\[[^\]]+\]\(#[^)\s]*\)\s*$")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_NAME_SPAN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::|-)[A-Za-z0-9_]+)*"
    r"(?:<[A-Za-z0-9_.,:\s\[\]<>-]*>)?(?:\[\])?"
)
_VERSION_PIN = re.compile(r"(?<=\S)(?:==|>=|<=|~=|!=|>|<)[^\s]+|\s--version\s+\S+")
_PROMPT = re.compile(r"^\s*(?:[$>]\s+)")

UNRENDERED_FACTS = "unrendered_facts"
UNRENDERED_COMMAND = "unrendered_command"
SECTION_RENDERS_OTHER_KINDS = "section_renders_other_kinds"
NOT_LEAD_PARAGRAPH = "not_lead_paragraph"
PLAN_DEPENDENT = "plan_dependent"
EXAMPLE_NOT_VERIFIED = "example_not_verified"
NO_DESTINATION = "no_destination"
API_MEMBERS = "api_members"
NOT_AN_API_LISTING = "not_an_api_listing"
NOT_A_DIAGRAM = "not_a_diagram"
NOT_NAVIGATION = "not_navigation"
OMIT_UNRESOLVED_EXAMPLE = "omit_unresolved_example"
OMIT_VERIFIED_EXAMPLE = "omit_verified_example"
OMIT_NAMES_SUPPORTED = "omit_names_supported"
UNCOVERED_SUPERSESSION = "uncovered_supersession"
DANGLING_POINTER = "dangling_pointer"
SUPPORTED_OMISSION = "supported_omission"
OMIT_VERSION_SKEW = "omit_version_skew"

_SKEW_WARNING = re.compile(
    r"\b(?:predate[sd]?|lags?\s+behind|behind\s+the\s+(?:source|repository|main|latest)"
    r"|ahead\s+of\s+the\s+(?:release|published|registry|pypi|npm|nuget|maven|crates)"
    r"|newer\s+than\s+(?:the\s+)?(?:release|published|registry|pypi|npm|nuget|maven|crates)"
    r"|unreleased|not\s+(?:yet\s+)?(?:in|part\s+of|included\s+in)\s+(?:that|the|this)\s+"
    r"(?:published\s+)?(?:release|version|package|build))\b",
    re.IGNORECASE,
)
_SKEW_CONTEXT = re.compile(
    r"\b(?:release|registry|pypi|npm|nuget|maven|crates\.io|published|package|version)\b",
    re.IGNORECASE,
)
_SKEW_KINDS = frozenset({"paragraph", "list", "blockquote"})


def is_version_skew_warning(text: str) -> bool:
    """Whether ``text`` warns that the registry's release lags the source tree."""
    return bool(_SKEW_WARNING.search(text) and _SKEW_CONTEXT.search(text))


@dataclass(frozen=True)
class CoverageGap:
    """One disposition that claims more than reconciliation can prove, and why."""

    unit_id: str
    disposition: str
    destination: str | None
    reason: str
    detail: str


def _unit_kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _is_mermaid(text: str) -> bool:
    first = text.splitlines()[0].strip().lower() if text.strip() else ""
    return first.startswith("```") and first[3:].strip() == "mermaid"


def _command_lines(text: str) -> list[str]:
    """The comparable command lines of a fenced block: prompts, comments, fences and version pins
    removed, release numbers replaced, whitespace collapsed, lower case."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = _PROMPT.sub("", raw).strip()
        if not line or line.startswith(("```", "#", "//")):
            continue
        lines.append(" ".join(unversioned(_VERSION_PIN.sub("", line)).split()).lower())
    return lines


@dataclass(frozen=True)
class _Coverage:
    """What reconciliation can prove a destination carries: derived from the facts alone."""

    facts: FactsDocument
    units: Mapping[str, Fact]
    kinds: Mapping[str, str]
    deterministic: frozenset[str]
    placeable: frozenset[str]
    rendered: Mapping[str, frozenset[str]]
    api_ids: frozenset[str]
    api_names: frozenset[str]
    namespaces: frozenset[str]
    api_members: frozenset[str]
    examples: Mapping[str, tuple[str, str]]
    commands: frozenset[str]
    lead: frozenset[str]
    commands_blocks: frozenset[str]
    lag: str = ""

    def text(self, unit_id: str) -> str:
        unit = self.units.get(unit_id)
        return unit.value if unit is not None else ""

    def named(self, unit_id: str) -> frozenset[str]:
        return inherited_unit_named_symbols(self.facts, self.text(unit_id))


def _example_status(facts: FactsDocument) -> dict[str, tuple[str, str]]:
    """Each inherited code block's example fact: ``unit -> (polarity, example fact id)``."""
    status: dict[str, tuple[str, str]] = {}
    for fact in facts.by_kind("example"):
        for evidence in fact.evidence:
            match = _UNIT_REFERENCE.search(evidence.detail or "")
            if match:
                status[match.group(1)] = (fact.polarity, fact.id)
    return status


def _rendered_commands(facts: FactsDocument) -> frozenset[str]:
    """The command lines the Installation row can print."""
    lines: set[str] = set()
    for fact in facts.by_kind("install_command"):
        if fact.polarity == "SUPPORTED":
            lines.update(_command_lines(fact.value))
    ecosystem = next(
        (f.value for f in facts.by_kind("identity") if f.id == "identity:ecosystem"), ""
    )
    repository = next(
        (f.value for f in facts.by_kind("identity") if f.id == "identity:repository"), ""
    )
    try:
        spec = spec_for(ecosystem)
    except ConfigError:
        return frozenset(lines)
    executed = [fact for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"]
    install = next(
        (f for f in facts.by_kind("install_command") if f.id == spec.install_fact_id), None
    )
    kind = (install.attributes or {}).get("install_kind") if install is not None else None
    if executed and repository and kind not in {"source", "source_checkout"}:
        lines.update(
            _command_lines(
                spec.source_checkout_command(install, repository, repository.split("/")[-1])
            )
        )
    imported = [
        fact.value
        for fact in facts.by_kind("import_path")
        if fact.polarity == "SUPPORTED"
        and any(
            re.search(spec.import_pattern.format(module=re.escape(fact.value)), example.value)
            for example in executed
        )
    ]
    if imported and spec.verify_command:
        lines.update(_command_lines(spec.verify_command.format(module=max(imported, key=len))))
    lines.update(_alternative_lines(facts, spec, install, kind))
    return frozenset(lines)


def _alternative_lines(
    facts: FactsDocument, spec: EcosystemSpec, install: Fact | None, kind: str | None
) -> set[str]:
    """The lines of the alternative declarations the Installation row prints under a registry
    install."""
    if install is None or install.polarity != "SUPPORTED" or kind in {"source", "source_checkout"}:
        return set()
    packages = {fact.id: fact for fact in facts.by_kind("package")}
    if any(
        fact.id.startswith(DISTRIBUTION_FACT_PREFIX) and fact.polarity == "SUPPORTED"
        for fact in packages.values()
    ):
        return set()
    package = packages.get("package:name")
    published = packages.get(PUBLISHED_VERSION_FACT_ID)
    version = (
        published
        if published is not None and published.polarity == "SUPPORTED"
        else packages.get("package:version")
    )
    if package is None or version is None:
        return set()
    return {
        line
        for _lead, _fence, body in spec.install_alternative_blocks(package.value, version.value)
        for line in _command_lines(body)
    }


def _lead_paragraphs(units: list[Fact]) -> frozenset[str]:
    """The README's lead paragraph: the first paragraph directly under the H1."""
    ordered = sorted(
        (u for u in units if _unit_kind(u.id) == "paragraph"),
        key=lambda u: (_unit_ordinal(u.id) is None, _unit_ordinal(u.id) or 0, u.id),
    )
    for unit in ordered:
        section = str((unit.attributes or {}).get("section") or "")
        if ">" not in section:
            return frozenset({unit.id})
    return frozenset()


def coverage_context(facts: FactsDocument) -> _Coverage:
    deterministic = frozenset(set(section_ids()) - placeable_section_ids())
    rendered = {section: frozenset(rendering_fact_ids(section, facts)) for section in deterministic}
    rendered["installation"] = rendered["installation"] | frozenset(
        f.id for f in facts.by_kind("import_path") if f.polarity == "SUPPORTED"
    )
    api_ids = renderer_fact_ids("api_reference", facts)
    api_names: set[str] = set()
    for fact in facts.by_kind("public_symbol"):
        if fact.id in api_ids:
            api_names.update({fact.value, fact.value.rsplit(".", 1)[-1]})
    units = list(facts.by_kind("inherited_unit"))
    return _Coverage(
        facts=facts,
        units={u.id: u for u in units},
        kinds={f.id: f.kind for f in facts.facts},
        deterministic=deterministic,
        placeable=placeable_section_ids(),
        rendered=rendered,
        api_ids=api_ids,
        api_names=frozenset(api_names),
        namespaces=frozenset(
            f.id
            for f in facts.by_kind("public_symbol")
            if (f.attributes or {}).get("symbol_kind") == "module"
        ),
        api_members=frozenset(
            f.value.rsplit(".", 1)[-1]
            for f in facts.by_kind("public_symbol")
            if f.polarity == "SUPPORTED"
            and f.id not in api_ids
            and (f.attributes or {}).get("symbol_kind") != "module"
        ),
        examples=_example_status(facts),
        commands=_rendered_commands(facts),
        lead=_lead_paragraphs(units),
        commands_blocks=frozenset(command_block_units(facts)),
        lag="; ".join(
            f"{e.path}: {e.detail}"
            for f in facts.facts
            if f.id == REGISTRY_LAG_FACT_ID and f.polarity == "SUPPORTED"
            for e in f.evidence
        ),
    )


def _table_first_column(text: str) -> str:
    """The first cell of each body row: what a table lists. The other cells describe it."""
    cells: list[str] = []
    for row in text.splitlines()[2:]:
        parts = row.strip().strip("|").split("|")
        if parts and parts[0].strip():
            cells.append(parts[0])
    return "\n".join(cells)


def _uncovered_members(text: str, members: frozenset[str], names: frozenset[str]) -> list[str]:
    """Verified members the unit spells in code spans that the Core API table does not print."""
    found: list[str] = []
    for span in _CODE_SPAN.findall(text):
        token = _type_name(span.strip())
        if token in members and token not in names and token not in found:
            found.append(token)
    return found


def _type_name(span: str) -> str:
    """The name a listing's span stands for: its last dotted segment, without the generic, array
    or module suffix the README adds to tell two same-named types apart."""
    base = re.split(r"[<\[]", span, maxsplit=1)[0].split("-", 1)[0]
    return re.split(r"::|\.", base)[-1]


def _supersession_gap(
    unit_id: str, destination: str | None, cited: set[str], ctx: _Coverage
) -> tuple[str, str] | None:
    """Why ``destination`` cannot be shown to carry ``unit_id`` before a plan exists, or ``None``
    when it provably does."""
    kind = _unit_kind(unit_id)
    if kind not in _CONTENT_KINDS:
        return None
    text = ctx.text(unit_id)
    if kind == "code_block" and _is_mermaid(text):
        return None
    status = ctx.examples.get(unit_id)
    if status is not None and kind == "code_block":
        polarity, example_id = status
        if polarity != "SUPPORTED":
            return (
                EXAMPLE_NOT_VERIFIED,
                f"its example {example_id} is {polarity}, so no section prints this block",
            )
        if destination in {"quick_start", "additional_examples"}:
            return None
    if destination is None:
        return (NO_DESTINATION, "it names no section that carries the unit")
    if destination == "at_a_glance":
        return (NOT_A_DIAGRAM, "At a Glance holds one diagram and nothing else")
    named = ctx.named(unit_id)
    content = sorted(
        fact_id
        for fact_id in cited | named
        if ctx.kinds.get(fact_id) is not None
        and ctx.kinds[fact_id] not in _NEUTRAL_FACT_KINDS
        and fact_id not in ctx.namespaces
    )
    if destination in ctx.deterministic:
        if kind not in _SECTION_RENDERS.get(destination, frozenset()):
            return (
                SECTION_RENDERS_OTHER_KINDS,
                f"{destination} renders from facts and prints no {kind.replace('_', ' ')}",
            )
        if destination == "navigation" and not all(
            _NAVIGATION_ITEM.match(line) for line in text.splitlines() if line.strip()
        ):
            return (NOT_NAVIGATION, "navigation lists the document's own sections only")
        unrendered = (
            []
            if destination == "navigation"
            else [fact_id for fact_id in content if fact_id not in ctx.rendered[destination]]
        )
        if unrendered:
            return (
                UNRENDERED_FACTS,
                f"it rests on facts {destination} does not render: {', '.join(unrendered[:6])}",
            )
        if destination == "installation" and kind == "code_block":
            lines = _command_lines(text)
            missing = [line for line in lines if line not in ctx.commands]
            if not lines or missing:
                return (
                    UNRENDERED_COMMAND,
                    "installation prints the verified install command, not "
                    f"{(missing or ['this block'])[0]!r}",
                )
        return None
    if destination == "api_reference":
        if kind not in {"table", "list"}:
            return (
                SECTION_RENDERS_OTHER_KINDS,
                f"the Core API table lists classes and enums, not a {kind.replace('_', ' ')}",
            )
        unrendered = (
            []
            if kind == "table"
            else [
                fact_id
                for fact_id in content
                if fact_id not in ctx.api_ids and fact_id not in ctx.namespaces
            ]
        )
        spelled = _table_first_column(text) if kind == "table" else text
        spans = [span.strip() for span in _CODE_SPAN.findall(spelled)]
        if not spans or not all(_NAME_SPAN.fullmatch(span) for span in spans):
            return (NOT_AN_API_LISTING, "it lists paths or code, not the classes the table prints")
        unknown = _uncovered_members(spelled, ctx.api_members, ctx.api_names)
        if unrendered or unknown:
            what = unknown[:6] or unrendered[:6]
            return (
                API_MEMBERS,
                "the Core API table lists verified classes and enums only, not " + ", ".join(what),
            )
        return None
    if destination in _CARRY_SECTIONS and kind in {"paragraph", "list"}:
        return None
    if destination == "opening":
        if unit_id in ctx.lead:
            return None
        return (NOT_LEAD_PARAGRAPH, "the opening replaces the lead paragraph only")
    return (PLAN_DEPENDENT, f"what {destination} carries is chosen by the plan, after this stage")


# Real hosted defect (2026-10-27, run 40571540396, C++; recurs on 40571547837, Go): an
# OMIT_UNSUPPORTED with an empty ``fact_ids`` whose rationale claims "not supported by facts" or
# "redundant", while the unit's own text spells a SUPPORTED ``package`` or ``link_target`` fact's
# value verbatim (a NuGet ``PackageReference`` naming the repository's own verified distribution
# package; a Go paragraph naming the repository's own verified ``docs/usage.md`` link). The claim
# is false -- a matching fact DOES exist -- so ``live_readme_loss_rule``'s own ``_accounting_units``
# (``readme/review/independent_reviewer.py``) correctly refuses to count it as accounted for (it
# requires ``fact_ids`` truthy), and the content is reported lost even though a disposition exists.
# Scoped to the two fact kinds this shape was actually found with, cross-ecosystem; kept narrow and
# additive -- the disposition itself is never loosened, only an already-true citation is attached,
# the same way the PLACING-only backfill below attaches a named symbol it finds.
_OMISSION_CITABLE_KINDS = frozenset({"package", "link_target"})
_MIN_SPELLED_VALUE_CHARS = 4


def _spelled_supported_facts(unit_text: str, facts: FactsDocument) -> frozenset[str]:
    """SUPPORTED ``package``/``link_target`` fact IDs whose value is spelled verbatim inside
    ``unit_text``, long enough that a match cannot be a trivial coincidence."""
    return frozenset(
        fact.id
        for fact in facts.facts
        if fact.polarity == "SUPPORTED"
        and fact.kind in _OMISSION_CITABLE_KINDS
        and len(fact.value) >= _MIN_SPELLED_VALUE_CHARS
        and fact.value in unit_text
    )


def _omission_gap(unit_id: str, entry: Mapping[str, Any], ctx: _Coverage) -> tuple[str, str] | None:
    """Why an OMIT_UNSUPPORTED is not a failed support lookup, or ``None`` when it stands."""
    kind = _unit_kind(unit_id)
    if kind not in _CONTENT_KINDS or unit_id in ctx.commands_blocks:
        return None
    status = ctx.examples.get(unit_id)
    if status is not None and kind == "code_block":
        polarity, example_id = status
        if polarity == "UNRESOLVED":
            return (
                OMIT_UNRESOLVED_EXAMPLE,
                f"its example {example_id} is UNRESOLVED: facts neither support nor contradict "
                "it, which is a deferral",
            )
        if polarity == "SUPPORTED":
            return (OMIT_VERIFIED_EXAMPLE, f"its example {example_id} is verified")
        return None
    if ctx.lag and kind in _SKEW_KINDS and is_version_skew_warning(ctx.text(unit_id)):
        return (
            OMIT_VERSION_SKEW,
            f"it warns that the registry's release lags this source tree, which "
            f"{REGISTRY_LAG_FACT_ID} verifies ({ctx.lag})",
        )
    if entry.get("fact_ids") or kind in _PROSE_UNIT_KINDS:
        return None
    named = sorted(ctx.named(unit_id))
    if named:
        return (OMIT_NAMES_SUPPORTED, "its text spells SUPPORTED facts: " + ", ".join(named[:6]))
    return None


_PROSE_UNIT_KINDS = frozenset({"paragraph", "list"})


def _narrow_citations(entry: Mapping[str, Any], ctx: _Coverage) -> list[str]:
    """The facts a disposition cites that name something narrower than "this repository"."""
    return sorted(
        fact_id
        for fact_id in entry.get("fact_ids") or []
        if ctx.kinds.get(fact_id) not in {"identity", "package"}
    )


_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{2,}")
_FILLER = frozenset(
    {"the", "and", "for", "with", "this", "that", "are", "see", "from", "into", "use", "using"}
    | {"can", "you", "your", "has", "have", "was", "will", "its", "also", "all", "not", "but"}
)
_RESTATABLE_KINDS = frozenset({"paragraph", "list", "table", "blockquote"})
_RESTATED_SHARE = 0.8
_RESTATED_MIN_WORDS = 3
Claims = dict[tuple[str, str], set[str]]


def _subject_words(text: str) -> set[str]:
    """The words a unit's prose is about: lower case, filler dropped, paths and names whole."""
    return {word.rstrip("./-").lower() for word in _WORD.findall(text)} - _FILLER


def _restates(entry: Mapping[str, Any], destination: str, claims: Claims, ctx: _Coverage) -> bool:
    """Whether the unit only repeats what placed units in ``destination`` already say."""
    unit = str(entry.get("unit_id", "?"))
    if _unit_kind(unit) not in _RESTATABLE_KINDS:
        return False
    shared = [
        claims[destination, fact_id]
        for fact_id in _narrow_citations(entry, ctx)
        if (destination, fact_id) in claims
    ]
    words = _subject_words(ctx.text(unit))
    if not shared or len(words) < _RESTATED_MIN_WORDS:
        return False
    earlier = set().union(*shared)
    return len(words - earlier) <= (1 - _RESTATED_SHARE) * len(words)


def _claim(entry: Mapping[str, Any], destination: str, claims: Claims, ctx: _Coverage) -> None:
    """Record that ``entry`` places its prose in ``destination`` for each narrow fact it cites."""
    unit = str(entry.get("unit_id", "?"))
    if _unit_kind(unit) not in _RESTATABLE_KINDS:
        return
    words = _subject_words(ctx.text(unit))
    for fact_id in _narrow_citations(entry, ctx):
        claims.setdefault((destination, fact_id), set()).update(words)


def _judge(
    output: Mapping[str, Any], ctx: _Coverage
):
    """Each disposition with why it claims more than the stage can prove, or ``None``."""
    claims: Claims = {}
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        disposition = entry.get("disposition")
        destination = entry.get("destination_section")
        cited = set(entry.get("fact_ids") or [])
        gap: tuple[str, str] | None = None
        if disposition == "SUPERSEDE_REDUNDANT" or (
            disposition in PLACING and destination in ctx.deterministic
        ):
            gap = _supersession_gap(unit, destination, cited, ctx)
            if (
                gap is not None
                and disposition == "SUPERSEDE_REDUNDANT"
                and destination in ctx.placeable
                and gap[0] in {PLAN_DEPENDENT, NOT_LEAD_PARAGRAPH, API_MEMBERS, UNRENDERED_FACTS}
                and _restates(entry, destination, claims, ctx)
            ):
                gap = None
        elif disposition == "OMIT_UNSUPPORTED":
            gap = _omission_gap(unit, entry, ctx)
        yield entry, gap
        destination = entry.get("destination_section")
        if entry.get("disposition") in PLACING and destination in ctx.placeable:
            _claim(entry, destination, claims, ctx)


def coverage_findings(output: Mapping[str, Any], facts: FactsDocument) -> list[CoverageGap]:
    """Every disposition in ``output`` that claims more than reconciliation can prove.

    Read-only; ``normalize`` folds what it can, the (deferred) ``placement_errors`` refuses the
    rest."""
    return [
        CoverageGap(
            str(entry.get("unit_id", "?")),
            str(entry.get("disposition")),
            entry.get("destination_section"),
            gap[0],
            gap[1],
        )
        for entry, gap in _judge(output, coverage_context(facts))
        if gap is not None
    ]


def _prune_incidental_coverage(output: dict[str, Any], ctx: _Coverage) -> None:
    """Drop the class and enum citations that would make placement discard a unit as covered."""
    for entry in output.get("dispositions", []):
        if entry.get("disposition") not in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}:
            continue
        unit = str(entry.get("unit_id", "?"))
        if entry.get("destination_section") != "api_reference" or _unit_kind(unit) not in {
            "paragraph",
            "list",
            "table",
        }:
            continue
        cited = set(entry.get("fact_ids") or [])
        if not cited & ctx.api_ids:
            continue
        if _supersession_gap(unit, "api_reference", cited, ctx) is not None:
            entry["fact_ids"] = sorted(cited - ctx.api_ids)


_API_ROW = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)


def _is_row_table(unit: str, entry: Mapping[str, Any], ctx: _Coverage) -> bool:
    """An API Reference table whose rows BC-07 would count, that the Core API table does not
    cover."""
    return (
        entry.get("destination_section") == "api_reference"
        and unit.endswith(".table")
        and bool(_API_ROW.search(ctx.text(unit)))
        and _supersession_gap(unit, "api_reference", set(entry.get("fact_ids") or []), ctx)
        is not None
    )


def _fold_uncovered(output: dict[str, Any], facts: FactsDocument, ctx: _Coverage) -> None:
    """Fold every disposition that claims more than reconciliation can prove into the one it
    can."""
    for entry, gap in _judge(output, ctx):
        if gap is None:
            continue
        unit = str(entry.get("unit_id", "?"))
        cited = set(entry.get("fact_ids") or [])
        if entry.get("disposition") == "OMIT_UNSUPPORTED":
            if gap[0] == OMIT_UNRESOLVED_EXAMPLE:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
                entry["fact_ids"] = sorted(cited | {ctx.examples[unit][1]})
        elif gap[0] == NOT_A_DIAGRAM:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
        elif gap[0] == EXAMPLE_NOT_VERIFIED:
            polarity, example_id = ctx.examples[unit]
            entry["disposition"] = (
                "OMIT_UNSUPPORTED" if polarity == "CONTRADICTED" else "DEFER_UNRESOLVED"
            )
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {example_id})
        elif entry.get("disposition") == "SUPERSEDE_REDUNDANT" and (
            entry.get("destination_section") in ctx.placeable
        ):
            entry["disposition"] = (
                "VERIFIED_REWRITE" if _is_row_table(unit, entry, ctx) else "VERIFIED_PRESERVE"
            )


def _printed_by_installation(unit_id: str, cited: set[str], ctx: _Coverage) -> bool:
    """Whether ``unit_id`` is a code block every line of which the Installation row prints."""
    if _unit_kind(unit_id) != "code_block" or unit_id in ctx.examples:
        return False
    lines = _command_lines(ctx.text(unit_id))
    if not lines or any(line not in ctx.commands for line in lines):
        return False
    return _supersession_gap(unit_id, "installation", cited, ctx) is None


REHOMED_RATIONALE = "Kept in {section}: {old} holds no {topic} material. "
# The manifest's rationale field's own maxLength (the old repository's own
# ``_RATIONALE_MAX_CHARS``, the job-wiring schema bound; inlined here since that schema is not
# ported). Any rewritten rationale is truncated to this length, matching the field it fills.
_RATIONALE_LIMIT = 160


def _rehome_misfiled_units(
    output: dict[str, Any], facts: FactsDocument, units: Mapping[str, Fact]
) -> None:
    """Move every kept unit filed in a section that has no place for its topic to the section
    that does, in place."""
    holdable = holdable_sections(facts)
    root = root_heading(list(units.values()))
    for entry in output.get("dispositions", []):
        if entry.get("disposition") not in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}:
            continue
        unit_id = str(entry.get("unit_id", "?"))
        old = entry.get("destination_section")
        heading = source_heading(units.get(unit_id))
        home = rehomed(unit_id, heading, old, holdable, root)
        if home is None:
            continue
        lead = REHOMED_RATIONALE.format(section=home, old=old, topic=path_topic(heading, root))
        reason = str(entry.get("rationale") or "").strip()
        room = _RATIONALE_LIMIT - len(lead)
        if len(reason) > room:
            reason = reason[: max(room - 3, 0)].rstrip() + "..."
        entry["destination_section"] = home
        entry["rationale"] = (lead + reason).strip()


_PROSE_PRINTED_KINDS = frozenset({"paragraph", "list", "table", "blockquote"})
_OTHER_EDITION = re.compile(r"\b([A-Z][A-Za-z]+) Edition\b")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
RECOVERED_LABEL_RATIONALE = "Restated: it names an edition BC-06 forbids. "
RECOVERED_FENCE_RATIONALE = "Restated: it embeds an unverified code example BC-03 forbids. "


def edition_labels(text: str) -> list[str]:
    """The edition names BC-06 forbids in prose: a substitute for Enterprise Edition, or any
    other capitalised "Xxx Edition"."""
    prose = _INLINE_CODE.sub(" ", text)
    return [
        *edition_substitutes(prose),
        *(m.group(0) for m in _OTHER_EDITION.finditer(prose) if m.group(1) != "Enterprise"),
    ]


def example_fences(text: str, languages: Any) -> list[str]:
    """The fence languages of ``text`` BC-03 holds to a planned, verified example."""
    found: list[str] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type == "fence":
            info = token.info.strip()
            language = info.split()[0] if info else ""
            if language.lower() in languages:
                found.append(language)
    return found


def _example_languages(facts: FactsDocument) -> frozenset[str]:
    ecosystem = next(
        (f.value for f in facts.by_kind("identity") if f.id == "identity:ecosystem"), ""
    )
    try:
        return spec_for(ecosystem).example_fences
    except ConfigError:
        return frozenset()


def _omits_contradicted_command(entry: Mapping[str, Any], block: str, facts: FactsDocument) -> bool:
    """Whether an omitted command block is provably contradicted by a SUPPORTED fact the omission
    cites: the block installs a near-miss of the SUPPORTED ``package:name`` identity
    (``claims.install_identity_findings``) and the entry cites that identity or a SUPPORTED
    install fact. Mission section 7 step 3: contradicted content is removable with a specific
    evidence-backed explanation; anything short of this proof is a dropped verified command."""
    if not install_identity_findings(block, facts):
        return False
    cited = set(entry.get("fact_ids") or [])
    admitted = [f for f in facts.by_kind("package") if f.id == "package:name"]
    return any(
        fact.id in cited and fact.polarity == "SUPPORTED"
        for fact in (*admitted, *facts.by_kind("install_command"))
    )


def normalize(
    output: dict[str, Any], facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> list[str]:
    """Fold placements deterministic code cannot honour into the disposition it can, in place.

    A placement into a deterministic section becomes a supersession citing the facts that section
    renders. A placed code block whose example is UNRESOLVED, or a placement into the Enterprise
    Edition section while the policy carries no verified target, is deferred: the candidate cannot
    render either at this revision, so "verified" would be false. A code block placed into At a
    Glance is superseded by the renderer's own diagram. Returns the units that cannot be folded
    because the section renders nothing here.
    """
    deterministic = set(section_ids()) - placeable_section_ids()
    coverage = coverage_context(facts)
    unresolved = code_units_by_polarity(facts, "UNRESOLVED")
    contradicted = code_units_by_polarity(facts, "CONTRADICTED")
    contradicted_links = contradicted_link_hrefs(facts)
    commands = command_block_units(facts)
    unpublished = unpublished_registry_blocks(facts)
    units_by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    fence_languages = _example_languages(facts)
    install_ids = sorted(
        f.id for f in facts.by_kind("install_command") if f.polarity == "SUPPORTED"
    )
    build_ids = sorted(f.id for f in facts.by_kind("build_test_asset") if f.polarity == "SUPPORTED")
    absent = {
        section for section, holds in section_conditions(facts, policy).items() if holds is False
    }
    errors: list[str] = []
    _fold_uncovered(output, facts, coverage)
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        destination = entry.get("destination_section")
        disposition = entry.get("disposition")
        cited = set(entry.get("fact_ids") or [])
        if unit in unpublished:
            if disposition != "OMIT_UNSUPPORTED":
                entry["rationale"] = (
                    "The registry lists no such package, so this install command cannot be run; "
                    "the Installation section states that the package is unpublished and gives "
                    "the source checkout."
                )
            entry["disposition"] = "OMIT_UNSUPPORTED"
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {unpublished[unit]})
            continue
        if disposition in PLACING and unit in unresolved:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {unresolved[unit]})
            continue
        if (
            disposition == "OMIT_UNSUPPORTED"
            and unit in commands
            and _omits_contradicted_command(entry, units_by_id[unit].value, facts)
        ):
            continue
        restated = (
            disposition == "DEFER_UNRESOLVED"
            and not cited
            and unit not in unresolved
            and unit not in contradicted
        )
        if (
            (disposition == "OMIT_UNSUPPORTED" or restated)
            and unit in commands
            and (install_ids or build_ids)
        ):
            block = units_by_id[unit]
            heading = " ".join(e.detail or "" for e in block.evidence)
            installing = "> Installation" in heading or bool(_INSTALL_COMMAND.search(block.value))
            installing = installing and (
                _supersession_gap(unit, "installation", cited, coverage) is None
            )
            if installing and install_ids:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "installation"
                entry["fact_ids"] = sorted(cited | set(install_ids))
            elif "development_testing" in absent:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "VERIFIED_PRESERVE"
                entry["destination_section"] = "development_testing"
                entry["fact_ids"] = sorted(cited | set(build_ids or install_ids))
            continue
        if (
            disposition in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
            and install_ids
            and _printed_by_installation(unit, cited, coverage)
        ):
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "installation"
            entry["fact_ids"] = sorted(cited | set(install_ids))
            continue
        if disposition in PLACING and unit in contradicted:
            entry["disposition"] = "OMIT_UNSUPPORTED"
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {contradicted[unit]})
            continue
        if (
            disposition in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            unit_fact = units_by_id.get(unit)
            bad_links = (
                contradicted_embedded_links(unit_fact.value, contradicted_links)
                if unit_fact is not None
                else set()
            )
            if bad_links:
                entry["disposition"] = "VERIFIED_REWRITE"
                entry["fact_ids"] = sorted(cited - bad_links)
                continue
            if unit_fact is not None and unit.rsplit(".", 1)[-1] in _PROSE_PRINTED_KINDS:
                if edition_labels(unit_fact.value):
                    entry["disposition"] = "VERIFIED_REWRITE"
                    entry["rationale"] = (
                        RECOVERED_LABEL_RATIONALE + str(entry.get("rationale") or "")
                    )[:_RATIONALE_LIMIT]
                    continue
                if example_fences(unit_fact.value, fence_languages):
                    entry["disposition"] = "VERIFIED_REWRITE"
                    entry["rationale"] = (
                        RECOVERED_FENCE_RATIONALE + str(entry.get("rationale") or "")
                    )[:_RATIONALE_LIMIT]
                    continue
        if disposition in PLACING and (
            destination == "banner" or (unit.endswith(".badge_row") and BANNER_FACT_ID in cited)
        ):
            if banner_target(facts.facts) is None:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            elif unit.rsplit(".", 1)[-1] not in _CONTENT_KINDS:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "banner"
                entry["fact_ids"] = sorted(cited | {BANNER_FACT_ID, HOMEPAGE_FACT_ID})
            continue
        if disposition in PLACING and destination == "enterprise_relationship":
            if enterprise_target(facts.facts) is None or unit.rsplit(".", 1)[-1] not in {
                "paragraph",
                "heading",
            }:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "enterprise_relationship"
                entry["fact_ids"] = sorted(cited | {ENTERPRISE_FACT_ID})
            continue
        if (
            disposition in PLACING
            and destination == "opening"
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
            and unit in coverage.lead
        ):
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "opening"
            continue
        if (
            disposition in PLACING
            and destination == "api_reference"
            and unit.endswith(".table")
            and _supersession_gap(unit, "api_reference", cited, coverage) is None
        ):
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "api_reference"
            continue
        if disposition in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"} and _is_row_table(
            unit, entry, coverage
        ):
            entry["disposition"] = "VERIFIED_REWRITE"
            continue
        if (
            disposition in PLACING
            and destination == "at_a_glance"
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            covered = bool(cited) and _supersession_gap(unit, destination, cited, coverage) is None
            entry["disposition"] = "SUPERSEDE_REDUNDANT" if covered else "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if (
            disposition == "SUPERSEDE_REDUNDANT"
            and destination in absent
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if (
            disposition in PLACING
            and destination in absent
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if destination not in deterministic:
            continue
        ids = rendering_fact_ids(destination, facts)
        if not ids:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if _supersession_gap(unit, destination, cited, coverage) is not None:
            continue
        entry["disposition"] = "SUPERSEDE_REDUNDANT"
        entry["fact_ids"] = sorted(cited | set(ids))
    _rehome_misfiled_units(output, facts, units_by_id)
    claims: Claims = {}
    for entry in output.get("dispositions", []):
        destination = entry.get("destination_section")
        if entry.get("disposition") not in PLACING or destination not in placeable_section_ids():
            continue
        if _restates(entry, destination, claims, coverage):
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            continue
        _claim(entry, destination, claims, coverage)
    for entry in output.get("dispositions", []):
        if entry.get("disposition") not in PLACING:
            continue
        unit_fact = units_by_id.get(str(entry.get("unit_id", "?")))
        if unit_fact is None or unit_fact.polarity != "SUPPORTED":
            continue
        named = inherited_unit_named_symbols(facts, unit_fact.value)
        if not named:
            continue
        entry["fact_ids"] = sorted(set(entry.get("fact_ids") or []) | named)
    for entry in output.get("dispositions", []):
        if entry.get("disposition") != "OMIT_UNSUPPORTED" or entry.get("fact_ids"):
            continue
        unit_fact = units_by_id.get(str(entry.get("unit_id", "?")))
        if unit_fact is None:
            continue
        cited = _spelled_supported_facts(unit_fact.value, facts)
        if not cited:
            continue
        entry["fact_ids"] = sorted(cited)
        entry["rationale"] = (
            "Redundant with the verified facts it names: "
            + ", ".join(sorted(cited))
            + ". "
            + str(entry.get("rationale") or "")
        )[:_RATIONALE_LIMIT]
    _prune_incidental_coverage(output, coverage)
    return errors


# S4 job-wiring half, ported later than the rest of this module (2026-10-22): builds the actual
# LLM packet/schema/batching for ``source_reconciliation``, now that core/llm/prompts.py's
# plumbing and the real prompts/source_reconciliation.yaml content both exist in this repository.
# ``reconciliation_narrowing`` (the narrowed re-ask repair path), ``placement_errors``,
# ``dangling_pointers``, ``coordinate_neighbor_promises``, and ``recover_uncited_prose_omits`` are
# still NOT ported -- the refusal-message/repair layer built on top of ``coverage_findings``,
# needed only once a real rejection or repair round is being driven, not to fire one real call.


def _longest(node: Mapping[str, Any]) -> int | None:
    """The longest serialized value a schema node admits, JSON quotes included; ``None`` if open."""
    if "enum" in node:
        return max(len(json.dumps(value, ensure_ascii=False)) for value in node["enum"])
    for key in ("oneOf", "anyOf"):
        if key in node:
            known = [
                size for size in (_longest(option) for option in node[key]) if size is not None
            ]
            return max(known) if len(known) == len(node[key]) else None
    if node.get("type") == "null":
        return len("null")
    if node.get("type") == "string" and "maxLength" in node:
        return int(node["maxLength"]) + 2
    return None


def _reply_chars(
    records: int,
    *,
    unit_chars: int,
    disposition_chars: int,
    destination_chars: int,
    fact_id_chars: int,
    citations: int,
    rationale_chars: int,
) -> int:
    """Characters of the longest reply of ``records`` dispositions: every value at the given
    serialized length, every citation list full, pretty-printed (the wider of the two forms a
    model writes, so compact output is bounded too)."""
    record = {
        "unit_id": "u" * (unit_chars - 2),
        "disposition": "d" * (disposition_chars - 2),
        "destination_section": "s" * (destination_chars - 2),
        "fact_ids": ["f" * (fact_id_chars - 2)] * citations,
        "rationale": "r" * (rationale_chars - 2),
    }
    return len(json.dumps({"dispositions": [record] * records}, indent=2, ensure_ascii=False))


def output_chars_bound(schema: Mapping[str, Any]) -> int | None:
    """The longest reply, in characters, that ``schema`` admits; ``None`` when a field it leaves
    open makes the bound infinite. Computed from the schema the job is decoded under, so it tracks
    the schema rather than a separate estimate; it is a bound only to the extent the decoder
    enforces that schema, which the live proof checks against a real reply."""
    dispositions = schema["properties"]["dispositions"]
    items = dispositions["items"]
    bounds = [
        _variant_chars(dispositions, variant["properties"])
        for variant in items.get("anyOf", [items])
    ]
    return None if None in bounds else max(bound for bound in bounds if bound is not None)


def _variant_chars(dispositions: Mapping[str, Any], props: Mapping[str, Any]) -> int | None:
    """The longest reply one shape of the disposition object admits (see ``output_chars_bound``)."""
    fact_ids = props["fact_ids"]
    sizes = {
        "unit_chars": _longest(props["unit_id"]),
        "disposition_chars": _longest(props["disposition"]),
        "destination_chars": _longest(props["destination_section"]),
        "rationale_chars": _longest(props["rationale"]),
        "citations": fact_ids.get("maxItems"),
    }
    if None in sizes.values() or "maxItems" not in dispositions:
        return None
    fact_chars = _longest(fact_ids["items"]) if "items" in fact_ids else 0
    if fact_chars is None:
        return None
    return _reply_chars(
        dispositions["maxItems"],
        **{k: v for k, v in sizes.items() if k != "citations"},
        fact_id_chars=fact_chars,
        citations=sizes["citations"],
    )


def _batch_size(facts: FactsDocument, max_output_tokens: int) -> int:
    """The largest batch, up to _RECONCILIATION_BATCH units, whose longest reply the schema
    admits still fits the budget. Sized from the repository's own longest identifiers, so it
    holds for any citable set the packet can show: every ID a batch could cite is in ``facts``."""
    units = list(facts.by_kind("inherited_unit"))
    if not units:
        return _RECONCILIATION_BATCH
    budget = max_output_tokens * OUTPUT_CHARS_PER_TOKEN_FLOOR
    sizes = {
        "unit_chars": max(len(json.dumps(unit.id)) for unit in units),
        "disposition_chars": max(len(json.dumps(name)) for name in _DISPOSITIONS),
        "destination_chars": max(len(json.dumps(name)) for name in section_ids()),
        "rationale_chars": _RATIONALE_MAX_CHARS + 2,
        "fact_id_chars": max(len(json.dumps(fact.id)) for fact in facts.facts),
        "citations": RECONCILIATION_FACT_IDS_PER_DISPOSITION,
    }

    def fits(size: int) -> bool:
        return _reply_chars(size, **sizes) <= budget

    size = min(_RECONCILIATION_BATCH, len(units))
    while size > 1 and not fits(size):
        size -= 1
    if not fits(size):
        raise ConfigError(
            f"one unit's longest reply ({_reply_chars(1, **sizes)} characters) exceeds the "
            f"source_reconciliation budget ({budget:.0f} characters); lower "
            "RECONCILIATION_FACT_IDS_PER_DISPOSITION or raise max_output_tokens"
        )
    return size


def units_per_reply(facts: FactsDocument, max_output_tokens: int) -> int:
    """How many dispositions the longest reply the schema admits can hold within
    ``max_output_tokens``: the same bound that sizes a batch, for a caller asking about a different
    budget (the repair of a disposition answers under the repair prompt's, not this job's)."""
    return _batch_size(facts, max_output_tokens)


def reconciliation_batches(
    facts: FactsDocument, max_output_tokens: int
) -> list[tuple[str, list[Fact]]]:
    """Every inherited unit, split into batches in document (ordinal) order - one
    ``(batch_id, units)`` pair per ``source_reconciliation`` call this round makes. A batch holds
    at most _RECONCILIATION_BATCH units, and fewer when its longest reply would not fit
    ``max_output_tokens`` (see _batch_size). No unit is ever dropped.

    Ordinal order, not grouped by ``.section``: a batch boundary may occasionally fall inside one
    heading's own units, but preserves the document's own unit ordering exactly, which
    ``merge_dispositions()`` and every downstream reader already assume - grouping by section
    first would need to interleave document order back in afterward for no real benefit, since
    ``reconcile_checks`` judges each disposition independently of its neighbours anyway.
    """
    units = list(facts.by_kind("inherited_unit"))
    size = _batch_size(facts, max_output_tokens)
    return [
        (f"reconciliation#{index // size + 1}", units[index : index + size])
        for index in range(0, len(units), size)
    ]


def reconciliation_batch_facts(facts: FactsDocument, batch_units: Sequence[Fact]) -> FactsDocument:
    """``facts``, with its own ``inherited_unit`` facts narrowed to exactly ``batch_units``.

    Real bug this closes, found live against Cells-Rust (not assumed): ``core/llm/binding.py``'s
    ``binding_errors`` recomputes its own "every inherited unit expected" set directly from
    ``facts.by_kind("inherited_unit")`` - the whole ``FactsDocument`` passed as the job's own
    ``facts=`` argument - independent of whatever the packet or schema for one particular call
    were scoped to. Passing the same, unscoped ``facts`` for every batch's own call made
    ``binding_errors`` demand full coverage from each individual batch reply, rejecting every
    batch but the last on "no disposition for inherited units: ...". A batch's own call must see -
    and be judged against - only its own units; every other fact kind is untouched, so
    ``bounded_records()`` and every other check reading this document still see the real, whole
    repository.
    """
    keep = frozenset(fact.id for fact in batch_units)
    return FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(fact for fact in facts.facts if fact.kind != "inherited_unit" or fact.id in keep),
        facts.schema_version,
    )


def _packet_fact_records(facts: FactsDocument, manifest: PromptManifest) -> list[dict[str, str]]:
    """The fact records the reconciliation packet shows - one function, so the packet and the
    schema's citable set can never drift apart (the planning schema's own lesson)."""
    kinds = [kind for kind in manifest.packet.fact_kinds if kind != "inherited_unit"]
    return bounded_records(
        facts, kinds, ("SUPPORTED", "CONTRADICTED"), symbol_kinds=DECLARED_SYMBOL_KINDS
    )


def citable_fact_ids(
    facts: FactsDocument,
    manifest: PromptManifest,
    batch_units: Sequence[Fact],
    investigation: Mapping[str, Any],
) -> list[str]:
    """Every ID the job may *write* in this batch, sorted: the packet's own fact records, the
    facts the accepted investigation cites (the prompt lets the job copy those one by one, and
    the investigation travels in the packet, so each is an ID the job can actually see), and this
    batch's own inherited units. Nothing the packet never showed is in it, so an UNRESOLVED fact
    is absent - ``normalize`` adds one by code where a rule calls for it.
    """
    known = {fact.id for fact in facts.facts}
    shown = {record["id"] for record in _packet_fact_records(facts, manifest)}
    cited = {fact_id for fact_id in collect_ids(investigation).fact_ids if fact_id in known}
    return sorted(shown | cited | {fact.id for fact in batch_units})


def reconciliation_schema(
    manifest: LoadedManifest,
    batch_units: Sequence[Fact],
    facts: FactsDocument,
    investigation: Mapping[str, Any],
) -> dict[str, Any]:
    """The reconciliation schema specialised for one batch: its units, and the IDs it may cite.

    Every inherited unit in this batch needs one disposition and no other unit is in this batch,
    which the code knows exactly, so the schema says so rather than letting the job invent a unit
    and be rejected for it. ``fact_ids`` gets the same enum-plus-``maxItems`` treatment as
    ``unit_id``, for the same reason: the IDs a disposition may cite are known here exactly
    (``citable_fact_ids``), so the schema lists them, and no single disposition can legitimately
    cite more distinct facts than exist in its own packet.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    dispositions = schema["properties"]["dispositions"]
    item = dispositions["items"]
    citable = citable_fact_ids(facts, manifest.manifest, batch_units, investigation)
    item["properties"]["destination_section"] = {
        "oneOf": [{"type": "null"}, {"type": "string", "enum": list(section_ids())}]
    }
    if citable:
        item["properties"]["fact_ids"]["items"] = {"type": "string", "enum": citable}
        item["properties"]["fact_ids"]["maxItems"] = min(
            len(citable), RECONCILIATION_FACT_IDS_PER_DISPOSITION
        )
    else:
        item["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
    units = [fact.id for fact in batch_units]
    if units:
        item["properties"]["unit_id"] = {"type": "string", "enum": units}
    dispositions["items"] = {"anyOf": disposition_variants(item, holdable_sections(facts))}
    if not units:
        return schema
    dispositions["maxItems"] = len(units)
    return schema


def reconciliation_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    manifest: PromptManifest,
    batch_units: Sequence[Fact],
) -> dict[str, Any]:
    """One batch's own packet: ``inherited_units`` is exactly ``batch_units``, not every
    inherited unit in the repository. ``facts`` (bounded, non-``inherited_unit`` kinds) is
    shared context every batch needs, already capped by ``bounded_records()``."""
    units = [
        {"id": fact.id, "type": fact.id.rsplit(".", 1)[-1], "text": fact.value}
        for fact in batch_units
    ]
    return {
        "repository": entry.repository,
        "inherited_units": units,
        "facts": _packet_fact_records(facts, manifest),
        "investigation": investigation,
        "sections": _sections_packet(facts),
    }


def _sections_packet(facts: FactsDocument) -> list[dict[str, Any]]:
    """The shell as the job sees it: ``placeable`` is true exactly where a placing disposition may
    send a unit in this repository (``destinations.holdable_sections``), the same set the schema's
    destination enum is cut from. A section the shell lets the LLM write but that cannot hold a
    kept unit here says why in ``unavailable``, so the packet and the decoder never disagree."""
    holdable = set(holdable_sections(facts))
    sections = []
    for record in shell_packet():
        shown = dict(record)
        if record["placeable"] and record["id"] not in holdable:
            shown["unavailable"] = (
                "holds one diagram and nothing else"
                if record["id"] == "at_a_glance"
                else "its condition does not hold at this revision, so the section is not rendered"
            )
        shown["placeable"] = record["id"] in holdable
        sections.append(shown)
    return sections


def merge_dispositions(outputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Every batch's own accepted dispositions, concatenated in batch order into one flat
    document. Simpler than composition's ``merge_units()``: a disposition is never rendered in
    shell order the way an authored unit is, so nothing here needs re-sorting by section - batch
    order already is document order (``reconciliation_batches()``'s own contract)."""
    dispositions: list[dict[str, Any]] = []
    for output in outputs:
        dispositions.extend(output.get("dispositions", []))
    return {"dispositions": dispositions}


def summarize(output: dict[str, Any]) -> Counter[str]:
    return Counter(entry["disposition"] for entry in output.get("dispositions", []))


def write_dispositions(output: dict[str, Any], path: Path) -> str:
    """Write the accepted dispositions as deterministic JSON; returns the SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


# Refusal/repair half, ported later still (2026-10-22, found live): render_readme() produced a
# real README for aspose-3d-foss/Aspose.3D-FOSS-for-Python with a duplicate opening paragraph --
# a VERIFIED_PRESERVE into "opening" (an LLM-authored section, not a deterministic one) that
# coverage_findings()'s own self-audit does not check (its gap-check only fires for
# SUPERSEDE_REDUNDANT or a PLACING disposition into a *deterministic* section). This is exactly
# the gap this module's own earlier docstring predicted placement_errors() would need to close.
# Ports coordinate_neighbor_promises (settles a lead-in/payload pair across batches, after
# merge_dispositions), uncited_omit_candidates + _coverage_errors (the typed, repairable refusal
# messages), unprinted_commands (BC-08 mirror), dangling_pointers (BC-07 mirror, needs the
# just-ported composition/references.py), and placement_errors itself (the job's own checks,
# combined with normalize() as reconcile_checks does in the old repo).


def coordinate_neighbor_promises(
    dispositions: dict[str, Any], facts: FactsDocument
) -> dict[str, Any]:
    """Keep a lead-in and the block it introduces one thing: the same fate and the same section.

    A lead-in (a paragraph or list ending ``:``) is never carried alone and never leaves its
    block behind. Its payload is the next code block, list or table, and the pair is settled from
    both sides, whichever of the two the reconciler got wrong. Runs once, after
    ``merge_dispositions()`` folds every batch into one flat document -- the one point a
    neighbor's own final disposition is visible regardless of which batch produced it.
    """
    units_by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    entries_by_id = {
        str(entry.get("unit_id", "?")): entry for entry in dispositions.get("dispositions", [])
    }
    examples = _example_status(facts)
    for entry in dispositions.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        if unit.rsplit(".", 1)[-1] not in {"paragraph", "list"}:
            continue
        unit_fact = units_by_id.get(unit)
        if unit_fact is None or not unit_fact.value.rstrip().endswith(":"):
            continue
        payload = _payload_of(unit, units_by_id)
        neighbor = entries_by_id.get(payload) if payload is not None else None
        if payload is None or neighbor is None:
            continue
        _settle_lead_in(entry, unit_fact, neighbor, payload, examples)
    return dispositions


def _settle_lead_in(
    entry: dict[str, Any],
    lead: Fact,
    neighbor: dict[str, Any],
    payload: str,
    examples: Mapping[str, tuple[str, str]],
) -> None:
    """One lead-in settled against its payload's disposition (``coordinate_neighbor_promises``)."""
    state = entry.get("disposition")
    block = neighbor.get("disposition")
    if block == "OMIT_UNSUPPORTED":
        if state in PLACING or state == "DEFER_UNRESOLVED":
            _omit_lead_in(entry, neighbor, payload)
        return
    if block == "DEFER_UNRESOLVED":
        if state in PLACING:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
        return
    kind = _unit_kind(payload)
    target = neighbor.get("destination_section")
    verified_example = kind == "code_block" and examples.get(payload, ("", ""))[0] == "SUPPORTED"
    if state == "DEFER_UNRESOLVED":
        if verified_example and target in _EXAMPLE_SECTIONS and block in _KEPT_OR_COVERED:
            _supersede_lead_in(entry, str(target))
        elif (
            kind == "code_block"
            and block in PLACING
            and target in placeable_section_ids()
            and _bare_lead_in(lead.value)
        ):
            entry["disposition"] = "VERIFIED_PRESERVE"
            entry["destination_section"] = target
            entry["rationale"] = _LEAD_IN_KEPT_RATIONALE
        state = entry.get("disposition")
    if state not in PLACING:
        return
    destination = entry.get("destination_section")
    if verified_example:
        section = next(
            (s for s in (destination, target) if s in _EXAMPLE_SECTIONS),
            None,
        )
        if section is not None and block in _KEPT_OR_COVERED:
            _supersede_lead_in(entry, section)
            return
    if (
        kind == "list"
        and _unit_kind(str(entry.get("unit_id"))) == "paragraph"
        and destination in _CARRY_SECTIONS
        and block in PLACING
        and target == destination
    ):
        _supersede_lead_in(entry, str(destination))
        return
    if block in PLACING and target in placeable_section_ids() and target != destination:
        entry["destination_section"] = target
        entry["rationale"] = _LEAD_IN_FOLLOWED_RATIONALE


def _omit_lead_in(entry: dict[str, Any], neighbor: Mapping[str, Any], payload: str) -> None:
    """Omit a lead-in with the block it introduces. An omission names what shows the claim
    unsupported (``placement_errors``' own rule for prose), which for a lead-in is its block: the
    block's own citations, or the block itself when it cited none."""
    entry["disposition"] = "OMIT_UNSUPPORTED"
    entry["destination_section"] = None
    entry["fact_ids"] = sorted(set(neighbor.get("fact_ids") or [])) or [payload]
    entry["rationale"] = _LEAD_IN_OMITTED_RATIONALE.format(block=payload)


_KEPT_OR_COVERED = PLACING | {"SUPERSEDE_REDUNDANT"}
_LEAD_IN_OMITTED_RATIONALE = (
    "Lead-in of the omitted block that follows ({block}): withheld with it, never alone."
)
_LEAD_IN_KEPT_RATIONALE = "Lead-in of the kept block that follows: placed with it, never alone."
_LEAD_IN_FOLLOWED_RATIONALE = "Lead-in of the block that follows: kept in its section, with it."
_BARE_LEAD_IN_WORDS = 14
_CLAIM_WORDS = re.compile(
    r"\b(?:install\w*|publish\w*|releas\w*|version\w*|registry|pypi|npm|nuget|maven|crates?|"
    r"cargo|pip|supports?|requires?|compatible|works?)\b",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"[.!?]\s+\S")


def _bare_lead_in(text: str) -> bool:
    """Whether a colon-ending sentence only introduces what follows (``_CLAIM_WORDS``)."""
    body = " ".join(text.split()).rstrip(":").strip()
    return (
        bool(body)
        and len(body.split()) <= _BARE_LEAD_IN_WORDS
        and not any(mark in body for mark in ("`", "](", "://"))
        and not any(character.isdigit() for character in body)
        and _SENTENCE_BREAK.search(body) is None
        and _CLAIM_WORDS.search(body) is None
    )


_PAYLOAD_KINDS = frozenset({"code_block", "list", "table"})
_EXAMPLE_SECTIONS = frozenset({"quick_start", "additional_examples"})
_LEAD_IN_RATIONALE = "Lead-in of the block that follows: carried together with it, never alone."


def _payload_of(unit_id: str, units: Mapping[str, Fact]) -> str | None:
    """The block that immediately follows ``unit_id`` in the source README when it is the kind of
    block a colon introduces (a code block, a list or a table), else ``None``."""
    ordinal = _unit_ordinal(unit_id)
    if ordinal is None:
        return None
    following = sorted(
        (other, nxt)
        for other in units
        if (nxt := _unit_ordinal(other)) is not None and nxt > ordinal
    )
    if not following:
        return None
    first = min(following, key=lambda pair: (pair[1], pair[0]))
    return first[0] if _unit_kind(first[0]) in _PAYLOAD_KINDS else None


def lead_in_of(unit_id: str, units: Mapping[str, Fact]) -> str | None:
    """The sentence that introduces ``unit_id`` in the source README - a paragraph or list ending
    ``:`` right before a code block, list or table - or ``None``. The inverse of ``_payload_of``."""
    if _unit_kind(unit_id) not in _PAYLOAD_KINDS:
        return None
    ordinal = _unit_ordinal(unit_id)
    if ordinal is None:
        return None
    before = [
        (other_ordinal, other)
        for other in units
        if (other_ordinal := _unit_ordinal(other)) is not None and other_ordinal < ordinal
    ]
    if not before:
        return None
    nearest = max(ordinal_ for ordinal_, _ in before)
    for _, candidate in sorted((o, u) for o, u in before if o == nearest):
        if _unit_kind(candidate) in {"paragraph", "list"} and units[
            candidate
        ].value.rstrip().endswith(":"):
            return candidate
    return None


def _supersede_lead_in(entry: dict[str, Any], destination: str) -> None:
    entry["disposition"] = "SUPERSEDE_REDUNDANT"
    entry["destination_section"] = destination
    entry["rationale"] = _LEAD_IN_RATIONALE


UNCITED_PROSE_OMIT = "uncited_prose_omit"
_PROSE_UNIT_KINDS = frozenset({"paragraph", "list"})
UNCITED_REDUNDANT_DIAGRAM = "uncited_redundant_diagram"
# UNCITED_PROSE_OMIT's own kind set, local to placement_errors: a code_block is substantive
# content too (measured live, aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 40730367161 -- a
# CMake add_subdirectory() snippet OMIT_UNSUPPORTED with empty fact_ids and a "superseded by the
# installation section" rationale, which is a SUPERSEDE_REDUNDANT claim wearing the wrong
# disposition, uncited either way). Kept separate from the shared _PROSE_UNIT_KINDS, which
# _omission_gap above also reads for a different purpose (whether to suggest spelled-but-uncited
# facts); widening that shared constant would have silently also stopped suggesting candidates
# for an uncited code_block omission, the opposite of what this fix wants.
_UNCITED_OMIT_KINDS = _PROSE_UNIT_KINDS | frozenset({"code_block"})


def uncited_omit_candidates(unit_text: str, facts: FactsDocument) -> list[str]:
    """SUPPORTED fact IDs the refused unit's own text already spells, sorted - a deterministic
    candidate list the ``uncited_prose_omit`` re-ask can name, so the model has somewhere
    concrete to look rather than only being told to "try harder"."""
    return sorted(inherited_unit_named_symbols(facts, unit_text))


_OMISSION_ACTION = {
    OMIT_UNRESOLVED_EXAMPLE: "Choose DEFER_UNRESOLVED: an example the facts neither support nor "
    "contradict is withheld and listed, never called unsupported",
    OMIT_VERIFIED_EXAMPLE: "Supersede it into quick_start or additional_examples (the plan "
    "renders every verified example there) or place it; do not omit a verified example",
    OMIT_NAMES_SUPPORTED: "Cite the facts that support it and place it, or choose "
    "DEFER_UNRESOLVED if no fact settles its claim",
    OMIT_VERSION_SKEW: "The warning is the maintainers' own and true: keep it "
    "(VERIFIED_PRESERVE or VERIFIED_MOVE into scope_limitations, where the limits of the "
    "registry release belong) so a reader who installs from the registry is told what that "
    "release lacks; do not omit it",
}
_QUOTE_LIMIT = 600


def _coverage_errors(
    gaps: Sequence[CoverageGap],
    unit_text: Mapping[str, str],
    holdable: Sequence[str],
    nearest: Mapping[str, str | None] | None = None,
) -> list[str]:
    """One typed, repairable refusal per disposition that claims more than the stage can prove,
    quoting the unit's exact text and naming the sections that can hold it, nearest first."""
    errors: list[str] = []
    for gap in gaps:
        kind = _unit_kind(gap.unit_id).replace("_", " ")
        text = json.dumps(unit_text.get(gap.unit_id, "(text not in the facts)"), ensure_ascii=False)
        if len(text) > _QUOTE_LIMIT:
            text = text[:_QUOTE_LIMIT] + "..."
        if gap.disposition == "OMIT_UNSUPPORTED":
            errors.append(
                f"{gap.unit_id}: {SUPPORTED_OMISSION}: OMIT_UNSUPPORTED claims no fact supports "
                f"this {kind}, but {gap.detail}. {_OMISSION_ACTION[gap.reason]}; the unit's exact "
                f"text is {text}"
            )
            continue
        home = (nearest or {}).get(gap.unit_id)
        advice = f" The nearest section that can hold it is {home}." if home is not None else ""
        errors.append(
            f"{gap.unit_id}: {UNCOVERED_SUPERSESSION}: {gap.disposition} treats "
            f"{gap.destination or 'no section'} as carrying this {kind}, but {gap.detail}. A unit "
            "is superseded only when something that renders takes its place: place it "
            "(VERIFIED_PRESERVE or VERIFIED_MOVE) into a section that can hold it "
            f"({', '.join(holdable)}) or choose DEFER_UNRESOLVED.{advice} The unit's exact text "
            f"is {text}"
        )
    return errors


_PRINTED_AS_WRITTEN = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
_COMMAND_LINE = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip3?|python3?(?:\s+-m)?|npm|npx|yarn|pnpm|dotnet|mvn|gradle|go|"
    r"cargo|cmake|make|git)\b(?!-)",
    re.IGNORECASE,
)
UNPRINTED_COMMAND = "unprinted_command"


def unprinted_commands(text: str, facts: FactsDocument) -> list[str]:
    """The command lines of a code block that no verified section prints: not the Installation
    row's lines (``_rendered_commands``) and not a build or test command the repository records.
    BC-08 holds every command of a kept block to the finished README, so a block that is
    corrected or rewritten (and so never printed as written) must have none."""
    printed = set(_rendered_commands(facts))
    for fact in facts.by_kind("build_test_asset"):
        if fact.polarity == "SUPPORTED":
            printed.update(_command_lines(fact.value))
    return [
        raw.strip()
        for raw in text.splitlines()
        if _COMMAND_LINE.match(raw) and (_command_lines(raw) or [""])[0] not in printed
    ]


_POINTER_REFERENTS = frozenset({"paragraph", "list", "table", "blockquote"})
_POINTER_BATCH_TAIL = 3
_POINTS_UP = re.compile(r"precedes it|ends with a colon|' section this README does not have")
_NAMED_SECTION = re.compile(r"refers to a '([^']+)' section this README does not have")
_TOP_HEADING = re.compile(r"^#{1,2}\s+(.*?)\s*#*\s*$")


def _unanswerable_section(reason: str, former: Collection[str]) -> bool:
    """Whether a "refers to a 'N' section this README does not have" reason names a section no
    heading can answer: one pointed at as "below" (kept units print after their section's
    content, and a heading is the shell's), or one the old README had at the top level and the
    shell does not print (``former``)."""
    match = _NAMED_SECTION.search(reason)
    if match is None:
        return False
    name = match.group(1)
    return name.lower().endswith((" below", " above")) or heading_slug(name) in former


def dangling_pointers(
    output: Mapping[str, Any], facts: FactsDocument
) -> list[tuple[str, str, str]]:
    """``(unit_id, sentence, reason)`` for each kept-as-written paragraph or list that points
    forward ("the table below", "the following example") at something no unit kept after it in
    the same section provides (BC-07, composition/references.py)."""
    inherited = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    tail = set(list(inherited)[-_POINTER_BATCH_TAIL:])
    commands = command_block_units(facts)
    placeable = placeable_section_ids()
    shell_slugs = frozenset(
        heading_slug(section.heading) for section in SEMANTIC_SHELL if section.heading
    )
    printed = shell_slugs | {heading_slug(title) for title in SUBSECTION_HEADINGS}
    former = {
        heading_slug(match.group(1))
        for fact in inherited.values()
        if fact.id.endswith(".heading") and (match := _TOP_HEADING.match(fact.value.strip()))
    } - printed
    kept: dict[str, list[tuple[str, str]]] = {}
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        destination = entry.get("destination_section")
        fact = inherited.get(unit)
        if (
            fact is None
            or entry.get("disposition") not in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
            or destination not in placeable
        ):
            continue
        if _unit_kind(unit) in _POINTER_REFERENTS or unit in commands:
            text = resolve_intra_document_anchors(fact.value, shell_slugs)
            kept.setdefault(str(destination), []).append((unit, text))
    found: list[tuple[str, str, str]] = []
    for destination, units in kept.items():
        document = "\n\n".join([f"## {destination}", *(text.strip("\n") for _, text in units)])
        for reference in dangling_references(document):
            reasons = [
                reason
                for reason in reference.reason.split("; ")
                if not _POINTS_UP.search(reason) or _unanswerable_section(reason, former)
            ]
            if not reasons:
                continue
            sentence = " ".join(reference.sentence.split())
            owner = next(
                (
                    unit_id
                    for unit_id, text in units
                    if unit_id not in tail
                    and _unit_kind(unit_id) in {"paragraph", "list"}
                    and sentence in " ".join(text.split())
                ),
                None,
            )
            if owner is not None:
                found.append((owner, sentence, "; ".join(reasons)))
    return found


def placement_errors(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """Why the dispositions may not be used, beyond schema and binding; empty when they hold.

    An OMIT_UNSUPPORTED on a paragraph or list must cite at least one fact ID as its reason (the
    facts that show the claim unsupported), or be placed instead. When the unit's own text
    already spells a SUPPORTED fact's identifier, the refusal also names that fact ID as a
    candidate (``uncited_omit_candidates``) - the model still decides whether it truly supports
    the claim; this never assigns a disposition on its own.
    """
    placeable = placeable_section_ids()
    holdable = holdable_sections(facts)
    contradicted = contradicted_code_units(facts)
    commands = command_block_units(facts)
    unpublished = unpublished_registry_blocks(facts)
    inherited = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    unit_text = {unit_id: fact.value for unit_id, fact in inherited.items()}
    build_facts = sorted(
        fact.id
        for fact in facts.facts
        if fact.kind in {"build_test_asset", "install_command"} and fact.polarity == "SUPPORTED"
    )
    errors: list[str] = []
    for entry in output.get("dispositions", []):
        unit = entry.get("unit_id", "?")
        disposition = entry.get("disposition")
        destination = entry.get("destination_section")
        cited = entry.get("fact_ids") or []
        if (
            disposition == "OMIT_UNSUPPORTED"
            and not cited
            and unit.rsplit(".", 1)[-1] in _UNCITED_OMIT_KINDS
        ):
            kind = unit.rsplit(".", 1)[-1]
            raw_text = unit_text.get(unit, "(text not in the facts)")
            text = json.dumps(raw_text, ensure_ascii=False)
            candidates = uncited_omit_candidates(raw_text, facts)
            candidate_clause = (
                " This unit's own text already spells these SUPPORTED facts: "
                f"{', '.join(candidates)}. Cite whichever of them actually support the claim "
                "(SUPERSEDE_REDUNDANT or CORRECT_WITH_EVIDENCE), or OMIT_UNSUPPORTED with a "
                "cited reason if none of them truly apply."
                if candidates
                else ""
            )
            errors.append(
                f"{unit}: {UNCITED_PROSE_OMIT}: OMIT_UNSUPPORTED on a {kind} needs at least one "
                "fact ID that shows the claim unsupported, or the unit must be placed in a section "
                f"the shell can hold; the unit's exact text is {text}.{candidate_clause} Cite the "
                "supporting fact IDs or place the unit; do not omit it without a cited reason"
            )
        if (
            disposition == "SUPERSEDE_REDUNDANT"
            and not cited
            and unit.rsplit(".", 1)[-1] == "code_block"
        ):
            # Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Java, hosted run
            # 40730382891): a live diagram code block was correctly superseded by the renderer's
            # own at_a_glance diagram, but cited no fact, so independent_reviewer.py's own
            # accounting check (which requires a citation from every ACCOUNTING_DISPOSITIONS kind,
            # not only OMIT_UNSUPPORTED -- the earlier badge_row disposition already cites its
            # license/link_target facts correctly, proving a model can) never counted it as
            # accounted for and reported it as live content lost three stages later. SUPERSEDE_
            # REDUNDANT on prose already escapes this (a heading or a short lead-in rarely has an
            # independent fact of its own); a diagram is substantial content making its own claim
            # about the product's shape, so it gets the same citation requirement as an omission.
            errors.append(
                f"{unit}: {UNCITED_REDUNDANT_DIAGRAM}: SUPERSEDE_REDUNDANT on a code_block needs "
                "at least one fact ID showing what the destination section regenerates it from "
                "(the same facts that section's own content is built from); an empty fact_ids "
                "leaves the supersession unaccounted for later, as if the content had simply "
                "vanished"
            )
        if (
            disposition == "OMIT_UNSUPPORTED"
            and unit in commands
            and build_facts
            and unit not in unpublished
            and not _omits_contradicted_command(entry, unit_text.get(unit, ""), facts)
        ):
            errors.append(
                f"{unit}: a command block is never OMIT_UNSUPPORTED while build or install "
                f"facts exist ({', '.join(build_facts)}); choose VERIFIED_PRESERVE into "
                "development_testing, or SUPERSEDE_REDUNDANT by installation for an install "
                "command"
            )
        if disposition in PLACING:
            if destination not in placeable:
                errors.append(
                    f"{unit}: {disposition} needs a destination the shell can hold "
                    f"({', '.join(holdable)}); got {destination!r}"
                )
            if unit in contradicted:
                errors.append(f"{unit}: its example is CONTRADICTED and cannot be placed")
        elif disposition == "SUPERSEDE_REDUNDANT":
            if destination is None and not cited:
                errors.append(
                    f"{unit}: SUPERSEDE_REDUNDANT names the section whose content renders or "
                    "covers the unit in destination_section, or cites at least one fact ID"
                )
        elif destination is not None:
            errors.append(f"{unit}: {disposition} takes no destination; got {destination!r}")
        if disposition == "CORRECT_WITH_EVIDENCE" and not cited:
            errors.append(f"{unit}: CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence")
    pointers: dict[str, list[str]] = {}
    for unit, sentence, reason in dangling_pointers(output, facts):
        pointers.setdefault(unit, []).append(f"{json.dumps(sentence, ensure_ascii=False)} {reason}")
    for unit, said in pointers.items():
        kept = next(e for e in output.get("dispositions", []) if e.get("unit_id") == unit)
        errors.append(
            f"{unit}: {DANGLING_POINTER}: {kept.get('disposition')} keeps it as written in "
            f"{kept.get('destination_section')}, but its sentence "
            f"{'; and '.join(said)[:_QUOTE_LIMIT]}. Kept units print after the section's own "
            "content, so a pointer to what follows is answered only by a unit kept right after it "
            "in the same section: keep that unit there too, or choose VERIFIED_REWRITE (the "
            "wording is re-authored from facts, without the pointer), or OMIT_UNSUPPORTED citing "
            "the fact that shows the claim unsupported"
        )
    verified_blocks = _example_status(facts)
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        if (
            entry.get("disposition") not in {"CORRECT_WITH_EVIDENCE", "VERIFIED_REWRITE"}
            or not unit.endswith(".code_block")
            or unit in verified_blocks
            or unit not in inherited
        ):
            continue
        unprinted = unprinted_commands(unit_text[unit], facts)
        if unprinted:
            keep = (
                "keep it as written (VERIFIED_PRESERVE or VERIFIED_MOVE into a section that can "
                "hold it), or SUPERSEDE_REDUNDANT by installation if the Installation row prints it"
                if unit in commands and build_facts
                else "keep it as written (VERIFIED_PRESERVE or VERIFIED_MOVE), or withhold it "
                "(OMIT_UNSUPPORTED citing the fact that shows it unsupported, or DEFER_UNRESOLVED)"
            )
            errors.append(
                f"{unit}: {UNPRINTED_COMMAND}: {entry.get('disposition')} edits a code block the "
                "README prints only as written, and BC-08 holds every command in it to the "
                f"finished README, where no verified section prints {', '.join(unprinted[:3])!r}. "
                f"Choose: {keep}"
            )
    unfolded = [
        gap
        for gap in coverage_findings(output, facts)
        if not (gap.disposition == "SUPERSEDE_REDUNDANT" and gap.destination in placeable)
        and gap.reason != OMIT_UNRESOLVED_EXAMPLE
    ]
    root = root_heading(list(inherited.values()))
    nearest = {
        gap.unit_id: nearest_holdable(
            gap.unit_id, source_heading(inherited.get(gap.unit_id)), holdable, root
        )
        for gap in unfolded
    }
    errors.extend(_coverage_errors(unfolded, unit_text, holdable, nearest))
    return errors


def reconcile_checks(
    output: dict[str, Any], facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> list[str]:
    """The job's own checks for the runner: normalise, then judge what remains."""
    return normalize(output, facts, policy) + placement_errors(output, facts)
