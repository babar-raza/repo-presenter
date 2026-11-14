"""M9 hosted scorer (TC-014's score.py logic, wired for real): decrypts the seed manifest a prior
`audit-seed.yml` run produced, reads a COMMITTED, FROZEN set of auditor findings, and computes
the real seeded-recall and false-flag-rate gates (docs/design/2026-11-06-acceptance-redesign.md
section 4.3).

Run only in the hosted `audit-score.yml` workflow (environment: acceptance-audit) -- never by
the supervisor locally with the real AUDIT_SEED_KEY, for the same reason the seeder is hosted-
only: decrypting the manifest reveals which candidates were seeded, which must never happen
before the findings are frozen (committed, unchangeable).

``defective_accepted_rate`` (the third M9 gate: do already-accepted, non-batch candidates hide
an undisclosed defect) is intentionally NOT computed by this script yet: this seed batch's design
(run_m9_seeder.py) draws every candidate from the SAME selected set that is split into seeded/
clean-control -- there is no separate "unseeded, already-accepted, outside this batch" population
to measure it against. This is a known, flagged gap (see this module's own docstring), not a
silent omission.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.score import (  # noqa: E402
    Finding,
    false_flag_rate,
    seeded_recall,
)
from repo_presenter.acceptance.audit.seed import (  # noqa: E402
    CLEAN_SHAPE,
    decrypt_seed_manifest,
    key_manifest_by_case_id,
)


def load_findings(path: Path) -> list[Finding]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Finding(
            candidate_id=item["candidate_id"], claim=item["claim"], verdict=item["verdict"],
            path=item["path"], line=int(item["line"]),
        )
        for item in raw
    ]


def split_candidate_id(candidate_id: str) -> tuple[str, str, str] | None:
    """``(repository, lane, revision)`` of a seeder candidate id ``<repository>@<lane>@<revision>``."""
    parts = str(candidate_id).rsplit("@", 2)
    return (parts[0], parts[1], parts[2]) if len(parts) == 3 and all(parts) else None


def not_recertified_controls(raw_manifest: list[dict], recertified: set[tuple[str, str, str]]) -> list[str]:
    """BL-075: the case ids of clean controls whose seal, at the audited revision, does not re-certify
    under current code (``repo_presenter.recertify``) -- the population the acceptance writer reports
    as ``controls_not_recertified`` and leaves out of its false-flag rate. ``raw_manifest`` is the
    decrypted manifest before ``key_manifest_by_case_id`` (its candidate ids still name the seal)."""
    found = []
    for entry in raw_manifest:
        if entry.get("shape") != CLEAN_SHAPE:
            continue
        key = split_candidate_id(str(entry.get("candidate_id", "")))
        if key is None or key not in recertified:
            found.append(str(entry.get("case_id", entry.get("candidate_id"))))
    return sorted(found)


def _metric(metric) -> dict:
    return {"matched": metric.matched, "total": metric.total, "rate": metric.rate}


def score(manifest: list[dict], findings: list[Finding], not_recertified: list[str] | None = None) -> dict:
    clean_control_ids = [m["candidate_id"] for m in manifest if m["shape"] == CLEAN_SHAPE]
    recall = seeded_recall(findings, manifest)
    flag_rate = false_flag_rate(findings, clean_control_ids)
    result = {
        "seeded_recall": _metric(recall),
        "false_flag_rate": _metric(flag_rate),
        "defective_accepted_rate": None,
        "defective_accepted_rate_note": (
            "not computed: this seed batch has no separate unseeded-accepted population "
            "outside the seeded/clean-control split -- see this script's own module docstring"
        ),
    }
    if not_recertified is not None:
        # BL-075: the raw figure above stays the scorecard's gate figure (thresholds unchanged); beside it,
        # the split by whether the control's seal re-certifies under current code -- the population the
        # acceptance writer judges (it leaves controls_not_recertified out of its rate).
        excluded = set(not_recertified)
        stale = [cid for cid in clean_control_ids if cid in excluded]
        fresh = [cid for cid in clean_control_ids if cid not in excluded]
        result["false_flag_split"] = {
            "recertified_controls": _metric(false_flag_rate(findings, fresh)) if fresh else None,
            "not_recertified_controls": _metric(false_flag_rate(findings, stale)) if stale else None,
            "controls_not_recertified": sorted(stale),
            "note": "raw false_flag_rate is the gate figure (thresholds unchanged); the acceptance writer "
                    "leaves controls_not_recertified out of its rate",
        }
    return result


def render_split(result: dict) -> str:
    """One line: the raw false-flag figure with its re-certified / not-re-certified split beside it."""
    raw = result["false_flag_rate"]
    line = f"false-flag (raw): {raw['matched']}/{raw['total']}"
    split = result.get("false_flag_split")
    if split is None:
        return line + "; not-recertified split: not computed"
    parts = []
    for label, key in (("recertified controls", "recertified_controls"),
                       ("not-recertified controls", "not_recertified_controls")):
        value = split.get(key)
        parts.append(f"{label} {value['matched']}/{value['total']}" if value else f"{label} 0/0")
    return line + "; " + ", ".join(parts)


def recertified_seals(remote: str = "origin") -> set[tuple[str, str, str]]:
    """(repository, lane, revision) of every latest seal RECERTIFIED under current code (zero provider
    calls), read as the acceptance writer reads it."""
    from repo_presenter.recertify import portfolio_recertification

    results, _history = portfolio_recertification(
        remote=remote, registry=REPO_ROOT / "data" / "registry.json", prompts_dir=REPO_ROOT / "prompts"
    )
    return {(r.repository, r.lane, r.revision) for r in results if r.recertified}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True, help="seed_manifest.enc")
    parser.add_argument("--findings", type=Path, required=True, help="committed findings JSON")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--remote", default="origin",
                        help="state remote for the zero-call re-certification of each control's seal (BL-075)")
    parser.add_argument("--no-recertify", action="store_true",
                        help="skip the not-recertified split (the raw figures are the same either way)")
    args = parser.parse_args()

    key_hex = os.environ.get("AUDIT_SEED_KEY")
    if not key_hex:
        print("FAIL: AUDIT_SEED_KEY is not set", file=sys.stderr)
        return 1
    key = bytes.fromhex(key_hex)

    raw = list(decrypt_seed_manifest(args.manifest.read_bytes(), key))
    manifest = key_manifest_by_case_id(raw)
    findings = load_findings(args.findings)
    stale = None
    if not args.no_recertify:
        try:
            stale = not_recertified_controls(raw, recertified_seals(args.remote))
        except Exception as error:  # noqa: BLE001 -- the split is a report beside the gate, never the gate
            print(f"WARNING: not-recertified split unavailable: {type(error).__name__}: {error}", file=sys.stderr)
    result = score(manifest, findings, stale)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(render_split(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
