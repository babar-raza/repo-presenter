"""The engine end to end on synthetic facts: confined, deterministic, idempotent, model-free.

Adapted from the old repository's ``tests/components/readme_correction/test_engine.py``. Two
differences from the old file, both because this pass ports a smaller detector roster (see
``migration/reuse-manifest.yaml``'s readme_correction/ entry for what is deferred and why):

* ``test_every_registered_detector_is_loaded_by_name`` lists the 8 detectors this repository has
  (6 ported + 2 new), not the old repo's 21 -- ``sections``/``additions``/``stale``/``diagram``
  are not pulled into this package, so ``load_detectors`` never finds them to import.
* the end-to-end fixture only exercises detectors that exist here (``broken_link``,
  ``second_h1``, ``enterprise_edition_naming``) instead of the old file's full roster
  (``claim_*``, ``add_install_forms``, ``missing_sections``, ...).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors import load_detectors
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.model import Context

NL = chr(10)

README = """# Product

The maintainers wrote this opening and every sentence below it.

## Key Capabilities

- Reads files; see [the notes](upstream-issues.md).

# Scope and Limitations

The API matches the commercial [Aspose.Widgets for Java](https://products.aspose.com/widgets/java/).
Do not touch this unrelated sentence, version 26.5.0 of the spec, or this link [x](LICENSE).
"""
TREE = (
    "README.md",
    "LICENSE",
    "docs/upstream-issues.md",
)


def build(make_context: Any, make_facts: Any, make_fact: Any) -> Context:
    broken = make_fact(
        "link_target:001",
        "upstream-issues.md",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "line 7; relative; text 'the notes'"),
            ("README.md", "MISSING: tree does not contain upstream-issues.md"),
        ),
    )
    enterprise = make_fact(
        "link_target:product.enterprise",
        "https://products.aspose.com/widgets/java/",
        evidence=(("https://products.aspose.com/widgets/", "enterprise target"),),
    )
    return make_context(README, make_facts(broken, enterprise), tree=TREE)


def test_every_registered_detector_is_loaded_by_name() -> None:
    assert sorted(load_detectors()) == [
        "broken_link",
        "enterprise_edition_naming",
        "failing_example",
        "format_overclaim",
        "report_gaps",
        "second_h1",
        "stray_fence",
        "unclosed_details",
    ]


def test_each_ported_kind_of_correction_is_made_and_nothing_else_changes(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = build(make_context, make_facts, make_fact)
    result = correct(ctx)
    kinds = sorted((e.kind, e.detector) for e in result.edits)
    assert kinds == [
        ("BROKEN_LINK", "broken_link"),
        ("FALSE_CLAIM_FIX", "enterprise_edition_naming"),
        ("STRUCTURE_FIX", "second_h1"),
    ]
    for old, new in (
        ("(upstream-issues.md)", "(docs/upstream-issues.md)"),
        ("# Scope and Limitations", "## Scope and Limitations"),
        (
            "the commercial [Aspose.Widgets for Java](https://products.aspose.com/widgets/java/)",
            "[Aspose.Widgets for Java — Enterprise Edition]"
            "(https://products.aspose.com/widgets/java/)",
        ),
    ):
        assert old in README and new in result.corrected
    # The unrelated maintainer sentence and the working link stay as written.
    for kept in (
        "Do not touch this unrelated sentence, version 26.5.0 of the spec, or this link "
        "[x](LICENSE).",
        "The maintainers wrote this opening and every sentence below it.",
    ):
        assert kept in result.corrected


def test_a_second_run_is_byte_identical_and_a_run_on_the_output_finds_nothing(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = build(make_context, make_facts, make_fact)
    result = correct(ctx)
    assert is_stable(ctx, result) == (True, True)
    again = correct(Context(ctx.entry, ctx.facts, result.corrected, ctx.tree_paths))
    assert again.edits == [] and again.corrected == result.corrected


def test_a_conformant_readme_yields_no_edit_and_no_diff(make_context: Any) -> None:
    clean = "# P\n\n## Installation\n\ntext\n\n## License\n\nMIT License.\n"
    result = correct(make_context(clean))
    assert result.edits == [] and result.corrected == clean


def test_the_correction_path_names_no_model_client_and_opens_no_network_import() -> None:
    """Zero provider calls by construction: no module under this package names a model client or
    gateway library, the same invariant the old repo's own test proved for its (larger) package."""
    import ast
    from pathlib import Path

    import repo_presenter.readme.correction as package

    banned = ("openai", "anthropic", "httpx", "requests", "repo_presenter.core.llm")
    for path in Path(package.__file__).parent.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not [n for n in names if n.startswith(banned)], (path.name, names)
