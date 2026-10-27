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
import yaml
from support import (
    commit_all,
    head_revision,
    init_git_repository,
    monitor_registry_entry,
    write_registry_file,
)

from repo_presenter import present
from repo_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME
from repo_presenter.core.errors import (
    ConfigError,
    JobError,
    NotAllowlistedError,
    OutputRejectedError,
)
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.state.health import evaluate_repository_health
from repo_presenter.facts_handoff import (
    MANIFEST_FILENAME,
    FactsHandoffError,
    load_handoff,
    write_handoff,
)
from repo_presenter.lane_l import build_lane_l_facts
from repo_presenter.present import PresentFailure, main, run_present
from repo_presenter.readme.evidence.facts import links

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
            candidates_root=workdir,
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
            candidates_root=tmp_path / "work",
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


def test_a_model_output_rejection_is_recorded_as_a_retryable_failure(
    remote: Path, tmp_path: Path
) -> None:
    entry = _entry()

    def pipeline() -> None:
        raise OutputRejectedError(
            "section_authoring: output rejected twice; last rejection: unit capability:4: "
            "cites facts outside its slot's planned set (format:output.3mf)"
        )

    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present(
            backend=backend,
            entry=entry,
            candidates_root=tmp_path / "work",
            holder_id="present:run-4",
            workflow_run_id="run-4",
            pipeline=pipeline,
        )
        record = backend.load(REPO)

    assert exit_code == 1
    assert record is not None
    assert record.state == "FAILED_INTERNAL"
    assert record.lease is None
    assert record.failure is not None
    assert record.failure.classification == "transient"
    assert "retryable" in record.failure.detail
    assert "format:output.3mf" in record.failure.detail


@pytest.mark.parametrize(
    "error",
    [
        PresentFailure("independent review returned REJECT with 1 finding(s); nothing sealed"),
        JobError("section_authoring: output truncated at the manifest's max_output_tokens"),
    ],
)
def test_other_typed_failures_keep_the_validation_failed_classification(
    remote: Path, tmp_path: Path, error: Exception
) -> None:
    entry = _entry()

    def pipeline() -> None:
        raise error

    with GitStateBackend(remote=str(remote)) as backend:
        run_present(
            backend=backend,
            entry=entry,
            candidates_root=tmp_path / "work",
            holder_id="present:run-5",
            workflow_run_id="run-5",
            pipeline=pipeline,
        )
        record = backend.load(REPO)

    assert record is not None
    assert record.failure is not None
    assert record.failure.classification == "validation_failed"
    assert record.state == "FAILED_INTERNAL"


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
                candidates_root=tmp_path / "work",
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


def test_lane_l_facts_describe_the_pinned_clone_and_its_readme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []

    def fetch(url: str, transport: object = None) -> tuple[int, str]:
        asked.append(url)
        return 200, url

    monkeypatch.setattr(links, "fetch_status", fetch)
    clone = init_git_repository(tmp_path / "clone")
    (clone / "README.md").write_text(
        "# Example\n\nA plain description. See [the docs](https://example.org/docs).\n",
        encoding="utf-8",
    )
    (clone / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted.\n", encoding="utf-8"
    )
    (clone / "example_widget.py").write_text(
        "def render():\n    return 1\n", encoding="utf-8"
    )
    workflows = clone / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "on: [push]\njobs:\n  test:\n    steps:\n      - run: pytest\n",
        encoding="utf-8",
    )
    revision = commit_all(clone, "seed")

    document = build_lane_l_facts(
        REPO,
        clone,
        "python",
        source_revision=revision,
        workspace=tmp_path / "examples",
        entry=_entry(),
    )

    assert document.repository == REPO
    assert document.source_revision == revision
    ids = {fact.id for fact in document.facts}
    assert {
        "license:spdx",
        "link_target:badge.ci",
        "link_target:product.enterprise",
        "link_target:product.homepage",
        "link_target:product.banner",
        "build_test_asset:test-command",
    } <= ids
    assert "https://example.org/docs" in asked


STAGE_REPO = "aspose-widget-foss/Aspose.Widget-FOSS-for-Python"
WORKFLOW = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "present.yml"
)
TOOLCHAIN_ACTIONS = (
    "setup-dotnet",
    "setup-java",
    "setup-go",
    "setup-node",
    "setup-ruby",
    "setup-rust",
    "rust-toolchain",
    "setup-cpp",
)


@pytest.fixture
def upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A disposable upstream repository the stages clone through ``file://`` instead of GitHub."""

    def fetch(url: str, transport: object = None) -> tuple[int, str]:
        return 200, url

    monkeypatch.setattr(links, "fetch_status", fetch)
    root = init_git_repository(tmp_path / "upstream")
    (root / "README.md").write_text(
        "# Widget\n\nA plain description.\n", encoding="utf-8"
    )
    (root / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted.\n", encoding="utf-8"
    )
    (root / "widget.py").write_text("def render():\n    return 1\n", encoding="utf-8")
    commit_all(root, "seed")
    monkeypatch.setattr(present, "_clone_url", lambda repository: root.as_uri())
    return root


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    return write_registry_file(
        tmp_path / "reg",
        [monitor_registry_entry(STAGE_REPO, mode="full", repository_id=7)],
    )


def _stage_args(stage: str, tmp_path: Path, registry: Path, *extra: str) -> list[str]:
    return [
        "--stage",
        stage,
        "--repository",
        STAGE_REPO,
        "--ecosystem",
        "python",
        "--registry",
        str(registry),
        "--workdir",
        str(tmp_path / f"work-{stage}"),
        "--facts-dir",
        str(tmp_path / "handoff"),
        "--candidates-root",
        str(tmp_path / "candidates"),
        *extra,
    ]


def _run_facts_stage(tmp_path: Path, registry: Path) -> dict[str, str]:
    assert main(_stage_args("facts", tmp_path, registry)) == 0
    return json.loads(
        (tmp_path / "handoff" / MANIFEST_FILENAME).read_text(encoding="utf-8")
    )


def _cascade_stage(
    tmp_path: Path,
    registry: Path,
    monkeypatch: pytest.MonkeyPatch,
    state_remote: Path,
    *extra: str,
) -> tuple[int, Any, list[dict[str, Any]]]:
    """Run ``--stage cascade`` with provider env present and ``run_cascade`` replaced by a recorder
    that stops the pipeline with a typed failure, so no provider is ever called."""
    reached: list[dict[str, Any]] = []

    def fake_cascade(*args: Any, **kwargs: Any) -> None:
        reached.append({"args": args, **kwargs})
        raise PresentFailure("cascade reached")

    monkeypatch.setattr(present, "run_cascade", fake_cascade)
    monkeypatch.setenv("GPT_OSS_ENDPOINT", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("GPT_OSS_API_KEY", "not-a-real-key")
    exit_code = main(
        _stage_args(
            "cascade", tmp_path, registry, "--state-remote", str(state_remote), *extra
        )
    )
    with GitStateBackend(remote=str(state_remote)) as backend:
        record = backend.load(STAGE_REPO)
    return exit_code, record, reached


def test_the_facts_stage_needs_no_provider_variables_and_no_state_backend(
    upstream: Path, registry: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "GPT_OSS_ENDPOINT",
        "GPT_OSS_API_KEY",
        "GPT_OSS_MODEL",
        "GITHUB_ACTIONS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("REPOSITORY_PRESENTER_STATE_TOKEN", raising=False)
    monkeypatch.delenv("REPOSITORY_PRESENTER_READ_TOKEN", raising=False)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "the facts stage must not touch the state backend or the provider"
        )

    monkeypatch.setattr(present, "GitStateBackend", forbidden)
    monkeypatch.setattr(present, "run_cascade", forbidden)
    monkeypatch.setattr(present, "load_gateway_config", forbidden)

    manifest = _run_facts_stage(tmp_path, registry)

    handoff = tmp_path / "handoff"
    assert manifest == {
        "repository": STAGE_REPO,
        "ecosystem": "python",
        "source_revision": head_revision(upstream),
        "facts_sha256": hashlib.sha256(
            (handoff / "facts.json").read_bytes()
        ).hexdigest(),
    }
    loaded, document = load_handoff(handoff, repository=STAGE_REPO, ecosystem="python")
    assert loaded.source_revision == document.source_revision


def test_the_cascade_stage_consumes_verified_facts_at_the_recorded_revision(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _run_facts_stage(tmp_path, registry)

    def never(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the cascade stage must never build facts")

    monkeypatch.setattr(present, "build_lane_l_facts", never)
    exit_code, record, reached = _cascade_stage(
        tmp_path,
        registry,
        monkeypatch,
        remote,
        "--expected-facts-sha256",
        manifest["facts_sha256"],
    )

    assert exit_code == 1
    assert len(reached) == 1
    assert record is not None
    assert record.failure is not None
    assert "cascade reached" in record.failure.detail
    clone = reached[0]["args"][2]
    assert (clone / "README.md").read_text(encoding="utf-8").startswith("# Widget")
    consumed = json.loads(reached[0]["facts_path"].read_text(encoding="utf-8"))
    assert consumed["source_revision"] == manifest["source_revision"]


def test_the_cascade_stage_rejects_a_tampered_facts_file(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run_facts_stage(tmp_path, registry)
    facts = tmp_path / "handoff" / "facts.json"
    payload = json.loads(facts.read_text(encoding="utf-8"))
    payload["facts"][0]["value"] = payload["facts"][0]["value"] + " (edited)"
    facts.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    exit_code, record, reached = _cascade_stage(tmp_path, registry, monkeypatch, remote)

    assert exit_code == 1
    assert reached == []
    assert record is not None and record.failure is not None
    assert "FactsHandoffError" in record.failure.detail
    assert "does not match the manifest" in record.failure.detail


def test_the_cascade_stage_rejects_a_digest_that_differs_from_the_published_one(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run_facts_stage(tmp_path, registry)
    exit_code, record, reached = _cascade_stage(
        tmp_path, registry, monkeypatch, remote, "--expected-facts-sha256", "0" * 64
    )
    assert exit_code == 1 and reached == []
    assert record is not None and record.failure is not None
    assert "differs from the digest the facts job published" in record.failure.detail


def test_the_cascade_stage_rejects_a_missing_manifest(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run_facts_stage(tmp_path, registry)
    (tmp_path / "handoff" / MANIFEST_FILENAME).unlink()

    exit_code, record, reached = _cascade_stage(tmp_path, registry, monkeypatch, remote)

    assert exit_code == 1 and reached == []
    assert record is not None and record.failure is not None
    assert "facts manifest is missing" in record.failure.detail


def test_the_cascade_stage_rejects_a_manifest_revision_that_the_facts_do_not_carry(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run_facts_stage(tmp_path, registry)
    manifest_path = tmp_path / "handoff" / MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_revision"] = "0" * 40
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    exit_code, record, reached = _cascade_stage(tmp_path, registry, monkeypatch, remote)

    assert exit_code == 1 and reached == []
    assert record is not None and record.failure is not None
    assert "FactsHandoffError" in record.failure.detail
    assert "the manifest" in record.failure.detail


def test_the_cascade_stage_fails_closed_when_upstream_moved_since_the_facts_were_built(
    upstream: Path,
    registry: Path,
    tmp_path: Path,
    remote: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _run_facts_stage(tmp_path, registry)
    (upstream / "README.md").write_text(
        "# Widget\n\nChanged after the facts.\n", encoding="utf-8"
    )
    commit_all(upstream, "upstream moved")

    exit_code, record, reached = _cascade_stage(tmp_path, registry, monkeypatch, remote)

    assert exit_code == 1 and reached == []
    assert record is not None and record.failure is not None
    assert "moved from" in record.failure.detail


def test_the_combined_stage_is_refused_on_a_hosted_runner(
    upstream: Path, registry: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("combined mode must be refused before any work")

    monkeypatch.setattr(present, "pinned_read_only_clone", forbidden)
    monkeypatch.setattr(present, "build_lane_l_facts", forbidden)
    monkeypatch.setattr(present, "GitStateBackend", forbidden)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    explicit = _stage_args("combined", tmp_path, registry)
    implicit = [arg for arg in explicit if arg not in ("--stage", "combined")]
    for argv in (explicit, implicit):
        assert main(argv) == ConfigError.exit_code
    assert not (tmp_path / "work-combined").exists()


def test_a_facts_file_is_validated_as_data(tmp_path: Path) -> None:
    revision = "a" * 40

    def handoff_with(name: str, evidence_path: str) -> Path:
        directory = tmp_path / name
        fact = Fact("license:spdx", "license", "MIT", (Evidence(evidence_path),))
        write_handoff(FactsDocument(STAGE_REPO, revision, (fact,)), "python", directory)
        return directory

    load_handoff(
        handoff_with("ok", "LICENSE"), repository=STAGE_REPO, ecosystem="python"
    )
    hostile = ("../../etc/passwd", "/etc/passwd", "C:\\Windows\\win.ini", "a/../../b")
    for index, path in enumerate(hostile):
        with pytest.raises(FactsHandoffError, match="outside the repository"):
            load_handoff(
                handoff_with(f"hostile-{index}", path),
                repository=STAGE_REPO,
                ecosystem="python",
            )

    with pytest.raises(FactsHandoffError, match="other/repo"):
        load_handoff(
            handoff_with("named", "README.md"),
            repository="other/repo",
            ecosystem="python",
        )

    garbage = tmp_path / "garbage"
    garbage.mkdir()
    (garbage / "facts.json").write_text("[1, 2", encoding="utf-8")
    (garbage / MANIFEST_FILENAME).write_text(
        json.dumps(
            {
                "repository": STAGE_REPO,
                "ecosystem": "python",
                "source_revision": revision,
                "facts_sha256": hashlib.sha256(b"[1, 2").hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(FactsHandoffError, match="failed validation"):
        load_handoff(garbage, repository=STAGE_REPO, ecosystem="python")


# --- the workflow's trust boundary -------------------------------------------------------------


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _effective_permissions(
    workflow: dict[str, Any], job: dict[str, Any]
) -> dict[str, str]:
    return dict(job.get("permissions", workflow.get("permissions", {})))


def _uses(job: dict[str, Any]) -> list[str]:
    return [str(step["uses"]) for step in job["steps"] if "uses" in step]


def assert_facts_job_is_unprivileged(workflow: dict[str, Any]) -> None:
    job = workflow["jobs"]["facts"]
    rendered = json.dumps(job)
    assert "secrets." not in rendered, (
        "the facts job executes repository code: no secrets"
    )
    assert "github.token" not in rendered and "GITHUB_TOKEN" not in rendered
    assert (
        "REPOSITORY_PRESENTER_STATE_TOKEN" not in rendered and "GPT_OSS" not in rendered
    )
    assert not any("cache" in use for use in _uses(job)), (
        "no state cache in the facts job"
    )
    assert _effective_permissions(workflow, job) == {"contents": "read"}


def assert_present_job_runs_no_repository_code(workflow: dict[str, Any]) -> None:
    job = workflow["jobs"]["present"]
    assert job["needs"] in ("facts", ["facts"])
    for use in _uses(job):
        assert not any(name in use for name in TOOLCHAIN_ACTIONS), (
            f"toolchain step: {use}"
        )
    for step in job["steps"]:
        assert "--stage facts" not in str(step.get("run", ""))
        assert "--stage combined" not in str(step.get("run", ""))


def test_the_workflow_splits_the_untrusted_facts_job_from_the_credentialed_present_job() -> (
    None
):
    workflow = _load_workflow()
    assert set(workflow["jobs"]) == {"facts", "present"}
    assert_facts_job_is_unprivileged(workflow)
    assert_present_job_runs_no_repository_code(workflow)

    facts, presenting = workflow["jobs"]["facts"], workflow["jobs"]["present"]
    assert any("setup-dotnet" in use for use in _uses(facts))
    assert any("setup-java" in use for use in _uses(facts))
    assert "secrets.GPT_OSS_API_KEY" in json.dumps(presenting)
    assert _effective_permissions(workflow, presenting) == {"contents": "write"}
    assert "--stage facts" in json.dumps(facts)
    assert "--stage cascade" in json.dumps(presenting)
    assert any("download-artifact" in use for use in _uses(presenting))
    assert any("upload-artifact" in use for use in _uses(facts))


def test_adding_a_secret_to_the_facts_job_fails_the_structure_check() -> None:
    workflow = _load_workflow()
    workflow["jobs"]["facts"]["steps"][-1]["env"] = {
        "GPT_OSS_API_KEY": "${{ secrets.GPT_OSS_API_KEY }}"
    }
    with pytest.raises(AssertionError, match="no secrets"):
        assert_facts_job_is_unprivileged(workflow)


def test_widening_the_facts_job_token_fails_the_structure_check() -> None:
    workflow = _load_workflow()
    workflow["jobs"]["facts"]["permissions"] = {"contents": "write"}
    with pytest.raises(AssertionError):
        assert_facts_job_is_unprivileged(workflow)


def test_a_toolchain_step_in_the_present_job_fails_the_structure_check() -> None:
    workflow = _load_workflow()
    workflow["jobs"]["present"]["steps"].insert(
        1, {"uses": "actions/setup-dotnet@v4", "with": {"dotnet-version": "10.0.204"}}
    )
    with pytest.raises(AssertionError, match="toolchain step"):
        assert_present_job_runs_no_repository_code(workflow)
