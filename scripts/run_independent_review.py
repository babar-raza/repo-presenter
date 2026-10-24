"""The independent reviewer's first real portfolio pass (BUILD_INDEPENDENT_REVIEWER,
project/state.yaml).

Runs readme.review.independent_reviewer.review_candidate against every repository under
scripts/_lane_r_output/ that has reached a complete render (README.coherent.md or
README.rendered.md, plus the matching content_units(.coherent).json and dispositions.json),
using the exact matching facts.json already pinned per repository under
evidence/build/P2_REAL_ENGINE_SALVAGE/<repo_dir>/facts.json -- no name-guessing or fuzzy
matching: the directory name is the repository identifier (``/`` replaced with ``__``) in both
places, the same convention run_lane_r_render.py already uses.

This is a first-ever independent review pass, not a recheck of already-accepted work: per
project/state.yaml's owner_review_status note (2026-10-24), none of these candidates carry
owner acceptance, and SALVAGE_INVENTORY_2026_10_23 confirmed no independent reviewer existed in
this repository before BUILD_INDEPENDENT_REVIEWER. A REJECT found here is a new finding against
mission non-negotiable #3 ("consumed-scope invalidation only"), not a global reseal.

Usage:
    python scripts/run_independent_review.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.facts import read_facts
from repo_presenter.readme.review.independent_reviewer import review_candidate

LANE_R_OUTPUT = Path("scripts/_lane_r_output")
FACTS_ROOT = Path("evidence/build/P2_REAL_ENGINE_SALVAGE")
REPORT_PATH = Path("evidence/build/P2_REAL_ENGINE_SALVAGE/independent_review_report.json")


def _repo_dirs() -> list[Path]:
    return sorted(p for p in LANE_R_OUTPUT.iterdir() if p.is_dir())


def _load_units(out_dir: Path) -> tuple[list[dict[str, object]], str]:
    """Prefer the coherence-finalized units/render (the last accepted stage before publish);
    fall back to the pre-coherence render when S8 was never run for this repository."""
    if (out_dir / "content_units.coherent.json").exists():
        units_doc = json.loads((out_dir / "content_units.coherent.json").read_text(encoding="utf-8"))
        stage = "coherent"
    else:
        units_doc = json.loads((out_dir / "content_units.json").read_text(encoding="utf-8"))
        stage = "rendered"
    return units_doc["units"], stage


def _readme_text(out_dir: Path, stage: str) -> str:
    preferred = out_dir / ("README.coherent.md" if stage == "coherent" else "README.rendered.md")
    return preferred.read_text(encoding="utf-8")


def main() -> None:
    results: dict[str, object] = {}
    reviewed = 0
    not_reviewable = 0
    rejected = 0

    for out_dir in _repo_dirs():
        if not out_dir.is_dir():
            continue
        repo_dir = out_dir.name
        has_coherent = (out_dir / "content_units.coherent.json").exists() and (
            out_dir / "README.coherent.md"
        ).exists()
        has_rendered = (out_dir / "content_units.json").exists() and (
            out_dir / "README.rendered.md"
        ).exists()
        if not (has_coherent or has_rendered):
            results[repo_dir] = {"reviewable": False, "reason": "no rendered candidate yet"}
            not_reviewable += 1
            print(f"SKIP  {repo_dir}: no rendered candidate yet")
            continue

        facts_path = FACTS_ROOT / repo_dir / "facts.json"
        if not facts_path.exists():
            results[repo_dir] = {"reviewable": False, "reason": f"no facts.json at {facts_path}"}
            not_reviewable += 1
            print(f"SKIP  {repo_dir}: no facts.json")
            continue

        units, stage = _load_units(out_dir)
        readme_text = _readme_text(out_dir, stage)
        facts = read_facts(facts_path)
        dispositions = json.loads((out_dir / "dispositions.json").read_text(encoding="utf-8"))

        verdict = review_candidate(
            readme_text=readme_text, units=units, facts=facts, dispositions=dispositions
        )
        reviewed += 1
        if verdict.verdict == "REJECT":
            rejected += 1
        results[repo_dir] = {
            "reviewable": True,
            "stage": stage,
            "verdict": verdict.verdict,
            "deterministic_reject_count": verdict.deterministic_reject_count,
            "findings": [asdict(f) for f in verdict.findings],
        }
        print(f"{verdict.verdict:6} {repo_dir} (stage={stage}, findings={len(verdict.findings)})")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"\n{reviewed} reviewed, {rejected} REJECT, {reviewed - rejected} ACCEPT, "
        f"{not_reviewable} not yet reviewable. Report: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
