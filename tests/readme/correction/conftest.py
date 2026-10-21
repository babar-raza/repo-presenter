"""Synthetic facts and READMEs for the correction path's tests: no network, no clone, no registry.

Adapted from the old repository's ``tests/components/readme_correction/conftest.py``: the real
``entry_for`` there loads ``data/registry.json`` through ``core.registry.loader`` (not ported in
this repository -- see ``migration/reuse-manifest.yaml``); here ``entry_for`` just builds the
documented ``RegistryEntryStub`` placeholder instead, since none of the detectors ported so far
read any attribute of ``Context.entry``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry_entry_stub import RegistryEntryStub
from repo_presenter.readme.correction.model import Context

JAVA_REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
REVISION = "a" * 40


def fact(
    fact_id: str,
    value: str,
    *,
    polarity: str = "SUPPORTED",
    evidence: Iterable[tuple[str, str | None]] = (("pom.xml", None),),
    attributes: dict[str, str] | None = None,
) -> Fact:
    kind = fact_id.split(":", 1)[0]
    return Fact(
        id=fact_id,
        kind=kind,  # type: ignore[arg-type]
        value=value,
        evidence=tuple(Evidence(path, detail) for path, detail in evidence),
        polarity=polarity,  # type: ignore[arg-type]
        attributes=attributes,
    )


def base_facts(*extra: Fact, drop: Iterable[str] = ()) -> list[Fact]:
    """A published, MIT-licensed Java package; ``extra`` facts add to or replace (by id) the base
    ones, ``drop`` removes ids."""
    facts = [
        fact("identity:repository", JAVA_REPOSITORY),
        fact("identity:revision", REVISION, evidence=(("source/snapshot.json", None),)),
        fact("package:name", "org.aspose:aspose-3d-foss"),
        fact("package:version", "26.8.0"),
        fact(
            "package:published_version", "26.7.0", evidence=(("https://repo1.maven.org/x", None),)
        ),
        fact(
            "install_command:maven",
            "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
            attributes={"install_kind": "registry"},
            evidence=(("pom.xml", None), ("https://repo1.maven.org/x", "package registry: found")),
        ),
        fact("license:spdx", "MIT", evidence=(("LICENSE", "license text states this license"),)),
        fact("license:file", "LICENSE", evidence=(("LICENSE", None),)),
        fact("dependency:none", "none", evidence=(("pom.xml", "the manifest declares none"),)),
        fact(
            "build_test_asset:tests",
            "src/test/",
            evidence=(("src/test/", "3 files; test suite"),),
        ),
    ]
    by_id = {f.id: f for f in facts}
    for replacement in extra:
        by_id[replacement.id] = replacement
    for fact_id in drop:
        by_id.pop(fact_id, None)
    return list(by_id.values())


def entry_for(repository: str = JAVA_REPOSITORY) -> RegistryEntryStub:
    owner, _, name = repository.partition("/")
    return RegistryEntryStub(repository=repository, family=name, platform="", ecosystem="java")


def context(
    readme: str,
    facts: Iterable[Fact] | None = None,
    tree: Iterable[str] = ("README.md", "LICENSE", "pom.xml"),
    repository: str = JAVA_REPOSITORY,
) -> Context:
    document = FactsDocument(repository, REVISION, tuple(facts or base_facts()))
    return Context(entry_for(repository), document, readme, tuple(tree))


@pytest.fixture
def make_fact() -> Any:
    return fact


@pytest.fixture
def make_facts() -> Any:
    return base_facts


@pytest.fixture
def make_context() -> Any:
    return context
