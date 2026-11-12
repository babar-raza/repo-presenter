"""TC-016, second task: cross-ecosystem confirmation that each of the seven README example
verifiers already routes its own most relevant false-positive category -- a fragment run
without the surrounding context a different, uninherited section of the README established, a
substituted test input, a missing optional helper, or an ambiguous/unresolved import -- away
from ``FAILED``, while a genuine defect still reaches it. This card found (by reading each
module and proving it with a test here, not by assuming) that all seven already do this
correctly; nothing below changes production behaviour -- only ``readme/evidence/facts/examples.py``'s
``TIMED_OUT`` mapping (fixed and tested in ``tests/readme/evidence/facts/test_examples.py``)
was a genuine defect. Each test also carries a negative control: the same helper must still
recognise an unrelated, genuine defect as one, so the fix (where there was one) or the existing
behaviour (where there wasn't) never widens what counts as fine.
"""

from __future__ import annotations

from repo_presenter.core.examples import FixtureBinding
from repo_presenter.extractors.platforms import (
    cpp_examples,
    go_examples,
    java_examples,
    net_examples,
    python_examples,
    rust_examples,
    typescript_examples,
)

# --------------------------------------------------------------------------------------------
# C++: a fence opening on a name an earlier, uninherited README section established (fragment).
# --------------------------------------------------------------------------------------------


def test_cpp_a_fragments_unbound_identifier_is_not_a_falsehood() -> None:
    fragment = ["example_004.cpp:2:5: error: 'workbook' was not declared in this scope"]
    assert cpp_examples.unbound_identifiers(fragment) == ["workbook"]


def test_cpp_a_genuine_type_mismatch_is_still_a_defect() -> None:
    real_defect = [
        "example_002.cpp:10:48: error: no match for 'operator[]' (operand types are "
        "'Aspose::Cells_FOSS::WorksheetCollection' and 'const char [9]')"
    ]
    assert cpp_examples.unbound_identifiers(real_defect) == []


# --------------------------------------------------------------------------------------------
# .NET: the same fragment class (CS0103 on an undeclared local), never a renamed/removed API.
# --------------------------------------------------------------------------------------------


def test_net_an_undeclared_local_is_a_fragment_not_a_contradiction() -> None:
    diagnostics = "Program.cs(1,9): error CS0103: The name 'bytes' does not exist in the current context"
    outcome, detail = net_examples.classify_build_failure(diagnostics, "var n = bytes;")
    assert outcome == "NOT_VERIFIED"
    assert "fragment" in detail


def test_net_a_removed_api_qualifier_is_still_a_contradiction() -> None:
    diagnostics = (
        "Program.cs(1,1): error CS0103: The name 'RemovedStatic' does not exist in the "
        "current context"
    )
    outcome, _detail = net_examples.classify_build_failure(diagnostics, "RemovedStatic.Foo();")
    assert outcome == "FAILED"


# --------------------------------------------------------------------------------------------
# Java: `cannot find symbol` naming a variable (fragment) vs. naming a type/method (defect).
# --------------------------------------------------------------------------------------------


def test_java_a_cannot_find_symbol_variable_is_a_fragment() -> None:
    output = (
        "Example.java:4: error: cannot find symbol\n"
        '        workbook.save("out.xlsx");\n'
        "        ^\n"
        "  symbol:   variable workbook\n"
        "  location: class Example\n"
    )
    assert java_examples.unbound_variables(output) == ["workbook"]


def test_java_a_cannot_find_symbol_type_is_still_a_defect() -> None:
    output = (
        "Example.java:4: error: cannot find symbol\n"
        "        Missing value = new Missing();\n"
        "        ^\n"
        "  symbol:   class Missing\n"
        "  location: class Example\n"
    )
    assert java_examples.unbound_variables(output) == []


# --------------------------------------------------------------------------------------------
# Go: a single unresolved qualifier is read as the product's own import (completable); two or
# more unresolved qualifiers leave the wrapper genuinely incomplete rather than condemned.
# --------------------------------------------------------------------------------------------


def test_go_two_unresolved_qualifiers_are_an_incomplete_wrapper_not_a_falsehood() -> None:
    diagnostics = "./main.go:3:2: undefined: aliasedrand\n./main.go:4:2: undefined: ecdsa\n"
    code = "aliasedrand.Reader()\necdsa.GenerateKey()\n"
    imports, unknown = go_examples.resolve_imports(diagnostics, "example.com/widget", code)
    assert unknown == ["aliasedrand", "ecdsa"]
    assert imports == []


def test_go_one_unresolved_name_resolves_to_the_products_own_import() -> None:
    diagnostics = "./main.go:3:2: undefined: fmt\n./main.go:5:2: undefined: widget\n"
    code = "fmt.Println()\nwidget.New()\n"
    imports, unknown = go_examples.resolve_imports(diagnostics, "example.com/widget", code)
    assert unknown == []
    assert any("example.com/widget" in line for line in imports)


# --------------------------------------------------------------------------------------------
# Rust: `cannot find value` (E0425) alone is a fragment; any other error code is a real defect.
# --------------------------------------------------------------------------------------------


def test_rust_a_cannot_find_value_is_a_fragment() -> None:
    diagnostics = "error[E0425]: cannot find value `workbook` in this scope\n"
    assert rust_examples.unbound_values(diagnostics) == ["workbook"]


def test_rust_a_missing_type_is_still_a_defect() -> None:
    diagnostics = "error[E0412]: cannot find type `Missing` in this scope\n"
    assert rust_examples.unbound_values(diagnostics) == []


# --------------------------------------------------------------------------------------------
# TypeScript: TS2304 on a bare lower-case local is a fragment; the same code on a capitalised
# name (a type/class) may be a missing export, so it stays a contradiction.
# --------------------------------------------------------------------------------------------


def test_typescript_an_undeclared_lowercase_local_is_a_fragment() -> None:
    diagnostic = "example_001.ts(3,1): error TS2304: Cannot find name 'workbook'."
    outcome, detail = typescript_examples.own_diagnostics_outcome([diagnostic])
    assert outcome == "NOT_VERIFIED"
    assert "fragment" in detail


def test_typescript_an_undeclared_capitalised_name_is_still_a_defect() -> None:
    diagnostic = "example_001.ts(3,1): error TS2304: Cannot find name 'Workbook'."
    outcome, _detail = typescript_examples.own_diagnostics_outcome([diagnostic])
    assert outcome == "FAILED"


# --------------------------------------------------------------------------------------------
# Python: two categories apply -- a substituted fixture input proves nothing about the example,
# and a missing module a declared optional extra would resolve is an environment gap, not a
# contradiction. Both are exercised through the real production helpers, not reimplemented here.
# --------------------------------------------------------------------------------------------


def test_python_a_failure_on_a_substituted_input_is_inconclusive() -> None:
    substituted = FixtureBinding(literal="template.pdf", source_path="tests/other.pdf")
    outcome, detail = python_examples._substitute_inconclusive(
        "FAILED", "KeyError: 'Field1'", [substituted]
    )
    assert outcome == "NEEDS_INPUT"
    assert "substitute input" in detail


def test_python_a_code_intrinsic_failure_is_never_excused_by_a_substituted_input() -> None:
    substituted = FixtureBinding(literal="template.pdf", source_path="tests/other.pdf")
    outcome, detail = python_examples._substitute_inconclusive(
        "FAILED", "NameError", [substituted]
    )
    assert outcome == "FAILED"
    assert detail == "NameError"


def test_python_a_module_only_a_declared_optional_extra_provides_is_named() -> None:
    trace = (
        'Traceback (most recent call last):\n  File "example_001.py", line 1, in <module>\n'
        "    import reportlab\n"
        "ModuleNotFoundError: No module named 'reportlab'\n"
    )
    assert python_examples.missing_module_name(trace) == "reportlab"


def test_python_a_plain_value_error_names_no_module_at_all() -> None:
    assert python_examples.missing_module_name("ValueError: bad input\n") is None
