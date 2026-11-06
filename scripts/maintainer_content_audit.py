"""Audit what the pipeline did with maintainer-authored README content (read-only).

Requirement 6 of docs/MAINTAINER_CONTENT_PRESERVATION.md: calibrate the preservation rules on real
candidates, not assumptions -- and re-measure after a change. For each sealed Lane R candidate it
reports the disposition counts, why each omitted unit was omitted (by its own rationale), and how much
of each SUPERSEDE_REDUNDANT unit's distinctive content still appears in the final README (a superseded
unit whose words mostly vanished is a possible loss of maintainer knowledge, requirement 5).

    python scripts/maintainer_content_audit.py --bundles-dir <dir>          # already exported bundles
    python scripts/maintainer_content_audit.py --export-to <dir>            # export every Lane R bundle from origin first
    ... [--json out.json] [--show 20]

``<dir>`` holds ``<key>/<key>/CURRENT`` and ``<key>/<key>/<revision>/`` as
``core/state/bundle_store.export_bundle`` writes them. No provider call, no upstream access.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

_STOP = frozenset(
    ["the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "is", "are", "be", "this", "that", "it", "its", "as", "from", "at", "your", "you", "can", "not", "no", "all", "any", "each", "into", "via", "using", "use", "used", "uses", "more", "see", "also"]
)
_WORD = re.compile(r"[a-z][a-z0-9_.+-]{2,}")
LOW, PARTIAL = 0.5, 0.8


def words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


def coverage(unit_text: str, readme: str) -> float:
    """Share of the unit's distinctive words that occur in the README (1.0 for a unit too short to
    judge)."""
    unit = words(unit_text)
    if len(unit) < 4:
        return 1.0
    return len(unit & words(readme)) / len(unit)


def omission_reason(rationale: str, unit_id: str) -> str:
    text = rationale.lower()
    if "contradicted" in text:
        return "tied to a CONTRADICTED example"
    if "redundant" in text or "duplicat" in text:
        return "redundant with facts or other text"
    if unit_id.endswith((".heading", ".html_block", ".badge_row")) or "wrapper" in text or "heading" in text:
        return "heading, wrapper or badge markup"
    if "promot" in text or "marketing" in text:
        return "promotional"
    return "no fact supports it"


def _rows(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, dict):
        return list(document.get("dispositions", []))
    return list(document)


def audit_bundle(revision_dir: Path) -> dict[str, Any]:
    readme = (revision_dir / "README.md").read_text(encoding="utf-8")
    facts = {
        f["id"]: f
        for f in json.loads((revision_dir / "facts.json").read_text(encoding="utf-8"))["facts"]
    }
    rows = _rows(json.loads((revision_dir / "dispositions.json").read_text(encoding="utf-8")))
    counts = collections.Counter(str(r.get("disposition")) for r in rows)
    omitted = collections.Counter()
    superseded: list[dict[str, Any]] = []
    for row in rows:
        unit_id = str(row.get("unit_id", ""))
        rationale = str(row.get("rationale") or "")
        text = str((facts.get(unit_id) or {}).get("value", ""))
        if row.get("disposition") == "OMIT_UNSUPPORTED":
            omitted[omission_reason(rationale, unit_id)] += 1
        elif row.get("disposition") == "SUPERSEDE_REDUNDANT":
            superseded.append(
                {
                    "unit_id": unit_id,
                    "coverage": round(coverage(text, readme), 2),
                    "text": text[:200],
                    "rationale": rationale[:200],
                }
            )
    return {"counts": dict(counts), "omitted": dict(omitted), "superseded": superseded}


def bundle_dirs(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for current in sorted(root.glob("*/*/CURRENT")):
        key = current.parent.name
        if key not in found:
            found[key] = current.parent / current.read_text(encoding="utf-8").strip()
    return found


def export_all(target: Path, remote: str = "origin") -> None:
    from repo_presenter.core.state.bundle_store import BUNDLE_REF_PREFIX, export_bundle

    listed = subprocess.run(
        ["git", "ls-remote", remote, f"{BUNDLE_REF_PREFIX}/*"],
        capture_output=True, text=True, check=True,
    ).stdout
    for line in listed.splitlines():
        key = line.split("\t")[1].rsplit("/", 1)[-1]
        if key.endswith("@lane-l"):
            continue
        export_bundle(key.replace("__", "/", 1), "R", target / key, remote=remote)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundles-dir", type=Path)
    source.add_argument("--export-to", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--show", type=int, default=20, help="lowest-coverage superseded units to list")
    args = parser.parse_args(argv)
    root = args.bundles_dir or args.export_to
    if args.export_to is not None:
        export_all(args.export_to)
    results = {key: audit_bundle(path) for key, path in bundle_dirs(root).items()}
    counts: collections.Counter[str] = collections.Counter()
    omitted: collections.Counter[str] = collections.Counter()
    superseded: list[dict[str, Any]] = []
    for key, result in results.items():
        counts.update(result["counts"])
        omitted.update(result["omitted"])
        superseded.extend({"repository": key, **row} for row in result["superseded"])
    buckets = collections.Counter(
        "low (<0.5)" if r["coverage"] < LOW else "partial (0.5-0.8)" if r["coverage"] < PARTIAL else "carried (>=0.8)"
        for r in superseded
    )
    print(f"{len(results)} candidates, {sum(counts.values())} inherited units")
    print("dispositions:", dict(counts.most_common()))
    print("omitted, by reason:", dict(omitted.most_common()))
    print("superseded, content still in the README:", dict(buckets))
    for row in sorted(superseded, key=lambda r: r["coverage"])[: args.show]:
        print(f"  {row['coverage']:.2f} {row['repository'].split('__')[-1]} {row['unit_id']}: {row['text'][:110]}")
    if args.json is not None:
        args.json.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
