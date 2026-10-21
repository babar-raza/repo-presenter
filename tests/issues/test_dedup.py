"""Tests for the fingerprint-marker dedup primitive (repo_presenter.issues.dedup), ported in shape
from the old repo's components/issues/file.py marker tests and core/github/client.py dedup tests,
adapted to this repository's own marker prefix."""

from __future__ import annotations

import pytest

from repo_presenter.github.errors import RepositoryMetadataError
from repo_presenter.issues.dedup import body_with_marker, check_dedup, fingerprint_marker

FINGERPRINT = "sha256:abc123"
OWNER = "aspose-3d-foss"
REPO = "Aspose.3D-FOSS-for-Python"


def test_fingerprint_marker_is_stable_and_contains_the_fingerprint() -> None:
    marker = fingerprint_marker(FINGERPRINT)
    assert FINGERPRINT in marker
    assert marker == fingerprint_marker(FINGERPRINT)


def test_body_with_marker_appends_once() -> None:
    body = "The defect text."
    with_marker = body_with_marker(body, FINGERPRINT)
    assert fingerprint_marker(FINGERPRINT) in with_marker
    assert body in with_marker
    # Appending again to an already-marked body does not duplicate the marker.
    assert body_with_marker(with_marker, FINGERPRINT).count(fingerprint_marker(FINGERPRINT)) == 1


class _PagedFetch:
    def __init__(self, *pages: tuple[int, object]) -> None:
        self.pages = list(pages)
        self.urls: list[str] = []

    def __call__(self, url: str, token: str | None) -> tuple[int, object]:
        self.urls.append(url)
        index = len(self.urls) - 1
        return self.pages[min(index, len(self.pages) - 1)]


def _issue(number: int, body: str, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "html_url": f"https://github.com/{OWNER}/{REPO}/issues/{number}",
        "body": body,
        **extra,
    }


def test_check_dedup_finds_an_existing_issue_carrying_the_marker() -> None:
    marker = fingerprint_marker(FINGERPRINT)
    fetch = _PagedFetch((200, [_issue(1, "unrelated"), _issue(7, f"stuff\n\n{marker}\n")]))
    found = check_dedup(OWNER, REPO, FINGERPRINT, token="ghp_r", fetch=fetch)
    assert found is not None
    assert found.number == 7


def test_check_dedup_returns_none_when_no_issue_carries_the_marker() -> None:
    fetch = _PagedFetch((200, [_issue(1, "unrelated"), _issue(2, "also unrelated")]))
    assert check_dedup(OWNER, REPO, FINGERPRINT, token="ghp_r", fetch=fetch) is None


def test_check_dedup_does_not_match_a_different_fingerprints_marker() -> None:
    other_marker = fingerprint_marker("sha256:different")
    fetch = _PagedFetch((200, [_issue(1, f"text\n\n{other_marker}\n")]))
    assert check_dedup(OWNER, REPO, FINGERPRINT, token="ghp_r", fetch=fetch) is None


def test_check_dedup_fails_closed_on_an_inconclusive_scan() -> None:
    fetch = _PagedFetch((403, {"message": "Forbidden"}))
    with pytest.raises(RepositoryMetadataError):
        check_dedup(OWNER, REPO, FINGERPRINT, token="ghp_r", fetch=fetch)
