"""BL-061 (K01): a compiled .NET or Java example is also RUN, so an example whose calls exist but
throw is a contradiction, not a verified example; and BL-006: Java enum constants are read for a
sealed enum fact from its pinned declaration.

Real shapes: the 3D .NET Quick Start saves with ``FileFormat.FBX7400Binary``, which compiles and
throws ``NotImplementedException`` (``FileFormat.cs:66,83,347-350`` @52b0f00ebf28); 3D Java's
``PresetShaders`` is ``public enum PresetShaders { DEFAULT, CUSTOMIZED; }`` and ``ReferenceMode``
``{ DIRECT, INDEX_TO_DIRECT, INDEX }`` (@3d2ed6be91f5)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from repo_presenter.core.examples import ExampleCandidate
from repo_presenter.core.execution import ExecutionResult
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.extractors.platforms.java import JavaPlugin, java_enum_constants
from repo_presenter.extractors.platforms.java_examples import (
    classify_java_run,
    verify_java_examples,
)
from repo_presenter.extractors.platforms.net_examples import classify_net_run


def _result(code: int, stderr: str = "", timed_out: bool = False) -> ExecutionResult:
    return ExecutionResult(argv=("x",), return_code=code, stdout="", stderr=stderr, timed_out=timed_out)


def test_a_net_run_that_throws_is_failed_and_a_missing_input_is_not() -> None:
    thrown = _result(
        134,
        "Unhandled exception. System.NotImplementedException: FBX7400Binary is not supported\n"
        "   at Aspose.ThreeD.FileFormat.get_FBX7400Binary()",
    )
    assert classify_net_run(thrown, 60) == (
        "FAILED", "ran and threw System.NotImplementedException: FBX7400Binary is not supported"
    )
    missing = _result(134, "Unhandled exception. System.IO.FileNotFoundException: Could not find file 'input.fbx'.")
    assert classify_net_run(missing, 60)[0] == "NEEDS_INPUT"
    assert classify_net_run(_result(0), 60) == ("EXECUTED", "ran (exit 0)")
    assert classify_net_run(_result(-1, timed_out=True), 60)[0] == "TIMED_OUT"


def test_a_java_run_is_classified_the_same_way() -> None:
    thrown = _result(1, 'Exception in thread "main" java.lang.UnsupportedOperationException: not yet\n\tat x')
    assert classify_java_run(thrown, 60) == (
        "FAILED", "ran and threw java.lang.UnsupportedOperationException: not yet"
    )
    missing = _result(1, 'Exception in thread "main" java.io.FileNotFoundException: box.stl (No such file)')
    assert classify_java_run(missing, 60)[0] == "NEEDS_INPUT"


def _candidate(ordinal: int, code: str) -> ExampleCandidate:
    return ExampleCandidate(
        ordinal=ordinal, language="java", code=code, source_path="README.md",
        start_line=ordinal * 10, end_line=ordinal * 10 + 3, unit_id=f"inherited_unit:{ordinal:03d}.code_block",
    )


@pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="no JDK")
def test_a_compiled_java_example_that_throws_is_failed_and_one_that_runs_executed(tmp_path: Path) -> None:
    source = tmp_path / "product" / "src" / "main" / "java" / "com" / "acme"
    source.mkdir(parents=True)
    (source / "Scene.java").write_text(
        "package com.acme;\n"
        "public class Scene {\n"
        "    public void save(String path) { throw new UnsupportedOperationException(\"FBX\"); }\n"
        "    public int count() { return 1; }\n"
        "}\n",
        encoding="utf-8",
    )
    candidates = [
        _candidate(1, "Scene scene = new Scene();\nscene.save(\"out.fbx\");\n"),
        _candidate(2, "Scene scene = new Scene();\nSystem.out.println(scene.count());\n"),
    ]
    receipts = verify_java_examples(
        tmp_path / "product" / "src" / "main" / "java", "17", False, (), candidates, tmp_path / "work", 120.0
    )
    by = {receipt.ordinal: receipt for receipt in receipts}
    assert by[1].outcome == "FAILED" and "UnsupportedOperationException" in by[1].detail
    assert by[2].outcome == "EXECUTED" and by[2].detail.endswith("ran (exit 0)")


def test_java_enum_constants_are_read_from_the_declaration() -> None:
    assert java_enum_constants("package x;\n\npublic enum PresetShaders {\n    DEFAULT,\n    CUSTOMIZED;\n}\n", "PresetShaders") == ("DEFAULT", "CUSTOMIZED")
    assert java_enum_constants("public enum ReferenceMode {\n DIRECT,\n INDEX_TO_DIRECT,\n INDEX\n}", "ReferenceMode") == ("DIRECT", "INDEX_TO_DIRECT", "INDEX")
    assert java_enum_constants('enum A { /* c */ @Deprecated FOO(1, "a,b") { void f() {} }, BAR(2), BAZ; int v; }', "A") == ("FOO", "BAR", "BAZ")
    assert java_enum_constants("enum A { ONE TWO }", "A") == ()  # not read whole: nothing claimed


def test_a_sealed_java_enum_gains_its_values_from_the_pinned_source() -> None:
    path = "src/main/java/com/aspose/threed/PresetShaders.java"
    enum = Fact(
        "public_symbol:com.aspose.threed.presetshaders",
        "public_symbol",
        "com.aspose.threed.PresetShaders",
        (Evidence(path, "line 3; enum; public by declaration"),),
        attributes={"symbol_kind": "enum"},
    )
    document = FactsDocument("aspose-3d-foss/Aspose.3D-FOSS-for-Java", "a" * 40, (enum,))
    updated, changed = JavaPlugin().member_count_facts(
        document, {path: "public enum PresetShaders {\n    DEFAULT,\n    CUSTOMIZED;\n}\n"}
    )
    assert changed == 1
    assert updated.facts[0].attributes["enum_values"] == "DEFAULT,CUSTOMIZED"
    assert JavaPlugin().member_count_facts(updated, {path: ""})[1] == 0  # idempotent
