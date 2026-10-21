#!/usr/bin/env python
"""gatectl - deterministic primitives for repo-presenter's supervised execution loop.

Adapted 2026-10-21 from foss-mcp's ops/gatectl.py (reference mechanics only, not
a product authority -- see docs/MISSION_AUTHORITY.md). Deliberately simplified
for v1 (see migration/reuse-manifest.yaml "foss-mcp ops/ supervisor mechanics"
entry and ops/SUPERVISOR.md "What v1 defers"):

  * No pinned-venv-by-lockfile-hash (foss-mcp's ensure_shared_venv) -- this repo
    has no requirements.lock yet. Verification runs under whatever Python
    invoked gatecli.py; the fingerprint records that interpreter's version so a
    later mismatch is at least visible, not hidden.
  * No container-runner fallback -- host-only for v1.
  * Git-worktree isolation for verification IS kept (not simplified away): only
    committed content may participate in a verdict is a core safety property,
    not an incidental one, and `git worktree add` costs little.

Every verdict in this system is one of this program's exit codes. No verdict is
ever a sentence, and no model ever hand-writes project/state.yaml, a receipt, or
a timestamp.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def _find_repo_root() -> Path:
    """Walk up from this file to the git repo root. Never hardcoded (mission
    §4: foss-mcp's hardcoded repo path must not be copied unexamined)."""
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"no .git found walking up from {here}")


REPO = _find_repo_root()
OPS = REPO / "ops"
TASKCARDS = REPO / "project" / "taskcards"
SCHEMAS = REPO / "schemas"
EVIDENCE = REPO / "evidence"
STATE_FILE = REPO / "project" / "state.yaml"
STATUS_JSONL = OPS / "status.jsonl"
INSTRUCTIONS_JSONL = OPS / "instructions.jsonl"
WORKTREE_ROOT = REPO / ".gatectl-worktrees"

CARD_RE = re.compile(r"^TC-\d{3}[a-z]?$")

# Paths no taskcard may EVER declare in write_paths, regardless of what the
# card says. Enforced at scope-check time. Supervisor-owned (mission AGENTS.md
# authority table + this repo's own layout as of 2026-10-21).
GLOBAL_DENY = [
    "plans/**",
    "project/**",
    "ops/**",
    "schemas/**",
    "docs/**",
    "migration/**",
    "evidence/**",
    ".github/**",
    ".claude/**",
    ".gitattributes",
    ".gitignore",
    "AGENTS.md",
    "README.md",
]

CANONICAL_ENV = {
    "PYTHONHASHSEED": "0",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONIOENCODING": "utf-8",
    "TZ": "UTC",
}

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def now_utc() -> str:
    """The ONLY timestamp source in this system. No model types a timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes()) if p.exists() else "0" * 64


_GIT_REPO_DISCOVERY_ENV_VARS = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
    "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def run(cmd, cwd=None, env=None, timeout=None, text=True):
    """Run a command, capturing both streams. Never raises on non-zero."""
    e = {k: v for k, v in os.environ.items() if k not in _GIT_REPO_DISCOVERY_ENV_VARS}
    if env:
        e.update(env)
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd or REPO),
            env=e,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
            encoding="utf-8" if text else None,
            errors="replace" if text else None,
            shell=isinstance(cmd, str),
            start_new_session=os.name != "nt",
        )
    except Exception as exc:  # noqa: BLE001 - a launch failure is a real verdict
        return 125, "", f"LAUNCH-FAILED: {exc}"
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, (out or ""), (err or "")
    except subprocess.TimeoutExpired:
        kill_process_tree(p)
        try:
            p.communicate(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        return 124, "", f"TIMEOUT after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        kill_process_tree(p)
        return 125, "", f"LAUNCH-FAILED: {exc}"


def kill_process_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=False,
            )
        else:
            import signal
            os.killpg(p.pid, signal.SIGKILL)
    except Exception:  # noqa: BLE001
        pass
    try:
        p.kill()
    except Exception:  # noqa: BLE001
        pass


def git(*args, cwd=None):
    rc, out, err = run(["git", *args], cwd=cwd)
    return rc, out.strip(), err.strip()


def git_porcelain_status(*extra_args, cwd=None):
    """`git status --porcelain`, output NOT globally .strip()'d.

    git()'s strip() is safe for one-line output, but porcelain status is a
    fixed-column format (`XY path`) and strip() on the whole multi-line blob
    eats only the first line's leading space -- desyncing column 0 for that
    one line only (found 2026-10-21 self-testing commit-guard: " M ops/x.py"
    became "M ops/x.py" after a whole-string strip, so line[3:] sliced one
    character too many and reported "ps/x.py"). Only rstrip trailing
    newline/whitespace here; never strip leading content.
    """
    rc, out, err = run(["git", "status", "--porcelain", *extra_args], cwd=cwd)
    return rc, out.rstrip("\n"), err.strip()


def die(msg: str, code: int = EXIT_FAIL):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# yaml / json loading
# --------------------------------------------------------------------------
def _yaml():
    import yaml

    class TextTimestampLoader(yaml.SafeLoader):
        pass

    TextTimestampLoader.yaml_implicit_resolvers = {
        k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    return yaml, TextTimestampLoader


def load_yaml_text(text: str):
    yaml, loader = _yaml()
    return yaml.load(text, Loader=loader)


def load_yaml(p: Path):
    return load_yaml_text(p.read_text(encoding="utf-8"))


def dump_yaml(obj) -> str:
    import yaml
    return yaml.safe_dump(obj, sort_keys=False, default_flow_style=False, allow_unicode=True)


def load_schema(name: str):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def schema_errors(schema, instance):
    import jsonschema
    v = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(str(x) for x in e.path)}: {e.message}" for e in v.iter_errors(instance)]


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def append_jsonl(p: Path, obj: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, sort_keys=False) + "\n")


# --------------------------------------------------------------------------
# path matching (segment-wise, not prefix matching)
# --------------------------------------------------------------------------
def norm_path(p: str) -> str:
    return p.replace("\\", "/").strip().strip("/")


def path_matches(path: str, pattern: str) -> bool:
    p = norm_path(path).casefold()
    q = norm_path(pattern).casefold()
    if q.endswith("/**"):
        base = q[:-3]
        return p == base or p.startswith(base + "/")
    if q.endswith("/*"):
        base = q[:-2]
        # p == base covers git's aggregated "dir/" status line for an entirely
        # untracked directory -- git reports the directory itself, not each
        # file inside, so a single-level pattern must still recognize it.
        return p == base or (p.startswith(base + "/") and "/" not in p[len(base) + 1:])
    return p == q


def matches_any(path: str, patterns) -> bool:
    return any(path_matches(path, pat) for pat in patterns)


ILLEGAL_NAME_RE = re.compile(r"(^|/)(con|aux|nul|prn|com[1-9]|lpt[1-9])(\.|/|$)", re.IGNORECASE)


def illegal_path_reasons(p: str):
    out = []
    n = norm_path(p)
    if ":" in n:
        out.append("contains ':' (NTFS alternate data streams are invisible to git diff)")
    if ILLEGAL_NAME_RE.search(n):
        out.append("uses a Windows reserved device name")
    for seg in n.split("/"):
        if seg != seg.strip() or seg.endswith("."):
            out.append(f"segment {seg!r} has a trailing space or dot")
    return out


# --------------------------------------------------------------------------
# taskcards
# --------------------------------------------------------------------------
def card_path(card_id: str) -> Path:
    return TASKCARDS / f"{card_id}.yaml"


def load_card_from_worktree(card_id: str):
    p = card_path(card_id)
    if not p.exists():
        die(f"no such card: {p}")
    return load_yaml(p)


def load_card_at_rev(card_id: str, rev: str):
    """Read the card as it existed at the revision it was ISSUED at. A worker
    that edits its own card must not be able to redefine its own permissions."""
    rc, out, err = git("show", f"{rev}:project/taskcards/{card_id}.yaml")
    if rc != 0:
        die(f"cannot read {card_id} at {rev}: {err}")
    return load_yaml_text(out), sha256_bytes(out.encode("utf-8"))


def all_cards():
    cards = {}
    if not TASKCARDS.exists():
        return cards
    for p in sorted(TASKCARDS.glob("TC-*.yaml")):
        c = load_yaml(p)
        if isinstance(c, dict) and "id" in c:
            cards[c["id"]] = c
    return cards


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------
def resolve_rev(rev: str) -> str:
    rc, out, err = git("rev-parse", "--verify", f"{rev}^{{commit}}")
    if rc != 0 or len(out) != 40:
        die(f"cannot resolve revision {rev!r}: {err or out}")
    return out


def commits_recorded_for(card_id: str) -> set:
    latest: dict[int, str] = {}
    for d in read_jsonl(STATUS_JSONL):
        if d.get("card") == card_id and isinstance(d.get("commit"), str):
            try:
                latest[int(d.get("attempt", 1))] = d["commit"]
            except (TypeError, ValueError):
                continue
    return set(latest.values())


def commit_subject(rev: str) -> str:
    return git("log", "-1", "--format=%s", rev)[1]


def commit_body(rev: str) -> str:
    return git("log", "-1", "--format=%b", rev)[1]


def changed_paths(base: str, head: str, card_id: str | None = None, gate: str | None = None):
    rc, out, err = git("rev-list", "--reverse", f"{base}..{head}")
    if rc != 0:
        die(f"rev-list failed: {err}")
    revs = [r for r in out.splitlines() if r.strip()]

    unattributed = []
    if card_id:
        tag = f"({gate}/{card_id})" if gate else f"/{card_id})"
        recorded = commits_recorded_for(card_id)
        mine, others = [], []
        for r in revs:
            if tag in commit_subject(r) or r in recorded:
                mine.append(r)
            elif re.search(r"Co-Authored-By:\s*Claude\s+\S+", commit_body(r)):
                others.append(r)
            else:
                unattributed.append(r)
        revs = mine + unattributed

    touched, per_commit = set(), {}
    for r in revs:
        rc, out, _ = git("diff-tree", "--no-commit-id", "--no-renames", "-r", "--name-status", r)
        if rc != 0:
            continue
        paths = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                for pth in parts[1:]:
                    if pth.strip():
                        paths.append(norm_path(pth))
        per_commit[r] = paths
        touched.update(paths)
    return revs, sorted(touched), per_commit, unattributed


def risky_modes(base: str, head: str):
    out_flags = []
    rc, out, _ = git("diff", "--no-renames", "--raw", f"{base}..{head}")
    for line in out.splitlines():
        if not line.startswith(":"):
            continue
        fields = line[1:].split()
        if len(fields) >= 2:
            newmode = fields[1]
            if newmode in ("120000", "160000"):
                kind = "symlink" if newmode == "120000" else "submodule/gitlink"
                out_flags.append(f"{kind} introduced: {line.strip()}")
    return out_flags


def check_scope(card, base: str, head: str):
    """Returns (ok, changed, violations)."""
    write_paths = card.get("write_paths", [])
    revs, changed, _, unattributed = changed_paths(base, head, card.get("id"), card.get("gate"))
    violations = []

    if not revs:
        violations.append(
            f"no commit in {base[:12]}..{head[:12]} is tagged for this card - the commit "
            f"subject must end with ({card.get('gate')}/{card.get('id')})"
        )
    for r in unattributed:
        violations.append(
            f"commit {r[:12]} claims neither this card nor the supervisor: {commit_subject(r)[:70]!r}"
        )
    for p in changed:
        if matches_any(p, GLOBAL_DENY):
            violations.append(f"{p}: touches a globally denied path")
        elif not matches_any(p, write_paths):
            violations.append(f"{p}: outside the card's declared write_paths")
    violations.extend(risky_modes(base, head))

    rc, _, _ = git("merge-base", "--is-ancestor", base, head)
    if rc != 0:
        violations.append(f"{head[:12]} does not descend from base {base[:12]} (history was rewritten)")

    return (len(violations) == 0), changed, violations


# --------------------------------------------------------------------------
# environment fingerprint (simplified for v1: no pinned venv)
# --------------------------------------------------------------------------
def fingerprint():
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


# --------------------------------------------------------------------------
# worktree isolation (kept from foss-mcp: only committed content may verdict)
# --------------------------------------------------------------------------
def make_worktree(rev: str) -> Path:
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    wt = Path(tempfile.mkdtemp(prefix="wt-", dir=str(WORKTREE_ROOT)))
    shutil.rmtree(wt, ignore_errors=True)
    rc, _, err = git("worktree", "add", "--detach", "--force", str(wt), rev)
    if rc != 0:
        die(f"worktree add failed for {rev}: {err}")
    return wt


def drop_worktree(wt: Path):
    git("worktree", "remove", "--force", str(wt))
    shutil.rmtree(wt, ignore_errors=True)


def parse_junit(xml_path: Path):
    if not xml_path.exists():
        return {}
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return {}
    nodes = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    agg = {"tests": 0, "skipped": 0, "errors": 0, "failures": 0}
    for n in nodes:
        for k in agg:
            agg[k] += int(n.attrib.get(k, 0) or 0)
    return agg


def main(argv=None) -> int:
    """Entry point. The command surface lives in gatecli to keep this file
    focused on primitives (paths, scope, fingerprint, worktrees)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gatecli
    return gatecli.main(argv)


if __name__ == "__main__":
    sys.exit(main())
