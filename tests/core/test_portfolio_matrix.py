"""The derived portfolio matrix (core/portfolio_matrix.py): counts come from evidence, never typed.

Grounded in the 2026-10-31 independent status review, which found the hand-entered state.yaml
counters (lane_r_accepted 34, lane_l_accepted 36) contradicted by the durable records (Lane R good
4 of 36, Lane L good 4 of 36, both lanes 1) and by candidates/ (one committed bundle).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from support import init_git_repository

from repo_presenter.core.portfolio_matrix import (
    NO_RECORD,
    PIPELINE_GOOD_STATES,
    backend_reader,
    build_matrix,
    summarize,
)
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.state.schema import RepositoryRecord

A = SimpleNamespace(repository="aspose-a-foss/Aspose.A-FOSS-for-.NET", ecosystem="net", mode="full")
B = SimpleNamespace(repository="aspose-b-foss/Aspose.B-FOSS-for-Java", ecosystem="java", mode="dry_run")
C = SimpleNamespace(repository="aspose-c-foss/Aspose.C-FOSS-for-Python", ecosystem="python", mode="dry_run")


def _reader(table: dict[tuple[str, str], str]):
    return lambda repository, lane: table.get((repository, lane))


def test_a_repository_with_no_record_is_reported_as_such_not_as_missing(tmp_path: Path) -> None:
    rows = build_matrix([A], _reader({}), tmp_path)
    assert rows[0].record_r == NO_RECORD and rows[0].record_l == NO_RECORD


def test_counts_are_derived_per_lane_and_both_lanes_is_the_intersection(tmp_path: Path) -> None:
    table = {
        (A.repository, "R"): "READY_FOR_PROPOSAL",
        (A.repository, "L"): "ACCEPTED",
        (B.repository, "R"): "ACCEPTED",
        (B.repository, "L"): "FAILED_INTERNAL",
        (C.repository, "R"): "FAILED_INTERNAL",
    }
    summary = summarize(build_matrix([A, B, C], _reader(table), tmp_path))
    assert summary["registry_total"] == 3
    assert summary["write_eligible_mode_full"] == 1
    assert summary["lane_r_attempted"] == 3 and summary["lane_l_attempted"] == 2
    assert summary["lane_r_pipeline_good"] == 2 and summary["lane_l_pipeline_good"] == 1
    assert summary["both_lanes_pipeline_good"] == [A.repository]
    assert summary["lane_r_record_states"] == {
        "ACCEPTED": 1,
        "FAILED_INTERNAL": 1,
        "READY_FOR_PROPOSAL": 1,
    }


def test_a_pipeline_good_record_is_not_a_committed_bundle(tmp_path: Path) -> None:
    """The review's central finding: a good durable record says nothing about whether a bundle
    exists in git. Both facts are reported separately."""
    table = {(A.repository, "R"): "READY_FOR_PROPOSAL"}
    summary = summarize(build_matrix([A], _reader(table), tmp_path))
    assert summary["lane_r_pipeline_good"] == 1
    assert summary["committed_bundles_lane_r"] == 0 and summary["committed_bundles_lane_l"] == 0


def test_owner_review_is_never_reported_as_a_number(tmp_path: Path) -> None:
    summary = summarize(build_matrix([A], _reader({}), tmp_path))
    assert isinstance(summary["owner_reviewed"], str)
    assert "not tracked" in summary["owner_reviewed"]


def test_only_accepted_and_ready_for_proposal_count_as_pipeline_good() -> None:
    assert PIPELINE_GOOD_STATES == {"ACCEPTED", "READY_FOR_PROPOSAL"}


def test_the_real_git_backend_reader_returns_each_lanes_own_state(tmp_path: Path) -> None:
    remote = init_git_repository(tmp_path / "remote")
    base = RepositoryRecord(repository=A.repository, provider_repository_id=1)
    with (
        GitStateBackend(remote=str(remote), lane="R") as lane_r,
        GitStateBackend(remote=str(remote), lane="L") as lane_l,
    ):
        assert lane_r.save(A.repository, base.model_copy(update={"state": "ACCEPTED"}), None)
        assert lane_l.save(A.repository, base.model_copy(update={"state": "OBSERVED"}), None)
    with backend_reader(str(remote)) as read_state:
        rows = build_matrix([A, B], read_state, tmp_path)
    by_repo = {row.repository: row for row in rows}
    assert by_repo[A.repository].record_r == "ACCEPTED"
    assert by_repo[A.repository].record_l == "OBSERVED"
    assert by_repo[B.repository].record_r == NO_RECORD


def test_stored_bundle_refs_mark_each_lane_separately(tmp_path: Path) -> None:
    """A good record says nothing about whether a bundle survives; the durable refs do."""
    from repo_presenter.core.state.bundle_store import bundle_ref

    refs = {bundle_ref(A.repository, "R"), bundle_ref(B.repository, "L")}
    rows = build_matrix([A, B, C], _reader({}), tmp_path, refs)
    by_repo = {row.repository: row for row in rows}
    assert (by_repo[A.repository].stored_r, by_repo[A.repository].stored_l) == (True, False)
    assert (by_repo[B.repository].stored_r, by_repo[B.repository].stored_l) == (False, True)
    assert (by_repo[C.repository].stored_r, by_repo[C.repository].stored_l) == (False, False)
    summary = summarize(rows)
    assert summary["durable_bundles_lane_r"] == 1 and summary["durable_bundles_lane_l"] == 1


def test_stored_bundle_refs_lists_the_remote_refs(tmp_path: Path) -> None:
    from repo_presenter.core.portfolio_matrix import stored_bundle_refs
    from repo_presenter.core.state.bundle_store import bundle_ref

    remote = init_git_repository(tmp_path / "remote")
    head = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()
    ref = bundle_ref(A.repository, "L")
    assert run_git(["update-ref", ref, head], cwd=remote).returncode == 0
    assert stored_bundle_refs(str(remote)) == frozenset({ref})
