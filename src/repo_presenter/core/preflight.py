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

**TC-008a update (2026-11-04).** ``seal.py`` DOES produce a full ``dependencies.json`` (it was
ported before this card; the paragraph above describes the state when TC-008 was written), and
``current_dependencies_document`` there builds the record a seal made now would write from the
same code path. When a caller passes that as ``current_dependencies``, ``preflight_decision``
runs the whole ``evaluate()`` comparison and returns ``can_skip_provider_call=True`` ONLY when

* the lane's CURRENT bundle exists and passes ``verify_bundle`` (every file's digest, the ledger
  totals, the lane) -- any corrupt or unreadable evidence fails closed (no skip);
* its ``dependencies.json`` is a readable object, and its manifest state is
  ``READY_FOR_PROPOSAL`` (an ``ACCEPTED`` bundle still needs the second, fresh zero-call run that
  proves the no-op; skipping would withhold that proof forever);
* ``evaluate(sealed, current)`` reports no change in ANY consumed scope.

Only a scope a candidate actually consumed can reopen it (``evaluate`` compares the sealed
record's own keys), so an unrelated input never forces a call (consumed-scope invalidation, never
a global reseal). Without ``current_dependencies`` the legacy source-revision-only behavior
stays: never skip.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    DEPENDENCIES_FILENAME,
    lane_directory,
    verify_bundle,
)
from repo_presenter.readme.bundle.evaluation import evaluate

#: The only manifest state whose no-op has been PROVEN by a fresh zero-call rerun.
PROVEN_STATE = "READY_FOR_PROPOSAL"


@dataclass(frozen=True)
class PreflightDecision:
    can_skip_provider_call: bool
    reason: str
    checked_scopes: tuple[str, ...]
    unchecked_scopes: tuple[str, ...]
    changed: tuple[str, ...] = ()


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


def _full_decision(
    *,
    candidates_root: Path,
    repository: str,
    lane: str,
    current_source_revision: str,
    current_dependencies: dict[str, Any],
) -> PreflightDecision:
    """The fully-checked comparison. Every non-skip branch is a fail-closed answer."""
    all_scopes = CHECKED_SCOPES + UNCHECKED_SCOPES

    def no(reason: str, changed: tuple[str, ...] = ()) -> PreflightDecision:
        return PreflightDecision(False, reason, (), all_scopes, changed)

    slug = repository.replace("/", "__")
    lane_root = lane_directory(candidates_root / CANDIDATES_DIRNAME / slug, lane)
    current_file = lane_root / CURRENT_FILENAME
    if not current_file.is_file():
        return no("no prior sealed bundle for this repository/lane -- nothing to compare against")
    try:
        revision = current_file.read_text(encoding="utf-8").strip()
        if not revision:
            return no("the CURRENT pointer is empty -- treated as no usable evidence")
        bundle = lane_root / revision
        manifest = verify_bundle(bundle, lane)
        if manifest is None:
            return no("the CURRENT pointer names a bundle with no manifest -- evidence missing")
        sealed = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        if not isinstance(sealed, dict) or not isinstance(sealed.get("source"), dict):
            return no("the sealed dependencies.json is not a dependency record -- failing closed")
        state = manifest.get("state")
        evaluation = evaluate(sealed, current_dependencies)
    except Exception as exc:  # noqa: BLE001 -- corrupt/unreadable evidence must never skip
        return no(f"sealed evidence is corrupt or unreadable ({type(exc).__name__}: {exc}) -- failing closed")
    changed = tuple(change.dependency for change in evaluation.changes)
    if changed:
        return PreflightDecision(
            False,
            f"consumed input changed: {', '.join(changed)} (earliest reopened stage "
            f"{evaluation.earliest})",
            CHECKED_SCOPES + UNCHECKED_SCOPES, (), changed,
        )
    if sealed.get("source", {}).get("revision") != current_source_revision:
        return no(
            f"sealed source revision {sealed.get('source', {}).get('revision')!r} is not the "
            f"current {current_source_revision!r}"
        )
    if state != PROVEN_STATE:
        return PreflightDecision(
            False,
            f"nothing consumed changed, but the sealed bundle is {state!r}, not {PROVEN_STATE}: "
            "the rerun that proves the no-op has not happened yet, so the pipeline runs (it "
            "replays from the call store)",
            all_scopes, (), (),
        )
    return PreflightDecision(
        True,
        f"every consumed scope equals the sealed record of a proven bundle ({revision}); "
        "no provider call is needed",
        all_scopes, (), (),
    )


def preflight_decision(
    *, candidates_root: Path, repository: str, lane: str, current_source_revision: str,
    current_dependencies: dict[str, Any] | None = None,
) -> PreflightDecision:
    """The one entry point either lane calls before a provider call. Conservative by
    construction: can_skip_provider_call is True only when ``current_dependencies`` is given and
    every consumed scope compares equal against a verified, proven sealed bundle; every other case
    (no prior bundle, corrupt evidence, any changed scope, an unproven bundle, or no current
    dependencies supplied) returns False, so the full pipeline runs exactly as it always did."""
    if current_dependencies is not None:
        return _full_decision(
            candidates_root=candidates_root, repository=repository, lane=lane,
            current_source_revision=current_source_revision,
            current_dependencies=current_dependencies,
        )
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
            "cannot yet be checked because the caller supplied no current_dependencies -- "
            "proceeding with the full pipeline rather than fabricating a currency claim"
        ),
        checked_scopes=CHECKED_SCOPES, unchecked_scopes=UNCHECKED_SCOPES,
    )
