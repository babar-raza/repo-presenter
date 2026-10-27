"""The independent reviewer's finding model (plan D1, D2; mission section 7 step 7 and 11).

A finding is BLOCKING unless a registered clearance proves its one typed claim false. There is no
advisory tier and no way to demote a finding: ``status`` is ``BLOCKING`` or ``CLEARED``, a CLEARED
finding must carry a ``Clearance`` whose digest binds the clearance's name and evidence to this
finding's own claim fields, and ``Finding.__post_init__`` refuses any other CLEARED finding. The
only code that builds one is ``clearances.apply_clearances`` (``tests/readme/review/
test_review_invariants.py`` asserts that by walking the source). A hand-written or hand-edited
clearance is therefore detectably invalid, though - being plain Python with no secret - not
unforgeable: the guarantee is the registry plus that structural test, not cryptography.

Migration of the previous model (every caller was updated in the same change):

    Finding.kind == "deterministic"   ->  Finding.source == "deterministic"
    Finding.kind == "judgment"        ->  removed (a judgment finding that could never block was the
                                          annotate-only tier D1 forbids; a v1 file that carries one
                                          fails to load rather than be silently read as blocking)
    Finding.refuted_by (Refutation)   ->  Finding.evidence (the rule's proof text); a deterministic
                                          finding is always BLOCKING and can never be cleared
    new                               ->  claim_kind, status, clearance, and the LLM-only fields
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, get_args

ClaimKind = Literal[
    "contradiction",
    "unsupported_claim",
    "omission",
    "absence",
    "name_denial",
    "quality",
]
FindingSource = Literal["deterministic", "llm"]
FindingStatus = Literal["BLOCKING", "CLEARED"]

CLAIM_KINDS: tuple[str, ...] = get_args(ClaimKind)
SOURCES: tuple[str, ...] = get_args(FindingSource)
STATUSES: tuple[str, ...] = get_args(FindingStatus)

#: The claim kinds code can decide from the supplied sources, and the clearances that may decide
#: them. ``contradiction``, ``unsupported_claim`` and ``quality`` are absent on purpose: no pure
#: function proves them false (plan D2).
CLEARANCES_FOR_KIND: Mapping[str, tuple[str, ...]] = {
    "absence": ("absence_present", "absence_unsourced"),
    "name_denial": ("names_supported",),
    "omission": ("omission_present",),
}
CLEARANCE_NAMES: tuple[str, ...] = tuple(
    name for names in CLEARANCES_FOR_KIND.values() for name in names
)


@dataclass(frozen=True)
class OmissionClaim:
    """The typed form of "section X lacks these facts / phrases" (prompt contract ``omission``)."""

    section_id: str
    missing_ids: tuple[str, ...] = ()
    missing_quotes: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not self.missing_ids and not self.missing_quotes


@dataclass(frozen=True)
class Clearance:
    """The proof that a registered clearance disproved a finding's typed claim. ``digest`` binds
    ``name`` and ``evidence`` to the finding it was issued for."""

    name: str
    evidence: tuple[str, ...]
    digest: str


def _claim_fields(finding: Finding) -> dict[str, Any]:
    omission = finding.omission
    return {
        "finding_id": finding.finding_id,
        "section_id": finding.section_id,
        "claim_kind": finding.claim_kind,
        "quote": finding.quote,
        "fact_ids": list(finding.fact_ids),
        "absent": list(finding.absent),
        "unsupported_names": list(finding.unsupported_names),
        "omission": None
        if omission is None
        else {
            "section_id": omission.section_id,
            "missing_ids": list(omission.missing_ids),
            "missing_quotes": list(omission.missing_quotes),
        },
    }


def _clearance_digest(name: str, finding: Finding, evidence: tuple[str, ...]) -> str:
    payload = {
        "clearance": name,
        "claim": _claim_fields(finding),
        "evidence": list(evidence),
    }
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _seal_clearance(
    name: str, finding: Finding, evidence: tuple[str, ...]
) -> Clearance:
    """Issue a clearance for ``finding``. Called only by the registered clearance functions."""
    return Clearance(
        name=name, evidence=evidence, digest=_clearance_digest(name, finding, evidence)
    )


@dataclass(frozen=True)
class Finding:
    """One finding against one candidate.

    ``source == "deterministic"``: a rule proved the candidate defective; ``evidence`` is that
    proof. Always BLOCKING. ``source == "llm"``: a reviewer's claim; BLOCKING until a registered
    clearance proves its single typed claim false. Fields below ``quote`` are the LLM contract's.
    """

    rule: str
    source: FindingSource
    message: str
    claim_kind: ClaimKind = "quality"
    status: FindingStatus = "BLOCKING"
    clearance: Clearance | None = None
    # The literal flagged text, when one exists -- not a paraphrase. readme.review.defect_bridge
    # matches this against composition/placement.py's placed_texts() to tell an authoring (S6)
    # defect from one over content the candidate inherited verbatim (S4); that distinction
    # cannot be guessed from `rule`/`source` alone (project/state.yaml's
    # root_cause_traced_2026_10_24: the real aspose-font-foss/Python case was inherited, not
    # authored, and a naive always-S6 router would have misrouted it).
    quote: str = ""
    evidence: str = ""
    finding_id: str = ""
    section_id: str = ""
    causal_stage: str = ""
    criterion: str = ""
    fact_ids: tuple[str, ...] = ()
    absent: tuple[str, ...] = ()
    unsupported_names: tuple[str, ...] = ()
    omission: OmissionClaim | None = None
    repair: str = ""

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"unknown finding source {self.source!r}")
        if self.claim_kind not in CLAIM_KINDS:
            raise ValueError(f"unknown claim_kind {self.claim_kind!r}")
        if self.status not in STATUSES:
            raise ValueError(f"unknown finding status {self.status!r}")
        if self.status == "BLOCKING":
            if self.clearance is not None:
                raise ValueError(
                    f"finding {self.rule!r} is BLOCKING but carries a clearance"
                )
            return
        if self.source != "llm":
            raise ValueError(
                f"deterministic finding {self.rule!r} cannot be CLEARED: only a reviewer's claim "
                "has a typed claim a clearance can disprove"
            )
        allowed = CLEARANCES_FOR_KIND.get(self.claim_kind, ())
        if not allowed:
            raise ValueError(f"a {self.claim_kind!r} finding is never clearable")
        clearance = self.clearance
        if not isinstance(clearance, Clearance) or clearance.name not in allowed:
            raise ValueError(
                f"a {self.claim_kind!r} finding is cleared only by one of {allowed}, "
                f"not {getattr(clearance, 'name', None)!r}"
            )
        if clearance.digest != _clearance_digest(
            clearance.name, self, clearance.evidence
        ):
            raise ValueError(
                f"the {clearance.name!r} clearance does not prove this finding: its digest "
                "does not match the finding's claim and the clearance's evidence"
            )

    @property
    def blocking(self) -> bool:
        return self.status == "BLOCKING"

    def to_record(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "source": self.source,
            "message": self.message,
            "claim_kind": self.claim_kind,
            "status": self.status,
            "clearance": None
            if self.clearance is None
            else {
                "name": self.clearance.name,
                "evidence": list(self.clearance.evidence),
                "digest": self.clearance.digest,
            },
            "quote": self.quote,
            "evidence": self.evidence,
            "finding_id": self.finding_id,
            "section_id": self.section_id,
            "causal_stage": self.causal_stage,
            "criterion": self.criterion,
            "fact_ids": list(self.fact_ids),
            "absent": list(self.absent),
            "unsupported_names": list(self.unsupported_names),
            "omission": None
            if self.omission is None
            else {
                "section_id": self.omission.section_id,
                "missing_ids": list(self.omission.missing_ids),
                "missing_quotes": list(self.omission.missing_quotes),
            },
            "repair": self.repair,
        }

    @classmethod
    def from_record(cls, raw: Mapping[str, Any]) -> Finding:
        """Rebuild a finding from ``to_record`` output. Raises ``ValueError`` or ``KeyError`` on a
        shape or proof this model cannot honour (a forged CLEARED status fails ``__post_init__``)."""

        def strings(key: str) -> tuple[str, ...]:
            value = raw.get(key, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise ValueError(f"{key} must be a list of strings")
            return tuple(value)

        omission_raw = raw.get("omission")
        omission = (
            None
            if omission_raw is None
            else OmissionClaim(
                section_id=str(omission_raw["section_id"]),
                missing_ids=tuple(str(item) for item in omission_raw["missing_ids"]),
                missing_quotes=tuple(
                    str(item) for item in omission_raw["missing_quotes"]
                ),
            )
        )
        clearance_raw = raw.get("clearance")
        clearance = (
            None
            if clearance_raw is None
            else Clearance(
                name=str(clearance_raw["name"]),
                evidence=tuple(str(item) for item in clearance_raw["evidence"]),
                digest=str(clearance_raw["digest"]),
            )
        )
        return cls(
            rule=str(raw["rule"]),
            source=raw["source"],
            message=str(raw["message"]),
            claim_kind=raw["claim_kind"],
            status=raw["status"],
            clearance=clearance,
            quote=str(raw.get("quote", "")),
            evidence=str(raw.get("evidence", "")),
            finding_id=str(raw.get("finding_id", "")),
            section_id=str(raw.get("section_id", "")),
            causal_stage=str(raw.get("causal_stage", "")),
            criterion=str(raw.get("criterion", "")),
            fact_ids=strings("fact_ids"),
            absent=strings("absent"),
            unsupported_names=strings("unsupported_names"),
            omission=omission,
            repair=str(raw.get("repair", "")),
        )
