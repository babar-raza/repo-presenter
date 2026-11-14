"""The Python platform plugin: manifest facts from pyproject.toml, setup.cfg, and setup.py.

Adapted from the legacy Python manifest parser, itself adapted from a production reference tuned
against the same Aspose FOSS corpus. pyproject.toml is authoritative when it yields a name;
setup.cfg and setup.py are consulted only when it is absent or incomplete. Nothing is executed:
setup.py is read through the AST and only literal keywords of a proven setuptools call count.
Import paths come from the packages the manifest declares or, failing that, from the package
directories the tree inventory proves.

Ported (REUSE, near-verbatim) from the old repository-presenter project's
``components/readme/extractors/platforms/python.py`` per migration/reuse-manifest.yaml.
``verify_examples`` now calls the ported execution/toolchain-backed ``python_examples.py``
(itself ported from the old repo), which drives a real pip install and subprocess run of each
README code fence under ``core/execution.py``/``core/toolchains.py`` and classifies each
candidate EXECUTED/FAILED/TIMED_OUT/NEEDS_INPUT/NOT_VERIFIED from what actually happened -
never a fabricated receipt.
"""

from __future__ import annotations

import ast
import json
import tomllib
from collections.abc import Mapping, Sequence
from configparser import ConfigParser
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement

from repo_presenter.extractors.platforms.python_examples import (
    verify_python_examples,
)
from repo_presenter.extractors.platforms.python_format_declarations import (
    format_declarations,
)
from repo_presenter.extractors.platforms.python_formats import (
    format_claims,
)
from repo_presenter.extractors.platforms.python_registry import (
    observe_pypi,
)
from repo_presenter.extractors.platforms.python_setup_py import (
    parse_setup_py,
)
from repo_presenter.extractors.platforms.python_surface import (
    inspect_public_surface,
    public_symbol_facts,
)
from repo_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repo_presenter.core.facts import (
    Evidence,
    Fact,
    fact_id,
)
from repo_presenter.core.package_registry import install_verdict
from repo_presenter.core.probes import ProbeRecord

MANIFEST_NAMES = ("pyproject.toml", "setup.cfg", "setup.py")
_NON_PRODUCT_TOP_LEVEL = frozenset({"tests", "test", "docs", "examples", "pyi", "scripts", "build"})
_MAX_IMPORT_PATH_DEPTH = 2
# The conventional "src layout": packages live under `src/`, which is a directory, not a package.
_SOURCE_LAYOUT_DIRECTORY = "src"
# Extras whose requirements serve development, not users of the package.
_DEVELOPMENT_EXTRAS = frozenset({"dev", "develop", "development", "test", "tests", "testing"})
_NOT_DECLARED = {
    "pyproject.toml": "no `project.dependencies` is declared",
    "setup.cfg": "no `options.install_requires` is declared",
    "setup.py": "no `install_requires` is declared",
}
_DYNAMIC_DEPENDENCIES = (
    "`dependencies` is declared dynamic in pyproject.toml, so the requirements are computed at "
    "build time and not statically known"
)


# The field each manifest spells the interpreter floor with.
_FLOOR_FIELDS: dict[str, str] = {
    "pyproject.toml": "requires-python",
    "setup.cfg": "python_requires",
    "setup.py": "python_requires",
}


def _requirement_fact(identifier: str, requirement: str, path: str, detail: str) -> Fact:
    """A dependency fact for one declared requirement string.

    The string is taken whole: a PEP 508 specifier is ``numpy>=1.20,<2``, one requirement with
    two clauses, never two requirements. One a PEP 508 parser rejects (a ``-r file`` line, a
    URL typo) is recorded but not asserted, so a README never states it as a package.
    """
    try:
        Requirement(requirement)
    except InvalidRequirement:
        return Fact(
            identifier,
            "dependency",
            requirement,
            (Evidence(path, f"{detail}; not a valid PEP 508 requirement"),),
            polarity="UNRESOLVED",
            confidence=0.5,
        )
    return Fact(identifier, "dependency", requirement, (Evidence(path, detail),))


def _literal_assignment(path: Path, name: str) -> str | None:
    """Read one module-level string assignment without importing repository code."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        value = None
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is None:
            continue
        try:
            literal = ast.literal_eval(value)
        except (TypeError, ValueError):
            return None
        return literal if isinstance(literal, str) and literal.strip() else None
    return None


def _dynamic_setuptools_version(pyproject_path: Path, data: dict[str, Any]) -> str | None:
    """Resolve a PEP 621 setuptools ``version.attr`` from static source only."""
    project = data.get("project", {})
    if "version" not in project.get("dynamic", []):
        return None
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    version_cfg = setuptools_cfg.get("dynamic", {}).get("version", {})
    attr = version_cfg.get("attr") if isinstance(version_cfg, dict) else None
    if not isinstance(attr, str) or "." not in attr:
        return None
    module_name, attribute_name = attr.rsplit(".", 1)
    if not module_name or not attribute_name.isidentifier():
        return None
    package_dirs = setuptools_cfg.get("package-dir", {})
    source_root = ""
    if isinstance(package_dirs, dict):
        configured = package_dirs.get("")
        if isinstance(configured, str):
            source_root = configured
    module_path = (pyproject_path.parent / source_root).joinpath(*module_name.split("."))
    for candidate in (module_path.with_suffix(".py"), module_path / "__init__.py"):
        version = _literal_assignment(candidate, attribute_name)
        if version is not None:
            return version
    return None


def parse_pyproject(pyproject_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8", errors="replace"))
    project = data.get("project", {})
    if project.get("name"):
        info["name"] = project["name"]
    if project.get("version"):
        info["version"] = project["version"]
    elif dynamic_version := _dynamic_setuptools_version(pyproject_path, data):
        info["version"] = dynamic_version
    license_value = project.get("license", "")
    if isinstance(license_value, dict):
        license_value = license_value.get("text", license_value.get("file", ""))
    if license_value:
        info["license"] = str(license_value)
    if project.get("requires-python"):
        info["requires_python"] = project["requires-python"]
    dependencies = [d for d in project.get("dependencies", []) if isinstance(d, str) and d.strip()]
    dynamic = project.get("dynamic", [])
    if dependencies:
        info["dependencies"] = json.dumps([d.strip() for d in dependencies])
    elif isinstance(dynamic, list) and "dependencies" in dynamic:
        # PEP 621: a field listed in `dynamic` is computed by the build backend. "Not written
        # here" is not "none": the requirements exist, and only a build would reveal them.
        info["dependencies_dynamic"] = _DYNAMIC_DEPENDENCIES
    elif "dependencies" in project:
        info["dependency_evidence"] = "the `project.dependencies` list is empty"
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        buckets = {
            str(extra): [d.strip() for d in reqs if isinstance(d, str) and d.strip()]
            for extra, reqs in optional.items()
            if isinstance(reqs, list)
        }
        if any(buckets.values()):
            info["extras"] = json.dumps({k: v for k, v in buckets.items() if v}, sort_keys=True)
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    packages_cfg = setuptools_cfg.get("packages", [])
    if isinstance(packages_cfg, dict):
        candidates = packages_cfg.get("find", {}).get("include", [])
    elif isinstance(packages_cfg, list):
        candidates = packages_cfg
    else:
        candidates = []
    declared = [
        candidate
        for candidate in candidates
        if isinstance(candidate, str) and candidate and not candidate.endswith(("*", ".*"))
    ]
    if declared:
        info["declared_packages"] = ",".join(declared)
    return info


def parse_setup_cfg(setup_cfg_path: Path) -> dict[str, str]:
    parser = ConfigParser()
    parser.read(setup_cfg_path, encoding="utf-8")
    info: dict[str, str] = {}
    if parser.has_section("metadata"):
        for source, target in (("name", "name"), ("version", "version"), ("license", "license")):
            value = parser.get("metadata", source, fallback="").strip()
            if value:
                info[target] = value
    if parser.has_section("options"):
        requires_python = parser.get("options", "python_requires", fallback="").strip()
        if requires_python:
            info["requires_python"] = requires_python
        if parser.has_option("options", "install_requires"):
            raw = parser.get("options", "install_requires")
            declared = _requirement_lines(raw)
            if raw.strip().startswith(("file:", "attr:")):
                info["dependencies_dynamic"] = (
                    "`options.install_requires` reads its requirements from "
                    f"`{raw.strip().split(maxsplit=1)[0]}`, which is not statically known"
                )
            elif declared:
                info["dependencies"] = json.dumps(declared)
            else:
                info["dependency_evidence"] = "the `options.install_requires` list is empty"
    if parser.has_section("options.extras_require"):
        buckets = {
            extra: _requirement_lines(parser.get("options.extras_require", extra))
            for extra in parser.options("options.extras_require")
        }
        if any(buckets.values()):
            info["extras"] = json.dumps({k: v for k, v in buckets.items() if v}, sort_keys=True)
    return info


def _requirement_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def parse_manifests(root: Path) -> dict[str, dict[str, str]]:
    """Metadata per manifest file, in authority order, for every manifest present at the root."""
    parsed: dict[str, dict[str, str]] = {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        parsed["pyproject.toml"] = parse_pyproject(pyproject)
    if not any(info.get("name") for info in parsed.values()) and (root / "setup.cfg").is_file():
        parsed["setup.cfg"] = parse_setup_cfg(root / "setup.cfg")
    if not any(info.get("name") for info in parsed.values()) and (root / "setup.py").is_file():
        parsed["setup.py"] = parse_setup_py(root / "setup.py")
    return parsed


def package_locations(tree_paths: list[str]) -> list[tuple[str, str]]:
    """``(dotted import path, repository-relative directory)`` per proven package directory.

    Shallowest first. In a src layout (``src/`` holds packages and is itself no package) the
    import path omits ``src``: ``src/pkg/__init__.py`` is imported as ``pkg``, which is also the
    name the public surface reads its symbols under.
    """
    in_tree = set(tree_paths)
    src_layout = f"{_SOURCE_LAYOUT_DIRECTORY}/__init__.py" not in in_tree
    found: dict[str, str] = {}
    for path in tree_paths:
        parts = path.split("/")
        if parts[-1] != "__init__.py" or len(parts) < 2:
            continue
        directory = parts[:-1]
        package = (
            directory[1:] if src_layout and directory[0] == _SOURCE_LAYOUT_DIRECTORY else directory
        )
        if not package or len(package) > _MAX_IMPORT_PATH_DEPTH:
            continue
        if package[0] in _NON_PRODUCT_TOP_LEVEL or not all(part.isidentifier() for part in package):
            continue
        found.setdefault(".".join(package), "/".join(directory))
    ordered = sorted(found, key=lambda dotted: (dotted.count("."), dotted))
    return [(dotted, found[dotted]) for dotted in ordered]


def package_directories(tree_paths: list[str]) -> list[str]:
    """Dotted import paths of the package directories the tree proves, shallowest first."""
    return [dotted for dotted, _ in package_locations(tree_paths)]


# --- the packages the build ships (BL-065, Python variant) ------------------------------------
#
# M9 round 43559491132 (Words Python Lane L, seal at 2d2efee2): "The library ships 198 public types"
# counted 9 classes of `ApiExamples/`, a tree package the wheel never contains -- pyproject.toml:66-67
# `[tool.hatch.build.targets.wheel] packages = ["aspose"]` ships 189. The tree proves a package
# directory exists; only the build manifest says which ones a user installs. ``shipped_path_filter``
# reads that list from the root manifest (pyproject.toml, else setup.cfg, else a literal setup.py
# call) and answers, per repository path, whether the build ships it. It only ever NARROWS the tree
# discovery (``package_locations``): a manifest that declares nothing, or names nothing the tree
# holds, leaves every package as before (fail open: never an empty surface from a misread manifest).


def _pattern_match(name: str, patterns: Sequence[str]) -> bool:
    from fnmatch import fnmatchcase

    return any(fnmatchcase(name, pattern) for pattern in patterns)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.replace(",", "\n").splitlines() if part.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def _found_package_dirs(
    tree_paths: Sequence[str], where: Sequence[str], include: Sequence[str],
    exclude: Sequence[str], namespaces: bool,
) -> set[str]:
    """setuptools ``find_packages`` / ``find_namespace_packages`` over the tree: the repository-relative
    directories of every package under ``where`` whose dotted name matches ``include`` and no
    ``exclude`` (fnmatch, as setuptools). A classic find needs an ``__init__.py`` in the directory
    and in each parent below ``where``; a namespace find takes every directory holding a module."""
    in_tree = set(tree_paths)
    found: set[str] = set()
    for base in where or ["."]:
        base = base.strip().strip("/")
        prefix = "" if base in ("", ".") else base + "/"
        for path in tree_paths:
            if not path.endswith(".py") or not path.startswith(prefix):
                continue
            parts = path[len(prefix):].split("/")[:-1]
            if not parts or not all(part.isidentifier() for part in parts):
                continue
            for depth in range(1, len(parts) + 1):
                directory = parts[:depth]
                if not namespaces and f"{prefix}{'/'.join(directory)}/__init__.py" not in in_tree:
                    break
                dotted = ".".join(directory)
                if _pattern_match(dotted, include or ["*"]) and not _pattern_match(dotted, exclude):
                    found.add(prefix + "/".join(directory))
    return found


def _listed_package_dirs(dotted_names: Sequence[str], package_dir: Any) -> set[str]:
    """setuptools ``packages = [...]`` (dotted names) to directories through ``package-dir``."""
    mapping = package_dir if isinstance(package_dir, dict) else {}
    roots: set[str] = set()
    for dotted in dotted_names:
        top, _, rest = dotted.partition(".")
        if top in mapping and isinstance(mapping[top], str):
            base = mapping[top].strip("/")
            directory = "/".join(filter(None, [base, *rest.split(".")])) if rest else base
        else:
            base = str(mapping.get("", "") or "").strip("/").strip(".")
            directory = "/".join(filter(None, [base, *dotted.split(".")]))
        roots.add(directory)
    return roots


def _setup_py_find(text: str) -> dict[str, Any] | None:
    """A literal ``setup(packages=find_packages(...)|find_namespace_packages(...)|[...])`` call, read
    through the AST (never executed); ``None`` when the keyword is absent or not literal."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        if name != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg != "packages":
                continue
            value = keyword.value
            try:
                if isinstance(value, ast.Call):
                    finder = value.func.id if isinstance(value.func, ast.Name) else getattr(value.func, "attr", "")
                    if finder not in ("find_packages", "find_namespace_packages"):
                        return None
                    args = {k.arg: ast.literal_eval(k.value) for k in value.keywords if k.arg}
                    if value.args:
                        args.setdefault("where", ast.literal_eval(value.args[0]))
                    return {"find": {**args, "namespaces": finder == "find_namespace_packages"}}
                return {"list": ast.literal_eval(value)}
            except (ValueError, TypeError, SyntaxError):
                return None
    return None


def shipped_package_roots(
    manifests: Mapping[str, str], tree_paths: Sequence[str]
) -> tuple[str, frozenset[str], bool] | None:
    """``(manifest clause, shipped package directories, subtrees)`` the root build manifest declares:
    ``subtrees`` true when each directory ships with everything below it (a hatch/poetry/setuptools
    list), false when the set names every shipped package directory (a setuptools find). ``None``
    when no manifest declares its packages, or none of the declared directories is in the tree."""
    in_tree_dirs = {path.rsplit("/", 1)[0] for path in tree_paths if "/" in path}
    declared: tuple[str, set[str], bool] | None = None
    pyproject = manifests.get("pyproject.toml")
    if pyproject:
        try:
            data = tomllib.loads(pyproject)
        except tomllib.TOMLDecodeError:
            data = {}
        tool = data.get("tool", {}) if isinstance(data.get("tool"), dict) else {}
        hatch = (tool.get("hatch") or {}).get("build") or {}
        wheel = ((hatch.get("targets") or {}).get("wheel") or {}) if isinstance(hatch, dict) else {}
        setuptools_cfg = tool.get("setuptools") or {}
        poetry = tool.get("poetry") or {}
        if isinstance(wheel, dict) and _string_list(wheel.get("packages")):
            declared = ("tool.hatch.build.targets.wheel.packages",
                        {p.strip("/") for p in _string_list(wheel.get("packages"))}, True)
        elif isinstance(hatch, dict) and _string_list(hatch.get("packages")):
            declared = ("tool.hatch.build.packages", {p.strip("/") for p in _string_list(hatch.get("packages"))}, True)
        elif isinstance(setuptools_cfg, dict) and "packages" in setuptools_cfg:
            packages = setuptools_cfg.get("packages")
            if isinstance(packages, list):
                declared = ("tool.setuptools.packages",
                            _listed_package_dirs(_string_list(packages), setuptools_cfg.get("package-dir")), True)
            elif isinstance(packages, dict) and isinstance(packages.get("find"), dict):
                find = packages["find"]
                declared = ("tool.setuptools.packages.find", _found_package_dirs(
                    tree_paths, _string_list(find.get("where")) or ["."], _string_list(find.get("include")),
                    _string_list(find.get("exclude")), bool(find.get("namespaces", True))), False)
        elif isinstance(poetry, dict) and isinstance(poetry.get("packages"), list):
            roots = set()
            for item in poetry["packages"]:
                if isinstance(item, dict) and isinstance(item.get("include"), str):
                    base = str(item.get("from") or "").strip("/")
                    roots.add("/".join(filter(None, [base, item["include"].strip("/")])))
            if roots:
                declared = ("tool.poetry.packages", roots, True)
    if declared is None and manifests.get("setup.cfg"):
        parser = ConfigParser()
        try:
            parser.read_string(manifests["setup.cfg"])
        except Exception:  # noqa: BLE001 -- an unreadable setup.cfg declares nothing
            parser = ConfigParser()
        if parser.has_option("options", "packages"):
            raw = parser.get("options", "packages").strip()
            package_dir = {}
            if parser.has_option("options", "package_dir"):
                for line in _string_list(parser.get("options", "package_dir")):
                    key, _, value = line.partition("=")
                    package_dir[key.strip()] = value.strip()
            if raw.startswith(("find:", "find_namespace:")):
                section = "options.packages.find"
                get = (lambda key: _string_list(parser.get(section, key)) if parser.has_option(section, key) else [])
                declared = ("setup.cfg options.packages", _found_package_dirs(
                    tree_paths, get("where") or [str(package_dir.get("", ".") or ".")], get("include"),
                    get("exclude"), raw.startswith("find_namespace:")), False)
            else:
                declared = ("setup.cfg options.packages", _listed_package_dirs(_string_list(raw), package_dir), True)
    if declared is None and manifests.get("setup.py"):
        call = _setup_py_find(manifests["setup.py"])
        if call and "find" in call:
            find = call["find"]
            declared = ("setup.py packages", _found_package_dirs(
                tree_paths, _string_list(find.get("where")) or ["."], _string_list(find.get("include")),
                _string_list(find.get("exclude")), bool(find.get("namespaces"))), False)
        elif call and isinstance(call.get("list"), list):
            declared = ("setup.py packages", _listed_package_dirs(_string_list(call["list"]), {}), True)
    if declared is None:
        return None
    clause, directories, subtrees = declared
    present = {d for d in directories if d and (d in in_tree_dirs or any(t.startswith(d + "/") for t in in_tree_dirs))}
    return (clause, frozenset(present), subtrees) if present else None


def shipped_path_filter(manifests: Mapping[str, str], tree_paths: Sequence[str]):
    """``(clause, ships)``: whether the build ships a repository path (a ``.py`` module is shipped
    when its directory is a shipped package; any other path is not judged and passes), or ``None``
    when the manifest declares no package list (see ``shipped_package_roots``)."""
    roots = shipped_package_roots(manifests, tree_paths)
    if roots is None:
        return None
    clause, directories, subtrees = roots

    def ships(path: str) -> bool:
        if not path.endswith(".py"):
            return True
        directory = path.rsplit("/", 1)[0] if "/" in path else ""
        if subtrees:
            return any(directory == d or directory.startswith(d + "/") for d in directories)
        return directory in directories

    return clause, ships


def read_root_manifests(root: Path) -> dict[str, str]:
    """The root build manifests' text (``MANIFEST_NAMES``) present in a checkout."""
    found: dict[str, str] = {}
    for name in MANIFEST_NAMES:
        path = root / name
        if path.is_file():
            found[name] = path.read_text(encoding="utf-8", errors="replace")
    return found


def fact_paths(fact: Fact) -> list[str]:
    """The repository source paths a fact's evidence names (URLs and non-paths excluded)."""
    return [e.path for e in fact.evidence if e.path and "://" not in e.path]


def unshipped_fact(fact: Fact, ships) -> bool:
    """A ``public_symbol`` / ``import_path`` fact every source path of which the build does not ship."""
    if fact.kind not in ("public_symbol", "import_path"):
        return False
    paths = [p for p in fact_paths(fact) if p.endswith(".py")]
    return bool(paths) and not any(ships(p) for p in paths)


class PythonPlugin:
    """Python packages: manifest facts and the import paths the tree proves."""

    ecosystem = "python"
    manifest_globs: tuple[str, ...] = MANIFEST_NAMES
    source_suffixes = frozenset({".py"})

    def detect_manifest(self, root: Path) -> Path | None:
        for name in MANIFEST_NAMES:
            candidate = root / name
            if candidate.is_file():
                return candidate
        return None

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        package_dirs = [directory for _, directory in package_locations(tree_paths)]
        facts = public_symbol_facts(inspect_public_surface(root, package_dirs))
        shipped = self.shipped_path_filter(read_root_manifests(root), tree_paths)
        if shipped is None:
            return facts
        return [fact for fact in facts if not unshipped_fact(fact, shipped[1])]

    def shipped_path_filter(self, manifests: Mapping[str, str], tree_paths: Sequence[str]):
        """The build's package list as a path predicate (``shipped_path_filter``); also used by
        re-certification over a sealed facts document (``recertify.shipped_facts``)."""
        return shipped_path_filter(manifests, tree_paths)

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the pip install claim against PyPI; the fact keeps its ID and gains evidence.

        The read's status, its duration, and the registry's current latest version go to the
        probe record instead of the evidence, so a release published upstream cannot reopen a
        stage for a repository that did not change.
        """
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get("install_command:pip")
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        version = by_id.get("package:version")
        repository = next((f.value for f in facts if f.id == "identity:repository"), None)
        observation = observe_pypi(
            name.value, version.value if version else None, repository=repository
        )
        polarity, confidence, detail = install_verdict(
            conclusive=observation.error is None,
            published=observation.found,
            repository_matched=observation.repository_matched,
            summary=observation.summary,
        )
        return [
            Fact(
                install.id,
                install.kind,
                install.value,
                (
                    Evidence(
                        install.evidence[0].path, "distribution name declared by the manifest"
                    ),
                    Evidence(observation.url, detail),
                ),
                polarity=polarity,
                confidence=confidence,
            )
        ], [observation.probe]

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        """Install the clone into a fresh venv and run every README example against it.

        Delegates to ``python_examples.verify_python_examples``: a real ``pip install`` and a
        real subprocess run of each candidate in a disposable profile, classified from what
        actually happened (EXECUTED/FAILED/TIMED_OUT/NEEDS_INPUT/NOT_VERIFIED) - never a
        fabricated receipt.
        """
        return verify_python_examples(root, tree_paths, candidates, workspace)

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        return format_claims(code)

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        return format_declarations(root, tree_paths)

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        facts: list[Fact] = []
        merged: dict[str, str] = {}
        sources: dict[str, str] = {}
        for filename, info in parse_manifests(root).items():
            for key, value in info.items():
                if key not in merged:
                    merged[key] = value
                    sources[key] = filename

        def add(
            kind: Any,
            slug: str,
            key: str,
            detail: str,
            attributes: dict[str, str] | None = None,
        ) -> None:
            if key in merged:
                facts.append(
                    Fact(
                        fact_id(kind, slug),
                        kind,
                        merged[key],
                        (Evidence(sources[key], detail),),
                        attributes=attributes,
                    )
                )

        add("package", "name", "name", "distribution name declared by the manifest")
        add("package", "version", "version", "version declared by the manifest")
        # The floor's field name differs by manifest: PEP 621 `requires-python` in pyproject.toml,
        # setuptools' `python_requires` in setup.cfg/setup.py. The renderer cites this attribute,
        # so a pyproject-only repository is never said to declare `python_requires` (real Lane R
        # false claims: Cells, Email and HTML Python).
        floor_field = _FLOOR_FIELDS.get(sources.get("requires_python", ""), "python_requires")
        add(
            "package",
            "python_requires",
            "requires_python",
            f"{floor_field} declared",
            {"floor_declaration": floor_field},
        )
        add("package", "python_versions", "python_classifier_versions", "Python classifiers")
        add("package", "license", "license", "license declared by the manifest")
        # The dependency snapshot: every required requirement, or the verified-zero marker citing
        # the manifest clause that proves it, then each extra's requirements in the optional or
        # development bucket.
        for requirement in json.loads(merged.get("dependencies", "[]")):
            facts.append(
                _requirement_fact(
                    fact_id("dependency", requirement),
                    requirement,
                    sources["dependencies"],
                    "install requirement declared",
                )
            )
        if "dependencies_dynamic" in merged:
            facts.append(
                Fact(
                    fact_id("dependency", "dynamic"),
                    "dependency",
                    "dynamic",
                    (Evidence(sources["dependencies_dynamic"], merged["dependencies_dynamic"]),),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )
        elif "dependencies" not in merged and "name" in merged:
            # A parsed manifest that declares no requirement proves verified-zero: an empty
            # list when the manifest spells one out, else the absence of the declaration.
            path = sources.get("dependency_evidence", sources["name"])
            clause = merged.get("dependency_evidence") or _NOT_DECLARED[sources["name"]]
            facts.append(
                Fact(fact_id("dependency", "none"), "dependency", "none", (Evidence(path, clause),))
            )
        for extra, requirements in json.loads(merged.get("extras", "{}")).items():
            bucket = "development" if extra.lower() in _DEVELOPMENT_EXTRAS else "optional"
            for requirement in requirements:
                facts.append(
                    _requirement_fact(
                        fact_id("dependency", bucket, extra, requirement),
                        requirement,
                        sources["extras"],
                        f"extra '{extra}' declared",
                    )
                )

        if "name" in merged:
            facts.append(
                Fact(
                    fact_id("install_command", "pip"),
                    "install_command",
                    f"pip install {merged['name']}",
                    (Evidence(sources["name"], "package-registry observation pending"),),
                    polarity="UNRESOLVED",
                    confidence=0.5,
                )
            )

        declared = merged.get("declared_packages", "")
        locations = (
            [(dotted, "") for dotted in declared.split(",")]
            if declared
            else package_locations(tree_paths)
        )
        shipped = None if declared else shipped_path_filter(read_root_manifests(root), tree_paths)
        for dotted, directory in locations:
            evidence_path = sources["declared_packages"] if declared else f"{directory}/__init__.py"
            if shipped is not None and not shipped[1](evidence_path):
                continue  # a tree package the build does not ship (BL-065)
            facts.append(
                Fact(
                    fact_id("import_path", dotted),
                    "import_path",
                    dotted,
                    (Evidence(evidence_path, "package declared" if declared else "package dir"),),
                )
            )
        return facts


# The registry discovers a plugin by module name and this attribute; it never lists plugins.
PLUGIN = PythonPlugin()
