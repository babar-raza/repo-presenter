"""BC-06: every link resolves, Aspose links stay within their ceilings, edition names are canonical,
and no unsafe raw HTML renders outside a fence.

ADAPT from the old repository-presenter project's ``components/readme/validation/registry.py``
(``_check_links`` and its helpers) and ``components/readme/evidence/facts/links.py``
(``check_anchor``, ``check_relative``, ``LinkResult``). Two changes, each named:

* ``enterprise_anchor_problems`` is not called. It required the Enterprise Edition anchor to open
  "full-featured" (see ``rules.py``), which the mission's owner correction R2/R3 retired.
* ``check_anchor`` and ``check_relative`` are the pure local-link judges only. The live-fetching
  half of the old module (``fetch_status``, ``check_external``) is extraction-time and stays
  unported; external links are judged here by their recorded ``link_target`` fact.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote, urlsplit

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.readme.composition.authoring import EDITION_SUBSTITUTE
from repo_presenter.readme.composition.link_budget import slot_violations
from repo_presenter.readme.evidence.facts.links import extract_links, heading_slugs
from repo_presenter.readme.validation.failures import Candidate, Failure
from repo_presenter.readme.validation.rules import readme_link_budget
from repo_presenter.readme.validation.text import (
    LINK_DESTINATION,
    located,
    outside_fences,
    section_lines,
    visible_prose,
)

LinkOutcome = Literal["RESOLVED", "MISSING", "UNCHECKED"]
ASPOSE_HOSTS = frozenset({"aspose.com", "aspose.org", "aspose.app", "aspose.cloud"})
ASPOSE_SUFFIXES = (".aspose.com", ".aspose.org", ".aspose.app", ".aspose.cloud")
_EDITION = re.compile(r"\b([A-Z][A-Za-z]+) Edition\b")
# The raw-HTML hazards no other check reached: a standalone or block-level tag that executes or
# navigates on its own, an inline event-handler attribute (onerror=, onload=, ...), and a
# javascript:/vbscript: scheme where a URL is read. Scanned outside fenced code blocks only: a
# fence renders as inert text, so a documentation example quoting one of these is not the hazard.
_UNSAFE_HTML_TAG = re.compile(r"(?is)<\s*/?\s*(script|iframe|object|embed|meta|base)\b")
_EVENT_HANDLER_ATTR = re.compile(r"(?is)\bon[a-z]+\s*=\s*[\"']")
# A scheme is a hazard only at a position a URL is read: a markdown link or image destination,
# a reference definition, an autolink, or the value of a URL-bearing attribute (SVG's values, to,
# from and by set an href through an animation, so they count).
_URL_ATTRIBUTES = (
    "href",
    "src",
    "action",
    "formaction",
    "data",
    "poster",
    "background",
    "cite",
    "codebase",
    "longdesc",
    "lowsrc",
    "dynsrc",
    "srcset",
    "values",
    "to",
    "from",
    "by",
)
_MD_DESTINATION = re.compile(r"\]\(\s*<?(?P<url>[^\s<>)]*)")
_MD_REFERENCE_DEFINITION = re.compile(
    r"(?m)^[ ]{0,3}\[[^\]\n]+\]:[ \t]*<?(?P<url>[^\s<>]*)"
)
_AUTOLINK = re.compile(r"<(?P<url>[^\s<>]*)")
_HTML_URL_ATTRIBUTE = re.compile(
    r"(?i)(?<![\w.:-])(?:[\w.-]+:)?(?:" + "|".join(_URL_ATTRIBUTES) + r")\s*=\s*"
    r"""(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<bare>[^\s"'>]+))"""
)
_DANGEROUS_SCHEME = re.compile(r"(?i)(?:javascript|vbscript):")
_URL_CONTROLS = "".join(chr(code) for code in range(0x21))
_URL_TAB_OR_NEWLINE = re.compile(r"[\t\n\r]")


@dataclass(frozen=True)
class LinkResult:
    outcome: LinkOutcome
    detail: str


def check_anchor(href: str, slugs: set[str]) -> LinkResult:
    """An in-page anchor must name a heading the README renders."""
    slug = unquote(href[1:]).lower()
    if slug in slugs:
        return LinkResult("RESOLVED", f"heading #{slug} exists")
    return LinkResult("MISSING", f"no heading #{slug}")


def check_relative(href: str, tree_paths: Sequence[str]) -> LinkResult:
    """A repository path (or directory) the tree inventory must contain."""
    path = unquote(urlsplit(href).path)
    while path.startswith("./"):
        path = path[2:]
    path = path.strip("/")
    if not path:
        return LinkResult("MISSING", "empty path")
    if path in tree_paths or any(entry.startswith(path + "/") for entry in tree_paths):
        return LinkResult("RESOLVED", f"tree contains {path}")
    return LinkResult("MISSING", f"tree does not contain {path}")


def _is_aspose(host: str) -> bool:
    return host in ASPOSE_HOSTS or host.endswith(ASPOSE_SUFFIXES)


def _renderer_owned(candidate: Candidate, href: str) -> bool:
    """A target the renderer derives from verified facts rather than from the README's links: the
    ecosystem's own registry page, read generically off ``EcosystemSpec.badge``, and the
    repository's own GitHub pages, shields.io badges."""
    parts = urlsplit(href)
    host = (parts.hostname or "").lower()
    if host == "img.shields.io":
        return True
    if host == "github.com":
        return parts.path.startswith(f"/{candidate.entry.repository}/")
    package = next(
        (f.value for f in candidate.facts.by_kind("package") if f.id == "package:name"),
        None,
    )
    if package is None:
        return False
    badge = spec_for(candidate.entry.ecosystem).badge(package)
    destinations: list[str] = LINK_DESTINATION.findall(badge)
    if not destinations:
        return False
    # The badge markdown is ``[![alt](img_url)](link_url)``; the last ``](...)`` is the
    # click-through target, the one link a reader can follow.
    target = destinations[-1].removeprefix("](").removesuffix(")")
    return href.rstrip("/") == target.rstrip("/")


def _is_dangerous_url(value: str) -> bool:
    """Whether a URL read at a URL position carries a javascript:/vbscript: scheme, judged the way
    a renderer reads it: character references decode first, then a browser drops ASCII tab and
    newline anywhere and leading C0 controls and spaces before it reads the scheme."""
    url = _URL_TAB_OR_NEWLINE.sub("", html.unescape(value)).lstrip(_URL_CONTROLS)
    return _DANGEROUS_SCHEME.match(url) is not None


def _dangerous_url_spans(prose_text: str) -> list[tuple[int, str]]:
    """Every (offset, span) where a javascript:/vbscript: scheme sits at a URL position."""
    found: list[tuple[int, str]] = []
    for pattern in (_MD_DESTINATION, _MD_REFERENCE_DEFINITION, _AUTOLINK):
        for match in pattern.finditer(prose_text):
            if _is_dangerous_url(match.group("url")):
                found.append((match.start(), match.group(0)))
    for match in _HTML_URL_ATTRIBUTE.finditer(prose_text):
        value = match.group("dq") or match.group("sq") or match.group("bare") or ""
        if _is_dangerous_url(value):
            found.append((match.start(), match.group(0)))
    return found


def unsafe_html_failures(readme: str) -> list[Failure]:
    """Every executing or navigating raw-HTML hazard outside a fenced code block, each distinct
    span named once in document order so a repair has something concrete to remove. A scheme word
    in ordinary prose is not a URL and is not named."""
    prose_text = "\n".join(outside_fences(readme))
    found = [
        (match.start(), match.group(0))
        for pattern in (_UNSAFE_HTML_TAG, _EVENT_HANDLER_ATTR)
        for match in pattern.finditer(prose_text)
    ]
    found.extend(_dangerous_url_spans(prose_text))
    failures: list[Failure] = []
    seen: set[str] = set()
    for _, span in sorted(found):
        if span in seen:
            continue
        seen.add(span)
        failures.append(
            Failure("COMPOSING", f"unsafe raw HTML in the candidate: {span!r}")
        )
    return failures


def edition_substitute_failures(readme: str) -> list[Failure]:
    """plans/idea.md L51-53: Enterprise Edition is the only edition name. "commercial edition",
    "On-Premise edition", "paid version", "full version" or another substitute is forbidden in any
    letter case, and so is any other capitalised "Xxx Edition". Each distinct phrase is named once
    per section it renders in, in document order."""
    text = visible_prose(readme)
    found: list[tuple[int, str]] = [
        (match.start(), match.group(0))
        for match in _EDITION.finditer(text)
        if match.group(1) != "Enterprise"
    ]
    found += [
        (match.start(), match.group(0)) for match in EDITION_SUBSTITUTE.finditer(text)
    ]
    failures: list[Failure] = []
    seen: set[tuple[str, str | None]] = set()
    for offset, raw in sorted(found):
        phrase = " ".join(raw.split())
        section = located(readme, text, offset)
        if (phrase.lower(), section) in seen:
            continue
        seen.add((phrase.lower(), section))
        failures.append(
            Failure("COMPOSING", f"non-canonical edition name {phrase!r}", section)
        )
    return failures


def link_failures(candidate: Candidate) -> list[Failure]:
    """BC-06: local links resolve, external links are verified targets, Aspose links are within the
    ceilings the document's own size derives, edition names are canonical, and no unsafe raw HTML
    renders."""
    failures: list[Failure] = []
    failures.extend(unsafe_html_failures(candidate.readme))
    slugs = heading_slugs(candidate.readme)
    by_value = {fact.value: fact for fact in candidate.facts.by_kind("link_target")}
    # The Aspose ceiling bounds the contextual links the plan assigns; the banner and the
    # Enterprise target are shell-rendered from verified product facts and stand outside it.
    mandated = {
        fact.value
        for fact in candidate.facts.by_kind("link_target")
        if fact.id.startswith("link_target:product.") and fact.polarity == "SUPPORTED"
    }
    aspose_hrefs: list[str] = []
    sections = section_lines(candidate.readme)
    for target in extract_links(candidate.readme):
        if target.kind == "anchor":
            result = check_anchor(target.href, slugs)
            if result.outcome != "RESOLVED":
                section = (
                    sections[target.line - 1]
                    if 0 < target.line <= len(sections)
                    else None
                )
                failures.append(
                    Failure("COMPOSING", f"{target.href}: {result.detail}", section)
                )
        elif target.kind == "relative":
            result = check_relative(target.href, candidate.tree_paths)
            if result.outcome != "RESOLVED":
                failures.append(
                    Failure("EXTRACTING", f"{target.href}: {result.detail}")
                )
        elif target.kind == "external":
            host = (urlsplit(target.href).hostname or "").lower()
            if _is_aspose(host) and target.href not in mandated:
                aspose_hrefs.append(target.href)
            fact = by_value.get(target.href)
            if fact is not None:
                if fact.polarity != "SUPPORTED":
                    last = fact.evidence[-1].detail or "" if fact.evidence else ""
                    failures.append(
                        Failure(
                            "EXTRACTING", f"{target.href} is {fact.polarity}: {last}"
                        )
                    )
            elif not _renderer_owned(candidate, target.href):
                failures.append(
                    Failure("PLANNING", f"{target.href} is not a verified link target")
                )
        else:
            failures.append(
                Failure(
                    "COMPOSING",
                    f"{target.href}: {target.kind} links are never rendered",
                )
            )
    # Ceilings derived per document from its visible size and verified examples (or configured),
    # per total, per domain, and per surface slot.
    budget = readme_link_budget(candidate.readme, candidate.facts, candidate.policy)
    for problem in slot_violations(budget, aspose_hrefs):
        failures.append(
            Failure(
                "PLANNING",
                f"{problem} ({budget.mode} budget from {budget.measurement.visible_prose_words}"
                f" visible words and {budget.measurement.verified_examples} verified examples)",
            )
        )
    failures.extend(edition_substitute_failures(candidate.readme))
    return failures
