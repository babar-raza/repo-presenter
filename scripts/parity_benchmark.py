"""Real, reproducible pilot-parity comparison between a repo-presenter candidate and the
corresponding aspose.org refresh-candidate reference (2026-11-04, TC-006, follow-up directive
§7/§9 -- read-only analysis of already-committed candidates against a local sibling checkout;
does NOT touch, resume, or ratify the paused broad sweep).

Measures objective, deterministic structural facts -- heading list, code-fence count, line
count, link count, and presence of specific required sections -- rather than a subjective
"looks similar" judgment. Independently reproducible: re-run it and get the same numbers from
the same two files.

Usage:
    python scripts/parity_benchmark.py <repo-presenter readme.md> <aspose.org readme.md>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
REQUIRED_SECTION_PATTERNS = {
    "quickstart_or_minimal_example": re.compile(r"quick\s*start|minimal\s*example", re.IGNORECASE),
    "at_a_glance": re.compile(r"at\s*a\s*glance", re.IGNORECASE),
    "installation": re.compile(r"install", re.IGNORECASE),
}


def analyze(text: str) -> dict:
    headings = [(len(m.group(1)), m.group(2).strip()) for m in HEADING_RE.finditer(text)]
    lines = text.splitlines()
    return {
        "line_count": len(lines),
        "heading_count": len(headings),
        "h2_headings": [h for level, h in headings if level == 2],
        "code_fence_count": len(CODE_FENCE_RE.findall(text)) // 2,
        "link_count": len(LINK_RE.findall(text)),
        "has_required_section": {
            name: bool(pattern.search(text)) for name, pattern in REQUIRED_SECTION_PATTERNS.items()
        },
        # A real, checkable structural defect class from prior independent review: the opening
        # H1 appearing more than once (a "double opening" symptom), checked directly here rather
        # than trusted from narration.
        "h1_count": sum(1 for level, _ in headings if level == 1),
    }


def compare(candidate_path: Path, reference_path: Path) -> dict:
    candidate = analyze(candidate_path.read_text(encoding="utf-8"))
    reference = analyze(reference_path.read_text(encoding="utf-8"))
    return {
        "candidate_path": str(candidate_path),
        "reference_path": str(reference_path),
        "candidate": candidate,
        "reference": reference,
        "deltas": {
            "line_count": candidate["line_count"] - reference["line_count"],
            "code_fence_count": candidate["code_fence_count"] - reference["code_fence_count"],
            "link_count": candidate["link_count"] - reference["link_count"],
        },
        "candidate_missing_required_sections": [
            name for name, present in candidate["has_required_section"].items() if not present
        ],
        "candidate_has_duplicate_h1": candidate["h1_count"] > 1,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: parity_benchmark.py <candidate readme.md> <reference readme.md>")
        return 2
    candidate_path, reference_path = Path(argv[0]), Path(argv[1])
    import json

    result = compare(candidate_path, reference_path)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
