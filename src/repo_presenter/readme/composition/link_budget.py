"""Aspose-link ceilings derived per document, per domain, and per surface slot.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/link_budget.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). A pure function of the policy, the measured document, and the link list: no
I/O, no model call, no clock.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

LINK_BUDGET_VERSION = "1"
DOMAINS: tuple[str, ...] = ("aspose.org", "aspose.com")
SURFACES: tuple[str, ...] = ("products", "docs", "kb", "blog", "reference")
OTHER_ASPOSE_DOMAINS: tuple[str, ...] = ("aspose.app", "aspose.cloud")
ASPOSE_DOMAINS: tuple[str, ...] = (*DOMAINS, *OTHER_ASPOSE_DOMAINS)
AUTOMATIC_TOTAL_CAP = 4
LARGEST_CONTENT_UNITS = 10**9
EXAMPLE_UNITS = 100

_URL = re.compile(r"https?://[^\s<>()\]]+", re.IGNORECASE)
_WORD = re.compile(r"\b[\w][\w.+#-]*\b", re.UNICODE)
_DETAILS_OPEN = re.compile(r"(?i)<details\b")
_DETAILS_CLOSE = re.compile(r"(?i)</details\s*>")


@dataclass(frozen=True)
class LinkAllocationPolicy:
    """Explicitly configured maxima. When present they replace every automatic value."""

    max_total: int
    aspose_org: int
    aspose_com: int
    products: int
    docs: int
    kb: int
    blog: int
    reference: int

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"link allocation {name} must be a non-negative integer")

    def as_dict(self) -> dict[str, int]:
        return {
            "max_total": self.max_total,
            "aspose_org": self.aspose_org,
            "aspose_com": self.aspose_com,
            "products": self.products,
            "docs": self.docs,
            "kb": self.kb,
            "blog": self.blog,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class ContentMeasurement:
    """Visible content size: prose words outside ``<details>`` plus verified examples."""

    visible_prose_words: int
    verified_examples: int

    @property
    def total_units(self) -> int:
        return self.visible_prose_words + EXAMPLE_UNITS * self.verified_examples


@dataclass(frozen=True)
class LinkBudget:
    """Concrete ceilings for one document."""

    mode: str  # "auto" or "configured"
    measurement: ContentMeasurement
    max_total: int
    domain_maxima: Mapping[str, int] = field(default_factory=dict)
    surface_maxima: Mapping[str, int] = field(default_factory=dict)


def plan_time_budget(
    configured: LinkAllocationPolicy | None = None, cap: int = AUTOMATIC_TOTAL_CAP
) -> LinkBudget:
    """The ceilings the plan stage trims to: the largest the policy admits for any document."""
    return resolve_link_budget(ContentMeasurement(LARGEST_CONTENT_UNITS, 0), configured, cap)


def code_sha256(code: str) -> str:
    """The normalized code digest that recognizes a verified example."""
    return hashlib.sha256(code.replace("\r\n", "\n").strip().encode("utf-8")).hexdigest()


def _inline_words(children: Iterable[Token]) -> int:
    words = 0
    for child in children:
        if child.type in {"text", "code_inline"}:
            words += len(_WORD.findall(_URL.sub(" ", child.content)))
    return words


def measure_content(markdown: str, verified_code_sha256s: Iterable[str] = ()) -> ContentMeasurement:
    """Count visible prose words (outside ``<details>``) and verified fenced examples (anywhere)."""
    verified = set(verified_code_sha256s)
    depth = 0
    words = 0
    examples = 0
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type == "html_block":
            depth += len(_DETAILS_OPEN.findall(token.content))
            depth = max(depth - len(_DETAILS_CLOSE.findall(token.content)), 0)
        elif token.type == "inline" and token.children and depth == 0:
            words += _inline_words(token.children)
        elif (
            token.type == "fence"
            and token.info.strip().casefold() != "mermaid"
            and code_sha256(token.content) in verified
        ):
            examples += 1
    return ContentMeasurement(words, examples)


def _automatic_total(units: int, cap: int) -> int:
    """The automatic ceiling for a document of ``units`` (visible words plus verified examples).

    Calibrated against the portfolio's own finalized READMEs (independent measurement, 2026-10-31,
    all 35 aspose.org candidates): none has fewer than 586 visible words, and every one that carries
    the fixed Documentation & Resources section needs four contextual Aspose links (a products, a
    docs, a kb and a reference link) beside the banner and the Enterprise Edition link. The earlier
    tiers (up to 600 units 2, up to 1,200 units 3) gave 3 to a document of 1,153 words and no
    verified example, which is the Words-.NET BC-06 failure, and would have failed 23 of those 35
    reference READMEs. A ceiling stays a ceiling: a short document is still held to fewer links.
    """
    for bound, total in ((300, 2), (500, 3), (2_000, 4), (3_000, 5)):
        if units <= bound:
            return min(total, cap)
    return min(6, cap)


def resolve_link_budget(
    measurement: ContentMeasurement,
    configured: LinkAllocationPolicy | None = None,
    cap: int = AUTOMATIC_TOTAL_CAP,
) -> LinkBudget:
    """The exact ceilings: configured values replace every automatic one; the automatic total
    never exceeds ``cap``."""
    if configured is not None:
        return LinkBudget(
            "configured",
            measurement,
            configured.max_total,
            {"aspose.org": configured.aspose_org, "aspose.com": configured.aspose_com},
            {surface: configured.as_dict()[surface] for surface in SURFACES},
        )
    total = _automatic_total(measurement.total_units, cap)
    return LinkBudget(
        "auto",
        measurement,
        total,
        {
            "aspose.org": total,
            "aspose.com": math.ceil(total / 2),
        },
        {
            "products": min(2, total),
            "docs": min(2, total),
            "kb": min(2, total),
            "blog": min(1, total),
            "reference": min(2, total),
        },
    )


@dataclass(frozen=True)
class LinkSlot:
    """Where one Aspose href lands: its budgeted domain (None for aspose.app/.cloud) and surface."""

    domain: str | None
    surface: str | None


def classify_link(href: str) -> LinkSlot | None:
    """The slot an Aspose href occupies, or ``None`` when it is not an Aspose host at all."""
    host = (urlsplit(href).hostname or "").lower()
    for domain in ASPOSE_DOMAINS:
        if host == domain or host.endswith("." + domain):
            label = host[: -len(domain) - 1].split(".")[-1] if host != domain else ""
            surface = label if label in SURFACES else None
            return LinkSlot(domain if domain in DOMAINS else None, surface)
    return None


def slot_violations(budget: LinkBudget, hrefs: Iterable[str]) -> list[str]:
    """Every ceiling the Aspose ``hrefs`` exceed, one sentence each; empty when all hold."""
    total = 0
    by_domain: dict[str, int] = {}
    by_surface: dict[str, int] = {}
    for href in hrefs:
        slot = classify_link(href)
        if slot is None:
            continue
        total += 1
        if slot.domain is not None:
            by_domain[slot.domain] = by_domain.get(slot.domain, 0) + 1
        if slot.surface is not None:
            by_surface[slot.surface] = by_surface.get(slot.surface, 0) + 1
    problems: list[str] = []
    if total > budget.max_total:
        problems.append(f"{total} Aspose links exceed the ceiling of {budget.max_total}")
    for domain in DOMAINS:
        if by_domain.get(domain, 0) > budget.domain_maxima.get(domain, 0):
            problems.append(
                f"{by_domain[domain]} {domain} links exceed the {domain} ceiling of "
                f"{budget.domain_maxima.get(domain, 0)}"
            )
    for surface in SURFACES:
        if by_surface.get(surface, 0) > budget.surface_maxima.get(surface, 0):
            problems.append(
                f"{by_surface[surface]} {surface} links exceed the {surface} slot ceiling of "
                f"{budget.surface_maxima.get(surface, 0)}"
            )
    return problems


class SlotCounter:
    """Admits Aspose links one at a time against a budget; used by the plan-time trim."""

    def __init__(self, budget: LinkBudget) -> None:
        self.budget = budget
        self.total = 0
        self.domains: dict[str, int] = {}
        self.surfaces: dict[str, int] = {}

    def would_fit(self, href: str) -> bool:
        slot = classify_link(href)
        if slot is None:
            return True
        if self.total + 1 > self.budget.max_total:
            return False
        if slot.domain is not None and self.domains.get(slot.domain, 0) + 1 > (
            self.budget.domain_maxima.get(slot.domain, 0)
        ):
            return False
        return not (
            slot.surface is not None
            and self.surfaces.get(slot.surface, 0) + 1
            > self.budget.surface_maxima.get(slot.surface, 0)
        )

    def add(self, href: str) -> None:
        slot = classify_link(href)
        if slot is None:
            return
        self.total += 1
        if slot.domain is not None:
            self.domains[slot.domain] = self.domains.get(slot.domain, 0) + 1
        if slot.surface is not None:
            self.surfaces[slot.surface] = self.surfaces.get(slot.surface, 0) + 1
