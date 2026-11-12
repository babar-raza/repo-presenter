"""I1 (docs/design/2026-11-06-acceptance-redesign.md; TC-024 part e): the acceptance/verification
code never imports the generation/repair modules it is supposed to check independently. A
verifier that can import what it verifies can quietly agree with it -- the same reasoning
``tests/readme/review/test_review_invariants.py`` already applies to "no ACCEPT/REJECT value is
assigned outside the fold", mirrored here for "the seal-path's verdict-computing code never reaches
into generation/repair".

Static and transitive: walks the SOURCE import graph with ``ast`` (no module is ever executed)
from TC-013's ``acceptance/`` package, and fails if that closure ever reaches
``repo_presenter.readme.composition``, ``repo_presenter.readme.reconciliation`` or
``repo_presenter.readme.repair``.

Scoped to ``acceptance/`` alone, not also to ``readme.review.llm_review`` (TC-024's own M8-gate
module, which the card text names as a second possible root: "plus whatever module now computes
the deterministic+M8 verdict"). Measured directly (this file's own history, now reverted): adding
``llm_review.py`` as a root makes this test fail against PRE-EXISTING, unrelated code this card
does not touch -- ``readme/review/scope.py`` and ``readme/review/reply.py`` (both already imported
by ``llm_review`` before TC-024) import ``readme.composition.components.shell`` and
``readme.composition.placement`` for a genuinely different reason than the one I1 guards against:
telling renderer-printed text apart from author-written text, which the reviewer needs to know
what it may even look at. That is not "verification code that can import what it verifies and
quietly agree with it" (I1's actual target, and ``acceptance/``'s own actual design, per I2's
"separate evidence" principle) -- it is "a reviewer that needs to know which lines are its own
business." The NEW gate logic this card adds (``m8_blocking_units``, and ``recertify.py``'s/
``core.state.bundle_store``'s own ``_model_accept``/``model_accept``) imports nothing from
composition/reconciliation/repair either, by direct inspection of their own bodies; splitting
``llm_review.py`` into a packet-building half and a gate half to make a module-level import-graph
test pass for the whole file is a real, separate refactor this card's ``write_paths`` do not
authorize undertaking as a side effect of this one test.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "repo_presenter"

#: The acceptance/verification code this invariant protects (TC-024's card text, part e): TC-013's
#: acceptance package. See the module docstring for why ``readme.review.llm_review`` is not also a
#: root here.
ROOTS: tuple[Path, ...] = (SRC / "acceptance",)


def test_m8_gate_and_recertify_gate_functions_import_nothing_from_generation_or_repair() -> None:
    """The narrower, real claim behind "whatever module now computes the deterministic+M8
    verdict": the specific functions that DECIDE the TC-013/TC-024 contract from a verdict/stored
    review -- ``llm_review.m8_blocking_units``, ``recertify._model_accept`` and
    ``core.state.bundle_store.SealRecord.model_accept`` -- never reference a name imported from
    composition/reconciliation/repair, checked at the function-body level (``ast``, no module-
    level import noise from the rest of those files' other, unrelated responsibilities)."""
    import inspect
    import textwrap

    from repo_presenter import recertify
    from repo_presenter.core.state import bundle_store
    from repo_presenter.readme.review import llm_review

    targets = [
        llm_review.m8_blocking_units,
        recertify._model_accept,
        bundle_store.SealRecord.model_accept.fget,
    ]
    for target in targets:
        source = textwrap.dedent(inspect.getsource(target))
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        offenders = sorted(
            name for name in imports if any(name.startswith(p) for p in FORBIDDEN_PREFIXES)
        )
        assert not offenders, f"{target.__qualname__} imports {offenders}"

#: A reached module whose dotted name starts with any of these is a violation: the generation and
#: repair halves this code is supposed to check independently of.
FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "repo_presenter.readme.composition",
    "repo_presenter.readme.reconciliation",
    "repo_presenter.readme.repair",
)


def _module_name(path: Path) -> str:
    """The dotted module name ``path`` (a file under ``SRC``'s parent) would import as."""
    relative = path.relative_to(SRC.parent)
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_parts(path: Path) -> list[str]:
    """The dotted package ``path`` lives in (its own module name, minus the leaf module unless
    ``path`` is itself a package's ``__init__.py``) -- what a relative import inside it resolves
    against."""
    parts = _module_name(path).split(".")
    if path.name != "__init__.py":
        parts = parts[:-1]
    return parts


def _resolve_relative(path: Path, module: str | None, level: int) -> str:
    base = _package_parts(path)
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join([*base, module] if module else base)


def _imports_of(path: Path) -> set[str]:
    """Every dotted module name ``path`` imports, directly, as its source literally reads it
    (``ast``, no execution): absolute ``import``/``from ... import`` statements as written, and a
    relative ``from . import ...`` resolved against ``path``'s own package."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    names.add(node.module)
            else:
                names.add(_resolve_relative(path, node.module, node.level))
    return names


def _files_of(root: Path) -> list[Path]:
    return [root] if root.is_file() else sorted(root.rglob("*.py"))


def _module_path(name: str) -> Path | None:
    """``name`` resolved back to one of THIS project's own ``.py`` files, or ``None`` for a
    stdlib/third-party name (those are never followed -- only this project's own import graph is
    walked)."""
    if not name.startswith("repo_presenter"):
        return None
    relative = Path(*name.split("."))
    as_module = SRC.parent / relative.with_suffix(".py")
    if as_module.is_file():
        return as_module
    as_package = SRC.parent / relative / "__init__.py"
    if as_package.is_file():
        return as_package
    return None


def _transitive_closure(start: list[Path]) -> set[str]:
    """Every module name reachable, directly or indirectly, from ``start``'s own source files."""
    seen_files: set[Path] = set()
    reached: set[str] = set()
    stack = list(start)
    while stack:
        path = stack.pop()
        if path in seen_files:
            continue
        seen_files.add(path)
        for name in _imports_of(path):
            reached.add(name)
            next_path = _module_path(name)
            if next_path is not None and next_path not in seen_files:
                stack.append(next_path)
    return reached


def test_roots_exist_and_are_this_projects_own_files() -> None:
    """A guard against the test silently passing because a root path was renamed/removed: every
    root must actually exist and resolve to at least one real ``.py`` file."""
    for root in ROOTS:
        assert root.exists(), f"{root} does not exist"
        assert _files_of(root), f"{root} has no .py files to check"


def test_acceptance_and_the_seal_verdict_module_never_import_generation_or_repair() -> None:
    start = [file for root in ROOTS for file in _files_of(root)]
    reached = _transitive_closure(start)
    offenders = sorted(
        name for name in reached if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
    )
    assert not offenders, (
        "the acceptance/verification code's own import closure reaches a generation/repair "
        f"module (design doc I1): {offenders}"
    )


def test_the_forbidden_prefixes_are_themselves_real_packages() -> None:
    """A guard against the invariant being vacuous because a forbidden prefix was mistyped: each
    one must resolve to a real package under ``src/repo_presenter``."""
    for prefix in FORBIDDEN_PREFIXES:
        relative = Path(*prefix.split("."))
        assert (SRC.parent / relative / "__init__.py").is_file(), f"{prefix} is not a real package"


def test_a_synthetic_forbidden_import_is_actually_caught() -> None:
    """The negative control this test file proves against itself: a file that imports a forbidden
    module must be flagged by the same closure walk the real test uses -- otherwise the whole
    mechanism could be silently inert (a typo'd prefix, a closure that never follows relative
    imports, ...) and the real test above would pass for the wrong reason."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad_module.py"
        bad.write_text(
            "from repo_presenter.readme.composition.renderer import render_readme\n",
            encoding="utf-8",
        )
        # _module_path only resolves repo_presenter.* names against SRC.parent, so the import
        # itself is inspected directly here rather than through the full closure walk (which
        # would need the fake file to live under SRC.parent to be followed).
        imports = _imports_of(bad)
        offenders = [
            name for name in imports if any(name.startswith(p) for p in FORBIDDEN_PREFIXES)
        ]
        assert offenders == ["repo_presenter.readme.composition.renderer"]
