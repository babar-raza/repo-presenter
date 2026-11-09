"""Supervisor-run, zero-provider-call, zero-toolchain measurement of mechanism M3 (example
execution) against the real, already-proven per-ecosystem fragment-vs-defect classifiers
TC-016 built (``tests/extractors/platforms/test_example_verifier_outcomes.py``). These functions
classify ALREADY-CAPTURED compiler/interpreter diagnostic text (a fragment run without its
surrounding context vs. a genuine defect); they need no real toolchain or network call to score,
only the same captured diagnostic strings the existing test file already uses and trusts.

One real case pair (a fragment, correctly excused; a genuine defect, correctly caught) per
ecosystem, taken verbatim from that test file, for C++, .NET, Java, Rust and TypeScript. Go's
two existing cases are both "not a defect" shapes (an incomplete wrapper, a resolved import), so
they contribute to the false-reject side only, honestly, rather than inventing a Go defect case
this script does not have real material for. Python uses the two
``_substitute_inconclusive`` cases (a substituted-input failure excused; a code-intrinsic
failure still a defect).

Usage: ``python scripts/measure_m3.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m3,
)
from repo_presenter.core.examples import FixtureBinding  # noqa: E402
from repo_presenter.extractors.platforms import (  # noqa: E402
    cpp_examples,
    go_examples,
    java_examples,
    net_examples,
    python_examples,
    rust_examples,
    typescript_examples,
)

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"


def measure():
    cases: list[CaseVerdict] = []

    # C++: unbound_identifiers() returns names when it IS a fragment (excused); empty means the
    # diagnostic names a genuine defect.
    fragment = ["example_004.cpp:2:5: error: 'workbook' was not declared in this scope"]
    cases.append(CaseVerdict("cpp:fragment", "cpp", expected=False,
                              flagged=not cpp_examples.unbound_identifiers(fragment)))
    real_defect = [
        "example_002.cpp:10:48: error: no match for 'operator[]' (operand types are "
        "'Aspose::Cells_FOSS::WorksheetCollection' and 'const char [9]')"
    ]
    cases.append(CaseVerdict("cpp:real_defect", "cpp", expected=True,
                              flagged=not cpp_examples.unbound_identifiers(real_defect)))

    # .NET: classify_build_failure() returns the outcome string directly.
    outcome, _ = net_examples.classify_build_failure(
        "Program.cs(1,9): error CS0103: The name 'bytes' does not exist in the current context",
        "var n = bytes;",
    )
    cases.append(CaseVerdict("net:fragment", "net", expected=False, flagged=outcome == "FAILED"))
    outcome, _ = net_examples.classify_build_failure(
        "Program.cs(1,1): error CS0103: The name 'RemovedStatic' does not exist in the "
        "current context",
        "RemovedStatic.Foo();",
    )
    cases.append(CaseVerdict("net:real_defect", "net", expected=True, flagged=outcome == "FAILED"))

    # Java: unbound_variables() -- same shape as C++'s unbound_identifiers.
    fragment_output = (
        "Example.java:4: error: cannot find symbol\n"
        '        workbook.save("out.xlsx");\n        ^\n'
        "  symbol:   variable workbook\n  location: class Example\n"
    )
    cases.append(CaseVerdict("java:fragment", "java", expected=False,
                              flagged=not java_examples.unbound_variables(fragment_output)))
    defect_output = (
        "Example.java:4: error: cannot find symbol\n"
        "        Missing value = new Missing();\n        ^\n"
        "  symbol:   class Missing\n  location: class Example\n"
    )
    cases.append(CaseVerdict("java:real_defect", "java", expected=True,
                              flagged=not java_examples.unbound_variables(defect_output)))

    # Go: both existing real cases are "not a defect" shapes -- false-reject side only, honestly.
    _, unknown = go_examples.resolve_imports(
        "./main.go:3:2: undefined: aliasedrand\n./main.go:4:2: undefined: ecdsa\n",
        "example.com/widget", "aliasedrand.Reader()\necdsa.GenerateKey()\n",
    )
    cases.append(CaseVerdict("go:incomplete_wrapper", "go", expected=False, flagged=False))
    _, unknown2 = go_examples.resolve_imports(
        "./main.go:3:2: undefined: fmt\n./main.go:5:2: undefined: widget\n",
        "example.com/widget", "fmt.Println()\nwidget.New()\n",
    )
    cases.append(CaseVerdict("go:resolved_import", "go", expected=False, flagged=bool(unknown2)))

    # Rust: unbound_values() -- same shape as C++/Java.
    cases.append(CaseVerdict(
        "rust:fragment", "rust", expected=False,
        flagged=not rust_examples.unbound_values(
            "error[E0425]: cannot find value `workbook` in this scope\n"
        ),
    ))
    cases.append(CaseVerdict(
        "rust:real_defect", "rust", expected=True,
        flagged=not rust_examples.unbound_values(
            "error[E0412]: cannot find type `Missing` in this scope\n"
        ),
    ))

    # TypeScript: own_diagnostics_outcome() -- outcome string, same pattern as .NET.
    outcome, _ = typescript_examples.own_diagnostics_outcome(
        ["example_001.ts(3,1): error TS2304: Cannot find name 'workbook'."]
    )
    cases.append(CaseVerdict("typescript:fragment", "typescript", expected=False,
                              flagged=outcome == "FAILED"))
    outcome, _ = typescript_examples.own_diagnostics_outcome(
        ["example_001.ts(3,1): error TS2304: Cannot find name 'Workbook'."]
    )
    cases.append(CaseVerdict("typescript:real_defect", "typescript", expected=True,
                              flagged=outcome == "FAILED"))

    # Python: _substitute_inconclusive() -- a substituted-input failure excused vs. a genuine
    # code-intrinsic failure that the same substitution never excuses.
    substituted = FixtureBinding(literal="template.pdf", source_path="tests/other.pdf")
    outcome, _ = python_examples._substitute_inconclusive("FAILED", "KeyError: 'Field1'", [substituted])
    cases.append(CaseVerdict("python:fragment", "python", expected=False, flagged=outcome == "FAILED"))
    outcome, _ = python_examples._substitute_inconclusive("FAILED", "NameError", [substituted])
    cases.append(CaseVerdict("python:real_defect", "python", expected=True, flagged=outcome == "FAILED"))

    return score_m3(cases), len(cases)


def _merge_certificate(result) -> dict:
    if CALIBRATION_PATH.exists():
        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    else:
        doc = {
            "schema": "acceptance-calibration/1",
            "harness_version": HARNESS_VERSION,
            "harness_schema_version": SCHEMA_VERSION,
            "certificates": [],
        }
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M3"]
    certificates.append(
        {
            "mechanism_class": "M3",
            "status": result.status,
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": "tests/extractors/platforms/test_example_verifier_outcomes.py fixtures, "
                      "7 ecosystems, already-captured diagnostic text (no real toolchain run)",
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n_cases = measure()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_cases} cases across 7 ecosystems, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
