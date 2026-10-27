"""Build the reviewer's forest calibration corpus from real cascade outputs and run the harness.

    python scripts/run_reviewer_calibration.py corpus --work NAME=PATH ... --recorded-clones DIR
        [--lane-r NAME=OUTPUT_DIR,CLONE_DIR[,BC-07,...] ...]
    python scripts/run_reviewer_calibration.py live   --work NAME=PATH ... --cap 200 [--out DIR]

``--work`` points at the ``.present-work`` directory of a downloaded hosted cascade run (named
``run5``, ``run7`` or ``run9``; the curated repairs below belong to those candidates). ``corpus``
is offline: it prints every case with what the deterministic stage alone would do. ``live`` asks
the gateway through ``llm_review.review_with_model`` -> ``core/llm/jobs.run_job`` only, under a hard
cap on physical provider calls counted from the ledger file (``--cap``, default 200), and stops the
moment the ledger holds that many. Nothing here pushes, dispatches a workflow or edits a rule.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from repo_presenter.core.config import load_gateway_config
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.review.calibration.corpus import (
    Base,
    Case,
    RecordedDefect,
    Repair,
    build_corpus,
)
from repo_presenter.readme.review.calibration.harness import (
    CaseResult,
    PreLLM,
    Run,
    compute_metrics,
    evaluate_gates,
    pre_llm,
    run_corpus,
)
from repo_presenter.readme.review.calibration.reviewers import (
    LiveReviewer,
    physical_calls,
)
from repo_presenter.readme.review.calibration.sources import (
    load_cascade_candidate,
    load_lane_r_candidate,
)

#: The defects this project's own reading of each candidate found, as the edit that removes each.
REPAIRS: dict[str, tuple[Repair, ...]] = {
    "run7": (
        Repair(
            " with full round-trip fidelity,",
            ",",
            "'full round-trip fidelity' is stated by no fact (the maintainers' README says it; "
            "no extracted fact does)",
            klass="unsupported_claim",
            targets=("round-trip", "fidelity"),
        ),
        Repair(
            ", and exposes `Aspose.ThreeD.Render` and `Aspose.ThreeD.Utilities` for rendering and "
            "utility operations in the net ecosystem.",
            ".",
            "says the library exposes rendering; inherited_unit:061 states rendering is not "
            "implemented in this FOSS build",
            klass="contradiction",
            targets=("aspose.threed.render", "rendering"),
        ),
    ),
    "run5": (
        Repair(
            " — with full round-trip fidelity, plus",
            ", plus",
            "'full round-trip fidelity' is stated by no fact",
            klass="unsupported_claim",
            targets=("round-trip", "fidelity"),
        ),
    ),
    "run9": (),
}
#: run9 is a hosted python candidate whose deterministic checks BC-02 (the registry's ownership
#: receipt for the package name) and BC-07 (a dangling colon and a 'below' pointer inside two
#: inherited units kept verbatim) fail. Neither can be repaired by editing text (the inherited
#: units must print as written), so the python twin carries them as a stated baseline.
TOLERATED = {"run9": ("BC-02", "BC-07")}
RECORDED = {
    "font": (
        "aspose-font-foss__Aspose.Font-FOSS-for-Python",
        Path("scripts/_lane_r_output"),
        "broken_install",
        (
            Repair(
                'pip install "aspose-font[mcp]"',
                'pip install "aspose-font-foss[mcp]"',
                "the inherited MCP install command names a distribution the project does not publish",
            ),
        ),
        (
            "recorded 2026-10-22: the inherited install command names 'aspose-font' but the "
            "package is 'aspose-font-foss' (evidence/build/P2_REAL_ENGINE_SALVAGE/"
            "aspose-font-foss__Aspose.Font-FOSS-for-Python)"
        ),
        ("aspose-font[mcp]", "mcp"),
    ),
    "duplicate_opening": (
        "aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript",
        Path("evidence/build/P2_REAL_ENGINE_SALVAGE/lane_r_ninth_full_cascade"),
        "duplicate_paragraph",
        (),
        (
            "recorded 2026-10-22: coherence made the opening a near word-for-word copy of the "
            "preserved paragraph beside it (lane_r_ninth_full_cascade)"
        ),
        ("duplicat", "restate", "near word-for-word", "opening"),
    ),
}


def parse_work(items: list[str]) -> dict[str, Path]:
    pairs = (item.split("=", 1) for item in items)
    return {name: Path(path) for name, path in pairs}


def parse_lane_r(items: list[str]) -> list[tuple[str, Path, Path, tuple[str, ...]]]:
    """``NAME=OUTPUT_DIR,CLONE_DIR[,CHECK...]``: a per-script Lane R output, the clone supplying its
    live README, and the blocking checks its candidate is known to fail (inherited text)."""
    found = []
    for item in items:
        name, spec = item.split("=", 1)
        output, clone, *tolerated = spec.split(",")
        found.append((name, Path(output), Path(clone), tuple(tolerated)))
    return found


def build(
    work: dict[str, Path],
    clones: Path | None,
    lane_r: list[tuple[str, Path, Path, tuple[str, ...]]] = (),
) -> list[Case]:
    bases = [
        Base(
            load_cascade_candidate(path, name=name),
            REPAIRS.get(name, ()),
            tolerated_checks=TOLERATED.get(name, ()),
        )
        for name, path in work.items()
    ]
    for name, output, clone, tolerated in lane_r:
        source = load_lane_r_candidate(
            output,
            facts_path=Path("scripts/_lane_l_output") / output.name / "facts.json",
            clone=clone,
            name=name,
        )
        bases.append(Base(source, (), tolerated_checks=tolerated))
    recorded = []
    if clones is not None:
        for key, (repo, output, klass, repairs, note, targets) in RECORDED.items():
            source = load_lane_r_candidate(
                output / repo if output.name == "_lane_r_output" else output,
                facts_path=Path("scripts/_lane_l_output") / repo / "facts.json",
                clone=clones / repo,
                name=key,
                recorded=True,
            )
            recorded.append(RecordedDefect(source, klass, repairs, note, targets))
    return build_corpus(bases, recorded)


def describe(case: Case, pre: PreLLM) -> str:
    stage = ",".join((*pre.rules, *pre.checks)) or "-"
    return f"{case.case_id:62s} {case.role:12s} {case.klass or '-':20s} {case.ecosystem:7s} det:{stage}"


def stratified(cases: list[Case], per_class: int) -> list[Case]:
    """Every clean twin (scored or not) and real defect, plus at most ``per_class`` mutants of each class,
    taken round-robin across bases so every ecosystem is represented."""
    chosen = [c for c in cases if c.role in {"clean", "real_defect", "unscored_twin"}]
    by_class: dict[str, list[Case]] = {}
    for case in cases:
        if case.role == "mutant":
            by_class.setdefault(case.klass or "?", []).append(case)
    for klass, members in sorted(by_class.items()):
        bases = sorted({m.base for m in members})
        ordered = [
            m
            for index in range(len(members))
            for m in members
            if m.base == bases[index % len(bases)]
        ]
        seen: list[Case] = []
        for member in ordered + members:
            if member not in seen:
                seen.append(member)
        chosen.extend(seen[:per_class])
    return chosen


def result_record(result: CaseResult) -> dict:
    return {
        "case": result.case.case_id,
        "role": result.case.role,
        "klass": result.case.klass,
        "ecosystem": result.case.ecosystem,
        "pre_llm_rules": list(result.pre.rules),
        "pre_llm_checks": list(result.pre.checks),
        "outcomes": [
            {
                "verdict": o.verdict,
                "calls": o.calls,
                "json_valid_first": o.first_reply_json_valid,
                "contract_valid_first": o.first_reply_contract_valid,
                "blocking_kinds": list(o.blocking_kinds),
                "cleared": o.cleared,
                "model": o.model_served,
                "evidence": list(o.evidence),
                "detail": o.detail,
            }
            for o in result.outcomes
        ],
    }


def print_metrics(run: Run) -> None:
    metrics = compute_metrics(run)
    print(
        f"cases asked {metrics.cases_asked}, provider calls {metrics.calls}, stopped: {run.stopped or 'no'}"
    )
    for klass, stats in metrics.per_class.items():
        print(
            f"  {klass:20s} n={stats.n} llm_recall={stats.llm_recall()} "
            f"llm_on_target={stats.llm_target_recall()} "
            f"pipeline_recall={stats.pipeline_recall()} "
            f"pipeline_on_target={stats.pipeline_target_recall()} unavailable={stats.unavailable}"
        )
    print(
        f"  clean n={metrics.clean_n} llm_false_reject={metrics.false_reject_rate} "
        f"pipeline_false_reject={metrics.pipeline_false_reject_rate} unavailable={metrics.clean_unavailable} "
        f"approved_yield={metrics.approved_yield}"
    )
    print(
        f"  first replies {metrics.first_replies} json_valid={metrics.json_valid_first_reply_rate} "
        f"contract_valid={metrics.contract_valid_first_reply_rate} stability={metrics.stability} "
        f"(n={metrics.repeated_cases}) content_loss_rate={metrics.content_loss_rate}"
    )
    print(
        f"  unscored recorded twins asked {metrics.unscored_n}, llm-rejected {metrics.unscored_llm_rejected}"
    )
    for scope in ("llm", "pipeline"):
        for gate in evaluate_gates(metrics, scope=scope):
            print(f"  [{scope}] {gate.line()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["corpus", "live"])
    parser.add_argument("--work", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--recorded-clones", type=Path)
    parser.add_argument(
        "--lane-r", action="append", default=[], metavar="NAME=OUT,CLONE[,CHECK]"
    )
    parser.add_argument("--out", type=Path, default=Path(".calibration"))
    parser.add_argument("--cap", type=int, default=200)
    parser.add_argument("--per-class", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--only", help="comma-separated case ids; default is the stratified sample"
    )
    parser.add_argument(
        "--tag",
        default="pass1",
        help="names the call store (a new tag bypasses the cache)",
    )
    parser.add_argument(
        "--model", help="ask this model instead of the manifest's route"
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=Path("prompts"),
        help="the manifests directory (a candidate prompt is tried by pointing here)",
    )
    parser.add_argument(
        "--results-name",
        help="the results file name (default results-<tag>.jsonl); a replay of a cached pass "
        "uses another name so it does not overwrite the first-reply flags",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="a new call store for every review (no cache replay)",
    )
    args = parser.parse_args(argv)

    cases = build(
        parse_work(args.work), args.recorded_clones, parse_lane_r(args.lane_r)
    )
    if args.mode == "corpus":
        for case in cases:
            print(
                describe(
                    case,
                    pre_llm(case) if case.role != "unscored_twin" else PreLLM((), ()),
                )
            )
        print(f"{len(cases)} cases")
        return 0

    from repo_presenter.core.llm.fallback import ModelSelection, RouteDecision

    selected = (
        [c for c in cases if c.case_id in set(args.only.split(","))]
        if args.only
        else stratified(cases, args.per_class)
    )
    models = None
    if args.model:
        route = load_manifests(args.prompts)["independent_review"].manifest.model_route
        models = ModelSelection(
            (), {route: RouteDecision(route, (route,), args.model, None, "calibration")}
        )
    args.out.mkdir(parents=True, exist_ok=True)
    ledger_path = args.out / "ledger.jsonl"
    reviewer = LiveReviewer(
        prompts=load_manifests(args.prompts),
        config=load_gateway_config(os.environ),
        ledger_path=ledger_path,
        store_dir=args.out / "calls" / args.tag,
        cap=args.cap,
        models=models,
        fresh_store_per_call=args.fresh,
    )
    print(
        f"{len(selected)} cases selected; ledger holds {physical_calls(ledger_path)} of {args.cap} calls"
    )
    run = run_corpus(selected, reviewer, repeats=args.repeats)
    out_file = args.out / (args.results_name or f"results-{args.tag}.jsonl")
    with out_file.open("w", encoding="utf-8", newline="\n") as stream:
        for result in run.results:
            stream.write(json.dumps(result_record(result), sort_keys=True) + "\n")
    print_metrics(run)
    print(
        f"ledger now holds {physical_calls(ledger_path)} of {args.cap} calls; results: {out_file}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
