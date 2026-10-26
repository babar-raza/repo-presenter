"""The hosted ``present`` wiring: durable transaction around one pipeline, against the real git-ref
backend on a disposable local remote (no mocked backend), plus the Lane L facts stage on a real
clone-shaped repository. The LLM cascade itself is proven by the live runs in
evidence/build/P2_REAL_ENGINE_SALVAGE/, not re-run here."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from support import commit_all, init_git_repository, write_registry_file

from repo_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME
from repo_presenter.core.errors import NotAllowlistedError
from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.state.health import evaluate_repository_health
from repo_presenter.lane_l import build_lane_l_facts
from repo_presenter.present import PresentFailure, main, run_present

REPO = "example/Aspose.Widget-FOSS-for-Python"
PROVIDER_ID = 4242


def _entry() -> RegistryEntry:
    return RegistryEntry(
        repository=REPO,
        family="widget",
        platform="python",
        ecosystem="python",
        mode="full",
        policy_profile="example-widget",
        active=True,
        provider_identity=ProviderIdentity(repository_id=PROVIDER_ID, node_id="R_4242"),
    )


def _write_sealed_bundle(root: Path, entry: RegistryEntry, state: str) -> None:
    bundle = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / "rev-1"
    bundle.mkdir(parents=True)
    artifact = b"README content\n"
    (bundle / "README.md").write_bytes(artifact)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "repository": entry.repository,
        "revision": "rev-1",
        "state": state,
        "provider_calls": 3,
        "no_op_proof": None,
        "files": {
            "README.md": {
                "sha256": hashlib.sha256(artifact).hexdigest(),
                "bytes": len(artifact),
            }
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (bundle.parent / CURRENT_FILENAME).write_text("rev-1\n", encoding="utf-8")


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "state-remote")


def test_a_sealed_candidate_commits_accepted_and_releases_the_lease(
    remote: Path, tmp_path: Path
) -> None:
    entry = _entry()
    workdir = tmp_path / "work"

    def pipeline() -> None:
        _write_sealed_bundle(workdir, entry, "ACCEPTED")

    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present(
            backend=backend,
            entry=entry,
            workdir=workdir,
            holder_id="present:run-1",
            workflow_run_id="run-1",
            pipeline=pipeline,
        )
        record = backend.load(REPO)

    assert exit_code == 0
    assert record is not None
    assert record.state == "ACCEPTED"
    assert record.lease is None
    assert record.last_transition is not None
    assert record.last_transition.from_state == "REVIEWING"
    assert record.last_transition.to_state == "ACCEPTED"
    assert evaluate_repository_health(REPO, record) == []


def test_a_rejected_candidate_records_a_named_failure_not_a_silent_drop(
    remote: Path, tmp_path: Path
) -> None:
    entry = _entry()

    def pipeline() -> None:
        raise PresentFailure(
            "independent review returned REJECT with 2 finding(s); nothing sealed"
        )

    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present(
            backend=backend,
            entry=entry,
            workdir=tmp_path / "work",
            holder_id="present:run-2",
            workflow_run_id="run-2",
            pipeline=pipeline,
        )
        record = backend.load(REPO)

    assert exit_code == 1
    assert record is not None
    assert record.state == "FAILED_INTERNAL"
    assert record.lease is None
    assert record.failure is not None
    assert "independent review returned REJECT" in record.failure.detail
    alerts = evaluate_repository_health(REPO, record)
    assert [a.kind for a in alerts] == ["transaction_failed"]
    assert alerts[0].repository == REPO


def test_an_untyped_defect_propagates_and_still_releases_the_lease(
    remote: Path, tmp_path: Path
) -> None:
    entry = _entry()

    def pipeline() -> None:
        raise RuntimeError("a genuine bug, not a typed failure")

    with GitStateBackend(remote=str(remote)) as backend:
        with pytest.raises(RuntimeError, match="genuine bug"):
            run_present(
                backend=backend,
                entry=entry,
                workdir=tmp_path / "work",
                holder_id="present:run-3",
                workflow_run_id="run-3",
                pipeline=pipeline,
            )
        record = backend.load(REPO)

    assert record is not None
    assert record.lease is None


def test_a_repository_outside_the_allow_list_is_refused_before_any_work(
    tmp_path: Path,
) -> None:
    registry = write_registry_file(tmp_path, [])
    exit_code = main(
        [
            "--repository",
            "someone-else/not-listed",
            "--ecosystem",
            "python",
            "--registry",
            str(registry),
            "--workdir",
            str(tmp_path / "work"),
        ]
    )
    assert exit_code == NotAllowlistedError.exit_code
    assert not (tmp_path / "work").exists()


def test_lane_l_facts_describe_the_pinned_clone_and_its_readme(tmp_path: Path) -> None:
    clone = init_git_repository(tmp_path / "clone")
    (clone / "README.md").write_text(
        "# Example\n\nA plain description.\n", encoding="utf-8"
    )
    (clone / "example_widget.py").write_text(
        "def render():\n    return 1\n", encoding="utf-8"
    )
    revision = commit_all(clone, "seed")

    document = build_lane_l_facts(
        REPO,
        clone,
        "python",
        source_revision=revision,
        workspace=tmp_path / "examples",
    )

    assert document.repository == REPO
    assert document.source_revision == revision
    assert any(fact.kind == "identity" for fact in document.facts)
