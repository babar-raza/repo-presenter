"""gateverify - the acceptance engine. Adapted 2026-10-21 from foss-mcp's
ops/gateverify.py (reference mechanics only). Simplified for v1: no container
runner, no pinned-venv-by-lockfile, no holdout directory wiring yet (the
mechanism is a TODO for when a second card exists -- see
ops/SUPERVISOR.md "What v1 defers"). The core safety property is kept
unsimplified: checks run twice clean (flake = fail), then the supervisor's
negative control MUST make them fail, or the card is rejected however green
it looked.
"""

from __future__ import annotations

import json
import re
import shlex
import time
from pathlib import Path

from gatectl import (
    CANONICAL_ENV,
    EVIDENCE,
    REPO,
    STATUS_JSONL,
    TASKCARDS,
    all_cards,
    check_scope,
    drop_worktree,
    fingerprint,
    git,
    load_card_at_rev,
    load_yaml,
    make_worktree,
    now_utc,
    parse_junit,
    read_jsonl,
    resolve_rev,
    run,
    sha256_bytes,
    sha256_file,
)

# 2026-11-04: real state model, replacing the collapsed PENDING/IN_PROGRESS pair that caused
# `tick` to report "ready cards: none" forever once any undispatched diagnostic `verify` run
# produced a non-accepting receipt (confirmed, not theoretical -- this happened to TC-002/004/
# 006/007/008/009/010/011/012 in this very session). AWAITING_OWNER_DECISION and
# AWAITING_PREREQUISITE are both "blocked," but for different reasons the supervisor must not
# treat interchangeably: a prerequisite is something an agent can go work on; an owner decision
# is not. VERIFICATION_FAILED and STALE_RECEIPT are both immediately re-attemptable -- a check
# failing because a feature does not exist yet must not permanently block the very task that
# would implement it.
GATE_STATUS_ORDER = [
    "BLOCKED_ENV", "AWAITING_PREREQUISITE", "AWAITING_OWNER_DECISION", "FAILED_INTERNAL",
    "IN_PROGRESS", "VERIFICATION_FAILED", "STALE_RECEIPT", "INCOHERENT_RECEIPT", "READY",
    "ACCEPTED", "SUPERSEDED",
]
READY_LIKE = {"READY", "VERIFICATION_FAILED", "STALE_RECEIPT", "INCOHERENT_RECEIPT"}


def receipt_is_coherent(receipt: dict, card: dict | None = None) -> list[str]:
    """2026-11-04: 'accepted: true because the JSON says so' is not authoritative on its own --
    confirmed real by the follow-up directive. Checks that a receipt claiming accepted=True is
    actually INTERNALLY CONSISTENT with do_verify's own acceptance invariant (two identical
    clean passes, scope ok, negative control applied and genuinely broke the checks), catching a
    hand-forged or corrupted receipt that a tool did not actually produce honestly. Schema
    validity is checked first (schemas/receipt.schema.json) -- a malformed receipt is incoherent
    by construction.

    2026-11-04 (supervisor directive correction): "two identical clean passes" previously meant
    only "both runs declared all_passed=True" -- a forged receipt could satisfy that with run 1
    and run 2 listing entirely DIFFERENT commands, neither matching what the card actually
    declares. Now also requires both runs to have checked the exact same ordered list of
    commands as each other, and -- when `card` is supplied -- the exact same list the card's own
    `checks[]` declares, so a receipt cannot claim to prove a check it never actually ran."""
    import gatectl

    problems: list[str] = []
    schema = gatectl.load_schema("receipt.schema.json")
    schema_problems = gatectl.schema_errors(schema, receipt)
    if schema_problems:
        return [f"schema violation: {p}" for p in schema_problems]  # nothing else is trustworthy

    if receipt.get("generated_by") != "gatecli":
        problems.append("generated_by is not 'gatecli'")

    if receipt.get("accepted") is True:
        runs = receipt.get("runs") or []
        if len(runs) != 2 or not all(r.get("all_passed") is True for r in runs):
            problems.append("accepted=True but runs do not show two identical clean passes")
        elif [c.get("command") for c in runs[0].get("checks", [])] != [
            c.get("command") for c in runs[1].get("checks", [])
        ]:
            problems.append(
                "accepted=True but run 1 and run 2 checked different commands -- not a real "
                "repeat of the same check set"
            )
        elif card is not None:
            declared = [c.get("command") for c in card.get("checks", []) or []]
            ran = [c.get("command") for c in runs[0].get("checks", [])]
            if ran != declared:
                problems.append(
                    "accepted=True but the runs' commands do not match the card's own "
                    "declared checks[] -- this receipt does not prove what the card claims"
                )
        scope = receipt.get("scope", {})
        if not scope.get("ok", False):
            problems.append("accepted=True but scope.ok is not True")
        if scope.get("evaluated") is not True:
            # 2026-11-04 (P0 follow-up directive section 5): `--no-scope` sets scope.ok=True
            # trivially (nothing was checked) and, until this line existed, that was
            # indistinguishable from a genuinely scope-evaluated pass. Every one of this
            # project's "accepted" cards was verified this way -- a real, confirmed integrity
            # gap, not theoretical. Normal release-gate acceptance now requires a real scope
            # evaluation; `--no-scope` stays available for diagnostic reruns but can never
            # again produce an ACCEPTED-eligible receipt.
            problems.append(
                "accepted=True but scope.evaluated is not True -- a --no-scope run never "
                "satisfies normal release-gate acceptance, however clean its checks were"
            )
        nc = receipt.get("negative_control", {})
        if nc.get("applied") is not True:
            problems.append("accepted=True but negative_control.applied is not True")
        if nc.get("patch_applied_failed") is not True:
            problems.append("accepted=True but negative_control.patch_applied_failed is not True "
                             "(the falsifier did not actually break the checks)")
        if not nc.get("tree_changed"):
            problems.append("accepted=True but negative_control.tree_changed is empty -- "
                             "no evidence anything was actually mutated")
        if not nc.get("exit_codes"):
            problems.append("accepted=True but negative_control.exit_codes is empty -- "
                             "no evidence the falsifier run was ever measured")
    return problems


def receipt_artifact_present(gate: str, card_id: str) -> bool:
    """A receipt without its own stdout.log sibling is missing the artifact that would let a
    human or a future audit actually inspect what ran -- treated as a real integrity gap, not
    cosmetic (2026-11-04)."""
    return (receipt_dir(gate, card_id) / "stdout.log").exists()


def receipt_dir(gate: str, card_id: str) -> Path:
    return EVIDENCE / "build" / gate / card_id


def load_receipt(gate: str, card_id: str):
    f = receipt_dir(gate, card_id) / "receipt.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def capabilities_missing(requires) -> list[str]:
    """v1 only knows about python (always present, this is python) and git."""
    import shutil
    missing = []
    for cap in requires or []:
        if cap == "git" and not shutil.which("git"):
            missing.append("git")
        # "python" is always present -- gatecli.py is running under it.
    return missing


def _blocked_env(card_id, gate, head, missing, outdir):
    receipt = {
        "schema_version": 1,
        "card": card_id,
        "gate": gate,
        "generated_by": "gatecli",
        "generated_at": now_utc(),
        "base_rev": head,
        "head_rev": head,
        "fingerprint": fingerprint(),
        "scope": {"ok": True, "changed_paths": [], "violations": [], "evaluated": False},
        "runs": [
            {"run": 1, "checks": [], "all_passed": False},
            {"run": 2, "checks": [], "all_passed": False},
        ],
        "negative_control": {"kind": "mutate", "patch": "n/a", "patch_sha256": "0" * 64,
                              "applied": False, "patch_applied_failed": False},
        "accepted": False,
        "reason": f"BLOCKED_ENV: missing capability: {', '.join(missing)}",
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def run_checks(card, wt: Path, log_lines):
    env = dict(CANONICAL_ENV)
    if not card.get("network", False):
        env["HTTP_PROXY"] = env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        env["GATECTL_OFFLINE"] = "1"

    results, all_passed = [], True
    for idx, chk in enumerate(card["checks"]):
        cmd = chk["command"]
        junit = None
        if chk.get("junitxml"):
            junit = wt / f".junit-{idx}.xml"
            cmd = f'{cmd} "--junitxml={junit}"'
        cwd = wt / chk.get("cwd", ".")
        t0 = time.time()
        rc, out, err = run(cmd, cwd=cwd, env=env, timeout=chk.get("timeout_seconds", 600))
        dur = round(time.time() - t0, 3)
        log_lines.append(f"$ {cmd}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n")
        entry = {
            "command": chk["command"],
            "exit_code": rc,
            "duration_s": dur,
            "stdout_sha256": sha256_bytes((out + err).encode("utf-8", "replace")),
        }
        if junit:
            entry.update(parse_junit(junit))
        results.append(entry)
        if rc != 0:
            all_passed = False
    return results, all_passed


def structural_gate(card, checks):
    """Exit code 0 is a near-worthless predicate alone -- demand real, unskipped
    tests where a check reports junit counts."""
    problems = []
    min_tests = card.get("min_tests")
    for c in checks:
        if "tests" not in c:
            continue
        if min_tests is not None and c["tests"] < min_tests:
            problems.append(f"{c['command']}: collected {c['tests']} tests, card requires >= {min_tests}")
        if c.get("skipped", 0) > 0:
            problems.append(f"{c['command']}: {c['skipped']} skipped test(s); skips are not evidence")
        if c.get("errors", 0) > 0:
            problems.append(f"{c['command']}: {c['errors']} collection error(s)")
    return problems


def do_verify(card_id: str, base: str, head: str, issue_rev: str | None = None,
              evaluate_scope: bool = True, persist: str = "always"):
    """Run a card's checks for real and write the receipt. Order matters: clean
    run twice (flake detection), structural gate, then the negative control,
    which MUST make the checks fail."""
    if persist not in ("always", "on_fail"):
        raise ValueError(f"persist must be 'always' or 'on_fail', got {persist!r}")
    base = resolve_rev(base)
    head = resolve_rev(head)
    issue_rev = resolve_rev(issue_rev or head)
    card, card_sha = load_card_at_rev(card_id, issue_rev)
    gate = card["gate"]
    outdir = receipt_dir(gate, card_id)
    outdir.mkdir(parents=True, exist_ok=True)

    absent = capabilities_missing(card.get("requires"))
    if absent:
        return _blocked_env(card_id, gate, head, absent, outdir)

    if evaluate_scope:
        ok_scope, changed, violations = check_scope(card, base, head)
    else:
        ok_scope, changed, violations = True, [], []

    log_lines: list[str] = []
    runs: list[dict] = []
    nc_spec = card["negative_control"]
    nc_kind = "patch" if "patch" in nc_spec else "mutate"
    negctl = {
        "kind": nc_kind,
        "patch": nc_spec.get("patch") or nc_spec.get("mutate"),
        "patch_sha256": "0" * 64,
        "applied": False,
        "patch_applied_failed": False,
        "exit_codes": [],
    }
    structural: list[str] = []
    clean_passed = False

    wt = make_worktree(head)
    try:
        for i in (1, 2):
            log_lines.append(f"\n===== CLEAN RUN {i} =====\n")
            checks, passed = run_checks(card, wt, log_lines)
            runs.append({"run": i, "checks": checks, "all_passed": passed})
        structural = structural_gate(card, runs[0]["checks"])

        codes1 = [c["exit_code"] for c in runs[0]["checks"]]
        codes2 = [c["exit_code"] for c in runs[1]["checks"]]
        flaky = codes1 != codes2
        clean_passed = runs[0]["all_passed"] and runs[1]["all_passed"] and not flaky

        if clean_passed:
            if nc_kind == "patch":
                patch = REPO / nc_spec["patch"]
                if patch.exists():
                    negctl["patch_sha256"] = sha256_file(patch)
                    rc, _, err = run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=wt)
                    applied, why = rc == 0, err
                else:
                    applied, why = False, f"patch missing: {patch}"
            else:
                cmd = nc_spec["mutate"]
                negctl["patch_sha256"] = sha256_bytes(cmd.encode("utf-8"))
                rc, out, err = run(cmd, cwd=wt, timeout=120)
                applied, why = rc == 0, (err or out)

            if applied:
                _, dirty, _ = run(["git", "status", "--porcelain"], cwd=wt)
                if not dirty.strip():
                    applied = False
                    why = ("command exited 0 but left the tree byte-identical - it mutated "
                           "nothing. This is NOT a passing falsifier.")
                else:
                    negctl["tree_changed"] = [ln.strip() for ln in dirty.strip().splitlines()]

            if applied:
                negctl["applied"] = True
                log_lines.append("\n===== NEGATIVE CONTROL (checks MUST now fail) =====\n")
                log_lines.append("mutated: " + ", ".join(negctl.get("tree_changed", [])) + "\n")
                nchecks, npassed = run_checks(card, wt, log_lines)
                negctl["exit_codes"] = [c["exit_code"] for c in nchecks]
                negctl["patch_applied_failed"] = not npassed
            else:
                log_lines.append(f"\n!! falsifier did not apply ({nc_kind}): {why}\n")
        else:
            log_lines.append("\n!! clean runs failed; falsifier skipped (it would prove nothing)\n")
    finally:
        drop_worktree(wt)

    log_text = "".join(log_lines)

    reasons = []
    if not ok_scope:
        reasons.append("scope violation: " + "; ".join(violations[:5]))
    if not clean_passed:
        if runs and runs[0]["all_passed"] != runs[1]["all_passed"]:
            reasons.append("FLAKY: the two clean runs disagreed")
        elif runs and not runs[0]["all_passed"]:
            failed = [c["command"] for c in runs[0]["checks"] if c["exit_code"] != 0]
            reasons.append("checks failed: " + "; ".join(failed))
        else:
            reasons.append("clean checks did not pass identically twice")
    if structural:
        reasons.append("structural gate: " + "; ".join(structural))
    if not negctl["applied"]:
        reasons.append("negative-control patch did not apply")
    elif not negctl["patch_applied_failed"]:
        reasons.append("VACUOUS CHECKS: the suite still passed with the falsifier applied")

    receipt = {
        "schema_version": 1,
        "card": card_id,
        "gate": gate,
        "generated_by": "gatecli",
        "generated_at": now_utc(),
        "base_rev": base,
        "head_rev": head,
        "card_sha256": card_sha,
        "checker_fileset_sha256": checker_fileset_sha256(card, head, FILESET_SCHEME_CURRENT),
        "checker_fileset_scheme": FILESET_SCHEME_CURRENT,
        "fingerprint": fingerprint(),
        "scope": {"ok": ok_scope, "changed_paths": changed, "violations": violations, "evaluated": evaluate_scope},
        "runs": runs,
        "negative_control": negctl,
        "accepted": len(reasons) == 0,
        "reason": "; ".join(reasons) if reasons else "all gates passed",
    }
    stored = load_receipt(gate, card_id)
    stored_passed = bool(stored and stored.get("accepted"))
    if persist == "always" or not receipt["accepted"] or not stored_passed:
        (outdir / "stdout.log").write_text(log_text, encoding="utf-8")
        (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


# --------------------------------------------------------------------------
# dependency-graph integrity (2026-11-04: real checks, not per-card linting --
# cardlint.py only ever validated one card's own shape in isolation)
# --------------------------------------------------------------------------
def find_duplicate_card_ids() -> list[str]:
    """all_cards() keys its dict by each card's own declared `id`, so two
    files declaring the same id silently overwrite one another in that dict
    and the collision is invisible to every caller of all_cards(). This
    walks the files directly instead."""
    from collections import defaultdict

    by_id: dict[str, list[str]] = defaultdict(list)
    if TASKCARDS.exists():
        for p in sorted(TASKCARDS.glob("TC-*.yaml")):
            c = load_yaml(p)
            if isinstance(c, dict) and "id" in c:
                by_id[c["id"]].append(str(p))
    return [
        f"duplicate card id {cid!r} declared in: {', '.join(paths)}"
        for cid, paths in sorted(by_id.items())
        if len(paths) > 1
    ]


def find_dependency_graph_problems(cards: dict) -> list[str]:
    """Self-dependency, missing dependency IDs, and real cycle detection
    (DFS over depends_on edges), checked once over the whole graph."""
    problems: list[str] = []
    for cid, card in sorted(cards.items()):
        deps = card.get("depends_on", [])
        if cid in deps:
            problems.append(f"{cid}: depends_on includes itself")
        for d in deps:
            if d not in cards:
                problems.append(f"{cid}: depends_on references unknown card {d!r}")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in cards}
    seen_cycles: set[tuple] = set()

    def visit(cid: str, stack: list[str]) -> None:
        color[cid] = GRAY
        stack.append(cid)
        for d in cards[cid].get("depends_on", []):
            if d not in cards:
                continue  # already reported above; do not also report a confusing cycle
            if color.get(d) == GRAY:
                cyc = tuple(stack[stack.index(d):] + [d])
                if cyc not in seen_cycles:
                    seen_cycles.add(cyc)
                    problems.append("dependency cycle: " + " -> ".join(cyc))
            elif color.get(d) == WHITE:
                visit(d, stack)
        stack.pop()
        color[cid] = BLACK

    for cid in sorted(cards):
        if color[cid] == WHITE:
            visit(cid, [])
    return problems


# --------------------------------------------------------------------------
# derived state
# --------------------------------------------------------------------------
def gate_status(statuses: list[str], accepted: bool, exit_verdict) -> str:
    if accepted:
        return "ACCEPTED"
    if not statuses:
        return "READY"
    if any(s == "BLOCKED_ENV" for s in statuses):
        return "BLOCKED_ENV"
    if any(s == "FAILED_INTERNAL" for s in statuses):
        return "FAILED_INTERNAL"
    if all(s in ("ACCEPTED", "SUPERSEDED") for s in statuses):
        return "EXIT_FAILED" if exit_verdict == "NOT_MET" else "EXIT_PENDING"
    if any(s == "IN_PROGRESS" for s in statuses):
        return "IN_PROGRESS"
    return "READY"


_REFERENCED_FILE_RE = re.compile(r"^[\w./-]+\.(?:py|json|ya?ml|md)$")


def referenced_files(card: dict) -> list[str]:
    """Every checker script or required-evidence document this card's own `checks[].command`
    strings name -- e.g. `ops/checks/parity_benchmark_pilot_complete.py`,
    `docs/PARITY_BENCHMARK_PILOT.md`. A card's own taskcard YAML is excluded: that is already
    covered by `card_sha256`, and a card must never be able to extend its own currency check to
    cover itself twice."""
    paths: set[str] = set()
    for c in card.get("checks", []) or []:
        for raw in str(c.get("command", "")).split():
            tok = raw.strip("'\"")
            if _REFERENCED_FILE_RE.match(tok) and not tok.startswith("project/taskcards/"):
                paths.add(tok)
    return sorted(paths)


FILESET_SCHEME_CURRENT = "v3"

# The decision log owner_decision_record.py resolves every `ref=<anchor>` against (it hard-codes
# this relative path, so the fileset hash must too).
DECISION_LOG_PATH = "docs/DECISION_LOG.md"


def _marker_checks(card: dict) -> dict[str, list[str]]:
    """``{file: [markers]}`` for every ``marker_check.py <file> <marker>...`` command in the card.
    Such a check consumes ONLY whether each marker substring occurs in the file, nothing else."""
    found: dict[str, list[str]] = {}
    for c in card.get("checks", []) or []:
        try:
            tokens = shlex.split(str(c.get("command", "")))
        except ValueError:
            continue
        for i, tok in enumerate(tokens):
            if tok.endswith("marker_check.py") and len(tokens) > i + 2:
                found.setdefault(tokens[i + 1], []).extend(tokens[i + 2 :])
    return found


def _consumed_digest(path: str, markers: list[str], rev: str) -> str:
    """Digest of exactly what a marker check consumes: each marker's occurrence lines (sorted,
    with counts). Unrelated edits to the file do not change it; removing, altering or duplicating
    the marker line does."""
    rc, out, _ = git("show", f"{rev}:{path}")
    if rc != 0:
        return "MISSING"
    lines = out.splitlines()
    parts = [f"{m}\t" + "\n".join(sorted(ln for ln in lines if m in ln)) for m in sorted(set(markers))]
    return sha256_bytes("\x00".join(parts).encode("utf-8"))


def _record_pattern(prefix: str) -> re.Pattern:
    """Exactly the record regex ops/checks/owner_decision_record.py matches."""
    return re.compile(re.escape(prefix) + r"\s+(\d{4}-\d{2}-\d{2})\s+ref=(\S+)")


def _consumption_v3(card: dict) -> tuple[dict[str, list[tuple[str, str]]], set[str]]:
    """Scheme v3's view of what each check reads.

    Returns ``(needles, other_use)``: ``needles[path]`` lists ``(kind, value)`` pairs for every
    file read only line-wise -- ``("marker", m)`` from ``marker_check.py <file> <m>...``,
    ``("prefix", p)`` for the target of ``owner_decision_record.py <file> <p>``, and
    ``("anchor_of", "<file>\\x00<p>")`` on DECISION_LOG_PATH for that record's ``ref=`` anchor
    (resolved at the hashed revision, see _needle_digest). ``other_use`` holds every token any
    command uses outside those invocations; a path in it is hashed whole, never line-wise."""
    needles: dict[str, list[tuple[str, str]]] = {}
    other_use: set[str] = set()
    for c in card.get("checks", []) or []:
        cmd = str(c.get("command", ""))
        try:
            tokens = shlex.split(cmd)
        except ValueError:
            other_use.update(t.strip("\"'") for t in cmd.split())
            continue
        consumed = [False] * len(tokens)
        for i, tok in enumerate(tokens):
            if tok.endswith("marker_check.py") and len(tokens) > i + 2:
                needles.setdefault(tokens[i + 1], []).extend(("marker", m) for m in tokens[i + 2 :])
                consumed[i:] = [True] * (len(tokens) - i)
                break
            if tok.endswith("owner_decision_record.py") and len(tokens) > i + 2:
                target, prefix = tokens[i + 1], tokens[i + 2]
                needles.setdefault(target, []).append(("prefix", prefix))
                needles.setdefault(DECISION_LOG_PATH, []).append(("anchor_of", f"{target}\x00{prefix}"))
                consumed[i + 1] = consumed[i + 2] = True
        other_use.update(t for t, used in zip(tokens, consumed) if not used)
    return needles, other_use


def _needle_digest(path: str, needles: list[tuple[str, str]], rev: str) -> str:
    """Digest of exactly the lines of ``path`` at ``rev`` that the v3 needles consume (sorted,
    with counts, so a duplicated line changes it). A ``prefix`` needle also hashes the exact
    record text the checker's regex matches first (which can span a line break). An
    ``anchor_of`` needle resolves the record's ``ref=`` anchor from its target AT ``rev`` and
    hashes every line containing it; a missing record hashes as ``NO_RECORD``."""
    rc, out, _ = git("show", f"{rev}:{path}")
    if rc != 0:
        return "MISSING"
    lines = out.splitlines()
    parts = []
    for kind, value in sorted(set(needles)):
        if kind == "anchor_of":
            target, prefix = value.split("\x00", 1)
            trc, tout, _ = git("show", f"{rev}:{target}")
            m = _record_pattern(prefix).search(tout) if trc == 0 else None
            if not m:
                parts.append(f"{kind}:{value}\tNO_RECORD")
                continue
            needle, head = m.group(2), f"{kind}:{value}:{m.group(2)}"
        elif kind == "prefix":
            m = _record_pattern(value).search(out)
            needle, head = value, f"{kind}:{value}:{m.group(0) if m else 'NO_RECORD'}"
        else:
            needle, head = value, f"{kind}:{value}"
        parts.append(head + "\t" + "\n".join(sorted(ln for ln in lines if needle in ln)))
    return sha256_bytes("\x00".join(parts).encode("utf-8"))


def checker_fileset_sha256(card: dict, rev: str, scheme: str = FILESET_SCHEME_CURRENT) -> str:
    """2026-11-04 (supervisor directive correction): currentness was tied only to the taskcard
    YAML's own hash, so the EXECUTABLE acceptance checker it calls (e.g. a script under
    ops/checks/) or a required evidence document could change underneath an accepted receipt
    without the receipt ever going stale. This hashes every file `referenced_files()` finds, AT
    `rev`, combined into one digest; a file absent at `rev` hashes as literal 'MISSING' so its
    removal is also detected as a change, not silently ignored.

    Scheme v2 (2026-11-04): a file that the card consumes ONLY through ``marker_check.py`` (an
    append-only decision log, AGENTS.md, a prose contract) is hashed as the marker lines it
    consumes, not whole: appending an unrelated decision must not invalidate an acceptance that
    never read it, while changing the consumed marker still does. v1 (whole file) is kept so
    receipts written before v2 are compared the way they were made.

    Scheme v3 (2026-11-05): the same treatment for ``owner_decision_record.py <file> <PREFIX>``.
    Such a check consumes the PREFIX lines of its target plus the DECISION_LOG_PATH lines that
    contain the record's ``ref=`` anchor (resolved at ``rev``), so DECISION_LOG_PATH is part of
    the fileset even when no command names it. Before v3 a record kept in the decision log itself
    (TC-004) went stale on every unrelated new entry. v1/v2 receipts are still compared under
    their own scheme."""
    if scheme == "v3":
        needles, other_use = _consumption_v3(card)
        paths = sorted(set(referenced_files(card)) | set(needles))
        parts = []
        for path in paths:
            if path in needles and path not in other_use:
                parts.append(f"{path}:lines:{_needle_digest(path, needles[path], rev)}")
                continue
            rc, out, _ = git("show", f"{rev}:{path}")
            parts.append(f"{path}:{sha256_bytes(out.encode('utf-8')) if rc == 0 else 'MISSING'}")
        return sha256_bytes("\n".join(parts).encode("utf-8"))
    markers = _marker_checks(card) if scheme == "v2" else {}
    other_use = set()
    if markers:
        for c in card.get("checks", []) or []:
            cmd = str(c.get("command", ""))
            if "marker_check.py" in cmd:
                continue
            other_use.update(t.strip("\"'") for t in cmd.split())
    parts = []
    for path in referenced_files(card):
        if path in markers and path not in other_use:
            parts.append(f"{path}:marker:{_consumed_digest(path, markers[path], rev)}")
            continue
        rc, out, _ = git("show", f"{rev}:{path}")
        parts.append(f"{path}:{sha256_bytes(out.encode('utf-8')) if rc == 0 else 'MISSING'}")
    return sha256_bytes("\n".join(parts).encode("utf-8"))


def card_is_stale(cid: str, receipt: dict) -> bool:
    """A receipt's accepted=True is NECESSARY, never SUFFICIENT: it must also
    still describe the card as currently committed at HEAD. If the card file
    was edited (e.g. a check weakened) after the receipt was generated, the
    receipt's card_sha256 no longer matches and the receipt must not be
    trusted as current. Mirrors load_card_at_rev's own hashing exactly
    (git show -> .strip() -> utf-8 -> sha256) so the comparison is apples to
    apples with what do_verify itself computed. Also stale if any file
    referenced_files() names has changed since the receipt was generated, or if the receipt
    predates this check existing at all (checker_fileset_sha256 absent) -- new, stronger
    acceptance must be earned, a historical receipt does not grandfather past a real
    strengthening of what currentness means."""
    try:
        card, current_sha = load_card_at_rev(cid, "HEAD")
    except SystemExit:
        return True  # HEAD does not contain this card yet -- cannot be current
    if current_sha != receipt.get("card_sha256"):
        return True
    if "checker_fileset_sha256" not in receipt:
        return True
    scheme = receipt.get("checker_fileset_scheme", "v1")
    return checker_fileset_sha256(card, "HEAD", scheme) != receipt.get("checker_fileset_sha256")


def compute_rows(cards: dict, raw: dict, dispatched: set, attempts: dict, latest_kind: dict):
    """Pure function, no IO: the actual dependency-enforcement/status logic,
    extracted 2026-11-04 so it can be unit-tested directly against synthetic
    cards/receipts without a live git worktree. `raw[cid]` is
    {"receipt": dict|None, "attempt": int, "stale": bool}.

    A positive receipt is necessary, never sufficient, for ACCEPTED: it must
    also be non-stale and every depends_on edge must itself resolve to an
    effectively-accepted card -- a fixed point over the whole graph, not one
    card's own receipt read in isolation. A card that was merely
    verify-checked for diagnostic purposes (never actually `instruct --kind
    dispatch`ed) does not get stuck in IN_PROGRESS forever: only a real
    dispatch does that -- VERIFICATION_FAILED/STALE_RECEIPT stay
    immediately re-attemptable (see READY_LIKE)."""
    effectively_accepted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for cid in sorted(cards):
            if cid in effectively_accepted:
                continue
            if latest_kind.get(cid) == "supersede":
                continue  # a superseded card never counts as accepted for a downstream
                          # dependency, even if its own historical receipt still says so --
                          # "previously accepted downstream cards lose release eligibility if a
                          # required upstream gate is genuinely invalidated" (2026-11-04 directive)
            info = raw[cid]
            r = info["receipt"]
            if not (r and r.get("accepted")) or info["stale"] or info.get("incoherent"):
                continue
            deps = cards[cid].get("depends_on", [])
            if all(d in effectively_accepted for d in deps):
                effectively_accepted.add(cid)
                changed = True

    rows = []
    for cid in sorted(cards):
        c = cards[cid]
        info = raw[cid]
        r, stale, attempt = info["receipt"], info["stale"], info.get("attempt", attempts.get(cid, 0))
        incoherent = info.get("incoherent", False)
        incoherent_reasons = info.get("incoherent_reasons", [])
        deps = c.get("depends_on", [])
        deps_met = all(d in effectively_accepted for d in deps)
        row = {"id": cid, "gate": c["gate"], "status": "AWAITING_PREREQUISITE",
               "attempt": attempt, "blocker": None}

        if latest_kind.get(cid) == "supersede":
            row["status"] = "SUPERSEDED"
        elif cid in effectively_accepted:
            row["status"] = "ACCEPTED"
            row["commit"] = r["head_rev"]
            row["receipt"] = f"{r['gate']}/{cid}/receipt.json"
        elif not deps_met:
            unmet = [d for d in deps if d not in effectively_accepted]
            row["status"] = "AWAITING_PREREQUISITE"
            summary = f"depends on {', '.join(unmet)}, not yet accepted"
            if r and r.get("accepted") and stale:
                summary += " (receipt also stale: card changed since verification)"
            if r and r.get("accepted") and incoherent:
                summary += f" (receipt also incoherent: {'; '.join(incoherent_reasons)})"
            row["blocker"] = {"class": "AWAITING_PREREQUISITE", "summary": summary}
        elif r and r.get("accepted") and incoherent:
            row["status"] = "INCOHERENT_RECEIPT"
            row["blocker"] = {
                "class": "INCOHERENT_RECEIPT",
                "summary": "receipt claims accepted=True but fails internal consistency checks "
                           "(forged, corrupted, or missing its own artifact): " + "; ".join(incoherent_reasons),
            }
        elif r and r.get("accepted") and stale:
            row["status"] = "STALE_RECEIPT"
            row["blocker"] = {
                "class": "STALE_RECEIPT",
                "summary": "card definition changed since this receipt was generated -- re-verify",
            }
        elif cid in dispatched:
            if r and not r.get("accepted") and attempt >= 3:
                row["status"] = "FAILED_INTERNAL"
                row["blocker"] = {
                    "class": "FAILED_INTERNAL",
                    "summary": r.get("reason", "verification failed"),
                    "resume_predicate": f"a new commit for {cid} passes `gatecli.py verify {cid}`",
                    "recorded_at": r.get("generated_at", now_utc()),
                }
            else:
                row["status"] = "IN_PROGRESS"
        elif r and not r.get("accepted"):
            if c.get("requires_owner_decision"):
                row["status"] = "AWAITING_OWNER_DECISION"
            else:
                row["status"] = "VERIFICATION_FAILED"
            row["blocker"] = {"class": row["status"], "summary": r.get("reason", "verification failed")}
        else:
            row["status"] = "READY"
        rows.append(row)

    return rows, effectively_accepted


def rebuild_state(cards_order: list[str] | None = None):
    """project/state.yaml's CARD-DRIVEN portion is a FUNCTION of primary
    evidence (cards on disk + receipts + instructions log), never a narration.
    This only covers the `cards`/`current_gate`/`accepted_gates`/
    `execution_limits` fields -- the bootstrap-era fields (`authority`,
    `progress`, `active_work_item`, pre-card `current_gate.id` like
    P0_BOOTSTRAP) are supervisor-authored directly until the first taskcard
    exists, exactly as ops/SUPERVISOR.md documents. This is the IO-performing
    wrapper; compute_rows() above is the pure logic, unit-tested directly."""
    cards = all_cards()
    instructions = read_jsonl(Path(STATUS_JSONL).parent / "instructions.jsonl")

    attempts: dict[str, int] = {}
    dispatched: set[str] = set()
    latest_kind: dict[str, str] = {}
    for ins in instructions:
        t = ins.get("target_card")
        if t and t != "ALL":
            attempts[t] = max(attempts.get(t, 0), int(ins.get("attempt", 0)))
            if ins.get("kind") in ("dispatch", "rework"):
                dispatched.add(t)
            latest_kind[t] = ins.get("kind")

    raw: dict[str, dict] = {}
    for cid in sorted(cards):
        c = cards[cid]
        r = load_receipt(c["gate"], cid)
        stale = bool(r and r.get("accepted") and card_is_stale(cid, r))
        incoherent_reasons: list[str] = []
        if r and r.get("accepted"):
            incoherent_reasons = receipt_is_coherent(r, card=c)
            if not receipt_artifact_present(c["gate"], cid):
                incoherent_reasons.append("missing stdout.log artifact alongside receipt.json")
        raw[cid] = {
            "receipt": r, "attempt": attempts.get(cid, 0), "stale": stale,
            "incoherent": bool(incoherent_reasons), "incoherent_reasons": incoherent_reasons,
        }

    return compute_rows(cards, raw, dispatched, attempts, latest_kind)


def ready_cards_from_rows(rows):
    return [r["id"] for r in rows if r["status"] in READY_LIKE]


def next_card_from_rows(rows):
    ready = sorted(ready_cards_from_rows(rows))
    return ready[0] if ready else None
