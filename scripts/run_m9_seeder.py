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
from typing import Any
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
from repo_presenter.acceptance.record import (  # noqa: E402
    CANDIDATE_DIGEST_FIELD,
    CONTENT_BOUND,
    REVISION_ONLY,
    acceptance_binding,
    candidate_sha256,
)
from repo_presenter.core.state.bundle_store import seal_history  # noqa: E402

import importlib.util  # noqa: E402

# The run-request validator is stdlib-only and owns the M9 branch conventions; load it by path.
_rr_spec = importlib.util.spec_from_file_location("run_request", REPO_ROOT / "scripts" / "run_request.py")
run_request = importlib.util.module_from_spec(_rr_spec)
_rr_spec.loader.exec_module(run_request)

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


def is_noop(lane: str, seal: Any) -> bool:
    """A Lane L seal whose README equals its own recorded original: R16 says it can never be
    accepted, so a control slot spent on it is wasted."""
    files = getattr(seal, "files", None) or {}
    new, old = files.get("README.md"), files.get("README.original.md")
    return lane == "L" and bool(new) and bool(old) and new.get("sha256") == old.get("sha256")


class RecordsUnavailable(RuntimeError):
    """The acceptance-record branches could not be read: NOT the same as "no records" (BL-189)."""


#: ``judged_controls`` key: (repository, lane, revision, candidate_sha256 or ``""`` for a legacy record).
JudgedKey = tuple[str, str, str, str]


def already_accepted(remote: str = "origin") -> set[tuple[str, str, str]]:
    """(repository, lane, revision) of every clean control any acceptance-record branch marks
    audit-passed. Public data; only used to avoid spending a control slot on them again. A record bound to
    other README bytes than the current seal's is NOT excluded by this revision-keyed view -- use
    ``judged_for(judged, repository, lane, seal)`` for the seal-specific answer."""
    return {key[:3] for key, passed in judged_controls(remote).items() if passed}


def _git(remote_args: list[str], what: str) -> bytes:
    import subprocess

    done = subprocess.run(["git", *remote_args], capture_output=True, check=False)
    if done.returncode != 0:
        raise RecordsUnavailable(f"{what} failed (git exit {done.returncode}): {done.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return done.stdout


def judged_controls(remote: str = "origin") -> dict[JudgedKey, bool]:
    """{(repository, lane, revision, candidate_sha256 or ""): audit_passed} for every candidate any non-dry-run
    acceptance record already judged AS A CLEAN CONTROL (passed if any record passed it). A seeded copy is
    audit material, not a judgement of the candidate, so it is not listed. A legacy record (no digest field)
    is keyed with ``""``; a record whose digest is not 64 lowercase hex judges nothing.

    A git failure (listing, fetch, tree or blob read) raises :class:`RecordsUnavailable`: an unreadable
    record set is not an empty one (BL-189), so a transient failure can never make every candidate look
    unjudged. A readable file that is not valid JSON, or has no records, simply judges nothing."""
    found: dict[JudgedKey, bool] = {}
    listed = _git(["ls-remote", "--heads", remote, "refs/heads/acceptance-record/*"], "listing the acceptance-record branches").decode("utf-8", "replace")
    branches = [ln.split("refs/heads/", 1)[1] for ln in listed.splitlines() if "refs/heads/" in ln]
    if branches:
        _git(["fetch", "-q", remote, *[f"+refs/heads/{b}:refs/remotes/{remote}/{b}" for b in branches]], "fetching the acceptance-record branches")
    for branch in branches:
        names = _git(["ls-tree", "--name-only", f"{remote}/{branch}"], f"listing {branch}").decode("utf-8", "replace")
        for name in names.split():
            if not (name.startswith("acceptance-records-") and name.endswith(".json")):
                continue
            blob = _git(["show", f"{remote}/{branch}:{name}"], f"reading {branch}:{name}")
            try:
                doc = json.loads(blob)
                if doc.get("dry_run") is not False:
                    continue
                for r in doc["records"]:
                    if r.get("role") == "clean_control":
                        digest = r.get(CANDIDATE_DIGEST_FIELD)
                        if digest is not None and acceptance_binding(digest, digest) != CONTENT_BOUND:
                            continue  # malformed digest: judges nothing
                        key = (str(r["repository"]), str(r["lane"]), str(r["revision"]), digest or "")
                        found[key] = found.get(key, False) or r.get("audit_passed") is True
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
    return found


def judged_for(judged: dict, repository: str, lane: str, seal: Any) -> tuple[bool | None, str]:
    """(was this EXACT seal judged as a clean control -- passed? None when never --, binding label).

    A record judges the seal when its digest equals the digest of the seal's README bytes (``content_bound``),
    or when it is a legacy record without a digest at the same revision (``revision_only``: still eligible,
    reported as such). A record bound to other README bytes at the same revision judges nothing. Keys of the
    older 3-tuple shape (repository, lane, revision) are legacy records."""
    digest = candidate_sha256(seal.readme or b"")
    verdict: bool | None = None
    label = REVISION_ONLY
    for key, passed in judged.items():
        if tuple(key[:3]) != (repository, lane, seal.revision):
            continue
        recorded = key[3] if len(key) > 3 else ""
        if recorded and recorded != digest:
            continue
        if recorded:
            label = CONTENT_BOUND
        verdict = (verdict or False) or bool(passed)
    return verdict, label if verdict is not None else ""


# --- the scheduled round's gate (owner R37: the system runs itself on GitHub Actions) -------------------

#: Bounded retries: a batch whose hosted audit has started this many times without freezing findings is
#: ``blocked`` -- the gate fails visibly and the run-request override path (scripts/run_request.py) ends it.
MAX_AUDIT_ATTEMPTS = 3


def fresh_candidates(by_lane: dict[str, list], judged: dict[tuple[str, str, str], bool]) -> list[tuple[str, str, str]]:
    """(repository, lane, revision) of every latest seal that could become an accepted record and has
    not been judged as a clean control yet: a counted seal (pipeline-good, model-reviewed ACCEPT -- the
    seal standard; current-code re-certification is checked again by the acceptance writer), not a
    Lane L no-op (R16), and at a revision no acceptance record judged before. A candidate that failed
    as a control is not fresh again until it is re-sealed at a new revision, so an unchanged portfolio
    never re-spends a round on itself."""
    fresh = []
    for lane, entries in sorted(by_lane.items()):
        for repository, seal in entries:
            key = (repository, lane, seal.revision)
            if getattr(seal, "counted", False) and not is_noop(lane, seal) and judged_for(judged, repository, lane, seal)[0] is None:
                fresh.append(key)
    return fresh


def gate(
    heads: list[str],
    *,
    run_id: str,
    require_fresh: bool,
    count_fresh: Any = None,
    minimum: int = MIN_PER_LANE,
) -> dict[str, str]:
    """What this run of the round does, as ``$GITHUB_OUTPUT`` lines: ``action`` is

    * ``resume`` -- a seed batch is open (``run_request.open_seed_batches``): finish it (audit if its
      frozen findings do not exist yet, score if its scorecard does not, then write) instead of seeding;
    * ``blocked`` -- the open batch's audit has been attempted ``MAX_AUDIT_ATTEMPTS`` times;
    * ``seed`` -- no batch is open and (only on the schedule) at least ``minimum`` fresh candidates exist;
    * ``noop`` -- nothing to do; the reason says why (an evidenced no-op).

    One open batch at a time: a new seed is never spent while an earlier round is unwritten."""
    still_open = run_request.open_seed_batches(heads)
    if still_open:
        seed = still_open[0]
        attempts = sum(1 for h in heads if h.startswith(f"{run_request.ATTEMPT_BRANCH_PREFIX}{seed}-"))
        has_findings = run_request.findings_ref_for(seed) in heads
        has_score = f"{run_request.SCORE_BRANCH_PREFIX}{seed}" in heads
        action, reason = "resume", f"seed batch {seed} is open; finishing it before any new seed"
        if not has_findings and attempts >= MAX_AUDIT_ATTEMPTS:
            action = "blocked"
            reason = (f"seed batch {seed}: {attempts} hosted audit attempts froze no findings; end it with "
                      "the run-request override (scripts/run_request.py runbook)")
        return {"action": action, "seed_run_id": seed, "has_findings": str(has_findings).lower(),
                "has_score": str(has_score).lower(), "reason": reason}
    out = {"action": "seed", "seed_run_id": str(run_id), "has_findings": "false", "has_score": "false",
           "reason": "no open seed batch"}
    if require_fresh:
        fresh = count_fresh() if count_fresh is not None else 0
        if fresh < minimum:
            return {**out, "action": "noop", "seed_run_id": "",
                    "reason": f"{fresh} fresh sealed candidates (not yet judged as a clean control) < {minimum}"}
        out["reason"] = f"no open seed batch; {fresh} fresh sealed candidates >= {minimum}"
    return out


def recertified_seals(remote: str = "origin") -> set[tuple[str, str, str]]:
    """BL-075: (repository, lane, revision) of every latest seal whose zero-call re-certification under
    current code (``repo_presenter.recertify``) is RECERTIFIED -- the only seals a clean control can be
    accepted from (the acceptance writer excludes the rest as ``controls_not_recertified``)."""
    from repo_presenter.recertify import portfolio_recertification

    results, _history = portfolio_recertification(
        remote=remote, registry=REPO_ROOT / "data" / "registry.json", prompts_dir=REPO_ROOT / "prompts"
    )
    return {(r.repository, r.lane, r.revision) for r in results if r.recertified}


def _accepted_seal(accepted: Any, repository: str, lane: str, seal: Any) -> bool:
    """Is THIS seal (its README bytes, not just its revision) already accepted? ``accepted`` is either the
    judged-controls mapping (digest-aware) or a legacy set of (repository, lane, revision) triples."""
    if isinstance(accepted, dict):
        return judged_for(accepted, repository, lane, seal)[0] is True
    return (repository, lane, seal.revision) in accepted


def build_seed_plan(
    by_lane: dict[str, list], salt: int = 0, accepted: set[tuple[str, str, str]] | dict = frozenset(),
    recertified: set[tuple[str, str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """(case_index_entries, manifest_records) -- deterministic, ordered, so a dry run and the
    real hosted run select identically given the same seal history.

    Only a clean control can be accepted, so control slots go to candidates that still can be: a
    no-op Lane L seal (R16), one already accepted, or (BL-075, when ``recertified`` is given) one whose
    latest seal does not re-certify under current code is seeded first, and the remaining candidates
    are controls, except that at least MIN_PER_LANE per lane stay seeded (rotated by ``salt`` so a
    burned batch is not repeated). A stale seal is still audit material: it may carry a seed."""
    case_index: list[dict] = []
    manifest: list[dict] = []
    shape_cycle = list(BLIND_SHAPES)
    for lane, entries in sorted(by_lane.items()):
        shape_i = salt  # a burned batch's seeds must not repeat: rotate shapes and controls by salt
        unfit = {
            i for i, (repository, seal) in enumerate(entries)
            if is_noop(lane, seal) or _accepted_seal(accepted, repository, lane, seal)
            or (recertified is not None and (repository, lane, seal.revision) not in recertified)
        }
        fit = [i for i in range(len(entries)) if i not in unfit]
        need_seed = max(0, MIN_PER_LANE - len(unfit))
        if need_seed and fit:
            rot = salt % len(fit)
            fit = fit[rot:] + fit[:rot]
        controls = set(fit[need_seed:]) if (unfit or need_seed < len(fit)) else set()
        if not unfit and not accepted:
            controls = {i for i in range(len(entries)) if (i + salt) % CLEAN_EVERY == 0}
        for i, (repository, seal) in enumerate(entries):
            readme_text = seal.readme.decode("utf-8", errors="replace")
            case_id = hashlib.sha256(f"{repository}|{lane}|{seal.revision}".encode()).hexdigest()[:16]
            if i in controls:
                result = clean_control(f"{repository}@{lane}@{seal.revision}", readme_text)
            else:
                start = shape_i % len(shape_cycle)
                shape_i += 1
                result = None
                # BL-075: a shape with no injection site in this README falls through to the next shape
                # of the cycle -- only when none fits does the seal become a control (formerly the first
                # miss made it one, which handed control slots to seals that do not re-certify).
                for offset in range(len(shape_cycle)):
                    shape = shape_cycle[(start + offset) % len(shape_cycle)]
                    try:
                        result = seed_shape(f"{repository}@{lane}@{seal.revision}", readme_text, shape)
                        break
                    except SeedingError:
                        continue
                if result is None:
                    result = clean_control(f"{repository}@{lane}@{seal.revision}", readme_text)
            case_index.append({
                "case_id": case_id, "repository": repository, "lane": lane,
                "revision": seal.revision, "text": result.seeded_readme,
            })
            # BL-189: the digest of the ORIGINAL sealed bytes, committed before any mutation, inside the encrypted
            # manifest only (a digest beside a seeded copy would reveal which texts were mutated).
            manifest.append({"case_id": case_id, "original_sha256": candidate_sha256(seal.readme), **result.record.as_dict()})
    return case_index, manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--dry-run", action="store_true", help="select and plan, write nothing")
    parser.add_argument("--salt", type=int, default=0, help="rotate which candidates are controls and which shapes they get (use the workflow run id)")
    parser.add_argument("--gate", action="store_true",
                        help="print the round's next action as $GITHUB_OUTPUT lines (no key, nothing written)")
    parser.add_argument("--require-fresh", action="store_true",
                        help="with --gate: seed only when enough fresh candidates exist (the scheduled run)")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--refuse-if-open", action="store_true",
                        help="refuse to seed while an earlier seed batch is open (the hosted seed step)")
    args = parser.parse_args()

    if args.gate:
        heads = run_request.remote_heads(args.remote)

        def count() -> int:
            return len(fresh_candidates(select_candidates(remote=args.remote), judged_controls(args.remote)))

        try:
            outputs = gate(heads, run_id=args.run_id, require_fresh=args.require_fresh, count_fresh=count)
        except RecordsUnavailable as error:
            print(f"FAIL: the acceptance records could not be read (not the same as none): {error}", file=sys.stderr)
            return 1
        for key, value in outputs.items():
            print(f"{key}={value}")
        print(f"gate: {outputs['action']}: {outputs['reason']}", file=sys.stderr)
        return 1 if outputs["action"] == "blocked" else 0
    if args.out_dir is None:
        parser.error("--out-dir is required unless --gate")
    if args.refuse_if_open:
        still_open = run_request.open_seed_batches(run_request.remote_heads(args.remote))
        if still_open:
            print(f"FAIL: seed batch {still_open[0]} is still open; one open seed batch at a time", file=sys.stderr)
            return 1

    by_lane = select_candidates(remote=args.remote)
    for lane, entries in by_lane.items():
        if len(entries) < MIN_PER_LANE:
            print(f"WARNING: lane {lane} has only {len(entries)} sealed candidates "
                  f"(design minimum {MIN_PER_LANE})", file=sys.stderr)

    # BL-075: control slots only for seals that re-certify under current code (zero provider calls).
    # Fail closed: a control drawn from a stale seal can never be accepted, so an unreadable
    # re-certification is a visible failure, never a silent fall-back to the old population.
    try:
        recertified = recertified_seals(args.remote)
    except Exception as error:  # noqa: BLE001
        print(f"FAIL: zero-call re-certification of the latest seals failed: {type(error).__name__}: {error}",
              file=sys.stderr)
        return 1
    try:
        judged = judged_controls(args.remote)
    except RecordsUnavailable as error:
        print(f"FAIL: the acceptance records could not be read (not the same as none): {error}", file=sys.stderr)
        return 1
    case_index, manifest = build_seed_plan(by_lane, args.salt, judged, recertified)
    seeded_count = sum(1 for m in manifest if m["shape"] != CLEAN_SHAPE)
    stale = sum(1 for lane, entries in by_lane.items() for repository, seal in entries
                if (repository, lane, seal.revision) not in recertified)
    print(f"selected {sum(len(v) for v in by_lane.values())} candidates "
          f"({len(by_lane.get('L', []))} L, {len(by_lane.get('R', []))} R); "
          f"{seeded_count} seeded, {len(manifest) - seeded_count} clean controls; "
          f"{stale} latest seals not RECERTIFIED under current code (never a control slot, BL-075)")

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
