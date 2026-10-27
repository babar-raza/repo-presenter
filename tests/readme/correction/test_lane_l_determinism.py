"""Lane L is deterministic, so its zero-drift rerun must hold across machines
(plans/PLAN_lane_l_hosted.md L4): no newline translation, no path, no clock in any artifact.

The checks are structural where a behavioural test could pass on one platform only: a
``write_text`` without ``newline=`` writes CRLF on Windows and LF on Linux, so the same cascade
would seal different bytes on each (the Lane R bug fixed in hosted run 8). Every Lane L module
writes bytes, or text with its newline pinned.
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path

import pytest

import repo_presenter
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.report import canonical_json, corrections_document
from tests.readme.correction.conftest import base_facts, context
from tests.readme.correction.test_lane_l_report import TREE, broken_link

SRC = Path(repo_presenter.__file__).parent
LANE_L_MODULES = (
    "lane_l_run.py",
    "readme/correction/report.py",
    "lane_l_review.py",
)


@pytest.mark.parametrize("module", LANE_L_MODULES)
def test_no_lane_l_module_writes_text_with_the_platform_newline(module: str) -> None:
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"write_text", "open"}
    ]
    unpinned = [
        node.lineno
        for node in writes
        if not any(keyword.arg == "newline" for keyword in node.keywords)
    ]
    assert unpinned == [], (
        f"{module}: text written without newline= at lines {unpinned}"
    )


def test_the_lane_l_stage_writes_every_artifact_as_bytes() -> None:
    source = (SRC / "lane_l_run.py").read_text(encoding="utf-8")
    for artifact in (
        "CORRECTED_README_FILENAME",
        "ORIGINAL_README_FILENAME",
        "PATCH_FILENAME",
        "CORRECTIONS_FILENAME",
        "HOLDOUTS_FILENAME",
    ):
        assert f"(out_dir / {artifact}).write_bytes(" in source, artifact


CRLF_README = (
    "# Product\r\n\r\nThe maintainers wrote this.\r\n\r\n## Documentation\r\n\r\n"
    "See [the notes](upstream-issues.md) for details.\r\n"
)


def test_a_crlf_readme_keeps_its_line_endings_outside_and_inside_the_edit() -> None:
    """A README checked out with CRLF (or committed with it) is edited in place: the corrected
    bytes are the original bytes with the one fragment replaced, every line ending untouched."""
    ctx = context(
        CRLF_README, base_facts(broken_link()), tree=TREE
    )  # the link is on line 7
    result = correct(ctx)
    assert [edit.kind for edit in result.edits] == ["BROKEN_LINK"]
    expected = CRLF_README.replace("(upstream-issues.md)", "(docs/upstream-issues.md)")
    assert result.corrected.encode("utf-8") == expected.encode("utf-8")
    assert result.corrected.count("\r\n") == CRLF_README.count("\r\n")
    assert result.corrected.count("\n") == result.corrected.count(
        "\r\n"
    )  # no bare LF appeared


def test_the_correction_and_its_report_do_not_depend_on_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.readme.correction.test_lane_l_report import README

    def report_bytes() -> tuple[bytes, bytes]:
        ctx = context(README, base_facts(broken_link()), tree=TREE)
        result = correct(ctx)
        deterministic, idempotent = is_stable(ctx, result)
        document = corrections_document(
            ctx,
            result,
            original_sha256=hashlib.sha256(README.encode()).hexdigest(),
            corrected_sha256=hashlib.sha256(result.corrected.encode()).hexdigest(),
            deterministic=deterministic,
            idempotent=idempotent,
        )
        return result.corrected.encode("utf-8"), canonical_json(document)

    here = report_bytes()
    elsewhere = tmp_path / "a" / "deeper" / "directory"
    elsewhere.mkdir(parents=True)
    monkeypatch.chdir(elsewhere)
    assert report_bytes() == here
    assert os.getcwd() == str(elsewhere.resolve()) or os.getcwd() == str(elsewhere)
