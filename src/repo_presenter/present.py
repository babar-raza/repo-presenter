"""Hosted ``present``: one repository, one durable transaction, one cascade, one sealed candidate.

Wires the durable-state backend (``core/state/``) around the present-equivalent cascade
(``cascade.py``): the transaction's recovery, dedup, and lease discipline come from
``core/state/present_transaction.py``; the work itself is one pinned clone, the Lane L facts, the
whole S3-S8 cascade under one invocation, the independent review, and the first seal. The
transaction's committed outcome is derived from what the run actually left on disk, never from a
second guess.

Usage (what ``.github/workflows/present.yml`` runs):

    python -m repo_presenter.present --repository <owner>/<repo> --ecosystem <ecosystem>
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from repo_presenter.cascade import (
    DEFAULT_PROMPTS_PATH,
    DEFAULT_REGISTRY_PATH,
    run_cascade,
)
from repo_presenter.core.config import GatewayConfig, load_gateway_config
from repo_presenter.core.errors import ConfigError, PresenterError
from repo_presenter.core.facts import write_facts
from repo_presenter.core.git_safety.clone import pinned_read_only_clone
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.state.cas import StateBackend
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.state.present_transaction import (
    STATE_TOKEN_VARIABLE,
    PresentOutcome,
    classify_present_outcome,
    run_present_transaction,
)
from repo_presenter.lane_l import build_lane_l_facts
from repo_presenter.readme.bundle.seal import SealInputs, seal_candidate

READ_TOKEN_VARIABLE = "REPOSITORY_PRESENTER_READ_TOKEN"
DEFAULT_WORKDIR = Path(".present-work")
# Sealed bundles live in the checkout's committed candidates/ tree (or a restored copy of it),
# never in the disposable workdir: a rerun can only prove a no-op against a bundle that outlives
# the run that sealed it.
DEFAULT_CANDIDATES_ROOT = Path(".")


class PresentFailure(PresenterError):
    """The pipeline reached an expected, typed refusal (the independent review rejected the
    candidate, so nothing was sealed). Recorded as a failed transaction with this message."""


def cascade_pipeline(
    *,
    repository: str,
    ecosystem: str,
    workdir: Path,
    candidates_root: Path,
    config: GatewayConfig,
    read_token: str | None,
    prompts_path: Path,
    registry_path: Path,
) -> None:
    clone = pinned_read_only_clone(
        f"https://github.com/{repository}.git", workdir / "clone", token=read_token
    )
    document = build_lane_l_facts(
        repository,
        clone.path,
        ecosystem,
        source_revision=clone.revision,
        workspace=workdir / "examples",
        entry=require_listed(load_registry(registry_path), repository),
    )
    facts_path = workdir / "facts.json"
    write_facts(document, facts_path)
    result = run_cascade(
        repository,
        ecosystem,
        clone.path,
        facts_path=facts_path,
        out_dir=workdir / "cascade",
        config=config,
        prompts_path=prompts_path,
        registry_path=registry_path,
    )
    verdict = result.review_verdict
    if verdict.verdict != "ACCEPT":
        raise PresentFailure(
            f"independent review returned {verdict.verdict} with {len(verdict.findings)} "
            "finding(s); nothing sealed"
        )
    seal_candidate(
        SealInputs(
            entry=result.entry,
            source_revision=result.source_revision,
            facts=result.document,
            prompts=load_manifests(prompts_path),
            out_dir=result.out_dir,
            facts_path=result.facts_path,
            candidates_root=candidates_root,
            provider_calls=result.provider_calls,
            invocation=result.invocation,
        )
    )


def run_present(
    *,
    backend: StateBackend,
    entry: RegistryEntry,
    candidates_root: Path,
    holder_id: str,
    workflow_run_id: str | None,
    pipeline: Callable[[], None],
) -> int:
    """Run ``pipeline`` under the durable transaction for ``entry``; returns the exit code.

    Any typed failure of the pipeline becomes a recorded failed transaction (never a silently
    dropped lease); an untyped exception is a defect and propagates after the lease is released.
    """
    failure: dict[str, str] = {}

    def run() -> int:
        try:
            pipeline()
        except PresenterError as exc:
            failure["detail"] = f"{type(exc).__name__}: {exc}"
            return 1
        return 0

    def classify(exit_code: int) -> PresentOutcome:
        if exit_code != 0:
            return PresentOutcome(
                kind="failed",
                detail=failure.get("detail", f"present exited {exit_code}"),
            )
        return classify_present_outcome(candidates_root, entry, exit_code)

    return run_present_transaction(
        backend=backend,
        repository=entry.repository,
        provider_repository_id=entry.provider_identity.repository_id,
        holder_id=holder_id,
        run=run,
        classify=classify,
        workflow_run_id=workflow_run_id,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_presenter.present",
        description="Present one listed repository under the durable-state transaction.",
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ecosystem", required=True)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--candidates-root", type=Path, default=DEFAULT_CANDIDATES_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS_PATH)
    parser.add_argument("--state-remote", default="origin")
    parser.add_argument("--workflow-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    args = parser.parse_args(argv)

    try:
        entry = require_listed(load_registry(args.registry), args.repository)
        if entry.ecosystem != args.ecosystem:
            raise ConfigError(
                f"{args.repository} is registered as {entry.ecosystem!r}, not {args.ecosystem!r}"
            )
        config = load_gateway_config(os.environ)
    except PresenterError as exc:
        print(f"::error::present refused before any work: {exc}", file=sys.stderr)
        return exc.exit_code

    read_token = os.environ.get(READ_TOKEN_VARIABLE) or None
    state_token = os.environ.get(STATE_TOKEN_VARIABLE) or None
    with GitStateBackend(remote=args.state_remote, token=state_token) as backend:
        exit_code = run_present(
            backend=backend,
            entry=entry,
            candidates_root=args.candidates_root,
            holder_id=f"present:{args.workflow_run_id or os.getpid()}",
            workflow_run_id=args.workflow_run_id,
            pipeline=lambda: cascade_pipeline(
                repository=args.repository,
                ecosystem=args.ecosystem,
                workdir=args.workdir,
                candidates_root=args.candidates_root,
                config=config,
                read_token=read_token,
                prompts_path=args.prompts,
                registry_path=args.registry,
            ),
        )
        record = backend.load(args.repository)

    state = record.state if record is not None else "NO_RECORD"
    print(f"present: {args.repository} exit {exit_code}, durable state {state}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
