"""Which write token a filing run may use, and how it is proven: local ``GH_TOKEN`` vs. production
GitHub App installation token.

Ported (trimmed) from the old repo's ``core/github/token_provenance.py``, whose docstring explains
the fuller design this is cut from: GitHub lets a bare installation token prove, through
``GET /installation/repositories``, that it is (a) actually an installation token (the ``ghs_``
prefix rules out every other family before any request is made) and (b) scoped to exactly one
repository. ``verify_installation_token`` is ported close to verbatim -- it is the part of the old
design this repository's production path will need unchanged.

What is new here (this repository's own model, not yet written in the old repo): the explicit
local-vs-production split. Local testing authenticates with a plain ``GH_TOKEN`` (a personal access
token, used directly -- there is no installation to verify against in a developer's own checkout).
Production is required to mint a GitHub App installation token and fails closed -- refuses, never
silently falls back to a personal token -- when that credential is absent or does not verify. This
is the shape ``migration/reuse-manifest.yaml``'s GitHub-App component entry asks to keep intact for
later even though only the local path is exercised end to end today.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from repo_presenter.authorization.refusals import Refusal
from repo_presenter.github.client import (
    API_ROOT,
    FetchFn,
    default_fetch,
    get_app_id,
    get_pull_request_author,
)
from repo_presenter.github.errors import RepositoryMetadataError

#: The GitHub App id/slug ``verify_pull_request_app`` attributes a presenter pull request to.
#: INHERITED FROM THE OLD REPO'S OWN REGISTERED APP (``core/github/token_provenance.py``,
#: ``project/state.yaml``), 2026-10-23 -- NOT independently confirmed as this repository's own
#: App identity. No pull request has ever been created by this repository (propose/effect.py
#: itself is "never fired live" by design), so this constant has not yet mattered in practice;
#: both values must be replaced with this repository's own actual GitHub App id/slug before
#: verify_pull_request_app is ever relied on for a real write -- consistent with mission section
#: 9's "the first live exercise against a real external target is owner-selected, never agent-
#: selected" rule. A caller may also override both as keyword arguments without editing this file.
EXPECTED_APP_ID = 5092474
EXPECTED_APP_SLUG = "repository-presenter"
INSTALLATION_TOKEN_PREFIX = "ghs_"
#: Env var a local run reads for its write-scoped token (never an installation token in practice).
LOCAL_TOKEN_ENV_VAR = "GH_TOKEN"
#: Env var a production run reads: a GitHub App installation token minted per run, scoped to one
#: repository. Never the same variable as the local path, so the two can never be confused.
APP_INSTALLATION_TOKEN_ENV_VAR = "GH_APP_INSTALLATION_TOKEN"

Mode = Literal["local", "production"]


@dataclass(frozen=True)
class TokenDecision:
    """``ok`` only when the token is usable for ``mode``; ``code``/``reason`` explain a refusal."""

    ok: bool
    token: str | None = None
    code: Refusal | None = None
    reason: str = "token verified"


def _refuse(code: Refusal, reason: str) -> TokenDecision:
    return TokenDecision(False, None, code, reason)


def verify_installation_token(
    repository: str, token: str, *, fetch: FetchFn = default_fetch
) -> TokenDecision:
    """Refuse unless ``token`` is an installation token whose reach is exactly ``repository``."""
    if not token.startswith(INSTALLATION_TOKEN_PREFIX):
        return _refuse(
            Refusal.TOKEN_NOT_INSTALLATION,
            "the write token is not a GitHub App installation token (expected a "
            f"{INSTALLATION_TOKEN_PREFIX!r} token minted per run; personal access tokens are "
            "never an accepted production write credential)",
        )
    url = f"{API_ROOT}/installation/repositories?per_page=100"
    status_code, body = fetch(url, token)
    if status_code == -1:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, f"could not verify the write token: {body}")
    if status_code in (401, 403):
        return _refuse(
            Refusal.TOKEN_NOT_INSTALLATION,
            f"GitHub refused the write token on the installation endpoint (HTTP {status_code}): "
            "it is not an installation token",
        )
    if status_code != 200 or not isinstance(body, dict):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            f"could not verify the write token: HTTP {status_code} from {url}",
        )
    listed = body.get("repositories")
    if not isinstance(listed, list) or body.get("total_count") != len(listed):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            "could not verify the write token: the installation repository list is incomplete",
        )
    reachable = sorted(
        str(item.get("full_name", "")).casefold() for item in listed if isinstance(item, dict)
    )
    if reachable != [repository.casefold()]:
        return _refuse(
            Refusal.TOKEN_WRONG_SCOPE,
            f"the write token reaches {len(reachable)} repositories, not exactly {repository} "
            "(mint it with the target repository as its only scope)",
        )
    return TokenDecision(True, token)


def resolve_write_token(
    environment: Mapping[str, str],
    *,
    repository: str,
    mode: Mode,
    fetch: FetchFn = default_fetch,
) -> TokenDecision:
    """Resolve the write-scoped token for ``mode``, failing closed rather than falling back.

    ``mode="local"``: reads ``GH_TOKEN`` and returns it unverified-by-GitHub-App-standards -- this
    is the local developer path idea.md names explicitly; there is no installation to check it
    against. Only its mere presence is required.

    ``mode="production"``: reads ``GH_APP_INSTALLATION_TOKEN`` and, if present, runs it through
    :func:`verify_installation_token` scoped to ``repository``. Absence is refused
    (``Refusal.NO_WRITE_TOKEN``) -- production never falls back to ``GH_TOKEN``.
    """
    if mode == "local":
        token = environment.get(LOCAL_TOKEN_ENV_VAR, "").strip()
        if not token:
            return _refuse(
                Refusal.NO_WRITE_TOKEN,
                f"no local write-scoped token available ({LOCAL_TOKEN_ENV_VAR} is unset or empty)",
            )
        return TokenDecision(True, token)
    token = environment.get(APP_INSTALLATION_TOKEN_ENV_VAR, "").strip()
    if not token:
        return _refuse(
            Refusal.NO_WRITE_TOKEN,
            f"no production write-scoped token available ({APP_INSTALLATION_TOKEN_ENV_VAR} is "
            f"unset or empty) - production never falls back to {LOCAL_TOKEN_ENV_VAR}",
        )
    return verify_installation_token(repository, token, fetch=fetch)


def verify_pull_request_app(
    owner: str,
    name: str,
    number: int,
    *,
    token: str,
    fetch: FetchFn = default_fetch,
    expected_app_id: int = EXPECTED_APP_ID,
    expected_app_slug: str = EXPECTED_APP_SLUG,
) -> TokenDecision:
    """Refuse unless pull request ``number`` was authored by the expected GitHub App's bot.

    Ported (ADAPT, 2026-10-23) alongside ``propose/effect.py``: what a bare installation token
    cannot prove about itself (which App minted it) is attested on the pull request it produced
    instead -- the author must be the ``Bot`` account ``<expected_app_slug>[bot]``, and that
    slug's own public App id must equal ``expected_app_id``.
    """
    try:
        author = get_pull_request_author(owner, name, number, token=token, fetch=fetch)
        app_id = get_app_id(expected_app_slug, token=token, fetch=fetch)
    except RepositoryMetadataError as exc:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, f"could not attribute pull request: {exc}")
    expected_login = f"{expected_app_slug}[bot]"
    if author is None or author[1] != "Bot" or author[0].casefold() != expected_login:
        who = "no author" if author is None else f"{author[1]} {author[0]}"
        return _refuse(
            Refusal.TOKEN_APP_MISMATCH,
            f"pull request #{number} was authored by {who}, not the expected App bot "
            f"{expected_login}",
        )
    if app_id != expected_app_id:
        return _refuse(
            Refusal.TOKEN_APP_MISMATCH,
            f"GitHub App {expected_app_slug} has id {app_id}, not the expected "
            f"{expected_app_id}",
        )
    return TokenDecision(True, token)
