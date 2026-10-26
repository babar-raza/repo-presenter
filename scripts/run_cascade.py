"""Run the whole S3-S8 cascade for one repository in one process, under one invocation, then
seal the result.

BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR (project/state.yaml): the thin CLI wrapper over
repo_presenter.cascade.run_cascade -- the present-equivalent orchestrator the owner decided to
build 2026-10-25. Replaces running scripts/run_lane_r_{investigation,reconciliation,planning,
authoring_real,coherence}.py and run_lane_r_render.py + scripts/run_independent_review.py as six
separate processes for one repository: this does the same real work, writes the same artifact
files, but under ONE Invocation/Ledger, which is what readme.bundle.seal needs.

Seals automatically after a successful cascade (PORT_BUNDLE_INTEGRITY_LAYER step 7/8): this is
the real caller seal_candidate's own module docstring named as not yet wired -- passes
CascadeResult.invocation/.entry/.document/.provider_calls directly, no hand reconstruction.
seal_candidate v1 raises NotImplementedError against an already-sealed bundle (re-seal is not
built yet, see that module's own docstring); this script reports that plainly rather than
crashing, since re-running a repository that was already sealed is an expected, not an
exceptional, case right now.

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
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.bundle.seal import SealInputs, seal_candidate


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

    seal_inputs = SealInputs(
        entry=result.entry,
        source_revision=result.source_revision,
        facts=result.document,
        prompts=load_manifests(Path("prompts")),
        out_dir=result.out_dir,
        facts_path=result.facts_path,
        candidates_root=Path("."),
        provider_calls=result.provider_calls,
        invocation=result.invocation,
    )
    try:
        sealed = seal_candidate(seal_inputs)
    except NotImplementedError as exc:
        print(f"\nnot sealed: {exc}")
        return
    print(f"\nsealed: {sealed.bundle} (state={sealed.state})")


if __name__ == "__main__":
    main()
