"""Seal one cascade's output into a durable, content-addressed bundle, and prove the no-op.

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

Scope, deliberately bounded in two passes, exactly as ``core/noop_proof.py`` itself was (step 1:
the bundle-independent subset; step 3: the ledger-reconciliation subset):

- v1 (2026-10-26): only the FIRST seal (manifest state ``ACCEPTED``, ``no_op_proof`` always
  ``None``).
- v2 (2026-10-26, same day): the no-op proof itself -- a SECOND, later, fresh-process rerun
  whose artifacts reproduce the sealed ones byte for byte with zero provider calls moves the
  bundle to ``READY_FOR_PROPOSAL`` with a measured proof. Still explicitly NOT built: the
  update-adoption dance for a rerun whose artifacts genuinely DIFFER from what is sealed (the old
  repo's ``_record_update``/``_adopt_update``, which route a difference through
  ``invalidation.py``'s ``route()`` into ``VALID_UPDATE_AVAILABLE``/``INVALIDATED``) -- that needs
  the new ``ARTIFACT_SCOPES`` rows this module's own v1 docstring deferred, and is a materially
  different, larger decision (does a differing rerun silently re-seal, or wait for the owner?)
  than proving a byte-identical one. Calling :func:`seal_candidate` against a bundle whose
  artifacts differ from an already-proven ``READY_FOR_PROPOSAL`` seal, or whose rerun is not
  fresh or not zero-call, raises ``NotImplementedError`` naming this precisely, the same pattern
  this package's own ``recheck_bundle``/``recheck_portfolio`` (``readme/bundle/recheck.py``)
  already use for a scope not yet built, rather than faking a result nothing actually computed.

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
from repo_presenter.core.noop_proof import (
    Invocation,
    Measurement,
    identity_of_run_ref,
    ledger_totals,
    measure_invocation,
    reconcile_ledger,
    same_process,
)
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
    no_op_proof: dict[str, Any] | None = None


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


def _write_bundle(
    bundle: Path,
    staged: Mapping[str, bytes],
    *,
    inputs: SealInputs,
    state: str = STATE_ACCEPTED,
    proof: dict[str, Any] | None = None,
) -> SealResult:
    files = {
        name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(staged.items())
    }
    manifest = {
        "schema_version": 1,
        "repository": inputs.entry.repository,
        "revision": inputs.source_revision,
        "state": state,
        "sealed_at": _now(),
        "files": files,
        "provider_calls": inputs.provider_calls,
        "no_op_proof": proof,
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
    return SealResult(bundle=bundle, state=state, files=files, no_op_proof=proof)


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SealError(f"seal: unreadable bundle manifest {path}: {exc}") from exc
    return loaded if isinstance(loaded, dict) else None


def _differing_artifacts(staged: Mapping[str, bytes], bundle: Path) -> list[str]:
    """Staged artifact names whose bytes differ from what is already sealed, ignoring the files
    that carry a clock by design (``REPLAY_EXEMPT``) and cannot be compared this way."""
    differing = []
    for name, data in staged.items():
        if name in REPLAY_EXEMPT:
            continue
        existing = bundle / name
        if not existing.is_file() or existing.read_bytes() != data:
            differing.append(name)
    return sorted(differing)


def _fresh_after(prior_ref: object, inputs: SealInputs) -> bool:
    """Whether this invocation is a different process from the one ``prior_ref`` names. A
    reference that names no process (a bundle sealed before processes were identified) cannot
    establish freshness, so it is not fresh."""
    prior = identity_of_run_ref(prior_ref)
    return prior is not None and not same_process(prior, inputs.invocation.identity)


def _proof(prior_ref: Mapping[str, Any], inputs: SealInputs, measured: Measurement) -> dict[str, Any]:
    """The no-op proof record: every field is something this seal measured or compared. A
    caller reaches here only after freshness, byte-identity, and zero provider calls all hold
    (:func:`seal_candidate` withholds the proof otherwise); the record names both runs so an
    audit can repeat the comparison."""
    return {
        "proven_at": _now(),
        "fresh_process": True,
        "byte_identical": True,
        "provider_calls": measured.provider_calls,
        "first_run": dict(prior_ref),
        "rerun": {**inputs.invocation.run_ref(), **measured.to_dict()},
    }


def seal_candidate(inputs: SealInputs) -> SealResult:
    """Seal this cascade's output: the bundle's FIRST manifest (state ACCEPTED, no_op_proof
    None) when nothing is sealed yet, or -- when a LATER, fresh process reproduces an already-
    sealed bundle byte for byte with zero provider calls -- the measured no-op proof that moves
    it to READY_FOR_PROPOSAL. A rerun whose artifacts differ from a bundle that was never proven
    (still ACCEPTED) simply re-seals over it -- nothing has claimed a no-op yet, so there is no
    proof to protect (the old repo's own ``seal_candidate`` takes exactly this path: a changed,
    not-yet-``waiting_state`` bundle re-seals as ACCEPTED, proof withdrawn -- there never was
    one). Raises :class:`NotImplementedError` only when a rerun's artifacts differ from a bundle
    that WAS already proven (state READY_FOR_PROPOSAL with a recorded no_op_proof): preserving
    that existing proof while routing the new difference through invalidation.py's route() into
    VALID_UPDATE_AVAILABLE/INVALIDATED is a deliberate, not-yet-built follow-on (see this
    module's own docstring) -- never faked as a result nothing here actually computed. Also
    raises it when byte-identical artifacts are not fresh or not zero-call -- never faking the
    proof either."""
    bundle = bundle_directory(inputs.candidates_root, inputs.entry, inputs.source_revision)
    existing = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    staged = _staged_artifacts(inputs)
    if existing is None:
        return _write_bundle(bundle, staged, inputs=inputs)

    differing = _differing_artifacts(staged, bundle)
    was_proven = existing.get("state") == STATE_READY and existing.get("no_op_proof") is not None
    if differing:
        if not was_proven:
            # Nothing was proven yet -- a plain re-seal with the new content, same as the first
            # seal would have been had this content been the first one staged.
            return _write_bundle(bundle, staged, inputs=inputs)
        raise NotImplementedError(
            f"seal_candidate: {bundle} is already proven READY_FOR_PROPOSAL and this rerun's "
            f"own {', '.join(differing)} differ from the proven content. The update-adoption "
            "dance (preserving the existing proof while routing the new difference through "
            "invalidation.py's route() into VALID_UPDATE_AVAILABLE/INVALIDATED) is not built yet "
            "(see this module's own docstring) -- never silently re-sealed over a proven "
            "bundle's own difference nothing has judged."
        )
    if inputs.provider_calls != 0:
        raise NotImplementedError(
            f"seal_candidate: {bundle}'s artifacts are byte-identical to this rerun, but it made "
            f"{inputs.provider_calls} provider call(s) -- a no-op proof needs zero. The proof is "
            "withheld; re-run in a way that makes no provider calls to prove it."
        )
    if not _fresh_after(existing.get("sealed_by"), inputs):
        raise NotImplementedError(
            f"seal_candidate: {bundle}'s artifacts are byte-identical and this rerun made zero "
            "provider calls, but it is not a fresh process (the same process that sealed the "
            "bundle, or the bundle names no sealing process to be fresh from) -- a no-op proof "
            "needs a genuinely later, different process."
        )
    measured = measure_invocation(
        inputs.out_dir / "llm_cache" / LEDGER_BUNDLE_FILENAME, inputs.invocation.invocation_id
    )
    proof = _proof(existing["sealed_by"], inputs, measured)
    return _write_bundle(bundle, staged, inputs=inputs, state=STATE_READY, proof=proof)
