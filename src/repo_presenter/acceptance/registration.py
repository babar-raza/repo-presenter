"""Freeze the held-out acceptance registration "A1" from data that already exists on disk or in
this project's own git history, at zero provider calls (TC-022a).

Why this module exists, exactly: an earlier draft of the acceptance-calibration plan had A1 draw
some of its clean-twin cases from freshly generated production candidates -- but those candidates
could not be generated until the acceptance pipeline they were meant to calibrate was already
switched on, which itself needed A1 to exist first. That is a real cycle: nothing can be first.
This module breaks it by building A1 entirely from three sources already committed to this
repository, never by calling a model or a provider.

The three sources (see TC-022a's own ``source_refs`` for the exact committed paths):

1. The reviewer-calibration corpus and its iteration-5 registration
   (``docs/investigations/2026-11-06-reviewer-calibration-iteration-5-data/registration.json``,
   schema ``reviewer-calibration-registration/1``). Reading it directly (zero provider calls, no
   ``--cache-corpus`` pickle rebuild needed -- that pickle does not exist in a fresh checkout and
   its rebuild needs upstream clones this worktree does not have) shows a REAL zero-call case
   universe of **1465** cases (``corpus_cases``), of which 574 excluded-id matches were dropped
   and 288 were registered (``selected``): 28 ``clean``, 124 ``mutant``, 113 ``real_defect``, 23
   ``unscored_twin``. This is NOT 924. Of the 288 registered cases, only the 113 ``real_defect``
   ones were individually hand-audited into the five recall classes A/B/C/D/E by
   ``docs/investigations/2026-11-06-unsupported-claim-class-audit.md`` (section "## 5. Every
   case", which this module parses directly -- it is the real, only source of a per-case A-E
   label; ``registration.json`` itself carries no recall-class field). The other 175 registered
   cases (28 clean + 124 mutant + 23 unscored_twin) have labels/digests in ``registration.json``
   but were never given that same per-case hand audit; this module keeps them in their own role,
   never invents an A-E label for them.
2. The 24 sealed candidates in ``data/recertification_baseline.json`` (schema_version 1,
   recertify_version 1): 10 ``RECERTIFIED``, 14 ``NEEDS_REPAIR``, 12 Lane L / 12 Lane R. This
   module reads only that committed file -- it does NOT call
   ``repo_presenter.core.state.bundle_store.seal_history`` itself, because that reader performs a
   real git fetch of the bundle remote (network access), which a zero-call, ``network: false``
   registration must not depend on. The per-unit ``dispositions.json``/``content_units.json`` for
   these 24 sealed revisions are also not present in a fresh worktree (they live only in the
   bundle history, which needs that same fetch to materialize); this module therefore treats each
   sealed entry as one coarse, repository-level clean-twin candidate (``RECERTIFIED`` with no
   ``failing_checks`` => a clean twin) rather than claiming per-claim detail it cannot read
   offline. A caller that HAS already materialized a sealed bundle on disk (e.g. the supervisor,
   with network access) may still build a richer record itself; this module does not require it.
3. The existing mutation operators in
   ``src/repo_presenter/readme/review/calibration/mutations.py`` (``OPERATORS``). The real names
   found by grep are ``inject_unsupported_claim``, ``contradict_version``,
   ``contradict_package_name``, ``contradict_format``, ``drop_section``, ``duplicate_paragraph``,
   ``break_install_command``, ``invent_api_name``, ``add_promotional_filler``. Of the three
   example names this card's own text gave, ``duplicate_paragraph`` and ``add_promotional_filler``
   match exactly; ``format_overclaim`` does **not** exist under that name -- the closest real
   operator for an unsupported/overclaimed statement is ``inject_unsupported_claim``. This module
   never calls an operator function directly (that needs a real ``SourceCandidate`` with live
   facts/README text, which is calibration-harness input, not a registration concern); instead it
   draws its synthetic-defect material from the already-mutated, already-labelled ``mutant`` cases
   recorded in source 1's ``registration.json``, which is the zero-call record of what those
   operators already produced.

What this module does NOT do: it does not write the real, committed ``data/registrations/A1.json``
(or equivalent path) -- that path is denied to a worker taskcard by ``ops/gatectl.py``'s
``GLOBAL_DENY`` (which covers ``data/**`` among others). ``build_a1_from_existing_data`` is the
real, end-to-end builder the supervisor calls directly, against the real paths, as a separate,
non-taskcard, supervisor-owned action once this module is accepted; this module's own tests only
ever write into a temporary directory.

Second-labeller pass: ``second_labeller_pass`` is a documented, deterministic, rule-based
STAND-IN second pass (a simple-majority baseline), not a genuine second independent labeller.
See its docstring for exactly what that means and does not mean.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

#: The five recall classes, defined exactly as
#: ``docs/investigations/2026-11-06-unsupported-claim-class-audit.md`` section 1 defines them:
#: A false (the repository contradicts the claim); B true (the facts extractor simply missed it);
#: C unverifiable but plausible maintainer knowledge; D generator-authored and unsupported;
#: E label error (the sentence is fine). A "clean twin" (a whole candidate expected to be
#: accepted, with no single flagged claim) carries none of these -- it is tracked separately via
#: ``CaseRecord.is_clean_twin``, never forced into a sixth pseudo-class.
RECALL_CLASSES = ("A", "B", "C", "D", "E")

#: Source tags, naming exactly which of the three sources above a ``CaseRecord`` came from.
SOURCE_AUDITED_LABEL = "audited_real_defect"
SOURCE_CALIBRATION_REGISTRATION = "calibration_registration"
SOURCE_SEALED_CANDIDATE = "sealed_candidate"

#: The real registration.json schema this module reads (reviewer-calibration-registration/1).
_CALIBRATION_REGISTRATION_SCHEMA = "reviewer-calibration-registration/1"

_SEPARATOR_CELL = re.compile(r"^:?-+:?$")


def _sha256_hex(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def rank(case_id: str) -> str:
    """The SHA-256 hex digest of ``case_id``: every selection/stratification/sampling choice in
    this module ranks by this value, so results are reproducible and no label or verdict can
    influence which cases are chosen (the same convention
    ``readme/review/calibration/selection.py`` already uses for the calibration harness)."""
    return hashlib.sha256(case_id.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CaseRecord:
    """One case drawn from one of the three zero-call sources.

    ``digest`` is a stable identity digest already available from the source: a real
    ``readme_sha256``/``defect_sha256`` from the calibration registration when the case came from
    there, or a digest computed from the sealed-candidate's own identifying fields otherwise.
    ``recall_class`` is one of ``RECALL_CLASSES`` only for a case the audit markdown actually
    labelled (``audited`` is True in exactly that situation); every other case leaves it ``None``
    and is never force-labelled by this module.
    """

    case_id: str
    source: str
    role: str
    is_clean_twin: bool
    digest: str
    recall_class: str | None = None
    audited: bool = False
    base: str | None = None
    klass: str | None = None


# --------------------------------------------------------------------------------------------
# Source 1a: the per-case A-E label, from the audit markdown's own table (the only place a
# recall-class label for a real-defect case actually exists).
# --------------------------------------------------------------------------------------------


def _section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        raise ValueError(f"heading {heading!r} not found in the audit markdown")
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## ") and lines[index].strip() != heading:
            end = index
            break
    return "\n".join(lines[start:end])


def _table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(_SEPARATOR_CELL.match(cell) for cell in cells):
            continue  # a "|---|---|" separator row
        rows.append(cells)
    return rows


def load_audit_labels(markdown: str, *, heading: str = "## 5. Every case") -> dict[str, str]:
    """``{case_id: recall_class}`` parsed from the audit markdown's own per-case table (its first
    two columns are ``Case`` and ``Class``). Raises ``ValueError`` on a row whose class is not one
    of ``RECALL_CLASSES`` -- a label this module cannot recognise is a reason to stop, not to
    drop the row silently."""
    labels: dict[str, str] = {}
    for cells in _table_rows(_section(markdown, heading)):
        if len(cells) < 2:
            continue
        first = cells[0].strip()
        if first.lower() == "case":
            continue  # the header row
        case_id = first.strip("`").strip()
        if not case_id:
            continue
        recall_class = cells[1].strip().upper()
        if recall_class not in RECALL_CLASSES:
            raise ValueError(
                f"audit row for {case_id!r} has an unrecognised class {recall_class!r} "
                f"(expected one of {RECALL_CLASSES})"
            )
        if case_id in labels and labels[case_id] != recall_class:
            raise ValueError(
                f"audit markdown labels {case_id!r} twice, as {labels[case_id]!r} and "
                f"{recall_class!r}"
            )
        labels[case_id] = recall_class
    return labels


def load_audit_labels_from_file(path: Path) -> dict[str, str]:
    return load_audit_labels(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------
# Source 1b: the calibration registration itself (clean / mutant / real_defect / unscored_twin).
# --------------------------------------------------------------------------------------------


def load_calibration_registration(document: Mapping[str, Any]) -> list[CaseRecord]:
    """Every case in a ``reviewer-calibration-registration/1`` document, as a ``CaseRecord``.
    ``clean`` and ``unscored_twin`` roles are expected-accept, so they are clean twins; ``mutant``
    and ``real_defect`` are not. No recall class is assigned here -- that only ever comes from
    ``load_audit_labels``, applied afterwards by ``apply_audit_labels``."""
    schema = document.get("schema")
    if schema != _CALIBRATION_REGISTRATION_SCHEMA:
        raise ValueError(
            f"not a {_CALIBRATION_REGISTRATION_SCHEMA!r} document (schema={schema!r})"
        )
    records: list[CaseRecord] = []
    for entry in document.get("cases", []):
        role = entry["role"]
        digest = entry.get("defect_sha256") or entry.get("readme_sha256")
        if not digest:
            digest = _sha256_hex("calibration_registration", entry["case"])
        records.append(
            CaseRecord(
                case_id=entry["case"],
                source=SOURCE_CALIBRATION_REGISTRATION,
                role=role,
                is_clean_twin=role in {"clean", "unscored_twin"},
                digest=digest,
                base=entry.get("base"),
                klass=entry.get("klass"),
            )
        )
    return records


def load_calibration_registration_from_file(path: Path) -> list[CaseRecord]:
    return load_calibration_registration(json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------------------------
# Source 2: the 24 sealed candidates (repository-level outcome only; no network fetch here).
# --------------------------------------------------------------------------------------------


def load_sealed_baseline(document: Mapping[str, Any]) -> list[CaseRecord]:
    """Every seal in a ``data/recertification_baseline.json``-shaped document, as one coarse,
    repository-level ``CaseRecord``. A ``RECERTIFIED`` seal with no ``failing_checks`` is treated
    as a clean twin; anything else (``NEEDS_REPAIR``, or ``RECERTIFIED`` with a recorded failing
    check) is not. This never fetches a bundle (``bundle_store.seal_history`` needs a real git
    fetch of the bundle remote); it reads only the fields already committed in the baseline file."""
    records: list[CaseRecord] = []
    for seal in document.get("seals", []):
        repository = seal["repository"]
        lane = seal["lane"]
        revision = seal["revision"]
        outcome = seal.get("outcome", "")
        failing_checks = seal.get("failing_checks") or []
        case_id = f"sealed:{repository}@{lane}@{revision}"
        is_clean = outcome == "RECERTIFIED" and not failing_checks
        digest = _sha256_hex(
            "sealed_candidate", repository, lane, revision, outcome, seal.get("commit", "")
        )
        records.append(
            CaseRecord(
                case_id=case_id,
                source=SOURCE_SEALED_CANDIDATE,
                role="sealed_clean" if is_clean else "sealed_needs_repair",
                is_clean_twin=is_clean,
                digest=digest,
                base=repository,
            )
        )
    return records


def load_sealed_baseline_from_file(path: Path) -> list[CaseRecord]:
    return load_sealed_baseline(json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------------------------
# Merge: overlay the audit's per-case A-E labels onto the matching registered real_defect cases.
# --------------------------------------------------------------------------------------------


def apply_audit_labels(
    records: Sequence[CaseRecord], labels: Mapping[str, str]
) -> tuple[list[CaseRecord], list[str]]:
    """``(updated_records, unmatched_label_ids)``. Every ``case_id`` in ``labels`` that matches a
    record in ``records`` gets that record's ``recall_class`` set and ``audited`` set True (its
    digest and every other field are kept exactly as registered). A label naming a case id this
    repository's own registration does not contain is never dropped silently -- it comes back in
    ``unmatched_label_ids`` so drift between the audit and the registration is always visible."""
    by_id = {record.case_id: record for record in records}
    unmatched: list[str] = []
    for case_id, recall_class in labels.items():
        existing = by_id.get(case_id)
        if existing is None:
            unmatched.append(case_id)
            continue
        by_id[case_id] = replace(existing, recall_class=recall_class, audited=True)
    updated = [by_id[record.case_id] for record in records]
    return updated, sorted(unmatched)


# --------------------------------------------------------------------------------------------
# Selection, shortfall, canonical digest, and the second-labeller stand-in.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ShortfallReport:
    """Honest reporting of whether A1 reaches its minimums from existing data alone. Never
    padded, never silently lowered: ``per_class_shortfall``/``clean_twin_shortfall`` name exactly
    which classes are short and by how much when a minimum is not met."""

    per_class_target: int
    clean_twin_target: int
    per_class_achieved: Mapping[str, int]
    clean_twin_achieved: int
    per_class_shortfall: Mapping[str, int]
    clean_twin_shortfall: int

    @property
    def met(self) -> bool:
        return not any(self.per_class_shortfall.values()) and self.clean_twin_shortfall == 0

    def short_classes(self) -> list[str]:
        return sorted(cls for cls, deficit in self.per_class_shortfall.items() if deficit > 0)


@dataclass(frozen=True)
class SecondLabellerResult:
    """The result of the (stand-in) second-labeller pass. ``stand_in`` is always True for the
    result ``second_labeller_pass`` produces: nothing in this module ever claims a genuinely
    independent second judgement. ``agreement`` is Cohen's kappa of the sampled cases' true
    recall class against this stand-in's prediction, or ``None`` when the sample is empty."""

    stand_in: bool
    sample_size: int
    agreement: float | None
    method: str


@dataclass(frozen=True)
class A1Registration:
    """The frozen A1 selection this module produces. ``labelled_cases`` is the recall-class
    sample: every entry carries exactly one of ``RECALL_CLASSES`` (this is the invariant TC-022a's
    own tests check). ``clean_twins`` is the separate expected-accept pool; by definition a clean
    twin has no single flagged claim to assign an A-E label to, so it is never forced into one."""

    labelled_cases: tuple[CaseRecord, ...]
    clean_twins: tuple[CaseRecord, ...]
    shortfall: ShortfallReport
    second_labeller: SecondLabellerResult
    digest: str


def _case_entry(record: CaseRecord) -> tuple[str, str, str, str, str, str]:
    """A canonical, order-independent tuple for one case, used by ``canonical_digest``."""
    return (
        record.case_id,
        record.source,
        record.role,
        record.recall_class or "",
        "1" if record.is_clean_twin else "0",
        record.digest,
    )


def canonical_digest(
    labelled_cases: Sequence[CaseRecord], clean_twins: Sequence[CaseRecord]
) -> str:
    """The SHA-256 hex digest of a canonical, sorted, deterministic serialization of the exact
    selected case set. Two runs over the same inputs -- in any input order -- produce a
    byte-identical digest: every component is sorted before serialization, and the JSON encoding
    uses fixed, sorted keys and no incidental whitespace."""
    payload = {
        "labelled_cases": sorted(_case_entry(record) for record in labelled_cases),
        "clean_twins": sorted(_case_entry(record) for record in clean_twins),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _majority_class(records: Sequence[CaseRecord]) -> str | None:
    counts: dict[str, int] = {}
    for record in records:
        if record.recall_class in RECALL_CLASSES:
            counts[record.recall_class] = counts.get(record.recall_class, 0) + 1
    if not counts:
        return None
    top = max(counts.values())
    # a deterministic tie-break: alphabetically first among the classes at the maximum count
    return sorted(cls for cls, n in counts.items() if n == top)[0]


def cohens_kappa(pairs: Sequence[tuple[str, str]]) -> float | None:
    """The standard two-rater, multi-class Cohen's kappa over ``(true, predicted)`` pairs, or
    ``None`` when there are no pairs."""
    if not pairs:
        return None
    total = len(pairs)
    classes = sorted({label for pair in pairs for label in pair})
    observed_agreement = sum(1 for true, predicted in pairs if true == predicted) / total
    true_counts = {cls: 0 for cls in classes}
    predicted_counts = {cls: 0 for cls in classes}
    for true, predicted in pairs:
        true_counts[true] += 1
        predicted_counts[predicted] += 1
    expected_agreement = sum(
        (true_counts[cls] / total) * (predicted_counts[cls] / total) for cls in classes
    )
    if expected_agreement >= 1.0:
        return 1.0 if observed_agreement >= 1.0 else 0.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def second_labeller_pass(
    labelled_cases: Sequence[CaseRecord], *, fraction: float = 0.2
) -> SecondLabellerResult:
    """A documented, deterministic, rule-based STAND-IN second-labeller pass over a hash-ranked
    sample of ``labelled_cases``.

    This registration has no second independent labelling source available in this zero-call,
    zero-model context: the real audit's own human judgement cannot be re-run inside a taskcard,
    and no second reviewer model may be called here (``network: false``, no provider calls). The
    "second pass" implemented here is therefore a **simple-majority baseline**: for every sampled
    case it predicts the single most common recall class already observed across the whole
    labelled selection (ties broken alphabetically, for determinism), and reports Cohen's kappa of
    the true labels against that fixed prediction.

    This is explicitly NOT a second genuinely independent labeller, and the kappa value it
    produces does not mean what a real inter-rater kappa would mean: a low (or even negative)
    value here mostly says the true labels are not dominated by one class, which is expected
    (B is the plurality class by a wide margin in the real audited data) and is not, by itself,
    evidence about label quality. ``SecondLabellerResult.stand_in`` is always ``True`` for the
    value this function returns.
    """
    ordered = sorted(labelled_cases, key=lambda record: rank(record.case_id))
    sample_size = math.ceil(len(ordered) * fraction)
    sample = ordered[:sample_size]
    majority = _majority_class(labelled_cases)
    if not sample or majority is None:
        return SecondLabellerResult(
            stand_in=True, sample_size=0, agreement=None, method="simple_majority_baseline"
        )
    pairs = [
        (record.recall_class, majority) for record in sample if record.recall_class in RECALL_CLASSES
    ]
    return SecondLabellerResult(
        stand_in=True,
        sample_size=len(sample),
        agreement=cohens_kappa(pairs),
        method="simple_majority_baseline",
    )


def select_a1(
    records: Sequence[CaseRecord],
    *,
    per_class_min: int = 30,
    clean_twin_min: int = 50,
    second_labeller_fraction: float = 0.2,
) -> A1Registration:
    """Build the A1 registration from already-loaded ``CaseRecord``s (from any mix of the three
    sources, already merged -- see ``apply_audit_labels``). Every audited (A-E labelled) case this
    repository's existing data holds is selected (there is no larger ground-truth pool to sample
    down from); nothing is padded or invented to reach a minimum, and the shortfall against
    ``per_class_min``/``clean_twin_min`` is reported exactly as found."""
    pool_by_class: dict[str, list[CaseRecord]] = {cls: [] for cls in RECALL_CLASSES}
    for record in records:
        if record.recall_class in RECALL_CLASSES:
            pool_by_class[record.recall_class].append(record)

    labelled_selected: list[CaseRecord] = []
    per_class_achieved: dict[str, int] = {}
    per_class_shortfall: dict[str, int] = {}
    for cls in RECALL_CLASSES:
        ordered = sorted(pool_by_class[cls], key=lambda record: rank(record.case_id))
        per_class_achieved[cls] = len(ordered)
        per_class_shortfall[cls] = max(0, per_class_min - len(ordered))
        labelled_selected.extend(ordered)
    labelled_selected.sort(key=lambda record: rank(record.case_id))

    seen_ids: set[str] = set()
    clean_twins: list[CaseRecord] = []
    for record in sorted(
        (r for r in records if r.is_clean_twin), key=lambda record: rank(record.case_id)
    ):
        if record.case_id in seen_ids:
            continue
        seen_ids.add(record.case_id)
        clean_twins.append(record)
    clean_twin_achieved = len(clean_twins)
    clean_twin_shortfall = max(0, clean_twin_min - clean_twin_achieved)

    shortfall = ShortfallReport(
        per_class_target=per_class_min,
        clean_twin_target=clean_twin_min,
        per_class_achieved=dict(per_class_achieved),
        clean_twin_achieved=clean_twin_achieved,
        per_class_shortfall=dict(per_class_shortfall),
        clean_twin_shortfall=clean_twin_shortfall,
    )
    second_labeller = second_labeller_pass(labelled_selected, fraction=second_labeller_fraction)
    digest = canonical_digest(labelled_selected, clean_twins)
    return A1Registration(
        labelled_cases=tuple(labelled_selected),
        clean_twins=tuple(clean_twins),
        shortfall=shortfall,
        second_labeller=second_labeller,
        digest=digest,
    )


def build_a1_from_existing_data(
    *,
    audit_markdown_path: Path,
    calibration_registration_path: Path,
    sealed_baseline_path: Path,
    per_class_min: int = 30,
    clean_twin_min: int = 50,
    second_labeller_fraction: float = 0.2,
) -> tuple[A1Registration, list[str]]:
    """The real, end-to-end, zero-provider-call build over the three committed sources this
    module's docstring names. Returns ``(registration, unmatched_audit_labels)``;
    ``unmatched_audit_labels`` lists any audited case id the markdown table names that the
    calibration registration file does not contain (a drift signal, never silently dropped).

    This function never writes anything. TC-022a's closeout calls it directly, against the real
    repository paths, as a separate, supervisor-owned action once this module is accepted, and
    commits the resulting registration and digest itself."""
    labels = load_audit_labels_from_file(audit_markdown_path)
    registered = load_calibration_registration_from_file(calibration_registration_path)
    sealed = load_sealed_baseline_from_file(sealed_baseline_path)
    combined, unmatched = apply_audit_labels(registered, labels)
    combined = combined + sealed
    registration = select_a1(
        combined,
        per_class_min=per_class_min,
        clean_twin_min=clean_twin_min,
        second_labeller_fraction=second_labeller_fraction,
    )
    return registration, unmatched
