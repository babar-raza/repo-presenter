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
    ``test_a_repository_outside_the_allow_list_is_refused_before_any_work`` to fail only in
    hosted CI. Deleted by default; a test that wants the real hosted refusal sets it back
    explicitly with its own ``monkeypatch.setenv``."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


@pytest.fixture(autouse=True)
def no_ambient_llm_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-06: the cloud environment now sets ``GPT_OSS_STREAMING=1`` (the gateway's ~30 s idle
    cutoff fix), and ``core/llm/jobs.py`` reads it to stream replies. The suite's fake transports
    answer the plain request shape, so the ambient value broke 130 tests in such a session while
    hosted CI (which does not set it) passed. Deleted by default; a streaming test sets it itself."""
    monkeypatch.delenv("GPT_OSS_STREAMING", raising=False)


@pytest.fixture(autouse=True)
def no_ambient_github_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-04 (P0 follow-up directive section 3, second real hosted-CI-only failure, found
    AFTER the GITHUB_ACTIONS fix above did not actually resolve it): the real hosted runner also
    sets ``GITHUB_RUN_ID`` to one fixed value for the whole job -- including the job running
    this suite. ``present.py``'s ``--workflow-run-id`` defaults to
    ``os.environ.get("GITHUB_RUN_ID")``, so any test that calls ``present.main()`` more than
    once without passing ``--workflow-run-id`` explicitly (``tests/test_lane_l_hosted.py``'s
    ``Hosted`` helper does exactly this) gets the SAME run id for both calls on a hosted
    runner, which ``admit_trigger``'s workflow_dispatch dedup key treats as the same trigger --
    deduplicating the second call into the first's in-flight transaction and silently running
    nothing. Locally this env var is simply absent, so each call falls back to a fresh
    ``uuid4().hex`` and never collides -- which is exactly why this only reproduced in real
    hosted CI (run 41832146529) and not in any local run. Deleted by default, matching every
    other test that cares about workflow_run_id semantics, which already passes it explicitly."""
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
