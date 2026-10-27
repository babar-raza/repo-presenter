"""One durable transaction record per repository per lane (plans/PLAN_lane_l_hosted.md L9), against
the real git-ref backend on a disposable local remote. Lane L's record lives in its own ref, so a
Lane L transaction can neither read nor overwrite Lane R's, and a failure in one lane leaves the
other lane's record exactly as it was."""

from __future__ import annotations

from pathlib import Path

import pytest
from support import init_git_repository

from repo_presenter.core.errors import StateBackendError
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.state.git_backend import (
    LANE_L_REF_SUFFIX,
    STATE_REF_PREFIX,
    GitStateBackend,
    _ref_key,
)
from repo_presenter.core.state.schema import RepositoryRecord

REPO = "aspose-3d-foss/example"
PROVIDER_ID = 42


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "remote")


def _refs(remote: Path) -> list[str]:
    listed = run_git(
        ["for-each-ref", "--format=%(refname)", STATE_REF_PREFIX], cwd=remote
    )
    assert listed.returncode == 0, listed.stderr
    return sorted(listed.stdout.split())


def test_the_lane_r_ref_key_is_exactly_what_it_always_was() -> None:
    assert _ref_key(REPO) == "aspose-3d-foss__example"
    assert _ref_key(REPO, "R") == "aspose-3d-foss__example"
    assert _ref_key(REPO, "L") == "aspose-3d-foss__example" + LANE_L_REF_SUFFIX
    with pytest.raises(StateBackendError, match="unknown lane"):
        _ref_key(REPO, "X")


def test_a_repository_name_can_never_own_the_lane_l_key() -> None:
    """``@`` is not a legal character of a GitHub owner or repository name, so no repository maps
    to another repository's Lane L ref (``__`` is legal in a name, which is why a ``__`` suffix
    would have collided)."""
    colliding_name = "aspose-3d-foss/example__lane-l"
    assert _ref_key(colliding_name, "R") != _ref_key(REPO, "L")


def test_the_ref_name_the_lane_l_key_makes_is_a_valid_git_ref(remote: Path) -> None:
    ref = f"{STATE_REF_PREFIX}/{_ref_key(REPO, 'L')}"
    checked = run_git(["check-ref-format", ref], cwd=remote)
    assert checked.returncode == 0, checked.stderr


def test_each_lane_keeps_its_own_record_in_its_own_ref(remote: Path) -> None:
    with (
        GitStateBackend(remote=str(remote), lane="R") as lane_r,
        GitStateBackend(remote=str(remote), lane="L") as lane_l,
    ):
        record = RepositoryRecord(repository=REPO, provider_repository_id=PROVIDER_ID)
        assert lane_r.save(
            REPO, record.model_copy(update={"state": "ACCEPTED"}), None
        ).outcome == ("saved")
        assert (
            lane_l.load(REPO) is None
        )  # Lane L has nothing: it does not see Lane R's record
        assert (
            lane_l.save(
                REPO, record.model_copy(update={"state": "EXTRACTING"}), None
            ).outcome
            == "saved"
        )

        in_r, in_l = lane_r.load(REPO), lane_l.load(REPO)
        assert in_r is not None and (in_r.lane, in_r.state, in_r.state_version) == (
            "R",
            "ACCEPTED",
            1,
        )
        assert in_l is not None and (in_l.lane, in_l.state, in_l.state_version) == (
            "L",
            "EXTRACTING",
            1,
        )
    assert _refs(remote) == [
        f"{STATE_REF_PREFIX}/{_ref_key(REPO, 'R')}",
        f"{STATE_REF_PREFIX}/{_ref_key(REPO, 'L')}",
    ]


def test_saving_through_the_lane_l_backend_stamps_lane_l_whatever_the_caller_built(
    remote: Path,
) -> None:
    """The cas helpers build a default record with the default lane; the backend, not the caller,
    decides which lane's ref it lands in, so a Lane R-shaped record can never reach Lane R's ref
    through Lane L's backend."""
    with GitStateBackend(remote=str(remote), lane="L") as lane_l:
        default = RepositoryRecord(repository=REPO, provider_repository_id=PROVIDER_ID)
        assert default.lane == "R"
        saved = lane_l.save(REPO, default, None)
        assert saved.record is not None and saved.record.lane == "L"
    with GitStateBackend(remote=str(remote), lane="R") as lane_r:
        assert lane_r.load(REPO) is None  # nothing landed in Lane R's ref


def test_a_record_of_the_other_lane_in_a_lane_s_ref_is_refused(
    remote: Path, tmp_path: Path
) -> None:
    """Fail closed: a Lane R record pushed into Lane L's ref (a hand edit, a bug) is not read."""
    with GitStateBackend(remote=str(remote), lane="R") as lane_r:
        saved = lane_r.save(
            REPO,
            RepositoryRecord(repository=REPO, provider_repository_id=PROVIDER_ID),
            None,
        )
        assert saved.outcome == "saved"
    source = f"{STATE_REF_PREFIX}/{_ref_key(REPO, 'R')}"
    target = f"{STATE_REF_PREFIX}/{_ref_key(REPO, 'L')}"
    moved = run_git(["update-ref", target, source], cwd=remote)
    assert moved.returncode == 0, moved.stderr
    with (
        GitStateBackend(remote=str(remote), lane="L") as lane_l,
        pytest.raises(StateBackendError, match="another lane's transaction"),
    ):
        lane_l.load(REPO)


def test_a_backend_for_an_unknown_lane_is_refused_before_touching_the_remote(
    remote: Path,
) -> None:
    with pytest.raises(StateBackendError, match="unknown lane"):
        GitStateBackend(remote=str(remote), lane="X")
    assert _refs(remote) == []


def test_a_record_written_before_the_lane_existed_loads_as_lane_r(remote: Path) -> None:
    """The old record shape has no ``lane`` key; it must read as Lane R, unchanged."""
    payload = RepositoryRecord(repository=REPO, provider_repository_id=PROVIDER_ID)
    raw = payload.model_dump_json(exclude={"lane"})
    assert '"lane"' not in raw
    loaded = RepositoryRecord.model_validate_json(raw)
    assert loaded.lane == "R"
