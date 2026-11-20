"""BL-542: the renderer's "No required third-party package dependencies" line is derived from the
``dependency:none`` fact it prints, so a model flag on it is cleared by the BL-400 derivation.

PSD Java (hosted Lane R seal; pre-audit sweep 2026-11-20): line 83, "No required third-party package
dependencies; in `pom.xml`, every `<dependency>` the POM declares is `test`, `provided` or optional.",
was flagged in 4 of 4 fresh audit samples as an unsupported claim because "provided" and "optional" occur
in no fact VALUE. Nothing could change that line: the renderer owns it, BL-430's degrade only withholds
authored text, and the BL-400 derivation refused it ("no fact value in the line", the fact's value being
the one word "none"). The line is the fact's evidence word for word, so the origin now cites the fact.

Negative controls: any other wording of the clause, a fact that is not SUPPORTED, and a candidate that
also records a required dependency (the renderer then prints the list, not the clause) are never cleared.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import no_required_dependencies_line, render_readme
from repo_presenter.readme.review.derivation import lane_r_derivation

REPOSITORY = "aspose-psd-foss/Aspose.PSD-FOSS-for-Java"
ROOT = Path(__file__).resolve().parents[3]
ENTRY = next(e for e in load_registry(ROOT / "data" / "registry.json").entries if e.repository == REPOSITORY)
DETAIL = "every `<dependency>` the POM declares is `test`, `provided` or optional"
CLAUSE = f"No required third-party package dependencies; in `pom.xml`, {DETAIL}."


def _marker(polarity: str = "SUPPORTED", detail: str = DETAIL) -> Fact:
    return Fact("dependency:none", "dependency", "none", (Evidence("pom.xml", detail),), polarity=polarity)  # type: ignore[arg-type]


def _facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        REPOSITORY, "d808d1d",
        (
            Fact("identity:repository", "identity", REPOSITORY, (Evidence("registry"),)),
            Fact(
                "dependency:development.org.junit.jupiter-junit-jupiter", "dependency",
                "org.junit.jupiter:junit-jupiter 5.10.2",
                (Evidence("pom.xml", "declared with `<scope>test</scope>`, never resolved for a consumer"),),
            ),
            *extra,
        ),
    )


def _plan() -> dict:
    return {"sections": [{"section_id": "dependencies", "include": True, "reason": "r"}]}


def _derive(facts: FactsDocument, readme: str | None = None):
    plugin_for(ENTRY.ecosystem)
    plan, units, dispositions = _plan(), {"units": []}, {"dispositions": []}
    rendered = render_readme(ENTRY, facts, plan, units, dispositions)
    text = readme if readme is not None else rendered
    lines = [n for n, row in enumerate(text.splitlines(), 1) if "third-party package" in row]
    derived = lane_r_derivation(
        text, entry=ENTRY, facts=facts, plan=plan, units=units, dispositions=dispositions, ask=set(lines),
        register_path=ROOT / "data" / "readme_findings.json",
    )
    return text, lines, derived


def test_the_clause_is_printed_word_for_word_from_the_fact() -> None:
    assert no_required_dependencies_line(_marker()) == CLAUSE
    assert no_required_dependencies_line(_marker("UNRESOLVED")) is None


def test_a_model_flag_on_the_clause_is_cleared_with_the_fact_it_states() -> None:
    text, lines, derived = _derive(_facts(_marker()))
    assert CLAUSE in text and len(lines) == 1
    assert derived is not None and set(lines) <= derived.clearable
    assert derived.cited[lines[0]] == ("dependency:none",)


def test_reworded_clause_is_not_cleared() -> None:
    facts = _facts(_marker())
    text, lines, _ = _derive(facts)
    reworded = text.replace("is `test`, `provided` or optional", "is `test`, `provided` or optional, and none ships")
    _, lines, derived = _derive(facts, reworded)
    assert derived is not None and not set(lines) & derived.clearable


def test_an_unsupported_marker_prints_no_clause_and_clears_nothing() -> None:
    text, lines, derived = _derive(_facts(_marker("UNRESOLVED")))
    assert lines == [] and CLAUSE not in text


def test_a_recorded_required_dependency_is_listed_and_the_clause_is_not_printed() -> None:
    required = Fact("dependency:com.example-lib", "dependency", "com.example:lib 1.0", (Evidence("pom.xml", "compile"),))
    text, lines, _ = _derive(_facts(_marker(), required))
    assert lines == [] and "`com.example:lib 1.0`" in text
