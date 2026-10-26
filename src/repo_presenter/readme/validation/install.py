"""BC-02: the install command the README prints is verified against the facts that admit it.

ADAPT (import paths, public names) from the old repository-presenter project's
``components/readme/validation/registry.py``: ``_check_install`` and its helpers, and
``_check_source_checkout`` (TC-TST-01). The judgments read the install facts that extraction
(``readme/evidence/facts/commands.py``, ``core/package_registry.py``) already records; the
documented source-build re-derivation is ``readme/evidence/facts/unpublished.documented_steps``.
"""

from __future__ import annotations

import re

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.facts import (
    DOCUMENTED_COMMAND_ATTRIBUTE,
    DOCUMENTED_SOURCE_BASIS,
    NOT_PUBLISHED,
    REGISTRY_COMMAND_ATTRIBUTE,
    REGISTRY_STATE_ATTRIBUTE,
    SOURCE_BASIS_ATTRIBUTE,
    SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE,
    Fact,
)
from repo_presenter.core.package_registry import (
    DISTRIBUTION_FACT_PREFIX,
    RETRYABLE_READINGS,
    fact_registry_reading,
)
from repo_presenter.readme.evidence.facts.unpublished import (
    DOCUMENTED_BUILD_PHRASE,
    README_STATEMENT_PHRASE,
    documented_steps,
)
from repo_presenter.readme.validation.failures import Candidate, Failure
from repo_presenter.readme.validation.text import COMMAND, section_lines
from repo_presenter.readme.validation.units import placements_of

# The install kinds a verified build or checkout justifies (`extract.py`'s source tiers), never a
# registry command.
SOURCE_KINDS = frozenset({"source", "source_checkout"})
# A line that installs a package from a registry: a package tool, an install/add/get verb or a
# Maven artifact coordinate, and the package's own name.
REGISTRY_INSTALL_VERB = re.compile(
    r"(?i)\b(?:install|add|get|i)\b|dependency:get|-Dartifact="
)


def install_failures(candidate: Candidate) -> list[Failure]:
    """BC-02: every install fact is SUPPORTED on evidence that admits it, a registry-kind install
    is never SUPPORTED on a registry that found no distribution, a source build states only the
    steps its receipt proved, and no README line prints a registry install of an unpublished
    package."""
    installs = candidate.facts.by_kind("install_command")
    if not installs:
        return [
            Failure(
                "EXTRACTING",
                "no install command fact; the source install is not verified at this revision",
            )
        ]
    failures: list[Failure] = []
    for fact in installs:
        details = " ".join(evidence.detail or "" for evidence in fact.evidence)
        proved = (fact.attributes or {}).get("build_command", "")
        checkout_kind = (fact.attributes or {}).get("install_kind") == "source_checkout"
        if fact.polarity != "SUPPORTED":
            if not _stated_by_distribution(candidate, fact):
                failures.append(Failure("EXTRACTING", _unestablished_install(fact)))
        elif problems := _documented_source_failures(candidate, fact):
            failures.extend(problems)
        elif (fact.attributes or {}).get("install_kind") not in SOURCE_KINDS and (
            "distribution not found" in details
        ):
            # A registry-kind install that is SUPPORTED while its own registry reading found no
            # distribution is the unverified command a 404 contradicts, however its wording reads.
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact.id} is SUPPORTED on a registry reading that found no distribution; "
                    "an unpublished package is stated plainly, never as an install command",
                )
            )
        elif "manifest" not in details or (
            "package registry" not in details
            and "verified source build" not in details
            and not checkout_kind
        ):
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact.id} lacks manifest, package-registry, or source-build evidence: "
                    f"{details}",
                )
            )
        elif proved and not (
            fact.value == proved or fact.value.endswith("\n" + proved)
        ):
            # The receipt names the exact steps the verifier proved for this repository; the
            # command a reader is told to run ends with those and no other.
            tail = "\n".join(fact.value.splitlines()[-(len(proved.splitlines()) + 1) :])
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact.id} advertises build steps its receipt did not prove: the receipt "
                    f"names {proved!r}, the command ends {tail!r}",
                )
            )
        elif f"```bash\n{fact.value}\n```" not in candidate.readme:
            failures.append(
                Failure(
                    "COMPOSING",
                    f"the Installation section does not render {fact.value!r}",
                )
            )
    failures.extend(_registry_command_failures(candidate))
    failures.extend(_check_source_checkout(candidate))
    return failures


def _stated_by_distribution(candidate: Candidate, fact: Fact) -> bool:
    """Whether a registry-less install nothing proved is simply not what the README claims.

    A C++ library has no registry, so its CMake source build stays UNRESOLVED unless a build
    exited 0. When a registry confirmed the package the README names (``package:distribution.*``)
    the Installation row states that distribution, prints no command, and the UNRESOLVED fact is
    not a claim anyone reads. It becomes a claim the moment the README prints its command.
    """
    distributions = [
        f.value
        for f in candidate.facts.facts
        if f.id.startswith(DISTRIBUTION_FACT_PREFIX) and f.polarity == "SUPPORTED"
    ]
    return (
        fact.polarity == "UNRESOLVED"
        and fact_registry_reading(fact) == "no_registry"
        and any(f"`{value}`" in candidate.readme for value in distributions)
        and f"```bash\n{fact.value}\n```" not in candidate.readme
    )


def _unestablished_install(fact: Fact) -> str:
    """Why a non-SUPPORTED install fact refuses the candidate, naming the class of the registry
    reading behind it. The classes call for different responses, so the sentence says which this is.

    ``RETRY_REGISTRY_READ``: the registry gave no answer, which says nothing about the package -
    extract again, and never repair a README for it. ``PACKAGE_ABSENT``: the registry's own answer
    is that nothing is published, a true statement that becomes a source install only when the
    maintainers' README says so and the repository documents a build. ``NO_REGISTRY``: the
    ecosystem has no registry to ask, so the install is a source build.
    """
    last = fact.evidence[-1].detail or "" if fact.evidence else ""
    base = f"{fact.id} is {fact.polarity}: {last}"
    reading = fact_registry_reading(fact)
    if reading in RETRYABLE_READINGS:
        return (
            f"{base}; RETRY_REGISTRY_READ: the registry gave no answer, which says nothing about "
            "the package - extract again, the candidate is not at fault"
        )
    if reading == "not_published":
        return (
            f"{base}; PACKAGE_ABSENT: the registry lists no such package, and it becomes a "
            "source install only when the maintainers' README says it is unpublished and the "
            "repository documents a build"
        )
    if reading == "no_registry":
        return (
            f"{base}; NO_REGISTRY: the ecosystem has no registry to ask, so the install is a "
            "source build, stated only from a build that exited 0 or - when the maintainers' "
            "README says it is unpublished - the build the repository documents"
        )
    return base


def _documented_source_failures(candidate: Candidate, fact: Fact) -> list[Failure]:
    """A documented source-checkout install (``source_basis: documented``) is held to what admits
    it: its registry reading is the registry's own "nothing is published" (or the ecosystem has no
    registry), the maintainers' README states the same, and the steps after the clone are the
    repository's own build, re-derived from the build-command fact rather than trusted from the
    attribute. A fact with any one missing is refused at EXTRACTING."""
    attributes = fact.attributes or {}
    if attributes.get(SOURCE_BASIS_ATTRIBUTE) != DOCUMENTED_SOURCE_BASIS:
        return []
    details = [evidence.detail or "" for evidence in fact.evidence]
    reading = fact_registry_reading(fact)
    problems: list[str] = []
    if attributes.get("install_kind") != "source_checkout":
        problems.append("a documented source install is a source_checkout kind")
    if attributes.get(REGISTRY_STATE_ATTRIBUTE) != NOT_PUBLISHED or reading not in (
        "not_published",
        "no_registry",
    ):
        problems.append(
            f"its registry reading ({reading or 'none'}) does not show the package unpublished"
        )
    if not any(README_STATEMENT_PHRASE in detail for detail in details):
        problems.append(
            "the maintainers' README is not recorded as saying it is unpublished"
        )
    steps = attributes.get(DOCUMENTED_COMMAND_ATTRIBUTE, "")
    expected = documented_steps(
        spec_for(candidate.entry.ecosystem), candidate.facts.facts, candidate.tree_paths
    )
    if (
        not any(DOCUMENTED_BUILD_PHRASE in detail for detail in details)
        or expected is None
    ):
        problems.append("the repository documents no build to state")
    elif steps != expected[0]:
        problems.append(
            f"it names the steps {steps!r}, but the repository documents {expected[0]!r}"
        )
    elif not fact.value.endswith("\n" + steps):
        problems.append(f"its command does not end with the documented steps {steps!r}")
    return [
        Failure("EXTRACTING", f"{fact.id} is a documented source install but {problem}")
        for problem in problems
    ]


def _registry_install_lines(
    readme: str, implied: set[str], package_name: str
) -> list[tuple[int, str]]:
    """``(line index, stripped line)`` for each README line that is the registry install.

    Either the exact command the manifest implied (anywhere, as a line or as an inline code span),
    or - inside a fence only, where a reader copies and runs it - a package tool installing the
    package by its own name (a pinned or re-spelled variant of the same command).
    """
    found: list[tuple[int, str]] = []
    inside = False
    for index, line in enumerate(readme.splitlines()):
        stripped = line.strip()
        if stripped.startswith("```"):
            inside = not inside
            continue
        plain = stripped.removeprefix("$ ").strip()
        exact = plain in implied or any(f"`{item}`" in line for item in implied)
        variant = (
            inside
            and package_name != ""
            and package_name in plain.lower()
            and COMMAND.match(plain) is not None
            and REGISTRY_INSTALL_VERB.search(plain) is not None
            and "git clone" not in plain
        )
        if exact or variant:
            found.append((index, stripped))
    return found


def _registry_command_failures(candidate: Candidate) -> list[Failure]:
    """A README never prints the registry install of a package its registry says is not published:
    the unpublished state is only true if the page says so plainly. A line from a placed inherited
    unit routes to that unit's disposition (RECONCILING, ``unit``), because the section's author
    cannot change a verbatim inherited line."""
    failures: list[Failure] = []
    package = next((f for f in candidate.facts.facts if f.id == "package:name"), None)
    package_name = package.value.lower() if package is not None else ""
    for fact in candidate.facts.by_kind("install_command"):
        command = (fact.attributes or {}).get(REGISTRY_COMMAND_ATTRIBUTE)
        if not command or fact.polarity != "SUPPORTED":
            continue
        implied = {line.strip() for line in command.splitlines() if line.strip()}
        printed = _registry_install_lines(candidate.readme, implied, package_name)
        if not printed:
            continue
        carriers = {
            line.strip(): placement.unit_id
            for placement in placements_of(candidate)
            if placement.outcome == "placed"
            for line in placement.text.splitlines()
        }
        sections = section_lines(candidate.readme)
        for index, line in printed:
            detail = (
                f"{fact.id}: the README prints {line!r}, the registry install of a package its "
                "registry reading says is not published"
            )
            unit = carriers.get(line)
            if unit is not None:
                failures.append(Failure("RECONCILING", detail, unit=unit))
            else:
                failures.append(Failure("COMPOSING", detail, sections[index]))
    return failures


def _check_source_checkout(candidate: Candidate) -> list[Failure]:
    """A "work from a source checkout instead" block is only the command the facts recorded as
    proven from the checkout root (TC-TST-01: a block that reads ``dotnet build`` at a root holding
    no project fails MSB1003, so it must be the recorded command or none)."""
    spec = spec_for(candidate.entry.ecosystem)
    if not spec.source_install_lead:
        return []
    lead = f"To work from a source checkout instead, {spec.source_install_lead}:"
    block = re.search(
        re.escape(lead) + r"\n\n```bash\n(.*?)\n```", candidate.readme, re.DOTALL
    )
    if block is None:
        return []
    install = next(
        (
            f
            for f in candidate.facts.by_kind("install_command")
            if f.id == spec.install_fact_id
        ),
        None,
    )
    repository = candidate.entry.repository
    expected = spec.source_checkout_command(
        install, repository, repository.split("/")[-1]
    )
    rendered = block.group(1)
    if expected and rendered == expected:
        return []
    why = (
        (install.attributes or {}).get(SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE)
        if install is not None
        else None
    )
    if expected:
        detail = (
            f"the source-checkout block renders {rendered!r}, not the command the facts record "
            f"as proven from the checkout root, {expected!r}"
        )
    else:
        detail = (
            f"the source-checkout block renders {rendered!r}, which no build proved from the "
            f"checkout root ({why or 'no source-checkout command recorded'})"
        )
    return [Failure("COMPOSING", detail, "installation")]
