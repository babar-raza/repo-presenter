"""Ported (trimmed) from the old repo's tests/core/github/test_client.py: issue creation and the
fingerprint-marker dedup search, a fake fetch/write only -- no test here makes a live call."""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.github.client import (
    API_ROOT,
    ISSUE_LIST_MAX_PAGES,
    create_issue,
    find_issue_with_marker,
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
