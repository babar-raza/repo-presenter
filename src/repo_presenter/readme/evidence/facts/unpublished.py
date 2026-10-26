"""The documented source build of an unpublished package, as BC-02 reads it.

ADAPT (narrow slice) from the old repository-presenter project's
``components/readme/evidence/facts/unpublished.py``. Only what the blocking install check
(``readme/validation/install.py``) reads is ported here: the two evidence phrases a
documented-source install fact must carry, and ``documented_steps``, which re-derives the build
the repository documents. The extraction half (``unpublished_statement``,
``documented_source_install``, which decide whether a fact is admitted as a source checkout) is
not ported; it belongs with the extraction taskcard that owns the registry observers.
"""

from __future__ import annotations

from collections.abc import Sequence
from fnmatch import fnmatchcase

from repo_presenter.core.ecosystems import CLONE_PREFIX, EcosystemSpec
from repo_presenter.core.facts import Fact
from repo_presenter.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    PRECONDITION_ATTRIBUTE,
)

README_STATEMENT_PHRASE = "the maintainers' README states the package is not published"
DOCUMENTED_BUILD_PHRASE = "documented source build, not run for this revision"


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
    own build-command fact comes first, with the precondition it records; the ecosystem's standard
    command is the fallback only when the checkout root holds the manifest that command starts
    from (a template is never offered where nothing can start it).
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
                "the ecosystem's standard command for the project the root manifest declares is "
                f"`{template}`"
            ),
        )
    return None
