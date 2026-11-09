"""Quality parity of one sealed candidate against the README already published upstream (R2).

Owner ruling R2 (``docs/CONSOLIDATED_GOALS_2026-11-06.md``): the aspose.org readme-refresh output
already live upstream is the **minimum quality floor** for both lanes. This module recomputes, from
the two texts and the seal's own evidence (``facts.json``, ``dispositions.json`` for Lane R,
``corrections.json`` for Lane L), nine objective, deterministic dimensions, each pass/fail with
numbers. Parity is every dimension passing. It is a measurement: it changes no pipeline mechanism,
calls no provider, and writes nothing anywhere but the caller's scratch directory.

1. ``section_coverage`` -- every benchmark H2 topic is a candidate H2/H3 topic, or is justified:
   every inherited unit of that section has a non-loss disposition (Lane R) / is inside an
   evidenced edit (Lane L).
2. ``technical_content`` -- benchmark code blocks, install commands, API identifiers (inline code
   naming an extracted public symbol), links and version numbers are in the candidate, or are
   accounted for with a non-loss reason (a CONTRADICTED fact, a non-loss disposition, an evidenced
   Lane L edit, or replacement by the verified install command / published version).
3. ``verified_examples`` -- distinct EXECUTED (``SUPPORTED``) example facts the candidate prints
   >= those the benchmark prints, and the candidate prints no CONTRADICTED example.
4. ``links`` -- no candidate link is a ``link_target`` fact marked CONTRADICTED, and every
   candidate ``#anchor`` resolves to one of its own headings.
5. ``internal_markers`` -- ``validation.public_text.internal_markers`` finds nothing.
6. ``maintainer_preservation`` -- Lane R: every ``SUPERSEDE_REDUNDANT`` unit is carried
   (``scripts/maintainer_content_audit.coverage`` >= its own "carried" bound); Lane L: every
   benchmark line missing from the candidate sits inside an evidenced edit.
7. ``maintainability`` (docs/CONSOLIDATED_GOALS_2026-11-06.md section 6) -- structural upkeep of
   the candidate relative to the benchmark, computed from the two texts alone: (a) nesting -- for
   every benchmark heading with a candidate counterpart (by topic, closest level preferred), the
   counterpart is no more than one level deeper than the benchmark's own heading; (b) paragraph
   length -- no candidate paragraph exceeds roughly twice the word count of the benchmark's own
   longest paragraph; (c) emptied sections -- no benchmark H2 section that has content (a
   paragraph, fence, list, table, blockquote, HTML block or nested subheading) matches a
   candidate H2 section with nothing under it. A pass needs none of the three violated; the
   numbers report the benchmark's longest paragraph word count, the limit derived from it, and a
   count for each violation kind. Self-parity (the same text as both candidate and benchmark) is
   automatic for every rule here: an identical document can never nest deeper than itself, never
   write a paragraph longer than its own longest, and never leave a section empty that it itself
   fills.
8. ``required_sections`` (2026-11-07, checked directly against the aspose.org readme-refresh
   skill's own durable template contract, ``aspose.org/data/readme_template_contract.json``, and
   its hard-gate checks ``check_banner_present``/``check_badge_row_meets_verified_floor`` in
   ``readme_refresh_checks.py``) -- the fixed, aspose.org-mandated backbone section names (At a
   Glance, Key Capabilities, Installation, Dependencies, Quick Start, API Reference,
   Documentation & Resources, Scope and Limitations, Development and Testing, License):
   whichever of these the benchmark itself carries as an H2 must be a candidate H2/H3 topic too,
   unconditionally -- never excused by a non-loss disposition or an evidenced edit the way
   ``section_coverage`` allows. A real candidate found missing all four of Dependencies, API
   Reference, Scope and Limitations and Development and Testing (Aspose.3D-FOSS-for-.NET) is
   exactly the degradation this gate exists to catch, and ``section_coverage`` alone did not.
9. ``badge_banner_completeness`` (2026-11-07, same aspose.org parity check) -- computed from the
   two texts alone: a shields.io badge count in the candidate at least equal to the benchmark's,
   and a banner image link (``...banner-readme...``) in the candidate whenever the benchmark
   carries one.

"Non-loss" follows goal section 5: content may go only when demonstrably incorrect, obsolete,
duplicated or contradictory. ``NON_CONTENT`` and ``CORRECT_WITH_EVIDENCE`` qualify; an
``OMIT_UNSUPPORTED`` qualifies only when it cites a CONTRADICTED fact or states the content is
contradicted, incorrect, obsolete, outdated, deprecated or version-skewed. ``SUPERSEDE_REDUNDANT``,
``DEFER_UNRESOLVED``, an unsupported omission, and a placing disposition whose content is absent
are losses.

The benchmark text is read at run time and never stored: only counts, headings and short item
labels leave this module.
"""

from __future__ import annotations

import importlib.util
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from repo_presenter.core.package_registry import (
    is_unconfirmed_registry_install,
    unconfirmed_registry_packages,
)
from repo_presenter.readme.evidence.facts.links import (
    check_anchor,
    extract_links,
    heading_slugs,
)
from repo_presenter.readme.validation.public_text import internal_markers

LANE_R = "R"
LANE_L = "L"
DIMENSIONS = (
    "section_coverage",
    "technical_content",
    "verified_examples",
    "links",
    "internal_markers",
    "maintainer_preservation",
    "maintainability",
    "required_sections",
    "badge_banner_completeness",
)
#: The aspose.org readme-refresh skill's own durable, mechanically-verified backbone section
#: list (``aspose.org/data/readme_template_contract.json`` ``required_sections``, schema_version
#: 2, verified_at 2026-09-02) -- the fixed names ``required_sections`` (the dimension) holds the
#: candidate to whenever the benchmark itself carries one of them.
ASPOSE_REQUIRED_SECTIONS = (
    "At a Glance",
    "Key Capabilities",
    "Installation",
    "Dependencies",
    "Quick Start",
    "API Reference",
    "Documentation & Resources",
    "Scope and Limitations",
    "Development and Testing",
    "License",
)
_BADGE_IMG = re.compile(r"!\[[^\]]*\]\(([^)]*shields\.io[^)]*)\)", re.IGNORECASE)
_BANNER_IMG = re.compile(r"!\[[^\]]*\]\(([^)]*banner-readme[^)]*)\)", re.IGNORECASE)
REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDIT_SCRIPT = REPO_ROOT / "scripts" / "maintainer_content_audit.py"

NON_LOSS_ALWAYS = frozenset({"NON_CONTENT", "CORRECT_WITH_EVIDENCE"})
_NON_LOSS_RATIONALE = re.compile(
    r"contradict|incorrect|obsolete|outdated|deprecated|version[\s_-]*skew|no\s+longer",
    re.IGNORECASE,
)
_COMMAND_LANGS = frozenset(
    {
        "bash",
        "sh",
        "shell",
        "console",
        "zsh",
        "powershell",
        "pwsh",
        "cmd",
        "bat",
        "ps1",
        "text",
    }
)
_INSTALL = re.compile(
    r"^\s*(?:[$>]\s*)?(?:python3?\s+-m\s+)?(?:pip3?\s+install|npm\s+(?:install|i)|yarn\s+add|"
    r"pnpm\s+add|dotnet\s+add|cargo\s+add|go\s+get|go\s+install|Install-Package|"
    r"nuget\s+install|gem\s+install|composer\s+require|mvn\s+install|git\s+clone)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
_IDENT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)*(?:\(\))?$"
)
_VERSION = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.\d+){0,2})(?![\w.]*\d)")
_MD_DEST = re.compile(r"\]\([^)]*\)")
_BARE_URL = re.compile(r"https?://\S+")
_GH_BLOB = re.compile(
    r"^https?://github\.com/([^/]+/[^/]+)/(?:blob|tree)/[^/]+/(.+)$", re.IGNORECASE
)
_STOP = frozenset(
    {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "your"}
)
_SYNONYMS = {
    "installation": "install",
    "installing": "install",
    "quickstart": "quick start",
    "getting": "quick",
    "started": "start",
    "licence": "license",
    "licensing": "license",
    "examples": "example",
    "features": "feature",
    "capabilities": "capability",
    "formats": "format",
    "requirements": "requirement",
    "dependencies": "dependency",
}
_PUBLIC_API_KINDS = frozenset({"public_symbol", "enum_member"})
_PLACING_OR_SUPERSEDED = frozenset(
    {
        "VERIFIED_PRESERVE",
        "VERIFIED_REWRITE",
        "VERIFIED_MOVE",
        "PRESERVE_ATTRIBUTED",
        "SUPERSEDE_REDUNDANT",
    }
)


# --- markdown reading -----------------------------------------------------------------------


@dataclass(frozen=True)
class Fence:
    info: str
    code: str

    @property
    def lang(self) -> str:
        return (self.info.split() or [""])[0].lower()

    @property
    def is_command(self) -> bool:
        return self.lang in _COMMAND_LANGS


@dataclass(frozen=True)
class Document:
    text: str
    headings: tuple[tuple[int, str], ...]
    fences: tuple[Fence, ...]
    inline_code: tuple[str, ...]
    hrefs: tuple[str, ...]
    paragraphs: tuple[str, ...] = ()
    #: Every level-2 heading's name, in document order, paired with whether anything (a
    #: paragraph, fence, list, table, blockquote, HTML block or a nested H3+ subheading) sits
    #: under it before the next H2 -- the ``maintainability`` dimension's emptied-section check.
    h2_sections: tuple[tuple[str, bool], ...] = ()

    @property
    def h2(self) -> tuple[str, ...]:
        return tuple(name for level, name in self.headings if level == 2)


#: Top-level (sibling-to-headings) block token types that count as "this H2 has content".
_BLOCK_OPEN = frozenset(
    {
        "paragraph_open",
        "bullet_list_open",
        "ordered_list_open",
        "table_open",
        "blockquote_open",
        "html_block",
        "hr",
    }
)


def read_markdown(text: str) -> Document:
    tokens = MarkdownIt("commonmark").enable(["table", "strikethrough"]).parse(text)
    headings: list[tuple[int, str]] = []
    fences: list[Fence] = []
    inline: list[str] = []
    paragraphs: list[str] = []
    h2_sections: list[list[Any]] = []
    current_h2: int | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1])
            name = tokens[index + 1].content.strip()
            headings.append((level, name))
            if level == 2:
                h2_sections.append([name, False])
                current_h2 = len(h2_sections) - 1
            elif level == 1:
                current_h2 = None
            elif current_h2 is not None:
                h2_sections[current_h2][1] = True
            continue
        if token.type in {"fence", "code_block"}:
            fences.append(Fence(token.info.strip(), token.content))
            if token.level == 0 and current_h2 is not None:
                h2_sections[current_h2][1] = True
            continue
        if token.type == "inline":
            inline.extend(
                c.content for c in token.children or [] if c.type == "code_inline"
            )
            if token.level == 1 and tokens[index - 1].type == "paragraph_open":
                paragraphs.append(token.content)
            continue
        if token.level == 0 and token.type in _BLOCK_OPEN and current_h2 is not None:
            h2_sections[current_h2][1] = True
    hrefs = tuple(target.href for target in extract_links(text))
    return Document(
        text,
        tuple(headings),
        tuple(fences),
        tuple(inline),
        hrefs,
        tuple(paragraphs),
        tuple((name, has_content) for name, has_content in h2_sections),
    )


def code_lines(code: str) -> frozenset[str]:
    return frozenset(
        " ".join(line.split()) for line in code.splitlines() if line.strip()
    )


def contains_code(container: str, item: str) -> bool:
    """Every non-blank line of ``item`` (whitespace-normalised) is a line of ``container``: robust
    to a verifier's prelude, re-indentation and blank-line changes, never to a changed line."""
    wanted = code_lines(item)
    return bool(wanted) and wanted <= code_lines(container)


def _topic(name: str) -> frozenset[str]:
    words = re.sub(r"[^\w\s]", " ", name.lower()).split()
    canon = " ".join(_SYNONYMS.get(w, w) for w in words if w not in _STOP)
    return frozenset(canon.split())


def topics_match(left: str, right: str) -> bool:
    a, b = _topic(left), _topic(right)
    if not a or not b:
        return False
    return a == b or a <= b or b <= a


# --- badge / banner slot equivalence ----------------------------------------------------------
#
# R2 is content equivalence, not byte identity. A maintainers' badge or banner whose SLOT
# (banner, package, runtime, build, license, contributors) the candidate fills with the renderer's
# own verified slot badge is REPLACED, not lost -- the same standing the module already gives a
# command replaced by the verified install command or a version replaced by the verified published
# version. ONE function judges it (``badge_slot_replaced``); BC-17 (``technical_content`` below),
# the independent reviewer's ``live_readme_loss`` and ``disposition_coverage`` rules, and S9
# accounting all call it, so "replaced" can never mean one thing in one gate and another elsewhere.
# A slot the candidate leaves empty is never exempt, and neither is a link_target fact the facts
# record CONTRADICTED (callers pass those hrefs in ``contradicted``).

_LINKED_BADGE = re.compile(r"\[!\[[^\]]*\]\(([^)\s]+)[^)]*\)\]\(([^)\s]+)[^)]*\)")
_ANY_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
_ANY_BADGE_MARKDOWN = re.compile(
    r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\)"
)


def badge_slot_of_url(url: str) -> str | None:
    """The slot an image URL fills: ``banner``, ``package``, ``runtime``, ``build``, ``license``
    or ``contributors``; ``None`` for anything that is not recognisably a badge or a banner
    (a body image, a diagram) -- those are content and are never exempted here."""
    low = url.strip().lower()
    path = low.split("?", 1)[0]
    if "banner" in path.rsplit("/", 1)[-1]:
        return "banner"
    if "shields.io" not in low and "/badge.svg" not in path and "badgen.net" not in low:
        return None
    if "github/contributors" in low:
        return "contributors"
    if "/actions/workflows/" in low or "/workflow/status" in low or "travis" in low or "circleci" in low:
        return "build"
    if "/pypi/l/" in low or "/github/license" in low or "/npm/l/" in low or "/crates/l/" in low \
            or "/nuget/l" in low or "/badge/license" in low:
        return "license"
    if "/pypi/pyversions" in low or "/badge/python" in low or "/badge/go" in low \
            or "/badge/java" in low or "/badge/.net" in low or "/badge/dotnet" in low \
            or "/badge/node" in low or "/badge/rust" in low or "/badge/c%2b%2b" in low \
            or "/badge/typescript" in low or "/badge/c++" in low:
        return "runtime"
    if any(f"/{registry}/v/" in low for registry in ("pypi", "npm", "nuget", "crates", "maven-central", "gem")):
        return "package"
    return None


def candidate_badge_slots(candidate_text: str) -> frozenset[str]:
    """Every slot some image in the candidate fills."""
    return frozenset(
        slot
        for url in _ANY_IMAGE.findall(candidate_text)
        if (slot := badge_slot_of_url(url)) is not None
    )


def badge_slot_replaced(
    href: str,
    benchmark_text: str,
    candidate_text: str,
    contradicted: frozenset[str] | set[str] = frozenset(),
) -> str | None:
    """Why ``href`` (an image URL of the benchmark, or the link target of one of its linked
    badges) is replaced rather than lost, or ``None``: the badge's slot is filled in the
    candidate and the href is not CONTRADICTED."""
    if href in contradicted:
        return None
    filled = candidate_badge_slots(candidate_text)
    own = badge_slot_of_url(href)
    if own is not None:
        return f"replaced by the candidate's verified {own} badge" if own in filled else None
    for image, target in _LINKED_BADGE.findall(benchmark_text):
        if target.strip().rstrip("/") == href.strip().rstrip("/"):
            slot = badge_slot_of_url(image)
            if slot is not None and slot in filled:
                return f"link of a {slot} badge the candidate replaces with its verified one"
    return None


def badge_row_replaced(
    unit_text: str,
    candidate_text: str,
    contradicted: frozenset[str] | set[str] = frozenset(),
) -> bool:
    """Whether an inherited badge-row unit is wholly accounted for in the candidate: it is nothing
    but badges, and every one of them is printed as written or replaced by its slot's verified
    badge. A row carrying any other text, or any badge the candidate neither prints nor replaces,
    is not (and keeps the stricter 'printed as written' standard)."""
    if _ANY_BADGE_MARKDOWN.sub("", unit_text).strip():
        return False
    badges = _ANY_BADGE_MARKDOWN.findall(unit_text)
    if not badges:
        return False
    squeezed = " ".join(candidate_text.split())
    for badge in badges:
        if " ".join(badge.split()) in squeezed:
            continue
        images = _ANY_IMAGE.findall(badge)
        if not images:
            return False
        image = images[0]
        if badge_slot_replaced(image, unit_text, candidate_text, contradicted) is None:
            return False
    return True


def _norm_href(href: str) -> str:
    href = href.strip()
    match = _GH_BLOB.match(href)
    if match:
        href = match.group(2)
    href = href.removeprefix("./")
    return href.rstrip("/")


def _has_word(text: str, token: str) -> bool:
    return re.search(r"(?<![\w.])" + re.escape(token) + r"(?![\w])", text) is not None


def _versions(text: str) -> set[str]:
    stripped = _BARE_URL.sub(" ", _MD_DEST.sub("]", text))
    return {m.group(1) for m in _VERSION.finditer(stripped)}


# --- the sealed candidate --------------------------------------------------------------------


@dataclass(frozen=True)
class SealedCandidate:
    lane: str
    readme: str
    facts: tuple[Mapping[str, Any], ...]
    dispositions: tuple[Mapping[str, Any], ...] = ()
    edits: tuple[Mapping[str, Any], ...] = ()

    def by_kind(self, kind: str) -> list[Mapping[str, Any]]:
        return [f for f in self.facts if f.get("kind") == kind]

    @property
    def facts_by_id(self) -> dict[str, Mapping[str, Any]]:
        return {str(f.get("id")): f for f in self.facts}


def load_revision_dir(revision_dir: Path, lane: str) -> SealedCandidate:
    """A sealed revision directory (as ``bundle_store`` / ``export_bundle`` write it)."""

    def read(name: str) -> Any:
        path = revision_dir / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    facts = (read("facts.json") or {}).get("facts", [])
    dispositions = read("dispositions.json") or {}
    rows = (
        dispositions.get("dispositions", [])
        if isinstance(dispositions, dict)
        else dispositions
    )
    edits = (read("corrections.json") or {}).get("edits", [])
    return SealedCandidate(
        lane,
        (revision_dir / "README.md").read_text(encoding="utf-8"),
        tuple(facts),
        tuple(rows or ()),
        tuple(edits or ()),
    )


# --- accounting: why an absent benchmark item is not a loss ----------------------------------


def disposition_is_non_loss(
    row: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]
) -> bool:
    disposition = str(row.get("disposition"))
    if disposition in NON_LOSS_ALWAYS:
        return True
    if disposition == "OMIT_UNSUPPORTED":
        cited = [facts.get(str(fid)) for fid in row.get("fact_ids") or ()]
        if any(f is not None and f.get("polarity") == "CONTRADICTED" for f in cited):
            return True
        return bool(_NON_LOSS_RATIONALE.search(str(row.get("rationale") or "")))
    return False


def _edit_is_evidenced(edit: Mapping[str, Any]) -> bool:
    return bool(edit.get("evidence") or edit.get("fact_ids") or edit.get("locators"))


class Accounting:
    """Answers "is this absent benchmark item accounted for, and why", from the seal's evidence."""

    def __init__(self, candidate: SealedCandidate) -> None:
        self.candidate = candidate
        self.facts = candidate.facts_by_id
        units = {str(f.get("id")): f for f in candidate.by_kind("inherited_unit")}
        self.units = units
        self.rows = {str(r.get("unit_id")): r for r in candidate.dispositions}

    def _units_containing(self, item: str, *, code: bool) -> list[str]:
        found = []
        for unit_id, unit in self.units.items():
            value = str(unit.get("value") or "")
            if contains_code(value, item) if code else item in value:
                found.append(unit_id)
        return found

    def reason(self, item: str, *, code: bool = False) -> str | None:
        """A non-loss reason, or ``None`` when the item's absence is a loss."""
        if self.candidate.lane == LANE_L:
            for edit in self.candidate.edits:
                original = str(edit.get("original") or "")
                hit = contains_code(original, item) if code else item in original
                if hit and _edit_is_evidenced(edit):
                    return f"evidenced Lane L edit ({edit.get('detector')})"
            return None
        unit_ids = self._units_containing(item, code=code)
        if not unit_ids:
            return None
        rows = [self.rows.get(unit_id) for unit_id in unit_ids]
        if all(
            row is not None and disposition_is_non_loss(row, self.facts) for row in rows
        ):
            return "disposition " + ",".join(
                sorted({str(r.get("disposition")) for r in rows if r is not None})
            )
        return None

    def loss_units(self, item: str, *, code: bool = False) -> tuple[str, ...]:
        """Lane R: the inherited units holding ``item`` whose disposition does not account for its
        absence (no row, or a loss disposition): the units a repair must re-reconcile. Empty for
        Lane L, and for an item no inherited unit holds."""
        if self.candidate.lane == LANE_L:
            return ()
        return tuple(
            unit_id
            for unit_id in self._units_containing(item, code=code)
            if (row := self.rows.get(unit_id)) is None
            or not disposition_is_non_loss(row, self.facts)
        )

    def section_reason(self, heading: str) -> str | None:
        """Lane R: every content unit of the benchmark section has a non-loss disposition (or the
        section has none). Lane L: the heading line itself is inside an evidenced edit."""
        return self.section_account(heading)[0]

    def section_account(self, heading: str) -> tuple[str | None, tuple[str, ...]]:
        """``(non-loss reason or None, the section's units that make it a loss)``; the units are
        empty for Lane L and for a section with no content unit."""
        if self.candidate.lane == LANE_L:
            return self.reason(heading), ()
        members = [
            unit_id
            for unit_id, unit in self.units.items()
            if topics_match(
                str((unit.get("attributes") or {}).get("section", "")).split(" > ")[-1],
                heading,
            )
            and not unit_id.endswith(".heading")
            and str((unit.get("attributes") or {}).get("section", ""))
        ]
        if not members:
            return None, ()
        audit = _load_audit()
        moved = 0
        losing: list[str] = []
        for unit_id in members:
            row = self.rows.get(unit_id)
            if row is None:
                losing.append(unit_id)
                continue
            if disposition_is_non_loss(row, self.facts):
                continue
            carried = audit.coverage(
                str(self.units[unit_id].get("value") or ""), self.candidate.readme
            )
            if (
                str(row.get("disposition")) in _PLACING_OR_SUPERSEDED
                and carried >= audit.PARTIAL
            ):
                moved += 1
                continue
            losing.append(unit_id)
        if losing:
            return None, tuple(losing)
        if moved:
            return (
                f"{moved} of {len(members)} section units carried under other headings, rest non-loss",
                (),
            )
        return f"all {len(members)} section units have non-loss dispositions", ()


# --- the six dimensions ---------------------------------------------------------------------


@dataclass(frozen=True)
class Loss:
    """One benchmark item a content dimension finds lost, with what a repair needs to route it.

    ``units`` are the inherited units (Lane R) holding the item with a disposition that does not
    account for its absence; empty when no inherited unit holds it (or for Lane L). ``stage`` is
    the causal stage that should have carried an item that maps to no unit."""

    dimension: str
    category: str
    item: str
    units: tuple[str, ...] = ()
    stage: str = "RECONCILING"


@dataclass
class Dimension:
    name: str
    passed: bool
    numbers: dict[str, Any]
    details: list[str] = field(default_factory=list)
    losses: list[Loss] = field(default_factory=list)


def _label(text: str, limit: int = 70) -> str:
    return " ".join(text.split())[:limit]


def section_coverage(bench: Document, cand: Document, acct: Accounting) -> Dimension:
    cand_topics = [name for level, name in cand.headings if level in (2, 3)]
    present, justified, missing = 0, 0, []
    losses: list[Loss] = []
    for heading in bench.h2:
        if any(topics_match(heading, other) for other in cand_topics):
            present += 1
            continue
        why, units = acct.section_account(heading)
        if why:
            justified += 1
        else:
            missing.append(heading)
            # A section with no content unit to re-reconcile was the plan's to carry.
            losses.append(
                Loss(
                    "section_coverage",
                    "h2",
                    _label(heading),
                    units,
                    "RECONCILING" if units else "PLANNING",
                )
            )
    return Dimension(
        "section_coverage",
        not missing,
        {
            "benchmark_h2": len(bench.h2),
            "present": present,
            "justified": justified,
            "missing": len(missing),
        },
        [f"missing H2: {_label(h)}" for h in missing],
        losses,
    )


def _items(bench: Document, cand: SealedCandidate) -> dict[str, list[tuple[str, bool]]]:
    """Benchmark technical items per category: ``(item text, is_code)``."""
    api_names: set[str] = set()
    for fact in cand.facts:
        if (
            fact.get("kind") in _PUBLIC_API_KINDS
            and fact.get("polarity") == "SUPPORTED"
        ):
            value = str(fact.get("value") or "")
            api_names.add(re.split(r"\.|::", value)[-1])
    # A maintainers' mermaid diagram is replaced by design when the candidate draws its own At a
    # Glance diagram from verified facts (BC-05 exempts it the same way); without one it is owed.
    candidate_draws = any(f.lang == "mermaid" for f in read_markdown(cand.readme).fences)
    code_blocks = [
        (f.code, True)
        for f in bench.fences
        if not f.is_command and f.code.strip() and not (f.lang == "mermaid" and candidate_draws)
    ]
    installs: list[tuple[str, bool]] = []
    for fence in bench.fences:
        for match in _INSTALL.finditer(fence.code):
            line = " ".join(match.group(0).lstrip("$> ").split())
            if (line, False) not in installs:
                installs.append((line, False))
    identifiers: list[tuple[str, bool]] = []
    for span in bench.inline_code:
        span = span.strip()
        if not _IDENT.match(span):
            continue
        last = re.split(r"\.|::", span.removesuffix("()"))[-1]
        if last in api_names and (span, False) not in identifiers:
            identifiers.append((span, False))
    links = []
    for href in bench.hrefs:
        if href.startswith("#") or not href.strip():
            continue
        if (href, False) not in links:
            links.append((href, False))
    versions = [(v, False) for v in sorted(_versions(bench.text))]
    return {
        "code_blocks": code_blocks,
        "install_commands": installs,
        "api_identifiers": identifiers,
        "links": links,
        "versions": versions,
    }


def _verified_values(
    cand: SealedCandidate, predicate: Callable[[Mapping[str, Any]], bool]
) -> list[str]:
    return [
        str(f.get("value") or "")
        for f in cand.facts
        if f.get("polarity") == "SUPPORTED" and predicate(f) and f.get("value")
    ]


def technical_content(
    bench: Document, cand_doc: Document, cand: SealedCandidate, acct: Accounting
) -> Dimension:
    items = _items(bench, cand)
    cand_hrefs = {_norm_href(h) for h in cand_doc.hrefs}
    contradicted_links = {
        str(f.get("value"))
        for f in cand.by_kind("link_target")
        if f.get("polarity") == "CONTRADICTED"
    }
    contradicted_examples = [
        str(f.get("value") or "")
        for f in cand.by_kind("example")
        if f.get("polarity") == "CONTRADICTED"
    ]
    install_facts = _verified_values(cand, lambda f: f.get("kind") == "install_command")
    unconfirmed_packages = unconfirmed_registry_packages(cand.facts)
    version_facts = _verified_values(
        cand,
        lambda f: (
            f.get("kind") == "package"
            and (
                str(f.get("id", "")).endswith("version")
                or "published_version" in str(f.get("id", ""))
            )
        ),
    )
    numbers: dict[str, Any] = {}
    details: list[str] = []
    losses: list[Loss] = []
    lost_total = 0
    for category, entries in items.items():
        carried = accounted = 0
        for item, is_code in entries:
            if category == "code_blocks":
                here = any(contains_code(f.code, item) for f in cand_doc.fences)
            elif category == "links":
                here = _norm_href(item) in cand_hrefs
            elif category == "install_commands":
                here = " ".join(item.split()) in " ".join(cand.readme.split())
            elif category == "versions":
                # The same trailing boundary _VERSION itself uses: a bare "2.99m" decimal
                # literal (a C# ``decimal`` suffix, not a version) still carries no further
                # digit after it, so it must count as present the same way it was extracted --
                # self-parity requires one boundary rule, not two (found asymmetric 2026-11-07,
                # Aspose.Cells-FOSS-for-.NET's live README: `2.99m`/`1.99m` decimal literals).
                here = (
                    re.search(
                        r"(?<![\w.])v?" + re.escape(item) + r"(?![\w.]*\d)",
                        cand.readme,
                    )
                    is not None
                )
            else:
                here = _has_word(cand.readme, item.removesuffix("()"))
            if here:
                carried += 1
                continue
            why = acct.reason(item, code=is_code)
            if (
                why is None
                and category == "code_blocks"
                and any(
                    contains_code(value, item) or contains_code(item, value)
                    for value in contradicted_examples
                    if value.strip()
                )
            ):
                why = "its example fact is CONTRADICTED"
            if why is None and category == "links" and item in contradicted_links:
                why = "its link_target fact is CONTRADICTED"
            if why is None and category == "links":
                why = badge_slot_replaced(
                    item, bench.text, cand.readme, frozenset(contradicted_links)
                )
            if why is None and category == "install_commands":
                tool = " ".join(item.split()[:2]).lower()
                if any(
                    v.lower().startswith(tool) and v in cand.readme
                    for v in install_facts
                ):
                    why = "replaced by the verified install command"
            if (
                why is None
                and category == "install_commands"
                and is_unconfirmed_registry_install(item, unconfirmed_packages)
            ):
                why = (
                    "its registry install is not confirmed as this repository's own (BC-02); the "
                    "Installation section states that and gives the source install"
                )
            if why is None and category == "versions":
                shape = item.count(".")
                if any(
                    v in cand.readme and v != item and v.count(".") == shape
                    for v in version_facts
                ):
                    why = "replaced by the verified package version"
            if why is not None:
                accounted += 1
            else:
                lost_total += 1
                label = _label(item.splitlines()[0] if is_code else item)
                details.append(f"{category} lost: {label}")
                units = acct.loss_units(item, code=is_code)
                # An item no inherited unit holds was never extracted from the README it is in.
                losses.append(
                    Loss(
                        "technical_content",
                        category,
                        label,
                        units,
                        "RECONCILING" if units else "EXTRACTING",
                    )
                )
        numbers[category] = {
            "benchmark": len(entries),
            "carried": carried,
            "accounted": accounted,
            "lost": len(entries) - carried - accounted,
        }
    numbers["lost_total"] = lost_total
    return Dimension("technical_content", lost_total == 0, numbers, details, losses)


def verified_examples(
    bench: Document, cand_doc: Document, cand: SealedCandidate
) -> Dimension:
    examples = cand.by_kind("example")

    def printed(doc: Document, polarity: str) -> set[str]:
        hits = set()
        for fact in examples:
            value = str(fact.get("value") or "")
            if fact.get("polarity") != polarity or not value.strip():
                continue
            if any(contains_code(f.code, value) for f in doc.fences):
                hits.add(str(fact.get("id")))
        return hits

    bench_runnable = printed(bench, "SUPPORTED")
    cand_verified = printed(cand_doc, "SUPPORTED")
    cand_contradicted = printed(cand_doc, "CONTRADICTED")
    numbers = {
        "benchmark_runnable": len(bench_runnable),
        "candidate_verified": len(cand_verified),
        "candidate_contradicted": len(cand_contradicted),
        "benchmark_example_fences": sum(1 for f in bench.fences if not f.is_command),
        "candidate_example_fences": sum(1 for f in cand_doc.fences if not f.is_command),
        "example_facts_by_polarity": {
            p: sum(1 for f in examples if f.get("polarity") == p)
            for p in ("SUPPORTED", "UNRESOLVED", "CONTRADICTED")
        },
    }
    details = [
        f"runnable benchmark example not printed: {i}"
        for i in sorted(bench_runnable - cand_verified)
    ]
    details += [
        f"candidate prints CONTRADICTED example {i}" for i in sorted(cand_contradicted)
    ]
    passed = len(cand_verified) >= len(bench_runnable) and not cand_contradicted
    return Dimension("verified_examples", passed, numbers, details)


def links(cand_doc: Document, cand: SealedCandidate) -> Dimension:
    contradicted = {
        str(f.get("value"))
        for f in cand.by_kind("link_target")
        if f.get("polarity") == "CONTRADICTED"
    }
    known = {str(f.get("value")) for f in cand.by_kind("link_target")}
    slugs = heading_slugs(cand.readme)
    broken, dangling, unchecked = [], [], 0
    for href in cand_doc.hrefs:
        if href.startswith("#"):
            if check_anchor(href, slugs).outcome != "RESOLVED":
                dangling.append(href)
        elif href in contradicted:
            broken.append(href)
        elif href not in known:
            unchecked += 1
    return Dimension(
        "links",
        not broken and not dangling,
        {
            "candidate_links": len(cand_doc.hrefs),
            "contradicted": len(broken),
            "dangling_anchors": len(dangling),
            "not_in_link_facts": unchecked,
        },
        [f"broken link: {h}" for h in broken]
        + [f"dangling anchor: {h}" for h in dangling],
    )


def markers(cand: SealedCandidate) -> Dimension:
    found = internal_markers(cand.readme)
    return Dimension(
        "internal_markers",
        not found,
        {"markers": len(found)},
        [f"marker: {m}" for m in found],
    )


def _match_section(
    name: str, index: int, sections: Sequence[tuple[str, bool]]
) -> tuple[str, bool] | None:
    """The candidate H2 section matching ``name`` (one of ``sections``): same index first
    (self-parity's exact alignment), else the first topic match."""
    if index < len(sections) and topics_match(name, sections[index][0]):
        return sections[index]
    return next((s for s in sections if topics_match(name, s[0])), None)


def maintainability(bench: Document, cand_doc: Document) -> Dimension:
    """Structural upkeep (docstring section 7): nesting, paragraph length, emptied sections."""
    depth_violations: list[str] = []
    for index, (level, name) in enumerate(bench.headings):
        matches = [
            lvl for lvl, other in cand_doc.headings if topics_match(name, other)
        ]
        if not matches:
            continue
        if index < len(cand_doc.headings) and topics_match(
            name, cand_doc.headings[index][1]
        ):
            cand_level = cand_doc.headings[index][0]
        else:
            cand_level = min(matches, key=lambda lvl: abs(lvl - level))
        if cand_level - level > 1:
            depth_violations.append(
                f"heading nested {cand_level - level} levels deeper: {_label(name)}"
            )
    bench_paras = [p for p in bench.paragraphs if p.strip()]
    bench_longest = max((len(p.split()) for p in bench_paras), default=0)
    limit = max(1, bench_longest * 2)
    long_paragraphs = [
        p for p in cand_doc.paragraphs if p.strip() and len(p.split()) > limit
    ]
    emptied: list[str] = []
    for index, (name, has_content) in enumerate(bench.h2_sections):
        if not has_content:
            continue
        match = _match_section(name, index, cand_doc.h2_sections)
        if match is not None and not match[1]:
            emptied.append(name)
    passed = not depth_violations and not long_paragraphs and not emptied
    numbers = {
        "benchmark_longest_paragraph_words": bench_longest,
        "paragraph_limit_words": limit,
        "heading_depth_violations": len(depth_violations),
        "long_paragraphs": len(long_paragraphs),
        "emptied_sections": len(emptied),
    }
    details = (
        depth_violations
        + [
            f"paragraph too long ({len(p.split())}w > {limit}w): {_label(p)}"
            for p in long_paragraphs
        ]
        + [f"section emptied: {_label(n)}" for n in emptied]
    )
    return Dimension("maintainability", passed, numbers, details)


def required_sections(bench: Document, cand_doc: Document) -> Dimension:
    """Hard, unconditional backbone-section gate (docstring section 8): unlike
    ``section_coverage``, never excused by a non-loss disposition or an evidenced edit, and
    scoped to the fixed ``ASPOSE_REQUIRED_SECTIONS`` names the benchmark itself carries -- a
    benchmark H2 outside that fixed list is still ``section_coverage``'s job alone."""
    cand_topics = [name for level, name in cand_doc.headings if level in (2, 3)]
    carried_by_benchmark = [
        name
        for name in ASPOSE_REQUIRED_SECTIONS
        if any(topics_match(name, h) for h in bench.h2)
    ]
    missing = [
        name
        for name in carried_by_benchmark
        if not any(topics_match(name, other) for other in cand_topics)
    ]
    return Dimension(
        "required_sections",
        not missing,
        {
            "backbone_sections": len(ASPOSE_REQUIRED_SECTIONS),
            "carried_by_benchmark": len(carried_by_benchmark),
            "missing": len(missing),
        },
        [f"required section entirely absent from the candidate: {name}" for name in missing],
    )


def badge_banner_completeness(bench: Document, cand_doc: Document) -> Dimension:
    """Badge/banner floor (docstring section 9), from the two texts alone: aspose.org's own
    ``check_badge_row_meets_verified_floor`` and ``check_banner_present`` hard gates, approximated
    here without the live badge-availability facts those checks read -- a shields.io badge count
    that does not shrink, and a banner image link whenever the benchmark carries one."""
    bench_badges = _BADGE_IMG.findall(bench.text)
    cand_badges = _BADGE_IMG.findall(cand_doc.text)
    bench_banner = bool(_BANNER_IMG.search(bench.text))
    cand_banner = bool(_BANNER_IMG.search(cand_doc.text))
    missing_banner = bench_banner and not cand_banner
    badge_deficit = max(0, len(bench_badges) - len(cand_badges))
    passed = not missing_banner and badge_deficit == 0
    details = []
    if missing_banner:
        details.append(
            "banner image missing: the benchmark carries the product banner, the candidate does not"
        )
    if badge_deficit:
        details.append(
            f"badge row shrank by {badge_deficit} "
            f"(benchmark {len(bench_badges)}, candidate {len(cand_badges)})"
        )
    return Dimension(
        "badge_banner_completeness",
        passed,
        {
            "benchmark_badges": len(bench_badges),
            "candidate_badges": len(cand_badges),
            "badge_deficit": badge_deficit,
            "benchmark_has_banner": bench_banner,
            "candidate_has_banner": cand_banner,
        },
        details,
    )


def _load_audit() -> Any:
    spec = importlib.util.spec_from_file_location(
        "maintainer_content_audit", _AUDIT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_AUDIT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def maintainer_preservation(
    bench: Document, cand: SealedCandidate, acct: Accounting
) -> Dimension:
    if cand.lane == LANE_L:
        cand_lines = code_lines(cand.readme)
        missing = [line for line in sorted(code_lines(bench.text) - cand_lines)]
        unaccounted = [line for line in missing if acct.reason(line) is None]
        return Dimension(
            "maintainer_preservation",
            not unaccounted,
            {
                "benchmark_lines": len(code_lines(bench.text)),
                "missing_lines": len(missing),
                "unaccounted": len(unaccounted),
                "edits": len(cand.edits),
            },
            [
                f"line lost without an evidenced edit: {_label(line)}"
                for line in unaccounted[:25]
            ],
        )
    # The same judgement BC-05 makes (validation/supersession.py): one standard, never two gates a
    # candidate could pass one of and fail the other (owner ruling 2026-11-06: one version, one truth).
    from types import SimpleNamespace

    from repo_presenter.readme.validation.supersession import superseded_failures

    def by_kind(kind: str) -> list[Any]:
        return [
            SimpleNamespace(id=str(f.get("id")), value=str(f.get("value") or ""))
            for f in cand.by_kind(kind)
        ]

    view = SimpleNamespace(
        facts=SimpleNamespace(by_kind=by_kind),
        dispositions={"dispositions": list(cand.dispositions)},
        readme=cand.readme,
    )
    superseded = [
        r for r in cand.dispositions if r.get("disposition") == "SUPERSEDE_REDUNDANT"
    ]
    low = [(0.0, str(f.unit), f.detail) for f in superseded_failures(view)]
    counts: dict[str, int] = {}
    for row in cand.dispositions:
        key = str(row.get("disposition"))
        counts[key] = counts.get(key, 0) + 1
    return Dimension(
        "maintainer_preservation",
        bool(cand.dispositions) and not low,
        {
            "dispositions": counts,
            "superseded": len(superseded),
            "superseded_carried": len(superseded) - len(low),
            "superseded_not_carried": len(low),
            "judged_by": "validation.supersession (BC-05)",
            "has_dispositions": bool(cand.dispositions),
        },
        [
            f"superseded unit not carried ({s:.2f}) {u}: {_label(t)}"
            for s, u, t in sorted(low)
        ][:25]
        + (
            []
            if cand.dispositions
            else ["no dispositions.json: preservation cannot be shown"]
        ),
    )


@dataclass
class ParityResult:
    repository: str
    lane: str
    parity: bool
    dimensions: list[Dimension]
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "lane": self.lane,
            "parity": self.parity,
            "context": self.context,
            "dimensions": {d.name: asdict(d) for d in self.dimensions},
        }


#: The dimensions about content a candidate carries from the benchmark: what the blocking check
#: (``validation/parity.py``) enforces. ``maintainer_preservation`` is BC-05 itself
#: (``validation/supersession.py``); ``links`` and ``internal_markers`` are BC-06/BC-07's;
#: ``verified_examples`` compares counts and has no item to route.
CONTENT_DIMENSIONS = ("section_coverage", "technical_content")


def content_losses(candidate: SealedCandidate, benchmark_text: str) -> list[Loss]:
    """Every benchmark item the content dimensions find lost: the ONE judgement both the parity
    gate (``ops/checks/parity_gate.py``, through :func:`evaluate`) and the blocking check make."""
    bench = read_markdown(benchmark_text)
    cand_doc = read_markdown(candidate.readme)
    acct = Accounting(candidate)
    return [
        *section_coverage(bench, cand_doc, acct).losses,
        *technical_content(bench, cand_doc, candidate, acct).losses,
    ]


def evaluate(
    repository: str,
    candidate: SealedCandidate,
    benchmark_text: str,
    context: Mapping[str, Any] | None = None,
) -> ParityResult:
    bench = read_markdown(benchmark_text)
    cand_doc = read_markdown(candidate.readme)
    acct = Accounting(candidate)
    dims = [
        section_coverage(bench, cand_doc, acct),
        technical_content(bench, cand_doc, candidate, acct),
        verified_examples(bench, cand_doc, candidate),
        links(cand_doc, candidate),
        markers(candidate),
        maintainer_preservation(bench, candidate, acct),
        maintainability(bench, cand_doc),
        required_sections(bench, cand_doc),
        badge_banner_completeness(bench, cand_doc),
    ]
    return ParityResult(
        repository,
        candidate.lane,
        all(d.passed for d in dims),
        dims,
        dict(context or {}),
    )


def not_measured(
    repository: str, lane: str, why: str, context: Mapping[str, Any] | None = None
) -> ParityResult:
    """No parity without a measurement: every dimension fails with the reason."""
    dims = [Dimension(name, False, {}, [why]) for name in DIMENSIONS]
    return ParityResult(
        repository, lane, False, dims, {"not_measured": why, **dict(context or {})}
    )


def render(results: Sequence[ParityResult]) -> str:
    out = []
    for result in results:
        ctx = result.context
        head = f"{result.repository} lane {result.lane}: {'PARITY' if result.parity else 'NO PARITY'}"
        if ctx.get("version_set_label"):
            head += f"  [{ctx['version_set_label']}]"
        out.append(head)
        if ctx.get("not_measured"):
            out.append(f"  not measured: {ctx['not_measured']}")
            continue
        for dim in result.dimensions:
            nums = json.dumps(dim.numbers, sort_keys=True, separators=(",", ":"))
            out.append(f"  {'PASS' if dim.passed else 'FAIL'} {dim.name} {nums}")
            for line in dim.details[:8]:
                out.append(f"       - {line}")
            if len(dim.details) > 8:
                out.append(f"       - ... {len(dim.details) - 8} more")
    return "\n".join(out)


# --- live inputs: the seal and the upstream README (read-only) -------------------------------


@dataclass(frozen=True)
class SelectedSeal:
    commit: str
    revision: str
    manifest_state: str
    fingerprint: str | None
    counted: bool
    revision_dir: Path


def materialize_seals(
    repositories: Iterable[str],
    scratch: Path,
    *,
    remote: str = "origin",
    token: str | None = None,
) -> dict[tuple[str, str], list[tuple[Any, Path]]]:
    """Every seal of ``repositories`` on ``remote``'s bundle refs, oldest first, each verified by
    ``bundle_store._read_seal`` (the same check ``seal_history`` applies) and left extracted under
    ``scratch`` so its facts and dispositions can be read. Read-only: one fetch, nothing pushed."""
    from repo_presenter.core.errors import StateBackendError
    from repo_presenter.core.state.bundle_store import (
        _HISTORY_REF_PREFIX,
        BUNDLE_REF_PREFIX,
        BundleStoreError,
        _git,
        _read_seal,
        _slug,
        parse_bundle_ref,
    )
    from repo_presenter.core.state.git_backend import GitStateBackend

    wanted = set(repositories)
    found: dict[tuple[str, str], list[tuple[Any, Path]]] = {}
    try:
        with GitStateBackend(remote=remote, token=token) as backend, backend._lock:
            fetched = backend._run_remote_git(
                [
                    "fetch",
                    "--no-write-fetch-head",
                    "--no-tags",
                    backend._remote,
                    f"+{BUNDLE_REF_PREFIX}/*:{_HISTORY_REF_PREFIX}/*",
                ]
            )
            if fetched.returncode != 0:
                raise BundleStoreError(
                    f"fetch of the bundle history failed: {fetched.stderr.strip()}"
                )
            listed = _git(
                backend,
                ["for-each-ref", "--format=%(refname)", _HISTORY_REF_PREFIX],
                "for-each-ref",
            )
            for local in sorted(filter(None, listed.splitlines())):
                parsed = parse_bundle_ref(
                    BUNDLE_REF_PREFIX + local[len(_HISTORY_REF_PREFIX) :]
                )
                if parsed is None or parsed[0] not in wanted:
                    continue
                repository, lane = parsed
                where = scratch / lane / _slug(repository)
                commits = _git(
                    backend, ["rev-list", "--reverse", local], "rev-list"
                ).split()
                rows = []
                for commit in commits:
                    seal = _read_seal(backend._git_cwd, commit, repository, lane, where)
                    rows.append((seal, where / commit / seal.revision))
                found[parsed] = rows
    except StateBackendError as exc:
        raise BundleStoreError(str(exc)) from exc
    return found


def select_seal(
    rows: Sequence[tuple[Any, Path]], lane: str, current: str, *, older: bool = False
) -> SelectedSeal | None:
    """The latest pipeline-good seal under the CURRENT version set (or, ``older=True``, the latest
    pipeline-good seal under any OTHER set -- a dry measurement, never release evidence)."""
    from repo_presenter.core.version_set import fingerprint

    for seal, path in reversed(rows):
        if not seal.pipeline_good or not seal.dependencies:
            continue
        value = fingerprint(seal.dependencies, lane)
        if (value == current) != older:
            return SelectedSeal(
                seal.commit,
                seal.revision,
                seal.manifest_state,
                value,
                seal.counted,
                path,
            )
    return None


@dataclass(frozen=True)
class Benchmark:
    text: str
    head: str
    readme_path: str
    clone_path: Path


def fetch_benchmark(repository: str, workdir: Path) -> Benchmark:
    """The live upstream README at the default branch's current HEAD, read through the
    push-neutered pinned read-only clone (``core.git_safety.clone``)."""
    from repo_presenter.core.git_safety.clone import pinned_read_only_clone

    clone = pinned_read_only_clone(
        f"https://github.com/{repository}.git", workdir / repository.replace("/", "__")
    )
    names = {p.name for p in clone.path.iterdir() if p.is_file()}
    readme = next(
        (n for n in ("README.md", "readme.md", "Readme.md") if n in names), None
    )
    if readme is None:
        raise FileNotFoundError(
            f"{repository}@{clone.revision}: no README.md at the root"
        )
    text = (clone.path / readme).read_text(encoding="utf-8")
    return Benchmark(text, clone.revision, readme, clone.path)


def readme_changed_since(benchmark: Benchmark, revision: str) -> bool | None:
    """Whether the benchmark README differs from the README at the seal's source ``revision``
    (``None`` when that revision cannot be read). A read-only fetch into the scratch clone."""
    from repo_presenter.core.git_safety.git import run_git

    if revision == benchmark.head:
        return False
    got = run_git(
        ["fetch", "--depth", "1", "origin", revision],
        cwd=benchmark.clone_path,
        timeout=120,
    )
    if got.returncode != 0:
        return None
    old = run_git(
        ["rev-parse", f"{revision}:{benchmark.readme_path}"], cwd=benchmark.clone_path
    )
    new = run_git(
        ["rev-parse", f"HEAD:{benchmark.readme_path}"], cwd=benchmark.clone_path
    )
    if old.returncode != 0 or new.returncode != 0:
        return None
    return old.stdout.strip() != new.stdout.strip()
