"""Live product-page facts: the Enterprise Edition target, the product homepage, and the banner.

docs/RESEARCH_AND_GUIDELINES.md section 20 adopts the resolution shape, not the data: one live
lookup per candidate, platform first (``products.aspose.com/{family}/{platform}/`` through the
portfolio's known platform slugs) and the family page as the fallback, classified platform,
family, or unresolved. Two live platform variants with no rule to pick between them are
ambiguous and stay unresolved rather than silently chosen. README_CONTRACT.md row 3 needs a
verified illustration and homepage for the banner, so the same lookup records the product
homepage on products.aspose.org and its banner image, each SUPPORTED only on a live 200.
Nothing here guesses: an unreachable page is recorded as unresolved.

A fact's evidence is hashed into dependencies.json, so it carries only a verdict word per page
(RESOLVED, BROKEN or UNCHECKED); the HTTP status, the final URL after redirects and the time the
read took go to a ProbeRecord (``core/probes.py``, sealed unhashed as probes.json), so a changed
status with the same verdict reopens nothing (TC-INV-02).

``product_knowledge_refresh`` is the same live lookup declared explicitly as its own pipeline
stage (CONSOLIDATED_GOALS_2026-11-06.md section 4): a typed, named record of exactly what was
checked and whether it changed versus the last reading cached for this revision, rather than an
incidental fact kind indistinguishable from any other. ``extract.py`` calls it, not
``product_page_facts`` directly.
"""

from __future__ import annotations

import re
import time
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass

import httpx

from repo_presenter.core.facts import Evidence, Fact, fact_id
from repo_presenter.core.probes import ProbeRecord
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.evidence.facts import links

ENTERPRISE_FACT_ID = fact_id("link_target", "product.enterprise")
HOMEPAGE_FACT_ID = fact_id("link_target", "product.homepage")
BANNER_FACT_ID = fact_id("link_target", "product.banner")
ENTERPRISE_HOST = "https://products.aspose.com"
FOSS_HOST = "https://products.aspose.org"
# Platform slugs the portfolio publishes for each registry platform, the registry's own slug
# first; bridge slugs (python-net, go-cpp) are real, documented product pages (section 20).
PLATFORM_SLUGS: dict[str, tuple[str, ...]] = {
    "python": ("python", "python-net", "python-cpp", "python-java"),
    "net": ("net",),
    "java": ("java",),
    "cpp": ("cpp",),
    "go": ("go", "go-cpp"),
    "rust": ("rust", "rust-cpp"),
    "nodejs": ("nodejs", "nodejs-java", "nodejs-cpp"),
    "php": ("php", "php-java"),
}


def _verdict(status: int | None) -> str:
    """The verdict word a fact's evidence carries: RESOLVED on a live 200, BROKEN on any other
    answer, UNCHECKED when there was none."""
    if status is None:
        return "UNCHECKED"
    return "RESOLVED" if status == 200 else "BROKEN"


def _status(url: str, probes: list[ProbeRecord]) -> tuple[int | None, str]:
    """The live status of ``url`` and the URL it resolved to (the error name when unreachable,
    status None); the read is recorded in ``probes`` with its status and duration."""
    started = time.monotonic()
    try:
        status, final = links.fetch_status(url)
    except httpx.HTTPError as exc:
        status, final = None, type(exc).__name__
    probes.append(
        ProbeRecord(
            "link",
            url,
            _verdict(status),
            status=status,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            observation=final,
        )
    )
    return status, final


def _lookup(fact: str, url: str, role: str, probes: list[ProbeRecord]) -> Fact:
    status, _ = _status(url, probes)
    verdict = _verdict(status)
    if status == 200:
        return Fact(
            fact,
            "link_target",
            url,
            (Evidence(url, f"{verdict}; {role}"),),
            attributes={"role": role},
        )
    return Fact(
        fact,
        "link_target",
        url,
        (Evidence(url, f"{verdict}; {role}"),),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": role},
    )


def enterprise_fact(entry: RegistryEntry, probes: list[ProbeRecord]) -> Fact:
    """The Enterprise Edition target: the one live platform page, else the family page, else
    unresolved; two live platform variants are ambiguous and unresolved."""
    slugs = PLATFORM_SLUGS.get(entry.platform, (entry.platform,))
    live: list[tuple[str, str]] = []
    seen: list[str] = []
    for slug in slugs:
        url = f"{ENTERPRISE_HOST}/{entry.family}/{slug}/"
        status, _ = _status(url, probes)
        seen.append(f"{slug}: {_verdict(status)}")
        if status == 200:
            live.append((slug, url))
    if len(live) == 1:
        slug, url = live[0]
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (
                Evidence(
                    url, f"RESOLVED; enterprise target; platform level; slug {slug}"
                ),
            ),
            attributes={
                "role": "enterprise",
                "level": "platform",
                "platform": entry.platform,
            },
        )
    if len(live) > 1:
        variants = ", ".join(slug for slug, _ in live)
        url = f"{ENTERPRISE_HOST}/{entry.family}/"
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (
                Evidence(
                    url, f"ambiguous platform targets: {variants}; enterprise target"
                ),
            ),
            polarity="UNRESOLVED",
            confidence=0.5,
            attributes={
                "role": "enterprise",
                "level": "ambiguous",
                "platform": entry.platform,
                "variants": ",".join(slug for slug, _ in live),
            },
        )
    family_url = f"{ENTERPRISE_HOST}/{entry.family}/"
    status, _ = _status(family_url, probes)
    if status == 200:
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            family_url,
            (
                Evidence(
                    family_url,
                    f"RESOLVED; enterprise target; family level; platform pages {'; '.join(seen)}",
                ),
            ),
            attributes={"role": "enterprise", "level": "family"},
        )
    return Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        family_url,
        (
            Evidence(
                family_url,
                f"{_verdict(status)}; enterprise target; platform pages {'; '.join(seen)}",
            ),
        ),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": "enterprise", "level": "unresolved"},
    )


def product_page_facts(
    entry: RegistryEntry, probes: list[ProbeRecord] | None = None
) -> list[Fact]:
    """The three live product-page facts for the entry, each SUPPORTED only on a live 200.

    Every page read is appended to ``probes`` when given (status, final URL, duration), so the
    caller can seal it unhashed; the facts carry the verdict only."""
    probes = [] if probes is None else probes
    homepage = f"{FOSS_HOST}/{entry.family}/{entry.platform}/"
    banner = f"{FOSS_HOST}/media/{entry.family}/{entry.platform}/banner-readme.png"
    return [
        enterprise_fact(entry, probes),
        _lookup(HOMEPAGE_FACT_ID, homepage, "product homepage", probes),
        _lookup(BANNER_FACT_ID, banner, "banner illustration", probes),
    ]


REFRESH_FACT_ID = fact_id("identity", "product-knowledge-refresh")

#: Process-lifetime fallback cache for :func:`product_knowledge_refresh` when a caller passes no
#: ``cache`` of its own: keyed ``(repository, source_revision)`` -> the statuses last observed
#: for that exact revision, so a second extraction of the SAME revision in the same process can
#: tell "unchanged" from "first reading", while a different revision is always a different key.
_REFRESH_CACHE: dict[tuple[str, str], tuple[int | None, ...]] = {}


@dataclass(frozen=True)
class CheckedPage:
    """One page the product-knowledge refresh stage checked: what it is, the URL it read, and
    the HTTP status that URL answered with (``None`` when the read failed outright)."""

    role: str
    url: str
    status: int | None


@dataclass(frozen=True)
class ProductKnowledgeRefresh:
    """What the product/platform knowledge refresh stage (CONSOLIDATED_GOALS_2026-11-06.md
    section 4, "refresh product/platform knowledge... before generation") actually checked for
    one repository at one revision, and whether either page's answer changed versus the last
    reading cached for that exact ``(repository, source_revision)`` pair. A different revision is
    always a different cache key, so a genuinely changed source tree is never read as "unchanged"
    against stale history, and a first-ever reading for a revision is never reported as a change
    (there is nothing yet to have changed from)."""

    repository: str
    source_revision: str
    checked: tuple[CheckedPage, ...]
    changed: bool

    def summary_fact(self) -> Fact:
        """A single, named, distinctly-tagged artifact recording this refresh in the facts
        document -- not just the loose ``link_target`` facts :func:`product_page_facts` already
        produces, which carry no record of this being a declared pipeline stage at all."""
        evidence = tuple(
            Evidence(page.url, f"{page.role}; status {page.status}") for page in self.checked
        )
        value = (
            f"checked {len(self.checked)} page(s) at revision {self.source_revision[:12]}; "
            f"changed={self.changed}"
        )
        return Fact(
            REFRESH_FACT_ID,
            "identity",
            value,
            evidence,
            attributes={
                "stage": "product_knowledge_refresh",
                "changed": "true" if self.changed else "false",
                **{
                    f"{page.role}_status": "unchecked" if page.status is None else str(page.status)
                    for page in self.checked
                },
            },
        )


def product_knowledge_refresh(
    entry: RegistryEntry,
    probes: list[ProbeRecord],
    source_revision: str,
    *,
    cache: MutableMapping[tuple[str, str], tuple[int | None, ...]] | None = None,
) -> tuple[ProductKnowledgeRefresh, list[Fact]]:
    """The product/platform knowledge refresh as its own declared pipeline stage, not merely an
    incidental fact kind: re-probes the product homepage and the Enterprise Edition target live
    (through the same probes ``product_page_facts`` already calls -- one live pass, not two),
    names exactly what was checked and each resulting HTTP status, and reports whether either
    answer changed versus this exact revision's own last-cached reading.

    Returns ``(result, facts)`` -- ``facts`` is ``product_page_facts``'s own three facts plus one
    more, ``result.summary_fact()``, so a caller that extends its facts list with the second
    element gets both the existing product-page facts and this stage's own named record."""
    cache = _REFRESH_CACHE if cache is None else cache
    facts = product_page_facts(entry, probes)
    homepage = next(f for f in facts if f.id == HOMEPAGE_FACT_ID)
    enterprise = next(f for f in facts if f.id == ENTERPRISE_FACT_ID)

    def _status_of(url: str) -> int | None:
        return next((p.status for p in reversed(probes) if p.target == url), None)

    checked = (
        CheckedPage("product_homepage", homepage.value, _status_of(homepage.value)),
        CheckedPage("enterprise_target", enterprise.value, _status_of(enterprise.value)),
    )
    key = (entry.repository, source_revision)
    previous = cache.get(key)
    current = tuple(page.status for page in checked)
    changed = previous is not None and previous != current
    cache[key] = current
    result = ProductKnowledgeRefresh(entry.repository, source_revision, checked, changed)
    return result, [*facts, result.summary_fact()]


def enterprise_target(facts: tuple[Fact, ...] | list[Fact]) -> Fact | None:
    """The SUPPORTED Enterprise Edition target fact, or None when unresolved or absent."""
    for fact in facts:
        if fact.id == ENTERPRISE_FACT_ID and fact.polarity == "SUPPORTED":
            return fact
    return None


def enterprise_from_readme_link(facts: Sequence[Fact]) -> Fact | None:
    """The Enterprise Edition target chosen by the upstream's own README, when the live lookup was
    ambiguous: the one rule that picks between two live platform pages.

    ``enterprise_fact`` refuses to choose between live variants (``python`` and ``python-net`` both
    answer for Slides-Python) because nothing picks one. The maintainers did: their README links
    one of them from its Enterprise Edition paragraph, and the link extractor read that page live
    (RESOLVED). That is a verified target; leaving the fact unresolved dropped the paragraph from
    the candidate (wave-3 acceptance review, Slides-Python). Only a link to one of the variants the
    lookup itself found live, labelled as the Enterprise Edition, and unique among such links,
    settles it; anything else stays unresolved. Returns None when nothing is settled."""
    current = next((f for f in facts if f.id == ENTERPRISE_FACT_ID), None)
    attributes = (current.attributes or {}) if current is not None else {}
    if current is None or attributes.get("level") != "ambiguous":
        return None
    family = current.value.removeprefix(f"{ENTERPRISE_HOST}/").strip("/")
    variants = set(filter(None, attributes.get("variants", "").split(",")))
    chosen: dict[str, str] = {}
    for fact in facts:
        if (
            fact.kind != "link_target"
            or fact.polarity != "SUPPORTED"
            or fact.id == current.id
        ):
            continue
        if not any("enterprise" in (e.detail or "").lower() for e in fact.evidence):
            continue
        match = re.fullmatch(
            rf"{re.escape(ENTERPRISE_HOST)}/{re.escape(family)}/([^/?#]+)/?", fact.value
        )
        if match is not None and match.group(1) in variants:
            chosen[match.group(1)] = fact.value
    if len(chosen) != 1:
        return None
    ((slug, url),) = chosen.items()
    return Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        url,
        (
            Evidence(
                url,
                f"RESOLVED; enterprise target; platform level; slug {slug}; "
                "chosen by the README's own Enterprise Edition link",
            ),
        ),
        attributes={
            "role": "enterprise",
            "level": "platform",
            **(
                {"platform": attributes["platform"]}
                if attributes.get("platform")
                else {}
            ),
        },
    )


def banner_target(facts: tuple[Fact, ...] | list[Fact]) -> tuple[Fact, Fact] | None:
    """The SUPPORTED banner illustration and homepage facts (README_CONTRACT.md row 3), or None
    when either is unresolved: the banner is then omitted entirely, never unlinked or broken."""
    supported = {fact.id: fact for fact in facts if fact.polarity == "SUPPORTED"}
    banner = supported.get(BANNER_FACT_ID)
    homepage = supported.get(HOMEPAGE_FACT_ID)
    if banner is None or homepage is None:
        return None
    return banner, homepage
