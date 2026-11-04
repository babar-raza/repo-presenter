import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.extractors.platforms import cpp
from repo_presenter.extractors.surface.registry import observe
from repo_presenter.readme.evidence.facts import links, published_version


@pytest.fixture(scope="session", autouse=True)
def read_no_registry_for_the_published_version() -> Iterator[None]:
    """The published-version fact asks every registry through `surface.registry.observe`.
    Offline, the reading is "could not read" without a request, so no fact is emitted; a test
    that needs a reading patches `published_version._observe` itself."""
    with pytest.MonkeyPatch.context() as patch:
        offline = lambda ecosystem, name, **_: observe(ecosystem, name, offline=True)
        patch.setattr(published_version, "_observe", offline)
        patch.setattr(cpp, "_observe", offline)
        yield


@pytest.fixture(autouse=True)
def no_link_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test reaches a link target or a product page; a test that needs one injects its own."""

    def refuse(url: str, transport: object = None) -> object:
        raise RuntimeError(f"network is disabled in tests: {url}")

    monkeypatch.setattr(links, "fetch_status", refuse)


@pytest.fixture(autouse=True)
def no_ambient_github_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-04 (follow-up directive §3): the real GitHub-hosted CI runner sets
    ``GITHUB_ACTIONS=true`` for every job, including the job that runs this very test suite.
    ``present.py`` reads that variable to refuse the dangerous combined stage on a hosted
    runner (a real, deliberate safety property, with its own explicit test). Without this
    fixture, that ambient value leaks into any test that calls ``present.main()`` without
    picking a non-default ``--stage``, making the test's outcome depend on where the SUITE
    happens to run rather than on the product behavior under test -- this caused
    ``test_a_repository_outside_the_allow_list_is_refused_before_any_work`` and a Lane L hosted
    test to fail only in hosted CI. Deleted by default; a test that wants the real hosted
    refusal sets it back explicitly with its own ``monkeypatch.setenv``."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
