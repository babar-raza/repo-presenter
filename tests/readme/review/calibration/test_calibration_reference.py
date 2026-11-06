"""Iteration 4's two new base kinds: a README another process wrote (the aspose.org reference
candidate), and a sealed Lane R bundle of this project's own.

A reference README has no disposition record, so the rules that audit this project's record must not
fire on its absence (they would make every reference twin unscored and measure nothing), while the
rules that read the text alone must still fire; and the reviewer must be shown every prose line of it
(``rendered=False``), since none of it was printed by this renderer.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review import llm_review
from repo_presenter.readme.review.calibration import corpus as corpus_module
from repo_presenter.readme.review.calibration import reviewers as reviewers_module
from repo_presenter.readme.review.calibration import sources
from repo_presenter.readme.review.calibration.corpus import (
    Base,
    base_cases,
    deterministic_rules,
)
from repo_presenter.readme.review.calibration.harness import pre_llm
from repo_presenter.readme.review.calibration.outcomes import UNAVAILABLE
from repo_presenter.readme.review.verdict import ReviewUnavailable
from tests.readme.composition.synthetic import make_entry
from tests.readme.review.calibration.synthetic import (
    FACTS,
    ORIGINAL,
    README,
    make_source,
)

#: The facts with one inherited unit of the live README, so a disposition record has something to
#: account for: a README with no record leaves it unaccounted.
FACTS_WITH_UNIT = FactsDocument(
    FACTS.repository,
    FACTS.source_revision,
    (
        *FACTS.facts,
        Fact(
            "inherited_unit:001.paragraph",
            "inherited_unit",
            "Renders widgets to PNG and SVG.",
            (Evidence("README.md", "live"),),
        ),
    ),
)


def reference(tmp_path: Path, readme: str = README):
    return replace(
        make_source(tmp_path, readme=readme, facts=FACTS_WITH_UNIT),
        plan={},
        units={},
        dispositions={},
        rendered=False,
    )


def test_a_reference_twin_is_scored_although_it_has_no_disposition_record(tmp_path):
    rendered = replace(reference(tmp_path), rendered=True)
    # The same README judged as this renderer's output trips the record-auditing rules ...
    assert set(deterministic_rules(base_cases(Base(rendered))[0])) & {
        "disposition_coverage",
        "live_readme_loss",
    }
    # ... and judged as a README written elsewhere it does not.
    clean = base_cases(Base(reference(tmp_path)))[0]
    assert clean.role == "clean" and clean.baseline_rules == ()


def test_the_text_rules_still_block_a_reference_mutant(tmp_path):
    cases = {c.operator: c for c in base_cases(Base(reference(tmp_path)))}
    assert "claim_contradiction" in pre_llm(cases["contradict_version"]).rules
    assert "duplicate_paragraph" in pre_llm(cases["duplicate_paragraph"]).rules
    # A mutant the text rules cannot see is left to the reviewer.
    assert not pre_llm(cases["inject_unsupported_claim"]).blocked


def test_the_text_only_branch_is_what_keeps_the_record_rules_off(tmp_path, monkeypatch):
    """Falsifier for the branch above: route a reference README through ``review_candidate`` and
    the twin is no longer scored."""
    monkeypatch.setattr(
        corpus_module,
        "claim_contradiction_rule",
        lambda *a, **k: pytest.fail("the text branch must not run"),
    )
    source = replace(reference(tmp_path), rendered=True)
    clean = base_cases(Base(source))[0]
    assert clean.role == "unscored_twin"


def test_the_live_reviewer_shows_a_reference_readme_in_full(tmp_path, monkeypatch):
    seen: dict[str, object] = {}

    def fake_review(**kwargs):
        seen["rendered"] = kwargs["rendered"]
        raise ReviewUnavailable("stub", [])

    monkeypatch.setattr(reviewers_module, "review_with_model", fake_review)
    reviewer = reviewers_module.LiveReviewer(
        prompts=None,
        config=None,
        ledger_path=tmp_path / "ledger.jsonl",
        store_dir=tmp_path / "store",
        cap=5,
    )
    ref_case = base_cases(Base(reference(tmp_path)))[0]
    own_case = base_cases(Base(make_source(tmp_path)))[0]
    assert reviewer(ref_case).verdict == UNAVAILABLE and seen["rendered"] is False
    reviewer(own_case)
    assert seen["rendered"] is True
    assert llm_review.review_with_model.__kwdefaults__["rendered"] is True


def _clone(tmp_path: Path, repository: str) -> Path:
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "config").write_text(
        f'[remote "origin"]\n\turl = https://github.com/{repository}.git\n',
        encoding="utf-8",
    )
    (clone / "README.md").write_text(ORIGINAL, encoding="utf-8")
    (clone / "src.py").write_text("x = 1\n", encoding="utf-8")
    return clone


@pytest.fixture
def listed(tmp_path, monkeypatch):
    entry = make_entry()
    monkeypatch.setattr(sources, "load_registry", lambda path: None)
    monkeypatch.setattr(sources, "require_listed", lambda registry, repository: entry)
    return entry


def test_load_reference_candidate_reads_the_readme_as_written(tmp_path, listed):
    clone = _clone(tmp_path, FACTS.repository)
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(FACTS.to_json(), encoding="utf-8")
    readme_path = tmp_path / "ref" / "readme.md"
    readme_path.parent.mkdir()
    readme_path.write_text(README, encoding="utf-8")
    source = sources.load_reference_candidate(
        readme_path, facts_path=facts_path, clone=clone, name="ref"
    )
    assert source.readme == README and source.original == ORIGINAL
    assert source.rendered is False and source.dispositions == {}
    assert source.validation == {"summary": {}, "checks": []}
    assert "src.py" in source.tree_paths


def test_load_reference_candidate_refuses_another_repositorys_facts(tmp_path, listed):
    clone = _clone(tmp_path, "org/Some-Other-Repository")
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(FACTS.to_json(), encoding="utf-8")
    readme_path = tmp_path / "readme.md"
    readme_path.write_text(README, encoding="utf-8")
    with pytest.raises(ValueError, match="facts are for"):
        sources.load_reference_candidate(
            readme_path, facts_path=facts_path, clone=clone, name="ref"
        )


#: A live README holding the twin's limitations section, as the live README of every iteration-4
#: reference base whose drop_section mutant removed "Scope and Limitations" did.
LIVE_WITH_LIMITS = """# Aspose.Widget FOSS for Python

Renders widgets to PNG and SVG.

## Installation

pip install aspose-widget-foss

## Scope and Limitations

- Rendering to `.pdf` is not implemented in this build.
"""


def _lane_l_like(tmp_path: Path, original: str):
    return replace(reference(tmp_path), original=original)


def test_a_reference_drop_section_mutant_is_blocked_as_lane_l_blocks_it(tmp_path):
    """Root cause 2026-11-06: iteration 4's reference bases ran only the text rules, so 0 of 34
    dropped sections were caught deterministically, although Lane L's production holdouts
    (``lane_l_review.holdout_findings``) run ``live_readme_loss`` against the live README."""
    cases = {c.role if c.operator is None else c.operator: c for c in base_cases(
        Base(_lane_l_like(tmp_path, LIVE_WITH_LIMITS))
    )}
    assert cases["clean"].role == "clean" and cases["clean"].baseline_rules == ()
    assert "live_readme_loss" in pre_llm(cases["drop_section"]).rules
    assert not pre_llm(cases["inject_unsupported_claim"]).blocked


def test_a_new_finding_of_a_rule_the_twin_already_trips_is_still_a_catch(tmp_path):
    """The twin loses a live link (iteration 4: 24 of 34 reference twins already lost some live
    content), so ``live_readme_loss`` is a baseline rule. A rule-level baseline then hid the
    dropped section; the finding-level baseline counts the new finding and only it."""
    live = LIVE_WITH_LIMITS + "\nSee the [docs](https://example.org/widget/docs).\n"
    cases = {c.role if c.operator is None else c.operator: c for c in base_cases(
        Base(_lane_l_like(tmp_path, live))
    )}
    twin = cases["unscored_twin"]
    assert twin.baseline_rules == ("live_readme_loss",)
    assert any("example.org/widget/docs" in key[1] for key in twin.baseline_findings)
    assert pre_llm(cases["drop_section"]).rules == ("live_readme_loss",)
    # the link the twin already lost is not a catch of anything built from it
    assert not pre_llm(cases["inject_unsupported_claim"]).blocked
    assert not pre_llm(cases["add_promotional_filler"]).blocked


def test_load_bundle_candidate_refuses_facts_of_another_revision(tmp_path, listed):
    clone = _clone(tmp_path, FACTS.repository)
    revision_dir = tmp_path / ("c" * 40)
    revision_dir.mkdir()
    (revision_dir / "facts.json").write_text(FACTS.to_json(), encoding="utf-8")
    for name in ("plan", "content_units.coherent", "dispositions", "investigation"):
        (revision_dir / f"{name}.json").write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="bundle's facts are for"):
        sources.load_bundle_candidate(revision_dir, clone=clone, name="own")
