"""Quality parity of one sealed candidate against the README already published upstream (R2).

Owner ruling R2 (``docs/CONSOLIDATED_GOALS_2026-11-06.md``): the aspose.org readme-refresh output
already live upstream is the **minimum quality floor** for both lanes. This module recomputes, from
the two texts and the seal's own evidence (``facts.json``, ``dispositions.json`` for Lane R,
``corrections.json`` for Lane L), six objective, deterministic dimensions, each pass/fail with
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
)
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

    @property
    def h2(self) -> tuple[str, ...]:
        return tuple(name for level, name in self.headings if level == 2)


def read_markdown(text: str) -> Document:
    tokens = MarkdownIt("commonmark").enable(["table", "strikethrough"]).parse(text)
    headings: list[tuple[int, str]] = []
    fences: list[Fence] = []
    inline: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            headings.append((int(token.tag[1]), tokens[index + 1].content.strip()))
        elif token.type in {"fence", "code_block"}:
            fences.append(Fence(token.info.strip(), token.content))
        elif token.type == "inline":
            inline.extend(
                c.content for c in token.children or [] if c.type == "code_inline"
            )
    hrefs = tuple(target.href for target in extract_links(text))
    return Document(text, tuple(headings), tuple(fences), tuple(inline), hrefs)


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

    def section_reason(self, heading: str) -> str | None:
        """Lane R: every content unit of the benchmark section has a non-loss disposition (or the
        section has none). Lane L: the heading line itself is inside an evidenced edit."""
        if self.candidate.lane == LANE_L:
            return self.reason(heading)
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
            return None
        audit = _load_audit()
        moved = 0
        for unit_id in members:
            row = self.rows.get(unit_id)
            if row is None:
                return None
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
            return None
        if moved:
            return f"{moved} of {len(members)} section units carried under other headings, rest non-loss"
        return f"all {len(members)} section units have non-loss dispositions"


# --- the six dimensions ---------------------------------------------------------------------


@dataclass
class Dimension:
    name: str
    passed: bool
    numbers: dict[str, Any]
    details: list[str] = field(default_factory=list)


def _label(text: str, limit: int = 70) -> str:
    return " ".join(text.split())[:limit]


def section_coverage(bench: Document, cand: Document, acct: Accounting) -> Dimension:
    cand_topics = [name for level, name in cand.headings if level in (2, 3)]
    present, justified, missing = 0, 0, []
    for heading in bench.h2:
        if any(topics_match(heading, other) for other in cand_topics):
            present += 1
            continue
        why = acct.section_reason(heading)
        if why:
            justified += 1
        else:
            missing.append(heading)
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
    code_blocks = [
        (f.code, True) for f in bench.fences if not f.is_command and f.code.strip()
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
                here = (
                    re.search(
                        r"(?<![\w.])v?" + re.escape(item) + r"(?![\w]|\.\d)",
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
            if why is None and category == "install_commands":
                tool = " ".join(item.split()[:2]).lower()
                if any(
                    v.lower().startswith(tool) and v in cand.readme
                    for v in install_facts
                ):
                    why = "replaced by the verified install command"
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
                details.append(
                    f"{category} lost: {_label(item.splitlines()[0] if is_code else item)}"
                )
        numbers[category] = {
            "benchmark": len(entries),
            "carried": carried,
            "accounted": accounted,
            "lost": len(entries) - carried - accounted,
        }
    numbers["lost_total"] = lost_total
    return Dimension("technical_content", lost_total == 0, numbers, details)


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
    audit = _load_audit()
    units = {
        str(f.get("id")): str(f.get("value") or "")
        for f in cand.by_kind("inherited_unit")
    }
    superseded = [
        r for r in cand.dispositions if r.get("disposition") == "SUPERSEDE_REDUNDANT"
    ]
    low = []
    for row in superseded:
        unit_id = str(row.get("unit_id"))
        score = audit.coverage(units.get(unit_id, ""), cand.readme)
        if score < audit.PARTIAL:
            low.append((round(score, 2), unit_id, units.get(unit_id, "")))
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
            "carried_bound": audit.PARTIAL,
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
