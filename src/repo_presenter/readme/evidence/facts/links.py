"""Link targets of a README: the pure, composition-side subset.

Ported (TRIMMED, ADAPT) from the old repository-presenter project's
``components/readme/evidence/facts/links.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). Only the pure text-processing functions composition's own planning/
placement/renderer/dispositions modules actually import are ported: ``LinkTarget``,
``extract_links`` (Markdown link/image discovery), ``heading_slug``/``heading_slugs`` (GitHub's
anchor form), and ``link_text`` (the anchor text a fact's own evidence recorded).

The live-fetching half of the old module -- ``fetch_status``/``check_external``/``check_relative``/
``check_anchor``/``link_facts``/``PrivateAddressError`` (one bounded HTTP request per external
link, SSRF-guarded, to actually verify a target) -- is extraction-time apparatus: it is how a
``link_target`` fact is first produced (SUPPORTED/CONTRADICTED/UNRESOLVED), not something
composition, which only ever reads already-extracted facts, needs. That belongs with
migration/reuse-manifest.yaml's separate "extraction, package ownership, public API verification,
example execution" entry (PENDING_REVIEW), not this taskcard's pull.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token

from repo_presenter.core.facts import Fact

LinkKind = Literal["external", "anchor", "relative", "mailto", "other"]
_SLUG_STRIP = re.compile(r"[^\w\- ]")


@dataclass(frozen=True)
class LinkTarget:
    """One distinct link of the README, at its first occurrence."""

    ordinal: int
    href: str
    kind: LinkKind
    line: int
    text: str


def _classify(href: str) -> LinkKind:
    lowered = href.lower()
    if lowered.startswith(("http://", "https://")):
        return "external"
    if lowered.startswith("mailto:"):
        return "mailto"
    if href.startswith("#"):
        return "anchor"
    if "://" in href or lowered.startswith(("javascript:", "data:", "tel:")):
        return "other"
    return "relative"


def _attr(token: Token, name: str) -> str:
    value = token.attrGet(name)
    return "" if value is None else str(value)


_HTML_OPEN_TAG = re.compile(r"(?is)^<(a|img)\b(.*)>\s*$")
_HTML_ATTR = re.compile(r"""(?is)([a-zA-Z][\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")


def _html_attrs(attrs_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, double, single, bare in _HTML_ATTR.findall(attrs_text):
        values[name.lower()] = double or single or bare
    return values


def _html_tag(html: str) -> tuple[str, dict[str, str]] | None:
    """(tag name, attributes) of a raw HTML fragment's own opening ``<a>`` or ``<img>`` tag, or
    None for anything else."""
    match = _HTML_OPEN_TAG.match(html.strip())
    if match is None:
        return None
    return match.group(1).lower(), _html_attrs(match.group(2))


def _is_html_close(token: Token, name: str) -> bool:
    return token.type == "html_inline" and token.content.strip().lower() == f"</{name}>"


def _inline_links(inline: Token, line: int, found: list[tuple[str, int, str]]) -> None:
    children = inline.children or []
    index = 0
    while index < len(children):
        child = children[index]
        if child.type == "image":
            found.append((_attr(child, "src"), line, child.content))
        elif child.type == "link_open":
            href = _attr(child, "href")
            text_parts: list[str] = []
            index += 1
            while index < len(children) and children[index].type != "link_close":
                inner = children[index]
                if inner.type == "image":
                    found.append((_attr(inner, "src"), line, inner.content))
                    text_parts.append(inner.content)
                elif inner.type in {"text", "code_inline"}:
                    text_parts.append(inner.content)
                index += 1
            found.append((href, line, "".join(text_parts).strip()))
        elif child.type == "html_inline":
            tag = _html_tag(child.content)
            if tag is None:
                pass
            elif tag[0] == "img":
                found.append((tag[1].get("src", ""), line, tag[1].get("alt", "")))
            else:  # tag[0] == "a"
                href = tag[1].get("href", "")
                text_parts = []
                index += 1
                while index < len(children) and not _is_html_close(children[index], "a"):
                    inner = children[index]
                    if inner.type == "image":
                        found.append((_attr(inner, "src"), line, inner.content))
                        text_parts.append(inner.content)
                    elif inner.type in {"text", "code_inline"}:
                        text_parts.append(inner.content)
                    elif inner.type == "html_inline":
                        inner_tag = _html_tag(inner.content)
                        if inner_tag is not None and inner_tag[0] == "img":
                            found.append(
                                (inner_tag[1].get("src", ""), line, inner_tag[1].get("alt", ""))
                            )
                    index += 1
                found.append((href, line, "".join(text_parts).strip()))
        index += 1


def extract_links(readme_text: str) -> list[LinkTarget]:
    """Every distinct link or image target in document order, with its line and link text."""
    tokens = MarkdownIt("commonmark").enable(["table", "strikethrough"]).parse(readme_text)
    found: list[tuple[str, int, str]] = []
    line = 1
    for token in tokens:
        if token.map is not None:
            line = token.map[0] + 1
        if token.type == "inline":
            _inline_links(token, line, found)
    targets: list[LinkTarget] = []
    seen: set[str] = set()
    for href, at_line, text in found:
        if not href or href in seen:
            continue
        seen.add(href)
        targets.append(LinkTarget(len(targets) + 1, href, _classify(href), at_line, text))
    return targets


def heading_slug(text: str) -> str:
    """GitHub's anchor form of a heading: lowercase, punctuation dropped, spaces to hyphens."""
    return _SLUG_STRIP.sub("", text.strip().lower()).replace(" ", "-")


def heading_slugs(readme_text: str) -> set[str]:
    tokens = MarkdownIt("commonmark").parse(readme_text)
    slugs: set[str] = set()
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            slugs.add(heading_slug(tokens[index + 1].content))
    return slugs


_LINK_TEXT = re.compile(r"text '(.*)'$")


def link_text(fact: Fact) -> str:
    """The words a reader clicks: the anchor text the source gave this target, else the URL."""
    for evidence in fact.evidence:
        match = _LINK_TEXT.search(evidence.detail or "")
        if match and match.group(1):
            return match.group(1)
    return fact.value
