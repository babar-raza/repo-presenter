"""R5(a): the baseline revision and upstream-change trigger a Lane L run needs before it is even
attempted.

TC-025's census (``docs/investigations/2026-11-07-vs0-vertical-slice.md``) found that today's
engine runs Lane L's correction on ANY detected defect, with no check anywhere that anything
upstream has actually changed since the README was last reconciled -- so the two Lane L edits ever
sealed (3D-Java, Words-Python) would both fail a strict R5 reading, and 19 of 36 registry
repositories have a real upstream change with nobody looking for it. This module is that look: a
pure, offline decision over data the caller supplies (a registry read, a sealed bundle's manifest,
a tree diff -- whatever already exists; this module makes no provider call and reaches no
network itself).

Two steps, kept separate because they answer different questions:

* :func:`compute_baseline` -- the revision R5(a) measures "changed since" *from*: the latest Lane L
  seal's own source revision, when that seal ran under the detector set in force right now (an old
  seal that ran before a detector existed can never suppress the very defect that detector would
  newly catch); otherwise the presenter's own last README-touching commit, when one exists; failing
  that, upstream's own last commit that touched ``README.md``.
* :func:`compute_trigger` -- whether anything relevant (a source file, a package manifest, an
  example, the README itself) changed between that baseline and the current upstream head. A head
  that moved without touching anything relevant is not a trigger (the same ``IRRELEVANT_CHANGE``
  distinction ``monitor/drift.py`` already draws for Lane R, read here without that module's
  network coupling -- ``monitor/drift.py`` only ever judges an *already-sealed* bundle against a
  live head it reads itself, which is not this module's job or shape).

Both functions fail closed: an unknown head, or unknown changed paths, is a trigger (``True``),
never a silently-skipped repository.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

#: Extensions this module treats as source: a change here is never a release-bump-only commit.
_SOURCE_EXTENSIONS: tuple[str, ...] = (
    ".cs", ".java", ".py", ".pyi", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".go", ".rb", ".ts", ".tsx", ".js", ".jsx", ".rs", ".kt", ".scala", ".swift",
)
#: Manifest file names (exact, case-insensitive, at any depth) that describe what a package ships.
_MANIFEST_NAMES: frozenset[str] = frozenset(
    {
        "pom.xml", "build.gradle", "build.gradle.kts", "setup.py", "setup.cfg",
        "pyproject.toml", "requirements.txt", "package.json", "gemfile", "go.mod",
        "cargo.toml", "directory.build.props",
    }
)
_MANIFEST_SUFFIXES: tuple[str, ...] = (".csproj", ".gemspec", ".nuspec", ".fsproj", ".vbproj")


def is_relevant_path(path: str) -> bool:
    """Whether a changed path is something R5(a) means by "something changed": a source file, a
    package manifest, an example, or the README itself. A change that touches none of these (a CI
    badge tweak, an unrelated doc under ``docs/``, a release tag) is not a trigger by itself."""
    lower = path.lower()
    name = lower.rsplit("/", 1)[-1]
    if name == "readme.md":
        return True
    if "/examples/" in lower or lower.startswith("examples/"):
        return True
    if any(lower.endswith(extension) for extension in _SOURCE_EXTENSIONS):
        return True
    if name in _MANIFEST_NAMES:
        return True
    if any(name.endswith(suffix) for suffix in _MANIFEST_SUFFIXES):
        return True
    return False


@dataclass(frozen=True)
class LaneLSeal:
    """What a Lane L run's baseline needs from its most recent seal, when one exists."""

    source_revision: str
    detector_versions: Mapping[str, str]


@dataclass(frozen=True)
class Baseline:
    """The revision R5(a) measures from, and why."""

    repository: str
    revision: str | None
    source: str  # "lane_l_seal" | "presenter_commit" | "upstream_readme_commit" | "none"
    reason: str


def compute_baseline(
    repository: str,
    *,
    current_detector_versions: Mapping[str, str],
    last_lane_l_seal: LaneLSeal | None = None,
    presenter_last_readme_commit: str | None = None,
    upstream_last_readme_commit: str | None = None,
) -> Baseline:
    """The baseline revision, per the module docstring's three-tier fallback.

    A seal only wins when it ran under exactly today's detector set; a seal that ran under an
    older one is not consulted at all here (falling through, as if it did not exist) -- it can
    never suppress a defect a newly-added detector would now catch.
    """
    if last_lane_l_seal is not None and dict(last_lane_l_seal.detector_versions) == dict(
        current_detector_versions
    ):
        return Baseline(
            repository,
            last_lane_l_seal.source_revision,
            "lane_l_seal",
            "the latest Lane L seal ran under the current detector set",
        )
    if presenter_last_readme_commit is not None:
        reason = (
            "no Lane L seal exists yet; using the presenter's own last README-touching commit"
            if last_lane_l_seal is None
            else (
                "the latest Lane L seal ran under an older detector set and cannot suppress a "
                "newly-added detector's finding; falling back to the presenter's own last "
                "README-touching commit"
            )
        )
        return Baseline(repository, presenter_last_readme_commit, "presenter_commit", reason)
    if upstream_last_readme_commit is not None:
        return Baseline(
            repository,
            upstream_last_readme_commit,
            "upstream_readme_commit",
            "neither a current-detector-set Lane L seal nor a presenter commit exists; using "
            "upstream's own last commit that touched README.md",
        )
    return Baseline(
        repository, None, "none", "no baseline could be established from any of the three tiers"
    )


@dataclass(frozen=True)
class TriggerResult:
    """Whether R5(a) is present for this repository right now, and why."""

    repository: str
    baseline: Baseline
    triggered: bool
    reason: str
    changed_paths: tuple[str, ...] = ()


def compute_trigger(
    repository: str,
    *,
    baseline: Baseline,
    head_revision: str | None,
    changed_paths_since_baseline: Sequence[str] | None,
    relevant: Callable[[str], bool] = is_relevant_path,
) -> TriggerResult:
    """Whether anything relevant changed upstream since ``baseline``. Fails closed to triggered
    (never a silent skip) when the baseline, the head, or the changed paths are unknown."""
    if baseline.revision is None:
        return TriggerResult(
            repository,
            baseline,
            True,
            "no baseline revision is on record; the first observation of this repository is "
            "itself a trigger",
        )
    if head_revision is None:
        return TriggerResult(
            repository,
            baseline,
            True,
            "the upstream head could not be read; failing closed to triggered rather than "
            "silently skipping this repository",
        )
    if head_revision == baseline.revision:
        return TriggerResult(
            repository, baseline, False, "the upstream head equals the baseline revision"
        )
    if changed_paths_since_baseline is None:
        return TriggerResult(
            repository,
            baseline,
            True,
            "the head moved but the changed paths since the baseline are unknown; failing "
            "closed to triggered",
        )
    relevant_paths = tuple(path for path in changed_paths_since_baseline if relevant(path))
    if relevant_paths:
        return TriggerResult(
            repository,
            baseline,
            True,
            f"{len(relevant_paths)} path(s) relevant to R5(a) changed since the baseline",
            relevant_paths,
        )
    return TriggerResult(
        repository,
        baseline,
        False,
        "the upstream head moved but touched no source file, package manifest, example or the "
        "README itself",
    )


def trigger_for_repository(
    repository: str,
    *,
    current_detector_versions: Mapping[str, str],
    head_revision: str | None,
    changed_paths_since_baseline: Sequence[str] | None,
    last_lane_l_seal: LaneLSeal | None = None,
    presenter_last_readme_commit: str | None = None,
    upstream_last_readme_commit: str | None = None,
    relevant: Callable[[str], bool] = is_relevant_path,
) -> TriggerResult:
    """:func:`compute_baseline` followed by :func:`compute_trigger`, in one call -- the shape a
    caller with all the raw inputs on hand actually wants."""
    baseline = compute_baseline(
        repository,
        current_detector_versions=current_detector_versions,
        last_lane_l_seal=last_lane_l_seal,
        presenter_last_readme_commit=presenter_last_readme_commit,
        upstream_last_readme_commit=upstream_last_readme_commit,
    )
    return compute_trigger(
        repository,
        baseline=baseline,
        head_revision=head_revision,
        changed_paths_since_baseline=changed_paths_since_baseline,
        relevant=relevant,
    )


# --- the three-outcome taxonomy (TC-025 point 2) -------------------------------------------------

#: At least one net-improvement edit was made (or the run is a fresh, never-sealed repository that
#: still needs a real attempt): a real candidate, sealed or refused on its own merits downstream.
OUTCOME_EDIT_CANDIDATE = "EDIT_CANDIDATE"
#: No R5(a) trigger, or a trigger was present but every finding was already correctly fixed or
#: absent, EARNED by running TC-017a's probes over the live README first (never silence).
OUTCOME_NO_ACTION_JUSTIFIED = "NO_ACTION_JUSTIFIED"
#: No README exists at all: Lane L has nothing to correct, and Lane R is the right lane, not a
#: Lane L failure.
OUTCOME_NOT_APPLICABLE = "NOT_APPLICABLE"
OUTCOMES: tuple[str, ...] = (
    OUTCOME_EDIT_CANDIDATE,
    OUTCOME_NO_ACTION_JUSTIFIED,
    OUTCOME_NOT_APPLICABLE,
)


def classify_outcome(
    *,
    readme_exists: bool,
    trigger: TriggerResult,
    has_findings: bool,
    probes_clean: bool | None,
) -> str:
    """The three-outcome taxonomy, from already-computed signals; itself makes no provider call
    and runs no probe -- ``probes_clean`` is the caller's own result of running TC-017a's probes
    over the live README (mandatory before any ``NO_ACTION_JUSTIFIED`` seal: an earned result,
    never silence).

    ``has_findings`` is whether this run's own engine reported anything at all (a defect or an
    opportunity) against the live README as it stands today, independent of ``trigger``: a
    repository can have no R5(a) trigger and still carry a finding nothing has ever fixed, and
    that finding must not be waved through as "nothing to do" just because nothing upstream moved.
    """
    if not readme_exists:
        return OUTCOME_NOT_APPLICABLE
    if not trigger.triggered and not has_findings:
        return OUTCOME_NO_ACTION_JUSTIFIED
    if not trigger.triggered and has_findings:
        # A trigger absent but a finding present is not yet earned as "nothing to do": only a
        # clean probe pass may call it justified; anything else is a real attempt to make.
        if probes_clean is True:
            return OUTCOME_NO_ACTION_JUSTIFIED
        return OUTCOME_EDIT_CANDIDATE
    return OUTCOME_EDIT_CANDIDATE
