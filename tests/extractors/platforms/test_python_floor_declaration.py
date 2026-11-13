"""The Python floor names the field its manifest actually declares (R36(b) class C1a).

Real shapes: Aspose.Cells-FOSS-for-Python, Aspose.Email-FOSS-for-Python and
Aspose.HTML-FOSS-for-Python each declare ``requires-python = ">=3.10"`` in ``pyproject.toml`` and
ship neither ``setup.cfg`` nor ``setup.py``. The renderer printed "declares `python_requires`" and
``python_requires=">=3.10"`` in `pyproject.toml` for all three - seven confirmed false claims in
``data/readme_findings.json``. A setup.cfg/setup.py project does declare ``python_requires``, and
keeps that name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.python import PythonPlugin
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import (
    RenderContext,
    _dependencies,
    _installation,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = load_registry(ROOT / "data" / "registry.json")
# The head of Aspose.Cells-FOSS-for-Python's pyproject.toml at 952317ca (lines 1-11).
CELLS_PYPROJECT = """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "aspose-cells-foss"
version = "26.10.0"
description = "A Python library for creating, reading, and modifying Excel files (.xlsx format)"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
"""
REGISTER_REPOSITORIES = (
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    "aspose-email-foss/Aspose.Email-FOSS-for-Python",
    "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
)


def _floor(root: Path, tree: list[str]) -> Fact:
    facts = PythonPlugin().manifest_facts(root, root / tree[0], tree)
    return next(f for f in facts if f.id == "package:python_requires")


def test_a_pyproject_floor_is_declared_by_requires_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(CELLS_PYPROJECT, encoding="utf-8")
    floor = _floor(tmp_path, ["pyproject.toml"])
    assert floor.value == ">=3.10"
    assert floor.attributes == {"floor_declaration": "requires-python"}
    assert floor.evidence == (Evidence("pyproject.toml", "requires-python declared"),)


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("setup.cfg", "[metadata]\nname = cfg-name\n[options]\npython_requires = >=3.9\n"),
        ("setup.py", 'from setuptools import setup\nsetup(name="py-name", python_requires=">=3.9")\n'),
    ],
)
def test_a_setuptools_floor_is_declared_by_python_requires(
    tmp_path: Path, name: str, text: str
) -> None:
    (tmp_path / name).write_text(text, encoding="utf-8")
    floor = _floor(tmp_path, [name])
    assert floor.attributes == {"floor_declaration": "python_requires"}
    assert floor.evidence == (Evidence(name, "python_requires declared"),)


def _context(repository: str, *facts: Fact) -> RenderContext:
    entry = next(e for e in REGISTRY.entries if e.repository == repository)
    plugin_for(entry.ecosystem)
    return RenderContext(
        entry,
        FactsDocument(repository, "0" * 40, tuple(facts)),
        {"sections": []},
        {"units": []},
        {"dispositions": []},
    )


def _open_quotes(repository: str) -> list[str]:
    register = json.loads((ROOT / "data" / "readme_findings.json").read_text(encoding="utf-8"))
    return [
        row["quote"]
        for row in register["findings"]
        if row["repository"] == repository
        and row["status"] == "OPEN"
        and "python_requires" in row["quote"]
    ]


@pytest.mark.parametrize("repository", REGISTER_REPOSITORIES)
def test_the_rendered_floor_no_longer_prints_the_register_quotes(
    tmp_path: Path, repository: str
) -> None:
    (tmp_path / "pyproject.toml").write_text(CELLS_PYPROJECT, encoding="utf-8")
    floor = _floor(tmp_path, ["pyproject.toml"])
    context = _context(repository, floor)
    rendered = "\n".join([*_installation(context), *_dependencies(context)])
    assert "The package declares `requires-python` as `>=3.10`." in rendered
    assert (
        '- Requires Python 3.10 or later (`requires-python=">=3.10"` in `pyproject.toml`).'
        in rendered
    )
    quotes = _open_quotes(repository)
    assert quotes, "the register rows this fix corrects are expected to be open"
    for quote in quotes:
        assert quote not in rendered


def test_a_stored_floor_without_the_attribute_keeps_the_ecosystem_name() -> None:
    """A fact sealed before the attribute existed re-renders to its own bytes."""
    stored = Fact(
        "package:python_requires",
        "package",
        ">=3.9",
        (Evidence("setup.py", "python_requires declared"),),
    )
    lines = _installation(_context(REGISTER_REPOSITORIES[0], stored))
    assert "The package declares `python_requires` as `>=3.9`." in lines
