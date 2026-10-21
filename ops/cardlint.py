"""Authoring-time lint for taskcard checks. Ported near-verbatim from
foss-mcp's ops/cardlint.py (2026-10-21) -- no foss-mcp-specific content;
these are language/tooling-agnostic lessons from real past incidents there:

  L1  A falsifier built with a backslash or an escaped quote. The shell
      mangles it, so the falsifier does not apply, and a check that never
      broke is charged as the card's failure.
  L2  A check that reaches the network under `network: false`. The offline
      gate runs with a dead proxy, so such a test errors at setup.
  L3  A test that runs this repo's own CI/hook scripts. Its subprocess can
      run that same test again, so the run recurses.

Scope and the rule for old cards: lint applies only to cards WITHOUT an
accepted receipt. A card that passed verify has been proven once, so this
module must not retroactively fail it.

The lint is a heuristic over text, and it can be wrong in both directions. It
returns plain findings for a supervisor to read. It is never a silent gate.
"""

from __future__ import annotations

import re
from pathlib import Path

NETWORK_HINTS = (
    "git clone",
    "git fetch",
    "'clone'",
    "'fetch'",
    "urlopen(",
    "requests.get(",
)

# Invocation shapes for THIS repo's own CI/hooks, once they exist
# (ops/gatecli.py verify/review, scripts/ci_check.sh if added later).
CI_HINTS = (
    "'gatecli.py', 'verify'",
    '"gatecli.py", "verify"',
    "'bash', 'scripts/ci_check.sh'",
    '"bash", "scripts/ci_check.sh"',
)

_TEST_TOKEN = re.compile(r"^tests/\S*$")


def _strip_docstrings(text: str) -> str:
    """The source with its docstrings removed. A test that explains a hook is
    not a test that runs it."""
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    out = text
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                out = out.replace(first.value.value, "")
    return out


def _check_commands(card: dict) -> list[str]:
    return [str(c.get("command", "")) for c in card.get("checks", []) or []]


def _test_files(card: dict, repo: Path) -> list[Path]:
    out: list[Path] = []
    for cmd in _check_commands(card):
        for raw in cmd.split():
            tok = raw.strip("'\"")
            if not _TEST_TOKEN.match(tok):
                continue
            p = repo / tok.rstrip("/")
            if p.is_dir():
                out.extend(sorted(p.rglob("*.py")))
            elif p.is_file() and p.suffix == ".py":
                out.append(p)
    return sorted(set(out))


def _mutate_problems(card: dict) -> list[str]:
    neg = card.get("negative_control") or {}
    mutate = str(neg.get("mutate", ""))
    cid = card.get("id", "?")
    out = []
    if "\\" in mutate:
        out.append(
            f"{cid}: negative_control.mutate contains a backslash. The shell can mangle it, "
            "so the falsifier may never apply. Build it with chr() (AGENTS.md, falsifier rule)."
        )
    return out


def lint_card(card: dict, repo: Path, *, accepted: bool) -> list[str]:
    """Findings for one card. Empty when the card is accepted (grandfathered)."""
    if accepted:
        return []
    cid = card.get("id", "?")
    problems = _mutate_problems(card)

    files = _test_files(card, repo)
    offline = not bool(card.get("network", False))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(repo).as_posix()
        if offline:
            for hint in NETWORK_HINTS:
                if hint in text:
                    problems.append(
                        f"{cid}: {rel} reaches the network ({hint!r}) but the card says "
                        "network: false. Declare network: true, or read a pinned fixture."
                    )
                    break
        code = _strip_docstrings(text)
        for hint in CI_HINTS:
            if hint in code:
                problems.append(
                    f"{cid}: {rel} invokes the CI or a hook ({hint!r}). A test that runs "
                    "the gate can recurse into itself."
                )
                break
    return problems
