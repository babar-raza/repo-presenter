"""BL-002 (owner feedback 2026-11-13, P0): a vendor-published registry package is the repository's own.

The 3D Python Lane R README told readers ``aspose-3d-foss`` "could not be confirmed on PyPI" because
PyPI's project URL names ``github.com/aspose-3d/Aspose.3D-for-Python`` (the vendor's legacy
repository) instead of ``aspose-3d-foss/Aspose.3D-FOSS-for-Python``. The package is Aspose's own:
author ``Aspose``, URL in an Aspose organization. Rule (docs/DECISION_LOG.md, BL-002): a published
distribution is the repository's own when the registry's publisher is the product vendor (derived
from the portfolio organization ``<vendor>-<product>-foss``) AND one of its project URLs points at a
vendor-owned repository or site, whatever the repository's current or legacy name.

The PyPI fixtures are the real ``pypi.org/pypi/<name>/json`` documents of 2026-11-13 (publisher and
URL fields verbatim, release lists trimmed): 3D Python (legacy repository name), Cells Python
(renamed repository), PSD Python (``products.aspose.org`` and the exact repository), and
``requests`` as the foreign negative control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.core.package_registry import (
    fact_registry_reading,
    install_verdict,
    is_vendor_publisher,
    is_vendor_url,
    vendor_of,
    vendor_owned,
)
from repo_presenter.extractors.platforms.python_registry import observe_pypi
from repo_presenter.extractors.surface.registry import _publishers, observe

FIXTURES = Path(__file__).resolve().parents[1] / "extractors" / "platforms" / "fixtures" / "pypi_bl002"
REGISTRY = Path(__file__).resolve().parents[2] / "data" / "registry.json"


def _pypi(name: str, mutate: Any = None) -> Any:
    payload = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(payload["info"])

    def fetch(url: str) -> httpx.Response:
        assert url == f"https://pypi.org/pypi/{name}/json"
        return httpx.Response(200, json=payload)

    return fetch


def _never_resolve(url: str) -> str | None:
    """No GitHub redirect is followed in a test (and none is needed for the vendor rule)."""
    return None


def _read(name: str, repository: str, version: str | None = None, mutate: Any = None):  # type: ignore[no-untyped-def]
    return observe_pypi(
        name, version, fetch=_pypi(name, mutate), repository=repository, resolve_url=_never_resolve
    )


def _verdict(observation) -> tuple[str, float, str]:  # type: ignore[no-untyped-def]
    return install_verdict(
        conclusive=observation.error is None,
        published=observation.found,
        repository_matched=observation.repository_matched,
        summary=observation.summary,
    )


@pytest.mark.parametrize(
    ("name", "repository", "version"),
    [
        # Homepage github.com/aspose-3d/Aspose.3D-for-Python: Aspose's own legacy repository.
        ("aspose-3d-foss", "aspose-3d-foss/Aspose.3D-FOSS-for-Python", "26.1.0"),
        # github.com/aspose-cells-foss/aspose-cells-python: same organization, renamed repository.
        ("aspose-cells-foss", "aspose-cells-foss/Aspose.Cells-FOSS-for-Python", "26.7.0"),
        # products.aspose.org + the exact repository; publisher only in author_email.
        ("aspose-psd-foss", "aspose-psd-foss/Aspose.PSD-FOSS-for-Python", "26.10.0"),
    ],
)
def test_a_vendor_published_pypi_package_is_the_repositorys_own(
    name: str, repository: str, version: str
) -> None:
    observation = _read(name, repository, version)
    assert observation.found and observation.repository_matched is True and observation.owned
    polarity, confidence, detail = _verdict(observation)
    assert (polarity, confidence) == ("SUPPORTED", 1.0)
    assert detail == "package registry: found; manifest version published"


def test_the_3d_python_case_is_supported_end_to_end_through_the_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact BL-002 shape through ``PythonPlugin.registry_facts``: SUPPORTED, so the renderer
    prints the published install and never the "could not be confirmed" sentence."""
    from repo_presenter.extractors.platforms import python as plugin_module

    repository = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    monkeypatch.setattr(
        plugin_module,
        "observe_pypi",
        lambda name, version, repository: _read(name, repository, version),
    )
    facts = [
        Fact("install_command:pip", "install_command", "pip install aspose-3d-foss",
             (Evidence("setup.py", "distribution name declared by the manifest"),)),
        Fact("package:name", "package", "aspose-3d-foss",
             (Evidence("setup.py", "distribution name declared by the manifest"),)),
        Fact("package:version", "package", "26.1.0", (Evidence("setup.py", "version"),)),
        Fact("identity:repository", "identity", repository, (Evidence("git", "origin"),)),
    ]
    [resolved], _ = plugin_module.PythonPlugin().registry_facts(facts)
    assert resolved.polarity == "SUPPORTED"
    assert fact_registry_reading(resolved) == "published"


def test_a_foreign_package_stays_unconfirmed() -> None:
    """Negative control: ``requests`` (publisher Kenneth Reitz, source github.com/psf/requests)
    asked for an Aspose repository is another project's package."""
    observation = _read("requests", "aspose-3d-foss/Aspose.3D-FOSS-for-Python")
    assert observation.found and observation.repository_matched is False
    polarity, _confidence, detail = _verdict(observation)
    assert polarity == "UNRESOLVED" and "ownership not confirmed" in detail


@pytest.mark.parametrize(
    "mutate",
    [
        # Aspose's URL, someone else's upload: the publisher is not the vendor.
        lambda info: info.update(author="Mallory Squatter", author_email="m@example.net"),
        # Aspose's name on the upload, but the source is a stranger's repository.
        lambda info: info.update(
            home_page="https://github.com/mallory/aspose-3d-foss",
            project_urls={"Homepage": "https://github.com/mallory/aspose-3d-foss"},
        ),
        # A look-alike organization and a look-alike site are not the vendor's.
        lambda info: info.update(
            home_page="https://github.com/asposefan/Aspose.3D-for-Python",
            project_urls={"Homepage": "https://aspose.com.example.net/3d"},
        ),
    ],
)
def test_vendor_ownership_needs_both_the_vendor_publisher_and_a_vendor_url(mutate: Any) -> None:
    observation = _read("aspose-3d-foss", "aspose-3d-foss/Aspose.3D-FOSS-for-Python", mutate=mutate)
    assert observation.found and observation.repository_matched is False
    assert _verdict(observation)[0] == "UNRESOLVED"


def test_a_repository_outside_the_vendor_organizations_gets_no_vendor_rule() -> None:
    """The vendor is derived from the portfolio organization; any other owner has none, so the
    Aspose package is not claimed for it."""
    observation = _read("aspose-3d-foss", "someone/Aspose.3D-FOSS-for-Python")
    assert observation.repository_matched is False


def test_the_vendor_of_every_registered_repository_is_derived_not_hardcoded() -> None:
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["entries"]
    assert entries and {vendor_of(entry["repository"]) for entry in entries} == {"aspose"}
    assert vendor_of("acme-widgets-foss/Widgets-for-Python") == "acme"
    assert vendor_of("psf/requests") is None and vendor_of(None) is None


@pytest.mark.parametrize(
    ("url", "owned"),
    [
        ("https://github.com/aspose-3d/Aspose.3D-for-Python", True),
        ("https://GitHub.com/ASPOSE-CELLS-FOSS/aspose-cells-python.git", True),
        ("git+ssh://git@github.com/aspose-words-foss/x.git", True),
        ("git@github.com:aspose-3d/Aspose.3D-for-Java.git", True),
        ("https://github.com/aspose/aspose-sdk", True),
        ("https://products.aspose.org/psd/", True),
        ("https://www.aspose.com/", True),
        ("https://docs.aspose.com/3d/python/", True),
        ("github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go", True),
        ("https://github.com/asposefan/x", False),
        ("https://github.com/someone/aspose-3d", False),
        ("https://aspose.com.example.net/x", False),
        ("https://notaspose.com/", False),
        ("https://pypi.org/project/aspose-psd-foss/", False),
        ("", False),
    ],
)
def test_vendor_urls(url: str, owned: bool) -> None:
    assert is_vendor_url(url, "aspose") is owned


def test_vendor_publishers() -> None:
    assert is_vendor_publisher(["Aspose"], "aspose")
    assert is_vendor_publisher(["Aspose Pty <sales@aspose.com>, Aspose PSD Team <psd@aspose.com>"], "aspose")
    assert is_vendor_publisher(["https://aspose.com"], "aspose")  # a Maven group's domain
    assert not is_vendor_publisher(["Asposeish Ltd"], "aspose")
    assert not is_vendor_publisher(["Aspose Fan <fan@gmail.com>"], "aspose")
    assert not is_vendor_publisher(["Kenneth Reitz <me@kennethreitz.org>"], "aspose")
    assert not is_vendor_publisher([], "aspose")


def test_the_other_registries_publishers_and_the_same_rule() -> None:
    """NuGet authors, npm maintainer, Maven group domain and Go module path are the publisher the
    same rule reads; crates.io's crate id is the crate's name, never a publisher."""
    assert _publishers("nuget", "Aspose.3D.FOSS", {"verified_owner": "Aspose"}) == ("Aspose",)
    assert _publishers("maven", "com.aspose:aspose-3d-foss", {}) == ("https://aspose.com",)
    assert _publishers("cargo", "aspose-cells-foss", {"verified_owner": "aspose-cells-foss"}) == ()
    go = "github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go"
    assert vendor_owned([f"https://{go}"], _publishers("go_modules", go, {}), "aspose-pdf-foss/x")
    # A NuGet package Aspose publishes from its legacy repository: the vendor's own.
    assert vendor_owned(
        ["https://github.com/aspose-3d/Aspose.3D-for-.NET"], ["Aspose"],
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    )
    # A Maven artifact in a stranger's group: never the vendor's, whatever its URLs say.
    assert not vendor_owned(
        ["https://github.com/aspose-3d/x"], _publishers("maven", "io.github.mallory:x", {}),
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
    )
    # A crate gets no vendor rule at all (no publisher): only the exact repository match counts.
    assert not vendor_owned(
        ["https://github.com/aspose-cells-foss/x"], _publishers("cargo", "x", {"verified_owner": "x"}),
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    )


def test_a_foreign_npm_package_stays_unconfirmed_through_observe() -> None:
    """Negative control through the shared surface observer: ``left-pad`` (maintainer stevemao,
    source github.com/stevemao/left-pad) asked for an Aspose repository."""

    class _Body:
        def __init__(self, text: str, status: int = 200) -> None:
            self.status_code = status
            self.body = text.encode("utf-8")

    fixture = Path(__file__).resolve().parents[1] / "extractors" / "surface" / "fixtures" / "registry"
    text = (fixture / "npm-left-pad.json").read_text(encoding="utf-8")

    def fetch(url: str, **_kwargs: Any) -> _Body:
        return _Body(text) if url.endswith("registry.npmjs.org/left-pad") else _Body("", 404)

    reading = observe(
        "typescript", "left-pad", repository="aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
        fetch=fetch, sleep=lambda _s: None, resolve_url=_never_resolve,
    )
    assert reading.published and reading.repository_matched is False and not reading.owned
