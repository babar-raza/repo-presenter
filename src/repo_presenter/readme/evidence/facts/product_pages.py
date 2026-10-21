"""Live product-page fact IDs and their pure, composition-side predicates.

Ported (TRIMMED, ADAPT) from the old repository-presenter project's ``components/readme/
evidence/facts/product_pages.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).
Only the fact-ID constants and the pure predicates over an already-extracted facts tuple are
ported: ``ENTERPRISE_FACT_ID``/``HOMEPAGE_FACT_ID``/``BANNER_FACT_ID``, ``banner_target()``,
``enterprise_target()``, and ``enterprise_from_readme_link()``.

The live-HTTP half of the old module (``enterprise_fact``, ``product_page_facts``, ``_status``,
``_lookup`` -- the actual ``products.aspose.com``/``products.aspose.org`` probes that FIRST
populate these facts, each needing ``httpx`` and a ``RegistryEntry``) is extraction-time
apparatus, not composition; it belongs with the separate, PENDING_REVIEW extraction pull in
migration/reuse-manifest.yaml.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from repo_presenter.core.facts import Evidence, Fact, fact_id

ENTERPRISE_FACT_ID = fact_id("link_target", "product.enterprise")
HOMEPAGE_FACT_ID = fact_id("link_target", "product.homepage")
BANNER_FACT_ID = fact_id("link_target", "product.banner")
ENTERPRISE_HOST = "https://products.aspose.com"


def enterprise_target(facts: tuple[Fact, ...] | list[Fact]) -> Fact | None:
    """The SUPPORTED Enterprise Edition target fact, or None when unresolved or absent."""
    for fact in facts:
        if fact.id == ENTERPRISE_FACT_ID and fact.polarity == "SUPPORTED":
            return fact
    return None


def enterprise_from_readme_link(facts: Sequence[Fact]) -> Fact | None:
    """The Enterprise Edition target chosen by the upstream's own README, when the live lookup was
    ambiguous: the one rule that picks between two live platform pages.

    Only a link to one of the variants the lookup itself found live, labelled as the Enterprise
    Edition, and unique among such links, settles it; anything else stays unresolved. Returns
    ``None`` when nothing is settled."""
    current = next((f for f in facts if f.id == ENTERPRISE_FACT_ID), None)
    attributes = (current.attributes or {}) if current is not None else {}
    if current is None or attributes.get("level") != "ambiguous":
        return None
    family = current.value.removeprefix(f"{ENTERPRISE_HOST}/").strip("/")
    variants = set(filter(None, attributes.get("variants", "").split(",")))
    chosen: dict[str, str] = {}
    for fact in facts:
        if fact.kind != "link_target" or fact.polarity != "SUPPORTED" or fact.id == current.id:
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
            **({"platform": attributes["platform"]} if attributes.get("platform") else {}),
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
