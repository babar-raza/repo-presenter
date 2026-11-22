"""BL-670: a maintainers' static status badge no extractor fact verifies is carried when the maintainers' own
paragraph or list states the same status in words, so BC-17 no longer depends on which units the model kept.

Real data: aspose-tex-foss/Aspose.TeX-FOSS-for-Python at 07db3203 (README header row, link_target facts and the
Scope list 072.list that says 'This is a Pre-Alpha release'); hosted runs 44943500229 and 44959650874 ended
'no LLM review ... BC-17 inherited_unit:002.badge_row holds links https://img.shields.io/badge/status-pre--alpha-orange.svg'."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import EXTRA_BADGE_SLOT, RenderContext, badge_slots
from repo_presenter.readme.validation.rules import badge_problems

REGISTRY = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")
TEX = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
STATUS = "https://img.shields.io/badge/status-pre--alpha-orange.svg"
ROW = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python/blob/main/LICENSE) "
    "[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python/blob/main/pyproject.toml) "
    f"[![Status: Pre--Alpha]({STATUS})](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python#scope-and-limitations)"
)
SCOPE = (
    "- This is a Pre-Alpha release: the core engine and public API are under active development, and interfaces may change between releases.\n"
    "- Plain TeX is the supported format."
)


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attrs: str) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value=value,  # type: ignore[arg-type]
        evidence=(Evidence("README.md", None),), polarity=polarity,  # type: ignore[arg-type]
        attributes=attrs or None,
    )


def _context(scope: str | None = SCOPE, scope_id: str = "inherited_unit:072.list", row: str = ROW) -> RenderContext:
    entry = next(e for e in REGISTRY.entries if e.repository == TEX)
    plugin_for(entry.ecosystem)
    facts = [
        _fact("inherited_unit:002.badge_row", "inherited_unit", row, section="Aspose.TeX FOSS for Python"),
        _fact("license:spdx", "license", "MIT"),
        _fact("license:file", "license", "LICENSE"),
        _fact("package:python_requires", "package", ">=3.10", floor_declaration="requires-python"),
        _fact("link_target:005", "link_target", STATUS),
        _fact(
            "link_target:006", "link_target",
            "https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python#scope-and-limitations", polarity="UNRESOLVED",
        ),
    ]
    if scope is not None:
        facts.append(_fact(scope_id, "inherited_unit", scope, section="Scope and Limitations"))
    return RenderContext(
        entry, FactsDocument(TEX, "0" * 40, tuple(facts)), {"sections": []}, {"units": []}, {"dispositions": []},
    )


def _extras(context: RenderContext) -> list[str]:
    return [markdown for slot, markdown in badge_slots(context) if slot == EXTRA_BADGE_SLOT]


def test_the_status_badge_the_maintainers_state_in_words_is_carried_and_passes_the_badge_contract() -> None:
    context = _context()
    slots = badge_slots(context)
    extras = [markdown for slot, markdown in slots if slot == EXTRA_BADGE_SLOT]
    assert len(extras) == 1 and STATUS in extras[0]
    assert badge_problems(" ".join(markdown for _slot, markdown in slots), slots) == []


def test_the_unverified_link_target_is_dropped_and_the_image_stays() -> None:
    (extra,) = _extras(_context())
    assert extra == f"![Status: Pre--Alpha]({STATUS})"


def test_negative_control_a_status_no_maintainers_text_states_is_not_carried() -> None:
    silent = "- The core engine is under active development.\n- Plain TeX is the supported format."
    assert _extras(_context(silent)) == []
    assert _extras(_context(None)) == []


def test_negative_control_the_badge_row_itself_never_states_its_own_status() -> None:
    assert _extras(_context(None, row=ROW)) == []


def test_negative_control_a_code_block_or_heading_stating_the_word_does_not_carry_it() -> None:
    assert _extras(_context("```text\nPre-Alpha\n```", "inherited_unit:072.code_block")) == []
    assert _extras(_context("## Pre-Alpha", "inherited_unit:071.heading")) == []


def test_negative_control_an_unrelated_static_badge_is_still_not_carried() -> None:
    row = ROW.replace("status-pre--alpha-orange", "build-passing-green").replace("Pre--Alpha", "Build")
    assert _extras(_context(row=row)) == []
