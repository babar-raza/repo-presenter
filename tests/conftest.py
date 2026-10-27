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
