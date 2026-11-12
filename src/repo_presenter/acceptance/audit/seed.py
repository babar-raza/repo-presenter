"""TC-014 S2/M9: SEEDING LOGIC for the independent sampled audit (M9).

Given a sealed candidate's rendered README text and its evidence (facts, dispositions and/or
corrections that justified it), this module produces a SEEDED COPY carrying a small number of
blind-injected defects, each tagged internally with its shape, its mutation operator, and the
exact span changed - so a LATER, SEPARATE step (``score.py``) - never the auditor itself, and
never this module - can check what was actually caught. The auditor sees only the seeded README
text; it is never shown this module's manifest.

Five defect shapes are implemented, matching the exact definitions in
``docs/design/2026-11-06-acceptance-redesign.md`` section 2.2's responsibility matrix, grounded in
real cases from ``docs/investigations/2026-11-06-unsupported-claim-class-audit.md`` section 1/5:

* **A** - false checkable claim (the audit's class A). Two operators: ``count_mismatch`` (change a
  stated count, e.g. "39 public types", to a wrong number - ``own5:note-python
  real:unsupported_claim:0``) and ``invent_api_name`` (rename an API-table entry to a name that
  does not exist - ``ref:cells-cpp real:unsupported_claim:15``, "no Workbook_Impl anywhere in the
  repository").
* **D** - ungrounded generated claim (the audit's class D). ``inject_unsupported_claim`` inserts a
  plausible-sounding, fact-less sentence with no corresponding verification record - modelled on
  ``ref:slides-net real:unsupported_claim:1`` ("claims every capability was exercised and
  XML-verified"; "no verification record in the repository").
* **D9** - semantic description mismatch (the audit's residual A: ``CellFormatValue``, ``Row``,
  ``AssetInfo``). ``misdescribe_type`` swaps a type's one-line description for a different, real
  type's description from elsewhere in the same document - plausible prose, provably wrong once
  reattached to the wrong type, with no judgement call about what "wrong" prose might look like.
* **D14** - promotional/generic prose. ``add_promotional_filler`` inserts superlative filler
  language a real README would not need.
* **D15** - incoherent reordering. ``incoherent_reorder`` swaps two adjacent paragraphs/steps.

A "clean control" mode (``clean_control``) returns the candidate completely unmodified, tagged
``CLEAN_SHAPE``, for the false-flag-rate measurement ``score.py`` computes.

This module is pure, offline, deterministic, and network-free: no provider call, no subprocess,
no filesystem write, no randomness. ``encrypt_seed_manifest``/``decrypt_seed_manifest`` are a
clearly-named STUB pair - see their own docstrings - not wired to any live hosted step yet.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from cryptography.fernet import Fernet, InvalidToken

__all__ = [
    "CLEAN_SHAPE",
    "DEFECT_SHAPES",
    "OPERATORS_BY_SHAPE",
    "SHAPE_BY_OPERATOR",
    "SeedingError",
    "SeedSpan",
    "SeedRecord",
    "SeedResult",
    "clean_control",
    "seed_defect",
    "seed_shape",
    "encrypt_seed_manifest",
    "decrypt_seed_manifest",
]

#: The five class-audit shapes this module seeds. ``M9``'s own design-doc gate (section 4.3)
#: requires only A/D/D9 to be seeded blind; D14/D15 are additionally built here because
#: ``add_promotional_filler``/``incoherent_reorder`` are the same operators the design doc's
#: section 4.1 table lists as M8's own corpus-building mutants - one set of operators, two
#: consumers (M8 calibration and M9 seeding). See this card's closeout for the exact scope.
DEFECT_SHAPES: tuple[str, ...] = ("A", "D", "D9", "D14", "D15")

#: Tag used for an unmodified "clean control" copy - never one of ``DEFECT_SHAPES``.
CLEAN_SHAPE = "clean"


class SeedingError(ValueError):
    """Raised when a mutation operator cannot find a safe injection site in the given README text
    - e.g. no "<N> public types" claim for ``count_mismatch``, or fewer than two described
    API-table rows for ``misdescribe_type``. Never silently skipped: a caller that cannot seed a
    requested shape on a given candidate must know, rather than silently seeding nothing and still
    being counted as a seeded case."""


@dataclass(frozen=True)
class SeedSpan:
    """The exact character span, inside the SEEDED text, that a mutation changed."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid span ({self.start}, {self.end})")


@dataclass(frozen=True)
class SeedRecord:
    """One manifest entry: which candidate, which shape, which operator, at which exact line and
    span of the SEEDED text, with the text that was there before and the text that replaced it.
    ``span``/``line`` are ``None`` only for a clean control (nothing changed)."""

    candidate_id: str
    shape: str
    operator: str
    line: int | None
    span: SeedSpan | None
    original_text: str
    seeded_text: str

    def as_dict(self) -> dict[str, Any]:
        """A plain, JSON-serialisable mapping - the shape ``encrypt_seed_manifest`` consumes and
        a later scorer's decrypted manifest entries arrive in."""
        return {
            "candidate_id": self.candidate_id,
            "shape": self.shape,
            "operator": self.operator,
            "line": self.line,
            "span": None if self.span is None else {"start": self.span.start, "end": self.span.end},
            "original_text": self.original_text,
            "seeded_text": self.seeded_text,
        }


@dataclass(frozen=True)
class SeedResult:
    """The output of seeding (or clean-controlling) one candidate: the full seeded README text
    plus its single manifest record."""

    candidate_id: str
    seeded_readme: str
    record: SeedRecord


@dataclass(frozen=True)
class _Mutation:
    """Internal: one operator's raw output, before it is wrapped into a ``SeedRecord``."""

    seeded_text: str
    span: SeedSpan
    original_text: str


def clean_control(candidate_id: str, readme_text: str) -> SeedResult:
    """Return ``readme_text`` completely unmodified, tagged ``CLEAN_SHAPE``, for the
    false-flag-rate measurement (``score.false_flag_rate``)."""
    record = SeedRecord(
        candidate_id=candidate_id,
        shape=CLEAN_SHAPE,
        operator="clean_control",
        line=None,
        span=None,
        original_text="",
        seeded_text="",
    )
    return SeedResult(candidate_id=candidate_id, seeded_readme=readme_text, record=record)


# ---------------------------------------------------------------------------
# Class A: false checkable claim
# ---------------------------------------------------------------------------

_COUNT_CLAIM_PATTERN = re.compile(r"(?P<count>\d+)(?P<unit>\s+public\s+types\b)", re.IGNORECASE)


def op_count_mismatch(
    readme_text: str, evidence: Mapping[str, Any] | None = None
) -> _Mutation:
    """Class A. Change a stated public-type count to a wrong number (``own5:note-python
    real:unsupported_claim:0``: README says 39, ``__all__`` holds 33). If ``evidence`` carries a
    true ``public_type_count`` int, the wrong number is deliberately NOT that true count either -
    this operator seeds a defect, it never accidentally repairs one."""
    evidence = evidence or {}
    match = _COUNT_CLAIM_PATTERN.search(readme_text)
    if match is None:
        raise SeedingError(
            "count_mismatch: no '<N> public types' claim found in the README text"
        )
    original_number = int(match.group("count"))
    true_count = evidence.get("public_type_count")
    if isinstance(true_count, int):
        wrong = true_count + 1
        if wrong == original_number:
            wrong += 1
    else:
        wrong = original_number + 7
    if wrong == original_number:
        wrong += 1
    seeded_fragment = f"{wrong}{match.group('unit')}"
    start, end = match.span()
    seeded_text = readme_text[:start] + seeded_fragment + readme_text[end:]
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(start, start + len(seeded_fragment)),
        original_text=match.group(0),
    )


_API_TABLE_NAME_PATTERN = re.compile(r"\|\s*`(?P<name>[A-Za-z_][A-Za-z0-9_]*)`\s*\|")


def op_invent_api_name(
    readme_text: str, evidence: Mapping[str, Any] | None = None
) -> _Mutation:
    """Class A. Rename an API-table entry to a name that does not exist in the facts
    (``ref:cells-cpp real:unsupported_claim:15``: "no Workbook_Impl anywhere in the
    repository"). If ``evidence`` carries ``exported_types`` (the real, known-good names), the
    renamed row is one of those real names, so the mutation genuinely replaces a true entry with
    a false one rather than coincidentally editing an already-unknown name."""
    evidence = evidence or {}
    known_names = set(evidence.get("exported_types", []) or [])
    chosen = None
    for candidate in _API_TABLE_NAME_PATTERN.finditer(readme_text):
        name = candidate.group("name")
        if not known_names or name in known_names:
            chosen = candidate
            break
    if chosen is None:
        raise SeedingError(
            "invent_api_name: no backtick-quoted API-table entry found to rename"
        )
    real_name = chosen.group("name")
    invented = _invent_nonexistent_name(real_name, known_names)
    start, end = chosen.span("name")
    seeded_text = readme_text[:start] + invented + readme_text[end:]
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(start, start + len(invented)),
        original_text=real_name,
    )


def _invent_nonexistent_name(real_name: str, known_names: set[str]) -> str:
    candidate = f"{real_name}Ghost"
    suffix = 2
    while candidate in known_names:
        candidate = f"{real_name}Ghost{suffix}"
        suffix += 1
    return candidate


# ---------------------------------------------------------------------------
# Class D: ungrounded generated claim
# ---------------------------------------------------------------------------

_VERIFICATION_NARRATIVE_SENTENCES: tuple[str, ...] = (
    "Every public API surface in this release was exercised and verified against the full "
    "upstream test matrix.",
    "All examples in this guide were executed end to end and confirmed byte-identical to the "
    "reference output.",
    "This module has been independently verified for full behavioural parity with the upstream "
    "implementation.",
)


def op_inject_unsupported_claim(
    readme_text: str,
    evidence: Mapping[str, Any] | None = None,
    *,
    index: int = 0,
) -> _Mutation:
    """Class D. Insert a plausible-sounding, fact-less invented-verification sentence
    (``ref:slides-net real:unsupported_claim:1``: "claims every capability was exercised and
    XML-verified"; "no verification record in the repository"). ``evidence`` is accepted for a
    uniform operator signature but is never consulted - that is the point: this sentence is never
    grounded in any fact, by construction."""
    del evidence
    sentence = _VERIFICATION_NARRATIVE_SENTENCES[index % len(_VERIFICATION_NARRATIVE_SENTENCES)]
    insertion_point = _end_of_first_paragraph(readme_text)
    inserted = f" {sentence}"
    seeded_text = readme_text[:insertion_point] + inserted + readme_text[insertion_point:]
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(insertion_point, insertion_point + len(inserted)),
        original_text="",
    )


def _end_of_first_paragraph(text: str) -> int:
    """The character offset right after the first paragraph's own text (before its trailing blank
    line), or the end of the whole text if there is no blank-line paragraph break at all - this
    helper always finds somewhere to insert."""
    blank = text.find("\n\n")
    return len(text) if blank == -1 else blank


# ---------------------------------------------------------------------------
# Class D9: semantic description mismatch
# ---------------------------------------------------------------------------

_API_TABLE_ROW_WITH_DESC = re.compile(
    r"\|\s*`(?P<name>[A-Za-z_][A-Za-z0-9_]*)`\s*\|\s*(?P<desc>[^|\n]+?)\s*\|"
)


def op_misdescribe_type(
    readme_text: str, evidence: Mapping[str, Any] | None = None
) -> _Mutation:
    """Class D9. Swap in a plausible but wrong one-line description for a named type, by taking a
    second, real type's description from elsewhere in the same document
    (``own:cells-cpp real:unsupported_claim:1``: "CellFormatValue represents the formatted value
    of a cell" - a style record's description misapplied). Swapping with a genuinely different,
    real description (rather than inventing prose) guarantees the result is wrong without any
    judgement call about what "wrong" looks like. Only the first (target) row's text changes;
    the donor row is left untouched."""
    del evidence
    candidates = [
        match
        for match in _API_TABLE_ROW_WITH_DESC.finditer(readme_text)
        if match.group("desc").strip()
    ]
    target = donor = None
    for i, first in enumerate(candidates):
        for second in candidates[i + 1 :]:
            if first.group("desc").strip() != second.group("desc").strip():
                target, donor = first, second
                break
        if target is not None:
            break
    if target is None or donor is None:
        raise SeedingError(
            "misdescribe_type: need at least two described API-table rows with different "
            "descriptions to swap"
        )
    start, end = target.span("desc")
    original = target.group("desc")
    replacement = donor.group("desc")
    seeded_text = readme_text[:start] + replacement + readme_text[end:]
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(start, start + len(replacement)),
        original_text=original,
    )


# ---------------------------------------------------------------------------
# Class D14: promotional / generic prose
# ---------------------------------------------------------------------------

_PROMOTIONAL_FILLER_SENTENCES: tuple[str, ...] = (
    "It is an incredibly powerful, flexible, and remarkably easy-to-use solution that delivers "
    "seamless, best-in-class results for every workflow.",
    "This cutting-edge toolkit unlocks effortless productivity and world-class performance right "
    "out of the box.",
)


def op_add_promotional_filler(
    readme_text: str,
    evidence: Mapping[str, Any] | None = None,
    *,
    index: int = 0,
) -> _Mutation:
    """Class D14. Insert superlative, promotional filler language a real README would not need -
    the ``add_promotional_filler`` operator the design doc names for M8's own corpus (section
    4.1), reused here for M9 seeding."""
    del evidence
    sentence = _PROMOTIONAL_FILLER_SENTENCES[index % len(_PROMOTIONAL_FILLER_SENTENCES)]
    insertion_point = _end_of_first_paragraph(readme_text)
    inserted = f" {sentence}"
    seeded_text = readme_text[:insertion_point] + inserted + readme_text[insertion_point:]
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(insertion_point, insertion_point + len(inserted)),
        original_text="",
    )


# ---------------------------------------------------------------------------
# Class D15: incoherent reordering
# ---------------------------------------------------------------------------


def op_incoherent_reorder(
    readme_text: str, evidence: Mapping[str, Any] | None = None
) -> _Mutation:
    """Class D15. Swap the order of two adjacent, distinct, non-empty paragraphs/steps - the
    ``incoherent_reorder`` operator the design doc names (section 4.1). The document's own first
    paragraph (an H1 title, when present) is never chosen as one half of the swap, so the title
    itself is never reordered away from the top of the document."""
    del evidence
    parts = readme_text.split("\n\n")
    if len(parts) < 2:
        raise SeedingError(
            "incoherent_reorder: need at least two paragraphs/steps to reorder"
        )
    start_index = 1 if parts[0].strip().startswith("#") else 0
    swap_index = None
    for i in range(start_index, len(parts) - 1):
        first, second = parts[i].strip(), parts[i + 1].strip()
        if first and second and first != second:
            swap_index = i
            break
    if swap_index is None:
        raise SeedingError(
            "incoherent_reorder: no adjacent, distinct, non-empty paragraph pair found"
        )
    original_pair = "\n\n".join([parts[swap_index], parts[swap_index + 1]])
    parts[swap_index], parts[swap_index + 1] = parts[swap_index + 1], parts[swap_index]
    seeded_text = "\n\n".join(parts)
    before = "\n\n".join(parts[:swap_index])
    start = len(before) + (2 if before else 0)
    swapped_pair = "\n\n".join([parts[swap_index], parts[swap_index + 1]])
    end = start + len(swapped_pair)
    return _Mutation(
        seeded_text=seeded_text,
        span=SeedSpan(start, end),
        original_text=original_pair,
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

#: Every shape's operators, in the order ``seed_shape`` tries them.
OPERATORS_BY_SHAPE: dict[str, tuple[str, ...]] = {
    "A": ("count_mismatch", "invent_api_name"),
    "D": ("inject_unsupported_claim",),
    "D9": ("misdescribe_type",),
    "D14": ("add_promotional_filler",),
    "D15": ("incoherent_reorder",),
}

_OPERATOR_FUNCS: dict[str, Callable[..., _Mutation]] = {
    "count_mismatch": op_count_mismatch,
    "invent_api_name": op_invent_api_name,
    "inject_unsupported_claim": op_inject_unsupported_claim,
    "misdescribe_type": op_misdescribe_type,
    "add_promotional_filler": op_add_promotional_filler,
    "incoherent_reorder": op_incoherent_reorder,
}

#: The inverse of ``OPERATORS_BY_SHAPE`` - every operator maps to exactly one shape.
SHAPE_BY_OPERATOR: dict[str, str] = {
    operator: shape for shape, operators in OPERATORS_BY_SHAPE.items() for operator in operators
}


def seed_defect(
    candidate_id: str,
    readme_text: str,
    operator: str,
    evidence: Mapping[str, Any] | None = None,
    **operator_kwargs: Any,
) -> SeedResult:
    """Seed exactly one named ``operator``'s defect into ``readme_text``, returning the full
    seeded README plus its manifest record. Raises ``SeedingError`` (never anything else) if
    ``operator`` is unknown or cannot find a safe injection site in this particular text."""
    if operator not in _OPERATOR_FUNCS:
        known = ", ".join(sorted(_OPERATOR_FUNCS))
        raise SeedingError(f"unknown mutation operator {operator!r}; known operators: {known}")
    mutation = _OPERATOR_FUNCS[operator](readme_text, evidence, **operator_kwargs)
    shape = SHAPE_BY_OPERATOR[operator]
    line = mutation.seeded_text.count("\n", 0, mutation.span.start) + 1
    record = SeedRecord(
        candidate_id=candidate_id,
        shape=shape,
        operator=operator,
        line=line,
        span=mutation.span,
        original_text=mutation.original_text,
        seeded_text=mutation.seeded_text[mutation.span.start : mutation.span.end],
    )
    return SeedResult(candidate_id=candidate_id, seeded_readme=mutation.seeded_text, record=record)


def seed_shape(
    candidate_id: str,
    readme_text: str,
    shape: str,
    evidence: Mapping[str, Any] | None = None,
    **operator_kwargs: Any,
) -> SeedResult:
    """Seed ``shape`` into ``readme_text`` by trying each of ``OPERATORS_BY_SHAPE[shape]`` in
    order until one finds a safe injection site. Raises ``SeedingError`` only if every operator
    for that shape fails on this particular text."""
    if shape not in OPERATORS_BY_SHAPE:
        known = ", ".join(DEFECT_SHAPES)
        raise SeedingError(f"unknown defect shape {shape!r}; known shapes: {known}")
    problems: list[str] = []
    for operator in OPERATORS_BY_SHAPE[shape]:
        try:
            return seed_defect(candidate_id, readme_text, operator, evidence, **operator_kwargs)
        except SeedingError as error:
            problems.append(str(error))
    raise SeedingError(
        f"no operator for shape {shape!r} found an injection site: {'; '.join(problems)}"
    )


# ---------------------------------------------------------------------------
# Manifest encryption - real AEAD (cryptography.fernet.Fernet), wired 2026-11-09 once the
# restricted GitHub Environment holding AUDIT_SEED_KEY existed (owner action 1, complete).
# ---------------------------------------------------------------------------


def _fernet_key(key: bytes) -> bytes:
    """Fernet needs a 32-byte key, urlsafe-base64-encoded. This module's own external contract
    (every caller, every existing test) passes a raw 32-byte key -- ``AUDIT_SEED_KEY`` is stored
    as a 64-char hex string in the GitHub Environment and read as
    ``bytes.fromhex(os.environ["AUDIT_SEED_KEY"])`` by the hosted seeder/scorer, giving exactly
    32 raw bytes here. Deriving the Fernet-formatted key from that raw key, instead of asking
    every caller to pre-encode it, keeps the external contract exactly as it was under the old
    stub cipher -- no caller or test needed to change."""
    if len(key) != 32:
        raise ValueError(f"seed manifest key must be 32 raw bytes, got {len(key)}")
    return base64.urlsafe_b64encode(key)


def key_manifest_by_case_id(manifest):
    """The seeder writes each entry as ``{"case_id": <hash>, "candidate_id": "repo@lane@rev", ...}``
    but auditors, the case index and the findings all name a candidate by its ``case_id``. Scoring
    joins findings to manifest entries on ``candidate_id``, so re-key every entry to its case id
    first; without this a real run scores 0 recall and no clean control can ever be flagged."""
    return [{**entry, "candidate_id": entry.get("case_id", entry["candidate_id"])} for entry in manifest]


def encrypt_seed_manifest(
    manifest: Sequence[Mapping[str, Any]] | Mapping[str, Any], key: bytes
) -> bytes:
    """Encrypt ``manifest`` (canonical JSON) with ``cryptography.fernet.Fernet`` under ``key`` (a
    raw 32-byte key -- see ``_fernet_key``). Fernet is a real, audited AEAD: unlike the stub this
    replaced, it includes its own random nonce (safe to reuse a key across manifests) and a
    verified HMAC, so ``decrypt_seed_manifest`` fails closed on a wrong key or any tampering."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return Fernet(_fernet_key(key)).encrypt(canonical)


def decrypt_seed_manifest(blob: bytes, key: bytes) -> Any:
    """The inverse of ``encrypt_seed_manifest``. Raises ``ValueError`` (never returns a silently
    wrong result, and never leaks Fernet's own ``InvalidToken`` type past this module's own
    contract) on a wrong key, a tampered blob, or an expired/malformed token."""
    try:
        canonical = Fernet(_fernet_key(key)).decrypt(blob)
    except InvalidToken as error:
        raise ValueError("seed manifest decryption failed: tampered blob or wrong key") from error
    return json.loads(canonical.decode("utf-8"))
