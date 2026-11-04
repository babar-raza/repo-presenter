"""Discovery: construct real ``Handoff`` objects from a repository's own extracted facts.

2026-11-04 (TC-010, follow-up directive §4: "complete issues lifecycle exercised end to end").
Nothing in this repository constructed a ``Handoff`` before this module (confirmed absent --
only tests built them by hand). This is new code, built directly on the already-ported,
already-tested ``Fact``/``FactsDocument`` model (``core/facts.py``) and ``Handoff`` model
(``issues/model.py``): a handoff is produced only for a fact whose polarity is ``CONTRADICTED``
and whose kind maps to one of ``model.DEFECT_CLASSES``, with the fact's own evidence copied
verbatim -- never invented, never guessed at. A fact kind with no mapping is skipped, not
forced into the nearest class.
"""

from __future__ import annotations

import hashlib

from repo_presenter.core.facts import FactsDocument
from repo_presenter.issues.model import DEFECT_CLASSES, EvidenceEntry, Handoff, TriggeringCheck

# Deliberately narrow and explicit: only fact kinds with an unambiguous mapping to one of
# model.DEFECT_CLASSES. "identity"/"package"/"import_path"/etc. have no defect-class
# counterpart and are never turned into a handoff by this module.
KIND_TO_DEFECT_CLASS: dict[str, str] = {
    "license": "LICENSE_MISMATCH",
    "example": "EXAMPLE_FAILS",
    "install_command": "INSTALL_FAILS",
    "build_test_asset": "BUILD_OR_TESTS_FAIL",
}
assert set(KIND_TO_DEFECT_CLASS.values()) <= set(DEFECT_CLASSES), (
    "discovery must only emit defect classes model.py already recognizes"
)


def _defect_fingerprint(fact_id: str, claim: str) -> str:
    """approval.py's handoff_id() requires defect_fingerprint to be a sha256 hex digest (its own
    HANDOFF_ID_PATTERN: ``<owner>__<name>__<64 hex>``) -- the readable fact id is preserved
    separately in triggering_check.id, never used here directly. Deterministic: the same fact
    id + claim always hashes to the same fingerprint; a changed claim is a different defect."""
    return hashlib.sha256(f"{fact_id}|{claim}".encode("utf-8")).hexdigest()


def discover_handoffs(document: FactsDocument, *, extractor_version: str) -> list[Handoff]:
    """Every ``CONTRADICTED`` fact whose kind maps to a known defect class becomes a real,
    evidence-backed, ``HANDOFF_PENDING`` ``Handoff`` -- no ``issue_ref``, no ``close_reason``
    (``model.py``'s own validation would refuse either on a fresh handoff). Deterministic: the
    same facts document always discovers the same handoffs, in fact order."""
    handoffs: list[Handoff] = []
    for fact in document.facts:
        if fact.polarity != "CONTRADICTED":
            continue
        defect_class = KIND_TO_DEFECT_CLASS.get(fact.kind)
        if defect_class is None:
            continue
        handoffs.append(
            Handoff(
                schema_version=1,
                repository=document.repository,
                source_revision=document.source_revision,
                defect_fingerprint=_defect_fingerprint(fact.id, fact.value),
                triggering_check=TriggeringCheck(
                    id=fact.id, version=extractor_version, causal_stage="EXTRACTING",
                ),
                evidence=tuple(
                    EvidenceEntry(path=e.path, detail=e.detail) for e in fact.evidence
                ),
                claim=fact.value,
                suggested_issue_title=f"{fact.kind}: {fact.value}"[:120],
                suggested_issue_body=(
                    f"Detected by repo-presenter's own extraction at {document.repository}@"
                    f"{document.source_revision}.\n\nClaim: {fact.value}\n\nEvidence: "
                    + "; ".join(e.path for e in fact.evidence)
                ),
                status="HANDOFF_PENDING",
                issue_ref=None,
                close_reason=None,
                defect_class=defect_class,
            )
        )
    return handoffs
