"""BUILD_INDEPENDENT_REVIEWER (project/state.yaml): this repository's own Gate A reviewer,
built from scratch against real previously-encountered defect classes already on record in this
project -- not ported from the old repository's review.py/judge.py, which are disqualified (see
the module docstring for why).

The most important test here is ``test_fold_rejects_whenever_any_finding_carries_a_refutation``:
it is the structural guarantee that replaces the old repository's measured incident
(docs/MISSION_AUTHORITY.md's "critical fact": 27/30 real REJECT findings wrongly folded to
ACCEPT). A change that makes any of these tests fail by reintroducing a fold-to-ACCEPT path is
exactly the regression this module exists to make impossible.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.independent_reviewer import (
    REVIEWER_LOGIC_VERSION,
    Finding,
    Refutation,
    ReviewVerdict,
    ReviewVerdictError,
    _fold,
    claim_contradiction_rule,
    duplicate_opening_paragraph_rule,
    load_review_verdict,
    review_candidate,
    write_review_verdict,
)

import json
import pytest

REVISION = "a" * 40


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument("org/repo", REVISION, facts)


# ---------------------------------------------------------------------------
# the fold invariant itself: no quiet demotion, enforced structurally
# ---------------------------------------------------------------------------


def test_fold_accepts_when_there_are_no_findings() -> None:
    assert _fold([]) == "ACCEPT"


def test_fold_accepts_when_every_finding_is_judgment_only() -> None:
    findings = [
        Finding(rule="style_note", kind="judgment", message="a bit verbose"),
        Finding(rule="another_note", kind="judgment", message="could be tighter"),
    ]
    assert _fold(findings) == "ACCEPT"


def test_fold_rejects_whenever_any_finding_carries_a_refutation() -> None:
    """The exact invariant the old repository's fold-bug violated: one deterministic refutation,
    buried among any number of judgment-only annotations, must still REJECT."""
    findings = [
        Finding(rule="style_note", kind="judgment", message="minor"),
        Finding(
            rule="claim_contradiction",
            kind="deterministic",
            message="stale version",
            refuted_by=Refutation(rule="claim_contradiction", evidence="26.9.0 vs 26.10.0"),
        ),
        Finding(rule="another_note", kind="judgment", message="minor too"),
    ]
    assert _fold(findings) == "REJECT"


def test_a_judgment_finding_can_never_carry_a_refutation() -> None:
    """Enforced by construction, not convention -- the single most important guarantee this
    module makes. A future judgment rule literally cannot reintroduce the old bug class."""
    with pytest.raises(ValueError, match="annotate only"):
        Finding(
            rule="a_future_judgment_rule",
            kind="judgment",
            message="tried to refute",
            refuted_by=Refutation(rule="a_future_judgment_rule", evidence="should be impossible"),
        )


def test_review_verdicts_deterministic_reject_count_counts_only_refutations() -> None:
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(rule="a", kind="judgment", message="m"),
            Finding(
                rule="b",
                kind="deterministic",
                message="m",
                refuted_by=Refutation(rule="b", evidence="e"),
            ),
        ),
    )
    assert verdict.deterministic_reject_count == 1


# ---------------------------------------------------------------------------
# claim_contradiction_rule: the factual holdout (mission section 11)
# ---------------------------------------------------------------------------

NET = (
    Fact("package:name", "package", "Aspose.PDF.FOSS", (Evidence("pom.xml"),)),
    Fact("package:version", "package", "26.9.0", (Evidence("pom.xml"),)),
    Fact(
        "package:published_version",
        "package",
        "26.10.0",
        (Evidence("pom.xml", "current stable release"),),
    ),
)
STALE_README = (
    "## Installation\n\n```bash\ndotnet add package Aspose.PDF.FOSS --version 26.9.0\n```\n"
)
CURRENT_README = (
    "## Installation\n\n```bash\ndotnet add package Aspose.PDF.FOSS --version 26.10.0\n```\n"
)


def test_claim_contradiction_rule_flags_a_real_stale_version() -> None:
    """Grounded in the real aspose-pdf-foss/.NET defect class this project already found and
    corrected once (BC-14). The reviewer must catch it independently of whichever Lane produced
    the candidate."""
    [finding] = claim_contradiction_rule(STALE_README, _facts(*NET))
    assert finding.kind == "deterministic"
    assert finding.refuted_by is not None
    assert "26.10.0" in finding.refuted_by.evidence


def test_claim_contradiction_rule_is_silent_on_the_current_version() -> None:
    assert claim_contradiction_rule(CURRENT_README, _facts(*NET)) == []


# ---------------------------------------------------------------------------
# duplicate_opening_paragraph_rule: the preservation / previous-regression holdout
# ---------------------------------------------------------------------------

PRESERVED_OPENING = (
    "Aspose.Widget FOSS for Python is a free, open-source, pure-Python library for rendering "
    "widgets without any proprietary runtime dependency."
)
_DISPOSITIONS_PRESERVING_OPENING = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:004.paragraph",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "opening",
            "fact_ids": [],
            "rationale": "test fixture",
        }
    ]
}


def _facts_with_preserved_opening(text: str) -> FactsDocument:
    return _facts(
        Fact(
            "inherited_unit:004.paragraph",
            "inherited_unit",
            text,
            (Evidence("README.md", "section 'Aspose Widget'"),),
        )
    )


def test_duplicate_opening_paragraph_rule_flags_a_near_total_restatement() -> None:
    """Grounded in the real ninth cascade (aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript) this
    project already measured: S8 coherence's revision of "opening" there became a near word-
    for-word copy of the paragraph reconciliation had already preserved beside it. The reviewer
    must catch this independently of whether authoring's own inline guard already did."""
    facts = _facts_with_preserved_opening(PRESERVED_OPENING)
    units = [{"section": "opening", "slot": "opening", "text": PRESERVED_OPENING}]
    [finding] = duplicate_opening_paragraph_rule(
        units, dispositions=_DISPOSITIONS_PRESERVING_OPENING, facts=facts
    )
    assert finding.kind == "deterministic"
    assert finding.refuted_by is not None


def test_duplicate_opening_paragraph_rule_allows_genuinely_new_content() -> None:
    facts = _facts_with_preserved_opening(PRESERVED_OPENING)
    authored = (
        "It also provides a built-in validator via Widget.validate() and streaming export to "
        "PNG and SVG targets."
    )
    units = [{"section": "opening", "slot": "opening", "text": authored}]
    assert (
        duplicate_opening_paragraph_rule(
            units, dispositions=_DISPOSITIONS_PRESERVING_OPENING, facts=facts
        )
        == []
    )


def test_duplicate_opening_paragraph_rule_is_silent_without_a_preserved_opening_unit() -> None:
    facts = _facts()
    units = [{"section": "opening", "slot": "opening", "text": "Anything at all."}]
    assert (
        duplicate_opening_paragraph_rule(units, dispositions={"dispositions": []}, facts=facts)
        == []
    )


# ---------------------------------------------------------------------------
# review_candidate: the two rules wired together, and the negative control
# ---------------------------------------------------------------------------


def test_review_candidate_accepts_a_clean_candidate() -> None:
    """Negative control (mission section 11): a checker that rejects everything is as broken as
    one that accepts everything. A genuinely clean candidate must ACCEPT."""
    facts = _facts(*NET, *_facts_with_preserved_opening(PRESERVED_OPENING).facts)
    authored = "It also provides a built-in validator via Widget.validate()."
    units = [{"section": "opening", "slot": "opening", "text": authored}]
    sep = "\n\n"
    clean = sep.join([PRESERVED_OPENING, authored, CURRENT_README])
    verdict = review_candidate(
        readme_text=clean,
        units=units,
        facts=facts,
        dispositions=_DISPOSITIONS_PRESERVING_OPENING,
        original_readme=clean,
    )
    assert verdict.verdict == "ACCEPT"
    assert verdict.findings == ()


def test_review_candidate_rejects_a_real_stale_version_end_to_end() -> None:
    verdict = review_candidate(
        readme_text=STALE_README,
        units=[],
        facts=_facts(*NET),
        dispositions={"dispositions": []},
        original_readme=STALE_README,
    )
    assert verdict.verdict == "REJECT"
    assert verdict.deterministic_reject_count == 1


def test_review_candidate_rejects_the_duplicate_opening_regression_end_to_end() -> None:
    facts = _facts_with_preserved_opening(PRESERVED_OPENING)
    units = [{"section": "opening", "slot": "opening", "text": PRESERVED_OPENING}]
    verdict = review_candidate(
        readme_text="# Anything\n\nNo claims here.\n",
        units=units,
        facts=facts,
        dispositions=_DISPOSITIONS_PRESERVING_OPENING,
        original_readme="# Anything\n\nNo claims here.\n",
    )
    assert verdict.verdict == "REJECT"
    assert "duplicate_opening_paragraph" in {finding.rule for finding in verdict.findings}


# ---------------------------------------------------------------------------
# the falsifier BUILD_INDEPENDENT_REVIEWER names (project/state.yaml)
# ---------------------------------------------------------------------------


def test_falsifier_a_quoted_span_matching_a_supported_fact_elsewhere_still_rejects() -> None:
    """The exact old-repository incident: a false claim's quoted span (here, the stale version
    string) also appears, verbatim, as a SUPPORTED fact value elsewhere available to the
    reviewer (package:version == "26.9.0"). The old fold bug treated that coincidental match as
    proof of correctness and folded the REJECT to ACCEPT. This must never happen here: the
    verdict is decided by `_fold`, which looks only at `refuted_by`, never at whether a quoted
    span happens to match some other fact's literal value."""
    readme = (
        "## Installation\n\n```bash\ndotnet add package Aspose.PDF.FOSS --version 26.9.0\n```\n\n"
        "The current version is 26.9.0.\n"
    )
    verdict = review_candidate(
        readme_text=readme, units=[], facts=_facts(*NET), dispositions={"dispositions": []},
        original_readme=readme,
    )
    assert verdict.verdict == "REJECT"


# ---------------------------------------------------------------------------
# persisting a verdict (PORT_BUNDLE_INTEGRITY_LAYER's own named gap: a ReviewVerdict was
# computed but never written per repository before now)
# ---------------------------------------------------------------------------


def test_write_then_load_round_trips_an_accept_verdict_with_no_findings(tmp_path) -> None:
    verdict = ReviewVerdict(verdict="ACCEPT", findings=())
    path = tmp_path / "review_verdict.json"
    write_review_verdict(verdict, path)
    assert load_review_verdict(path) == verdict


def test_write_then_load_round_trips_a_reject_verdict_with_mixed_findings(tmp_path) -> None:
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(rule="style_note", kind="judgment", message="a bit verbose"),
            Finding(
                rule="claim_contradiction",
                kind="deterministic",
                message="stale version",
                refuted_by=Refutation(rule="claim_contradiction", evidence="26.1.0 != 26.9.0"),
                quote="version 26.1.0",
            ),
        ),
    )
    path = tmp_path / "review_verdict.json"
    write_review_verdict(verdict, path)
    assert load_review_verdict(path) == verdict


def test_the_persisted_artifact_carries_the_reviewer_logic_version(tmp_path) -> None:
    path = tmp_path / "review_verdict.json"
    write_review_verdict(ReviewVerdict(verdict="ACCEPT", findings=()), path)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["reviewer_logic_version"] == REVIEWER_LOGIC_VERSION


def test_write_review_verdict_returns_the_sha256_of_the_bytes_it_wrote(tmp_path) -> None:
    import hashlib

    path = tmp_path / "review_verdict.json"
    digest = write_review_verdict(ReviewVerdict(verdict="ACCEPT", findings=()), path)
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_fails_closed_on_a_verdict_that_does_not_match_its_own_findings(tmp_path) -> None:
    """An artifact claiming ACCEPT while carrying a deterministic refutation is internally
    inconsistent -- exactly the shape _fold's own invariant forbids being produced honestly, so
    a load must refuse it rather than silently trust the stored ``verdict`` field."""
    path = tmp_path / "review_verdict.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewer_logic_version": REVIEWER_LOGIC_VERSION,
                "verdict": "ACCEPT",
                "findings": [
                    {
                        "rule": "claim_contradiction",
                        "kind": "deterministic",
                        "message": "stale version",
                        "refuted_by": {"rule": "claim_contradiction", "evidence": "x"},
                        "quote": "",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ReviewVerdictError, match="does not match"):
        load_review_verdict(path)


def test_load_fails_closed_on_an_unknown_finding_kind(tmp_path) -> None:
    path = tmp_path / "review_verdict.json"
    path.write_text(
        json.dumps(
            {
                "verdict": "ACCEPT",
                "findings": [{"rule": "x", "kind": "mystery", "message": "m"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ReviewVerdictError, match="unknown finding kind"):
        load_review_verdict(path)


def test_load_fails_closed_on_malformed_json(tmp_path) -> None:
    path = tmp_path / "review_verdict.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ReviewVerdictError, match="cannot read/parse"):
        load_review_verdict(path)
