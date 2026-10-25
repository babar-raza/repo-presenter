"""Run the whole S3-S8 cascade for one repository in one process, under one invocation.

BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR (project/state.yaml): the thin CLI wrapper over
repo_presenter.cascade.run_cascade -- the present-equivalent orchestrator the owner decided to
build 2026-10-25. Replaces running scripts/run_lane_r_{investigation,reconciliation,planning,
authoring_real,coherence}.py and run_lane_r_render.py + scripts/run_independent_review.py as six
separate processes for one repository: this does the same real work, writes the same artifact
files, but under ONE Invocation/Ledger, which is what a future seal.py adaptation needs.

Usage:
    python scripts/run_cascade.py <owner>/<repo> <ecosystem> <clone_path>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.cascade import run_cascade
from repo_presenter.core.config import load_gateway_config


def main() -> None:
    repository, ecosystem, clone_path_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    clone_path = Path(clone_path_arg)
    repo_dir = repository.replace("/", "__")
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    out_dir = Path("scripts/_lane_r_output") / repo_dir
    config = load_gateway_config(os.environ)

    print(f"Running the whole S3-S8 cascade for {repository} ({ecosystem}) under one invocation")
    result = run_cascade(
        repository, ecosystem, clone_path, facts_path=facts_path, out_dir=out_dir, config=config,
    )
    print(f"invocation {result.invocation.invocation_id}: {result.provider_calls} provider call(s)")
    print(f"review verdict: {result.review_verdict.verdict} "
          f"({len(result.review_verdict.findings)} finding(s))")
    print(f"README: {result.readme_path}")


if __name__ == "__main__":
    main()
