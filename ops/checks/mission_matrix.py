"""Validate project/mission_matrix.yaml: schema, no overclaiming, evidence paths exist.
Exit 0 when valid. Prints a one-line tally. Never decides completeness for a row; only refuses
rows whose claimed status the recorded states cannot support."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "P1", "P2", "P3", "P4", "P5", "M1"]
STATES = {"NONE", "PARTIAL", "YES", "NO_EXTERNAL_EFFECT_ATTEMPTED"}
FIELDS = ["id", "title", "status", "implementation", "test", "real_execution",
          "independent_verification", "evidence", "gaps", "next_action", "external_effect_prohibited"]


def check(path: Path = ROOT / "project" / "mission_matrix.yaml") -> list[str]:
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))["rows"]
    for r in rows:  # YAML 1.1 reads a bare YES as True
        for f in ("implementation", "test", "real_execution", "independent_verification"):
            if r.get(f) is True:
                r[f] = "YES"
    errors: list[str] = []
    ids = [r.get("id") for r in rows]
    for need in REQUIRED:
        if need not in ids:
            errors.append(f"missing requirement {need}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids")
    for r in rows:
        for f in FIELDS:
            if f not in r:
                errors.append(f"{r.get('id')}: missing field {f}")
        for f in ("implementation", "test", "real_execution", "independent_verification"):
            if r.get(f) not in STATES:
                errors.append(f"{r['id']}: bad {f} {r.get(f)!r}")
        for e in r.get("evidence") or []:
            if not (ROOT / e).exists():
                errors.append(f"{r['id']}: evidence path missing: {e}")
        if not r.get("evidence"):
            errors.append(f"{r['id']}: no evidence")
        if r.get("status") == "COMPLETE" and not all(
            r.get(f) == "YES" for f in ("implementation", "test", "real_execution", "independent_verification")
        ):
            errors.append(f"{r['id']}: COMPLETE without all four states YES")
        if r.get("status") == "COMPLETE" and r.get("gaps"):
            errors.append(f"{r['id']}: COMPLETE with remaining gaps")
    return errors


if __name__ == "__main__":
    errs = check()
    for e in errs:
        print("FAIL:", e)
    if not errs:
        rows = yaml.safe_load((ROOT / "project" / "mission_matrix.yaml").read_text())["rows"]
        from collections import Counter
        print("mission_matrix OK:", dict(Counter(r["status"] for r in rows)))
    sys.exit(1 if errs else 0)
