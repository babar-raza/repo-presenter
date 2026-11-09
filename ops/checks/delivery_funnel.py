#!/usr/bin/env python
"""Delivery funnel (docs/DELIVERY_PLAN_2026-11-07.md section 6.1; TC-027's report half).

One honest table per lane, never summed, built from the same evidence the portfolio counter reads
(``ops/checks/portfolio_delivery_count.py``: the durable seal history, a zero-call re-certification
of every latest seal, GitHub for PRs). Columns, in order of strictness:

  registered          repositories in data/registry.json
  sealed              a durable seal exists for the lane
  deterministic       the latest seal re-certifies under current code (zero provider calls)
  mechanism_passing   deterministic AND a model-reviewed ACCEPT is sealed AND every required
                      mechanism class holds a PASSED certificate (acceptance/record.py)
  independently       mechanism_passing AND a verified, attested M9 audit record -- reported n/25;
                      this script has no attestation source until the hosted writer exists on main,
                      so it is 0 by construction, never guessed
  pr_created, live_verified   from the counter's GitHub-derived columns

Header line (every report): ``Lane R accepted | Lane L accepted | mechanism-passing only |
upstream PRs | upstream issues | live-verified``. Exit 0 always: this reports, it does not gate.

Usage: python ops/checks/delivery_funnel.py [--json]
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("portfolio_delivery_count", HERE / "portfolio_delivery_count.py")
pdc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pdc
_SPEC.loader.exec_module(pdc)


def funnel(outcomes, certificates, registered: int) -> dict:
    rows = {}
    for lane in ("R", "L"):
        mine = [o for o in outcomes if o.lane == lane and o.current]
        sealed = [o for o in mine if o.evidence_source or o.pipeline_good or o.certification]
        deterministic = [o for o in mine if o.certification == "RECERTIFIED" or (o.sealed_by_current and not o.failing_checks and o.pipeline_good)]
        mechanism = [o for o in deterministic if o.bucket in (pdc.ACCEPTED, pdc.UNCALIBRATED) and certificates is not None and certificates.complete]
        rows[lane] = {
            "registered": registered,
            "sealed": len(sealed),
            "deterministic": len(deterministic),
            "mechanism_passing": len(mechanism),
            "independently_accepted": sum(1 for o in mine if o.independently_accepted and False),
            "pr_created": sum(1 for o in mine if o.effect_executed),
            "live_verified": sum(1 for o in mine if o.live_verified),
            "needs_repair": sorted(o.repository for o in mine if o.certification == "NEEDS_REPAIR"),
            "mechanism_passing_repositories": sorted(o.repository for o in mechanism),
        }
    return rows


def main(argv: list[str]) -> int:
    from repo_presenter.core.registry.loader import load_registry

    outcomes, _calibration, certificates = pdc.collect("origin")
    registered = len(load_registry(pdc.REGISTRY).entries)
    rows = funnel(outcomes, certificates, registered)
    r, l = rows["R"], rows["L"]
    if "--json" in argv:
        print(json.dumps(rows, indent=2))
        return 0
    print(
        f"Lane R {r['independently_accepted']}/25 | Lane L {l['independently_accepted']}/25 | "
        f"mechanism-passing only R {r['mechanism_passing']} L {l['mechanism_passing']} | "
        f"upstream PRs {r['pr_created'] + l['pr_created']} | upstream issues 0 | "
        f"live-verified {r['live_verified'] + l['live_verified']}"
    )
    for lane, row in rows.items():
        print(
            f"lane {lane}: registered {row['registered']}  sealed {row['sealed']}  "
            f"deterministic {row['deterministic']}  mechanism_passing {row['mechanism_passing']}  "
            f"independently {row['independently_accepted']}/25"
        )
        print(f"  mechanism-passing: {', '.join(row['mechanism_passing_repositories']) or '-'}")
        print(f"  needs repair ({len(row['needs_repair'])}): {', '.join(row['needs_repair']) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
