"""Re-certification instead of regeneration: hold a sealed candidate to CURRENT standards without
asking any model anything again.

Owner rule (2026-11-06, binding; the two predecessor projects were abandoned over it): "we sealed
some candidates and then a candidate caused version bump, and all previous sealed candidates were
lost, and number dropped to 0, and then we have to reseal all previous candidates. I do not want
that." Every candidate is held to the SAME current pipeline (one version set for all), AND a
version bump never invalidates a seal or forces regeneration.

Both halves hold at once because a sealed bundle stores every LLM stage's output (facts, plan,
dispositions, content units for Lane R; the live README and the correction for Lane L) and its
model review verdict. Re-certification re-runs ONLY the deterministic stages with current code --
the renderer, the full blocking validation (``validation.blocking.validate_candidate``, BC-05
supersession and BC-07 public text included) and the deterministic reviewer rules for Lane R; the
correction engine and its holdouts for Lane L -- over those stored outputs. It makes ZERO provider
calls: nothing here imports a gateway, a ledger or a call store.

Outcomes:

* ``RECERTIFIED`` -- the stored outputs, re-rendered by current code, pass every current check.
  With ``write``, the re-rendered README, the current version set's dependencies record and a
  ``recertification.json`` naming the seal it derives from (``recertified_from``) become a NEW
  seal commit on the same bundle ref. The original's LLM outputs, ledger and model review verdict
  are carried over unchanged; the original commit stays in the ref's history.
* ``NEEDS_REPAIR`` -- the exact failing checks are listed. Nothing is written: the original seal is
  untouched and still recorded. Only this outcome (or a changed source revision / facts / live
  README) sends a candidate back through the generation pipeline.

A seal is never deleted or demoted by this module.

CLI (read-only unless ``--write``):

    python -m repo_presenter.recertify --repository OWNER/NAME --lane R|L [--write]
    python -m repo_presenter.recertify --all [--write] [--json]
    python -m repo_presenter.recertify --gate [--base-baseline PATH]
    python -m repo_presenter.recertify --write-baseline

``--gate`` is the no-regression merge gate: every bundle ref's latest seal is re-certified under the
working tree's code and compared with ``data/recertification_baseline.json``; any seal RECERTIFIED
in the (base) baseline that is NEEDS_REPAIR now fails the gate unless the baseline in the same
change records it as NEEDS_REPAIR with a ``justification`` naming every newly failing check.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    DEPENDENCIES_FILENAME,
    LANE_L,
    LANE_R,
    LANES,
    lane_directory,
    verify_bundle,
)
from repo_presenter.core.errors import PresenterError
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.version_set import fingerprint

OUTCOME_RECERTIFIED = "RECERTIFIED"
OUTCOME_NEEDS_REPAIR = "NEEDS_REPAIR"
RECERTIFICATION_FILENAME = "recertification.json"
#: Bump when what re-certification re-runs, or how it records the result, changes meaning.
RECERTIFY_VERSION = "1"
#: Most restore-and-rejudge passes ``_rerun_lane_r(restore=True)`` makes (each pass can expose a unit
#: the previous one made renderable); a bound, so a restore that keeps failing stops and reports.
RESTORE_ROUNDS = 3
DEFAULT_BASELINE = Path("data/recertification_baseline.json")
#: Manifest states whose sealed files are a model-accepted candidate. VALID_UPDATE_AVAILABLE is a
#: proven seal beside which a later, different rerun was merely recorded (``seal._record_update``):
#: its files are still the proven candidate. INVALIDATED (a factual scope changed) is not.
GOOD_STATES = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL", "VALID_UPDATE_AVAILABLE"})
#: The artifacts an LLM stage produced, per lane. A later seal of the SAME source revision whose
#: digests for any of these differ was a regeneration (re-run model stages), not a re-certification.
LLM_STAGE_ARTIFACTS: dict[str, tuple[str, ...]] = {
    LANE_R: (
        "investigation.json",
        "dispositions.json",
        "plan.json",
        "content_units.json",
        "content_units.coherent.json",
        "review_verdict.json",
    ),
    LANE_L: ("review_verdict.json",),
}


class RecertifyError(PresenterError):
    """Re-certification could not be carried out (not a failing check: a missing input)."""


@dataclass(frozen=True)
class SourceSnapshot:
    """The two things re-certification needs from the pinned revision and a bundle does not
    store: the tracked tree (link and install checks) and, for Lane R, the live README (the
    preservation and loss rules). Read from the upstream repository at the sealed revision."""

    tree_paths: tuple[str, ...]
    readme: bytes | None


@dataclass(frozen=True)
class Recertification:
    repository: str
    lane: str
    revision: str
    outcome: str
    failing_checks: tuple[str, ...] = ()
    details: tuple[str, ...] = ()
    sealed_version_set: str = ""
    current_version_set: str = ""
    readme_changed: bool = False
    seal_commit: str = ""
    regenerations: int = 0
    provider_calls: int = 0
    #: What a writer needs; never serialized into a report.
    readme: bytes = field(default=b"", repr=False, compare=False)
    artifacts: Mapping[str, bytes] = field(default_factory=dict, repr=False, compare=False)

    @property
    def recertified(self) -> bool:
        return self.outcome == OUTCOME_RECERTIFIED

    @property
    def sealed_by_current(self) -> bool:
        return bool(self.sealed_version_set) and self.sealed_version_set == self.current_version_set

    @property
    def certified(self) -> bool:
        """Counts under current standards: re-certified now, or sealed by current code."""
        return self.recertified or (self.sealed_by_current and not self.failing_checks)

    def report(self) -> dict[str, Any]:
        row = {
            k: v for k, v in asdict(self).items() if k not in ("readme", "artifacts")
        }
        row["failing_checks"] = list(self.failing_checks)
        row["details"] = list(self.details)
        return row


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _load_json(bundle: Path, name: str) -> Any:
    return json.loads((bundle / name).read_text(encoding="utf-8"))


# --- the source snapshot ---------------------------------------------------------------------


def fetch_source(
    repository: str, revision: str, workdir: Path, *, token: str | None = None
) -> SourceSnapshot:
    """Fetch exactly ``revision`` of ``repository`` (shallow, no checkout, nothing executed) and
    read its tracked paths and root README. Read-only against the upstream repository."""
    from repo_presenter.core.git_safety.clone import _github_read_auth_env

    url = f"https://github.com/{repository}.git"
    git_dir = workdir / (repository.replace("/", "__") + f"-{revision[:12]}.git")
    if git_dir.exists():
        shutil.rmtree(git_dir)
    git_dir.parent.mkdir(parents=True, exist_ok=True)
    env = {"GIT_LFS_SKIP_SMUDGE": "1", **_github_read_auth_env(url, token)}
    for args in (
        ["init", "-q", "--bare", str(git_dir)],
        ["--git-dir", str(git_dir), "fetch", "-q", "--depth", "1", "--no-tags", url, revision],
    ):
        done = run_git(args, env=env)
        if done.returncode != 0:
            raise RecertifyError(f"fetch of {repository}@{revision[:12]} failed: {done.stderr.strip()}")
    listed = run_git(["--git-dir", str(git_dir), "ls-tree", "-r", "-z", "--name-only", revision])
    if listed.returncode != 0:
        raise RecertifyError(f"ls-tree of {repository}@{revision[:12]} failed: {listed.stderr.strip()}")
    paths = tuple(sorted(p for p in listed.stdout.split("\0") if p))
    readme = None
    if "README.md" in paths:
        import subprocess

        shown = subprocess.run(
            ["git", "--git-dir", str(git_dir), "cat-file", "blob", f"{revision}:README.md"],
            stdin=subprocess.DEVNULL, capture_output=True, check=False,
        )
        if shown.returncode == 0:
            readme = shown.stdout
    shutil.rmtree(git_dir, ignore_errors=True)
    return SourceSnapshot(tree_paths=paths, readme=readme)


# --- the deterministic re-run, per lane --------------------------------------------------------


#: ``unit_reviews[*]["m8"]["status"]`` values TC-013/TC-024's contract reads as "no M8 objection"
#: -- mirrors ``readme.review.llm_review.M8_PASSING_STATUSES`` exactly (duplicated, not imported:
#: this module's own docstring promises "nothing here imports a gateway, a ledger or a call
#: store", and ``llm_review`` pulls all three in; update both sets together).
_M8_PASSING_STATUSES = frozenset({None, "not_run", "ok"})


def _model_accept(review):
    """TC-013/TC-024's seal-path contract: deterministically-validated (``verdict == "ACCEPT"``,
    which ``readme.review.verdict.fold_verdict``'s own invariant already means no deterministic
    mechanism -- M1-M7, M10, ``readme.validation.blocking``, unchanged -- found a blocking finding,
    and every model-reported REJECT_* was deterministically cleared: non-negotiable 5 is never
    weakened by this) AND a real model review was made (``model_verdict`` recorded; a
    deterministic-only verdict never re-certifies) AND M8's recorded verdict (TC-023,
    ``readme.review.prose_judge``, carried per unit in ``unit_reviews[*]["m8"]``) is never a
    REJECT/INCONCLUSIVE for any unit. Replaces the old reviewer's own stricter
    ``model_verdict == "ACCEPT"`` requirement -- that required the OLD monolithic reviewer's
    single call to have said ACCEPT outright, which is exactly "the old reviewer's
    one-call-does-everything verdict" TC-024 moves this gate away from. A unit's ``m8`` field
    absent (every seal made before this card), or recorded ``"not_run"``/``"ok"``, is read as "no
    M8 objection" -- TC-023's real provider-backed calibration is separately budgeted (owner
    ruling R26) and not yet wired; a future card's real ``"reject"``/``"inconclusive"`` blocks
    exactly like the old reviewer's REJECT did, with zero further change to this function. Mirrors
    ``core.state.bundle_store.SealRecord.model_accept`` -- update both together."""
    review = review or {}
    if review.get("verdict") != "ACCEPT":
        return False
    if review.get("model_verdict") is None:
        return False
    for record in review.get("unit_reviews") or ():
        if not isinstance(record, Mapping):
            continue
        m8 = record.get("m8")
        if isinstance(m8, Mapping) and m8.get("status") not in _M8_PASSING_STATUSES:
            return False
    return True


def _rerun_lane_r(
    bundle: Path, entry: Any, source: SourceSnapshot, *, restore: bool = False
) -> tuple[list[str], list[str], dict[str, bytes]]:
    """(failing check ids, details, re-derived artifacts) for a Lane R bundle.

    With ``restore`` (opt-in, used only when WRITING a repaired seal, never by the dry counter or
    the no-regression gate), units BC-05/BC-17 name as lost are re-dispositioned deterministically
    (``readme.repair.restore_units``) and the bundle is re-judged, up to ``RESTORE_ROUNDS`` times;
    the restored ``dispositions.json`` and the list of restored units ride along in the artifacts.
    A restore that does not clear every blocking check still returns the checks it leaves failing:
    the verdict is the validators', never this loop's."""
    dispositions = _load_json(bundle, "dispositions.json")
    failing, details, artifacts = _evaluate_lane_r(bundle, entry, source, dispositions)
    if not restore or not failing:
        return failing, details, artifacts
    from repo_presenter.readme.reconciliation.destinations import holdable_sections
    from repo_presenter.readme.repair.restore_units import choose_units, restore_lost_units

    document = read_facts(bundle / "facts.json")
    holdable = holdable_sections(document)
    included = [
        section["section_id"]
        for section in _load_json(bundle, "plan.json").get("sections", [])
        if section.get("include")
    ]
    restored: list[dict[str, str]] = []
    for _round in range(RESTORE_ROUNDS):
        unit_ids = choose_units(details, document, [c["unit_id"] for c in restored])
        if not unit_ids:
            break
        dispositions, changes = restore_lost_units(dispositions, document, unit_ids, holdable, included)
        if not changes:
            break
        restored.extend(changes)
        failing, details, artifacts = _evaluate_lane_r(bundle, entry, source, dispositions)
        if not failing:
            break
    if restored:
        artifacts["dispositions.json"] = _canonical_json(dispositions)
        artifacts["restored_units.json"] = _canonical_json({"restored": restored})
    return failing, details, artifacts


def _evaluate_lane_r(
    bundle: Path, entry: Any, source: SourceSnapshot, dispositions: Mapping[str, Any]
) -> tuple[list[str], list[str], dict[str, bytes]]:
    from repo_presenter.readme.composition.authoring import authoring_tasks
    from repo_presenter.readme.composition.renderer import render_patch, render_readme
    from repo_presenter.readme.review.independent_reviewer import review_candidate
    from repo_presenter.readme.validation.blocking import (
        blocking_failures,
        validate_candidate,
    )
    from repo_presenter.readme.validation.failures import Candidate

    document = read_facts(bundle / "facts.json")
    plan = _load_json(bundle, "plan.json")
    units_name = (
        "content_units.coherent.json"
        if (bundle / "content_units.coherent.json").is_file()
        else "content_units.json"
    )
    units = _load_json(bundle, units_name)
    investigation = (
        _load_json(bundle, "investigation.json")
        if (bundle / "investigation.json").is_file()
        else {}
    )
    readme = render_readme(entry, document, plan, units, dispositions)
    failing: list[str] = []
    details: list[str] = []
    if source.readme is None:
        failing.append("SOURCE")
        details.append("SOURCE: the pinned revision has no README.md to judge preservation against")
        original = ""
    else:
        original = source.readme.decode("utf-8", errors="replace")
    candidate = Candidate(
        entry=entry,
        facts=document,
        plan=plan,
        units=units,
        dispositions=dispositions,
        readme=readme,
        original_readme=None,  # as in cascade._candidate: BC-01's digest is Lane L's to hold
        source_revision=document.source_revision,
        readme_sha256=None,
        tree_paths=list(source.tree_paths),
        tasks=authoring_tasks(entry, document, investigation, dispositions, plan),
        benchmark_readme=original,  # BC-17: the README the run read, at the sealed revision
    )
    with tempfile.TemporaryDirectory(prefix="recertify-") as empty:
        validation = validate_candidate(candidate, Path(empty), [])
    for check in blocking_failures(validation):
        failing.append(str(check["id"]))
        details.extend(f"{check['id']}: {detail}" for detail in check.get("details") or [])
    verdict = review_candidate(
        readme_text=readme,
        units=units.get("units", []),
        facts=document,
        dispositions=dispositions,
        original_readme=original,
    )
    for finding in verdict.blocking_findings:
        label = f"REVIEW:{finding.rule}"
        if label not in failing:
            failing.append(label)
        details.append(f"{label}: {finding.message}")
    artifacts = {
        "README.md": readme.encode("utf-8"),
        "README.patch.diff": render_patch(original, readme).encode("utf-8"),
        "validation.json": _canonical_json(validation),
    }
    return failing, details, artifacts


def _rerun_lane_l(
    bundle: Path, entry: Any, source: SourceSnapshot
) -> tuple[list[str], list[str], dict[str, bytes]]:
    """(failing check ids, details, re-derived artifacts) for a Lane L bundle: the correction
    engine (pure, deterministic) over the sealed live README, and its deterministic holdouts."""
    from repo_presenter.core.registry_entry_stub import RegistryEntryStub
    from repo_presenter.lane_l_review import holdout_findings, holdouts_document
    from repo_presenter.readme.composition.renderer import render_patch
    from repo_presenter.readme.correction.engine import correct, is_stable
    from repo_presenter.readme.correction.model import Context
    from repo_presenter.readme.correction.report import (
        canonical_json,
        corrections_document,
    )

    document: FactsDocument = read_facts(bundle / "facts.json")
    original_bytes = (bundle / "README.original.md").read_bytes()
    original = original_bytes.decode("utf-8")
    sealed_corrections = _load_json(bundle, "corrections.json")
    ctx = Context(
        entry=RegistryEntryStub(
            repository=entry.repository,
            family=entry.family,
            platform=entry.platform,
            ecosystem=entry.ecosystem,
        ),
        facts=document,
        readme=original,
        tree_paths=tuple(source.tree_paths),
        readme_path=str(sealed_corrections.get("readme_path") or "README.md"),
    )
    result = correct(ctx)
    deterministic, idempotent = is_stable(ctx, result)
    findings = holdout_findings(ctx, result, deterministic=deterministic)
    holdouts = holdouts_document(
        findings, idempotent=idempotent, source_revision=document.source_revision
    )
    failing = [
        check["id"]
        for check in holdouts["checks"]
        if check["verdict"] == "FAIL" and check["id"] != "L-06"  # L-06 is recorded, not blocking
    ]
    details = [
        f"{check['id']}: {detail}"
        for check in holdouts["checks"]
        if check["id"] in failing
        for detail in check.get("details") or []
    ]
    corrected = result.corrected.encode("utf-8")
    artifacts = {
        "README.md": corrected,
        "README.patch.diff": render_patch(original, result.corrected).encode("utf-8"),
        "corrections.json": canonical_json(
            corrections_document(
                ctx,
                result,
                original_sha256=_sha256(original_bytes),
                corrected_sha256=_sha256(corrected),
                deterministic=deterministic,
                idempotent=idempotent,
            )
        ),
        "holdouts.json": canonical_json(holdouts),
    }
    return failing, details, artifacts


def recertify_bundle(
    bundle: Path,
    lane: str,
    *,
    entry: Any,
    source: SourceSnapshot,
    current_version_set: str = "",
    seal_commit: str = "",
    restore: bool = False,
) -> Recertification:
    """Re-run the deterministic stages of ``bundle`` (one ``<revision>`` directory) with current
    code. Pure apart from reading ``bundle``; zero provider calls; writes nothing."""
    repository = entry.repository
    # A platform lane registers its ecosystem spec when its plugin is imported
    # (core/ecosystems.py SPECS); the generation path does that via plugin_for, so re-certification
    # must too, or every non-built-in ecosystem fails "no ecosystem spec registered" (dry run
    # 2026-11-06: Cells Cpp/Go/Java/Rust/TypeScript and PDF Java Lane R).
    from repo_presenter.extractors.platforms.registry import plugin_for

    with contextlib.suppress(Exception):  # an unknown ecosystem is reported by the check that needs it
        plugin_for(entry.ecosystem)

    def needs(revision: str, checks: Sequence[str], why: Sequence[str], sealed: str = "") -> Recertification:
        return Recertification(
            repository, lane, revision, OUTCOME_NEEDS_REPAIR, tuple(checks), tuple(why),
            sealed_version_set=sealed, current_version_set=current_version_set,
            seal_commit=seal_commit,
        )

    try:
        manifest = verify_bundle(bundle, lane)
    except Exception as exc:  # noqa: BLE001 -- unreadable evidence is a failing check, never a pass
        return needs(bundle.name, ["BUNDLE"], [f"BUNDLE: {type(exc).__name__}: {exc}"])
    if manifest is None:
        return needs(bundle.name, ["BUNDLE"], ["BUNDLE: no manifest"])
    revision = str(manifest.get("revision") or bundle.name)
    files = manifest.get("files", {})
    try:
        sealed_deps = _load_json(bundle, DEPENDENCIES_FILENAME) if DEPENDENCIES_FILENAME in files else None
        sealed_set = fingerprint(sealed_deps, lane) if isinstance(sealed_deps, dict) else ""
        review = _load_json(bundle, "review_verdict.json") if "review_verdict.json" in files else None
    except Exception as exc:  # noqa: BLE001
        return needs(revision, ["BUNDLE"], [f"BUNDLE: {type(exc).__name__}: {exc}"])
    if str(manifest.get("state")) not in GOOD_STATES:
        return needs(revision, ["SEAL"], [f"SEAL: manifest state {manifest.get('state')!r}"], sealed_set)
    if not _model_accept(review):
        return needs(revision, ["SEAL"], ["SEAL: the seal carries no model-reviewed ACCEPT"], sealed_set)
    try:
        if lane == LANE_L:
            failing, details, artifacts = _rerun_lane_l(bundle, entry, source)
        else:
            failing, details, artifacts = _rerun_lane_r(bundle, entry, source, restore=restore)
    except Exception as exc:  # noqa: BLE001 -- a stored output current code cannot read needs repair
        return needs(revision, ["RERUN"], [f"RERUN: {type(exc).__name__}: {exc}"], sealed_set)
    readme = artifacts["README.md"]
    stored = (bundle / "README.md").read_bytes() if (bundle / "README.md").is_file() else b""
    return Recertification(
        repository, lane, revision,
        OUTCOME_NEEDS_REPAIR if failing else OUTCOME_RECERTIFIED,
        tuple(failing), tuple(details),
        sealed_version_set=sealed_set,
        current_version_set=current_version_set,
        readme_changed=readme != stored,
        seal_commit=seal_commit,
        readme=readme,
        artifacts=artifacts,
    )


# --- writing the re-certified seal -------------------------------------------------------------


def recertified_dependencies(
    sealed: Mapping[str, Any], lane: str, prompts: Any, facts: FactsDocument,
    original_readme: bytes | None,
) -> dict[str, Any]:
    """The current version set's dependencies record for a re-certified seal: every mechanism
    key as current code would write it, the per-repository inputs (``source``, ``facts``) and the
    machine half of ``environment`` exactly as sealed (re-certification ran no extraction)."""
    from repo_presenter.readme.bundle.seal import current_dependencies_document

    revision = str((sealed.get("source") or {}).get("revision") or facts.source_revision)
    current = current_dependencies_document(
        lane=lane, source_revision=revision, facts=facts, prompts=prompts,
        original_readme=original_readme,
    )
    current["source"] = sealed.get("source", current["source"])
    current["facts"] = sealed.get("facts", current["facts"])
    sealed_env = sealed.get("environment")
    if isinstance(sealed_env, Mapping) and isinstance(current.get("environment"), dict):
        current["environment"] = {**dict(sealed_env), **current["environment"]}
        for key in ("python_version", "os", "toolchains"):
            if key in sealed_env:
                current["environment"][key] = sealed_env[key]
    return current


def write_recertified(
    bundle: Path, rec: Recertification, *, candidates_root: Path, prompts: Any,
    seal_commit: str = "",
) -> Path:
    """Write the re-certified seal as ``candidates_root/candidates/<slug>/[lane-l/]<revision>``
    (and its ``CURRENT``). The stored LLM outputs, ledger and review verdict are copied unchanged;
    the README (and its patch, and Lane L's correction record) are the re-derived ones."""
    if not rec.recertified:
        raise RecertifyError("only a RECERTIFIED result is written; NEEDS_REPAIR leaves the seal as it is")
    from repo_presenter.core.noop_proof import reconcile_ledger

    manifest = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    sealed_deps = _load_json(bundle, DEPENDENCIES_FILENAME)
    facts = read_facts(bundle / "facts.json")
    original = (bundle / "README.original.md").read_bytes() if rec.lane == LANE_L else None
    staged: dict[str, bytes] = {
        name: (bundle / name).read_bytes() for name in manifest.get("files", {})
    }
    staged.pop(RECERTIFICATION_FILENAME, None)
    for name in (
        "README.md", "README.patch.diff", "corrections.json", "holdouts.json",
        "dispositions.json", "restored_units.json",
    ):
        if name in rec.artifacts:
            staged[name] = rec.artifacts[name]
    dependencies = recertified_dependencies(sealed_deps, rec.lane, prompts, facts, original)
    staged[DEPENDENCIES_FILENAME] = _canonical_json(dependencies)
    current_set = fingerprint(dependencies, rec.lane)
    origin = {
        "commit": seal_commit or rec.seal_commit,
        "revision": rec.revision,
        "state": manifest.get("state"),
        "sealed_at": manifest.get("sealed_at"),
        "version_set": rec.sealed_version_set,
        "readme_sha256": _sha256((bundle / "README.md").read_bytes()),
        "dependencies_sha256": _sha256((bundle / DEPENDENCIES_FILENAME).read_bytes()),
        "no_op_proof": manifest.get("no_op_proof"),
    }
    staged[RECERTIFICATION_FILENAME] = _canonical_json(
        {
            "schema_version": 1,
            "recertify_version": RECERTIFY_VERSION,
            "outcome": rec.outcome,
            "recertified_at": _now(),
            "provider_calls": 0,
            "version_set": current_set,
            "readme_changed": rec.readme_changed,
            "llm_outputs_from": origin,
            "recertified_from": origin,
        }
    )
    new_manifest = {
        **{k: v for k, v in manifest.items() if k not in ("adopted", "update", "invalidated")},
        "state": "ACCEPTED",
        "files": {
            name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(staged.items())
        },
        "no_op_proof": None,
        "recertified_from": origin,
        "recertified_at": _now(),
    }
    repo_dir = candidates_root / CANDIDATES_DIRNAME / rec.repository.replace("/", "__")
    lane_root = lane_directory(repo_dir, rec.lane)
    target = lane_root / rec.revision
    staging = Path(tempfile.mkdtemp(prefix=".recertify-", dir=_mkdir(lane_root)))
    try:
        for name, data in staged.items():
            (staging / name).write_bytes(data)
        (staging / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(new_manifest))
        reconcile_ledger(new_manifest, staging / "ledger.jsonl")
        if verify_bundle(staging, rec.lane) is None:
            raise RecertifyError("the re-certified bundle does not verify")
        if target.is_dir():
            shutil.rmtree(target)
        staging.rename(target)
    finally:
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
    (lane_root / CURRENT_FILENAME).write_bytes(f"{rec.revision}\n".encode())
    return target


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def recertify_local(
    *, candidates_root: Path, entry: Any, lane: str, source: SourceSnapshot, prompts: Any,
    write: bool,
) -> Recertification:
    """Re-certify the CURRENT bundle of ``entry``/``lane`` under ``candidates_root`` (what
    ``present.py`` calls when preflight finds only mechanism versions changed); with ``write`` a
    RECERTIFIED result replaces the local bundle with the re-certified seal (the caller publishes
    it as a new commit on the bundle ref, so the original commit stays in its history)."""
    from repo_presenter.core.version_set import current_fingerprint

    lane_root = lane_directory(
        candidates_root / CANDIDATES_DIRNAME / entry.repository.replace("/", "__"), lane
    )
    revision = (lane_root / CURRENT_FILENAME).read_text(encoding="utf-8").strip()
    bundle = lane_root / revision
    rec = recertify_bundle(
        bundle, lane, entry=entry, source=source,
        current_version_set=current_fingerprint(lane, prompts),
    )
    if write and rec.recertified:
        with tempfile.TemporaryDirectory(prefix="recertify-src-") as tmp:
            copy = Path(tmp) / revision
            shutil.copytree(bundle, copy)
            write_recertified(copy, rec, candidates_root=candidates_root, prompts=prompts)
    return rec


# --- seal history: latest seal per ref, regeneration counts ------------------------------------


def regeneration_count(seals: Sequence[Any], lane: str) -> int:
    """How many times the LATEST seal's candidate was regenerated: seal commits of the same
    source revision whose LLM-stage artifact digests differ from the previous seal of that
    revision. A re-certified seal copies those artifacts unchanged, so it is never counted. Pure:
    ``seals`` are oldest-first objects with ``revision``, ``files`` ({name: {sha256}}) and
    ``error``."""
    usable = [s for s in seals if not getattr(s, "error", "")]
    if not usable:
        return 0
    revision = usable[-1].revision
    names = LLM_STAGE_ARTIFACTS.get(lane, ())
    previous: dict[str, Any] | None = None
    count = 0
    for seal in usable:
        if seal.revision != revision:
            continue
        digests = {n: (seal.files.get(n) or {}).get("sha256") for n in names}
        if previous is not None and digests != previous:
            count += 1
        previous = digests
    return count


SourceFetcher = Callable[[str, str], SourceSnapshot]


def recertify_history(
    history: Mapping[tuple[str, str], Sequence[Any]],
    *,
    entries: Mapping[str, Any],
    fetch: SourceFetcher,
    current: Mapping[str, str],
    restore: bool = False,
) -> list[Recertification]:
    """Re-certify the LATEST seal of every bundle ref in ``history`` (``bundle_store.seal_history``
    read with a ``scratch`` directory, so each record names its materialized ``bundle``). Dry:
    nothing is written. A source snapshot is fetched once per repository revision."""
    results: list[Recertification] = []
    sources: dict[tuple[str, str], SourceSnapshot | str] = {}
    for (repository, lane), seals in sorted(history.items()):
        if not seals:
            continue
        latest = seals[-1]
        regenerations = regeneration_count(seals, lane)
        base = {
            "repository": repository, "lane": lane, "revision": latest.revision,
            "outcome": OUTCOME_NEEDS_REPAIR, "current_version_set": current.get(lane, ""),
            "seal_commit": latest.commit, "regenerations": regenerations,
        }
        if latest.error or getattr(latest, "bundle", None) is None:
            results.append(Recertification(**base, failing_checks=("BUNDLE",),
                                           details=(f"BUNDLE: {latest.error or 'not materialized'}",)))
            continue
        entry = entries.get(repository)
        if entry is None:
            results.append(Recertification(**base, failing_checks=("REGISTRY",),
                                           details=("REGISTRY: not in data/registry.json",)))
            continue
        key = (repository, latest.revision)
        if key not in sources:
            try:
                sources[key] = fetch(repository, latest.revision)
            except Exception as exc:  # noqa: BLE001 -- unreadable source fails closed
                sources[key] = f"{type(exc).__name__}: {exc}"
        source = sources[key]
        if isinstance(source, str):
            results.append(Recertification(**base, failing_checks=("SOURCE",),
                                           details=(f"SOURCE: {source}",)))
            continue
        rec = recertify_bundle(
            latest.bundle, lane, entry=entry, source=source,
            current_version_set=current.get(lane, ""), seal_commit=latest.commit,
            restore=restore,
        )
        results.append(_with(rec, regenerations=regenerations))
    return results


def _with(rec: Recertification, **changes: Any) -> Recertification:
    from dataclasses import replace

    return replace(rec, **changes)


# --- the no-regression merge gate --------------------------------------------------------------


def baseline_document(results: Iterable[Recertification], previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The committed baseline: one row per latest seal. A justification already recorded for the
    same seal commit and the same outcome is kept."""
    kept = {
        (row.get("repository"), row.get("lane"), row.get("commit")): row
        for row in (previous or {}).get("seals", [])
    }
    rows = []
    for rec in sorted(results, key=lambda r: (r.repository, r.lane)):
        row = {
            "repository": rec.repository,
            "lane": rec.lane,
            "commit": rec.seal_commit,
            "revision": rec.revision,
            "outcome": rec.outcome,
            "failing_checks": sorted(rec.failing_checks),
            "regenerations": rec.regenerations,
        }
        old = kept.get((rec.repository, rec.lane, rec.seal_commit))
        if old and old.get("outcome") == rec.outcome and old.get("justification"):
            row["justification"] = old["justification"]
        rows.append(row)
    return {"schema_version": 1, "recertify_version": RECERTIFY_VERSION, "seals": rows}


def _rows(document: Mapping[str, Any] | None) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    return {
        (str(r.get("repository")), str(r.get("lane")), str(r.get("commit"))): r
        for r in (document or {}).get("seals", [])
    }


_CHECK_TOKEN = re.compile(r"[A-Za-z0-9_:.\-]+")


def _justification_names(justification: str) -> frozenset[str]:
    """The check ids a free-text justification names, as WHOLE tokens: ``BC-17`` names ``BC-17`` and
    nothing shorter (``BC-1`` is not "named" by a sentence about ``BC-17``), and trailing sentence
    punctuation does not hide an id."""
    return frozenset(
        token.rstrip(".:-").lstrip(".:-") for token in _CHECK_TOKEN.findall(justification)
    ) - {""}


def gate(
    results: Iterable[Recertification],
    baseline: Mapping[str, Any],
    base_baseline: Mapping[str, Any] | None = None,
) -> list[str]:
    """The problems that fail the merge gate (empty = pass). Pure.

    A regression is a seal the BASE baseline (the target branch's committed file; the working
    baseline when none is given) records RECERTIFIED that re-certifies NEEDS_REPAIR now. It is
    allowed only when the working baseline records that same seal NEEDS_REPAIR with a
    ``justification`` that names every newly failing check, each as a whole token.

    Judged per seal commit AND per (repository, lane): a lane whose base baseline holds a
    RECERTIFIED seal and whose latest seal is a different commit that does not certify has lost its
    count just the same, so that seal is held to the same justified-NEEDS_REPAIR rule (R10: a
    replacement can never be a way around the gate)."""
    base = _rows(base_baseline if base_baseline is not None else baseline)
    working = _rows(baseline)
    base_lane_recertified: dict[tuple[str, str], Mapping[str, Any]] = {}
    for (repository, lane, _commit), row in sorted(base.items()):
        if row.get("outcome") == OUTCOME_RECERTIFIED:
            base_lane_recertified.setdefault((repository, lane), row)
    problems: list[str] = []
    for rec in results:
        key = (rec.repository, rec.lane, rec.seal_commit)
        before = base.get(key)
        if before is not None:
            if before.get("outcome") != OUTCOME_RECERTIFIED or rec.recertified:
                continue
        else:
            before = base_lane_recertified.get((rec.repository, rec.lane))
            if before is None or rec.certified:
                continue
        newly = sorted(set(rec.failing_checks) - set(before.get("failing_checks") or []))
        row = working.get(key) or {}
        justification = str(row.get("justification") or "").strip()
        named = _justification_names(justification)
        justified = (
            row.get("outcome") == OUTCOME_NEEDS_REPAIR
            and bool(justification)
            and all(check in named for check in newly)
        )
        if justified:
            continue
        detail = "; ".join(d for d in rec.details if any(d.startswith(c) for c in newly))[:600]
        problems.append(
            f"{rec.repository} lane {rec.lane} seal {rec.seal_commit[:12]}: RECERTIFIED in the "
            f"baseline, NEEDS_REPAIR now; newly failing {', '.join(newly) or '-'}"
            + (f" ({detail})" if detail else "")
            + (" -- the baseline row has no justification naming every newly failing check"
               if row else " -- no baseline row records it")
        )
    return problems


# --- CLI -----------------------------------------------------------------------------------------


def _token() -> str | None:
    from repo_presenter.core.state.present_transaction import STATE_TOKEN_VARIABLE

    return os.environ.get(STATE_TOKEN_VARIABLE) or os.environ.get("GITHUB_TOKEN") or None


def portfolio_recertification(
    *, remote: str = "origin", token: str | None = None, registry: Path, prompts_dir: Path,
    lanes: Sequence[str] = LANES, repository: str | None = None,
    fetch: SourceFetcher | None = None,
) -> tuple[list[Recertification], dict[tuple[str, str], list[Any]]]:
    """Dry re-certification of every bundle ref's latest seal on ``remote`` (read-only)."""
    from repo_presenter.core.registry.loader import load_registry
    from repo_presenter.core.state.bundle_store import seal_history
    from repo_presenter.core.version_set import current_fingerprints

    entries = {entry.repository: entry for entry in load_registry(registry).entries}
    current = current_fingerprints(prompts_dir)
    with tempfile.TemporaryDirectory(prefix="recertify-all-") as tmp:
        scratch = Path(tmp)
        history = seal_history(remote=remote, token=token, scratch=scratch / "seals")
        history = {
            key: seals for key, seals in history.items()
            if key[1] in lanes and (repository is None or key[0] == repository)
        }
        fetcher = fetch or (lambda repo, rev: fetch_source(repo, rev, scratch / "src"))
        results = recertify_history(history, entries=entries, fetch=fetcher, current=current)
        # The records' ``bundle`` paths point into the scratch directory removed here.
        return results, {key: list(seals) for key, seals in history.items()}


def _print_table(results: Sequence[Recertification], out: Any = sys.stdout) -> None:
    print(f"{'repository':<52} {'lane':<4} {'seal':<12} {'outcome':<13} {'regen':<5} checks", file=out)
    for rec in results:
        print(
            f"{rec.repository:<52} {rec.lane:<4} {rec.seal_commit[:12]:<12} {rec.outcome:<13} "
            f"{rec.regenerations:<5} {', '.join(rec.failing_checks) or '-'}",
            file=out,
        )
    for rec in results:
        if rec.regenerations > 1:
            print(f"REGENERATED {rec.regenerations}x: {rec.repository} lane {rec.lane}", file=out)
    certified = {lane: sum(1 for r in results if r.lane == lane and r.certified) for lane in LANES}
    print(f"certified under current code: lane R {certified[LANE_R]}, lane L {certified[LANE_L]}", file=out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo_presenter.recertify", description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--repository")
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--lane", choices=LANES, default=None)
    parser.add_argument("--write", action="store_true",
                        help="publish each RECERTIFIED result as a new seal commit on its bundle ref")
    parser.add_argument(
        "--restore-lost-units", action="store_true",
        help="with --write: re-disposition the inherited units BC-05/BC-17 name as lost "
        "(readme.repair.restore_units; zero provider calls) before judging the seal",
    )
    parser.add_argument(
        "--no-publish", action="store_true",
        help="with --write: stage the re-certified seal under --out-dir and publish nothing",
    )
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=Path("data/registry.json"))
    parser.add_argument("--prompts", type=Path, default=Path("prompts"))
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--base-baseline", type=Path, default=None,
                        help="the target branch's baseline (the gate's 'before'); default: --baseline")
    args = parser.parse_args(argv)
    if args.repository and not args.lane:
        parser.error("--repository needs --lane")
    if (args.gate or args.write_baseline) and args.write:
        parser.error("--gate and --write-baseline are read-only against the bundle refs")
    token = _token()
    lanes = (args.lane,) if args.lane else LANES
    if args.write:
        return _write_mode(args, token, lanes)
    results, _history = portfolio_recertification(
        remote=args.remote, token=token, registry=args.registry, prompts_dir=args.prompts,
        lanes=lanes, repository=args.repository,
    )
    if args.json:
        print(json.dumps([r.report() for r in results], indent=2))
    else:
        _print_table(results)
    if args.write_baseline:
        previous = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.is_file() else None
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_bytes(_canonical_json(baseline_document(results, previous)))
        print(f"wrote {args.baseline} ({len(results)} seals)")
        return 0
    if args.gate:
        if not args.baseline.is_file():
            print(f"FAIL: no baseline at {args.baseline}")
            return 1
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        base = None
        if args.base_baseline is not None:
            # An explicitly passed base baseline that cannot be read must fail the gate: silently
            # falling back to the working baseline would let a PR vouch for itself.
            try:
                base = json.loads(args.base_baseline.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"FAIL: --base-baseline {args.base_baseline} is unreadable: {exc}")
                return 1
            if not isinstance(base, dict):
                print(f"FAIL: --base-baseline {args.base_baseline} is not a JSON object")
                return 1
        problems = gate(results, baseline, base)
        known = _rows(baseline)
        for rec in results:
            if (rec.repository, rec.lane, rec.seal_commit) not in known:
                print(f"note: {rec.repository} lane {rec.lane} seal {rec.seal_commit[:12]} is not in the baseline ({rec.outcome})")
        if problems:
            for problem in problems:
                print(f"REGRESSION: {problem}")
            print(f"FAIL: {len(problems)} seal(s) that re-certified in the baseline no longer do")
            return 1
        print(f"OK: no seal that re-certified in the baseline regressed ({len(results)} seals checked)")
        return 0
    if args.all:
        return 0
    return 0 if results and all(r.recertified for r in results) else 2


def _write_mode(args: Any, token: str | None, lanes: Sequence[str]) -> int:
    """Re-certify and publish each RECERTIFIED latest seal as a new seal commit."""
    from repo_presenter.core.llm.prompts import load_manifests
    from repo_presenter.core.registry.loader import load_registry
    from repo_presenter.core.state.bundle_store import publish_bundle, seal_history
    from repo_presenter.core.version_set import current_fingerprints

    entries = {entry.repository: entry for entry in load_registry(args.registry).entries}
    prompts = load_manifests(args.prompts)
    current = current_fingerprints(args.prompts)
    failed = 0
    with tempfile.TemporaryDirectory(prefix="recertify-write-") as tmp:
        scratch = Path(tmp)
        history = seal_history(remote=args.remote, token=token, scratch=scratch / "seals")
        history = {
            k: v for k, v in history.items()
            if k[1] in lanes and (args.repository is None or k[0] == args.repository)
        }
        results = recertify_history(
            history, entries=entries, current=current,
            fetch=lambda repo, rev: fetch_source(repo, rev, scratch / "src"),
            restore=bool(getattr(args, "restore_lost_units", False)),
        )
        _print_table(results)
        for rec in results:
            repaired = "restored_units.json" in rec.artifacts
            if not rec.recertified or (rec.sealed_by_current and not repaired):
                continue
            latest = history[(rec.repository, rec.lane)][-1]
            kept = getattr(args, "out_dir", None)
            out_root = (kept or scratch / "out") / f"{rec.lane}-{rec.repository.replace('/', '__')}"
            write_recertified(latest.bundle, rec, candidates_root=out_root, prompts=prompts,
                              seal_commit=latest.commit)
            if getattr(args, "no_publish", False):
                print(f"staged (not published): {out_root}")
                continue
            try:
                publication = publish_bundle(
                    rec.repository, rec.lane,
                    out_root / CANDIDATES_DIRNAME / rec.repository.replace("/", "__"),
                    remote=args.remote, token=token,
                )
            except PresenterError as exc:
                failed += 1
                print(f"publish failed: {rec.repository} lane {rec.lane}: {exc}")
                continue
            print(f"recertified seal: {publication.ref} {publication.commit[:12]} "
                  f"(from {rec.seal_commit[:12]})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
