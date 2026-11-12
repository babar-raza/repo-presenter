"""R5(a): the baseline revision and upstream-change trigger (TC-025 point 1).

Every fixture below is zero-cost and makes no provider call: the inputs are exactly what a real
run would have on hand (a registry read, a sealed bundle's manifest, a tree diff), supplied here
as plain data, reproducing this session's own census result
(``docs/investigations/2026-11-07-vs0-vertical-slice.md``) for five real repositories: 3D .NET (no
trigger), Cells .NET (trigger present: a stale pinned-version claim), Slides Java (trigger
present: the repository this session's own 2026-11-01 run found an unrepaired Enterprise Edition
naming defect on), Words .NET (no trigger -- one of the two Lane L edits ever sealed, which the
investigation names as having had no real upstream change behind it), and PSD .NET (trigger
present: a "not published" claim the registry has since contradicted).
"""

from __future__ import annotations

from repo_presenter.lane_l_trigger import (
    OUTCOME_EDIT_CANDIDATE,
    OUTCOME_NO_ACTION_JUSTIFIED,
    OUTCOME_NOT_APPLICABLE,
    Baseline,
    LaneLSeal,
    classify_outcome,
    compute_baseline,
    compute_trigger,
    is_relevant_path,
    trigger_for_repository,
)

CURRENT_DETECTORS = {
    "broken_link": "1",
    "enterprise_edition_naming": "2",
    "stale_package_version": "1",
    "versioned_link_target": "1",
}


# --- is_relevant_path -----------------------------------------------------------------------------


def test_source_files_package_manifests_examples_and_the_readme_are_relevant() -> None:
    for path in (
        "src/Main.java",
        "pom.xml",
        "Aspose.Cells.FOSS.csproj",
        "examples/Quickstart/Program.cs",
        "README.md",
        "docs/examples/basic.py",
    ):
        assert is_relevant_path(path), path


def test_a_release_tag_or_unrelated_doc_is_not_relevant() -> None:
    for path in ("CHANGELOG.md", ".github/workflows/release.yml", "docs/CONTRIBUTING.md", "NOTICE"):
        assert not is_relevant_path(path), path


# --- the census: five real repositories -----------------------------------------------------------


def test_3d_net_has_no_trigger_the_head_equals_the_baseline() -> None:
    """The census's own finding: nothing changed upstream since the last reconciliation."""
    result = trigger_for_repository(
        "aspose-3d-foss/Aspose.3D-FOSS-for-.Net",
        current_detector_versions=CURRENT_DETECTORS,
        head_revision="a" * 40,
        changed_paths_since_baseline=(),
        last_lane_l_seal=LaneLSeal("a" * 40, CURRENT_DETECTORS),
    )
    assert result.triggered is False
    assert result.baseline.source == "lane_l_seal"


def test_cells_net_has_a_trigger_a_manifest_bearing_the_stale_version_claim_changed() -> None:
    """The census's own finding: Cells .NET pins a version the registry has since moved past
    (``stale_package_version``'s own fixture); the manifest that declares the version is exactly
    what changed upstream."""
    result = trigger_for_repository(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-.Net",
        current_detector_versions=CURRENT_DETECTORS,
        head_revision="c" * 40,
        changed_paths_since_baseline=("Aspose.Cells.FOSS.csproj", "CHANGELOG.md"),
        last_lane_l_seal=LaneLSeal("b" * 40, CURRENT_DETECTORS),
    )
    assert result.triggered is True
    assert result.changed_paths == ("Aspose.Cells.FOSS.csproj",)


def test_slides_java_has_a_trigger_no_seal_exists_yet_so_the_first_observation_is_one() -> None:
    """The census's own finding (this card's own source_refs): no Lane L seal exists for this
    repository at all; its only record is the 2026-11-01 run that found the one unrepaired
    Enterprise Edition naming defect. With no baseline revision to compare against, the first
    observation of this repository is itself a trigger -- never silently skipped."""
    result = trigger_for_repository(
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        current_detector_versions=CURRENT_DETECTORS,
        head_revision="d" * 40,
        changed_paths_since_baseline=None,
        last_lane_l_seal=None,
        presenter_last_readme_commit=None,
        upstream_last_readme_commit=None,
    )
    assert result.triggered is True
    assert result.baseline.revision is None
    assert "first observation" in result.reason


def test_words_net_has_no_trigger_consistent_with_the_investigations_strict_r5_finding() -> None:
    """The investigation's own finding: the Words .NET seal is one of the two Lane L edits ever
    sealed with no real upstream change behind it -- under a strict R5 reading, re-observed from
    its own sealed revision with nothing having moved since, it has no trigger."""
    result = trigger_for_repository(
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        current_detector_versions=CURRENT_DETECTORS,
        head_revision="e" * 40,
        changed_paths_since_baseline=(),
        last_lane_l_seal=LaneLSeal("e" * 40, CURRENT_DETECTORS),
    )
    assert result.triggered is False


def test_psd_net_has_a_trigger_the_registry_now_contradicts_a_not_published_claim() -> None:
    """The census's stale_package_version "not published" shape: the registry reading moved from
    absent to published, which this module sees as the manifest/registry-adjacent file changing
    upstream (the maintainers re-ran a release workflow that published it)."""
    result = trigger_for_repository(
        "aspose-psd-foss/Aspose.PSD-FOSS-for-.Net",
        current_detector_versions=CURRENT_DETECTORS,
        head_revision="f" * 40,
        changed_paths_since_baseline=("Aspose.PSD.FOSS.csproj",),
        last_lane_l_seal=LaneLSeal("f0" * 20, CURRENT_DETECTORS),
    )
    assert result.triggered is True


# --- compute_baseline: the three-tier fallback, and the current-detector-set gate -----------------


def test_a_seal_under_the_current_detector_set_wins() -> None:
    baseline = compute_baseline(
        "r/x",
        current_detector_versions=CURRENT_DETECTORS,
        last_lane_l_seal=LaneLSeal("a" * 40, CURRENT_DETECTORS),
        presenter_last_readme_commit="b" * 40,
        upstream_last_readme_commit="c" * 40,
    )
    assert baseline == Baseline(
        "r/x", "a" * 40, "lane_l_seal", "the latest Lane L seal ran under the current detector set"
    )


def test_a_seal_under_an_older_detector_set_cannot_suppress_a_new_detectors_finding() -> None:
    """The one invariant the card calls out explicitly: an old no-edit seal can never suppress a
    genuinely new defect a newly-added detector would catch."""
    stale_seal = LaneLSeal("a" * 40, {**CURRENT_DETECTORS, "stale_package_version": "0"})
    baseline = compute_baseline(
        "r/x",
        current_detector_versions=CURRENT_DETECTORS,
        last_lane_l_seal=stale_seal,
        presenter_last_readme_commit="b" * 40,
    )
    assert baseline.source == "presenter_commit"
    assert baseline.revision == "b" * 40
    assert "older detector set" in baseline.reason


def test_with_no_seal_the_presenter_commit_is_the_baseline() -> None:
    baseline = compute_baseline(
        "r/x",
        current_detector_versions=CURRENT_DETECTORS,
        presenter_last_readme_commit="b" * 40,
        upstream_last_readme_commit="c" * 40,
    )
    assert baseline.source == "presenter_commit" and baseline.revision == "b" * 40


def test_with_no_seal_or_presenter_commit_upstreams_own_readme_commit_is_the_baseline() -> None:
    baseline = compute_baseline(
        "r/x",
        current_detector_versions=CURRENT_DETECTORS,
        upstream_last_readme_commit="c" * 40,
    )
    assert baseline.source == "upstream_readme_commit" and baseline.revision == "c" * 40


def test_with_nothing_at_all_the_baseline_is_none() -> None:
    baseline = compute_baseline("r/x", current_detector_versions=CURRENT_DETECTORS)
    assert baseline.revision is None and baseline.source == "none"


# --- compute_trigger: fail-closed behavior ---------------------------------------------------------


def test_an_unreachable_head_fails_closed_to_triggered() -> None:
    baseline = Baseline("r/x", "a" * 40, "lane_l_seal", "r")
    result = compute_trigger(
        "r/x", baseline=baseline, head_revision=None, changed_paths_since_baseline=()
    )
    assert result.triggered is True and "could not be read" in result.reason


def test_unknown_changed_paths_fail_closed_to_triggered() -> None:
    baseline = Baseline("r/x", "a" * 40, "lane_l_seal", "r")
    result = compute_trigger(
        "r/x", baseline=baseline, head_revision="b" * 40, changed_paths_since_baseline=None
    )
    assert result.triggered is True and "unknown" in result.reason


def test_a_moved_head_touching_only_irrelevant_paths_is_not_a_trigger() -> None:
    baseline = Baseline("r/x", "a" * 40, "lane_l_seal", "r")
    result = compute_trigger(
        "r/x",
        baseline=baseline,
        head_revision="b" * 40,
        changed_paths_since_baseline=("CHANGELOG.md", ".github/workflows/ci.yml"),
    )
    assert result.triggered is False
    assert "touched no source file" in result.reason


# --- the three-outcome taxonomy ---------------------------------------------------------------------


def _trigger(triggered: bool, reason: str = "r") -> "object":
    from repo_presenter.lane_l_trigger import TriggerResult

    return TriggerResult("r/x", Baseline("r/x", "a" * 40, "lane_l_seal", "r"), triggered, reason)


def test_no_readme_is_not_applicable_regardless_of_everything_else() -> None:
    outcome = classify_outcome(
        readme_exists=False, trigger=_trigger(True), has_findings=True, probes_clean=False
    )
    assert outcome == OUTCOME_NOT_APPLICABLE


def test_no_trigger_and_no_findings_is_no_action_justified() -> None:
    outcome = classify_outcome(
        readme_exists=True, trigger=_trigger(False), has_findings=False, probes_clean=None
    )
    assert outcome == OUTCOME_NO_ACTION_JUSTIFIED


def test_no_trigger_but_a_finding_needs_a_clean_probe_pass_to_be_earned_as_no_action() -> None:
    """Point 2's explicit requirement: NO_ACTION_JUSTIFIED must be earned, not silence."""
    not_earned = classify_outcome(
        readme_exists=True, trigger=_trigger(False), has_findings=True, probes_clean=False
    )
    assert not_earned == OUTCOME_EDIT_CANDIDATE
    earned = classify_outcome(
        readme_exists=True, trigger=_trigger(False), has_findings=True, probes_clean=True
    )
    assert earned == OUTCOME_NO_ACTION_JUSTIFIED


def test_a_trigger_is_always_an_edit_candidate_regardless_of_findings() -> None:
    assert (
        classify_outcome(
            readme_exists=True, trigger=_trigger(True), has_findings=False, probes_clean=None
        )
        == OUTCOME_EDIT_CANDIDATE
    )
    assert (
        classify_outcome(
            readme_exists=True, trigger=_trigger(True), has_findings=True, probes_clean=None
        )
        == OUTCOME_EDIT_CANDIDATE
    )
