"""Seal one cascade's output into a durable, content-addressed bundle (first seal only).

ADAPT (not ported verbatim -- design recorded in
``plans/PLAN_bundle_integrity_and_noop_proof.md``'s "seal.py v1 design" section, 2026-10-26) from
the old repository-presenter project's ``components/readme/bundle/seal.py`` (1,203 lines). That
module assumes one ``transaction`` directory holding every artifact together, one ledger per
transaction, and the old repo's own ``validation.json``/``review.json`` pair. This repository has
none of those: its real evidence splits across ``scripts/_lane_r_output/<repo>/`` (the cascade's
own output, including the one shared ledger ``cascade.run_cascade`` now writes) and
``evidence/build/<phase>/<repo>/facts.json`` (the durable, committed evidence store) -- and it
has ``review_verdict.json`` (``readme.review.independent_reviewer``), not the old repo's
consolidated 21-check validation.json.

Scope of v1, deliberately bounded: only the FIRST seal of a cascade's output (manifest state
``ACCEPTED``, ``no_op_proof`` always ``None``). The old repo's re-seal / update-adoption / no-op-
proof-adoption dance (its own ``_record_update``/``_adopt_update``/``_proof``) needs a SECOND
fresh-process rerun to compare against -- a separate, later step, exactly as
``core/noop_proof.py`` itself was staged in two passes (step 1: the bundle-independent subset;
step 3: the ledger-reconciliation subset). Calling :func:`seal_candidate` against an already-
sealed bundle raises ``NotImplementedError`` naming this, the same pattern this package's own
``recheck_bundle``/``recheck_portfolio`` (``readme/bundle/recheck.py``) already use for a scope
not yet built, rather than faking a result nothing actually computed.

The bundle lives at ``candidates/<owner>__<name>/<revision>/`` at the repository root (matching
``recheck.py``'s own already-ported ``receipt_path()``), committed to git -- unlike
``scripts/_lane_r_output/``, which stays gitignored working output.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.core.errors import PresenterError
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.ledger import parse_records
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.core.noop_proof import Invocation, ledger_totals, reconcile_ledger
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.secrets import ConfiguredSecret, scan_for_secrets
from repo_presenter.core.toolchains import toolchain_fingerprint
from repo_presenter.readme.composition.authoring import NORMALISATION_VERSION
from repo_presenter.readme.composition.components.shell import SHELL_VERSION
from repo_presenter.readme.composition.renderer import RENDERER_VERSION
from repo_presenter.readme.evidence.facts.inherited import INHERITED_UNITS_VERSION
from repo_presenter.readme.review.independent_reviewer import REVIEWER_LOGIC_VERSION

CANDIDATES_DIRNAME = "candidates"
BUNDLE_MANIFEST_NAME = "manifest.json"
CURRENT_FILENAME = "CURRENT"
DEPENDENCIES_FILENAME = "dependencies.json"
# The ledger's name INSIDE the sealed bundle -- this repository's own scripts (and
# cascade.run_cascade) always write it as "ledger.jsonl", never core/llm/ledger.py's own
# LEDGER_FILENAME="calls.jsonl" constant (that constant was ported from the old repo, where the
# sealed ledger really is named calls.jsonl; no script in this repository has ever used it for
# its own workspace ledger path).
LEDGER_BUNDLE_FILENAME = "ledger.jsonl"
STATE_ACCEPTED = "ACCEPTED"
STATE_READY = "READY_FOR_PROPOSAL"

# Bundle filename -> required. README.md's own source picks README.coherent.md, falling back to
# README.rendered.md when coherence was never run for this repository.
REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "README.md",
    "README.patch.diff",
    "facts.json",
    "dispositions.json",
    "plan.json",
    "review_verdict.json",
    LEDGER_BUNDLE_FILENAME,
)
OPTIONAL_ARTIFACTS: tuple[str, ...] = (
    "investigation.json",
    "content_units.json",
    "content_units.coherent.json",
)
REPLAY_EXEMPT = frozenset({LEDGER_BUNDLE_FILENAME, BUNDLE_MANIFEST_NAME})


class SealError(PresenterError):
    """The cascade's output cannot be sealed as a bundle."""

    exit_code = 1


class BundleLeakError(SealError):
    """A configured secret's value appears in the bundle."""

    exit_code = 3


@dataclass(frozen=True)
class SealInputs:
    """Everything one first seal needs, read from the cascade's own real output locations."""

    entry: RegistryEntry
    source_revision: str
    facts: FactsDocument
    prompts: PromptRegistry
    out_dir: Path
    facts_path: Path
    candidates_root: Path
    provider_calls: int
    invocation: Invocation
    secrets: Sequence[ConfiguredSecret] = ()


@dataclass(frozen=True)
class SealResult:
    bundle: Path
    state: str
    files: dict[str, dict[str, Any]]


def bundle_directory(candidates_root: Path, entry: RegistryEntry, revision: str) -> Path:
    return candidates_root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / revision


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def environment_dependencies() -> dict[str, Any]:
    """What answered this cascade's extraction and rendering: the Python version, OS, this
    codebase's own extractor/inherited-unit-inventory versions, and every machine toolchain a
    verifier resolves. A change in any of these is a ``facts``-scope input (invalidation.py)."""
    return {
        "python_version": platform.python_version(),
        "os": platform.system(),
        "inherited_units_version": INHERITED_UNITS_VERSION,
        "toolchains": toolchain_fingerprint(),
    }


def code_dependencies(prompts: PromptRegistry) -> dict[str, Any]:
    """The consumed-input classes the running code itself owns: prompts, template components.
    Deliberately does NOT invent an acceptance-profile, validator, or model-fallback-chain
    concept -- none exists in this repository yet (see this module's own docstring)."""
    return {
        "prompts": {
            name: {
                "sha256": prompts[name].sha256,
                "version": prompts[name].manifest.version,
                "model_route": prompts[name].manifest.model_route,
            }
            for name in sorted(prompts.hashes())
        },
        "components": {
            "shell": SHELL_VERSION,
            "renderer": RENDERER_VERSION,
            "normalisation": NORMALISATION_VERSION,
            "reviewer_logic": REVIEWER_LOGIC_VERSION,
        },
    }


def dependencies_document(inputs: SealInputs) -> dict[str, Any]:
    """Exactly the inputs this candidate consumed, so a future recheck can tell what changed."""
    code = code_dependencies(inputs.prompts)
    return {
        "schema_version": 1,
        "source": {"revision": inputs.source_revision},
        "environment": environment_dependencies(),
        "facts": {
            fact.id: _sha256(_canonical_json(asdict(fact)))
            for fact in sorted(inputs.facts.facts, key=lambda fact: fact.id)
        },
        "prompts": code["prompts"],
        "components": code["components"],
    }


def _readme_source(out_dir: Path) -> Path:
    coherent = out_dir / "README.coherent.md"
    if coherent.is_file():
        return coherent
    rendered = out_dir / "README.rendered.md"
    if rendered.is_file():
        return rendered
    raise SealError(f"seal: no README.coherent.md or README.rendered.md under {out_dir}")


def _artifact_sources(inputs: SealInputs) -> dict[str, Path]:
    """bundle filename -> the real file it is read from, across this repository's two real
    evidence locations (``out_dir`` and ``facts_path``'s own directory)."""
    out_dir = inputs.out_dir
    sources = {
        "README.md": _readme_source(out_dir),
        "README.patch.diff": out_dir / "README.patch.diff",
        "facts.json": inputs.facts_path,
        "dispositions.json": out_dir / "dispositions.json",
        "plan.json": out_dir / "plan.json",
        "review_verdict.json": out_dir / "review_verdict.json",
        LEDGER_BUNDLE_FILENAME: out_dir / "llm_cache" / LEDGER_BUNDLE_FILENAME,
        "investigation.json": out_dir / "investigation.json",
        "content_units.json": out_dir / "content_units.json",
        "content_units.coherent.json": out_dir / "content_units.coherent.json",
    }
    return sources


def _staged_artifacts(inputs: SealInputs) -> dict[str, bytes]:
    sources = _artifact_sources(inputs)
    staged: dict[str, bytes] = {}
    for name in REQUIRED_ARTIFACTS:
        path = sources[name]
        if not path.is_file():
            raise SealError(f"seal: the cascade output has no {name} (expected at {path})")
        staged[name] = path.read_bytes()
    for name in OPTIONAL_ARTIFACTS:
        path = sources[name]
        if path.is_file():
            staged[name] = path.read_bytes()
    staged[DEPENDENCIES_FILENAME] = _canonical_json(dependencies_document(inputs))
    return staged


def _write_bundle(bundle: Path, staged: Mapping[str, bytes], *, inputs: SealInputs) -> SealResult:
    files = {
        name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(staged.items())
    }
    manifest = {
        "schema_version": 1,
        "repository": inputs.entry.repository,
        "revision": inputs.source_revision,
        "state": STATE_ACCEPTED,
        "sealed_at": _now(),
        "files": files,
        "provider_calls": inputs.provider_calls,
        "no_op_proof": None,
        "sealed_by": inputs.invocation.run_ref(),
        "ledger_totals": ledger_totals(
            parse_records(staged[LEDGER_BUNDLE_FILENAME].decode("utf-8"), LEDGER_BUNDLE_FILENAME)
        ),
    }
    bundle.parent.mkdir(parents=True, exist_ok=True)
    # Staged to a sibling temp directory and scanned for secrets before anything under `bundle`
    # itself -- or CURRENT -- is touched: a leak must leave no trace on disk (seal.py's own old
    # docstring, TB-06, carried over verbatim as the one safety property that must not regress).
    staging = Path(tempfile.mkdtemp(dir=bundle.parent, prefix=f".{bundle.name}.staging-"))
    try:
        for name, data in staged.items():
            (staging / name).write_bytes(data)
        (staging / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(manifest))
        reconcile_ledger(manifest, staging / LEDGER_BUNDLE_FILENAME)
        leaks = scan_for_secrets(staging, inputs.secrets)
        if leaks:
            names = ", ".join(sorted({f"{leak.variable} in {leak.path.name}" for leak in leaks}))
            raise BundleLeakError(f"seal: a configured secret appears in the bundle: {names}")
        if bundle.is_dir():
            shutil.rmtree(bundle)
        staging.rename(bundle)
    finally:
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
    current = bundle.parent / CURRENT_FILENAME
    pointer = f"{inputs.source_revision}\n".encode()
    if not current.is_file() or current.read_bytes() != pointer:
        current.write_bytes(pointer)
    return SealResult(bundle=bundle, state=STATE_ACCEPTED, files=files)


def seal_candidate(inputs: SealInputs) -> SealResult:
    """Seal this cascade's output as the bundle's FIRST manifest (state ACCEPTED, no_op_proof
    None). Raises :class:`NotImplementedError` against an already-sealed bundle: re-seal and the
    no-op-proof-adoption dance are a deliberate, not-yet-built follow-on (see this module's own
    docstring) -- never faked as a result nothing here actually computed."""
    bundle = bundle_directory(inputs.candidates_root, inputs.entry, inputs.source_revision)
    if (bundle / BUNDLE_MANIFEST_NAME).is_file():
        raise NotImplementedError(
            f"seal_candidate: {bundle} is already sealed. Re-seal, update-adoption, and the "
            "no-op-proof-adoption dance are not ported in this v1 (see readme.bundle.seal's own "
            "module docstring and plans/PLAN_bundle_integrity_and_noop_proof.md's 'seal.py v1 "
            "design' section) -- this needs a second fresh-process rerun to compare against, a "
            "separate, later step."
        )
    staged = _staged_artifacts(inputs)
    return _write_bundle(bundle, staged, inputs=inputs)
