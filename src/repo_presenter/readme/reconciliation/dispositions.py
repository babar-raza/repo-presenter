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

**Deferred** (not ported, with the reason): the S4 job-wiring half -- ``reconciliation_packet``/
``reconciliation_schema``/``reconciliation_batches``/``reconciliation_narrowing``/
``merge_dispositions`` (builds the actual LLM packet/schema/narrowed-ask for ``source_
reconciliation``; needs ``core.llm.prompts.PromptManifest`` plumbing this repository's own prompt
content has not been authored for yet, mirroring ``core/llm/prompts.py``'s own module docstring);
``placement_errors``, ``dangling_pointers``, ``coordinate_neighbor_promises``, ``recover_uncited_
prose_omits`` and their own supporting functions (the refusal/repair half that reacts to what
``coverage_findings`` reports, rather than the self-audit itself -- these also need ``composition/
references.py``'s ``dangling_references``, not ported). This split follows the manifest's own
instruction precisely: the self-audit (what counts as provable) travels with ``normalize`` intact;
the separate refusal-message/repair layer built on top of it does not.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from markdown_it import MarkdownIt

from repo_presenter.core.ecosystems import EcosystemSpec, spec_for
from repo_presenter.core.errors import ConfigError
from repo_presenter.core.facts import REGISTRY_COMMAND_ATTRIBUTE, Fact, FactsDocument
from repo_presenter.core.package_registry import DISTRIBUTION_FACT_PREFIX, PUBLISHED_VERSION_FACT_ID
from repo_presenter.readme.composition.authoring import (
    _CARRY_SECTIONS,
    edition_substitutes,
    inherited_unit_named_symbols,
)
from repo_presenter.readme.composition.components.shell import placeable_section_ids, section_ids
from repo_presenter.readme.composition.coverage import unversioned
from repo_presenter.readme.composition.placement import renderer_fact_ids
from repo_presenter.readme.composition.planning import section_conditions
from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy
from repo_presenter.readme.composition.source_topics import path_topic, root_heading, source_heading
from repo_presenter.readme.evidence.facts.links import extract_links
from repo_presenter.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
from repo_presenter.readme.evidence.facts.registry_lag import REGISTRY_LAG_FACT_ID
from repo_presenter.readme.reconciliation.destinations import holdable_sections, rehomed

DISPOSITIONS_FILENAME = "dispositions.json"
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


_API_ROW = re.compile(r"^\| `([^`]+)` \|", re.M)


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
    _prune_incidental_coverage(output, coverage)
    return errors
