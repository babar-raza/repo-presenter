#!/usr/bin/env python
"""Generate evidence/build/GATE1_QUALITY/TC-008a/call_count_proof.json from MEASURED provider
request counts (tests/test_preflight_wiring.py records them at the fake provider boundary).
Nothing here is typed by hand: the file is a function of a real pytest run.
Lane R's pipeline body is a stub (see that test module's docstring); only the preflight
decision and the request boundary are real for Lane R."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/build/GATE1_QUALITY/TC-008a/call_count_proof.json"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "counts.jsonl"
        env = {**os.environ, "P5_PROOF_OUT": str(log)}
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_preflight_wiring.py", "-q",
                            "-p", "no:cacheprovider"], cwd=ROOT, env=env)
        if r.returncode != 0 or not log.exists():
            print("FAIL: measurement run did not pass")
            return 1
        rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    by: dict[str, dict[str, int]] = {}
    for row in rows:
        by.setdefault(row["scenario"], {})[row["lane"]] = row["requests"]
    need = ["warm_unchanged_rerun", "cold_runner", "evicted_cache", "corrupt_evidence"]
    if any(k not in by or set(by[k]) != {"L", "R"} for k in need):
        print("FAIL: missing scenario measurements", by)
        return 1
    doc = {
        "measured_by": "scripts/p5_call_count_proof.py running tests/test_preflight_wiring.py",
        "per_scenario_requests_by_lane": by,
        "warm_unchanged_rerun_calls": max(by["warm_unchanged_rerun"].values()),
        "cold_runner_calls": max(by["cold_runner"].values()),
        "evicted_cache_calls": max(by["evicted_cache"].values()),
        "corrupt_evidence_fail_closed": all(v >= 1 for v in by["corrupt_evidence"].values()),
        "caveat": "Lane R run_cascade body is stubbed to one request; Lane L is the real CLI path.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
