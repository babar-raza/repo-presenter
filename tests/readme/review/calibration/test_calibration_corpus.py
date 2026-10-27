"""The corpus builder: clean twin, mutants and real-defect cases, each paired with its twin."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from repo_presenter.readme.review.calibration.corpus import (
    Base,
    RecordedDefect,
    Repair,
    apply_repairs,
    build_corpus,
    deterministic_rules,
    new_blocking_checks,
)
from repo_presenter.readme.review.calibration.mutations import CLASSES, OPERATORS
from repo_presenter.readme.review.calibration.outcomes import ACCEPT, REJECT
from tests.readme.review.calibration.synthetic import README, make_source

DEFECT = " It offers full round-trip fidelity."
REPAIR = Repair(
    DEFECT, "", "unsupported 'full round-trip fidelity'", klass="unsupported_claim"
)


def defective_base(tmp_path: Path) -> Base:
    readme = README.replace(
        "through the `Widget` class and the `SvgExporter` class.",
        "through the `Widget` class and the `SvgExporter` class." + DEFECT,
    )
    assert DEFECT in readme
    return Base(make_source(tmp_path, readme=readme), (REPAIR,))


@pytest.fixture
def cases(tmp_path):
    return build_corpus([defective_base(tmp_path)])


def by_role(cases, role):
    return [case for case in cases if case.role == role]


def test_a_base_yields_its_clean_twin_its_real_defect_and_one_mutant_per_operator(
    cases,
):
    (clean,) = by_role(cases, "clean")
    assert clean.expected == ACCEPT and clean.twin_of is None and clean.klass is None
    assert DEFECT not in clean.readme
    (real,) = by_role(cases, "real_defect")
    assert real.klass == "unsupported_claim" and real.expected == REJECT
    assert DEFECT in real.readme and real.twin_of == clean.case_id
    assert apply_repairs(real.readme, [REPAIR]) == clean.readme
    mutants = by_role(cases, "mutant")
    assert {m.operator for m in mutants} == set(OPERATORS)
    assert {m.klass for m in mutants} == set(CLASSES)


def test_every_mutant_is_its_twin_with_exactly_one_declared_span_replaced(cases):
    (clean,) = by_role(cases, "clean")
    for mutant in by_role(cases, "mutant"):
        m = mutant.mutation
        assert mutant.twin_of == clean.case_id and mutant.expected == REJECT
        assert (
            mutant.readme
            == clean.readme[: m.start] + m.replacement + clean.readme[m.end :]
        )
        assert mutant.readme != clean.readme


def test_a_mutant_shows_the_model_the_twins_validation_not_its_own(cases):
    (clean,) = by_role(cases, "clean")
    for case in cases:
        assert case.source.validation == clean.source.validation


def test_the_clean_twin_passes_the_deterministic_stage(cases):
    (clean,) = by_role(cases, "clean")
    assert deterministic_rules(clean) == () and new_blocking_checks(clean) == ()


def test_the_install_mutant_is_caught_before_a_model_is_asked(cases):
    (broken,) = [c for c in cases if c.operator == "break_install_command"]
    assert "claim_contradiction" in deterministic_rules(broken)


def test_a_mutant_the_deterministic_stage_misses_is_what_the_model_must_catch(cases):
    escapes = {
        c.operator
        for c in by_role(cases, "mutant")
        if not deterministic_rules(c) and not new_blocking_checks(c)
    }
    assert {
        "inject_unsupported_claim",
        "contradict_version",
        "add_promotional_filler",
    } <= escapes


def test_a_repair_that_does_not_match_exactly_is_an_error(tmp_path):
    bad = Base(make_source(tmp_path), (Repair("text that is not there", "", "x"),))
    with pytest.raises(ValueError, match="expects 1 occurrence"):
        build_corpus([bad])
    twice = Base(make_source(tmp_path), (Repair("Widget", "", "x"),))
    with pytest.raises(ValueError, match="found"):
        build_corpus([twice])


def test_a_lint_level_repair_makes_no_real_defect_case(tmp_path):
    base = Base(
        make_source(
            tmp_path, readme=README.replace("MIT.", "MIT. (see this revision)")
        ),
        (Repair(" (see this revision)", "", "internal narration"),),
    )
    assert not by_role(build_corpus([base]), "real_defect")


def test_recorded_defects_pair_with_their_repaired_twin(tmp_path):
    source = make_source(
        tmp_path,
        readme=README.replace(
            "pip install aspose-widget-foss", "pip install aspose-widget[mcp]"
        ),
        name="font",
    )
    recorded = RecordedDefect(
        source,
        "broken_install",
        (Repair("aspose-widget[mcp]", "aspose-widget-foss[mcp]", "wrong dist"),),
        "inherited",
    )
    clean, defect = build_corpus([], [recorded])
    assert clean.expected == ACCEPT and "aspose-widget-foss[mcp]" in clean.readme
    assert defect.expected == REJECT and defect.klass == "broken_install"
    assert defect.twin_of == clean.case_id and "aspose-widget[mcp]" in defect.readme


def test_case_ids_are_unique_across_bases(tmp_path):
    other = Base(make_source(tmp_path, name="other"))
    ids = [c.case_id for c in build_corpus([defective_base(tmp_path), other])]
    assert len(ids) == len(set(ids))
    duplicate = replace(other, source=other.source)
    with pytest.raises(ValueError, match="duplicate case ids"):
        build_corpus([other, duplicate])


def test_a_recorded_twin_the_deterministic_stage_rejects_is_kept_but_not_scored(
    tmp_path,
):
    from repo_presenter.readme.review.calibration.harness import (
        compute_metrics,
        evaluate_gates,
        run_corpus,
    )
    from repo_presenter.readme.review.calibration.reviewers import oracle

    source = make_source(
        tmp_path,
        readme=README.replace(
            "pip install aspose-widget-foss", "pip install aspose-widget[mcp]"
        ),
    )
    repairs = (Repair("aspose-widget[mcp]", "aspose-widget-foss", "wrong dist"),)
    twin, _ = build_corpus([], [RecordedDefect(source, "broken_install", repairs, "n")])
    assert twin.role == "clean"
    gone = "\n## Gone\n\nText the live README has and the candidate lost.\n"
    moved_on = replace(source, original=source.original + gone)
    unscored, defect = build_corpus(
        [], [RecordedDefect(moved_on, "broken_install", repairs, "n")]
    )
    assert unscored.role == "unscored_twin" and defect.role == "real_defect"
    metrics = compute_metrics(run_corpus([unscored], oracle))
    assert metrics.clean_n == 0 and metrics.unscored_n == 1 and metrics.cases_asked == 1
    assert not any(
        g.name == "false_reject_rate" and g.n for g in evaluate_gates(metrics)
    )


def test_a_recorded_defect_with_no_repair_has_no_twin(tmp_path):
    source = make_source(tmp_path, name="dup")
    (only,) = build_corpus([], [RecordedDefect(source, "duplicate_paragraph", (), "n")])
    assert only.role == "real_defect" and only.twin_of is None
