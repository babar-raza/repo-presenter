"""M9 hosted seeder (TC-014's seed.py logic, wired for real): selects >=10 real sealed candidates
per lane from this repository's own bundle-ref history, seeds a defect (or keeps a clean
control) into each, and encrypts the ground-truth manifest with AUDIT_SEED_KEY so neither the
supervisor nor the auditor can see which candidates were seeded, or how, before the audit is
committed.

Design doc (docs/design/2026-11-06-acceptance-redesign.md section 4.3): ">=10 sealed candidates
per lane (>=20 seeds of shapes A, D, D9, D14, D15)". Candidate IDENTITY (repository, lane,
revision) is NOT blinded -- the auditor needs it to check claims against the real, pinned source.
What is blinded is which candidates carry a seeded defect, and which operator/shape/span was
used; that is exactly what the encrypted manifest holds.

Run only in the hosted `audit-seed.yml` workflow (environment: acceptance-audit, so
AUDIT_SEED_KEY resolves) -- never by the supervisor locally with a decrypt step, since the
supervisor already knows AUDIT_SEED_KEY's value (generated it) and must never see which
candidates were seeded before an audit is committed against them.

Outputs (all under --out-dir):
  candidates/<case_id>.md       -- the (possibly seeded) README text, auditor-facing, in the
                                    clear, named by case_id (not by shape/operator).
  case_index.json               -- {case_id: {repository, lane, revision}}, in the clear (the
                                    auditor needs this to know what to check).
  seed_manifest.enc             -- the encrypted ground truth (Fernet, AUDIT_SEED_KEY).
  commitment.sha256             -- sha256 hex digest of seed_manifest.enc, committed to the repo
                                    BEFORE any audit begins, so it cannot be swapped afterward.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.seed import (  # noqa: E402
    CLEAN_SHAPE,
    BLIND_SHAPES,
    SeedingError,
    clean_control,
    encrypt_seed_manifest,
    seed_shape,
)
from repo_presenter.core.state.bundle_store import seal_history  # noqa: E402

MIN_PER_LANE = 10
#: Roughly 1 in 4 candidates stays a clean control -- only a clean control can become an accepted
#: record, so a larger share means more candidates can be accepted per batch (>= 20 seeded still
#: holds at the 36 candidates of the full portfolio). Formerly 1 in 6 (false-flag-rate measurement needs some, but
#: the design minimum of >=20 SEEDED cases across ~24 available candidates leaves little room).
CLEAN_EVERY = 4


def select_candidates(remote: str = "origin", scratch: Path | None = None):
    history = seal_history(remote=remote, scratch=scratch)
    by_lane: dict[str, list] = {"L": [], "R": []}
    for (repository, lane), seals in sorted(history.items()):
        if lane not in by_lane or not seals:
            continue
        latest = seals[-1]
        if not latest.readme or latest.error:
            continue
        by_lane[lane].append((repository, latest))
    return by_lane


def build_seed_plan(by_lane: dict[str, list], salt: int = 0) -> tuple[list[dict], list[dict]]:
    """(case_index_entries, manifest_records) -- deterministic, ordered, so a dry run and the
    real hosted run select identically given the same seal history."""
    case_index: list[dict] = []
    manifest: list[dict] = []
    shape_cycle = list(BLIND_SHAPES)
    for lane, entries in sorted(by_lane.items()):
        shape_i = salt  # a burned batch's seeds must not repeat: rotate shapes and controls by salt
        for i, (repository, seal) in enumerate(entries):
            readme_text = seal.readme.decode("utf-8", errors="replace")
            case_id = hashlib.sha256(f"{repository}|{lane}|{seal.revision}".encode()).hexdigest()[:16]
            if (i + salt) % CLEAN_EVERY == 0:
                result = clean_control(f"{repository}@{lane}@{seal.revision}", readme_text)
            else:
                shape = shape_cycle[shape_i % len(shape_cycle)]
                shape_i += 1
                try:
                    result = seed_shape(f"{repository}@{lane}@{seal.revision}", readme_text, shape)
                except SeedingError:
                    result = clean_control(f"{repository}@{lane}@{seal.revision}", readme_text)
            case_index.append({
                "case_id": case_id, "repository": repository, "lane": lane,
                "revision": seal.revision, "text": result.seeded_readme,
            })
            manifest.append({"case_id": case_id, **result.record.as_dict()})
    return case_index, manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--dry-run", action="store_true", help="select and plan, write nothing")
    parser.add_argument("--salt", type=int, default=0, help="rotate which candidates are controls and which shapes they get (use the workflow run id)")
    args = parser.parse_args()

    by_lane = select_candidates(remote=args.remote)
    for lane, entries in by_lane.items():
        if len(entries) < MIN_PER_LANE:
            print(f"WARNING: lane {lane} has only {len(entries)} sealed candidates "
                  f"(design minimum {MIN_PER_LANE})", file=sys.stderr)

    case_index, manifest = build_seed_plan(by_lane, args.salt)
    seeded_count = sum(1 for m in manifest if m["shape"] != CLEAN_SHAPE)
    print(f"selected {sum(len(v) for v in by_lane.values())} candidates "
          f"({len(by_lane.get('L', []))} L, {len(by_lane.get('R', []))} R); "
          f"{seeded_count} seeded, {len(manifest) - seeded_count} clean controls")

    if args.dry_run:
        return 0

    key_hex = os.environ.get("AUDIT_SEED_KEY")
    if not key_hex:
        print("FAIL: AUDIT_SEED_KEY is not set", file=sys.stderr)
        return 1
    key = bytes.fromhex(key_hex)

    out = args.out_dir
    (out / "candidates").mkdir(parents=True, exist_ok=True)
    public_index = []
    for entry in case_index:
        (out / "candidates" / f"{entry['case_id']}.md").write_text(entry["text"], encoding="utf-8")
        public_index.append({
            "case_id": entry["case_id"], "repository": entry["repository"],
            "lane": entry["lane"], "revision": entry["revision"],
        })
    (out / "case_index.json").write_text(json.dumps(public_index, indent=2), encoding="utf-8")

    blob = encrypt_seed_manifest(manifest, key)
    (out / "seed_manifest.enc").write_bytes(blob)
    (out / "commitment.sha256").write_text(hashlib.sha256(blob).hexdigest() + "\n", encoding="utf-8")

    print(f"wrote {len(case_index)} candidate files, manifest commitment "
          f"{hashlib.sha256(blob).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
