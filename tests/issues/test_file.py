"""Tests for the gated filer (repo_presenter.issues.file), ported in shape from the old repo's
components/issues/test_file.py duplicate-filing-guard and kill-switch tests."""

from __future__ import annotations

from typing import Any

from repo_presenter.issues.dedup import fingerprint_marker
from repo_presenter.issues.file import AUTHORIZATION_VARIABLE, file_issue, write_authorized

FINGERPRINT = "sha256:abc123"
OWNER = "aspose-3d-foss"
REPO = "Aspose.3D-FOSS-for-Python"


class _RecordingWrite:
    def __init__(self, status_code: int = 201, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


def _empty_fetch(url: str, token: str | None) -> tuple[int, Any]:
    return 200, []


def _fetch_with_existing(number: int, fingerprint: str):  # type: ignore[no-untyped-def]
    marker = fingerprint_marker(fingerprint)

    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        return 200, [
            {
                "number": number,
                "html_url": f"https://github.com/{OWNER}/{REPO}/issues/{number}",
                "body": f"text\n\n{marker}\n",
            }
        ]

    return fetch


def test_write_authorized_is_true_only_for_truthy_values() -> None:
    assert write_authorized({AUTHORIZATION_VARIABLE: "1"}) is True
    assert write_authorized({AUTHORIZATION_VARIABLE: "true"}) is True
    assert write_authorized({AUTHORIZATION_VARIABLE: "YES"}) is True
    assert write_authorized({}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "0"}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: ""}) is False


def test_file_issue_refuses_without_authorization_no_network_call_made() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        raise AssertionError("must not search when not authorized")

    write = _RecordingWrite()
    result = file_issue(
        OWNER,
        REPO,
        title="t",
        body="b",
        defect_fingerprint=FINGERPRINT,
        token="ghp_w",
        authorized=False,
        fetch=fetch,
        write=write,
    )
    assert result.filed is False
    assert result.issue_ref is None
    assert write.calls == []


def test_file_issue_refuses_without_a_token_no_network_call_made() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        raise AssertionError("must not search without a token")

    write = _RecordingWrite()
    result = file_issue(
        OWNER,
        REPO,
        title="t",
        body="b",
        defect_fingerprint=FINGERPRINT,
        token=None,
        authorized=True,
        fetch=fetch,
        write=write,
    )
    assert result.filed is False
    assert write.calls == []


def test_file_issue_finds_an_already_filed_duplicate_and_never_creates_a_second_one() -> None:
    write = _RecordingWrite()
    result = file_issue(
        OWNER,
        REPO,
        title="t",
        body="b",
        defect_fingerprint=FINGERPRINT,
        token="ghp_w",
        authorized=True,
        fetch=_fetch_with_existing(99, FINGERPRINT),
        write=write,
    )
    assert result.filed is False
    assert result.issue_ref is not None
    assert result.issue_ref.number == 99
    assert write.calls == []  # the duplicate-filing guard: no POST is ever made


def test_file_issue_creates_a_new_issue_with_the_marker_appended_when_none_exists() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={"number": 101, "html_url": f"https://github.com/{OWNER}/{REPO}/issues/101"},
    )
    result = file_issue(
        OWNER,
        REPO,
        title="OBJ export drops material indices",
        body="Steps to reproduce...",
        defect_fingerprint=FINGERPRINT,
        token="ghp_w",
        authorized=True,
        fetch=_empty_fetch,
        write=write,
    )
    assert result.filed is True
    assert result.issue_ref is not None
    assert result.issue_ref.number == 101
    assert len(write.calls) == 1
    _, _, payload = write.calls[0]
    assert fingerprint_marker(FINGERPRINT) in payload["body"]
