"""Project-file and package-trait facts: what the build, test and packaging files state.

Class B of the 2026-11-06 unsupported-claim audit (build/test project files 12 cases, package
metadata 10): test-project dependencies, CMake settings and presets, Makefile targets and their
recipes, pytest configuration, the files a tree does or does not hold, test names and their
documentation; third-party notice entries and licence files, a runtime floor stated only in
``requirements.txt``, whether a package carries native code, and whether a Python package imports
anything beyond its standard library.

Each fact restates one file at one line. A trait the tree contradicts is recorded CONTRADICTED with
the contradicting file as its evidence (a "pure Python" package that ships a C extension source).
These are evidence kinds (``project_file``, ``package_trait``): no renderer reads them, so adding
them changes no rendered README.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from repo_presenter.core.facts import Evidence, Fact, fact_id
from repo_presenter.readme.evidence.facts.source_text import (
    is_test_path,
    language_of,
    leading_comment,
    line_at,
    line_offsets,
    product_sources,
    read_text,
)

TEST_CAP = 3000
_PLACEHOLDERS = frozenset({".gitkeep", ".keep", ".gitignore", ".placeholder", "README.md"})


class _Out:
    def __init__(self, taken: set[str]) -> None:
        self.ids = taken
        self.facts: list[Fact] = []
        self.tests = 0

    def add(
        self,
        kind: str,
        parts: Sequence[str],
        value: str,
        evidence: Sequence[tuple[str, int | None, str]],
        attributes: dict[str, str] | None = None,
        polarity: str = "SUPPORTED",
    ) -> None:
        try:
            identifier = fact_id(kind, *parts)  # type: ignore[arg-type]
        except ValueError:
            return
        if identifier in self.ids or not value.strip():
            return
        self.ids.add(identifier)
        cleaned = {k: v for k, v in (attributes or {}).items() if k and v}
        self.facts.append(
            Fact(
                identifier,
                kind,  # type: ignore[arg-type]
                value,
                tuple(
                    Evidence(path, f"line {line}; {detail}" if line else detail)
                    for path, line, detail in evidence
                ),
                polarity=polarity,  # type: ignore[arg-type]
                attributes=cleaned or None,
            )
        )


def _line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    return text.count("\n", 0, index) + 1 if index >= 0 else 0


# --- build and test files ---------------------------------------------------------------------

_PACKAGE_REFERENCE = re.compile(
    r"<PackageReference\s+Include=\"([^\"]+)\"(?:\s+Version=\"([^\"]+)\")?", re.IGNORECASE
)


def _test_projects(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        if not path.endswith((".csproj", ".fsproj", ".vbproj")):
            continue
        text = read_text(root, path) or ""
        is_test = (
            is_test_path(path)
            or "Microsoft.NET.Test.Sdk" in text
            or re.search(r"<IsTestProject>\s*true", text, re.IGNORECASE) is not None
        )
        if not is_test:
            continue
        offsets = line_offsets(text)
        for match in _PACKAGE_REFERENCE.finditer(text):
            name, version = match.group(1), match.group(2) or ""
            line = line_at(offsets, match.start())
            out.add(
                "project_file",
                ["test_dependency", name],
                f"{name} {version}".strip(),
                [(path, line, "PackageReference of a test project")],
                {"scope": "test", "project": path, "package": name, "version": version},
            )


_CMAKE_SET = re.compile(r"^\s*set\s*\(\s*(CMAKE_[A-Z_]+)\s+([^)\s]+)[^)]*\)", re.IGNORECASE | re.MULTILINE)
_CMAKE_OPTION = re.compile(r"^\s*option\s*\(\s*(\w+)\s+\"([^\"]*)\"\s+(\w+)\s*\)", re.IGNORECASE | re.MULTILINE)
_CMAKE_FIND = re.compile(r"^\s*(find_package|FetchContent_Declare|pkg_check_modules|ExternalProject_Add)\s*\(\s*(\w+)", re.IGNORECASE | re.MULTILINE)


def _cmake(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        name = PurePosixPath(path).name
        if name == "CMakeLists.txt" and path.count("/") <= 1:
            text = read_text(root, path) or ""
            offsets = line_offsets(text)
            for match in _CMAKE_SET.finditer(text):
                out.add(
                    "project_file",
                    ["cmake", path, match.group(1)],
                    f"{match.group(1)} {match.group(2)}",
                    [(path, line_at(offsets, match.start()), "CMake set()")],
                    {"file": path, "setting": match.group(1), "value": match.group(2)},
                )
            for match in _CMAKE_OPTION.finditer(text):
                out.add(
                    "project_file",
                    ["cmake_option", path, match.group(1)],
                    f"option {match.group(1)} (default {match.group(3)}): {match.group(2)}",
                    [(path, line_at(offsets, match.start()), "CMake option()")],
                    {"file": path, "option": match.group(1), "default": match.group(3)},
                )
            found = [(m.group(1), m.group(2), line_at(offsets, m.start())) for m in _CMAKE_FIND.finditer(text)]
            if path == "CMakeLists.txt":
                out.add(
                    "project_file",
                    ["cmake_external_packages", path],
                    "external packages: " + (", ".join(f"{n}" for _, n, _ in found) if found else "none (no find_package, FetchContent, pkg_check_modules or ExternalProject call)"),
                    [(path, found[0][2] if found else None, "the top-level CMakeLists.txt")],
                    {"file": path, "count": str(len(found))},
                )
        if name in ("CMakePresets.json", "CMakeUserPresets.json"):
            text = read_text(root, path) or ""
            try:
                presets = json.loads(text)
            except json.JSONDecodeError:
                continue
            for preset in presets.get("configurePresets", []) if isinstance(presets, dict) else []:
                if not isinstance(preset, dict) or not preset.get("name"):
                    continue
                described = [f"configure preset {preset['name']}"]
                for key in ("generator", "binaryDir", "toolchainFile"):
                    if preset.get(key):
                        described.append(f"{key} {preset[key]}")
                cache = preset.get("cacheVariables") or {}
                if isinstance(cache, dict):
                    described.extend(f"{k}={v if not isinstance(v, dict) else v.get('value')}" for k, v in sorted(cache.items()))
                out.add(
                    "project_file",
                    ["cmake_preset", path, str(preset["name"])],
                    "; ".join(described),
                    [(path, _line_of(text, f'"{preset["name"]}"'), "CMake configure preset")],
                    {"file": path, "preset": str(preset["name"]), "generator": str(preset.get("generator") or "")},
                )


_MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.%/-]+)\s*:(?!=)\s*([^\n#]*?)\s*(?:#+\s*(.*))?$")


def _makefiles(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        if PurePosixPath(path).name not in ("Makefile", "makefile", "GNUmakefile") or path.count("/") > 1:
            continue
        text = read_text(root, path) or ""
        lines = text.splitlines()
        for index, line in enumerate(lines):
            match = _MAKE_TARGET.match(line)
            if not match or match.group(1).startswith("."):
                continue
            recipe: list[str] = []
            cursor = index + 1
            while cursor < len(lines) and (lines[cursor].startswith("\t") or not lines[cursor].strip() and cursor + 1 < len(lines) and lines[cursor + 1].startswith("\t")):
                if lines[cursor].strip():
                    recipe.append(lines[cursor].strip().lstrip("@-"))
                cursor += 1
            prerequisites = match.group(2).strip()
            target = match.group(1)
            described = (match.group(3) or "").strip()
            value = f"make {target}"
            if prerequisites:
                value += f" (depends on {prerequisites})"
            if recipe:
                value += ": " + " && ".join(recipe)
            if described:
                value += f" -- {described}"
            out.add(
                "project_file",
                ["make_target", path, target],
                value[:600],
                [(path, index + 1, "Makefile target")],
                {"file": path, "target": target, "prerequisites": prerequisites, "recipe": "\n".join(recipe)[:600], "description": described},
            )


def _pytest(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        name = PurePosixPath(path).name
        if path.count("/") > 1 or name not in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
            continue
        text = read_text(root, path) or ""
        options: dict[str, str] = {}
        if name == "pyproject.toml":
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                continue
            section = ((data.get("tool") or {}).get("pytest") or {}).get("ini_options")
            if isinstance(section, dict):
                options = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in section.items()}
            header = "[tool.pytest.ini_options]"
        else:
            header = "[pytest]" if name in ("pytest.ini", "tox.ini") else "[tool:pytest]"
            block = re.search(re.escape(header) + r"\s*\n(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
            if block:
                for line in block.group(1).splitlines():
                    if "=" in line and not line.lstrip().startswith(("#", ";")):
                        key, _, value = line.partition("=")
                        options[key.strip()] = value.strip()
        for key, value in sorted(options.items()):
            out.add(
                "project_file",
                ["pytest", path, key],
                f"pytest {key} = {value}",
                [(path, _line_of(text, header) or None, f"pytest configuration {header}")],
                {"file": path, "option": key, "value": value},
            )


def _inventory(out: _Out, tree_paths: Sequence[str], ecosystem: str) -> None:
    directories: dict[str, list[str]] = {}
    for path in tree_paths:
        parent = PurePosixPath(path).parent.as_posix()
        directories.setdefault(parent, []).append(PurePosixPath(path).name)
    has_children = {PurePosixPath(d).parent.as_posix() for d in directories}
    for directory, names in sorted(directories.items()):
        if directory == "." or directory in has_children:
            continue
        if names and all(name in _PLACEHOLDERS - {"README.md"} for name in names):
            out.add(
                "project_file",
                ["empty_directory", directory],
                f"{directory}/ holds no files but {', '.join(sorted(names))}",
                [(f"{directory}/{min(names)}", None, "the directory's only tracked file is a placeholder")],
                {"directory": directory},
            )
    if ecosystem == "python":
        manifests = [p for p in ("pyproject.toml", "setup.py", "setup.cfg") if p in tree_paths]
        if not manifests:
            evidence = "requirements.txt" if "requirements.txt" in tree_paths else (tree_paths[0] if tree_paths else ".")
            out.add(
                "project_file",
                ["python_package_manifest"],
                "no pyproject.toml, setup.py or setup.cfg at the repository root",
                [(evidence, None, "the tracked root files hold no Python package manifest")],
                {"present": "none"},
            )


_TEST_DECL = {
    "csharp": re.compile(r"^\s*\[(?:Fact|Theory|Test|TestMethod|TestCase)[^\]]*\]\s*$"),
    "java": re.compile(r"^\s*@(?:Test|ParameterizedTest|RepeatedTest)\b"),
    "rust": re.compile(r"^\s*#\[(?:tokio::)?test\]"),
}
_METHOD_NAME = re.compile(r"\b(?:void|async\s+Task|Task|fn)\s+(\w+)\s*\(")
_PY_TEST = re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)\s*\(", re.MULTILINE)
_GO_TEST = re.compile(r"^func\s+(Test\w+)\s*\(", re.MULTILINE)
_JS_TEST = re.compile(r"\b(?:it|test)\s*\(\s*([\"'`])(.+?)\1", re.MULTILINE)
_CPP_TEST = re.compile(r"^\s*(?:TEST|TEST_F|TEST_CASE)\s*\(\s*(\w+)\s*,?\s*(\w*)", re.MULTILINE)


def _words(name: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|_", " ", name)
    return " ".join(spaced.split()).lower()


def _tests(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in sorted(tree_paths):
        language = language_of(path)
        if language is None or not is_test_path(path) or out.tests >= TEST_CAP:
            continue
        text = read_text(root, path)
        if text is None:
            continue
        lines = text.splitlines()
        found: list[tuple[str, int, str]] = []
        marker = _TEST_DECL.get(language)
        if marker is not None:
            for index, line in enumerate(lines):
                if not marker.match(line):
                    continue
                for ahead in range(index + 1, min(index + 6, len(lines))):
                    named = _METHOD_NAME.search(lines[ahead])
                    if named:
                        doc, _ = leading_comment(lines, index, language)
                        found.append((named.group(1), ahead + 1, doc))
                        break
        elif language == "python":
            tree = None
            try:
                tree = ast.parse(text)
            except (SyntaxError, ValueError):
                pass
            for node in ast.walk(tree) if tree else ():
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test"):
                    doc = ast.get_docstring(node) or ""
                    found.append((node.name, node.lineno, " ".join(doc.split())))
        elif language == "go":
            for match in _GO_TEST.finditer(text):
                number = text.count("\n", 0, match.start()) + 1
                doc, _ = leading_comment(lines, number - 1, "go")
                found.append((match.group(1), number, doc))
        elif language in ("typescript", "javascript"):
            for match in _JS_TEST.finditer(text):
                found.append((match.group(2), text.count("\n", 0, match.start()) + 1, ""))
        elif language == "cpp":
            for match in _CPP_TEST.finditer(text):
                name = "_".join(p for p in (match.group(1), match.group(2)) if p)
                found.append((name, text.count("\n", 0, match.start()) + 1, ""))
        for name, number, doc in found:
            if out.tests >= TEST_CAP:
                break
            words = name if " " in name else _words(name)
            value = f"test {words}" + (f": {doc}" if doc else "")
            before = len(out.facts)
            out.add(
                "project_file",
                ["test", path, name[:80]],
                value[:800],
                [(path, number, "test case")],
                {"test": name, "file": path, "docstring_full": doc[:2000]},
            )
            out.tests += len(out.facts) - before


# --- package traits ---------------------------------------------------------------------------

_LICENCES = re.compile(
    r"\b(MIT|ISC|BSD[ -]?[234]-Clause|BSD|Apache(?:[ -]License)?[ ,-]*(?:Version )?2\.0|Apache-2\.0|"
    r"MPL[ -]?2\.0|LGPL[ -v]*[0-9.]*(?:-or-later|\+)?|GPL[ -v]*[0-9.]*(?:-or-later|\+)?|"
    r"Zlib|Unlicense|CC0[ -]1\.0|PSF|Python Software Foundation|OFL[ -]?1\.1|SIL Open Font License|"
    r"Boost Software License|BSL-1\.0|Public Domain)\b",
    re.IGNORECASE,
)
_NOTICE_FILES = re.compile(r"(?:^|/)(?:THIRD[-_]?PARTY[-_ ]?(?:NOTICES?|LICEN[CS]ES?)[^/]*|NOTICES?(?:\.\w+)?|ThirdPartyNotices[^/]*)$", re.IGNORECASE)
_LICENCE_DIR_FILE = re.compile(r"^(?:licen[cs]es?|third[-_]?party)/([^/]+?)(?:[._-]?licen[cs]e)?(?:\.(?:txt|md))?$", re.IGNORECASE)
_HEADING = re.compile(r"^\s*(?:#{1,6}\s+|[-*]\s+\*\*|\*\*)([A-Za-z0-9][\w .+/@-]{1,60}?)(?:\*\*)?\s*(?:[(:-].*)?$")


def _notices(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        match = _LICENCE_DIR_FILE.match(path)
        if match and not _NOTICE_FILES.search(path):
            component = re.sub(r"[._-]?licen[cs]e$", "", match.group(1), flags=re.IGNORECASE)
            text = read_text(root, path) or ""
            licence = _LICENCES.search(text[:3000])
            out.add(
                "package_trait",
                ["licence_file", component],
                f"licence notice file for {component}: {path}" + (f" ({licence.group(1)})" if licence else ""),
                [(path, None, "a licence file the repository ships for a component")],
                {"component": component, "file": path, "licence": licence.group(1) if licence else ""},
            )
        if not _NOTICE_FILES.search(path) or path.count("/") > 1:
            continue
        text = read_text(root, path) or ""
        lines = text.splitlines()
        for index, line in enumerate(lines):
            heading = _HEADING.match(line)
            if heading is None:
                continue
            component = heading.group(1).strip().strip("*").strip()
            window = "\n".join(lines[index : index + 8])
            licence = _LICENCES.search(window)
            if licence is None or len(component) < 2 or _LICENCES.fullmatch(component):
                continue
            out.add(
                "package_trait",
                ["notice", component],
                f"{component}: {licence.group(1)} (third-party notice)",
                [(path, index + 1, "third-party notice entry")],
                {"component": component, "licence": licence.group(1), "file": path},
            )


_REQUIRES_PYTHON = re.compile(r"^\s*python\s*((?:[<>=!~]=?\s*[\d.*]+\s*,?\s*)+)", re.IGNORECASE | re.MULTILINE)


def _runtime_floor(out: _Out, root: Path, tree_paths: Sequence[str]) -> None:
    for path in tree_paths:
        if PurePosixPath(path).name not in ("requirements.txt", "requirements.in") or path.count("/") > 1:
            continue
        text = read_text(root, path) or ""
        match = _REQUIRES_PYTHON.search(text)
        if match:
            spec = "".join(match.group(1).split())
            out.add(
                "package_trait",
                ["runtime_floor", "python", path],
                f"python{spec}",
                [(path, text.count("\n", 0, match.start()) + 1, "Python version stated in a requirements file")],
                {"runtime": "python", "specifier": spec, "file": path},
            )


_NATIVE_SUFFIXES = (".c", ".cc", ".cpp", ".cxx", ".pyx", ".pxd", ".f90", ".cu")
_NATIVE_BACKENDS = ("maturin", "scikit_build", "mesonpy", "setuptools_rust", "pybind11", "cffi")


def _python_traits(out: _Out, root: Path, tree_paths: Sequence[str], facts: Sequence[Fact]) -> None:
    roots = sorted(
        {
            PurePosixPath(path).parent.as_posix()
            for path in tree_paths
            if path.endswith("/__init__.py") and not is_test_path(path)
        },
        key=len,
    )
    packages = [r for r in roots if not any(r.startswith(o + "/") for o in roots if o != r)]
    packages = [p for p in packages if PurePosixPath(p).parts[0] not in ("tests", "test", "examples", "docs", "scripts", "benchmarks")]
    if not packages:
        return
    manifests = [p for p in ("pyproject.toml", "setup.py", "setup.cfg") if p in tree_paths]
    native = [p for p in tree_paths if p.endswith(_NATIVE_SUFFIXES) and any(p.startswith(k + "/") for k in packages)]
    backend = ""
    for manifest in manifests:
        text = read_text(root, manifest) or ""
        if re.search(r"\bext_modules\b|\bExtension\s*\(", text):
            native.append(f"{manifest} (declares extension modules)")
        found = next((b for b in _NATIVE_BACKENDS if b in text.replace("-", "_")), "")
        backend = backend or found
    evidence = [(packages[0], None, "the package source tree")] + [(m, None, "package manifest") for m in manifests]
    if native or backend:
        out.add(
            "package_trait",
            ["pure_source", "python"],
            "pure-Python package: no compiled extension sources",
            [(native[0].split(" ")[0] if native else manifests[0], None, f"native build input: {native[0] if native else backend}")],
            {"language": "python", "native": ", ".join(native[:10]) or backend},
            polarity="CONTRADICTED",
        )
    else:
        out.add(
            "package_trait",
            ["pure_source", "python"],
            "pure-Python package: no compiled extension sources",
            evidence,
            {"language": "python", "packages": ", ".join(packages), "scope": "the package's own sources; dependencies are listed by the dependency facts"},
        )
    # Every import of the package's own modules: the standard library, the package itself, or not.
    stdlib = set(sys.stdlib_module_names)
    own = {PurePosixPath(p).parts[-1] for p in packages} | {PurePosixPath(p).parts[0] for p in packages}
    third: dict[str, str] = {}
    for path in product_sources(tree_paths):
        if not path.endswith(".py") or not any(path.startswith(k + "/") for k in packages):
            continue
        try:
            tree = ast.parse(read_text(root, path) or "")
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top in stdlib or top in own or top == "__future__":
                    continue
                third.setdefault(top, f"{path}:{getattr(node, 'lineno', 0)}")
    value = "imports only the Python standard library and the package's own modules"
    if third:
        first = min(third.items())[1]
        path, _, line = first.rpartition(":")
        out.add(
            "package_trait",
            ["stdlib_only", "python"],
            value,
            [(path, int(line), f"imports {min(third)}")],
            {"third_party_imports": ", ".join(f"{k} ({v})" for k, v in sorted(third.items())[:20])},
            polarity="CONTRADICTED",
        )
    else:
        out.add("package_trait", ["stdlib_only", "python"], value, evidence[:1], {"packages": ", ".join(packages)})


_NATIVE_MARKERS = {
    "go": (re.compile(r'^\s*import\s+"C"\s*$', re.MULTILINE), "cgo import \"C\"", "pure Go: no cgo"),
    "csharp": (re.compile(r"\[(?:DllImport|LibraryImport)\s*\("), "P/Invoke declaration", "pure managed .NET code: no P/Invoke declarations"),
    "java": (re.compile(r"^\s*(?:(?:public|private|protected|static|final)\s+)*native\s+[\w<>\[\]]+\s+\w+\s*\(", re.MULTILINE), "JNI native method", "pure Java: no native methods"),
    "rust": (re.compile(r'#\[link\(|extern\s+"C"\s*\{'), "FFI block", "pure Rust: no FFI link blocks"),
}


def _native_traits(out: _Out, root: Path, tree_paths: Sequence[str], ecosystem: str) -> None:
    language = {"go": "go", "net": "csharp", "java": "java", "rust": "rust"}.get(ecosystem)
    if language is None:
        return
    pattern, marker, value = _NATIVE_MARKERS[language]
    sources = [p for p in product_sources(tree_paths) if language_of(p) == language]
    if not sources:
        return
    hit = None
    for path in sources:
        text = read_text(root, path) or ""
        match = pattern.search(text)
        if match:
            hit = (path, text.count("\n", 0, match.start()) + 1)
            break
    if language == "rust" and hit is None and "build.rs" in tree_paths:
        hit = ("build.rs", 1)
    if hit:
        out.add("package_trait", ["pure_source", language], value, [(hit[0], hit[1], marker)], {"language": language}, polarity="CONTRADICTED")
    else:
        out.add(
            "package_trait",
            ["pure_source", language],
            value,
            [(sources[0], None, f"no {marker} in any of the {len(sources)} product source files")],
            {"language": language, "files_checked": str(len(sources))},
        )


def with_project_detail(
    root: Path, tree_paths: Sequence[str], ecosystem: str, facts: Sequence[Fact]
) -> list[Fact]:
    """``facts`` plus every project-file and package-trait fact the tree supports."""
    out = _Out({fact.id for fact in facts})
    tree = list(tree_paths)
    _test_projects(out, root, tree)
    _cmake(out, root, tree)
    _makefiles(out, root, tree)
    _pytest(out, root, tree)
    _inventory(out, tree, ecosystem)
    _tests(out, root, tree)
    _notices(out, root, tree)
    _runtime_floor(out, root, tree)
    if ecosystem == "python":
        _python_traits(out, root, tree, facts)
    _native_traits(out, root, tree, ecosystem)
    return [*facts, *out.facts]


__all__ = ["TEST_CAP", "with_project_detail"]
