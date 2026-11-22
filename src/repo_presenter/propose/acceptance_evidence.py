"""Gate 3b's evidence (BL-731): what the official delivered count already verified about a candidate.

``propose.effect`` used to classify a candidate with ``sealed=True`` and the reviewer's calibration flag
only, so no candidate could ever leave ``sealed`` and every real write would have been refused
``ACCEPTANCE_NOT_CERTIFIED``. The acceptance contract (``acceptance.record``) reaches ``publication-ready``
only through ``audit_passed`` AND ``attested`` AND ``publication_ready_signal``; those three come from the
same place the portfolio count reads them: the ``acceptance-records-*.json`` files on the bot branches
``acceptance-record/*`` (``ops/checks/portfolio_delivery_count.read_attested_records``), each signed by the
hosted acceptance writer and verified with ``gh attestation verify``.

* :func:`read_acceptance_evidence` reads those files exactly as the count does (same fetcher, same schema and
  writer, same ``clean_control`` role, ``dry_run`` documents ignored) but keeps what the count discards: the
  record's own mechanism verdicts, canaries and ``audit_passed``, plus whether its attestation verified.
* :func:`evaluate_acceptance` runs the REAL acceptance classifier over every record for the candidate's
  revision and keeps the best state. ``publication_ready_signal`` is derived HERE, never read from the file:
  it is true only when the record's ``candidate_sha256`` equals the SHA-256 of the README bytes about to be
  written (``content_bound``, BL-189). A legacy revision-only record still counts as accepted in the delivery
  count (R10) but is never publication-ready: it classifies ``independently-accepted`` and the gate refuses.
* The reviewer's calibration (frozen, R33) is not an input. The independent review's own ACCEPT stays a
  separate gate in the effect.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_presenter.acceptance.record import (
    CANDIDATE_DIGEST_FIELD,
    CONTENT_BOUND,
    STATES,
    acceptance_binding,
    candidate_sha256,
    verify_attestation,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DELIVERY_COUNT = REPO_ROOT / "ops" / "checks" / "portfolio_delivery_count.py"

#: ``classify``-shaped callable (``acceptance.record.classify``); injected so tests can use the real one.
ClassifyFn = Callable[..., str]


@dataclass(frozen=True)
class AttestedAcceptance:
    """One ``clean_control`` record from the hosted acceptance writer, as read for one cell."""

    repository: str
    lane: str
    revision: str
    #: The record's ``candidate_sha256`` field: ``None`` when absent (a legacy record), else the raw value.
    candidate_sha256: Any = None
    deterministically_validated: bool = False
    mechanism_verdicts: Mapping[str, bool] = field(default_factory=dict)
    canaries: Mapping[str, bool] = field(default_factory=dict)
    audit_passed: bool = False
    #: ``gh attestation verify`` succeeded for the file this record came from (signed by the acceptance writer on main).
    attested: bool = False


@dataclass(frozen=True)
class AcceptanceVerdict:
    state: str
    binding: str  # content_bound | revision_only | digest_mismatch | digest_malformed | "" (no record at the revision)
    detail: str
    records_considered: int = 0


def _delivery_count() -> Any:
    spec = importlib.util.spec_from_file_location("_propose_portfolio_delivery_count", DELIVERY_COUNT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {DELIVERY_COUNT}")
    if spec.name in sys.modules:
        return sys.modules[spec.name]
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def read_acceptance_evidence(
    repository: str,
    lane: str,
    *,
    remote: str = "origin",
    fetcher: Callable[[], list[tuple[str, str, bytes]]] | None = None,
    gh_runner: Any = None,
) -> tuple[AttestedAcceptance, ...]:
    """Every ``clean_control`` record for ``(repository, lane)`` on the record branches, each carrying whether
    its file's attestation verified. Same source and acceptance rules as the portfolio count; nothing here raises:
    an unreadable branch, file, record or attestation simply yields no (or an unattested) record."""
    try:
        count = _delivery_count()
        files = (fetcher or (lambda: count.fetch_record_files(remote)))()
        schema, writer = count.RECORDS_SCHEMA, count.ACCEPTANCE_WRITER
        runner = gh_runner or count._gh_with_repo
    except Exception:  # noqa: BLE001 -- an unreadable source is "no evidence", never a pass
        return ()
    found: list[AttestedAcceptance] = []
    with tempfile.TemporaryDirectory(prefix="propose-acc-") as tmp:
        for index, (_branch, name, blob) in enumerate(files):
            try:
                document = json.loads(blob)
                if document.get("schema") != schema or document.get("dry_run") is not False:
                    continue
                rows = [
                    r for r in document["records"]
                    if isinstance(r, dict) and r.get("role") == "clean_control"
                    and r.get("repository") == repository and r.get("lane") == lane
                ]
                if not rows:
                    continue
                path = Path(tmp) / f"{index}-{Path(name).name}"
                path.write_bytes(blob)
                attested = verify_attestation(path, writer, "refs/heads/main", runner=runner)
                for r in rows:
                    digest = r[CANDIDATE_DIGEST_FIELD] if CANDIDATE_DIGEST_FIELD in r else None
                    if CANDIDATE_DIGEST_FIELD in r and digest is None:
                        digest = ""  # an explicit null is malformed, not legacy (as the count)
                    found.append(
                        AttestedAcceptance(
                            repository=repository,
                            lane=lane,
                            revision=str(r.get("revision", "")),
                            candidate_sha256=digest,
                            deterministically_validated=r.get("deterministically_validated") is True,
                            mechanism_verdicts=dict(r.get("mechanism_verdicts") or {}),
                            canaries=dict(r.get("canaries") or {}),
                            audit_passed=r.get("audit_passed") is True,
                            attested=attested,
                        )
                    )
            except Exception:  # noqa: BLE001 -- a malformed record contributes nothing
                continue
    return tuple(found)


def evaluate_acceptance(
    records: Sequence[AttestedAcceptance],
    *,
    repository: str,
    lane: str,
    revision: str,
    readme_bytes_sha256: str,
    classify_fn: ClassifyFn,
) -> AcceptanceVerdict:
    """The best acceptance state any record gives the candidate sealed at ``revision`` whose README bytes
    hash to ``readme_bytes_sha256``. No record (or none for this revision) is the bare ``sealed`` state."""
    at_revision = [r for r in records if r.revision and r.revision == revision]
    if not at_revision:
        return AcceptanceVerdict(
            state=classify_fn(repository, lane, sealed=True),
            binding="",
            detail=f"no attested M9 acceptance record at revision {revision[:12] or 'unknown'}",
            records_considered=len(records),
        )
    best_state, best_binding = "", ""
    for record in at_revision:
        binding = acceptance_binding(record.candidate_sha256, readme_bytes_sha256)
        state = classify_fn(
            repository,
            lane,
            sealed=True,
            deterministically_validated=record.deterministically_validated,
            mechanism_verdicts=dict(record.mechanism_verdicts),
            canaries=dict(record.canaries),
            audit_passed=record.audit_passed,
            attestation_verified=record.attested,
            publication_ready_signal=binding == CONTENT_BOUND,
        )
        # the higher state wins; at an equal state a content-bound record is the one reported
        if (
            not best_state
            or STATES.index(state) > STATES.index(best_state)
            or (state == best_state and binding == CONTENT_BOUND and best_binding != CONTENT_BOUND)
        ):
            best_state, best_binding = state, binding
    note = {
        CONTENT_BOUND: "the record is bound to the README bytes to be written",
        "revision_only": "a legacy record covers the revision only, not the README bytes (not publication-ready)",
        "digest_mismatch": "the record audited other README bytes than the ones to be written",
        "digest_malformed": "the record carries a malformed candidate digest",
    }.get(best_binding, "")
    return AcceptanceVerdict(best_state, best_binding, note, len(at_revision))


def bytes_sha256(text: str) -> str:
    """SHA-256 of ``text`` as UTF-8 bytes (use the sealed file's own bytes when you have them)."""
    return candidate_sha256(text.encode("utf-8"))
