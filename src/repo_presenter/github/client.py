"""GitHub REST client: issue creation and the fingerprint-marker dedup search.

Ported (trimmed) from the old repo's
``src/repository_presenter/core/github/client.py``. That module's docstring explains the fuller
design this is cut from: a plain ``(status_code, body)`` fetch/write callable is injected
everywhere, so every test here runs against a fake and makes no live network call, and this module
itself never decides *whether* a write should happen -- the caller (``repo_presenter.issues.file``)
gates that.

Only ``create_issue`` and ``find_issue_with_marker`` are ported in this pull: the two calls needed
to file one issue locally with a real dedup check. The old repo's metadata PATCH/PUT halves and its
pull-request primitives are not needed yet and are left for a later taskcard (see
``migration/reuse-manifest.yaml``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NoReturn

import httpx

from repo_presenter.github.errors import RepositoryMetadataError

API_ROOT = "https://api.github.com"
USER_AGENT = "repo-presenter (+https://github.com/babar-raza/repo-presenter)"
REQUEST_TIMEOUT_SECONDS = 30.0

FetchFn = Callable[[str, "str | None"], "tuple[int, Any]"]
WriteFn = Callable[[str, str, "dict[str, Any]"], "tuple[int, Any]"]


def _write_headers(token: str) -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }


def default_fetch(url: str, token: str | None) -> tuple[int, Any]:
    """GET ``url`` from the GitHub REST API. Returns ``(status_code, parsed_json_or_none)``.

    Never raises for an HTTP-level failure (404, 403, 5xx) or a transport failure (DNS, timeout,
    connection refused) -- the caller decides what a given outcome means. Status ``-1`` means
    unreachable, with the exception recorded as the (unparsed) body.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def default_post(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``POST url`` with ``payload`` as JSON. Never called except by ``create_issue``, which is
    itself never called except by ``repo_presenter.issues.file`` after that module's own
    authorization check passes."""
    try:
        response = httpx.post(
            url, headers=_write_headers(token), json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


@dataclass(frozen=True)
class CreatedIssue:
    """What GitHub returns for a successfully created issue (or an existing one found by the
    dedup search) -- only what a caller needs to record it as filed."""

    number: int
    url: str


class IssueOutcomeUnknownError(RepositoryMetadataError):
    """A write whose effect is unknown: the request may have been applied although no usable
    answer came back (the connection dropped, the server timed out or answered 5xx, or an HTTP 201
    carried no body to record). A caller must reconcile -- search the target for what it tried to
    create -- before it ever retries. A definite rejection (4xx) is a plain
    :class:`RepositoryMetadataError`: nothing was created."""


# Statuses after which a create may nevertheless have taken effect: a timeout and the gateway
# family (the proxy gave up while the origin went on). 429 and every other 4xx are definite.
_AMBIGUOUS_WRITE_STATUSES = frozenset({408, 500, 502, 503, 504})


def _write_failure(owner: str, name: str, url: str, status_code: int, body: Any) -> NoReturn:
    """Raise the right error for a POST that did not return its success status."""
    if status_code == -1:
        raise IssueOutcomeUnknownError(f"{owner}/{name}: unreachable ({body})")
    if status_code in _AMBIGUOUS_WRITE_STATUSES:
        raise IssueOutcomeUnknownError(
            f"{owner}/{name}: POST {url} returned HTTP {status_code}; the effect is unknown"
        )
    raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")


def create_issue(
    owner: str,
    name: str,
    *,
    title: str,
    body: str,
    token: str,
    write: WriteFn = default_post,
) -> CreatedIssue:
    """``POST /repos/{owner}/{repo}/issues``.

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 201 (GitHub's own
    success status for issue creation), or a response missing the ``number``/``html_url`` fields a
    caller needs to record what was filed -- never a guessed or partial result. An outcome that may
    still have created the issue raises :class:`IssueOutcomeUnknownError` so the caller reconciles
    instead of retrying blind.
    """
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/issues"
    status_code, response_body = write(url, token, {"title": title, "body": body})
    if status_code != 201:
        _write_failure(owner, name, url, status_code, response_body)
    if (
        not isinstance(response_body, dict)
        or "number" not in response_body
        or "html_url" not in response_body
    ):
        raise IssueOutcomeUnknownError(
            f"{owner}/{name}: POST {url} returned HTTP 201 with no usable issue body"
        )
    return CreatedIssue(number=int(response_body["number"]), url=str(response_body["html_url"]))


ISSUE_LIST_PAGE_SIZE = 100
ISSUE_LIST_MAX_PAGES = 10

# The prefix every issue body this system files carries (repo_presenter.issues.dedup appends the
# full marker, ``<prefix> sha256:<fingerprint> -->``); scanning for the full marker finds a match.
MARKER_PREFIX = "<!-- repo-presenter-defect:"


def find_issue_with_marker(
    owner: str,
    name: str,
    marker: str,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
) -> CreatedIssue | None:
    """The issue (open or closed, never a pull request) whose body contains ``marker``, or
    ``None``.

    This is the dedup read: the target repository itself is searched for the marker, so a run
    started from a fresh checkout (or a second run of this same script) never re-files the same
    defect. ``None`` is returned only after every page was read and none matched. Raises
    :class:`RepositoryMetadataError` when the scan is incomplete (an error, or more than
    ``ISSUE_LIST_MAX_PAGES`` full pages) -- absence is never inferred from a partial read.
    """
    for page in range(1, ISSUE_LIST_MAX_PAGES + 1):
        url = (
            f"{API_ROOT}/repos/{owner}/{name}/issues"
            f"?state=all&per_page={ISSUE_LIST_PAGE_SIZE}&page={page}"
        )
        status_code, body = fetch(url, token)
        if status_code == -1:
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
        if status_code != 200 or not isinstance(body, list):
            raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
        for item in body:
            if not isinstance(item, dict) or "pull_request" in item:
                continue
            text = item.get("body")
            if isinstance(text, str) and marker in text:
                number = item.get("number")
                html_url = item.get("html_url")
                if not isinstance(number, int) or not isinstance(html_url, str):
                    raise RepositoryMetadataError(
                        f"{owner}/{name}: matching issue has no usable number/html_url"
                    )
                return CreatedIssue(number=number, url=html_url)
        if len(body) < ISSUE_LIST_PAGE_SIZE:
            return None
    raise RepositoryMetadataError(
        f"{owner}/{name}: more than {ISSUE_LIST_MAX_PAGES} pages of issues - cannot prove absence"
    )
