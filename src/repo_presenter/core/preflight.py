"""P5 preflight: decide, BEFORE a provider call, whether a lane's prior sealed output is still
current -- not just prove it was current after the fact (``core/noop_proof.py``'s job).

2026-11-04 (follow-up directive §8). Both lanes share this module. It is built directly on the
already-ported, already-tested ``readme/bundle/evaluation.py``/``invalidation.py`` (``evaluate``/
``route``), which this repository has had unused since they were first pulled in: nothing ever
called them before a provider call decided whether to happen.

**A real, confirmed prerequisite gap, not glossed over**: ``evaluation.py``'s own docstring
states plainly that ``readme/bundle/seal.py`` -- the component that would actually PRODUCE a
real ``dependencies.json`` record for a sealed bundle (``upstream_dependencies``/
``code_dependencies``) -- was never ported into this repository. There is therefore no committed
bundle today whose "sealed" side of a real ``evaluate()`` comparison is genuine, full-fidelity
data; a preflight gate that fabricated one to look complete would be exactly the "refuse stale/
corrupt evidence instead of fabricating currency" failure mode the directive explicitly warns
against. This module does NOT do that.

What this module DOES do, honestly: ``source_unchanged_since_last_seal`` is a real, narrow,
safe currency check using only what is genuinely available without that missing producer -- the
sealed bundle's own manifest already records the exact source revision it was built against
(``core/candidates.py``'s bundle manifest, read via ``load_current_bundle_manifest``). If the
current clone's revision matches, the source class of ``evaluate()``'s own table is provably
unchanged; everything else (prompts, policy, model version, detector versions) is NOT yet
checked here, because nothing in this repository can yet report the current state of those
classes against a sealed record that was never written. ``preflight_decision`` returns that
scope explicitly rather than claiming a false green for scopes it cannot check.

**Not wired into ``present.py`` this pass.** Wiring a provably-correct skip into the hosted
pipeline requires either porting ``seal.py``'s dependencies.json producer (so the full
``evaluate()`` comparison means something), or independently verifying ``present_transaction.py``'s
``classify_present_outcome`` contract tolerates a pipeline that sealed nothing new this run (not
yet done). This module is real, tested, and ready to be called from either lane's entry point
once one of those two things is true -- see ``tests/core/test_preflight.py`` for warm/cold/
cache-evicted/changed-source coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from repo_presenter.core.candidates import CANDIDATES_DIRNAME, CURRENT_FILENAME, lane_directory


@dataclass(frozen=True)
class PreflightDecision:
    can_skip_provider_call: bool
    reason: str
    checked_scopes: tuple[str, ...]
    unchecked_scopes: tuple[str, ...]


# The only evaluate()-table classes this module can genuinely assess without seal.py's
# dependencies.json producer. Kept as an explicit, named constant -- not inferred -- so a future
# reader (or test) can see exactly what "checked" means here and is never misled into assuming
# full consumed-scope coverage.
CHECKED_SCOPES: tuple[str, ...] = ("source",)
UNCHECKED_SCOPES: tuple[str, ...] = (
    "environment", "facts", "prompts", "detectors", "contract_version",
    "components", "validators", "acceptance_profile_version", "policy",
)


def load_current_bundle_manifest(candidates_root: Path, repository: str, lane: str) -> dict | None:
    """Read the sealed bundle's own manifest.json via its CURRENT pointer, or None if no sealed
    bundle exists for this repository/lane yet (cold start -- never a reason to fail, only to
    proceed with the full pipeline, exactly as today)."""
    slug = repository.replace("/", "__")
    lane_root = lane_directory(candidates_root / CANDIDATES_DIRNAME / slug, lane)
    current_file = lane_root / CURRENT_FILENAME
    if not current_file.exists():
        return None
    revision = current_file.read_text(encoding="utf-8").strip()
    if not revision:
        return None
    manifest_path = lane_root / revision / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None  # corrupt manifest is never treated as current -- fail safe, not fabricated


def preflight_decision(
    *, candidates_root: Path, repository: str, lane: str, current_source_revision: str,
) -> PreflightDecision:
    """The one entry point either lane would call before a provider call. Conservative by
    construction: can_skip_provider_call is True only for the narrow, fully-checked case; every
    other case (no prior bundle, corrupt manifest, source changed, or -- always, honestly --
    the unchecked scopes) returns False, matching today's existing behavior exactly (full
    pipeline runs) rather than a guessed skip."""
    manifest = load_current_bundle_manifest(candidates_root, repository, lane)
    if manifest is None:
        return PreflightDecision(
            can_skip_provider_call=False,
            reason="no prior sealed bundle for this repository/lane -- nothing to compare against",
            checked_scopes=(), unchecked_scopes=CHECKED_SCOPES + UNCHECKED_SCOPES,
        )
    sealed_revision = manifest.get("source_revision")
    if sealed_revision != current_source_revision:
        return PreflightDecision(
            can_skip_provider_call=False,
            reason=f"source revision changed: {sealed_revision!r} -> {current_source_revision!r}",
            checked_scopes=CHECKED_SCOPES, unchecked_scopes=UNCHECKED_SCOPES,
        )
    # Source matches -- but prompts/policy/model/detector/contract scopes are NOT checkable yet
    # (the real prerequisite gap this module's docstring names). Never claim a skip is safe for
    # a scope nothing here can actually evaluate.
    return PreflightDecision(
        can_skip_provider_call=False,
        reason=(
            "source revision unchanged, but prompts/policy/model/detector/contract scopes "
            "cannot yet be checked (seal.py's dependencies.json producer was never ported) -- "
            "proceeding with the full pipeline rather than fabricating a currency claim"
        ),
        checked_scopes=CHECKED_SCOPES, unchecked_scopes=UNCHECKED_SCOPES,
    )
