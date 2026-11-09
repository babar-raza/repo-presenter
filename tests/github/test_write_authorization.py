"""Owner ruling R3 (docs/CONSOLIDATED_GOALS_2026-11-06.md): the one effect-specific, default-deny
write-authorization boundary in ``repo_presenter.github.client`` (``authorize_write`` /
``authorize_request``), the ``first_pr_as_draft`` draft flag, and proof that the allowlist is a
necessary condition only -- a listed repository is still refused by the publish path's reviewer-
calibration gate while ``data/reviewer_calibration.json`` is NOT_PASSED.

Fake transports only: httpx is patched to fail the test if a refused write ever reaches it."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from support import make_permit

from repo_presenter.authorization.refusals import Refusal
from repo_presenter.github import client
from repo_presenter.github.client import (
    API_ROOT,
    CONTROL_REPOSITORY,
    UpstreamWriteForbiddenError,
    authorize_request,
    authorize_write,
    close_issue,
    comment_issue,
    create_pull_request,
    default_patch,
    default_post,
    default_put,
    reopen_issue,
)
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

LISTED = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
LISTED_OWNER, LISTED_NAME = LISTED.split("/")
UNLISTED = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
HEAD = "repository-presenter/readme-update"


@pytest.fixture(autouse=True)
def _no_http(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    """Every real write verb records its call; a test asserts the list stays empty on refusal."""
    seen: list[tuple[str, str, Any]] = []

    class _Response:
        status_code = 201

        def json(self) -> Any:
            return {"number": 1, "html_url": "https://github.com/x/y/pull/1"}

    def recorder(verb: str) -> Any:
        def fake(url: str, **kwargs: Any) -> _Response:
            seen.append((verb, url, kwargs.get("json")))
            return _Response()

        return fake

    for verb in ("post", "patch", "put"):
        monkeypatch.setattr(client.httpx, verb, recorder(verb))
    return seen


def _allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: Any) -> None:
    path = tmp_path / "upstream_write_allowlist.json"
    if content is not None:
        path.write_text(content if isinstance(content, str) else json.dumps(content), "utf-8")
    monkeypatch.setattr(client, "UPSTREAM_WRITE_ALLOWLIST", path)


def _entry(repository: str = LISTED, **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "repository": repository,
        "effects": ["pull_request"],
        "first_pr_as_draft": True,
    }
    entry.update(overrides)
    return entry


# ------------------------------------------------------------------ the committed allowlist


def test_the_committed_allowlist_grants_only_pull_requests_on_its_nine_repositories() -> None:
    data = json.loads(client.UPSTREAM_WRITE_ALLOWLIST.read_text("utf-8"))
    repositories = [entry["repository"] for entry in data["repositories"]]
    assert len(repositories) == 9 and LISTED in repositories  # R22: 3 pilots + 6 inherited full
    for repository in repositories:
        grant = authorize_write(repository, "pull_request")
        assert grant.upstream is True and grant.draft_required is True
        for effect in ("issue", "issue_comment", "internal"):
            with pytest.raises(UpstreamWriteForbiddenError):
                authorize_write(repository, effect)


# ------------------------------------------------------------------ control repository


@pytest.mark.parametrize("effect", ["pull_request", "issue", "issue_comment", "internal"])
def test_the_control_repository_is_allowed_every_known_effect(effect: str) -> None:
    grant = authorize_write("Babar-Raza/Repo-Presenter", effect)
    assert grant.upstream is False and grant.draft_required is False


def test_control_repository_writes_reach_the_transport_unchanged(
    _no_http: list[tuple[str, str, Any]],
) -> None:
    base = f"{API_ROOT}/repos/{CONTROL_REPOSITORY}"
    assert default_post(f"{base}/issues", "t", {"title": "x"})[0] == 201
    assert default_patch(f"{base}/pulls/3", "t", {"state": "closed"})[0] == 201
    assert default_put(f"{base}/contents/candidates/x", "t", {"branch": "main"})[0] == 201
    assert default_post(f"{base}/labels", "t", {"name": "n"})[0] == 201  # internal effect
    assert len(_no_http) == 4


def test_control_repository_pull_request_payload_has_no_draft_key() -> None:
    calls: list[dict[str, Any]] = []

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        calls.append(payload)
        return 201, {"number": 2, "html_url": "u"}

    owner, name = CONTROL_REPOSITORY.split("/")
    create_pull_request(owner, name, title="t", body="b", head="h", base="main", token="w",
                        write=write)
    assert "draft" not in calls[0]


# ------------------------------------------------------------------ listed upstream repository


def test_listed_repository_and_listed_effect_is_allowed_through_the_real_writer(
    _no_http: list[tuple[str, str, Any]],
) -> None:
    created = create_pull_request(
        LISTED_OWNER, LISTED_NAME, title="t", body="b", head=HEAD, base="main", token="w"
    )
    assert created.number == 1
    assert _no_http == [
        ("post", f"{API_ROOT}/repos/{LISTED}/pulls",
         {"title": "t", "body": "b", "head": HEAD, "base": "main", "draft": True}),
    ]


def test_draft_flag_is_sent_to_an_injected_writer_too() -> None:
    calls: list[dict[str, Any]] = []

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        calls.append(payload)
        return 201, {"number": 2, "html_url": "u"}

    create_pull_request(LISTED_OWNER, LISTED_NAME, title="t", body="b", head=HEAD, base="main",
                        token="w", write=write)
    assert calls[0]["draft"] is True


def test_no_draft_flag_when_the_entry_does_not_require_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_http: list[tuple[str, str, Any]]
) -> None:
    _allowlist(tmp_path, monkeypatch, {"schema_version": 1,
                                       "repositories": [_entry(first_pr_as_draft=False)]})
    create_pull_request(LISTED_OWNER, LISTED_NAME, title="t", body="b", head=HEAD, base="main",
                        token="w")
    assert "draft" not in _no_http[0][2]


def test_a_non_draft_pull_request_on_a_draft_repository_is_refused_at_the_transport(
    _no_http: list[tuple[str, str, Any]],
) -> None:
    with pytest.raises(UpstreamWriteForbiddenError, match="draft"):
        default_post(f"{API_ROOT}/repos/{LISTED}/pulls", "t", {"head": HEAD, "base": "main"})
    assert _no_http == []


@pytest.mark.parametrize(
    ("writer", "path", "payload"),
    [
        (default_post, "issues", {"title": "t", "body": "b"}),  # issue
        (default_patch, "issues/4", {"state": "closed"}),  # issue
        (default_post, "issues/4/comments", {"body": "b"}),  # issue_comment
        (default_post, "labels", {"name": "x"}),  # internal - never upstream
        (default_post, "git/refs", {"ref": "refs/heads/main", "sha": "s"}),  # outside prefix
        (default_put, "contents/README.md", {"branch": "main", "content": "x"}),  # default br.
        (default_put, "contents/README.md", {"content": "x"}),  # no branch named
        (default_patch, "pulls/9", {"state": "closed"}),  # beyond title/body
        (default_patch, "pulls/9", {"title": "t", "draft": False}),
        (default_post, "pulls", {"head": "feature", "base": "main", "draft": True}),
    ],
)
def test_listed_repository_refuses_unlisted_effects_and_shapes_before_any_request(
    writer: Any, path: str, payload: dict[str, Any], _no_http: list[tuple[str, str, Any]]
) -> None:
    with pytest.raises(UpstreamWriteForbiddenError):
        writer(f"{API_ROOT}/repos/{LISTED}/{path}", "t", payload)
    assert _no_http == []


def test_listed_repository_allows_its_presenter_branch_writes(
    _no_http: list[tuple[str, str, Any]],
) -> None:
    base = f"{API_ROOT}/repos/{LISTED}"
    default_post(f"{base}/git/refs", "t", {"ref": f"refs/heads/{HEAD}", "sha": "s"})
    default_put(f"{base}/contents/README.md", "t", {"branch": HEAD, "content": "x"})
    default_patch(f"{base}/pulls/9", "t", {"title": "t", "body": "b"})
    assert len(_no_http) == 3


@pytest.mark.parametrize("effect", ["issue", "issue_comment"])
def test_pull_request_permission_never_implies_issue_permission(effect: str) -> None:
    with pytest.raises(UpstreamWriteForbiddenError, match="not"):
        authorize_write(LISTED, effect)


def test_issue_primitives_refuse_a_pull_request_only_repository_before_the_injected_writer() -> None:
    calls: list[str] = []

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        calls.append(url)
        return 200, {}

    for call in (
        lambda: comment_issue(LISTED_OWNER, LISTED_NAME, 1, body="b", token="w", write=write),
        lambda: close_issue(LISTED_OWNER, LISTED_NAME, 1, reason="completed", token="w",
                            write=write),
        lambda: reopen_issue(LISTED_OWNER, LISTED_NAME, 1, token="w", write=write),
    ):
        with pytest.raises(UpstreamWriteForbiddenError):
            call()
    assert calls == []


def test_issue_and_comment_permissions_are_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allowlist(tmp_path, monkeypatch, {"schema_version": 1,
                                       "repositories": [_entry(effects=["issue_comment"])]})
    assert authorize_write(LISTED, "issue_comment").upstream is True
    for effect in ("issue", "pull_request"):
        with pytest.raises(UpstreamWriteForbiddenError):
            authorize_write(LISTED, effect)


# ------------------------------------------------------------------ refusals


def test_an_unlisted_repository_is_refused(_no_http: list[tuple[str, str, Any]]) -> None:
    with pytest.raises(UpstreamWriteForbiddenError, match="read-only"):
        authorize_write(UNLISTED, "pull_request")
    with pytest.raises(UpstreamWriteForbiddenError):
        default_post(f"{API_ROOT}/repos/{UNLISTED}/pulls", "t",
                     {"head": HEAD, "base": "main", "draft": True})
    assert _no_http == []


@pytest.mark.parametrize("effect", ["", "push", "pull_requests", "PULL_REQUEST", "merge"])
@pytest.mark.parametrize("repository", [CONTROL_REPOSITORY, LISTED])
def test_an_unknown_effect_is_refused_for_every_repository(repository: str, effect: str) -> None:
    with pytest.raises(UpstreamWriteForbiddenError, match="unknown effect"):
        authorize_write(repository, effect)


@pytest.mark.parametrize(
    "content",
    [
        None,  # missing
        "",
        "{not json",
        json.dumps([]),
        {"repositories": [_entry()]},  # no schema_version
        {"schema_version": 2, "repositories": [_entry()]},
        {"schema_version": 1},
        {"schema_version": 1, "repositories": {}},
        {"schema_version": 1, "repositories": ["x"]},
        {"schema_version": 1, "repositories": [_entry(repository="no-slash")]},
        {"schema_version": 1, "repositories": [_entry(effects=[])]},
        {"schema_version": 1, "repositories": [_entry(effects="pull_request")]},
        {"schema_version": 1, "repositories": [_entry(effects=["pull_request", "merge"])]},
        {"schema_version": 1, "repositories": [_entry(effects=["internal"])]},
        {"schema_version": 1, "repositories": [_entry(first_pr_as_draft="yes")]},
        {"schema_version": 1, "repositories": [_entry(), _entry(repository=LISTED.upper())]},
        {"schema_version": 1, "repositories": [_entry(), {"repository": UNLISTED}]},
    ],
)
def test_a_missing_or_malformed_allowlist_refuses_every_upstream_write(
    content: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _no_http: list[tuple[str, str, Any]],
) -> None:
    _allowlist(tmp_path, monkeypatch, content)
    with pytest.raises(UpstreamWriteForbiddenError, match="allowlist"):
        authorize_write(LISTED, "pull_request")
    with pytest.raises(UpstreamWriteForbiddenError):
        create_pull_request(LISTED_OWNER, LISTED_NAME, title="t", body="b", head=HEAD,
                            base="main", token="w")
    assert _no_http == []
    # the control repository is unaffected by the upstream file
    assert authorize_write(CONTROL_REPOSITORY, "issue").upstream is False


def test_an_unreadable_allowlist_makes_a_pull_request_a_draft_fail_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allowlist(tmp_path, monkeypatch, "{not json")
    assert client.pull_request_draft_required(LISTED_OWNER, LISTED_NAME) is True
    assert client.pull_request_draft_required(*CONTROL_REPOSITORY.split("/")) is False


@pytest.mark.parametrize(
    "url",
    [
        f"https://evil.example/repos/{LISTED}/pulls",
        f"{API_ROOT}/repos/{LISTED_OWNER}/{LISTED_NAME}%2F/pulls",
        f"{API_ROOT}/repos/{LISTED}/../x/pulls",
        f"{API_ROOT}/orgs/{LISTED_OWNER}/repos",
    ],
)
def test_malformed_urls_are_refused(url: str) -> None:
    with pytest.raises(UpstreamWriteForbiddenError):
        authorize_request("POST", url, {"head": HEAD, "draft": True})


def test_no_environment_override_exists() -> None:
    for function in (
        client.authorize_write,
        client.authorize_request,
        client._load_upstream_allowlist,
        client.classify_write,
    ):
        source = inspect.getsource(function)
        assert "environ" not in source and "getenv" not in source


# ------------------------------------------------------------------ composite publish gate


def test_a_listed_repository_is_still_refused_while_acceptance_is_not_certified(
    monkeypatch: pytest.MonkeyPatch, _no_http: list[tuple[str, str, Any]]
) -> None:
    """The allowlist is a necessary condition only. Gate 3b (2026-11-07, TC-013) now reads
    repo_presenter.acceptance.record.classify instead of the old reviewer calibration status;
    with neither data/acceptance_calibration.json nor data/acceptance_responsibility.json
    committed yet, classify() fails closed and propose_candidate refuses an allowlisted
    repository with ACCEPTANCE_NOT_CERTIFIED, using the real client primitives, before any
    request. Renamed from ...reviewer_calibration_is_not_passed (that file,
    data/reviewer_calibration.json, is now frozen history and this test no longer touches it)."""
    from repo_presenter.propose import effect

    assert authorize_write(LISTED, "pull_request").upstream is True  # the client would allow it

    def must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a gate after calibration was reached")

    review = ReviewVerdict.folded(
        (),
        model_verdict="ACCEPT",
        prompt_version="17",
        model_served="qwen3-next",
        request_sha256="a" * 64,
        reply_sha256="b" * 64,
        calibration_status="PASSED",
    )
    result = effect.propose_candidate(
        repository=LISTED,
        readme_text="# README\n",
        source_revision="0" * 40,
        base_branch="main",
        token="ghs_write",
        environment={effect.AUTHORIZATION_VARIABLE: "1"},
        review=review,
        permit=make_permit(LISTED),
        load_authorization=must_not_run,
        recheck_source=must_not_run,
        verify_token=must_not_run,
        pr_title="t",
        pr_body="b",
    )
    assert result.effected is False
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED
    assert _no_http == []
