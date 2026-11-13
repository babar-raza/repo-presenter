"""``Directory.Build.props`` alone is not a root a ``dotnet build`` can start from."""

from __future__ import annotations

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.readme.evidence.facts.extract import _has_root_manifest


def test_directory_build_props_alone_is_not_a_build_entry() -> None:
    net = spec_for("net")
    assert not _has_root_manifest(net, ["Directory.Build.props", "src/A/A.csproj", "README.md"])


def test_a_root_project_file_still_is() -> None:
    net = spec_for("net")
    assert _has_root_manifest(net, ["Directory.Build.props", "A.csproj"])
