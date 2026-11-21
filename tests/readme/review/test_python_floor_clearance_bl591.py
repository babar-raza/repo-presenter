"""BL-591: the renderer's "- Requires Python 3.10 or later." line is derived from the ``package:python_requires``
fact it prints, so a model flag on it is cleared by the BL-400 derivation.

Page Python (hosted audit round 44904444359, a clean control): line 115 was flagged as an "omission" because the
fact's VALUE is ``>=3.10`` and the line says "3.10 or later", so the derivation found "no fact value in the line"
and kept the flag, although only the renderer prints that line, from that fact. The origin now cites the fact.

Negative controls: any other wording of the line, a floor that does not match the fact, and a fact that is not
SUPPORTED are never cleared.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.derivation import lane_r_derivation

REPOSITORY = "aspose-page-foss/Aspose.Page-FOSS-for-Python"
ROOT = Path(__file__).resolve().parents[3]
ENTRY = next(e for e in load_registry(ROOT / "data" / "registry.json").entries if e.repository == REPOSITORY)
LINE = "- Requires Python 3.10 or later."


def _facts(polarity: str = "SUPPORTED", value: str = ">=3.10") -> FactsDocument:
    return FactsDocument(
        REPOSITORY, "43cef36",
        (
            Fact("identity:repository", "identity", REPOSITORY, (Evidence("registry"),)),
            Fact("package:python_requires", "package", value, (Evidence("pyproject.toml", "requires-python"),),
                 polarity=polarity, attributes={"floor_declaration": "requires-python"}),  # type: ignore[arg-type]
        ),
    )


def _derive(facts: FactsDocument, readme: str | None = None):
    plugin_for(ENTRY.ecosystem)
    plan = {"sections": [{"section_id": "dependencies", "include": True, "reason": "r"}]}
    units, dispositions = {"units": []}, {"dispositions": []}
    rendered = render_readme(ENTRY, facts, plan, units, dispositions)
    text = readme if readme is not None else rendered
    lines = [n for n, row in enumerate(text.splitlines(), 1) if "Requires Python" in row]
    derived = lane_r_derivation(
        text, entry=ENTRY, facts=facts, plan=plan, units=units, dispositions=dispositions, ask=set(lines),
        register_path=ROOT / "data" / "readme_findings.json",
    )
    return text, lines, derived


def test_a_model_flag_on_the_floor_line_is_cleared_with_the_fact_it_states() -> None:
    text, lines, derived = _derive(_facts())
    assert LINE in text.splitlines() and len(lines) == 1
    assert derived is not None and set(lines) <= derived.clearable
    assert derived.cited[lines[0]] == ("package:python_requires",)


def test_a_reworded_floor_line_is_not_cleared() -> None:
    facts = _facts()
    text, _, _ = _derive(facts)
    for reworded in (text.replace(LINE, "- Requires Python 3.9 or later."),
                     text.replace(LINE, "- Requires Python 3.10 or later and a C compiler.")):
        _, lines, derived = _derive(facts, reworded)
        assert derived is not None and lines and not set(lines) & derived.clearable


def test_an_unsupported_floor_fact_prints_no_line_and_clears_nothing() -> None:
    text, lines, derived = _derive(_facts("UNRESOLVED"))
    assert lines == [] and LINE not in text
