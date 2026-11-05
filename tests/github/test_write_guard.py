"""Owner directive 2026-11-04: only babar-raza/repo-presenter may be written. The three real HTTP
write primitives must refuse every other target BEFORE any request is made (httpx is patched to
fail the test if reached)."""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.github import client
from repo_presenter.github.client import (
    API_ROOT,
    UpstreamWriteForbiddenError,
    assert_write_allowed,
    default_patch,
    default_post,
    default_put,
)

ALLOWED = f"{API_ROOT}/repos/babar-raza/repo-presenter/issues"
FORBIDDEN = [
    f"{API_ROOT}/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues",
    f"{API_ROOT}/repos/babar-raza/repository-presenter/issues",
    f"{API_ROOT}/repos/babar-raza/repo-presenter-evil/issues",
    f"{API_ROOT}/repos/babar-raza/repo-presenter%2Fx/issues",
    f"{API_ROOT}/repos/babar-raza/other/pulls/1",
    f"{API_ROOT}/orgs/aspose-3d-foss/repos",
    f"{API_ROOT}/repos/babar-raza",
    "https://evil.example/repos/babar-raza/repo-presenter/issues",
    "http://api.github.com/repos/babar-raza/repo-presenter/issues",
    f"{API_ROOT}.evil.example/repos/babar-raza/repo-presenter/issues",
    "",
]


@pytest.mark.parametrize("url", FORBIDDEN)
def test_every_other_target_is_refused(url: str) -> None:
    with pytest.raises(UpstreamWriteForbiddenError):
        assert_write_allowed(url)


def test_the_allowed_repository_passes_case_insensitively() -> None:
    assert_write_allowed(ALLOWED)
    assert_write_allowed(f"{API_ROOT}/repos/Babar-Raza/Repo-Presenter/pulls/2")


@pytest.mark.parametrize("writer", [default_post, default_patch, default_put])
@pytest.mark.parametrize("url", FORBIDDEN[:3])
def test_real_writers_refuse_before_any_request(
    writer: Any, url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("an HTTP request was attempted for a forbidden target")

    for verb in ("post", "patch", "put"):
        monkeypatch.setattr(client.httpx, verb, boom)
    with pytest.raises(UpstreamWriteForbiddenError):
        writer(url, "token", {})


@pytest.mark.parametrize(
    ("writer", "verb"), [(default_post, "post"), (default_patch, "patch"), (default_put, "put")]
)
def test_real_writers_still_reach_the_allowed_repository(
    writer: Any, verb: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    class _Response:
        status_code = 201

        def json(self) -> Any:
            return {}

    def fake(url: str, **k: Any) -> _Response:
        seen.append(url)
        return _Response()

    monkeypatch.setattr(client.httpx, verb, fake)
    assert writer(ALLOWED, "token", {})[0] == 201
    assert seen == [ALLOWED]


def test_no_environment_override_exists() -> None:
    import inspect

    source = inspect.getsource(client.assert_write_allowed)
    assert "environ" not in source and "getenv" not in source
