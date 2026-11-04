"""create_issue labels/assignees (stage 7) and the guarded close/comment/reopen primitives
(stages 9 and 11). Fake transports only; httpx is patched to fail if ever reached."""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.github import client
from repo_presenter.github.client import (
    API_ROOT,
    UpstreamWriteForbiddenError,
    close_issue,
    comment_issue,
    create_issue,
    reopen_issue,
)
from repo_presenter.github.errors import RepositoryMetadataError

OWNER, NAME = "babar-raza", "repo-presenter"


class _Rec:
    def __init__(self, status: int = 200, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status, self.body = status, body if body is not None else {}

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status, self.body


def _created() -> _Rec:
    return _Rec(201, {"number": 1, "html_url": "https://x/issues/1"})


def test_create_issue_adds_labels_and_assignees_only_when_non_empty() -> None:
    write = _created()
    create_issue(OWNER, NAME, title="t", body="b", token="w", write=write,
                 labels=["repo-presenter", "defect:x"], assignees=["someone"])
    assert write.calls[0][2] == {
        "title": "t", "body": "b", "labels": ["repo-presenter", "defect:x"],
        "assignees": ["someone"],
    }


def test_create_issue_payload_unchanged_for_empty_or_absent_labels_and_assignees() -> None:
    for kwargs in ({}, {"labels": [], "assignees": []}, {"labels": None, "assignees": None}):
        write = _created()
        create_issue(OWNER, NAME, title="t", body="b", token="w", write=write, **kwargs)
        assert write.calls[0][2] == {"title": "t", "body": "b"}


# ----------------------------- close / comment / reopen -----------------------------


def test_comment_issue_posts_to_the_issue_comments_url() -> None:
    write = _Rec(201, {"id": 5})
    comment_issue(OWNER, NAME, 7, body="evidence", token="w", write=write)
    assert write.calls == [(f"{API_ROOT}/repos/{OWNER}/{NAME}/issues/7/comments", "w",
                            {"body": "evidence"})]


def test_close_issue_patches_state_and_reason() -> None:
    write = _Rec(200, {"state": "closed"})
    close_issue(OWNER, NAME, 7, reason="completed", token="w", write=write)
    assert write.calls == [(f"{API_ROOT}/repos/{OWNER}/{NAME}/issues/7", "w",
                            {"state": "closed", "state_reason": "completed"})]
    write = _Rec(200, {"state": "closed"})
    close_issue(OWNER, NAME, 7, reason="not planned", token="w", write=write)
    assert write.calls[0][2] == {"state": "closed", "state_reason": "not_planned"}


def test_reopen_issue_patches_state_open() -> None:
    write = _Rec(200, {"state": "open"})
    reopen_issue(OWNER, NAME, 7, token="w", write=write)
    assert write.calls == [(f"{API_ROOT}/repos/{OWNER}/{NAME}/issues/7", "w",
                            {"state": "open", "state_reason": "reopened"})]


def test_unknown_close_reason_is_refused_before_any_request() -> None:
    write = _Rec()
    with pytest.raises(ValueError):
        close_issue(OWNER, NAME, 7, reason="because", token="w", write=write)  # type: ignore[arg-type]
    assert write.calls == []


def test_missing_token_and_non_2xx_are_errors() -> None:
    for call in (
        lambda w: comment_issue(OWNER, NAME, 1, body="b", token="", write=w),
        lambda w: close_issue(OWNER, NAME, 1, reason="completed", token="", write=w),
        lambda w: reopen_issue(OWNER, NAME, 1, token="", write=w),
    ):
        w = _Rec()
        with pytest.raises(RepositoryMetadataError):
            call(w)
        assert w.calls == []
    with pytest.raises(RepositoryMetadataError):
        comment_issue(OWNER, NAME, 1, body="b", token="w", write=_Rec(422))
    with pytest.raises(RepositoryMetadataError):
        close_issue(OWNER, NAME, 1, reason="completed", token="w", write=_Rec(404))
    with pytest.raises(RepositoryMetadataError):
        reopen_issue(OWNER, NAME, 1, token="w", write=_Rec(-1, "boom"))


OTHER_REPOS = [("aspose-3d-foss", "Aspose.3D-FOSS-for-Python"), ("babar-raza", "other"),
               ("babar-raza", "repo-presenter-evil")]
CALLS = {
    "comment": lambda o, n, w: comment_issue(o, n, 1, body="b", token="w", write=w),
    "close": lambda o, n, w: close_issue(o, n, 1, reason="completed", token="w", write=w),
    "reopen": lambda o, n, w: reopen_issue(o, n, 1, token="w", write=w),
}


@pytest.mark.parametrize("which", sorted(CALLS))
@pytest.mark.parametrize("owner,name", OTHER_REPOS)
def test_any_other_repository_is_refused_before_any_request(which: str, owner: str, name: str) -> None:
    write = _Rec()
    with pytest.raises(UpstreamWriteForbiddenError):
        CALLS[which](owner, name, write)
    assert write.calls == []


@pytest.mark.parametrize("which", sorted(CALLS))
@pytest.mark.parametrize("owner,name", OTHER_REPOS)
def test_default_writers_refuse_other_repositories_before_httpx(
    which: str, owner: str, name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("an HTTP request was attempted for a forbidden target")

    for verb in ("post", "patch", "put"):
        monkeypatch.setattr(client.httpx, verb, boom)
    with pytest.raises(UpstreamWriteForbiddenError):
        # exercise the real default writers (no `write=` injected)
        if which == "comment":
            comment_issue(owner, name, 1, body="b", token="w")
        elif which == "close":
            close_issue(owner, name, 1, reason="completed", token="w")
        else:
            reopen_issue(owner, name, 1, token="w")
