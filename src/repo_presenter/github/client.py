"""GitHub REST client: issue creation, the fingerprint-marker dedup search, and the branch/
contents/pull-request primitives the README-proposal effect composes into one idempotent write.

Ported (trimmed) from the old repo's
``src/repository_presenter/core/github/client.py``. That module's docstring explains the fuller
design this is cut from: a plain ``(status_code, body)`` fetch/write callable is injected
everywhere, so every test here runs against a fake and makes no live network call, and this module
itself never decides *whether* a write should happen -- the caller (``repo_presenter.issues.file``,
``repo_presenter.propose.effect``) gates that.

``create_issue``/``find_issue_with_marker`` were pulled first (one real filed issue). The proposal-
effect primitives below (``get_ref``/``create_ref``/``get_contents``/``put_contents``/
``find_pull_requests``/``create_pull_request``/``update_pull_request``, plus
``get_pull_request_author``/``get_app_id`` for App attribution) were pulled 2026-10-23 alongside
``propose/effect.py``. The old repo's metadata PATCH/PUT halves (``update_repository``/
``replace_topics``, for ``components/metadata/apply.py``, idea.md's own explicitly-deferred
visual-asset/metadata work) are still not needed and left for later.
"""

from __future__ import annotations

import base64
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


def default_patch(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``PATCH url`` with ``payload`` as JSON. Never called except by ``update_pull_request``,
    which is itself never called except by ``repo_presenter.propose.effect`` after that module's
    own gates pass."""
    try:
        response = httpx.patch(
            url, headers=_write_headers(token), json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def default_put(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``PUT url`` with ``payload`` as JSON. Never called except by ``put_contents``, which is
    itself never called except by ``repo_presenter.propose.effect`` after that module's own gates
    pass."""
    try:
        response = httpx.put(
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


# ---------------------------------------------------------------------------
# Proposal effect: branch, contents, and pull-request primitives
# (repo_presenter.propose.effect's own gated caller, not this module).
# Ported (REUSE, verbatim apart from the import path) 2026-10-23.
# ---------------------------------------------------------------------------


def get_ref(
    owner: str,
    name: str,
    branch: str,
    *,
    token: str,
    fetch: FetchFn = default_fetch,
) -> str | None:
    """``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` -- the branch's current tip commit
    SHA, or ``None`` if the branch does not exist yet (HTTP 404, the only case this treats as a
    normal outcome rather than a failure -- the presenter branch legitimately does not exist on a
    target's first-ever proposal)."""
    url = f"{API_ROOT}/repos/{owner}/{name}/git/ref/heads/{branch}"
    status_code, body = fetch(url, token)
    if status_code == 404:
        return None
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    sha = body.get("object", {}).get("sha")
    if not isinstance(sha, str) or not sha:
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned no usable commit sha")
    return sha


def create_ref(
    owner: str,
    name: str,
    branch: str,
    sha: str,
    *,
    token: str,
    write: WriteFn = default_post,
) -> None:
    """``POST /repos/{owner}/{repo}/git/refs`` -- creates ``branch`` pointing at ``sha``. Only
    ever called when :func:`get_ref` has already confirmed the branch does not exist -- this
    project's one stable presenter branch per target is created once and reused, never
    recreated."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/git/refs"
    status_code, body = write(url, token, {"ref": f"refs/heads/{branch}", "sha": sha})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 201:
        raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")


@dataclass(frozen=True)
class FileContents:
    """One file's current content on one branch, as GitHub's Contents API reports it."""

    path: str
    sha: str
    text: str


def get_contents(
    owner: str,
    name: str,
    path: str,
    *,
    ref: str,
    token: str,
    fetch: FetchFn = default_fetch,
) -> FileContents | None:
    """``GET /repos/{owner}/{repo}/contents/{path}?ref={ref}`` -- the file's current text and
    blob ``sha`` on ``ref``, or ``None`` if the file does not exist on that branch yet (HTTP
    404)."""
    url = f"{API_ROOT}/repos/{owner}/{name}/contents/{path}?ref={ref}"
    status_code, body = fetch(url, token)
    if status_code == 404:
        return None
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    sha = body.get("sha")
    encoded = body.get("content")
    if not isinstance(sha, str) or not isinstance(encoded, str):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned no usable content")
    text = base64.b64decode(encoded.encode("ascii").replace(b"\n", b"")).decode("utf-8")
    return FileContents(path=path, sha=sha, text=text)


@dataclass(frozen=True)
class CommitOutcome:
    """The result of one ``put_contents`` call -- the new blob/commit SHAs GitHub assigned."""

    content_sha: str
    commit_sha: str


def put_contents(
    owner: str,
    name: str,
    path: str,
    *,
    branch: str,
    message: str,
    text: str,
    sha: str | None,
    token: str,
    write: WriteFn = default_put,
) -> CommitOutcome:
    """``PUT /repos/{owner}/{repo}/contents/{path}`` -- creates or updates ``path`` on ``branch``
    with one commit. ``sha`` is the file's current blob sha (from :func:`get_contents`) when
    updating an existing file, or ``None`` when creating it for the first time on this branch --
    GitHub's own endpoint distinguishes create/update by this field's presence, not a different
    verb. Raises :class:`RepositoryMetadataError` with the word "unreachable" in its message for
    a transport-level failure specifically (status ``-1``) -- ``propose/effect.py`` pattern-
    matches that wording to tell a genuinely lost response (eligible for reconciliation) apart
    from a hard rejection (422 validation error, 409 conflicting sha, etc.), which is never
    retried blindly."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PUT refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/contents/{path}"
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha is not None:
        payload["sha"] = sha
    status_code, body = write(url, token, payload)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code not in (200, 201) or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: PUT {url} returned HTTP {status_code}")
    content_sha = body.get("content", {}).get("sha")
    commit_sha = body.get("commit", {}).get("sha")
    if not isinstance(content_sha, str) or not isinstance(commit_sha, str):
        raise RepositoryMetadataError(f"{owner}/{name}: PUT {url} returned no usable commit")
    return CommitOutcome(content_sha=content_sha, commit_sha=commit_sha)


@dataclass(frozen=True)
class PullRequestRef:
    """One pull request's identity and current title/body, as GitHub reports it."""

    number: int
    url: str
    title: str
    body: str
    #: ``"open"``, ``"closed"`` (closed unmerged) or ``"merged"``.
    state: str = "open"


#: GitHub's list endpoint pages at this size; a full page means the history may be longer than
#: what was read, which the caller must treat as unknown rather than as complete.
PULLS_PAGE_SIZE = 100


def _pull_request_state(item: dict[str, Any]) -> str:
    if item.get("merged_at"):
        return "merged"
    return "open" if item.get("state") == "open" else "closed"


def find_pull_requests(
    owner: str,
    name: str,
    *,
    head_branch: str,
    token: str,
    fetch: FetchFn = default_fetch,
) -> tuple[PullRequestRef, ...]:
    """``GET /repos/{owner}/{repo}/pulls?head={owner}:{head_branch}&state=all`` -- every pull
    request ever opened from the presenter branch, newest first, open, closed and merged alike.
    A lookup that sees only open pull requests cannot tell "never proposed" from "proposed and
    merged or declined", and would recreate a settled proposal. A full page is reported as an
    error, not as a complete answer."""
    url = (
        f"{API_ROOT}/repos/{owner}/{name}/pulls?head={owner}:{head_branch}&state=all"
        f"&sort=created&direction=desc&per_page={PULLS_PAGE_SIZE}"
    )
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, list):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    if len(body) >= PULLS_PAGE_SIZE:
        raise RepositoryMetadataError(
            f"{owner}/{name}: {len(body)} pull requests from {head_branch!r} fill the page; the "
            "history cannot be proven complete"
        )
    return tuple(
        PullRequestRef(
            number=int(item["number"]),
            url=str(item["html_url"]),
            title=str(item.get("title", "")),
            body=str(item.get("body") or ""),
            state=_pull_request_state(item),
        )
        for item in body
    )


def get_pull_request_author(
    owner: str,
    name: str,
    number: int,
    *,
    token: str,
    fetch: FetchFn = default_fetch,
) -> tuple[str, str] | None:
    """``GET /repos/{owner}/{repo}/issues/{number}`` -- the ``(login, type)`` of the account that
    opened the pull request, or ``None`` when the response carries no author. A pull request
    opened by a GitHub App installation token is authored by that App's bot account
    (``<slug>[bot]``, type ``Bot``). ``performed_via_github_app`` is not that signal: GitHub
    leaves it null on a pull request's issue resource even when an App created it."""
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}"
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    user = body.get("user")
    if not isinstance(user, dict):
        return None
    login, kind = user.get("login"), user.get("type")
    return (login, kind) if isinstance(login, str) and isinstance(kind, str) else None


def get_app_id(slug: str, *, token: str, fetch: FetchFn = default_fetch) -> int | None:
    """``GET /apps/{slug}`` -- the numeric id of the public GitHub App ``slug`` (slugs are
    globally unique, so the bot login ``<slug>[bot]`` identifies exactly this App)."""
    url = f"{API_ROOT}/apps/{slug}"
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"app {slug}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"app {slug}: GET {url} returned HTTP {status_code}")
    app_id = body.get("id")
    return app_id if isinstance(app_id, int) else None


def create_pull_request(
    owner: str,
    name: str,
    *,
    title: str,
    body: str,
    head: str,
    base: str,
    token: str,
    write: WriteFn = default_post,
) -> PullRequestRef:
    """``POST /repos/{owner}/{repo}/pulls`` -- opens the one presenter PR from ``head`` into
    ``base``. Only ever called after :func:`find_pull_requests` has confirmed none is open and
    none for the same candidate was already settled."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls"
    status_code, response_body = write(
        url, token, {"title": title, "body": body, "head": head, "base": base}
    )
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code != 201 or not isinstance(response_body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")
    return PullRequestRef(
        number=int(response_body["number"]),
        url=str(response_body["html_url"]),
        title=str(response_body.get("title", title)),
        body=str(response_body.get("body") or body),
    )


def update_pull_request(
    owner: str,
    name: str,
    number: int,
    *,
    title: str,
    body: str,
    token: str,
    write: WriteFn = default_patch,
) -> PullRequestRef:
    """``PATCH /repos/{owner}/{repo}/pulls/{number}`` -- refreshes an existing presenter PR's
    title and body in place. Only ever called when the live title/body already differ from what
    this proposal would write -- a no-op invocation makes no call at all
    (``propose/effect.py`` checks before calling this), so a repeated, unchanged proposal never
    produces a spurious PR edit."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls/{number}"
    status_code, response_body = write(url, token, {"title": title, "body": body})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code != 200 or not isinstance(response_body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH {url} returned HTTP {status_code}")
    return PullRequestRef(
        number=number,
        url=str(response_body.get("html_url", f"{API_ROOT}/{owner}/{name}/pull/{number}")),
        title=str(response_body.get("title", title)),
        body=str(response_body.get("body") or body),
    )
