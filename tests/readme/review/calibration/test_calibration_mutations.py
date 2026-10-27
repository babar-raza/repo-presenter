"""Each mutation operator changes only what it claims to: the mutated README is the clean README
with exactly the declared span replaced, and the injected defect really is one."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.calibration.mutations import (
    CLASSES,
    HIGH_SEVERITY_CLASSES,
    OPERATORS,
    UNSUPPORTED_CLAIMS,
    changed_span,
    h2_sections,
    inject_unsupported_claim,
    paragraphs,
)
from repo_presenter.readme.review.calibration.outcomes import REJECT
from tests.readme.review.calibration.synthetic import FACTS, README, make_source


@pytest.fixture
def source(tmp_path: Path):
    return make_source(tmp_path)


def fact_text() -> str:
    return "\n".join(f.value for f in FACTS.facts).lower()


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_the_mutant_is_the_clean_text_with_exactly_the_declared_span_replaced(
    source, name
):
    mutation = OPERATORS[name](source)
    assert mutation is not None, (
        f"{name} found no place to edit in the synthetic candidate"
    )
    clean = source.readme
    assert mutation.readme != clean
    assert (
        mutation.readme
        == clean[: mutation.start] + mutation.replacement + clean[mutation.end :]
    )
    start, clean_end, mutated_end = changed_span(clean, mutation.readme)
    assert clean_end - start <= mutation.end - mutation.start
    assert mutated_end - start <= len(mutation.replacement)
    assert mutation.klass in CLASSES and mutation.expected == REJECT
    assert mutation.operator == name


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_operators_are_deterministic_and_leave_the_candidate_alone(source, name):
    before = source.readme
    assert OPERATORS[name](source) == OPERATORS[name](source)
    assert source.readme == before


def test_the_operators_cover_every_class_and_the_four_high_severity_classes():
    assert len(OPERATORS) == 9
    assert set(HIGH_SEVERITY_CLASSES) == {
        "contradiction",
        "content_loss",
        "unsupported_claim",
        "broken_install",
    }


def test_every_class_is_produced_by_some_operator(source):
    assert {OPERATORS[name](source).klass for name in OPERATORS} == set(CLASSES)


def test_an_injected_unsupported_claim_shares_no_distinctive_word_with_any_fact(source):
    mutation = inject_unsupported_claim(source)
    claim = mutation.replacement.strip()
    words = next(words for text, words in UNSUPPORTED_CLAIMS if text == claim)
    assert not any(word in fact_text() for word in words)
    assert not any(word in source.original.lower() for word in words)


def test_an_unsupported_claim_is_skipped_when_a_fact_supports_it(tmp_path):
    supportive = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            Fact(
                "capability:x",
                "capability",
                "round-trip fidelity lossless faster enterprises",
                (Evidence("README.md"),),
            ),
        ),
    )
    assert inject_unsupported_claim(make_source(tmp_path, facts=supportive)) is None


def test_the_wrong_version_is_not_a_fact_and_only_the_version_changes(source):
    from repo_presenter.readme.review.calibration.mutations import contradict_version

    mutation = contradict_version(source)
    assert source.readme[mutation.start : mutation.end] == "26.9.0"
    assert mutation.replacement == "27.9.0" and "27.9.0" not in fact_text()


def test_the_package_name_edit_stays_in_prose_and_leaves_the_install_command(source):
    from repo_presenter.readme.review.calibration.mutations import (
        contradict_package_name,
    )

    mutation = contradict_package_name(source)
    assert "pip install aspose-widget-foss\n" in mutation.readme
    assert mutation.replacement == "aspose-widget-foss-core"
    assert mutation.replacement.lower() not in fact_text()


def test_the_format_edit_swaps_one_supported_format_for_one_the_candidate_never_mentions(
    source,
):
    from repo_presenter.readme.review.calibration.mutations import contradict_format

    mutation = contradict_format(source)
    assert (
        mutation.replacement not in README and mutation.replacement not in fact_text()
    )
    assert source.readme[mutation.start : mutation.end] in {".png", ".svg"}


def test_drop_section_removes_the_whole_section_and_nothing_else(source):
    from repo_presenter.readme.review.calibration.mutations import drop_section

    mutation = drop_section(source)
    titles = [title for title, _s, _e in h2_sections(mutation.readme)]
    assert "Scope and Limitations" not in titles
    assert titles == [
        t for t, _s, _e in h2_sections(source.readme) if t != "Scope and Limitations"
    ]
    assert "Rendering to `.pdf` is not implemented" not in mutation.readme
    assert mutation.replacement == "" and mutation.klass == "content_loss"


def test_duplicate_paragraph_repeats_one_paragraph_right_after_itself(source):
    from repo_presenter.readme.review.calibration.mutations import duplicate_paragraph

    mutation = duplicate_paragraph(source)
    repeated = mutation.replacement.strip()
    assert repeated in README and mutation.readme.count(repeated) == 2
    assert len(mutation.readme) == len(README) + len(mutation.replacement)


def test_break_install_command_edits_only_the_command_inside_its_fence(source):
    from repo_presenter.readme.review.calibration.mutations import break_install_command

    mutation = break_install_command(source)
    assert (
        source.readme[mutation.start : mutation.end] == "pip install aspose-widget-foss"
    )
    assert "pip install aspose-widget-fsos\n" in mutation.readme
    assert mutation.replacement.lower() not in fact_text()


def test_an_invented_api_name_is_no_fact_value(source):
    from repo_presenter.readme.review.calibration.mutations import invent_api_name

    mutation = invent_api_name(source)
    assert mutation.replacement.lower() not in fact_text()
    assert source.readme[mutation.start : mutation.end] in {
        "Widget",
        "SvgExporter",
        "Widget.render",
    }


def test_an_operator_with_no_place_for_its_edit_returns_none(tmp_path):
    bare = make_source(tmp_path, readme="# Title\n\nShort.\n")
    for name in (
        "contradict_version",
        "contradict_package_name",
        "contradict_format",
        "break_install_command",
        "drop_section",
        "duplicate_paragraph",
        "inject_unsupported_claim",
        "add_promotional_filler",
    ):
        assert OPERATORS[name](bare) is None, name


def test_sections_and_paragraphs_ignore_headings_inside_code_fences():
    text = "# T\n\nOpening paragraph that is long enough to count as one.\n\n```md\n## Not a section\n```\n\n## Real\n\nBody.\n"
    assert [t for t, _s, _e in h2_sections(text)] == ["Real"]
    found = [text[s:e] for s, e in paragraphs(text)]
    assert "## Not a section" not in "".join(found)


def test_changed_span_is_the_minimal_differing_region():
    assert changed_span("abcXdef", "abcYYdef") == (3, 4, 5)
    assert changed_span("same", "same") == (4, 4, 4)
    assert changed_span("ab", "abcd") == (2, 2, 4)


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_every_mutation_says_what_a_finding_about_it_must_mention(source, name):
    mutation = OPERATORS[name](source)
    assert mutation.targets and all(t == t.lower() and t for t in mutation.targets)
