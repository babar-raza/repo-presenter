"""Owner rulings enforced by CI, not only written down (docs/CONSOLIDATED_GOALS_2026-11-06.md Part B).

R10 "one standard for every candidate": no product-specific special case may enter the pipeline code. A
registry repository's slug or name may appear in a comment or docstring (evidence citations), never in an
executable string a condition could test.

R9 "attribution internal only": no prompt instructs the model to print an attribution, and the renderer's
attribution path prints nothing.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "src" / "repo_presenter"


def _registry_names() -> list[str]:
    entries = json.loads((ROOT / "data" / "registry.json").read_text(encoding="utf-8"))["entries"]
    names = {part for e in entries for part in (e["repository"], e["repository"].split("/", 1)[1])}
    return sorted(names, key=len, reverse=True)


def _docstring_ids(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                found.add(id(body[0].value))
    return found


def test_no_product_specific_string_in_pipeline_code() -> None:
    pattern = re.compile("|".join(map(re.escape, _registry_names())))
    offenders = []
    for path in sorted(PIPELINE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_ids(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and pattern.search(node.value)
            ):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.value[:80]!r}")
    assert not offenders, "product-specific special case in pipeline code (R10):\n" + "\n".join(offenders)


_PRINT_ATTRIBUTION = re.compile(
    r"under a line (?:that )?attribut|print(?:s|ed)? (?:an? )?attribution|attribution line",
    re.IGNORECASE,
)


def test_no_prompt_instructs_printing_an_attribution() -> None:
    offenders = []
    for path in sorted((ROOT / "prompts").glob("*.yaml")):
        text = " ".join(path.read_text(encoding="utf-8").split())
        for match in _PRINT_ATTRIBUTION.finditer(text):
            window = text[max(0, match.start() - 80) : match.end() + 80].lower()
            if "never" in window or "no attribution" in window or "prints no" in window:
                continue
            offenders.append(f"{path.name}: ...{text[max(0, match.start() - 60):match.end() + 60]}...")
    assert not offenders, "a prompt tells the model to print an attribution (R9):\n" + "\n".join(offenders)


def test_the_renderer_attribution_path_prints_nothing() -> None:
    from repo_presenter.readme.composition.placement import ATTRIBUTION_LINE, with_attribution

    shown = with_attribution(["maintainer text", "more"], [True, True])
    assert shown == ["maintainer text", "more"]
    assert not any(ATTRIBUTION_LINE in text for text in shown)
