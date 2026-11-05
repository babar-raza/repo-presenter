#!/usr/bin/env python
"""Generate evidence/build/GATE1_QUALITY/TC-008a/call_count_proof.json from MEASURED provider
request counts, recorded at the fake provider boundary by:
  - tests/test_preflight_wiring.py        (lane L: real CLI; lane R: preflight + a STUBBED run_cascade)
  - tests/test_lane_r_real_cascade_p5.py  (lane R-real: the REAL present._cascade_and_seal / run_cascade)
Nothing here is typed by hand: the file is a function of a real pytest run. The headline numbers
use lane L and lane R-real; the stub-based R rows are kept only as a cross-check."""
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
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_preflight_wiring.py",
                            "tests/test_lane_r_real_cascade_p5.py", "-q",
                            "-p", "no:cacheprovider"], cwd=ROOT, env=env)
        if r.returncode != 0 or not log.exists():
            print("FAIL: measurement run did not pass")
            return 1
        rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    by: dict[str, dict[str, int]] = {}
    for row in rows:
        by.setdefault(row["scenario"], {})[row["lane"]] = row["requests"]
    need = ["warm_unchanged_rerun", "cold_runner", "evicted_cache", "corrupt_evidence"]
    if any(k not in by or not {"L", "R", "R-real"} <= set(by[k]) for k in need):
        print("FAIL: missing scenario measurements", by)
        return 1
    real = {k: {lane: n for lane, n in v.items() if lane in ("L", "R-real")} for k, v in by.items()}
    cold = by.get("cold_run", {}).get("R-real")
    if cold is None or cold < 1:
        print("FAIL: the real Lane R cold run made no measured request", by)
        return 1
    doc = {
        "measured_by": "scripts/p5_call_count_proof.py running tests/test_preflight_wiring.py "
                       "and tests/test_lane_r_real_cascade_p5.py",
        "per_scenario_requests_by_lane": by,
        "lane_r_real_cold_run_requests": cold,
        "warm_unchanged_rerun_calls": max(real["warm_unchanged_rerun"].values()),
        "cold_runner_calls": max(real["cold_runner"].values()),
        "evicted_cache_calls": max(real["evicted_cache"].values()),
        "corrupt_evidence_fail_closed": all(v >= 1 for v in real["corrupt_evidence"].values()),
        "caveat": "Headline numbers use lane L (real CLI) and lane R-real (real run_cascade, "
                  "nine stages + one review). Lane R rows from tests/test_preflight_wiring.py use "
                  "a stubbed run_cascade and are a cross-check only. All provider traffic is a "
                  "fake at the transport boundary; no live model was called.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
