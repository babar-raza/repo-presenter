"""Case selection is fixed before any reviewer output (``calibration.selection``)."""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.selection import (
    cap_real_defects,
    stability_subset,
)
from tests.readme.review.calibration.synthetic import make_source


def corpus(tmp_path, bases=2, reals=5):
    cases = []
    for b in range(bases):
        built = build_corpus([Base(make_source(tmp_path, name=f"b{b}"))])
        clean = built[0]
        cases.extend(built)
        cases.extend(
            replace(clean, case_id=f"b{b}/real:x:{i}", role="real_defect", klass="x")
            for i in range(reals)
        )
    return cases


def test_real_defects_are_capped_per_base_and_nothing_else_is_dropped(tmp_path):
    cases = corpus(tmp_path)
    capped = cap_real_defects(cases, 2)
    reals = [c for c in capped if c.role == "real_defect"]
    assert sorted({c.base for c in reals}) == ["b0", "b1"]
    assert all(sum(c.base == b for c in reals) == 2 for b in ("b0", "b1"))
    others = [c for c in cases if c.role != "real_defect"]
    assert [c for c in capped if c.role != "real_defect"] == others
    assert cap_real_defects(cases, -1) == cases


def test_the_selection_does_not_depend_on_input_order(tmp_path):
    cases = corpus(tmp_path)
    forward = {c.case_id for c in cap_real_defects(cases, 2)}
    backward = {c.case_id for c in cap_real_defects(list(reversed(cases)), 2)}
    assert forward == backward
    assert {c.case_id for c in stability_subset(cases, 4)} == {
        c.case_id for c in stability_subset(list(reversed(cases)), 4)
    }


def test_the_stability_subset_is_half_clean_half_defects(tmp_path):
    chosen = stability_subset(corpus(tmp_path), 4)
    assert [c.role for c in chosen[:2]] == ["clean", "clean"]
    assert all(c.role in {"mutant", "real_defect"} for c in chosen[2:])
