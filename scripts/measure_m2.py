"""Supervisor-run measurement of mechanism M2 (claim proof) against a REAL, freshly cloned
upstream repository -- the first M2 measurement that is not purely synthetic.

Unlike every other ``measure_m*.py`` script in this directory, this one needs network access
(a shallow ``git clone`` of one small, real registered repository) because M2's probe-based cross
-check (TC-017a/17b) is specifically about reading a REAL on-disk source tree; there is no
meaningful zero-network way to prove it against real names. No provider/model call is made --
this is a deterministic, code-only check, just one that needs a real git clone to have something
real to check against. The repository chosen (Aspose.BarCode-FOSS-for-Python) is small and the
clone is shallow (--depth 1); it is deleted after measurement, nothing is kept in the working
tree.

Three real cases, each built from names TC-017a's own python probe (``src/repo_presenter/
acceptance/probes/python.py``) independently confirms against the real clone (not invented,
not assumed):

1. clean: an API table whose every class name is both fact-backed and probe-confirmed exported.
   Expected: no findings (false-reject side).
2. unbacked_name (D5): an API table naming a class with NO supporting fact at all -- the
   fact-only check in ``readme.validation.surface_claims._table_findings`` catches it without
   needing the probe.
3. wrong_fact_probe_catches (D5, the TC-017a/17b cross-check itself): a DELIBERATELY WRONG fact
   that claims an invented class name is real and exported (simulating a facts-extractor bug);
   only the independent probe -- reading the real clone, not the (wrong) fact -- catches it.

Usage: ``python scripts/measure_m2.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m2,
)
from repo_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repo_presenter.readme.validation.claims import _lines  # noqa: E402
from repo_presenter.readme.validation.surface_claims import surface_findings  # noqa: E402

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"
CLONE_URL = "https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python.git"


def _symbol_fact(name: str) -> Fact:
    return Fact(
        id=f"public_symbol:{name.lower()}",
        kind="public_symbol",
        value=f"aspose_barcode_foss.{name}",
        evidence=(Evidence(path="src/aspose_barcode_foss/__init__.py"),),
        attributes={"symbol_kind": "class"},
    )


def _table(*names: str) -> str:
    rows = "\n".join(f"| `{name}` | Description. |" for name in names)
    return f"## Classes\n\n| Class | Description |\n|---|---|\n{rows}\n"


def measure(clone_root: Path):
    ecosystem = Fact(
        id="identity:ecosystem", kind="identity", value="python",
        evidence=(Evidence(path="pyproject.toml"),),
    )
    real_names = ("Barcode", "BarcodeError", "Code128Options")

    # Case 1: clean -- every name fact-backed and probe-confirmed.
    clean_facts = FactsDocument(
        repository="aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python", source_revision="HEAD",
        facts=(ecosystem, *[_symbol_fact(name) for name in real_names]),
    )
    clean_findings = surface_findings(_lines(_table(*real_names)), clean_facts, probe_root=clone_root)

    # Case 2: unbacked_name -- no fact at all states the invented name.
    unbacked_facts = FactsDocument(
        repository="aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python", source_revision="HEAD",
        facts=(ecosystem, _symbol_fact("Barcode"), _symbol_fact("BarcodeError")),
    )
    unbacked_findings = surface_findings(
        _lines(_table("Barcode", "BarcodeError", "TotallyInventedClassXYZ")),
        unbacked_facts, probe_root=clone_root,
    )

    # Case 3: wrong_fact_probe_catches -- a WRONG fact claims the invented name is real; only the
    # probe (reading the real clone) catches it.
    wrong_facts = FactsDocument(
        repository="aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python", source_revision="HEAD",
        facts=(
            ecosystem, _symbol_fact("Barcode"), _symbol_fact("BarcodeError"),
            _symbol_fact("TotallyInventedClassXYZ"),
        ),
    )
    wrong_findings = surface_findings(
        _lines(_table("Barcode", "BarcodeError", "TotallyInventedClassXYZ")),
        wrong_facts, probe_root=clone_root,
    )

    cases = [
        CaseVerdict("clean", "D5", expected=False, flagged=bool(clean_findings)),
        CaseVerdict("unbacked_name", "D5", expected=True, flagged=bool(unbacked_findings)),
        CaseVerdict(
            "wrong_fact_probe_catches", "D5", expected=True, flagged=bool(wrong_findings)
        ),
    ]
    return score_m2(cases), len(cases)


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
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M2"]
    certificates.append(
        {
            "mechanism_class": "M2",
            "status": result.status,
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": f"real shallow clone of {CLONE_URL} (deleted after measurement); "
                      "real TC-017a python probe against it; hand-built facts, small n=3 "
                      "-- a first real-source proof, not yet a full-recall measurement",
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="m2-measure-"))
    clone_root = tmp / "clone"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", CLONE_URL, str(clone_root)],
            check=True, timeout=120,
        )
        result, n_cases = measure(clone_root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_cases} cases against a real clone, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
