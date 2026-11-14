"""BL-065, Python variant: the public surface honours the build's package list.

M9 round 43559491132, Words Python Lane L control ab8a03 (seal at 2d2efee2): "The library ships 198
public types" counted the 9 classes of ``ApiExamples/``, a tree package the wheel never contains --
``pyproject.toml`` ``[tool.hatch.build.targets.wheel] packages = ["aspose"]`` ships 189.

The fixtures (``tests/fixtures/shipped_packages/*.json``) are real: each repository's root build
manifests verbatim, its tracked ``.py`` paths, and the class/enum/module ``public_symbol`` and
``import_path`` facts of its seal at that revision. Words Python is the positive case; the other five
Python repositories of the portfolio are the negative controls (every package-list shape the
portfolio uses: setuptools list, setuptools find with include/exclude, a literal ``setup.py``
``find_packages`` call, and no manifest at all) -- none of them loses a type.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.extractors.platforms.python import (
    PLUGIN,
    shipped_path_filter,
    unshipped_fact,
)
from repo_presenter.readme.validation.surface_claims import type_counts

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "shipped_packages"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _facts(case: dict) -> FactsDocument:
    facts = []
    for row in case["surface"]:
        attributes = {"symbol_kind": row["symbol_kind"]} if row["kind"] == "public_symbol" else None
        facts.append(Fact(row["id"], row["kind"], row["value"],
                          tuple(Evidence(path, row["detail"]) for path in row["paths"]), polarity=row["polarity"],
                          attributes=attributes))
    return FactsDocument(case["repository"], case["revision"], tuple(facts))


def _types(document: FactsDocument) -> int:
    return type_counts(document)[0]


def test_words_python_ships_only_the_aspose_package() -> None:
    case = _load("words_python")
    clause, ships = shipped_path_filter(case["manifests"], case["tree_py"])
    assert clause == "tool.hatch.build.targets.wheel.packages"
    document = _facts(case)
    assert _types(document) == 198  # the sealed count
    dropped = [fact for fact in document.facts if unshipped_fact(fact, ships)]
    dropped_types = sorted(f.value for f in dropped if (f.attributes or {}).get("symbol_kind") in ("class", "enum"))
    assert len(dropped_types) == 9 and all(v.startswith("ApiExamples.") for v in dropped_types)
    assert "import_path:apiexamples" in {f.id for f in dropped}
    kept = FactsDocument(document.repository, document.source_revision,
                         tuple(f for f in document.facts if f not in dropped))
    assert _types(kept) == 189
    assert not any("ApiExamples" in path for f in kept.facts for path in (e.path for e in f.evidence))


@pytest.mark.parametrize(
    ("name", "clause"),
    [
        ("cells_python", "tool.setuptools.packages"),
        ("pdf_python", "tool.setuptools.packages.find"),
        ("email_python", "tool.setuptools.packages.find"),
        ("threed_python", "setup.py packages"),
    ],
)
def test_other_python_builds_keep_every_type(name: str, clause: str) -> None:
    """Negative controls: the package list is read, and no type the facts count is outside it."""
    case = _load(name)
    found = shipped_path_filter(case["manifests"], case["tree_py"])
    assert found is not None and found[0] == clause
    document = _facts(case)
    dropped = [f for f in document.facts if unshipped_fact(f, found[1])]
    assert not [f for f in dropped if (f.attributes or {}).get("symbol_kind") in ("class", "enum")]
    if name == "pdf_python":  # fuzz/ is a tree package the find(include=aspose_pdf*) never ships
        assert {f.value for f in dropped} == {"fuzz", "fuzz.run", "fuzz.targets"}


def test_no_build_manifest_means_no_narrowing() -> None:
    case = _load("psd_python")  # no pyproject.toml, setup.cfg or setup.py at 2271c228
    assert case["manifests"] == {}
    assert shipped_path_filter(case["manifests"], case["tree_py"]) is None


def test_a_package_list_naming_nothing_in_the_tree_fails_open() -> None:
    manifests = {"pyproject.toml": '[tool.hatch.build.targets.wheel]\npackages = ["missing"]\n'}
    assert shipped_path_filter(manifests, ["aspose/__init__.py", "ApiExamples/x.py"]) is None


def test_the_extractor_drops_unshipped_packages(tmp_path: Path) -> None:
    """The plugin's surface: the same tree with and without the hatch package list."""
    (tmp_path / "aspose").mkdir()
    (tmp_path / "aspose" / "__init__.py").write_text("class Document:\n    pass\n", encoding="utf-8")
    (tmp_path / "ApiExamples").mkdir()
    (tmp_path / "ApiExamples" / "__init__.py").write_text("class ConvertDocument:\n    pass\n", encoding="utf-8")
    tree = ["ApiExamples/__init__.py", "aspose/__init__.py", "pyproject.toml"]
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n\n[tool.hatch.build.targets.wheel]\npackages = ["aspose"]\n', encoding="utf-8")
    shipped = {f.value for f in PLUGIN.surface_facts(tmp_path, tree)}
    assert "aspose.Document" in shipped and not any(v.startswith("ApiExamples") for v in shipped)
    imports = {f.value for f in PLUGIN.manifest_facts(tmp_path, tmp_path / "pyproject.toml", tree) if f.kind == "import_path"}
    assert imports == {"aspose"}
    # negative control: no package list -> the tree discovery is unchanged
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    unrestricted = {f.value for f in PLUGIN.surface_facts(tmp_path, tree)}
    assert "ApiExamples.ConvertDocument" in unrestricted


def test_recertification_narrows_the_sealed_facts_and_the_count_detector_follows() -> None:
    """``recertify.shipped_facts`` over the sealed facts; the Lane L count edit then writes 189."""
    from repo_presenter.core.registry_entry_stub import RegistryEntryStub
    from repo_presenter.readme.correction.detectors.stale_type_count import stale_type_count
    from repo_presenter.readme.correction.model import Context
    from repo_presenter.recertify import SourceSnapshot, shipped_facts

    case = _load("words_python")
    document = _facts(case)
    source = SourceSnapshot(tree_paths=tuple(case["tree_py"]), readme=b"", manifests=case["manifests"])
    narrowed, clause = shipped_facts(document, "python", source)
    assert clause == "tool.hatch.build.targets.wheel.packages" and _types(narrowed) == 189
    # the live README's own sentence (README.original.md line 328 at 2d2efee2)
    readme = ("the target format is otherwise inferred from the output file's extension. The library ships 146\n"
              "public types across the readers and writers.\n")
    entry = RegistryEntryStub(repository=case["repository"], family="words", platform="python", ecosystem="python")
    for facts, expected in ((document, "198"), (narrowed, "189")):
        (edit,) = stale_type_count(Context(entry=entry, facts=facts, readme=readme, tree_paths=(), readme_path="README.md")).edits
        assert edit.replacement == expected
    # negative controls: no manifests, or an ecosystem without a package list, change nothing
    assert shipped_facts(document, "python", SourceSnapshot(tree_paths=(), readme=b""))[1] is None
    assert shipped_facts(document, "dotnet", source)[1] is None
