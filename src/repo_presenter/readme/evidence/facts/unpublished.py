"""An unpublished package is a verified state, not a failure (BC-02, wave 6).

Eight of the 44 repositories are the Aspose.JMAP libraries, and their maintainers say so in the
README: "No package has been published to PyPI yet", "No artifact has been published to Maven
Central yet", "No versioned tag has been published yet". The registries agree - PyPI, Maven Central
and crates.io answer 404, the Go proxy lists no version - and BC-02 refused every one of them,
because a registry install nobody can run is not a verified install and the only path out was a
build this machine measured. The true README content for such a repository is the source install:
clone, then the repository's own build. This module admits it.

An install fact becomes a source checkout when, and only when, all three hold:

1. the registry reading is the registry's own answer that nothing is published
   (``not_published``: a 404, an empty Go version list, crates.io or Maven Central "not found"), or
   the ecosystem has no registry to ask (``no_registry``: C++). An unreadable registry
   (``unreadable``, ``ambiguous``) admits nothing - a network failure is never evidence that a
   package is absent, and the fact stays UNRESOLVED so the extraction is read again; a name some
   other project holds (``ownership_unconfirmed``) admits nothing either;
2. the maintainers' own README says the package is not published, so two independent sources
   agree and the README states what the registry shows rather than contradicting it - or (BL-340)
   its own install steps are a clone and a build and it prints no registry install and no registry
   listing, which agrees with the registry as a statement does (Aspose.Imaging FOSS for .NET), and
   no build this pipeline measured at this revision failed; and
3. the repository documents a build: the ``build_test_asset:build-command`` fact the clone's own CI
   workflow, script or toolchain manifest yields (read, never composed), else the ecosystem's
   standard command when the checkout root holds the manifest that command starts from.

A build that exited 0 at this revision is a stronger proof and is taken first, by
``extract._source_build_fact`` (``install_kind: source`` with the measured steps). This tier is
the one beneath it: ``install_kind: source_checkout`` with ``source_basis: documented``, whose
command was not run here, and which says nothing more than the README can say - the package is not
published, and the repository builds like so. It never renders a registry command, and the command
a registry would have implied is kept on the fact (``registry_command``) so BC-02 can refuse a
README that prints it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from fnmatch import fnmatchcase

from repo_presenter.core.ecosystems import CLONE_PREFIX, SPECS, EcosystemSpec
from repo_presenter.core.facts import (
    DOCUMENTED_COMMAND_ATTRIBUTE,
    DOCUMENTED_SOURCE_BASIS,
    NOT_PUBLISHED,
    REGISTRY_COMMAND_ATTRIBUTE,
    REGISTRY_STATE_ATTRIBUTE,
    SOURCE_BASIS_ATTRIBUTE,
    SOURCE_CHECKOUT_COMMAND_ATTRIBUTE,
    SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE,
    Evidence,
    Fact,
)
from repo_presenter.core.package_registry import fact_registry_reading
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    PRECONDITION_ATTRIBUTE,
)

# The evidence phrases BC-02 requires on a documented-source install fact. Defined once, here, so
# the writer and the judge cannot drift apart.
README_STATEMENT_PHRASE = "the maintainers' README states the package is not published"
DOCUMENTED_BUILD_PHRASE = "documented source build, not run for this revision"
# The second corroboration (BL-340): the maintainers' README does not use the word "unpublished" but
# its own Installation steps are a clone and a build, and it prints no registry install and claims
# no registry listing, so it agrees with a registry that lists nothing.
README_SOURCE_BUILD_PHRASE = (
    "the maintainers' README directs a source build from a clone and prints no registry install"
)

_SOURCE_INSTALL_KINDS = frozenset({"source", "source_checkout"})

# "No package has been published to PyPI yet", "No versioned tag has been published yet", "X is not
# yet published to crates.io", "unpublished", "not available on any registry". Each alternative is
# a statement that nothing is published; the sentence must also be about a distributable thing
# (_SUBJECT), so a sentence about a sibling tool or an unreleased feature does not count.
_UNPUBLISHED = re.compile(
    r"""(?ix)
    \b(?:
        unpublished
      | not \s+ (?:yet \s+)? (?:been \s+)? published
      | no \s+ (?:[\w-]+ \s+){0,3}? (?:has|have) \s+ (?:yet \s+)? been \s+ (?:published|released)
      | not \s+ (?:yet \s+)? (?:available|listed) \s+ (?:on|in|from) \s+
        (?:any \s+ |the \s+)? (?:package \s+)? (?:registry|pypi|nuget|npm|maven|crates\.io)
    )\b"""
)
_SUBJECT = re.compile(
    r"(?i)\b(?:package|packages|library|artifact|artefact|crate|module|sdk|distribution|"
    r"version|tag|release|registry|pypi|nuget|npm|maven|crates\.io|pkg\.go\.dev)\b"
)
_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_MARKDOWN = re.compile(r"[`*]|\[([^\]]*)\]\([^)]*\)")
_MAX_STATEMENT = 200


def _prose_paragraphs(readme: str) -> list[str]:
    """The README's paragraphs outside fenced code, each on one line, markdown links reduced to
    their text. A statement that wraps across lines is one sentence."""
    paragraphs: list[str] = []
    current: list[str] = []
    inside = False
    for line in readme.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if inside:
            continue
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return [_MARKDOWN.sub(lambda m: m.group(1) or "", p) for p in paragraphs]


def unpublished_statement(readme: str) -> str | None:
    """The first sentence of ``readme`` that says the package is not published, or None.

    Prose only: a fenced block, a link target and a heading's anchor say nothing. The sentence is
    returned as the README spells it (markdown stripped, trimmed) so the fact can quote it.
    """
    for paragraph in _prose_paragraphs(readme):
        for sentence in _SENTENCES.split(paragraph):
            if _UNPUBLISHED.search(sentence) and _SUBJECT.search(sentence):
                text = " ".join(sentence.split())
                return (
                    text
                    if len(text) <= _MAX_STATEMENT
                    else text[: _MAX_STATEMENT - 3] + "..."
                )
    return None


_CLONE_LINE = re.compile(r"^\s*(?:[$>]\s*)?git\s+clone\s+\S+")
# Anything that tells a reader the package can be fetched from a registry: a badge or link into one,
# or a sentence saying it is available there.
_REGISTRY_LISTING = re.compile(
    r"""(?ix)
    (?: img\.shields\.io/(?:nuget|pypi|npm|maven-central|crates|go-mod|packagist|gem)/
      | nuget\.org/packages | pypi\.org/project | npmjs\.com/package | crates\.io/crates/
      | search\.maven\.org | mvnrepository\.com | repo1?\.maven\.org | pkg\.go\.dev/
      | \b(?:available|published|released|listed|hosted)\s+(?:on|to|in|at|from)\s+
        (?:the\s+)?(?:nuget|pypi|npm|maven|crates\.io)
    )"""
)
_REGISTRY_TOOL_INSTALL = re.compile(
    r"""(?ix)
    \bdotnet\s+add\s+(?:[\w./\\-]+\s+)?package\b | \bInstall-Package\b | \bnuget\s+install\b
  | <PackageReference\s+Include | <dependency> | \b(?:implementation|compile|api)\s*[('"]
  | \bmvn\b.*dependency:get | \bnpm\s+(?:i|install|add)\b | \byarn\s+add\b | \bpnpm\s+(?:i|add|install)\b
  | \bcargo\s+add\b | \bgo\s+get\b | \bgem\s+install\b | \bcomposer\s+require\b"""
)
_PIP_INSTALL = re.compile(r"(?i)\bpip3?\s+install\b(.*)|\bpython3?\s+-m\s+pip\s+install\b(.*)")
_FLAG_WITH_PATH = frozenset({"-e", "--editable", "-r", "--requirement", "-c", "--constraint"})


def _pip_targets_a_registry(arguments: str) -> bool:
    """Whether ``pip install <arguments>`` names a package to fetch (not the checkout, a path or a
    requirements file)."""
    tokens = arguments.replace("`", " ").split()
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in _FLAG_WITH_PATH:
            skip = True
            continue
        if token.startswith("-"):
            continue
        if token in (".", "..") or token.startswith(("./", "../", "/", "~")) or "/" in token:
            continue
        if token.endswith((".whl", ".tar.gz", ".txt", ".toml")):
            continue
        return True
    return False


def _prints_a_registry_install(readme: str) -> bool:
    for line in readme.splitlines():
        if _REGISTRY_TOOL_INSTALL.search(line):
            return True
        match = _PIP_INSTALL.search(line)
        if match and _pip_targets_a_registry(match.group(1) or match.group(2) or ""):
            return True
    return False


def readme_directs_source_build(readme: str) -> str | None:
    """The clone command the maintainers' README gives as how to install, or None.

    The README counts only when it is a source-build README end to end: a fenced ``git clone`` is
    how it says to get the library, and nowhere does it print a registry install or point at a
    registry listing (a README that offers both a registry install and a clone is one that says the
    package is published, and stays refused). The returned line is the evidence quoted on the fact.
    """
    if _REGISTRY_LISTING.search(readme) or _prints_a_registry_install(readme):
        return None
    inside = False
    for line in readme.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside and _CLONE_LINE.match(line):
            return " ".join(line.split())
    return None


def _measured_build_failed(fact: Fact) -> bool:
    """Whether the facts stage drove the repository's build and it did not exit 0 (``failed (...)``
    in the unverified record, Aspose.GIS FOSS for .NET: 381 compile errors). "Not attempted" is not
    a failure: nothing was measured, which is what a documented source build says it is."""
    reason = (fact.attributes or {}).get(SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE, "")
    return reason.startswith("no build exited 0: failed")


def _has_root_manifest(spec: EcosystemSpec, tree_paths: Sequence[str]) -> bool:
    return any(
        "/" not in path and fnmatchcase(path, glob)
        for path in tree_paths
        for glob in spec.manifest_globs
    )


def documented_steps(
    spec: EcosystemSpec, facts: Sequence[Fact], tree_paths: Sequence[str]
) -> tuple[str, str, str] | None:
    """``(steps, evidence path, how it is documented)`` for the repository's own source build,
    or None when it documents none.

    The steps follow the clone, newline-joined in the order a reader runs them. The repository's
    own build-command fact comes first, with the precondition it records (a configure step, a tool
    to install); the ecosystem's standard command is the fallback only when the checkout root
    holds the manifest that command starts from (TC-TST-01: ``dotnet build`` at a root with no
    project fails MSB1003, so a template is never offered where nothing can start it).
    """
    build = next(
        (
            f
            for f in facts
            if f.id == BUILD_COMMAND_FACT_ID and f.polarity == "SUPPORTED"
        ),
        None,
    )
    if build is not None:
        attributes = build.attributes or {}
        before = [
            line
            for line in attributes.get(PRECONDITION_ATTRIBUTE, "").splitlines()
            if line
        ]
        source = attributes.get("source", "build file")
        steps = "\n".join([*before, build.value])
        if spec.source_dependencies and not steps.startswith(spec.source_dependencies):
            steps = f"{spec.source_dependencies}\n{steps}"
        return (
            steps,
            build.evidence[0].path,
            f"the repository's own {source} gives `{build.value}`",
        )
    template = spec.source_install.removeprefix(CLONE_PREFIX)
    if (
        template != spec.source_install
        and template
        and _has_root_manifest(spec, tree_paths)
    ):
        manifest = next(
            path
            for path in tree_paths
            if "/" not in path
            and any(fnmatchcase(path, glob) for glob in spec.manifest_globs)
        )
        return (
            template,
            manifest,
            (
                f"the ecosystem's standard command for the project the root manifest declares is "
                f"`{template}`"
            ),
        )
    return None


def documented_source_install(
    fact: Fact,
    entry: RegistryEntry,
    *,
    facts: Sequence[Fact],
    tree_paths: Sequence[str],
    readme_path: str,
    readme_text: str,
    registry_less: bool,
) -> Fact:
    """``fact`` as a documented source checkout when its package is unpublished, else ``fact``.

    See the module docstring for the three conditions. Anything short of them returns the fact
    untouched: an unreadable registry, an ownerless name, a README that does not say it, or a
    repository that documents no build all keep the install UNRESOLVED or CONTRADICTED, and BC-02
    keeps refusing them (with the reading's class named, so a transient failure is retried and not
    mistaken for an absent package).
    """
    spec = SPECS.get(entry.ecosystem)
    if (
        spec is None
        or fact.kind != "install_command"
        or fact.id != spec.install_fact_id
        or (fact.attributes or {}).get("install_kind") in _SOURCE_INSTALL_KINDS
    ):
        return fact
    reading = fact_registry_reading(fact)
    if not (
        (reading == "not_published" and fact.polarity == "CONTRADICTED")
        or (
            reading == "no_registry" and registry_less and fact.polarity == "UNRESOLVED"
        )
    ):
        return fact
    statement = unpublished_statement(readme_text)
    corroboration = (
        f"{README_STATEMENT_PHRASE}: {statement!r}" if statement is not None else None
    )
    if corroboration is None:
        # BL-340: the registry lists nothing and the README says nothing of publication, but its
        # own install steps are a clone and a build and it never offers a registry install. A build
        # this machine measured and watched fail is never told to a reader as the way to install.
        clone = readme_directs_source_build(readme_text)
        if clone is None or _measured_build_failed(fact):
            return fact
        corroboration = f"{README_SOURCE_BUILD_PHRASE}: {clone!r}"
    documented = documented_steps(spec, facts, tree_paths)
    if documented is None:
        return fact
    steps, path, how = documented
    attributes = {
        key: value
        for key, value in (fact.attributes or {}).items()
        if key
        not in (SOURCE_CHECKOUT_COMMAND_ATTRIBUTE, SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE)
    }
    attributes.update(
        {
            "install_kind": "source_checkout",
            REGISTRY_STATE_ATTRIBUTE: NOT_PUBLISHED,
            SOURCE_BASIS_ATTRIBUTE: DOCUMENTED_SOURCE_BASIS,
            DOCUMENTED_COMMAND_ATTRIBUTE: steps,
        }
    )
    if reading == "not_published":
        # The registry command the manifest implied; for a registry-less ecosystem the original
        # value was already a source build, not something a registry would have served.
        attributes[REGISTRY_COMMAND_ATTRIBUTE] = fact.value
    name = entry.repository.split("/")[-1]
    return replace(
        fact,
        value=spec.clone_and_run(entry.repository, name, steps),
        polarity="SUPPORTED",
        confidence=1.0,
        attributes=attributes,
        evidence=(
            *fact.evidence,
            Evidence(readme_path, corroboration),
            Evidence(path, f"{DOCUMENTED_BUILD_PHRASE}: {how}"),
        ),
    )
