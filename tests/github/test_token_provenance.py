"""Ported (trimmed) from the old repo's tests/core/github/test_token_provenance.py, plus new tests
for this repository's own local-vs-production ``resolve_write_token`` split.

``verify_pull_request_app``'s own tests, ported 2026-10-23 alongside ``propose/effect.py``, were
added below -- they pin the current EXPECTED_APP_ID/SLUG placeholders (inherited from the old
repo's own registered App, not yet confirmed as this repository's own; see token_provenance.py's
own docstring), so they will need updating the day those constants are replaced with this
repository's real App identity."""

from __future__ import annotations

from typing import Any

from repo_presenter.authorization.refusals import Refusal
from repo_presenter.github.token_provenance import (
    APP_INSTALLATION_TOKEN_ENV_VAR,
    EXPECTED_APP_ID,
    LOCAL_TOKEN_ENV_VAR,
    resolve_write_token,
    verify_installation_token,
    verify_pull_request_app,
)

TARGET = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
INSTALLATION_TOKEN = "ghs_installationtokenfortestsonly"


def _repos(*names: str) -> dict[str, Any]:
    return {
        "total_count": len(names),
        "repositories": [{"full_name": name} for name in names],
    }


def _fetch(status: int, body: Any, seen: list[str] | None = None):  # type: ignore[no-untyped-def]
    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        if seen is not None:
            seen.append(url)
        return status, body

    return fetch


def test_an_installation_token_scoped_to_exactly_the_target_is_accepted() -> None:
    seen: list[str] = []
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET), seen)
    )
    assert decision.ok is True
    assert decision.code is None
    assert seen and "/installation/repositories" in seen[0]


def test_the_scope_comparison_ignores_case() -> None:
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET.lower()))
    )
    assert decision.ok is True


def test_a_personal_access_token_is_refused_without_any_request() -> None:
    for pat in ("ghp_hand_set_pat", "github_pat_11AAAA", "gho_oauth", "ghu_user", "plain-secret"):
        seen: list[str] = []
        decision = verify_installation_token(TARGET, pat, fetch=_fetch(200, _repos(TARGET), seen))
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_NOT_INSTALLATION
        assert seen == []  # refused on the prefix alone; the token was never sent anywhere


def test_an_installation_token_reaching_more_than_the_target_is_refused() -> None:
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET, "other/repo"))
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_WRONG_SCOPE


# ---------------------------------------------------------------------------
# resolve_write_token: this repository's own local-vs-production split.
# ---------------------------------------------------------------------------


def test_local_mode_accepts_a_plain_gh_token_unverified() -> None:
    decision = resolve_write_token(
        {LOCAL_TOKEN_ENV_VAR: "ghp_real_local_pat"}, repository=TARGET, mode="local"
    )
    assert decision.ok is True
    assert decision.token == "ghp_real_local_pat"


def test_local_mode_fails_closed_without_gh_token() -> None:
    decision = resolve_write_token({}, repository=TARGET, mode="local")
    assert decision.ok is False
    assert decision.code is Refusal.NO_WRITE_TOKEN


def test_production_mode_fails_closed_without_app_credentials_even_if_gh_token_is_set() -> None:
    """The exact idea.md guarantee this pull is asked to keep intact: production never falls back
    to the local GITHUB_TOKEN."""
    decision = resolve_write_token(
        {LOCAL_TOKEN_ENV_VAR: "ghp_a_local_token_is_not_enough"},
        repository=TARGET,
        mode="production",
    )
    assert decision.ok is False
    assert decision.code is Refusal.NO_WRITE_TOKEN


def test_production_mode_verifies_the_app_installation_token_it_is_given() -> None:
    decision = resolve_write_token(
        {APP_INSTALLATION_TOKEN_ENV_VAR: INSTALLATION_TOKEN},
        repository=TARGET,
        mode="production",
        fetch=_fetch(200, _repos(TARGET)),
    )
    assert decision.ok is True
    assert decision.token == INSTALLATION_TOKEN


def test_production_mode_refuses_a_hand_set_pat_passed_as_the_app_token() -> None:
    decision = resolve_write_token(
        {APP_INSTALLATION_TOKEN_ENV_VAR: "ghp_not_an_installation_token"},
        repository=TARGET,
        mode="production",
        fetch=_fetch(200, _repos(TARGET)),
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_NOT_INSTALLATION


# ---------------------------------------------------------------------------
# verify_pull_request_app: what a bare installation token cannot prove about itself
# (which App minted it) is attested on the pull request it produced instead.
# ---------------------------------------------------------------------------


def _router(pr: dict[str, Any], app: dict[str, Any] | None = None) -> Any:
    """Answer ``/issues/N`` with ``pr`` and ``/apps/<slug>`` with ``app`` (200 each)."""
    app_body = {"id": EXPECTED_APP_ID, "slug": "repository-presenter"} if app is None else app

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return (200, app_body) if "/apps/" in url else (200, pr)

    return fetch


_BOT = {"login": "repository-presenter[bot]", "type": "Bot"}


def test_a_pull_request_authored_by_the_expected_app_bot_is_accepted() -> None:
    # The live shape (old repo, run 38883943550, presenter-sandbox#1): the App's bot is the
    # author and performed_via_github_app is null - the very case a naive check would refuse.
    pr = {"user": _BOT, "performed_via_github_app": None}
    decision = verify_pull_request_app("o", "n", 4, token=INSTALLATION_TOKEN, fetch=_router(pr))
    assert decision.ok is True


def test_a_pull_request_from_another_author_is_refused() -> None:
    for user in (
        {"login": "someone-else[bot]", "type": "Bot"},
        {"login": "repository-presenter", "type": "User"},
        {"login": "someone", "type": "User"},
        None,
    ):
        decision = verify_pull_request_app(
            "o", "n", 4, token=INSTALLATION_TOKEN, fetch=_router({"user": user})
        )
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_APP_MISMATCH


def test_a_slug_that_resolves_to_a_different_app_id_is_refused() -> None:
    decision = verify_pull_request_app(
        "o",
        "n",
        4,
        token=INSTALLATION_TOKEN,
        fetch=_router({"user": _BOT}, {"id": 15368, "slug": "repository-presenter"}),
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_APP_MISMATCH


def test_an_unreadable_pull_request_is_unverifiable() -> None:
    decision = verify_pull_request_app(
        "o", "n", 4, token=INSTALLATION_TOKEN, fetch=_fetch(404, {"message": "Not Found"})
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_UNVERIFIABLE
