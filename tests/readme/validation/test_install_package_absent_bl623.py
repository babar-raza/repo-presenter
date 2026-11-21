"""BL-623: BC-02 and a registry install of a package the registry itself lists as not published, when no
documented source install replaced the fact (Aspose.GIS-FOSS-for-.Net: the repository has no README and its
build does not exit 0; hosted Lane R run 44924694275: "install_command:dotnet is CONTRADICTED: package registry:
distribution not found on nuget; PACKAGE_ABSENT ..." at EXTRACTING, which no repair stage can change, so the
candidate failed before any review whatever the README said). The registry's answer is true and the renderer
states it plainly; the fact is a claim only where the README prints its command (COMPOSING / RECONCILING, which
the repair stages reach), exactly like the unconfirmed-ownership and registry-less classes.
Negative controls: a printed registry command still blocks; an unreadable registry still blocks at EXTRACTING."""

from __future__ import annotations

import hashlib

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.install import install_failures

REPOSITORY = "aspose-gis-foss/Aspose.GIS.FOSS-for-.Net"
ABSENT = "package registry: distribution not found on nuget"


def _install(reading: str = ABSENT, polarity: str = "CONTRADICTED") -> Fact:
    return Fact(
        "install_command:dotnet", "install_command", "dotnet add package Aspose.GIS.FOSS",
        (
            Evidence("Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj", "distribution name declared by the manifest"),
            Evidence("https://api.nuget.org/v3-flatcontainer/aspose.gis.foss/index.json", reading),
        ),
        polarity=polarity, confidence=0.0,
    )


PACKAGE = Fact("package:name", "package", "Aspose.GIS.FOSS", (Evidence("Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj"),))
PLAIN = "## Installation\n\n`Aspose.GIS.FOSS` is not yet published on NuGet.\n"
PRINTED = PLAIN + "\n```bash\ndotnet add package Aspose.GIS.FOSS\n```\n"


def _candidate(readme: str, install: Fact) -> Candidate:
    entry = RegistryEntry.model_validate(
        {
            "repository": REPOSITORY, "family": "gis", "platform": "net", "ecosystem": "net", "mode": "dry_run",
            "policy_profile": "aspose-gis-foss-net", "active": True,
            "provider_identity": {"provider": "github", "repository_id": 1381084812, "node_id": "R_x"},
        }
    )
    facts = FactsDocument(REPOSITORY, "0" * 40, (install, PACKAGE))
    return Candidate(
        entry, facts, {}, {"units": []}, {"dispositions": []}, readme, b"# x\n", "0" * 40,
        hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )


def _bc02(readme: str, install: Fact) -> list:
    return [f for f in install_failures(_candidate(readme, install)) if "install_command:dotnet" in f.detail]


def test_a_readme_that_states_the_package_is_unpublished_and_prints_no_command_passes() -> None:
    assert _bc02(PLAIN, _install()) == []


def test_a_printed_registry_command_fails_at_the_line_that_prints_it() -> None:
    (failure,) = _bc02(PRINTED, _install())
    assert failure.stage == "COMPOSING"
    assert "dotnet add package Aspose.GIS.FOSS" in failure.detail and "not published" in failure.detail


def test_an_unreadable_registry_or_a_supported_source_fact_is_unchanged() -> None:
    unreadable = _install("package registry could not be read: timeout", "UNRESOLVED")
    failures = _bc02(PLAIN, unreadable)
    assert failures and failures[0].stage == "EXTRACTING"
