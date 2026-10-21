"""Credential/secret pattern scanner for commits and working-tree diffs.

NOTE: this is a lightweight reimplementation from the foss-mcp description
(it has a 304-line original at ops/secretscan.py with likely more patterns and
CI-log-specific handling) rather than a verbatim port -- the original was not
read in full for this v1 pass. Treat this as a starting point to extend, not a
faithful port; see migration/reuse-manifest.yaml for the disposition note.
"""

from __future__ import annotations

import re
from pathlib import Path

# (name, regex) -- deliberately specific enough to avoid matching ordinary
# hex/base64-looking text that isn't actually a credential shape.
PATTERNS = [
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36,255}\b")),
    ("aws_access_key_id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws(.{0,20})?secret(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,48}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("generic_private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
]

# Files that legitimately contain pattern-shaped example text and should not
# be scanned (fixtures, this file itself).
DEFAULT_EXCLUDES = (
    "ops/secretscan.py",
    ".gatectl-worktrees/**",
)


def scan_text(text: str, path: str = "<text>") -> list[str]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pat in PATTERNS:
            if pat.search(line):
                findings.append(f"{path}:{lineno}: possible {name}")
    return findings


def scan_paths(paths: list[Path], repo_root: Path) -> list[str]:
    findings = []
    for p in paths:
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root).as_posix() if p.is_absolute() else str(p)
        if any(rel.startswith(x.rstrip("/*")) for x in DEFAULT_EXCLUDES):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        findings.extend(scan_text(text, rel))
    return findings


def scan_tree(repo_root: Path) -> list[str]:
    """Scan every git-tracked, non-binary-looking file. Used by `secret-scan`."""
    import subprocess
    out = subprocess.run(
        ["git", "ls-files"], cwd=str(repo_root), capture_output=True, text=True, check=False
    ).stdout
    paths = [repo_root / line.strip() for line in out.splitlines() if line.strip()]
    return scan_paths(paths, repo_root)
