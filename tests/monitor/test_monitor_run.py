"""WP-3 (owner ruling R50): the hosted portfolio monitor. Relevant / irrelevant / unreadable controls
through ``observe_cells``, the report document and its state-ref round trip, and the CLI's
read-only contract. Every GitHub read is a fake; no network, no provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from support import (
    FakeDefaultBranchReader,
    init_git_repository,
    monitor_registry_entry,
    write_bundle,
)

from repo_presenter.core.registry.models import Registry
from repo_presenter.github.read_client import TreeRead
from repo_presenter.monitor import run as monitor_run
from repo_presenter.monitor.run import (
    drifted_cells,
    observe_cells,
    read_report,
    report_document,
    summary_markdown,
    write_report,
)
from tests.monitor.test_drift_content import (
    BUNDLED,
    EXAMPLE,
    LICENSE,
    NEWER,
    PYTHON,
    PYTHON_DIR,
    RECORDED,
    UNRELATED,
    FakeTreeReader,
)

TOKEN = "ghs_fixture_read_token_value_0123456789"
OTHER = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"
OTHER_DIR = "aspose-cells-foss__Aspose.Cells-FOSS-for-Python"


def entries(*names: str):
    registry = Registry.model_validate(
        {"schema_version": 1, "entries": [monitor_registry_entry(n, repository_id=i + 1) for i, n in enumerate(names)]}
    )
    return list(registry.entries)


def observe(root: Path, heads: dict, tree, *names: str, lanes=("R",)):
    return observe_cells(
        entries(*names), token=TOKEN, export=None, bundle_root=root,
        read_head=FakeDefaultBranchReader(heads), read_tree=tree, lanes=lanes,
    )


def by_repo(cells):
    return {c["repository"]: c for c in cells}


def test_relevant_irrelevant_unreadable_and_unbundled_cells_are_told_apart(tmp_path: Path) -> None:
    for slug in (PYTHON_DIR, OTHER_DIR):
        write_bundle(tmp_path, slug, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    # a third repository with no bundle at all
    third = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Python"
    heads = {PYTHON: NEWER, OTHER: NEWER, third: NEWER}

    relevant = observe(tmp_path, heads, FakeTreeReader({**RECORDED, LICENSE: "dd" * 20}), PYTHON)
    assert (relevant[0]["class"], relevant[0]["status"]) == ("relevant", "DRIFTED")

    irrelevant = observe(tmp_path, heads, FakeTreeReader({**RECORDED, UNRELATED: "ee" * 20}), OTHER)
    assert (irrelevant[0]["class"], irrelevant[0]["status"]) == ("irrelevant", "CURRENT")

    unreadable_tree = observe(tmp_path, heads, FakeTreeReader(TreeRead(PYTHON, NEWER, error="boom")), PYTHON)
    assert (unreadable_tree[0]["class"], unreadable_tree[0]["status"]) == ("unreadable", "UNKNOWN")

    unreadable_head = observe(
        tmp_path, {PYTHON: RuntimeError(f"down {TOKEN}")}, FakeTreeReader(RECORDED), PYTHON
    )
    assert unreadable_head[0]["class"] == "unreadable"
    assert TOKEN not in json.dumps(unreadable_head)

    none = observe(tmp_path, heads, FakeTreeReader(RECORDED), third)
    assert none[0]["class"] == "no_bundle"


def test_one_unreadable_repository_never_stops_the_others(tmp_path: Path) -> None:
    write_bundle(tmp_path, OTHER_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    cells = observe(
        tmp_path, {PYTHON: RuntimeError("503"), OTHER: BUNDLED}, FakeTreeReader(dict(RECORDED)), PYTHON, OTHER
    )
    classes = {c["repository"]: c["class"] for c in cells}
    assert classes == {PYTHON: "unreadable", OTHER: "unchanged"}


def test_the_report_names_drifted_cells_and_the_cohort_reader_returns_exactly_them(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    cells = observe(tmp_path, {PYTHON: NEWER}, FakeTreeReader({**RECORDED, EXAMPLE: "ff" * 20}), PYTHON)
    document = report_document(cells, observed_at="2026-11-22T06:00:00+00:00", run_id="1")
    assert document["summary"]["relevant"] == 1
    drifted = drifted_cells(document)
    assert set(drifted) == {(PYTHON, "R")}
    assert drifted[(PYTHON, "R")]["bundle_revision"] == BUNDLED
    assert EXAMPLE in (drifted[(PYTHON, "R")]["detail"] or "")
    assert "Drifted cell" in summary_markdown(document)
    # a missing, foreign or malformed document names nothing: the selector behaves as before
    assert drifted_cells(None) == {} and drifted_cells({"kind": "x"}) == {} and drifted_cells({}) == {}


def test_a_30_day_old_bundle_is_listed_as_due_the_registry_recheck(tmp_path: Path) -> None:
    write_bundle(
        tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED,
        manifest_extra={"sealed_at": "2026-01-01T00:00:00+00:00"},
    )
    cells = observe(tmp_path, {PYTHON: BUNDLED}, FakeTreeReader(dict(RECORDED)), PYTHON)
    document = report_document(cells, observed_at="2026-11-22T06:00:00+00:00")
    assert [row["repository"] for row in document["freshness_due"]] == [PYTHON]


def test_the_report_round_trips_through_the_state_ref(tmp_path: Path) -> None:
    remote = init_git_repository(tmp_path / "remote")
    document = report_document([], observed_at="2026-11-22T06:00:00+00:00", run_id="7")
    assert read_report(remote=str(remote), token=None)[0] is None
    write_report(document, remote=str(remote), token=None)
    stored, note = read_report(remote=str(remote), token=None)
    assert stored == document and note == ""
    assert monitor_run.MONITOR_REF.startswith("refs/repository-presenter-state/")


def test_the_cli_writes_only_the_state_ref_and_never_an_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_bundle(tmp_path / "root", PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "entries": [monitor_registry_entry(PYTHON)]}), encoding="utf-8"
    )
    remote = init_git_repository(tmp_path / "remote")
    monkeypatch.setattr(monitor_run, "fetch_default_branch_sha", FakeDefaultBranchReader({PYTHON: BUNDLED}))
    from repo_presenter.monitor import drift

    monkeypatch.setattr(drift, "fetch_tree", FakeTreeReader(dict(RECORDED)))
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    out = tmp_path / "report.json"
    summary = tmp_path / "summary.md"
    code = monitor_run.main([
        "--registry", str(registry), "--remote", str(remote), "--bundle-root", str(tmp_path / "root"),
        "--no-discovery", "--no-freshness", "--out", str(out), "--summary", str(summary),
    ])
    assert code == 0
    assert json.loads(out.read_text())["summary"]["unchanged"] == 1
    assert "Portfolio monitor" in summary.read_text()
    assert read_report(remote=str(remote), token=None)[0]["kind"] == "monitor_report"
