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
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn
from urllib.parse import urlsplit

import httpx

from repo_presenter.github.errors import RepositoryMetadataError

API_ROOT = "https://api.github.com"
USER_AGENT = "repo-presenter (+https://github.com/babar-raza/repo-presenter)"
REQUEST_TIMEOUT_SECONDS = 30.0

FetchFn = Callable[[str, "str | None"], "tuple[int, Any]"]
WriteFn = Callable[[str, str, "dict[str, Any]"], "tuple[int, Any]"]


# Owner directive 2026-11-04 (docs/DECISION_LOG.md), amended by owner ruling R3
# (docs/CONSOLIDATED_GOALS_2026-11-06.md, 2026-11-06): the control repository below may be written
# for its own internal effects; every other repository is READ-ONLY unless the owner-controlled
# ``data/upstream_write_allowlist.json`` lists it for the specific effect being attempted.
# ``authorize_write`` is the single, effect-specific, default-deny decision; every real HTTP write
# primitive below (``default_post``/``default_patch``/``default_put`` and ``_guarded_issue_write``)
# reaches it through ``authorize_request`` before any request is made. There is deliberately no
# environment-variable override: changing it is a reviewed code or owner-data change.
#
# The allowlist is a NECESSARY condition only. It authorizes nothing by itself: the callers
# (``repo_presenter.propose.effect``'s registry permit, kill switch, reviewer veto, reviewer
# calibration, authorization record, token provenance and source recheck) still gate every effect.
CONTROL_REPOSITORY = "babar-raza/repo-presenter"
WRITE_ALLOWED_REPOSITORIES = frozenset({CONTROL_REPOSITORY})
_REPO_PATH = re.compile(r"^/repos/(?P<owner>[^/]+)/(?P<name>[^/]+)(?:/|$)")

#: The owner-controlled upstream allowlist (ruling R3). Read on every authorization, never cached,
#: so a removed entry takes effect immediately; missing or malformed means nothing is allowed.
UPSTREAM_WRITE_ALLOWLIST = (
    Path(__file__).resolve().parents[3] / "data" / "upstream_write_allowlist.json"
)

#: The owner-controlled issue-management pilot (ruling R39): a repository listed there may have
#: its existing issues closed/reopened (``issue``) and commented on (``issue_comment``), never a
#: new issue created. Read on every authorization, never cached; missing or malformed grants
#: nothing.
ISSUE_PILOT_ALLOWLIST = Path(__file__).resolve().parents[3] / "data" / "issue_pilot.json"
_PILOT_ISSUE_EFFECTS = frozenset({"issue", "issue_comment"})


def _pilot_effects(slug: str) -> frozenset[str]:
    from repo_presenter.issues.pilot import pilot_effects  # stdlib-only module; no import cycle

    return pilot_effects(slug, ISSUE_PILOT_ALLOWLIST)


WriteEffect = Literal["pull_request", "issue", "issue_comment", "internal"]
#: Effects an allowlist entry may grant on an upstream repository. Independent of each other: a
#: repository allowed ``pull_request`` is refused ``issue`` and ``issue_comment``.
UPSTREAM_EFFECTS = frozenset({"pull_request", "issue", "issue_comment"})
#: ``internal`` is any other write shape on the control repository (unchanged from before R3);
#: it is never grantable upstream.
KNOWN_EFFECTS = UPSTREAM_EFFECTS | {"internal"}

#: The branch namespace every upstream branch/contents write must stay inside: the pull-request
#: effect needs a presenter branch on the target, never a write to its default branch.
UPSTREAM_BRANCH_PREFIX = "repository-presenter/"


class UpstreamWriteForbiddenError(RepositoryMetadataError):
    """A write was refused before any request was made: its target is not an allowed repository,
    or not allowed for this effect."""


class PortfolioIncompleteError(UpstreamWriteForbiddenError):
    """Owner ruling R15: an upstream pull-request effect was refused before any request was made
    because not every active repository has a terminal outcome in both lanes
    (``repo_presenter.propose.portfolio_gate``)."""

    code = "portfolio_incomplete"


def portfolio_readiness() -> Any:
    """The R15 portfolio predicate, computed afresh on every upstream pull-request authorization
    (never cached). A module-level seam so a test substitutes the reader, never the decision."""
    from repo_presenter.propose.portfolio_gate import portfolio_readiness as compute

    return compute()


def _require_portfolio_complete(slug: str) -> None:
    try:
        readiness = portfolio_readiness()
        ready = readiness.ready is True
        reason = readiness.reason()
    except Exception as exc:  # noqa: BLE001 -- fail closed: an unreadable predicate is not ready
        ready, reason = False, f"portfolio readiness unreadable ({type(exc).__name__}: {exc})"
    if not ready:
        raise PortfolioIncompleteError(f"write refused: {slug}: {reason}")


@dataclass(frozen=True)
class WriteGrant:
    """What :func:`authorize_write` cleared: one repository, one effect."""

    repository: str
    effect: str
    upstream: bool
    #: The allowlist entry's ``first_pr_as_draft``. Every pull request this system opens on such a
    #: repository is a draft (see :func:`create_pull_request`).
    draft_required: bool = False
    #: Granted by the R39 issue-management pilot (``data/issue_pilot.json``) rather than the R3
    #: allowlist: maintenance of existing issues only -- never a create, and a PATCH may change
    #: only ``state``/``state_reason`` (enforced in :func:`authorize_request`).
    issue_pilot: bool = False


@dataclass(frozen=True)
class _AllowlistEntry:
    effects: frozenset[str]
    first_pr_as_draft: bool


def _load_upstream_allowlist(path: Path) -> dict[str, _AllowlistEntry]:
    """The allowlist as ``{lowercased slug: entry}``. Raises :class:`UpstreamWriteForbiddenError`
    for a missing, unreadable or malformed file: one bad entry invalidates the whole file."""

    def bad(why: str) -> NoReturn:
        raise UpstreamWriteForbiddenError(f"write refused: upstream allowlist {path} {why}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        bad("is missing")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        bad(f"is unreadable ({type(exc).__name__})")
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        bad("has no schema_version 1 object")
    entries = data.get("repositories")
    if not isinstance(entries, list):
        bad("has no repositories list")
    result: dict[str, _AllowlistEntry] = {}
    for item in entries:
        if not isinstance(item, dict):
            bad("has a non-object entry")
        slug = item.get("repository")
        effects = item.get("effects")
        draft = item.get("first_pr_as_draft")
        if not isinstance(slug, str) or slug.count("/") != 1 or not all(slug.split("/")):
            bad(f"has an invalid repository {slug!r}")
        if (
            not isinstance(effects, list)
            or not effects
            or not all(isinstance(e, str) and e in UPSTREAM_EFFECTS for e in effects)
        ):
            bad(f"has invalid effects for {slug}: {effects!r}")
        if not isinstance(draft, bool):
            bad(f"has a non-boolean first_pr_as_draft for {slug}")
        key = slug.lower()
        if key in result:
            bad(f"lists {slug} twice")
        result[key] = _AllowlistEntry(frozenset(effects), draft)
    return result


def authorize_write(repository: str, effect: str) -> WriteGrant:
    """The one write-authorization decision: default deny, fail closed, effect-specific.

    * Unknown ``effect`` -> refused (for every repository).
    * The control repository -> allowed for every known effect, exactly as before R3.
    * Any other repository -> allowed only when ``data/upstream_write_allowlist.json`` loads
      cleanly AND lists it AND lists ``effect`` for it. ``internal`` is never grantable upstream.
    * An upstream ``pull_request`` additionally requires the R15 portfolio predicate
      (:func:`portfolio_readiness`) to hold; otherwise :class:`PortfolioIncompleteError`.

    Raises :class:`UpstreamWriteForbiddenError`; never makes a request."""
    if effect not in KNOWN_EFFECTS:
        raise UpstreamWriteForbiddenError(f"write refused: unknown effect {effect!r}")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise UpstreamWriteForbiddenError(f"write refused: {repository!r} is not owner/name")
    slug = repository.lower()
    if slug == CONTROL_REPOSITORY:
        return WriteGrant(repository=slug, effect=effect, upstream=False)
    if effect not in UPSTREAM_EFFECTS:
        raise UpstreamWriteForbiddenError(
            f"write refused: {slug} is read-only for effect {effect!r} (only "
            f"{CONTROL_REPOSITORY} may be written for it)"
        )
    if effect in _PILOT_ISSUE_EFFECTS and effect in _pilot_effects(slug):
        # Owner ruling R39: the issue-management pilot maintains the presenter's own existing
        # issues on its listed repositories. A separate owner-controlled file, so the R3/R22
        # allowlist (draft pull requests only) is unchanged.
        return WriteGrant(repository=slug, effect=effect, upstream=True, issue_pilot=True)
    entry = _load_upstream_allowlist(UPSTREAM_WRITE_ALLOWLIST).get(slug)
    if entry is None:
        raise UpstreamWriteForbiddenError(
            f"write refused: {slug} is read-only for this execution (not in the upstream write "
            f"allowlist; only {sorted(WRITE_ALLOWED_REPOSITORIES)} may be written)"
        )
    if effect not in entry.effects:
        raise UpstreamWriteForbiddenError(
            f"write refused: {slug} is allowlisted for {sorted(entry.effects)}, not {effect!r}"
        )
    if effect == "pull_request":
        # Owner ruling R15 (with R16/R20/R24/R33): no upstream branch push or pull request before
        # every active repository has a terminal outcome in both lanes. Last, after every cheap
        # refusal; every upstream ref/contents/pull-request request reaches it via
        # ``authorize_request``. Issues (R39) are a different effect and never reach it.
        _require_portfolio_complete(slug)
    return WriteGrant(
        repository=slug, effect=effect, upstream=True, draft_required=entry.first_pr_as_draft
    )


def _parse_write_url(url: str) -> tuple[str, str]:
    """``(lowercased owner/name, path after it)`` for a ``/repos/{owner}/{repo}/...`` URL on the
    GitHub API root; raises for every other shape."""
    parts = urlsplit(url)
    if f"{parts.scheme}://{parts.netloc}" != API_ROOT:
        raise UpstreamWriteForbiddenError(f"write refused: {url} is not on {API_ROOT}")
    if "%" in parts.path or ".." in parts.path or parts.query.startswith("/"):
        raise UpstreamWriteForbiddenError(f"write refused: {url} has an encoded or dotted path")
    match = _REPO_PATH.match(parts.path)
    if match is None:
        raise UpstreamWriteForbiddenError(f"write refused: {url} does not target a repository")
    return f"{match['owner']}/{match['name']}".lower(), parts.path[match.end() :].rstrip("/")


# (method, path after /repos/{owner}/{repo}/) -> effect. Anything else is ``internal``.
_EFFECT_ROUTES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("POST", re.compile(r"^pulls$"), "pull_request"),
    ("PATCH", re.compile(r"^pulls/\d+$"), "pull_request"),
    ("POST", re.compile(r"^git/refs$"), "pull_request"),
    ("PUT", re.compile(r"^contents/.+$"), "pull_request"),
    ("POST", re.compile(r"^issues$"), "issue"),
    ("PATCH", re.compile(r"^issues/\d+$"), "issue"),
    ("POST", re.compile(r"^issues/\d+/comments$"), "issue_comment"),
)


def classify_write(method: str, url: str) -> tuple[str, str]:
    """``(repository, effect)`` for a write request; ``effect`` is ``internal`` for any shape
    outside the routes above (which :func:`authorize_write` allows only on the control repo)."""
    slug, rest = _parse_write_url(url)
    for verb, pattern, effect in _EFFECT_ROUTES:
        if method.upper() == verb and pattern.match(rest):
            return slug, effect
    return slug, "internal"


def authorize_request(
    method: str, url: str, payload: dict[str, Any] | None = None
) -> WriteGrant:
    """Authorize one concrete write request, before it is made. Beyond :func:`authorize_write`,
    an upstream request must also keep to the narrow shape its effect needs:

    * a branch/contents write stays inside ``UPSTREAM_BRANCH_PREFIX`` (never the default branch);
    * a pull-request update changes only ``title``/``body`` (never state, base or draft);
    * a pull request comes from a presenter branch, and on a ``first_pr_as_draft`` repository
      carries ``draft: true``."""
    slug, effect = classify_write(method, url)
    grant = authorize_write(slug, effect)
    if not grant.upstream:
        return grant
    body = payload if isinstance(payload, dict) else {}
    _, rest = _parse_write_url(url)

    def refuse(why: str) -> NoReturn:
        raise UpstreamWriteForbiddenError(f"write refused: {method.upper()} {url}: {why}")

    if grant.issue_pilot:
        if rest == "issues":
            refuse("the issue-management pilot (R39) maintains existing issues; it never creates one")
        if rest.startswith("issues/") and method.upper() == "PATCH" and (
            not body or not set(body) <= {"state", "state_reason"}
        ):
            refuse("a pilot issue update may change only state and state_reason")
        return grant
    if rest == "git/refs":
        ref = body.get("ref")
        if not isinstance(ref, str) or not ref.startswith("refs/heads/" + UPSTREAM_BRANCH_PREFIX):
            refuse(f"an upstream ref must be under refs/heads/{UPSTREAM_BRANCH_PREFIX}")
    elif rest.startswith("contents/"):
        branch = body.get("branch")
        if not isinstance(branch, str) or not branch.startswith(UPSTREAM_BRANCH_PREFIX):
            refuse(f"an upstream contents write must name a {UPSTREAM_BRANCH_PREFIX} branch")
    elif rest.startswith("pulls/"):
        if not set(body) <= {"title", "body"}:
            refuse("an upstream pull-request update may change only title and body")
    elif rest == "pulls":
        head = body.get("head")
        if not isinstance(head, str) or not head.split(":")[-1].startswith(
            UPSTREAM_BRANCH_PREFIX
        ):
            refuse(f"an upstream pull request must come from a {UPSTREAM_BRANCH_PREFIX} branch")
        if grant.draft_required and body.get("draft") is not True:
            refuse("this repository's pull requests must be opened as drafts")
    return grant


def assert_write_allowed(url: str) -> None:
    """Raise unless ``url`` is a ``/repos/{owner}/{repo}/...`` URL on the GitHub API root whose
    repository is the control repository (``WRITE_ALLOWED_REPOSITORIES``). Fails closed on every
    other shape. A control-repository-only check, unchanged since 2026-11-04; the real write
    primitives use the effect-aware :func:`authorize_request` instead."""
    slug, _ = _parse_write_url(url)
    if slug not in {a.lower() for a in WRITE_ALLOWED_REPOSITORIES}:
        raise UpstreamWriteForbiddenError(
            f"write refused: {slug} is read-only for this execution (only "
            f"{sorted(WRITE_ALLOWED_REPOSITORIES)} may be written)"
        )


def pull_request_draft_required(owner: str, name: str) -> bool:
    """Whether a pull request opened on ``owner/name`` must be a draft. The control repository:
    never. An upstream repository: its allowlist entry's ``first_pr_as_draft``; when the allowlist
    cannot be read, ``True`` (fail safe -- the write itself is then refused by the guard)."""
    slug = f"{owner}/{name}".lower()
    if slug == CONTROL_REPOSITORY:
        return False
    try:
        entry = _load_upstream_allowlist(UPSTREAM_WRITE_ALLOWLIST).get(slug)
    except UpstreamWriteForbiddenError:
        return True
    return entry.first_pr_as_draft if entry is not None else False


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
    authorize_request("POST", url, payload)
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
    authorize_request("PATCH", url, payload)
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
    authorize_request("PUT", url, payload)
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
    #: ``"open"`` or ``"closed"`` as GitHub reports it for an issue found by the dedup search
    #: (a freshly created issue is open). Lets a caller tell a recurrence of a closed defect
    #: apart from a duplicate of a still-open one.
    state: str = "open"


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
    labels: Sequence[str] | None = None,
    assignees: Sequence[str] | None = None,
) -> CreatedIssue:
    """``POST /repos/{owner}/{repo}/issues``. ``labels``/``assignees`` join the payload only when
    non-empty, so a call without them posts exactly ``{"title", "body"}`` as before.

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 201 (GitHub's own
    success status for issue creation), or a response missing the ``number``/``html_url`` fields a
    caller needs to record what was filed -- never a guessed or partial result. An outcome that may
    still have created the issue raises :class:`IssueOutcomeUnknownError` so the caller reconciles
    instead of retrying blind.
    """
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/issues"
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = list(labels)
    if assignees:
        payload["assignees"] = list(assignees)
    status_code, response_body = write(url, token, payload)
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


def _guarded_issue_write(
    owner: str, name: str, url: str, token: str, payload: dict[str, Any], write: WriteFn, verb: str
) -> Any:
    """Shared body of the comment/close/reopen primitives. ``authorize_request`` runs HERE, on
    the URL (comment -> ``issue_comment``, close/reopen -> ``issue``), before ``write`` is ever
    called -- so even an injected writer is never invoked for a repository not authorized for
    that effect (the real ``default_post``/``default_patch`` check again). A missing token, a
    transport failure or a non-2xx answer raises; nothing is guessed."""
    authorize_request(verb, url, payload)
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: {verb} refused - no write-scoped token")
    status_code, response_body = write(url, token, payload)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code not in (200, 201):
        raise RepositoryMetadataError(f"{owner}/{name}: {verb} {url} returned HTTP {status_code}")
    return response_body


def comment_issue(
    owner: str,
    name: str,
    number: int,
    *,
    body: str,
    token: str,
    write: WriteFn = default_post,
) -> None:
    """``POST /repos/{owner}/{repo}/issues/{number}/comments``. Adds a comment; never edits or
    deletes one, so the issue's history only grows."""
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}/comments"
    _guarded_issue_write(owner, name, url, token, {"body": body}, write, "POST")


def issue_has_comment_with_marker(
    owner: str,
    name: str,
    number: int,
    marker: str,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
) -> bool:
    """Whether any comment on issue ``number`` contains ``marker`` (a read only).

    Makes a retried write idempotent: a partial failure that already posted a comment must not post
    it again. Like ``find_issue_with_marker``, absence is never inferred from a partial read: an
    unreachable host, a non-200 answer, or more than ``ISSUE_LIST_MAX_PAGES`` full pages raises
    :class:`RepositoryMetadataError` instead of returning ``False``."""
    for page in range(1, ISSUE_LIST_MAX_PAGES + 1):
        url = (
            f"{API_ROOT}/repos/{owner}/{name}/issues/{number}/comments"
            f"?per_page={ISSUE_LIST_PAGE_SIZE}&page={page}"
        )
        status_code, body = fetch(url, token)
        if status_code == -1:
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
        if status_code != 200 or not isinstance(body, list):
            raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
        for item in body:
            text = item.get("body") if isinstance(item, dict) else None
            if isinstance(text, str) and marker in text:
                return True
        if len(body) < ISSUE_LIST_PAGE_SIZE:
            return False
    raise RepositoryMetadataError(
        f"{owner}/{name}#{number}: more than {ISSUE_LIST_MAX_PAGES} pages of comments - "
        "cannot prove absence"
    )


def _read_all_pages(owner: str, name: str, base_url: str, token: str | None, fetch: FetchFn) -> list[Any]:
    """Every item of a paginated list endpoint, or :class:`RepositoryMetadataError` -- a partial
    read is never returned as if it were complete."""
    items: list[Any] = []
    separator = "&" if "?" in base_url else "?"
    for page in range(1, ISSUE_LIST_MAX_PAGES + 1):
        url = f"{base_url}{separator}per_page={ISSUE_LIST_PAGE_SIZE}&page={page}"
        status_code, body = fetch(url, token)
        if status_code == -1:
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
        if status_code != 200 or not isinstance(body, list):
            raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
        items.extend(body)
        if len(body) < ISSUE_LIST_PAGE_SIZE:
            return items
    raise RepositoryMetadataError(
        f"{owner}/{name}: more than {ISSUE_LIST_MAX_PAGES} pages at {base_url} - cannot read it all"
    )


def list_issues(
    owner: str, name: str, *, token: str | None, fetch: FetchFn = default_fetch
) -> list[dict[str, Any]]:
    """Every issue of ``owner/name``, open and closed, pull requests left out (a read only)."""
    items = _read_all_pages(
        owner, name, f"{API_ROOT}/repos/{owner}/{name}/issues?state=all", token, fetch
    )
    return [i for i in items if isinstance(i, dict) and "pull_request" not in i]


def get_issue(
    owner: str, name: str, number: int, *, token: str | None, fetch: FetchFn = default_fetch
) -> dict[str, Any]:
    """One issue, with ``closed_by`` (which the list endpoint omits). A read only."""
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}"
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    return body


def list_issue_comments(
    owner: str, name: str, number: int, *, token: str | None, fetch: FetchFn = default_fetch
) -> list[dict[str, Any]]:
    """Every comment on issue ``number``, oldest first (a read only)."""
    items = _read_all_pages(
        owner, name, f"{API_ROOT}/repos/{owner}/{name}/issues/{number}/comments", token, fetch
    )
    return [i for i in items if isinstance(i, dict)]


IssueCloseReason = Literal["completed", "not planned"]
_STATE_REASONS = {"completed": "completed", "not planned": "not_planned"}


def close_issue(
    owner: str,
    name: str,
    number: int,
    *,
    reason: IssueCloseReason,
    token: str,
    write: WriteFn = default_patch,
) -> None:
    """``PATCH /repos/{owner}/{repo}/issues/{number}`` with ``state=closed`` and GitHub's
    ``state_reason`` (``completed`` / ``not_planned``). Only the state changes: labels, body and
    comments are untouched. The CALLER (``issues/close.py``) decides whether closing is
    authorized."""
    if reason not in _STATE_REASONS:
        raise ValueError(f"unknown close reason {reason!r}")
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}"
    payload = {"state": "closed", "state_reason": _STATE_REASONS[reason]}
    _guarded_issue_write(owner, name, url, token, payload, write, "PATCH")


def reopen_issue(
    owner: str,
    name: str,
    number: int,
    *,
    token: str,
    write: WriteFn = default_patch,
) -> None:
    """``PATCH /repos/{owner}/{repo}/issues/{number}`` with ``state=open``,
    ``state_reason=reopened``. The CALLER (``issues/file.py``) decides whether it is authorized."""
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}"
    payload = {"state": "open", "state_reason": "reopened"}
    _guarded_issue_write(owner, name, url, token, payload, write, "PATCH")


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
                state = item.get("state")
                return CreatedIssue(
                    number=number, url=html_url, state=state if isinstance(state, str) else "open"
                )
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
    none for the same candidate was already settled.

    ``draft: true`` is sent whenever the target's allowlist entry has ``first_pr_as_draft: true``
    (:func:`pull_request_draft_required`). Deliberately ALWAYS, not only for the first pull
    request: proving "no pull request by this system exists yet" would need an extra, paginated
    read whose partial failure could wrongly open a ready-for-review PR, so every PR on such a
    repository is opened as a draft and the owner marks it ready. The transport guard
    (:func:`authorize_request`) refuses a non-draft creation there. The control repository's
    payload is unchanged (no ``draft`` key)."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls"
    payload: dict[str, Any] = {"title": title, "body": body, "head": head, "base": base}
    if pull_request_draft_required(owner, name):
        payload["draft"] = True
    status_code, response_body = write(url, token, payload)
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
