"""Measure Lane R against the 2026-11-13 audit baseline (BL-085), reproducibly and with zero provider calls.

The baseline (``baseline.json`` beside this file) is the frozen record of the owner-requested audit of every
Lane R failure to 2026-11-14T00:00Z (``docs/investigations/2026-11-13-lane-r-not-progressing.md``). It is never
edited by hand: ``--write-baseline`` regenerates it from the frozen inputs in this directory and refuses to
overwrite a different existing file unless ``--force`` is given.

Measure a later state with the same classifier (``classify.py``) and compare:

    # 1. download the present job logs of the hosted runs to measure (one <run id>.log per run)
    gh run view <id> -R babar-raza/repo-presenter --log --job <present job id> > LOGDIR/<id>.log
    # 2. extract their Lane R lines, and re-judge every latest Lane R seal under current code
    python docs/investigations/2026-11-13-lane-r-not-progressing/extract_hosted.py LOGDIR > NEW/hosted_lane_r.jsonl
    PYTHONPATH=src python -m repo_presenter.recertify --all --json --remote origin > NEW/recertify_all.json
    # 3. compare with the baseline
    python docs/investigations/2026-11-13-lane-r-not-progressing/measure.py \
        --hosted NEW/hosted_lane_r.jsonl --recertify NEW/recertify_all.json

The comparison prints, per measure, baseline -> now: certified Lane R cells, cells attempted, findings per class,
classes gone and classes new, and repair success. A class's name is the audit's own vocabulary, so a fix is visible
as its class shrinking or disappearing, and a regression as a new class.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import classify  # noqa: E402  (the audit's own classifier; same vocabulary as the baseline)

BASELINE = HERE / "baseline.json"


def _lane_r(recertify: list[dict]) -> list[dict]:
    return [row for row in recertify if row.get("lane") == "R"]


def summarise(hosted_path: Path, recertify_path: Path) -> dict:
    recertify = json.loads(recertify_path.read_text(encoding="utf-8"))
    lane_r = _lane_r(recertify) if recertify and "lane" in recertify[0] else recertify
    filtered = recertify_path.with_suffix(".lane_r.tmp.json")
    filtered.write_text(json.dumps(lane_r), encoding="utf-8")
    try:
        hosted = classify.hosted_rows(hosted_path)
        recert = classify.recert_rows(filtered)
    finally:
        filtered.unlink(missing_ok=True)
    runs = [json.loads(line) for line in hosted_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sealed = [row for row in lane_r if row.get("outcome") == "RECERTIFIED"]
    findings = collections.Counter(row["class"] for row in hosted)
    seal_findings = collections.Counter(row["class"] for row in recert)
    cells = collections.defaultdict(set)
    for row in hosted:
        cells[row["class"]].add(row["repository"])
    repairs = collections.Counter()
    for run in runs:
        for line in run.get("repair", []):
            repairs["repaired" if line.startswith("repair repaired") else "not_repaired"] += 1
    return {
        "lane_r_certified_cells": sorted(row["repository"] for row in sealed),
        "lane_r_sealed_cells": len(lane_r),
        "lane_r_needs_repair_cells": sum(row.get("outcome") == "NEEDS_REPAIR" for row in lane_r),
        "hosted_lane_r_runs": len(runs),
        "hosted_cells_attempted": sorted({run["repository"] for run in runs if run.get("repository")}),
        "hosted_findings_by_class": dict(findings.most_common()),
        "hosted_cells_by_class": {k: len(v) for k, v in sorted(cells.items())},
        "seal_findings_by_class": dict(seal_findings.most_common()),
        "repair_attempts": dict(repairs),
    }


def compare(base: dict, now: dict) -> list[str]:
    out = [
        f"Lane R certified cells: {len(base['lane_r_certified_cells'])} -> {len(now['lane_r_certified_cells'])}"
        f"  (now: {', '.join(c.split('/')[-1] for c in now['lane_r_certified_cells']) or '-'})",
        f"Lane R sealed cells needing repair: {base['lane_r_needs_repair_cells']} -> {now['lane_r_needs_repair_cells']}",
        f"Hosted Lane R runs measured: {base['hosted_lane_r_runs']} -> {now['hosted_lane_r_runs']};"
        f" cells attempted {len(base['hosted_cells_attempted'])} -> {len(now['hosted_cells_attempted'])}",
    ]
    rb, rn = base["repair_attempts"], now["repair_attempts"]
    out.append(f"Repair: repaired {rb.get('repaired', 0)}/{sum(rb.values())} -> {rn.get('repaired', 0)}/{sum(rn.values())}")
    b, n = base["hosted_findings_by_class"], now["hosted_findings_by_class"]
    out.append("Hosted findings by class (baseline -> now):")
    for name in sorted(set(b) | set(n), key=lambda k: -(b.get(k, 0) + n.get(k, 0))):
        mark = " NEW" if name not in b else (" GONE" if name not in n else "")
        out.append(f"  {name:38} {b.get(name, 0):>4} -> {n.get(name, 0):<4}{mark}")
    bs, ns = base["seal_findings_by_class"], now["seal_findings_by_class"]
    out.append("Findings on latest Lane R seals by class (baseline -> now):")
    for name in sorted(set(bs) | set(ns), key=lambda k: -(bs.get(k, 0) + ns.get(k, 0))):
        mark = " NEW" if name not in bs else (" GONE" if name not in ns else "")
        out.append(f"  {name:38} {bs.get(name, 0):>4} -> {ns.get(name, 0):<4}{mark}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hosted", type=Path, default=HERE / "hosted_lane_r.jsonl")
    parser.add_argument("--recertify", type=Path, default=HERE / "recertify_lane_r.json")
    parser.add_argument("--write-baseline", action="store_true", help="regenerate baseline.json from the frozen inputs")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    now = summarise(args.hosted, args.recertify)
    if args.write_baseline:
        text = json.dumps({"as_of": "2026-11-14T00:00Z", "source": "BL-085 audit", **now}, indent=1, sort_keys=True) + "\n"
        if BASELINE.exists() and BASELINE.read_text(encoding="utf-8") != text and not args.force:
            print("refusing to overwrite a different baseline.json (it is the frozen record); pass --force", file=sys.stderr)
            return 1
        BASELINE.write_text(text, encoding="utf-8")
        print(f"wrote {BASELINE}")
        return 0
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    print("\n".join(compare(base, now)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
