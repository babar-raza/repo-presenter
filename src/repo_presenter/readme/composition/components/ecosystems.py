"""Per-ecosystem presentation knowledge the shell rows rely on: prose vocabulary only.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/components/ecosystems.py`` per migration/reuse-manifest.yaml
("readme/composition/" entry).
"""

from __future__ import annotations

from collections.abc import Iterable

REGISTRY_NAMES: dict[str, str] = {
    "python": "PyPI",
    "java": "Maven Central",
    "dotnet": "NuGet",
    "node": "npm",
    "rust": "crates.io",
    "go": "pkg.go.dev",
}
DISTRIBUTION_REGISTRY_NAMES: dict[str, str] = {"nuget": "NuGet"}
HOST_NAMES: dict[str, str] = {
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "bitbucket.org": "Bitbucket",
}


def host_names(values: Iterable[str]) -> frozenset[str]:
    """The display names of the hosting sites the given fact values link to."""
    return frozenset(
        name for host, name in HOST_NAMES.items() if any(host in value for value in values)
    )
