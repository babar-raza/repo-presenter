"""Ported (trimmed) from the old repo's tests/core/github/test_client.py: issue creation and the
fingerprint-marker dedup search, a fake fetch/write only -- no test here makes a live call.

The proposal-effect primitives (get_ref/create_ref/get_contents/put_contents/
find_pull_requests/create_pull_request/update_pull_request/get_pull_request_author/get_app_id)
were ported 2026-10-23 alongside propose/effect.py, reusing this file's own OWNER/REPO fixture
names rather than the old repo's own separate pair for that section -- neither pair's exact
identity matters to what is being tested."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from repo_presenter.github.client import (
    API_ROOT,
    ISSUE_LIST_MAX_PAGES,
    PULLS_PAGE_SIZE,
    create_issue,
    create_pull_request,
    create_ref,
    find_issue_with_marker,
    find_pull_requests,
    get_app_id,
    get_contents,
    get_pull_request_author,
    get_ref,
    put_contents,
    update_pull_request,
)
from repo_presenter.github.errors import RepositoryMetadataError

OWNER = "aspose-cells-foss"
REPO = "Aspose.Cells-FOSS-for-Cpp"


class _RecordingWrite:
    def __init__(self, status_code: int = 200, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


def test_create_issue_posts_title_and_body_and_returns_number_and_url() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={"number": 42, "html_url": "https://github.com/o/n/issues/42", "id": 999},
    )
    created = create_issue(
        OWNER,
        REPO,
        title="install_command:cmake is UNRESOLVED",
        body="See evidence.",
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/issues"
    assert token == "ghp_w"
    assert payload == {"title": "install_command:cmake is UNRESOLVED", "body": "See evidence."}
    assert created.number == 42
    assert created.url == "https://github.com/o/n/issues/42"


def test_create_issue_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_issue(OWNER, REPO, title="t", body="b", token="", write=write)
    assert write.calls == []


def test_create_issue_raises_on_a_non_201_status() -> None:
    write = _RecordingWrite(status_code=422, body={"message": "Validation failed"})
    with pytest.raises(RepositoryMetadataError):
        create_issue(OWNER, REPO, title="t", body="b", token="ghp_w", write=write)


def test_create_issue_raises_on_unreachable() -> None:
    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return -1, "ConnectError: name resolution failed"

    with pytest.raises(RepositoryMetadataError):
        create_issue(OWNER, REPO, title="t", body="b", token="ghp_w", write=write)


def test_create_issue_raises_on_a_malformed_success_body() -> None:
    write = _RecordingWrite(status_code=201, body={"message": "created but no number field"})
    with pytest.raises(RepositoryMetadataError):
        create_issue(OWNER, REPO, title="t", body="b", token="ghp_w", write=write)


# ---------------------------------------------------------------------------
# find_issue_with_marker (the remote dedup read)
# ---------------------------------------------------------------------------

MARKER = "<!-- repo-presenter-defect: sha256:abc -->"


class _PagedFetch:
    """Serves ``pages[n-1]`` for the nth request and records every URL it was asked for."""

    def __init__(self, *pages: tuple[int, object]) -> None:
        self.pages = list(pages)
        self.urls: list[str] = []

    def __call__(self, url: str, token: str | None) -> tuple[int, object]:
        self.urls.append(url)
        assert token == "ghp_r"
        index = len(self.urls) - 1
        return self.pages[min(index, len(self.pages) - 1)]


def _issue(number: int, body: str, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "html_url": f"https://github.com/o/n/issues/{number}",
        "body": body,
        **extra,
    }


def test_find_issue_returns_the_issue_whose_body_carries_the_marker_even_when_closed() -> None:
    fetch = _PagedFetch(
        (200, [_issue(3, "unrelated"), _issue(9, f"text\n\n{MARKER}\n", state="closed")]),
    )
    found = find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch)
    assert found is not None
    assert found.number == 9
    assert found.url == "https://github.com/o/n/issues/9"
    assert "state=all" in fetch.urls[0]


def test_find_issue_skips_pull_requests_that_happen_to_carry_the_marker() -> None:
    fetch = _PagedFetch(
        (200, [_issue(5, MARKER, pull_request={"url": "x"}), _issue(6, "no marker")]),
    )
    assert find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch) is None


def test_find_issue_returns_none_only_after_a_short_final_page() -> None:
    fetch = _PagedFetch((200, [_issue(1, "a"), _issue(2, "b")]))
    assert find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch) is None
    assert len(fetch.urls) == 1


def test_find_issue_pages_past_a_full_page_to_find_the_marker() -> None:
    full_page = [_issue(n, "no") for n in range(100)]
    fetch = _PagedFetch((200, full_page), (200, [_issue(777, MARKER)]))
    found = find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch)
    assert found is not None and found.number == 777
    assert "page=2" in fetch.urls[1]


def test_find_issue_fails_closed_on_an_http_error_never_reporting_absence() -> None:
    fetch = _PagedFetch((403, {"message": "Forbidden"}))
    with pytest.raises(RepositoryMetadataError):
        find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch)


def test_find_issue_fails_closed_when_unreachable() -> None:
    fetch = _PagedFetch((-1, "ConnectError: boom"))
    with pytest.raises(RepositoryMetadataError):
        find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch)


def test_find_issue_fails_closed_past_the_page_cap() -> None:
    full_page = [_issue(n, "no") for n in range(100)]
    fetch = _PagedFetch((200, full_page))
    with pytest.raises(RepositoryMetadataError, match="cannot prove absence"):
        find_issue_with_marker(OWNER, REPO, MARKER, token="ghp_r", fetch=fetch)
    assert len(fetch.urls) == ISSUE_LIST_MAX_PAGES


# ---------------------------------------------------------------------------
# The proposal-effect primitives: branch, contents, and pull-request RPCs
# propose/effect.py composes into one idempotent "create or update a presenter
# branch and its PR" write. Ported 2026-10-23.
# ---------------------------------------------------------------------------


def test_get_ref_returns_the_tip_sha_when_the_branch_exists() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/git/ref/heads/main"
        return 200, {"object": {"sha": "abc123"}}

    assert get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch) == "abc123"


def test_get_ref_returns_none_when_the_branch_does_not_exist() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 404, {"message": "Not Found"}

    assert get_ref(OWNER, REPO, "presenter/readme-update", token="ghp_w", fetch=fetch) is None


def test_get_ref_raises_on_unreachable() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch)


def test_get_ref_raises_on_a_malformed_success_body() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, {"object": {}}

    with pytest.raises(RepositoryMetadataError):
        get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch)


def test_create_ref_posts_the_new_branch_pointing_at_sha() -> None:
    write = _RecordingWrite(status_code=201, body={"ref": "refs/heads/presenter/readme-update"})
    create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="ghp_w", write=write)
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/git/refs"
    assert token == "ghp_w"
    assert payload == {"ref": "refs/heads/presenter/readme-update", "sha": "abc123"}


def test_create_ref_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="", write=write)
    assert write.calls == []


def test_create_ref_raises_on_a_non_201_status() -> None:
    write = _RecordingWrite(status_code=422, body={"message": "Reference already exists"})
    with pytest.raises(RepositoryMetadataError):
        create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="ghp_w", write=write)


def test_get_contents_decodes_base64_text() -> None:

    encoded = base64.b64encode(b"# Hello\n").decode("ascii")

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/contents/README.md?ref=main"
        return 200, {"sha": "filesha1", "content": encoded}

    contents = get_contents(OWNER, REPO, "README.md", ref="main", token="ghp_w", fetch=fetch)
    assert contents is not None
    assert contents.text == "# Hello\n"
    assert contents.sha == "filesha1"


def test_get_contents_returns_none_when_the_file_does_not_exist_on_this_branch() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 404, {"message": "Not Found"}

    found = get_contents(OWNER, REPO, "README.md", ref="presenter/x", token="ghp_w", fetch=fetch)
    assert found is None


def test_get_contents_raises_on_unreachable() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        get_contents(OWNER, REPO, "README.md", ref="main", token="ghp_w", fetch=fetch)


def test_put_contents_creates_a_new_file_with_no_sha() -> None:

    write = _RecordingWrite(
        status_code=201,
        body={"content": {"sha": "newfilesha"}, "commit": {"sha": "newcommitsha"}},
    )
    outcome = put_contents(
        OWNER,
        REPO,
        "README.md",
        branch="presenter/readme-update",
        message="Update README via repo-presenter",
        text="# New\n",
        sha=None,
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/contents/README.md"
    assert token == "ghp_w"
    assert "sha" not in payload
    assert base64.b64decode(payload["content"]).decode("utf-8") == "# New\n"
    assert outcome.content_sha == "newfilesha"
    assert outcome.commit_sha == "newcommitsha"


def test_put_contents_updates_an_existing_file_with_its_sha() -> None:
    write = _RecordingWrite(
        status_code=200,
        body={"content": {"sha": "updatedsha"}, "commit": {"sha": "updatedcommit"}},
    )
    put_contents(
        OWNER,
        REPO,
        "README.md",
        branch="presenter/readme-update",
        message="m",
        text="# Updated\n",
        sha="oldsha",
        token="ghp_w",
        write=write,
    )
    assert write.calls[0][2]["sha"] == "oldsha"


def test_put_contents_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        put_contents(
            OWNER, REPO, "README.md", branch="b", message="m", text="t", sha=None,
            token="", write=write,
        )
    assert write.calls == []


def test_put_contents_raises_on_unreachable_the_lost_response_shape() -> None:
    """propose/effect.py pattern-matches "unreachable" in this exact message to decide a
    response was lost (eligible for reconciliation) rather than hard-rejected."""

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return -1, "ReadTimeout: the server did not respond"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        put_contents(
            OWNER, REPO, "README.md", branch="b", message="m", text="t", sha=None,
            token="ghp_w", write=write,
        )


def test_put_contents_raises_on_a_non_2xx_status() -> None:
    write = _RecordingWrite(status_code=409, body={"message": "sha does not match"})
    with pytest.raises(RepositoryMetadataError):
        put_contents(
            OWNER, REPO, "README.md", branch="b", message="m", text="t", sha="stalesha",
            token="ghp_w", write=write,
        )


def _pull(
    number: int, *, state: str, merged_at: str | None = None, body: str = ""
) -> dict[str, Any]:
    return {
        "number": number,
        "html_url": f"https://github.com/x/y/pull/{number}",
        "title": "Update README",
        "body": body,
        "state": state,
        "merged_at": merged_at,
    }


def test_find_pull_requests_asks_for_every_state_not_only_open() -> None:
    seen: list[str] = []

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        seen.append(url)
        return 200, []

    assert (
        find_pull_requests(OWNER, REPO, head_branch="presenter/x", token="ghs_w", fetch=fetch) == ()
    )
    assert "state=all" in seen[0]
    assert "state=open" not in seen[0]
    assert f"head={OWNER}:presenter/x" in seen[0]


def test_find_pull_requests_classifies_open_closed_and_merged() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, [
            _pull(12, state="open"),
            _pull(11, state="closed", merged_at="2026-10-01T00:00:00Z", body="merged one"),
            _pull(10, state="closed", merged_at=None, body="declined one"),
        ]

    found = find_pull_requests(OWNER, REPO, head_branch="b", token="ghs_w", fetch=fetch)
    assert [(pr.number, pr.state) for pr in found] == [(12, "open"), (11, "merged"), (10, "closed")]
    assert found[1].body == "merged one"


def test_find_pull_requests_refuses_a_full_page_as_possibly_incomplete() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, [_pull(n, state="closed") for n in range(PULLS_PAGE_SIZE)]

    with pytest.raises(RepositoryMetadataError, match="cannot be proven complete"):
        find_pull_requests(OWNER, REPO, head_branch="b", token="ghs_w", fetch=fetch)


def test_find_pull_requests_raises_on_unreachable_and_on_http_errors() -> None:
    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        find_pull_requests(
            OWNER, REPO, head_branch="b", token="t", fetch=lambda u, t: (-1, "ConnectError")
        )
    with pytest.raises(RepositoryMetadataError, match="HTTP 500"):
        find_pull_requests(OWNER, REPO, head_branch="b", token="t", fetch=lambda u, t: (500, None))


def test_create_pull_request_posts_head_base_title_and_body() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={
            "number": 11,
            "html_url": "https://github.com/x/y/pull/11",
            "title": "Update README",
            "body": "body",
        },
    )
    created = create_pull_request(
        OWNER, REPO, title="Update README", body="body", head="presenter/readme-update",
        base="main", token="ghp_w", write=write,
    )
    assert len(write.calls) == 1
    url, _token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/pulls"
    assert payload == {
        "title": "Update README",
        "body": "body",
        "head": "presenter/readme-update",
        "base": "main",
    }
    assert created.number == 11
    assert created.url == "https://github.com/x/y/pull/11"


def test_create_pull_request_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_pull_request(
            OWNER, REPO, title="t", body="b", head="h", base="main", token="", write=write
        )
    assert write.calls == []


def test_update_pull_request_patches_title_and_body() -> None:
    write = _RecordingWrite(
        status_code=200,
        body={"html_url": "https://github.com/x/y/pull/11", "title": "New title", "body": "new"},
    )
    updated = update_pull_request(
        OWNER, REPO, 11, title="New title", body="new", token="ghp_w", write=write
    )
    assert len(write.calls) == 1
    url, _token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/pulls/11"
    assert payload == {"title": "New title", "body": "new"}
    assert updated.number == 11
    assert updated.title == "New title"


def test_update_pull_request_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        update_pull_request(OWNER, REPO, 11, title="t", body="b", token="", write=write)
    assert write.calls == []


def test_update_pull_request_raises_on_a_non_200_status() -> None:
    write = _RecordingWrite(status_code=404, body={"message": "Not Found"})
    with pytest.raises(RepositoryMetadataError):
        update_pull_request(OWNER, REPO, 11, title="t", body="b", token="ghp_w", write=write)


def test_get_pull_request_author_reads_the_bot_login_not_performed_via_github_app() -> None:
    seen: list[str] = []

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        seen.append(url)
        return 200, {
            "user": {"login": "repo-presenter[bot]", "type": "Bot"},
            "performed_via_github_app": None,
        }

    assert get_pull_request_author(OWNER, REPO, 4, token="ghs_w", fetch=fetch) == (
        "repo-presenter[bot]",
        "Bot",
    )
    assert seen == [f"{API_ROOT}/repos/{OWNER}/{REPO}/issues/4"]


def test_get_pull_request_author_is_none_without_a_user_and_raises_on_http_errors() -> None:
    assert (
        get_pull_request_author(OWNER, REPO, 4, token="t", fetch=lambda u, t: (200, {"user": None}))
        is None
    )
    with pytest.raises(RepositoryMetadataError, match="HTTP 404"):
        get_pull_request_author(OWNER, REPO, 4, token="t", fetch=lambda u, t: (404, {}))
    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        get_pull_request_author(OWNER, REPO, 4, token="t", fetch=lambda u, t: (-1, "x"))


def test_get_app_id_reads_the_public_app_by_slug() -> None:
    seen: list[str] = []

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        seen.append(url)
        return 200, {"id": 5092474, "slug": "repository-presenter"}

    assert get_app_id("repository-presenter", token="ghs_w", fetch=fetch) == 5092474
    assert seen == [f"{API_ROOT}/apps/repository-presenter"]
    with pytest.raises(RepositoryMetadataError, match="HTTP 404"):
        get_app_id("nope", token="t", fetch=lambda u, t: (404, {}))
