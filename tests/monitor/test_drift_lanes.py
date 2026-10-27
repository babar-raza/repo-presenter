"""The drift monitor observes each lane's CURRENT candidate on its own (plans/PLAN_lane_l_hosted.md
L7): a repository can be CURRENT in one lane and have no bundle in the other, and one lane's
bundle is never read as the other's."""

from __future__ import annotations

from pathlib import Path

from support import FakeDefaultBranchReader, monitor_registry_entry

from repo_presenter.core.candidates import LANE_L, LANE_R
from repo_presenter.github.read_client import TreeRead
from repo_presenter.monitor.drift import observe_drift
from tests.core.test_candidates_lanes import seal
from tests.monitor.test_drift import TOKEN, entries_of

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
SLUG = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
REVISION = "1" * 40
OTHER = "2" * 40


def _empty_tree(
    repository: str, revision: str, *, token: str | None = None
) -> TreeRead:
    return TreeRead(repository, revision)


def observe(root: Path, lane: str, head: str) -> tuple[str, str | None]:
    (row,) = observe_drift(
        root,
        entries_of(monitor_registry_entry(REPOSITORY)),
        token=TOKEN,
        read_head=FakeDefaultBranchReader({REPOSITORY: head}),
        read_tree=_empty_tree,
        lane=lane,
    )
    return row.status, row.bundle_revision


def test_a_lane_l_bundle_is_observed_in_its_own_lane_and_lane_r_reports_no_bundle(
    tmp_path: Path,
) -> None:
    seal(tmp_path, LANE_L, revision=REVISION, slug=SLUG, repository=REPOSITORY)
    assert observe(tmp_path, LANE_L, REVISION) == ("CURRENT", REVISION)
    status, bundle_revision = observe(tmp_path, LANE_R, REVISION)
    assert (status, bundle_revision) == ("NO_BUNDLE", None)  # Lane R has sealed nothing


def test_each_lane_is_compared_with_its_own_sealed_revision(tmp_path: Path) -> None:
    seal(tmp_path, LANE_R, revision=REVISION, slug=SLUG, repository=REPOSITORY)
    seal(tmp_path, LANE_L, revision=OTHER, slug=SLUG, repository=REPOSITORY)
    assert observe(tmp_path, LANE_R, REVISION) == ("CURRENT", REVISION)
    assert observe(tmp_path, LANE_L, REVISION)[1] == OTHER
    assert (
        observe(tmp_path, LANE_L, REVISION)[0] != "CURRENT"
    )  # head moved past Lane L's revision
