"""Hosted acceptance writer: turns one audited seed run into the per-candidate acceptance records
the counter reads (docs/DELIVERY_PLAN_2026-11-07.md section 5.3, "Attestation").

Run only by ``.github/workflows/acceptance-write.yml`` on ``main`` (environment:
acceptance-audit): it decrypts the seed manifest, reads the COMMITTED, FROZEN auditor findings,
applies the audit gates, and writes ONE file, ``acceptance-records-<seed_run_id>.json``. The
workflow then attests that file; ``ops/checks/portfolio_delivery_count.py`` counts a record only
when ``gh attestation verify`` ties the file to this exact workflow on ``main``.

Fail closed: a missing key, an empty seeded or clean population, a gate below threshold or an
unreadable finding sets ``audit_passed`` false for EVERY record and the file still records why.
Only a CLEAN CONTROL (the real sealed candidate, unmodified) can ever pass; a seeded copy is
audit material, never a candidate. ``--dry-run`` takes a plaintext manifest, never reads a key,
and marks the document ``dry_run`` so the counter ignores it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.score import (  # noqa: E402
    FLAGGED_VERDICTS,
    ScoringError,
    false_flag_rate,
    seeded_recall,
)
from repo_presenter.acceptance.audit.seed import (  # noqa: E402
    CLEAN_SHAPE,
    decrypt_seed_manifest,
    key_manifest_by_case_id,
)

SCHEMA = "acceptance-records/1"
SEEDED_RECALL_MIN = 0.90
FALSE_FLAG_RATE_MAX = 0.10
VERDICTS = frozenset({"supported", "false", "unverifiable"})

#: (repository, lane) -> (revision, certified): what ``repo_presenter.recertify`` says about the
#: latest seal under current code. Injected so tests and the dry run never touch the network.
Recertified = Mapping[tuple[str, str], tuple[str, bool]]


def recertified_from_remote(remote: str = "origin") -> Recertified:
    from repo_presenter.recertify import portfolio_recertification

    results, _history = portfolio_recertification(
        remote=remote, registry=REPO_ROOT / "data" / "registry.json", prompts_dir=REPO_ROOT / "prompts"
    )
    return {(r.repository, r.lane): (r.revision, bool(r.certified)) for r in results}


def evidence_validity(findings: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    """Structural validity only: every finding names a path, a positive line and a known verdict.
    That a cited line really holds the claim needs the pinned source clone and is NOT checked
    here, so the document records ``citations_checked: structural``."""
    for index, item in enumerate(findings):
        if item.get("verdict") not in VERDICTS:
            return False, f"finding {index} has verdict {item.get('verdict')!r}"
        if not str(item.get("path") or "").strip():
            return False, f"finding {index} cites no path"
        line = item.get("line")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            return False, f"finding {index} cites line {line!r}"
        if not str(item.get("candidate_id") or "").strip():
            return False, f"finding {index} names no candidate"
    return True, ""


def _adjudication_index(adjudications: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int], str]:
    """(case_id, line) -> 'confirmed' | 'refuted' for flags raised on clean controls. An
    adjudication is a second, independent check of the flag against the pinned source: a CONFIRMED
    flag is a real defect in the candidate (the candidate fails, the auditor was right); a REFUTED
    flag is an auditor false flag. Anything else is ignored, so an unadjudicated flag keeps
    counting against the auditor (fail closed)."""
    index: dict[tuple[str, int], str] = {}
    for item in adjudications:
        verdict = item.get("adjudication")
        line = item.get("line")
        if verdict in ("confirmed", "refuted") and isinstance(line, int) and not isinstance(line, bool):
            index[(str(item.get("candidate_id")), line)] = verdict
    return index


def evaluate_gates(
    manifest: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], list[str]]:
    """(gate numbers, reasons the audit fails). An empty reason list means every gate holds."""
    reasons: list[str] = []
    gates: dict[str, Any] = {
        "seeded_recall": None, "false_flag_rate": None,
        "thresholds": {"seeded_recall_min": SEEDED_RECALL_MIN, "false_flag_rate_max": FALSE_FLAG_RATE_MAX},
        "citations_checked": "structural",
    }
    valid, why = evidence_validity(findings)
    gates["evidence_validity"] = valid
    if not valid:
        reasons.append(f"evidence validity: {why}")
    clean_ids = [str(m["candidate_id"]) for m in manifest if m.get("shape") == CLEAN_SHAPE]
    try:
        recall = seeded_recall(findings, manifest)
        gates["seeded_recall"] = {"matched": recall.matched, "total": recall.total, "rate": recall.rate}
        if recall.rate < SEEDED_RECALL_MIN:
            reasons.append(f"seeded recall {recall.rate:.3f} < {SEEDED_RECALL_MIN}")
    except (ScoringError, KeyError) as error:
        reasons.append(f"seeded recall undefined: {error}")
    try:
        adjudicated = _adjudication_index(adjudications)
        # A flag an independent check CONFIRMED is a true finding, not an auditor false flag.
        counted = [
            f for f in findings
            if adjudicated.get((str(f.get("candidate_id")), f.get("line"))) != "confirmed"
        ]
        flag = false_flag_rate(counted, clean_ids)
        gates["false_flag_rate"] = {"matched": flag.matched, "total": flag.total, "rate": flag.rate}
        if flag.rate > FALSE_FLAG_RATE_MAX:
            reasons.append(f"false-flag rate {flag.rate:.3f} > {FALSE_FLAG_RATE_MAX}")
    except ScoringError as error:
        reasons.append(f"false-flag rate undefined: {error}")
    return gates, reasons


def build_records_document(
    seed_run_id: str,
    case_index: Sequence[Mapping[str, Any]],
    manifest: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    recertified: Recertified,
    *,
    dry_run: bool = False,
    adjudications: Sequence[Mapping[str, Any]] = (),
    verbatim_baseline: Callable[[str, int], bool] | None = None,
) -> dict[str, Any]:
    gates, reasons = evaluate_gates(manifest, findings, adjudications)
    adjudicated = _adjudication_index(adjudications)
    shapes = {str(m.get("candidate_id")): m.get("shape") for m in manifest}
    lanes = {str(e["case_id"]): str(e["lane"]) for e in case_index}
    # R21/R20: a CONFIRMED defect on a Lane L line that is verbatim maintainer text in the baseline
    # README is a recorded residual (the candidate did not introduce it), not a blocker.
    residuals: dict[str, list[int]] = {}

    def _residual(case_id: str, line: Any) -> bool:
        if (
            verbatim_baseline is not None and lanes.get(case_id) == "L"
            and adjudicated.get((case_id, line)) == "confirmed" and isinstance(line, int)
            and verbatim_baseline(case_id, line)
        ):
            residuals.setdefault(case_id, []).append(line)
            return True
        return False

    # a candidate is blocked by any flag that was not REFUTED by the independent check, or that is
    # a Lane L residual
    flagged = {
        str(f.get("candidate_id")) for f in findings
        if f.get("verdict") in FLAGGED_VERDICTS
        and adjudicated.get((str(f.get("candidate_id")), f.get("line"))) != "refuted"
        and not _residual(str(f.get("candidate_id")), f.get("line"))
    }
    batch_passed = not reasons
    records: list[dict[str, Any]] = []
    for entry in case_index:
        case_id = str(entry["case_id"])
        repository, lane, revision = str(entry["repository"]), str(entry["lane"]), str(entry["revision"])
        clean = shapes.get(case_id) == CLEAN_SHAPE
        seal_revision, certified = recertified.get((repository, lane), ("", False))
        validated = bool(certified) and seal_revision == revision
        records.append({
            "case_id": case_id, "repository": repository, "lane": lane, "revision": revision,
            "role": "clean_control" if clean else "seeded",
            "deterministically_validated": validated,
            "mechanism_verdicts": {"recertify": validated},
            "canaries": {},
            "audit_passed": bool(batch_passed and clean and case_id not in flagged),
            **({"residual_lines": sorted(set(residuals[case_id]))} if case_id in residuals else {}),
        })
    # Post-audit diagnostics: this document is written only AFTER the findings are frozen, so
    # naming what was missed cannot leak into the audit it describes.
    caught = {(str(f.get("candidate_id")), f.get("line")) for f in findings if f.get("verdict") in FLAGGED_VERDICTS}
    missed = [
        {"case_id": str(m["candidate_id"]), "shape": m.get("shape"), "operator": m.get("operator"), "line": m.get("line")}
        for m in manifest
        if m.get("shape") != CLEAN_SHAPE and (str(m["candidate_id"]), m.get("line")) not in caught
    ]
    return {
        "schema": SCHEMA, "seed_run_id": str(seed_run_id), "dry_run": dry_run,
        "gates": gates, "batch_passed": batch_passed, "failed_reasons": reasons,
        "missed_seeded": missed,
        "records": records,
    }


def baseline_checker(case_index: Sequence[Mapping[str, Any]], candidates_dir: Path) -> Callable[[str, int], bool]:
    """(case_id, 1-based line) -> True when that candidate line, stripped, is a non-empty line of the
    upstream README at the audited revision (fetched once per case; unreachable means False, so a
    missing baseline never turns a blocker into a residual)."""
    import urllib.request

    by_case = {str(e["case_id"]): e for e in case_index}
    cache: dict[str, tuple[list[str], set[str]] | None] = {}

    def load(case_id: str) -> tuple[list[str], set[str]] | None:
        if case_id not in cache:
            entry = by_case[case_id]
            try:
                cand = (candidates_dir / f"{case_id}.md").read_text(encoding="utf-8").splitlines()
                request = urllib.request.Request(
                    f"https://api.github.com/repos/{entry['repository']}/readme?ref={entry['revision']}",
                    headers={"Accept": "application/vnd.github.raw", "User-Agent": "acceptance-writer"}
                    | ({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    base = {ln.strip() for ln in response.read().decode("utf-8").splitlines() if ln.strip()}
                cache[case_id] = (cand, base)
            except Exception:  # noqa: BLE001 -- unverifiable is not verbatim
                cache[case_id] = None
        return cache[case_id]

    def verbatim(case_id: str, line: int) -> bool:
        loaded = load(case_id)
        if loaded is None or not 1 <= line <= len(loaded[0]):
            return False
        text = loaded[0][line - 1].strip()
        return bool(text) and text in loaded[1]

    return verbatim


def main(argv: Sequence[str] | None = None, *, recertify: Callable[[], Recertified] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed-run-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="seed_manifest.enc (plain JSON with --dry-run)")
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--case-index", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, default=None,
                        help="frozen JSON list of independent adjudications of flags on clean controls")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)

    if args.dry_run:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    else:
        key_hex = os.environ.get("AUDIT_SEED_KEY")
        if not key_hex:
            print("FAIL: AUDIT_SEED_KEY is not set", file=sys.stderr)
            return 1
        manifest = decrypt_seed_manifest(args.manifest.read_bytes(), bytes.fromhex(key_hex))
    manifest = key_manifest_by_case_id(manifest)
    findings = json.loads(args.findings.read_text(encoding="utf-8"))
    case_index = json.loads(args.case_index.read_text(encoding="utf-8"))
    adjudications = json.loads(args.adjudications.read_text(encoding="utf-8")) if args.adjudications else []
    recertified = (recertify or (lambda: recertified_from_remote(args.remote)))()
    document = build_records_document(
        args.seed_run_id, case_index, manifest, findings, recertified, dry_run=args.dry_run,
        adjudications=adjudications,
        verbatim_baseline=None if args.dry_run else baseline_checker(case_index, args.case_index.parent / "candidates"),
    )
    args.out.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    passed = sum(1 for r in document["records"] if r["audit_passed"])
    print(f"batch_passed={document['batch_passed']} audit_passed={passed}/{len(document['records'])}")
    for reason in document["failed_reasons"]:
        print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
