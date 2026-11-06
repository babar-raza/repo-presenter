#!/usr/bin/env python
"""Parity gate (owner ruling R2): is a sealed candidate at least as good as the README already
published upstream? Recomputes six deterministic dimensions (``repo_presenter.readme.parity_gate``)
instead of reading a line from a document.

Exit codes: 0 only when every measured (repository, lane) reaches parity on a seal under the
CURRENT version set; 1 when any does not (or has no current-set seal); 2 on a usage error; 3 for
``--older-set`` (a labelled dry measurement against the latest seal of an OLDER version set: never
release or pause-lift evidence, whatever it measures).

    # one repository, one lane, live (latest current-set seal on origin vs. upstream HEAD README)
    python ops/checks/parity_gate.py --repository aspose-email-foss/Aspose.Email-FOSS-for-.Net --lane R
    # the sweep-pause pilot set, both lanes where each applies (pause-lift evidence when exit 0)
    python ops/checks/parity_gate.py --pilot-set [--json out.json]
    # dry measurement on each pilot's latest OLDER-set seal (always exit 3)
    python ops/checks/parity_gate.py --pilot-set --older-set
    # offline: an extracted sealed revision directory against a local README file
    python ops/checks/parity_gate.py --candidate-dir <revision dir> --benchmark <README.md> --lane R

A lane "applies" to a repository when the upstream repository publishes a README at its root
(Lane R regenerates it, Lane L maintains it; R2 sets the published README as the floor for both).
A repository without one is reported NOT_APPLICABLE for both lanes and does not block. Read-only:
no provider call, nothing pushed, the upstream README is read in a scratch clone and never stored.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.readme.parity_gate import (
    LANE_L,
    LANE_R,
    evaluate,
    fetch_benchmark,
    load_revision_dir,
    materialize_seals,
    not_measured,
    readme_changed_since,
    render,
    select_seal,
)

#: The three-product pilot set whose parity lifts the owner-upheld sweep pause.
PILOT_SET = (
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    "aspose-email-foss/Aspose.Email-FOSS-for-.Net",
    "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
)
EXIT_PARITY, EXIT_NO_PARITY, EXIT_USAGE, EXIT_DRY = 0, 1, 2, 3


def run_live(
    repositories: list[str], lanes: list[str], older: bool, remote: str
) -> list:
    from repo_presenter.core.version_set import current_fingerprints, short

    current = current_fingerprints(REPO_ROOT / "prompts")
    results = []
    with tempfile.TemporaryDirectory(prefix="parity-gate-") as tmp:
        scratch = Path(tmp)
        seals = materialize_seals(repositories, scratch / "seals", remote=remote)
        for repository in repositories:
            benchmark = None
            fetch_error = ""
            for lane in lanes:
                label = (
                    f"DRY MEASUREMENT: latest OLDER version set (current {short(current[lane])})"
                    if older
                    else f"current version set {short(current[lane])}"
                )
                rows = seals.get((repository, lane), [])
                chosen = select_seal(rows, lane, current[lane], older=older)
                context = {
                    "version_set_label": label,
                    "current_version_set": current[lane],
                    "seals_on_lane": len(rows),
                    "dry_measurement": older,
                }
                if benchmark is None and not fetch_error:
                    try:
                        benchmark = fetch_benchmark(repository, scratch / "upstream")
                    except FileNotFoundError as exc:
                        fetch_error = f"NOT_APPLICABLE: {exc}"
                    except Exception as exc:  # noqa: BLE001 -- a failed read is no parity
                        fetch_error = (
                            f"benchmark unreadable: {type(exc).__name__}: {exc}"
                        )
                if fetch_error:
                    results.append(not_measured(repository, lane, fetch_error, context))
                    continue
                context.update(
                    {
                        "benchmark_head": benchmark.head,
                        "benchmark_path": benchmark.readme_path,
                    }
                )
                if chosen is None:
                    why = (
                        "no pipeline-good seal under an older version set"
                        if older
                        else "NO_CURRENT_SET_SEAL: no pipeline-good seal under the current version set"
                    )
                    results.append(not_measured(repository, lane, why, context))
                    continue
                context.update(
                    {
                        "seal_commit": chosen.commit,
                        "seal_source_revision": chosen.revision,
                        "seal_state": chosen.manifest_state,
                        "seal_version_set": chosen.fingerprint,
                        "seal_counted": chosen.counted,
                        "benchmark_readme_changed_since_seal": readme_changed_since(
                            benchmark, chosen.revision
                        ),
                    }
                )
                candidate = load_revision_dir(chosen.revision_dir, lane)
                results.append(evaluate(repository, candidate, benchmark.text, context))
    return results


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repository")
    target.add_argument("--pilot-set", action="store_true")
    target.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--lane", choices=[LANE_R, LANE_L])
    parser.add_argument(
        "--benchmark", type=Path, help="with --candidate-dir: the benchmark README"
    )
    parser.add_argument(
        "--older-set", action="store_true", help="dry measurement; always exit 3"
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    if args.candidate_dir is not None:
        if args.benchmark is None or args.lane is None:
            parser.error("--candidate-dir needs --benchmark and --lane")
        candidate = load_revision_dir(args.candidate_dir, args.lane)
        text = args.benchmark.read_text(encoding="utf-8")
        results = [
            evaluate(str(args.candidate_dir), candidate, text, {"offline": True})
        ]
    else:
        repositories = list(PILOT_SET) if args.pilot_set else [args.repository]
        lanes = [args.lane] if args.lane else [LANE_R, LANE_L]
        results = run_live(repositories, lanes, args.older_set, args.remote)

    applicable = [
        r
        for r in results
        if not str(r.context.get("not_measured", "")).startswith("NOT_APPLICABLE")
    ]
    parity = bool(applicable) and all(r.parity for r in applicable)
    evidence = parity and not args.older_set and args.candidate_dir is None
    document = {
        "parity": parity,
        "pause_lift_evidence": bool(args.pilot_set and evidence),
        "dry_measurement": args.older_set,
        "results": [r.as_dict() for r in results],
    }
    print(render(results))
    print(
        f"\nPARITY: {'YES' if parity else 'NO'} ({sum(r.parity for r in applicable)}/{len(applicable)})"
        + (
            "  [dry measurement on older version sets: not evidence]"
            if args.older_set
            else ""
        )
        + ("  PAUSE_LIFT_EVIDENCE: YES" if document["pause_lift_evidence"] else "")
    )
    if args.json is not None:
        args.json.write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    if args.older_set:
        return EXIT_DRY
    return EXIT_PARITY if parity else EXIT_NO_PARITY


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
