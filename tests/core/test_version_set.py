"""core/version_set.py and the seal-history counting built on it (owner rules, 2026-11-06).

(1) ONE version set for every candidate that counts -- counts are grouped by fingerprint and never
summed across fingerprints. (2) A version bump never invalidates a sealed candidate -- a later
failed run under a new set leaves every earlier seal counted under its own set.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import init_git_repository

from repo_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME
from repo_presenter.core.errors import PresenterError
from repo_presenter.core.portfolio_matrix import build_matrix, summarize
from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repo_presenter.core.state.bundle_store import SealRecord, publish_bundle, seal_history
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.version_set import (
    current_fingerprint,
    fingerprint,
    group_by_fingerprint,
    short,
    version_set_report,
)
from repo_presenter.present import run_present


def deps(*, review_sha: str = "a" * 64, revision: str = "r1", facts: dict | None = None,
         python: str = "3.13.0", reviewer_logic: str = "10") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": {"revision": revision},
        "environment": {
            "python_version": python,
            "os": "Linux",
            "inherited_units_version": "3",
            "toolchains": {"dotnet": "8.0"},
        },
        "facts": facts or {"f1": "0" * 64},
        "prompts": {
            "independent_review": {"sha256": review_sha, "version": "21", "model_route": "m"}
        },
        "components": {"renderer": "36", "reviewer_logic": reviewer_logic, "shell": "1",
                       "normalisation": "1"},
    }


# --- the fingerprint ---------------------------------------------------------------------------


def test_a_prompt_sha_change_alone_changes_the_fingerprint() -> None:
    assert fingerprint(deps(), "R") != fingerprint(deps(review_sha="b" * 64), "R")


def test_any_mechanism_version_changes_the_fingerprint() -> None:
    assert fingerprint(deps(), "R") != fingerprint(deps(reviewer_logic="11"), "R")
    changed = deps()
    changed["environment"]["inherited_units_version"] = "4"
    assert fingerprint(deps(), "R") != fingerprint(changed, "R")
    future = deps()
    future["acceptance_profile_version"] = "2"  # a mechanism key a future seal adds
    assert fingerprint(deps(), "R") != fingerprint(future, "R")


def test_per_repository_inputs_and_the_machine_never_change_the_fingerprint() -> None:
    base = fingerprint(deps(), "R")
    assert fingerprint(deps(revision="r2"), "R") == base
    assert fingerprint(deps(facts={"other": "1" * 64}), "R") == base
    assert fingerprint(deps(python="3.12.1"), "R") == base


def test_each_lane_has_its_own_fingerprint() -> None:
    assert fingerprint(deps(), "R") != fingerprint(deps(), "L")


def test_the_current_fingerprint_equals_a_bundle_sealed_by_current_code_lane_r(
    tmp_path: Path,
) -> None:
    from repo_presenter.readme.bundle.seal import seal_candidate
    from tests.readme.bundle.test_seal import _inputs, _prompt_registry

    result = seal_candidate(_inputs(tmp_path))
    sealed = json.loads((result.bundle / "dependencies.json").read_text(encoding="utf-8"))
    assert fingerprint(sealed, "R") == current_fingerprint("R", _prompt_registry())


def test_the_current_fingerprint_equals_a_bundle_sealed_by_current_code_lane_l(
    tmp_path: Path,
) -> None:
    from repo_presenter.readme.bundle.seal import seal_candidate
    from tests.readme.bundle.test_seal_lane_l import _l_inputs, _registry

    result = seal_candidate(_l_inputs(tmp_path))
    sealed = json.loads((result.bundle / "dependencies.json").read_text(encoding="utf-8"))
    assert fingerprint(sealed, "L") == current_fingerprint("L", _registry())
    assert fingerprint(sealed, "L") != current_fingerprint("R", _registry())


# --- counting: grouped, never summed ------------------------------------------------------------

A = SimpleNamespace(repository="o/a", ecosystem="net", mode="full")
B = SimpleNamespace(repository="o/b", ecosystem="java", mode="full")
ACCEPT = {"verdict": "ACCEPT", "model_verdict": "ACCEPT"}


def seal(repository: str, dependencies: dict, *, state: str = "ACCEPTED", review=ACCEPT,
         commit: str = "c1") -> SealRecord:
    return SealRecord(repository, "R", commit, "rev", state, dependencies, review)


def test_two_repositories_sealed_under_different_fingerprints_are_never_summed(
    tmp_path: Path,
) -> None:
    v1, v2 = deps(), deps(review_sha="b" * 64)
    history = {(A.repository, "R"): [seal(A.repository, v1)],
               (B.repository, "R"): [seal(B.repository, v2)]}
    rows = build_matrix([A, B], lambda _r, _l: None, tmp_path, (), history)
    summary = summarize(rows, {"R": fingerprint(v2, "R"), "L": "x"})
    assert summary["lane_r_pipeline_good"] == 1  # never 2
    sets = summary["lane_r_version_sets"]
    assert sets["current_repositories"] == [B.repository]
    assert sets["older_version_sets"] == {short(fingerprint(v1, "R")): 1}


def test_only_a_pipeline_good_model_accept_seal_counts(tmp_path: Path) -> None:
    v1 = deps()
    history = {
        (A.repository, "R"): [seal(A.repository, v1, state="INVALIDATED")],
        (B.repository, "R"): [seal(B.repository, v1, review={"verdict": "ACCEPT", "model_verdict": None})],
    }
    rows = build_matrix([A, B], lambda _r, _l: None, tmp_path, (), history)
    assert summarize(rows, {"R": fingerprint(v1, "R")})["lane_r_pipeline_good"] == 0


def test_the_record_state_is_reported_as_an_attempt_and_never_counted(tmp_path: Path) -> None:
    v1 = deps()
    history = {(A.repository, "R"): [seal(A.repository, v1)]}
    rows = build_matrix([A, B], lambda r, _l: "INVALIDATED" if r == A.repository else "ACCEPTED",
                        tmp_path, (), history)
    summary = summarize(rows, {"R": fingerprint(v1, "R")})
    # A's latest attempt failed (INVALIDATED) but its seal stands; B's record says ACCEPTED but
    # it has no seal at all, so it does not count.
    assert summary["lane_r_pipeline_good"] == 1
    assert summary["lane_r_version_sets"]["current_repositories"] == [A.repository]
    assert summary["lane_r_record_states"] == {"ACCEPTED": 1, "INVALIDATED": 1}


def test_version_set_report_never_totals_across_sets() -> None:
    report = version_set_report(group_by_fingerprint([("a", "f1"), ("b", "f2"), ("a", "f2")]), "f2")
    assert report["current_count"] == 2 and report["older_version_sets"] == {"f1": 1}
    assert not any("total" in key for key in report)


# --- no demotion, end to end against a real git state remote ------------------------------------

REPO = "example/Aspose.Widget-FOSS-for-Python"


def _entry() -> RegistryEntry:
    return RegistryEntry(
        repository=REPO, family="widget", platform="python", ecosystem="python", mode="full",
        policy_profile="example-widget", active=True,
        provider_identity=ProviderIdentity(repository_id=4242, node_id="R_4242"),
    )


def _write_seal(root: Path, dependencies: dict) -> Path:
    repository_dir = root / CANDIDATES_DIRNAME / REPO.replace("/", "__")
    bundle = repository_dir / "rev-1"
    bundle.mkdir(parents=True)
    artifacts = {
        "README.md": b"README content\n",
        "dependencies.json": json.dumps(dependencies).encode(),
        "review_verdict.json": json.dumps(ACCEPT).encode(),
    }
    for name, data in artifacts.items():
        (bundle / name).write_bytes(data)
    manifest = {
        "schema_version": 1, "repository": REPO, "revision": "rev-1", "state": "ACCEPTED",
        "provider_calls": 3, "no_op_proof": None,
        "files": {n: {"sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)}
                  for n, d in artifacts.items()},
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (repository_dir / CURRENT_FILENAME).write_text("rev-1\n", encoding="utf-8")
    return repository_dir


def test_a_seal_under_v1_survives_a_failed_run_under_v2(tmp_path: Path) -> None:
    remote = init_git_repository(tmp_path / "state-remote")
    workdir = tmp_path / "work"
    v1, v2 = deps(), deps(review_sha="b" * 64)
    fp1, fp2 = fingerprint(v1, "R"), fingerprint(v2, "R")
    entry = _entry()

    def sealed_run() -> None:
        _write_seal(workdir, v1)

    def publish() -> None:
        publish_bundle(REPO, "R", workdir / CANDIDATES_DIRNAME / REPO.replace("/", "__"),
                       remote=str(remote))

    def failed_run() -> None:
        raise PresenterError("review rejected the candidate under the new prompt")

    published: list[str] = []
    with GitStateBackend(remote=str(remote)) as backend:
        assert run_present(backend=backend, entry=entry, candidates_root=workdir,
                           holder_id="h1", workflow_run_id="run-1", pipeline=sealed_run,
                           publish=publish, version_set=fp1) == 0
        assert backend.load(REPO).state == "ACCEPTED"
        assert run_present(backend=backend, entry=entry, candidates_root=workdir,
                           holder_id="h2", workflow_run_id="run-2", pipeline=failed_run,
                           publish=lambda: published.append("x"), version_set=fp2) == 1
        record = backend.load(REPO)

    # the failed attempt is visible on the record, which routes to INVALIDATED for itself ...
    assert record.state == "INVALIDATED"
    assert record.failure is not None and f"version set {fp2[:12]}" in record.failure.detail
    assert published == []  # ... and a failed run never publishes to the bundle ref
    history = seal_history(remote=str(remote))
    seals = history[(REPO, "R")]
    assert len(seals) == 1 and seals[0].counted and seals[0].error == ""

    rows = build_matrix([entry], lambda _r, _l: str(record.state), tmp_path / "none", (), history)
    under_v2 = summarize(rows, {"R": fp2})
    assert under_v2["lane_r_pipeline_good"] == 0
    assert under_v2["lane_r_version_sets"]["older_version_sets"] == {short(fp1): 1}
    under_v1 = summarize(rows, {"R": fp1})
    assert under_v1["lane_r_pipeline_good"] == 1


def test_seal_history_keeps_every_seal_on_the_ref(tmp_path: Path) -> None:
    remote = init_git_repository(tmp_path / "state-remote")
    root = tmp_path / "work"
    repository_dir = _write_seal(root, deps())
    publish_bundle(REPO, "R", repository_dir, remote=str(remote))
    # a later re-seal under a new version set adds a commit; the first seal stays in the history
    import shutil

    shutil.rmtree(repository_dir)
    _write_seal(root, deps(review_sha="c" * 64))
    publish_bundle(REPO, "R", repository_dir, remote=str(remote))
    seals = seal_history(remote=str(remote))[(REPO, "R")]
    assert [fingerprint(s.dependencies, "R") for s in seals] == [
        fingerprint(deps(), "R"), fingerprint(deps(review_sha="c" * 64), "R")
    ]


def test_a_corrupt_seal_is_a_recorded_error_never_a_count(tmp_path: Path) -> None:
    remote = init_git_repository(tmp_path / "state-remote")
    repository_dir = _write_seal(tmp_path / "work", deps())
    publish_bundle(REPO, "R", repository_dir, remote=str(remote))
    history = seal_history(remote=str(remote))
    good = history[(REPO, "R")][0]
    corrupt = copy.replace(good, error="bundle artifact README.md is corrupt")
    assert good.counted and not corrupt.counted


@pytest.mark.parametrize("lane", ["R", "L"])
def test_parse_bundle_ref_round_trips(lane: str) -> None:
    from repo_presenter.core.state.bundle_store import bundle_ref, parse_bundle_ref

    assert parse_bundle_ref(bundle_ref("o/n", lane)) == ("o/n", lane)
