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


def score(manifest: list[dict], findings: list[Finding]) -> dict:
    clean_control_ids = [m["candidate_id"] for m in manifest if m["shape"] == CLEAN_SHAPE]
    recall = seeded_recall(findings, manifest)
    flag_rate = false_flag_rate(findings, clean_control_ids)
    return {
        "seeded_recall": {"matched": recall.matched, "total": recall.total, "rate": recall.rate},
        "false_flag_rate": {
            "matched": flag_rate.matched, "total": flag_rate.total, "rate": flag_rate.rate,
        },
        "defective_accepted_rate": None,
        "defective_accepted_rate_note": (
            "not computed: this seed batch has no separate unseeded-accepted population "
            "outside the seeded/clean-control split -- see this script's own module docstring"
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True, help="seed_manifest.enc")
    parser.add_argument("--findings", type=Path, required=True, help="committed findings JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    key_hex = os.environ.get("AUDIT_SEED_KEY")
    if not key_hex:
        print("FAIL: AUDIT_SEED_KEY is not set", file=sys.stderr)
        return 1
    key = bytes.fromhex(key_hex)

    manifest = key_manifest_by_case_id(decrypt_seed_manifest(args.manifest.read_bytes(), key))
    findings = load_findings(args.findings)
    result = score(manifest, findings)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
