"""Stage S7: the deterministic renderer - the Markdown document from shell, plan, units, facts.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/renderer.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). Confirmed pure: no LLM call anywhere in this module, as the task brief
required. The LLM never writes Markdown. This module owns every heading, badge, navigation link,
command, code block, details block, diagram, link, and license statement, emits the plan's
included sections in shell order, drops each authored unit into its slot with fact-value
identifiers wrapped in code spans, and places every inherited unit the reconciliation preserved or
moved. The result is a pure function of its inputs, so a rerun on the same inputs is
byte-identical.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import printed_example
from repo_presenter.core.facts import (
    DOCUMENTED_SOURCE_BASIS,
    SOURCE_BASIS_ATTRIBUTE,
    Fact,
    FactsDocument,
)
from repo_presenter.core.package_registry import DISTRIBUTION_FACT_PREFIX, PUBLISHED_VERSION_FACT_ID
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import (
    allowed_identifiers,
    canonical_abbreviations,
    cited_inherited_identifiers,
    identifier_allowed,
    identifier_tokens,
    surface_members,
    verified_members,
)
from repo_presenter.readme.composition.components.ecosystems import (
    DISTRIBUTION_REGISTRY_NAMES,
    REGISTRY_NAMES,
    host_names,
)
from repo_presenter.readme.composition.components.glance import draw_at_a_glance
from repo_presenter.readme.composition.components.identity import (
    elide_noncanonical,
    product_name,
    product_name_tokens,
)
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL, Section
from repo_presenter.readme.composition.components.terminology import LOWER_WORD, to_title_case
from repo_presenter.readme.composition.coverage import Destinations
from repo_presenter.readme.composition.placement import (
    Placement,
    api_reference_hub_methods,
    placed_texts,
    placements,
    renders_verbatim,
)
from repo_presenter.readme.composition.retained_examples import (
    RetainedBlock,
    active_retained,
    block_lines,
)
from repo_presenter.readme.evidence.facts.assets import CI_BADGE_FACT_ID
from repo_presenter.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    CI_MATRIX_FACT_ID,
    PRECONDITION_ATTRIBUTE,
    RELEASE_WORKFLOW_FACT_ID,
    TEST_COMMAND_FACT_ID,
    CommandForm,
    command_form,
    commands_in_text,
    matrix_axes,
)
from repo_presenter.readme.evidence.facts.links import link_text
from repo_presenter.readme.evidence.facts.product_pages import banner_target, enterprise_target

RENDERER_VERSION = "34"
ADDITIONAL_EXAMPLES_SUMMARY = "View Additional Examples"
API_SURFACE_SUMMARY = "View the Complete Public API Surface"
README_FILENAME = "README.md"
PATCH_FILENAME = "README.patch"
__all__ = ["renders_verbatim"]  # re-exported for the validator and the tests
_WORD = re.compile(r"\b[A-Z][A-Za-z0-9]*\b")
_EXTENSION = re.compile(r"(?<![\w`.])\.[a-z0-9]{2,}\b")
_SLUG_STRIP = re.compile(r"[^\w\- ]")
_CODE_SPAN_RUN = re.compile(r"`[^`\n]*`")
_MIT_PROSE = (
    "This project is licensed under the [MIT License]({file}). The MIT License permits use, "
    "copying, modification, distribution, sublicensing, and commercial use, provided its "
    "copyright and permission notice are retained. The software is provided without warranty."
)
_GENERIC_PROSE = "This project is licensed under the [{spdx}]({file})."
_MIT_DECLARED_PROSE = (
    "This project is licensed under the MIT License, as declared in `{manifest}`; no license file "
    "is present in the repository. The MIT License permits use, copying, modification, "
    "distribution, sublicensing, and commercial use, provided its copyright and permission notice "
    "are retained. The software is provided without warranty."
)
_GENERIC_DECLARED_PROSE = (
    "This project is licensed under the {spdx}, as declared in `{manifest}`; no license file is "
    "present in the repository."
)
_EXTRA = re.compile(r"extra '([^']+)'")
_FLOOR = re.compile(r">=\s*(\d+(?:\.\d+)*)")
_VERSION_NUMBER = re.compile(r"\d+(?:\.\d+)*")
_FILE_COUNT = re.compile(r"(\d+) files")


class RenderContext:
    """Everything the renderer reads, indexed once."""

    def __init__(
        self,
        entry: RegistryEntry,
        facts: FactsDocument,
        plan: dict[str, Any],
        units: dict[str, Any],
        dispositions: dict[str, Any],
    ) -> None:
        self.entry = entry
        self.facts = facts
        self.plan = plan
        self.spec = spec_for(entry.ecosystem)
        self.name = product_name(entry)
        self.by_id: dict[str, Fact] = {fact.id: fact for fact in facts.facts}
        self.planned: frozenset[str] = frozenset(
            str(item.get("section_id"))
            for item in plan.get("sections", [])
            if item.get("include")
        )
        self.retained: dict[str, list[RetainedBlock]] = {}
        for block in active_retained(facts, dispositions):
            self.retained.setdefault(block.section, []).append(block)
        self.included: list[Section] = [
            section
            for section in SEMANTIC_SHELL
            if section.id in self.planned or section.id in self.retained
        ]
        self.rendered_ids: frozenset[str] | None = None
        self.units: dict[tuple[str, str], str] = {
            (unit["section"], unit["slot"]): unit["text"] for unit in units.get("units", [])
        }
        self.unit_fact_ids: dict[tuple[str, str], list[str]] = {
            (unit["section"], unit["slot"]): unit.get("fact_ids", [])
            for unit in units.get("units", [])
        }
        self.dispositions = dispositions
        self._unplaced = False
        self._placements: list[Placement] | None = None
        self._placed: dict[str, list[str]] | None = None
        self.allowed = allowed_identifiers(facts, self.name)
        self.members = verified_members(facts)
        self.methods = surface_members(facts)
        self.name_tokens = product_name_tokens(self.name)
        self.hosts = host_names(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED")
        self.abbreviations = canonical_abbreviations(facts)
        self.symbol_names: frozenset[str] = frozenset(
            fact.value.rsplit(".", 1)[-1]
            for fact in facts.by_kind("public_symbol")
            if fact.polarity == "SUPPORTED"
            and fact.evidence
            and any(
                f"; {kind};" in (fact.evidence[0].detail or "")
                for kind in ("class", "enum", "function")
            )
        )

    @property
    def placements(self) -> list[Placement]:
        """Every kept unit's placement, decided once by ``placement.placements`` on the
        document as it renders with no kept unit placed."""
        if self._placements is None:
            self._placements = placements(
                self.plan,
                self.dispositions,
                self.facts,
                self.entry.ecosystem,
                self.unplaced_destinations,
            )
        return self._placements

    @property
    def placed(self) -> dict[str, list[str]]:
        """The verbatim text each section places; empty while the unplaced document is built."""
        if self._unplaced:
            return {}
        if self._placed is None:
            self._placed = placed_texts(self.placements)
        return self._placed

    def unplaced_destinations(self) -> Destinations:
        """The document as it renders with no kept unit placed."""
        sections = {section.id: section for section in self.included}

        def unplaced(section_id: str) -> str:
            section = sections.get(section_id)
            if section is None:
                return ""
            remembered, self._unplaced, self.rendered_ids = self.rendered_ids, True, None
            try:
                body = "\n".join(_section_body(self, section))
            finally:
                self._unplaced, self.rendered_ids = False, remembered
            return (
                body.split(ENTERPRISE_SENTENCE_LEAD, 1)[0]
                if section_id == "scope_limitations"
                else body
            )

        return Destinations(unplaced, tuple(sections))

    def canonical(self, text: str) -> str:
        """``text`` with every known abbreviation raised to the spelling the document uses."""
        return LOWER_WORD.sub(
            lambda match: self.abbreviations.get(match.group(0), match.group(0)), text
        )

    def fact(self, fact_id: str) -> Fact | None:
        return self.by_id.get(fact_id)

    def supported(self, kind: str) -> list[Fact]:
        return [f for f in self.facts.by_kind(kind) if f.polarity == "SUPPORTED"]  # type: ignore[arg-type]

    def unit(self, section: str, slot: str) -> str:
        fact_ids = (
            self.unit_fact_ids.get((section, slot), []) if section == "scope_limitations" else []
        )
        return self.prose(self.units.get((section, slot), ""), fact_ids)

    def prose(self, text: str, fact_ids: Iterable[str] = ()) -> str:
        """Authored text with every fact-value identifier wrapped in a code span."""
        text = self.canonical(text)
        cited = cited_inherited_identifiers(self.facts, fact_ids)
        tokens = set(identifier_tokens(text))
        tokens.update(word for word in _WORD.findall(text) if word in self.symbol_names)
        tokens.update(ext for ext in _EXTENSION.findall(text) if ext in self.allowed)
        wrapped = {
            token
            for token in tokens
            if not (token in self.name_tokens or token in REGISTRY_NAMES.values())
            and token not in self.hosts
            and (
                token in self.symbol_names
                or token in cited
                or identifier_allowed(token, self.allowed, self.members, self.methods)
            )
        }
        paths = [
            value
            for value in self.allowed
            if "/" in value
            and " " not in value
            and "://" not in value
            and value in text
            and any(token in value for token in wrapped)
            and re.search(rf"(?<![\w/.-]){re.escape(value)}(?![\w/-]|\.\w)", text)
        ]
        wrapped.update(paths)
        if not wrapped:
            return text
        pattern = "|".join(re.escape(token) for token in sorted(wrapped, key=len, reverse=True))
        # Boundaries exclude a colon on either side, the same way a dot already is on the left:
        # a Rust/C++ `Namespace::Member` compound where only one half is a known token (measured
        # live on aspose-cells-foss/Aspose.Cells-FOSS-for-Rust's independent review, finding F01 --
        # "CellsError" alone is a registered public_symbol, "Unsupported" is not, so the old
        # boundary let "CellsError" match with "::Unsupported" right behind it, wrapping only the
        # known half and leaving a broken code span: `` `CellsError`::Unsupported ``) must render
        # fully plain rather than half-wrapped, the same choice already made for a dotted compound.
        compiled = re.compile(rf"(?<![`\w.:])(?:{pattern})(\(\))?(?![`\w:])")
        pieces = re.split(r"(`[^`\n]*`)", text)
        return "".join(
            piece if index % 2 else compiled.sub(lambda m: f"`{m.group(0)}`", piece)
            for index, piece in enumerate(pieces)
        )


def _wrap_outside_spans(text: str, token: str) -> str:
    """``text`` with each whole-word ``token`` (and a call's trailing ``()``) in a code span,
    except where it already sits inside one."""
    spans = [match.span() for match in _CODE_SPAN_RUN.finditer(text)]

    def wrap(match: re.Match[str]) -> str:
        inside = any(start <= match.start() < end for start, end in spans)
        return match.group(0) if inside else f"`{match.group(0)}`"

    return re.sub(rf"(?<![`\w.]){re.escape(token)}(\(\))?(?![`\w])", wrap, text)


def anchor(heading: str) -> str:
    """GitHub's anchor form of a heading."""
    return _SLUG_STRIP.sub("", heading.strip().lower()).replace(" ", "-")


BADGE_ORDER: tuple[str, ...] = ("package", "runtime", "build", "license", "contributors")


def contributors_target(repository: str) -> str:
    """The contributors graph a contributors badge links to."""
    return f"https://github.com/{repository}/graphs/contributors"


def ci_badge(fact: Fact) -> str:
    """The build-status badge for the verified workflow ``fact`` records."""
    branch = (fact.attributes or {}).get("branch")
    query = f"?branch={quote(str(branch), safe='')}" if branch else ""
    return f"[![Build Status]({fact.value}/badge.svg{query})]({fact.value})"


def badge_slots(context: RenderContext) -> list[tuple[str, str]]:
    """Every badge the verified facts support, as ``(slot, markdown)`` in ``BADGE_ORDER``."""
    repo = context.entry.repository
    badges: list[tuple[str, str]] = []
    spec = context.spec
    install = context.fact(spec.install_fact_id)
    package = context.fact("package:name")
    source_kind = install is not None and (install.attributes or {}).get("install_kind") in (
        "source",
        "source_checkout",
    )
    if (
        install is not None
        and install.polarity == "SUPPORTED"
        and not source_kind
        and package is not None
    ):
        badge = spec.badge(package.value)
        if badge:
            badges.append(("package", badge))
    floor = context.fact(spec.floor_fact_id) if spec.floor_fact_id else None
    if floor is not None and floor.polarity == "SUPPORTED":
        runtime = spec.runtime_badge(floor.value)
        if runtime:
            badges.append(("runtime", runtime))
    ci = context.fact(CI_BADGE_FACT_ID)
    if ci is not None and ci.polarity == "SUPPORTED":
        badges.append(("build", ci_badge(ci)))
    spdx = context.fact("license:spdx")
    license_file = context.fact("license:file")
    if spdx is not None and license_file is not None and spdx.polarity == "SUPPORTED":
        badge = quote(spdx.value, safe="")
        badges.append(
            (
                "license",
                f"[![License: {spdx.value}](https://img.shields.io/badge/License-{badge}-blue.svg)]"
                f"({license_file.value})",
            )
        )
    target = contributors_target(repo).casefold()
    if any(
        fact.polarity == "SUPPORTED" and fact.value.casefold() == target
        for fact in context.facts.by_kind("link_target")
    ):
        badges.append(
            (
                "contributors",
                f"[![Contributors](https://img.shields.io/github/contributors/{repo})]"
                f"({contributors_target(repo)})",
            )
        )
    return badges


def _badges(context: RenderContext) -> list[str]:
    return [markdown for _slot, markdown in badge_slots(context)]


def _rendered_section_ids(context: RenderContext) -> frozenset[str]:
    """The included sections whose body renders non-empty."""
    if context.rendered_ids is None:
        context.rendered_ids = frozenset(
            section.id
            for section in context.included
            if section.id != "navigation"
            and any(line.strip() for line in _section_body(context, section))
        )
    return context.rendered_ids


def _navigation(context: RenderContext) -> list[str]:
    rendered = _rendered_section_ids(context)
    return [
        f"- [{section.heading}](#{anchor(section.heading)})"
        for section in context.included
        if section.heading is not None and section.id != "navigation" and section.id in rendered
    ]


def _extra_bullet(fact: Fact) -> str:
    match = _EXTRA.search(fact.evidence[0].detail or "") if fact.evidence else None
    suffix = f" (extra `{match.group(1)}`)" if match else ""
    return f"- `{fact.value}`{suffix}"


def _dependencies(context: RenderContext) -> list[str]:
    """The dependency snapshot in four subsections."""
    facts = context.supported("dependency")
    marker = context.fact("dependency:none")
    required = [
        fact
        for fact in facts
        if fact.id != "dependency:none"
        and not fact.id.startswith(("dependency:optional.", "dependency:development."))
    ]
    optional = [fact for fact in facts if fact.id.startswith("dependency:optional.")]
    development = [fact for fact in facts if fact.id.startswith("dependency:development.")]
    lines: list[str] = []
    if required:
        lines.extend(["### Required Package Dependencies", ""])
        lines.extend(f"- `{fact.value}`" for fact in required)
    elif marker is not None and marker.polarity == "SUPPORTED" and marker.evidence:
        clause = marker.evidence[0].detail or "the manifest declares none"
        lines.extend(["### Required Package Dependencies", ""])
        lines.append(
            "No required third-party package dependencies; in "
            f"`{marker.evidence[0].path}`, {clause}."
        )
    if optional:
        lines.extend(["", "### Optional Dependencies", ""])
        lines.extend(_extra_bullet(fact) for fact in optional)
    spec = context.spec
    requires = context.fact(spec.floor_fact_id) if spec.floor_fact_id else None
    requirements: list[str] = []
    if requires is not None and requires.polarity == "SUPPORTED" and requires.evidence:
        floor = _FLOOR.fullmatch(requires.value.strip())
        path = requires.evidence[0].path
        declaration = (requires.attributes or {}).get("floor_declaration") or spec.floor_declaration
        if floor:
            requirements.append(
                f"- Requires {spec.floor_label} {floor.group(1)} or later "
                f'(`{declaration}="{requires.value}"` in `{path}`).'
            )
        else:
            requirements.append(
                f"- Requires {spec.floor_label} `{requires.value}` (`{declaration}` in `{path}`)."
            )
    tool = context.fact(spec.build_tool_fact_id) if spec.build_tool_fact_id else None
    if (
        tool is not None
        and tool.polarity == "SUPPORTED"
        and tool.evidence
        and spec.build_tool_label
    ):
        path = tool.evidence[0].path
        declaration = spec.build_tool_declaration
        mention = f" (`{declaration}` in `{path}`)" if declaration else f" (`{path}`)"
        if _VERSION_NUMBER.fullmatch(tool.value.strip()):
            requirements.append(
                f"- Requires {spec.build_tool_label} {tool.value.strip()} or later{mention}."
            )
        else:
            requirements.append(f"- Requires {spec.build_tool_label} `{tool.value}`{mention}.")
    if requirements:
        lines.extend(["", "### Native and System Requirements", "", *requirements])
    if development:
        lines.extend(["", "### Development Dependencies", ""])
        lines.extend(_extra_bullet(fact) for fact in development)
    return lines[1:] if lines and lines[0] == "" else lines


def _public_type_count(context: RenderContext) -> int:
    return sum(
        1
        for fact in context.supported("public_symbol")
        if fact.evidence
        and any(f"; {kind};" in (fact.evidence[0].detail or "") for kind in ("class", "enum"))
    )


def _documentation_resources(context: RenderContext) -> list[str]:
    """One list, each item a bold link, an em dash, and the authored sentence."""
    sid = "documentation_resources"
    repository = context.fact("identity:repository")
    issues = f"https://github.com/{repository.value}/issues" if repository is not None else None
    api_included = any(section.id == "api_reference" for section in context.included)
    lines: list[str] = []
    seen: set[str] = set()
    for link in context.plan.get("links", []):
        if link.get("section_id") != sid:
            continue
        target = context.fact(link.get("link_fact_id", ""))
        if target is None or target.value in seen or target.value == issues:
            continue
        seen.add(target.value)
        sentence = context.unit(sid, f"link:{target.id}")
        host = (urlsplit(target.value).hostname or "").lower()
        if host.startswith("reference.") and api_included:
            count = _public_type_count(context)
            sentence += (
                f" It covers all {count} verified public types; the "
                "[API Reference](#api-reference) section above covers the essentials."
            )
        lines.append(f"- **[{link_text(target)}]({target.value})** — {sentence}")
    if issues is not None:
        lines.append(f"- Found a bug or have a feature request? [Open an issue]({issues}).")
    return lines


_MATRIX_LABELS = {
    "python-version": "Python",
    "python": "Python",
    "node-version": "Node.js",
    "node": "Node.js",
    "dotnet-version": ".NET",
    "dotnet": ".NET",
    "go-version": "Go",
    "go": "Go",
    "java-version": "Java",
    "java": "Java",
    "jdk": "JDK",
    "rust": "Rust",
}
_MATRIX_OPERATING_SYSTEMS = {"ubuntu": "Ubuntu", "windows": "Windows", "macos": "macOS"}
_MATRIX_OS_VALUE = re.compile(r"(ubuntu|windows|macos)(?:-(latest|\d+(?:\.\d+)*))?")
_MATRIX_RUNTIME_VALUE = re.compile(r"\d+(?:\.\d+)*|stable|beta|nightly")


def _operating_system(value: str) -> str | None:
    """``ubuntu-latest`` as ``Ubuntu``, ``macos-14`` as ``macOS 14``; ``None`` for any other."""
    match = _MATRIX_OS_VALUE.fullmatch(value)
    if match is None:
        return None
    name, version = match.groups()
    label = _MATRIX_OPERATING_SYSTEMS[name]
    return f"{label} {version}" if version and version != "latest" else label


def _matrix_phrase(axes: list[tuple[str, list[str]]]) -> str:
    """The CI matrix as prose."""
    systems: list[str] = []
    runtimes: list[str] = []
    for axis, values in axes:
        named = [label for value in values if (label := _operating_system(value)) is not None]
        if axis == "os" and len(named) == len(values):
            systems.extend(label for label in named if label not in systems)
        elif axis in _MATRIX_LABELS and all(_MATRIX_RUNTIME_VALUE.fullmatch(v) for v in values):
            runtimes.append(f"{_MATRIX_LABELS[axis]} {_join_and(values)}")
        else:
            runtimes.append(f"`{axis}: {', '.join(values)}`")
    parts = [f"on {_join_and(systems)}"] if systems else []
    if runtimes:
        parts.append(f"with {'; '.join(runtimes)}")
    return ", ".join(parts)


def _join_and(parts: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    if len(parts) <= 1:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} and {parts[-1]}"


def _readme_commands(context: RenderContext) -> list[CommandForm]:
    """Every command the README shows besides the ones Development and Testing is about to add."""
    included = {section.id for section in context.included}
    texts = [text for placed in context.placed.values() for text in placed]
    texts.extend(text for (section, _slot), text in context.units.items() if section in included)
    if "installation" in included:
        texts.append("\n".join(_installation(context)))
    return [form for text in texts for form in commands_in_text(text)]


def _development_commands(context: RenderContext) -> tuple[str, list[str]]:
    """The lead-in sentence and the commands of the build and test facts, in build then test
    order."""
    shown = _readme_commands(context)

    def present(command: str) -> bool:
        form = command_form(command)
        return form is not None and any(have.covers(form) for have in shown)

    roles: list[str] = []
    block: list[str] = []
    for role, fact_id_ in (("build", BUILD_COMMAND_FACT_ID), ("test", TEST_COMMAND_FACT_ID)):
        fact = context.fact(fact_id_)
        if fact is None or fact.polarity != "SUPPORTED" or present(fact.value):
            continue
        roles.append(role)
        needs = (fact.attributes or {}).get(PRECONDITION_ATTRIBUTE, "").splitlines()
        for line in (*(need for need in needs if not present(need)), fact.value):
            if line not in block:
                block.append(line)
    if not roles:
        return "", []
    names = {"build": "build", "test": "run the tests"}
    lead = f"To {' and '.join(names[role] for role in roles)} from a clone, run:"
    return lead, ["```bash", *block, "```"]


def _development_sentences(context: RenderContext) -> list[str]:
    """The suite-size sentence, the CI matrix in words, and the release sentence."""
    sentences: list[str] = []
    tests = context.fact("build_test_asset:tests")
    if tests is not None and tests.polarity == "SUPPORTED":
        counts = [
            m.group(1)
            for evidence in tests.evidence
            if (m := _FILE_COUNT.match(evidence.detail or "")) is not None
        ]
        if counts:
            sentences.append(f"The suite covers {counts[-1]} test files under `{tests.value}`.")
    matrix = context.fact(CI_MATRIX_FACT_ID)
    if matrix is not None and matrix.polarity == "SUPPORTED" and matrix.evidence:
        axes = matrix_axes(matrix)
        path = matrix.evidence[0].path
        if axes:
            stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            sentences.append(f"The [{stem} workflow]({path}) runs {_matrix_phrase(axes)}.")
    release = context.fact(RELEASE_WORKFLOW_FACT_ID)
    if release is not None and release.polarity == "SUPPORTED":
        stem = release.value.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        sentences.append(f"Releases run through the [{stem} workflow]({release.value}).")
    return sentences


def renderer_sentences(
    entry: RegistryEntry,
    facts: FactsDocument,
    plan: dict[str, Any],
    units: dict[str, Any],
    dispositions: dict[str, Any],
) -> tuple[str, ...]:
    """Every sentence the renderer writes into a section an LLM otherwise owns."""
    context = RenderContext(entry, facts, plan, units, dispositions)
    sentences = list(_development_sentences(context))
    command_lead = _development_commands(context)[0]
    if command_lead:
        sentences.append(command_lead)
    if any(section.id == "api_reference" for section in context.included):
        kinds = [
            (fact.attributes or {}).get("symbol_kind", "")
            for fact in context.supported("public_symbol")
        ]
        types = sum(1 for kind in kinds if kind in ("class", "enum"))
        sentences.append(f"The verified public surface has {types} types.")
        count = _public_type_count(context)
        sentences.append(
            f"It covers all {count} verified public types; the "
            "[API Reference](#api-reference) section above covers the essentials."
        )
    closing = _enterprise_paragraph(context)
    if closing:
        sentences.append(closing.split(". ", 1)[0] + ".")
    return tuple(sentences)


def _symbol_description(context: RenderContext, fact: Fact) -> str:
    """The docstring first line when the source has one, else the sentence authored from the
    signature in a bounded batch, else the verified signature; never an invented sentence."""
    attributes = fact.attributes or {}
    docstring = attributes.get("docstring") or ""
    text = docstring
    if docstring:
        text, _ = elide_noncanonical(docstring, context.name)
    if not text:
        text = context.units.get(("api_reference", f"type:{fact.id}"), "")
    if not text and attributes.get("signature"):
        signature = attributes["signature"].replace("|", "/").replace("`", "")
        return f"Defined as `{signature}`."
    if not text:
        text = f"Public {attributes.get('symbol_kind', 'symbol')}."
    return context.canonical(text.replace("|", "/").replace("`", ""))


def _member_summary(context: RenderContext, fact: Fact) -> str:
    """A hub member's own documentation summary, table-safe, or an empty string."""
    docstring = (fact.attributes or {}).get("docstring") or ""
    if not docstring:
        return ""
    text, _ = elide_noncanonical(docstring, context.name)
    return context.canonical(text.replace("|", "/").replace("`", "")).strip()


def quoted_evidence_elisions(context: RenderContext) -> list[tuple[str, str]]:
    """Every forbidden non-canonical name variant ``_symbol_description`` elides from a verified
    type's own docstring before placing it in the Core API table."""
    found: list[tuple[str, str]] = []
    for fact in context.supported("public_symbol"):
        if (fact.attributes or {}).get("symbol_kind") not in {"class", "enum"}:
            continue
        docstring = (fact.attributes or {}).get("docstring") or ""
        if not docstring:
            continue
        _, variants = elide_noncanonical(docstring, context.name)
        found.extend((fact.value, variant) for variant in variants)
    return found


def _table_names(values: list[str]) -> dict[str, str]:
    """The name each type takes in the table: its final segment, or the shortest dotted suffix
    that tells it apart when two verified types share that segment."""
    names: dict[str, str] = {}
    for value in values:
        segments = value.split(".")
        for depth in range(1, len(segments) + 1):
            suffix = ".".join(segments[-depth:])
            rivals = [
                other
                for other in values
                if other != value and ".".join(other.split(".")[-depth:]) == suffix
            ]
            if not rivals:
                break
        names[value] = suffix
    return names


def api_reference_names(facts: FactsDocument) -> dict[str, str]:
    """The name every SUPPORTED public symbol takes in the API Reference, by fact value."""
    symbols = [f for f in facts.by_kind("public_symbol") if f.polarity == "SUPPORTED"]
    types = [f for f in symbols if (f.attributes or {}).get("symbol_kind") in {"class", "enum"}]
    names = _table_names([f.value for f in types])
    return {f.value: names.get(f.value, f.value.rsplit(".", 1)[-1]) for f in symbols}


def _api_reference(context: RenderContext) -> list[str]:
    """A visible intro with the verified public type count, then one details block holding the
    Core API table."""
    sid = "api_reference"
    symbols = context.supported("public_symbol")
    by_kind: dict[str, list[Fact]] = {}
    for fact in symbols:
        by_kind.setdefault((fact.attributes or {}).get("symbol_kind", ""), []).append(fact)
    classes = sorted(by_kind.get("class", []), key=lambda f: f.value)
    enums = sorted(by_kind.get("enum", []), key=lambda f: f.value)
    count = len(classes) + len(enums)
    names = api_reference_names(context.facts)
    lines = [context.unit(sid, "intro"), "", f"The verified public surface has {count} types."]
    lines += ["", "<details>", f"<summary>{API_SURFACE_SUMMARY}</summary>", ""]
    lines += ["### Core API", "", "| Class | Description |", "| --- | --- |"]
    lines += [f"| `{names[f.value]}` | {_symbol_description(context, f)} |" for f in classes]
    if enums:
        lines += ["", "#### Enumerations", "", "| Enumeration | Description |", "| --- | --- |"]
        lines += [f"| `{names[f.value]}` | {_symbol_description(context, f)} |" for f in enums]
    hub_methods = api_reference_hub_methods(context.plan, context.facts)
    hubs: list[tuple[dict[str, Any], Fact]] = []
    for hub in context.plan.get("api_hubs", []):
        symbol = context.fact(hub.get("symbol_fact_id", ""))
        if symbol is not None:
            hubs.append((hub, symbol))
    if hubs:
        lines += ["", "#### Detailed Member Reference"]
        for hub, symbol in hubs:
            lines += ["", f"### {names.get(symbol.value, symbol.value.rsplit('.', 1)[-1])}", ""]
            lines.append(context.unit(sid, f"hub:{hub['symbol_fact_id']}"))
            owned = sorted(hub_methods.get(symbol.value, []), key=lambda f: f.value)
            bullets = [
                f"- `{f.value.rsplit('.', 1)[-1]}`: {summary}"
                for f in owned
                if (summary := _member_summary(context, f))
            ]
            if bullets:
                lines.append("")
                lines += bullets
    lines += ["", "</details>"]
    return lines


ENTERPRISE_SENTENCE_LEAD = "These limitations don't apply to"


def enterprise_anchor(name: str) -> str:
    """The Enterprise Edition anchor text for the product ``name``."""
    return f"full-featured {name} — Enterprise Edition"


def _enterprise_paragraph(context: RenderContext) -> str:
    """The closing paragraph of Scope and Limitations, from the live verified Enterprise target."""
    if not any(section.id == "enterprise_relationship" for section in context.included):
        return ""
    target = enterprise_target(context.facts.facts)
    if target is None:
        return ""
    level = (target.attributes or {}).get("level", "platform")
    name = context.name.replace(" FOSS", "")
    if level == "family":
        name = name.split(" for ", 1)[0]
    sentence = f"{ENTERPRISE_SENTENCE_LEAD} [{enterprise_anchor(name)}]({target.value})."
    adds = _sentence_start(context.unit("enterprise_relationship", "context").strip())
    return f"{sentence} {adds}" if adds else sentence


_PLAIN_FIRST_WORD = re.compile(r"[a-z]+(?:['’][a-z]+)?(?=\s|$)")
_RELATIVE_OPENING = re.compile(r"(?:which|that)\s+(?=[a-z])")


def _sentence_start(text: str) -> str:
    """``text`` as the start of a sentence that follows a full stop."""
    relative = _RELATIVE_OPENING.match(text)
    if relative is not None:
        return "It " + text[relative.end() :]
    if _PLAIN_FIRST_WORD.match(text) is None:
        return text
    return text[0].upper() + text[1:]


def _oxford(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _registry_install(install: Fact | None) -> bool:
    """Whether ``install`` is a SUPPORTED install from a registry, not a source build."""
    return (
        install is not None
        and install.polarity == "SUPPORTED"
        and (install.attributes or {}).get("install_kind") not in ("source", "source_checkout")
    )


def _published_distributions(context: RenderContext) -> list[Fact]:
    """The distributions a registry confirmed as this repository's own."""
    return [
        fact
        for fact in context.supported("package")
        if fact.id.startswith(DISTRIBUTION_FACT_PREFIX)
    ]


def _published_sentence(distributions: list[Fact]) -> str:
    """The verified distribution as one sentence, never a command."""
    names = _oxford([f"`{fact.value}`" for fact in distributions])
    registries = sorted(
        {
            DISTRIBUTION_REGISTRY_NAMES[token]
            for fact in distributions
            if (token := str((fact.attributes or {}).get("registry", "")).lower())
            in DISTRIBUTION_REGISTRY_NAMES
        }
    )
    where = f" on {_oxford(registries)}" if registries else ""
    return f"The library is published{where} as {names}."


def _installation(context: RenderContext) -> list[str]:
    """Every command verified at this revision."""
    lines: list[str] = []
    install = context.fact(context.spec.install_fact_id)
    package = context.fact("package:name")
    published = context.fact(PUBLISHED_VERSION_FACT_ID)
    version = (
        published
        if published is not None and published.polarity == "SUPPORTED"
        else context.fact("package:version")
    )
    kind = (install.attributes or {}).get("install_kind") if install is not None else None
    source_kind = kind == "source"
    checkout_kind = kind == "source_checkout"
    distributions = _published_distributions(context) if not _registry_install(install) else []
    if distributions and install is not None and install.polarity == "SUPPORTED" and source_kind:
        lines.append(_published_sentence(distributions))
        lines.extend(["", "To build it from a source checkout instead:"])
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif distributions:
        lines.append(_published_sentence(distributions))
    elif (
        install is not None
        and install.polarity == "SUPPORTED"
        and checkout_kind
        and (install.attributes or {}).get(SOURCE_BASIS_ATTRIBUTE) == DOCUMENTED_SOURCE_BASIS
        and package is not None
    ):
        lines.append(
            f"`{package.value}` is not published on {context.spec.registry} yet; to use it, build "
            "it from a source checkout:"
            if context.spec.manifest_names_distribution
            else f"Build `{package.value}` from a source checkout:"
        )
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif (
        install is not None
        and install.polarity == "SUPPORTED"
        and checkout_kind
        and package is not None
    ):
        registry = context.spec.registry
        lines.append(
            f"`{package.value}` is not yet published on {registry}, and no build or install "
            "command succeeds; work from the source checkout instead:"
        )
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif (
        install is not None
        and install.polarity == "SUPPORTED"
        and source_kind
        and package is not None
    ):
        registry = context.spec.registry
        lead = (
            f"`{package.value}` is not yet published on {registry}; build it from a source "
            "checkout instead:"
            if context.spec.manifest_names_distribution
            else f"Build `{package.value}` from a source checkout:"
        )
        lines.append(lead)
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif install is not None and install.polarity == "SUPPORTED" and package is not None:
        registry = context.spec.registry
        lead = f"Install the published package from {registry} (`{package.value}`"
        lead += f", version {version.value}):" if version is not None else "):"
        lines.append(lead)
        lines.append("")
        lines.extend(_code_block("bash", install.value))
        for alternative, fence, body in context.spec.install_alternative_blocks(
            package.value, version.value if version is not None else ""
        ):
            lines.extend(["", alternative, ""])
            lines.extend(_code_block(fence, body))
    elif install is not None and package is not None:
        detail = install.evidence[-1].detail or "the registry could not be checked"
        registry = context.spec.registry
        state = (
            f"is not yet published on {registry}"
            if install.polarity == "CONTRADICTED"
            else f"could not be confirmed on {registry}"
        )
        lines.append(f"The package `{package.value}` {state} ({detail}).")
    executed = context.supported("example")
    repository = context.fact("identity:repository")
    if executed and repository is not None and not source_kind and not checkout_kind:
        name = repository.value.split("/")[-1]
        command = context.spec.source_checkout_command(install, repository.value, name)
        if command and context.spec.source_install_lead:
            lines.append("")
            lines.append(
                f"To work from a source checkout instead, {context.spec.source_install_lead}:"
            )
            lines.append("")
            lines.extend(_code_block("bash", command))
    imported = [
        fact.value
        for fact in context.supported("import_path")
        if any(
            re.search(context.spec.import_pattern.format(module=re.escape(fact.value)), e.value)
            for e in executed
        )
    ]
    if imported:
        module = max(imported, key=len)
        lines.append("")
        lines.append("Verify the install:")
        lines.append("")
        lines.extend(_code_block("bash", context.spec.verify_command.format(module=module)))
    versions = context.fact("package:python_versions")
    requires = context.fact("package:python_requires")
    sentence = ""
    if versions is not None and versions.polarity == "SUPPORTED":
        listed = _oxford([v.strip() for v in versions.value.split(",") if v.strip()])
        sentence = f"The package supports Python {listed}"
        if requires is not None and requires.polarity == "SUPPORTED":
            sentence += f" and declares `python_requires` as `{requires.value}`"
        sentence += "."
    elif requires is not None and requires.polarity == "SUPPORTED":
        sentence = f"The package declares `python_requires` as `{requires.value}`."
    if sentence:
        lines.append("")
        lines.append(sentence)
    return lines[1:] if lines and lines[0] == "" else lines


def _code_block(language: str, code: str) -> list[str]:
    return [f"```{language}", code.rstrip("\n"), "```"]


def example_block_visible_lines(code: str) -> int:
    """The visible-line cost of one optional example block."""
    return 5 + len(code.rstrip("\n").split("\n"))


FORMAT_NAMES: dict[str, str] = {
    "gltf": "glTF",
    "dae": "COLLADA",
    "wrl": "VRML",
    "drc": "Draco",
    "x": "DirectX X",
}


def format_name(value: str) -> str:
    """The canonical display name of a format fact value such as ``.gltf``."""
    extension = value.lstrip(".").lower()
    return FORMAT_NAMES.get(extension, extension.upper())


def _or_list(items: list[str]) -> str:
    if len(items) <= 2:
        return " or ".join(items)
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _label(text: str) -> str:
    return text.replace(chr(34), "'")


def _at_a_glance(context: RenderContext) -> list[str]:
    """One chain, Starting Points --> product --> Core Capabilities --> Outputs."""
    glance = context.plan.get("at_a_glance") or {}
    inputs = [
        format_name(fact.value)
        for fact in (context.fact(i) for i in glance.get("input_format_ids", []))
        if fact is not None
    ]
    outputs = [
        format_name(fact.value)
        for fact in (context.fact(i) for i in glance.get("output_format_ids", []))
        if fact is not None
    ]
    titles = [_label(context.canonical(title)) for title in glance.get("capability_titles", [])]
    return draw_at_a_glance(
        product=_label(context.name),
        starting_points=(f"An existing {_or_list(inputs)} file",) if inputs else (),
        capability_titles=titles,
        outputs=(f"{_or_list(outputs)} file",) if outputs else (),
    )


def _example_entry(context: RenderContext, sid: str, example_id: str) -> list[str]:
    """One further example: its authored task heading, then the verified code verbatim."""
    example = context.fact(example_id)
    assert example is not None
    task = context.unit(sid, f"workflow:{example_id}").strip().rstrip(".")
    heading = to_title_case(task, context.abbreviations)
    return ["", f"### {heading}", "", *_code_block(context.spec.fence, printed_example(example))]


def _with_retained_examples(lines: list[str], blocks: list[RetainedBlock]) -> list[str]:
    """``lines`` (Additional Examples as planned) followed by the unverified inherited examples.

    They join the section's details block when it has one; otherwise the first prints on its own
    when the section has nothing else, and the rest sit in a details block of their own."""
    if not blocks:
        return lines
    chunks = [block_lines(block) for block in blocks]
    if lines and lines[-1] == "</details>":
        closing = lines.pop()
        for chunk in chunks:
            lines.extend(["", *chunk])
        return [*lines, "", closing]
    if not any(line.strip() for line in lines):
        lines, chunks = list(chunks[0]), chunks[1:]
    if chunks:
        lines.extend(["", "<details>", f"<summary>{ADDITIONAL_EXAMPLES_SUMMARY}</summary>"])
        for chunk in chunks:
            lines.extend(["", *chunk])
        lines.extend(["", "</details>"])
    return lines


def _section_body(context: RenderContext, section: Section) -> list[str]:
    sid = section.id
    plan = context.plan
    lines: list[str] = []
    if sid == "identity":
        lines.append(f"# {context.name}")
    elif sid == "badges":
        lines.append(" ".join(_badges(context)))
    elif sid == "banner":
        pair = banner_target(context.facts.facts)
        if pair is not None:
            image, homepage = pair
            lines.append(f"[![{context.name}]({image.value})]({homepage.value})")
    elif sid == "opening":
        lines.append(context.unit(sid, "opening"))
    elif sid == "navigation":
        lines.extend(_navigation(context))
    elif sid == "at_a_glance":
        lines.extend(_at_a_glance(context))
    elif sid == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            title = context.canonical(str(item["title"]))
            lines.append(f"- **{title}.** {context.unit(sid, f'capability:{index}')}")
    elif sid == "installation":
        lines.extend(_installation(context))
    elif sid == "dependencies":
        lines.extend(_dependencies(context))
    elif sid == "quick_start":
        if sid in context.planned:
            lines.append(context.unit(sid, "lead_in"))
        example = context.fact(plan.get("quick_start_example_id", ""))
        if example is not None:
            lines.append("")
            lines.extend(_code_block(context.spec.fence, printed_example(example)))
        second = context.fact(plan.get("second_quick_start_example_id") or "")
        if second is not None:
            lines.append("")
            lines.append(context.unit(sid, "lead_in:2"))
            lines.append("")
            lines.extend(_code_block(context.spec.fence, printed_example(second)))
        for block in context.retained.get(sid, []):
            lines.extend(["", *block_lines(block)])
    elif sid == "additional_examples":
        if sid in context.planned:
            lines.append(context.unit(sid, "preview"))
        additional = [
            example_id
            for example_id in plan.get("additional_example_ids", [])
            if context.fact(example_id) is not None
        ]
        flagship = plan.get("flagship_example_id")
        if isinstance(flagship, str) and flagship in additional:
            lines.extend(_example_entry(context, sid, flagship))
            additional.remove(flagship)
        if additional:
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>{ADDITIONAL_EXAMPLES_SUMMARY}</summary>")
            for example_id in additional:
                lines.extend(_example_entry(context, sid, example_id))
            lines.append("")
            lines.append("</details>")
        lines = _with_retained_examples(lines, context.retained.get(sid, []))
    elif sid == "api_reference":
        lines.extend(_api_reference(context))
    elif sid == "documentation_resources":
        lines.extend(_documentation_resources(context))
    elif sid == "scope_limitations":
        lines.append(context.unit(sid, "scope"))
        slots = sorted(
            (int(slot.split(":", 1)[1]), slot)
            for (section, slot) in context.units
            if section == sid and slot.startswith("limitation:") and slot[11:].isdigit()
        )
        if slots:
            lines.append("")
            lines.extend(f"- {context.unit(sid, slot)}" for _, slot in slots)
    elif sid == "development_testing":
        lines.append(context.unit(sid, "summary"))
        facts_sentences = _development_sentences(context)
        if facts_sentences:
            lines.append("")
            lines.append(" ".join(facts_sentences))
        lead, commands = _development_commands(context)
        if commands:
            lines.extend(["", lead, "", *commands])
    elif sid == "enterprise_relationship":
        pass
    elif sid == "third_party_notices":
        notices = context.supported("third_party_notices")
        for fact in notices:
            lines.append(f"See [Third-party notices]({fact.value}).")
    elif sid == "license":
        spdx = context.fact("license:spdx")
        license_file = context.fact("license:file")
        if spdx is not None and license_file is not None:
            template = _MIT_PROSE if spdx.value == "MIT" else _GENERIC_PROSE
            lines.append(
                template.format(name=context.name, spdx=spdx.value, file=license_file.value)
            )
        elif spdx is not None and spdx.polarity == "SUPPORTED":
            template = _MIT_DECLARED_PROSE if spdx.value == "MIT" else _GENERIC_DECLARED_PROSE
            lines.append(template.format(spdx=spdx.value, manifest=spdx.evidence[0].path))
    placed = context.placed.get(sid, [])
    if placed and section.visibility == "collapsible" and lines and lines[-1] == "</details>":
        closing = lines.pop()
        for verbatim in placed:
            lines.append("")
            lines.append(verbatim.rstrip("\n"))
        lines.append("")
        lines.append(closing)
    else:
        for verbatim in placed:
            lines.append("")
            lines.append(verbatim.rstrip("\n"))
    if sid == "scope_limitations":
        closing = _enterprise_paragraph(context)
        if closing:
            lines.append("")
            lines.append(closing)
    return [line for line in lines if line is not None]


def render_readme(
    entry: RegistryEntry,
    facts: FactsDocument,
    plan: dict[str, Any],
    units: dict[str, Any],
    dispositions: dict[str, Any],
) -> str:
    """The complete README as one string with LF endings and a single trailing newline."""
    context = RenderContext(entry, facts.canonical(), plan, units, dispositions)
    blocks: list[str] = []
    for section in context.included:
        body = _section_body(context, section)
        if not any(line.strip() for line in body):
            continue
        heading = [f"## {section.heading}", ""] if section.heading else []
        blocks.append("\n".join(heading + body).rstrip("\n"))
    return collapse_document_blank_runs("\n\n".join(blocks) + "\n")


def collapse_document_blank_runs(text: str) -> str:
    """``text`` with no run of two or more empty lines outside a fenced code block."""
    kept: list[str] = []
    inside = False
    previous_empty = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        empty = not inside and not stripped
        if not (empty and previous_empty):
            kept.append(line)
        previous_empty = empty
    return "\n".join(kept)


def render_patch(original: str, rendered: str) -> str:
    """A unified diff from the existing README to the candidate, LF endings, empty when equal."""
    lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile="a/README.md",
        tofile="b/README.md",
    )
    text = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    return text


def line_counts(readme: str) -> tuple[int, int]:
    """(visible lines outside details blocks, total lines) for the length budget."""
    visible = 0
    total = 0
    depth = 0
    for line in readme.splitlines():
        total += 1
        stripped = line.strip()
        if stripped.startswith("<details"):
            depth += 1
            continue
        if stripped.startswith("</details"):
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            visible += 1
    return visible, total


def write_text(text: str, path: Path) -> str:
    data = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
