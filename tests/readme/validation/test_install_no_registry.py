"""BC-02 and an UNRESOLVED source build of a registry-less ecosystem (Aspose.Email-FOSS-for-Cpp).

Real data: the ``install_command:cmake`` fact is copied from the hosted Lane R run. The library header
fails under g++ 13, so ``no build exited 0: not attempted`` and the fact is UNRESOLVED. The README prints
none of that fact's commands (its Installation section is the maintainers' own preset build), so it
claims nothing and BC-02 must not fail on it; a README that prints the unproved command still fails, at
the line that prints it, in a stage the repair loop can reach.
"""

from __future__ import annotations

import hashlib

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.install import install_failures

REPOSITORY = "aspose-email-foss/Aspose.Email-FOSS-for-Cpp"
CMAKE = Fact(
    "install_command:cmake",
    "install_command",
    "cmake -S . -B build\ncmake --build build",
    (
        Evidence(
            "CMakeLists.txt",
            "source build for the CMake project the manifest declares; C++ has no package registry to install from",
        ),
        Evidence("no package registry", "package registry: none could not be read"),
    ),
    polarity="UNRESOLVED",
    confidence=0.5,
    attributes={"source_checkout_unverified": "no build exited 0: not attempted"},
)

PRESET_INSTALLATION = """## Installation

Build it from source with CMake.

```powershell
cmake --preset default
cmake --build --preset default
```
"""

PRINTS_THE_UNPROVED_BUILD = """## Installation

Build it from source with CMake.

```bash
cmake -S . -B build
cmake --build build
```
"""


def _candidate(readme: str, fact: Fact = CMAKE) -> Candidate:
    entry = RegistryEntry.model_validate(
        {
            "repository": REPOSITORY,
            "family": "email",
            "platform": "cpp",
            "ecosystem": "cpp",
            "mode": "dry_run",
            "policy_profile": "aspose-email-foss-cpp",
            "active": True,
            "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_x"},
        }
    )
    facts = FactsDocument(REPOSITORY, "0" * 40, (fact,))
    return Candidate(
        entry, facts, {}, {"units": []}, {"dispositions": []}, readme, b"# x\n", "0" * 40,
        hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )


def _about(failures: list, fact_id: str = "install_command:cmake") -> list:
    return [f for f in failures if fact_id in f.detail]


def test_unresolved_source_build_with_no_command_printed_claims_nothing() -> None:
    assert install_failures(_candidate(PRESET_INSTALLATION)) == []
    # No distribution fact is needed either: the README simply states no install claim.
    assert install_failures(_candidate("## Installation\n\nSee the documentation.\n")) == []


def test_printed_unproved_build_fails_at_the_section_that_prints_it() -> None:
    failures = _about(install_failures(_candidate(PRINTS_THE_UNPROVED_BUILD)))
    assert {f.stage for f in failures} == {"COMPOSING"}
    assert len(failures) == 2  # one per printed line
    assert any("cmake --build build" in f.detail for f in failures)
    assert all("no build exited 0: not attempted" in f.detail for f in failures)
    assert all(str(f.section).lower().startswith("install") for f in failures)


def test_a_printed_command_in_an_inline_span_is_also_a_claim() -> None:
    readme = "## Installation\n\nRun `cmake --build build` to build it.\n"
    assert len(_about(install_failures(_candidate(readme)))) == 1


def test_contradicted_registryless_install_still_fails_at_extracting() -> None:
    contradicted = Fact(
        CMAKE.id, CMAKE.kind, CMAKE.value, CMAKE.evidence, polarity="CONTRADICTED",
        confidence=0.5, attributes=CMAKE.attributes,
    )
    failures = install_failures(_candidate(PRESET_INSTALLATION, contradicted))
    assert failures and failures[0].stage == "EXTRACTING"
    assert "NO_REGISTRY" in failures[0].detail


def test_unresolved_unreadable_registry_still_fails_even_with_no_command_printed() -> None:
    unreadable = Fact(
        CMAKE.id, CMAKE.kind, CMAKE.value,
        (CMAKE.evidence[0], Evidence("https://example.org", "package registry could not be read: timeout")),
        polarity="UNRESOLVED", confidence=0.5,
    )
    failures = install_failures(_candidate(PRESET_INSTALLATION, unreadable))
    assert failures and failures[0].stage == "EXTRACTING"
