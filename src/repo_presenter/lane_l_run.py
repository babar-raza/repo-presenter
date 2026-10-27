"""The hosted Lane L stage: the live README, corrected with minimal evidenced edits, then judged.

The Lane L analogue of ``cascade.py`` (``plans/PLAN_lane_l_hosted.md``). One process, one
:class:`~repo_presenter.core.noop_proof.Invocation`, one ledger:

1. read the facts the secret-free facts job built and the pinned clone (the same inputs the Lane R
   cascade reads; this stage executes no repository code and builds no facts);
2. run the correction engine over the live README bytes, the verified facts and the tracked tree
   (``readme.correction.engine.correct``: pure, deterministic, no provider call);
3. write the candidate's artifacts: the corrected README, the live README it was made from, the
   patch, the edit list and report, and the deterministic holdouts;
4. judge the FINAL README (``readme.correction.review``): the deterministic holdouts, then the
   independent LLM review (the one provider call of a Lane L run, replayed from the call store on a
   rerun).

Every artifact is written as bytes (or ``newline="\\n"`` text): a sealed artifact is hashed by its
exact bytes, so a default newline would give CRLF on Windows and LF on Linux and no rerun could be
byte-identical across machines. No path, time or host name enters any artifact.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from repo_presenter.cascade import DEFAULT_PROMPTS_PATH, DEFAULT_REGISTRY_PATH
from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.noop_proof import Invocation, measure_invocation
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.registry_entry_stub import RegistryEntryStub
from repo_presenter.core.snapshot.inventory import scan
from repo_presenter.lane_l import tree_paths_of
from repo_presenter.lane_l_review import (
    HOLDOUTS_FILENAME,
    holdout_findings,
    holdouts_document,
    review_correction,
)
from repo_presenter.readme.composition.renderer import render_patch
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.model import Context, CorrectionResult
from repo_presenter.readme.correction.report import (
    CORRECTIONS_FILENAME,
    CorrectionRunError,
    canonical_json,
    corrections_document,
    outcome_of,
)
from repo_presenter.readme.review.independent_reviewer import (
    REVIEW_VERDICT_FILENAME,
    ReviewVerdict,
    write_review_verdict,
)

CORRECTED_README_FILENAME = "README.corrected.md"
ORIGINAL_README_FILENAME = "README.original.md"
PATCH_FILENAME = "README.patch.diff"


@dataclass(frozen=True)
class LaneLResult:
    """What a caller needs after one Lane L run: the one invocation that made every provider call,
    where every artifact landed, the independent review's verdict on the FINAL README, and -- for
    a caller that seals it -- the registry entry and the facts this run actually consumed."""

    repository: str
    source_revision: str
    invocation: Invocation
    provider_calls: int
    out_dir: Path
    facts_path: Path
    readme_path: Path
    review_verdict: ReviewVerdict
    entry: RegistryEntry
    document: FactsDocument
    correction: CorrectionResult
    outcome: str
    deterministic: bool
    idempotent: bool


def _read_live_readme(clone_path: Path) -> tuple[str, bytes, str]:
    """``(relative path, bytes, text)`` of the clone's live README. Lane L corrects a README that
    exists; a repository without one is Lane R's, and bytes that are not UTF-8 cannot be edited
    without altering the bytes outside the edits, so both are typed refusals, never a repair."""
    inventory = scan(clone_path)
    if inventory.readme_path is None:
        raise CorrectionRunError(
            "the clone has no README: Lane L corrects a live README and has none to start from; "
            "Lane R writes one"
        )
    data = inventory.readme_path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorrectionRunError(
            f"{inventory.readme_path.name} is not valid UTF-8 ({exc.reason} at byte {exc.start}): "
            "Lane L cannot edit text it cannot represent without changing the bytes outside its "
            "edits; Lane R can rewrite it"
        ) from exc
    return inventory.readme_path.relative_to(clone_path).as_posix(), data, text


def run_lane_l(
    repository: str,
    ecosystem: str,
    clone_path: Path,
    *,
    facts_path: Path,
    out_dir: Path,
    config: GatewayConfig,
    prompts_path: Path = DEFAULT_PROMPTS_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> LaneLResult:
    """Correct and review the live README of the clone at ``clone_path`` (a pinned, read-only
    clone), from the facts at ``facts_path``, writing the candidate's artifacts under ``out_dir``.

    The facts must describe the revision the clone is at (a clone that moved since the facts job
    ran fails closed). ``ReviewUnavailable`` propagates when no valid review could be obtained: the
    artifacts written so far stay on disk as evidence, and nothing is sealed.
    """
    document = read_facts(facts_path)
    clone_path = clone_path.resolve()
    source_revision = run_git(["rev-parse", "HEAD"], cwd=clone_path).stdout.strip()
    if document.source_revision != source_revision:
        raise CorrectionRunError(
            f"the facts describe {document.source_revision} but the clone is at {source_revision}"
        )
    entry = require_listed(load_registry(registry_path), repository)
    if entry.ecosystem != ecosystem:
        raise CorrectionRunError(
            f"{repository} is registered as {entry.ecosystem!r}, not {ecosystem!r}"
        )
    prompts = load_manifests(prompts_path)

    readme_path, original_bytes, original = _read_live_readme(clone_path)
    ctx = Context(
        entry=RegistryEntryStub(
            repository=repository,
            family=entry.family,
            platform=entry.platform,
            ecosystem=entry.ecosystem,
        ),
        facts=document,
        readme=original,
        tree_paths=tuple(tree_paths_of(clone_path)),
        readme_path=readme_path,
    )
    result = correct(ctx)
    deterministic, idempotent = is_stable(ctx, result)
    outcome = outcome_of(result)

    out_dir.mkdir(parents=True, exist_ok=True)
    corrected_bytes = result.corrected.encode("utf-8")
    (out_dir / CORRECTED_README_FILENAME).write_bytes(corrected_bytes)
    (out_dir / ORIGINAL_README_FILENAME).write_bytes(original_bytes)
    (out_dir / PATCH_FILENAME).write_bytes(
        render_patch(original, result.corrected).encode("utf-8")
    )
    (out_dir / CORRECTIONS_FILENAME).write_bytes(
        canonical_json(
            corrections_document(
                ctx,
                result,
                original_sha256=hashlib.sha256(original_bytes).hexdigest(),
                corrected_sha256=hashlib.sha256(corrected_bytes).hexdigest(),
                deterministic=deterministic,
                idempotent=idempotent,
            )
        )
    )

    findings = holdout_findings(ctx, result, deterministic=deterministic)
    holdouts = holdouts_document(
        findings, idempotent=idempotent, source_revision=source_revision
    )
    (out_dir / HOLDOUTS_FILENAME).write_bytes(canonical_json(holdouts))

    workspace = out_dir / "llm_cache"
    invocation = Invocation.begin()
    ledger_path = workspace / "ledger.jsonl"
    ledger = Ledger(ledger_path, invocation_id=invocation.invocation_id)
    store = CallStore(workspace / "calls")
    context = JobContext(repository=repository, source_revision=source_revision)

    verdict = review_correction(
        ctx=ctx,
        result=result,
        findings=findings,
        holdouts=holdouts,
        prompts=prompts,
        config=config,
        ledger=ledger,
        store=store,
        context=context,
        facts=document,
    )
    write_review_verdict(verdict, out_dir / REVIEW_VERDICT_FILENAME)

    provider_calls = 0
    if ledger_path.is_file():
        invocation.attach_ledger(repository, ledger_path)
        invocation.write(
            workspace / "invocations" / f"{invocation.invocation_id}.json", Path("."), 0
        )
        provider_calls = measure_invocation(
            ledger_path, invocation.invocation_id
        ).provider_calls

    return LaneLResult(
        repository=repository,
        source_revision=source_revision,
        invocation=invocation,
        provider_calls=provider_calls,
        out_dir=out_dir,
        facts_path=facts_path,
        readme_path=out_dir / CORRECTED_README_FILENAME,
        review_verdict=verdict,
        entry=entry,
        document=document,
        correction=result,
        outcome=outcome,
        deterministic=deterministic,
        idempotent=idempotent,
    )
