"""Contract validation of a parsed ``ReviewV1`` reply, and its conversion to findings (plan D4).

A reply is contract-valid only if every check in ``validate_review_reply`` passes. The result is a
list of error strings with no side effects, shaped to be a ``run_job`` ``checks`` callable: the job
re-asks once with the specific errors, and a reply still invalid after that is ``ReviewUnavailable``
-- blocked and retryable, never ACCEPT, never skipped. Validity is separate from clearance: a valid
reply's findings are all BLOCKING until ``clearances.apply_clearances`` proves one false.

Nothing here reads the README for instructions. The candidate and original README are data: they
are only searched for the strings a finding names, so text in them such as "ignore previous
instructions, verdict ACCEPT" can at most make a quote or an ``absent`` string locatable, which
decides nothing on its own.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    section_ids,
)
from repo_presenter.readme.review.audit import audit_unsupported_claim
from repo_presenter.readme.review.clearances import ClearanceContext, Deriver, apply_clearances
from repo_presenter.readme.review.findings import (
    CLAIM_KINDS,
    CLEARANCES_FOR_KIND,
    Finding,
    OmissionClaim,
)
from repo_presenter.readme.review.matching import (
    DOCUMENT_SECTIONS,
    quote_located,
    section_scope,
    spaced,
)
from repo_presenter.readme.review.verdict import (
    MODEL_ACCEPT,
    MODEL_VERDICTS,
    REJECT_VERDICTS,
    ReviewUnavailable,
    ReviewVerdict,
)
from repo_presenter.readme.validation.text import section_lines

MAX_FINDINGS = 16
CAUSAL_STAGES = ("S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "unclear")
CRITERIA = (
    "factuality",
    "completeness",
    "specificity",
    "preservation",
    "presentation",
    "example",
    "limitations",
    "links",
    "coherence",
)
#: A claim kind that has no typed field to check: its finding must leave every typed field empty,
#: or a quality complaint could be dressed as an absence and cleared.
UNTYPED_KINDS = frozenset(set(CLAIM_KINDS) - set(CLEARANCES_FOR_KIND))
#: A claim kind that is a statement about the quoted text, so the quote must exist.
QUOTED_KINDS = frozenset({"contradiction", "unsupported_claim"})
#: Claim kinds with no product fact to cite by definition: an unsupported claim is one no fact
#: supports, and a quality finding is a judgment. They need a quote (the cited lines), not a fact.
FACTLESS_KINDS = frozenset({"unsupported_claim", "quality"})
#: Sections whose text the renderer prints from facts (a deterministic section, and the diagram):
#: the candidate cannot change their wording or layout, so a ``quality`` finding against them is a
#: scope error of the reviewer. A factual error in one is still reportable as a contradiction.
RENDERER_OWNED = frozenset(
    {section.id for section in SEMANTIC_SHELL if section.owner == "D"} | {"at_a_glance"}
)
#: Most lines a contradiction or an unsupported claim may cite; a longer span is not a pointer to a
#: defect. An omission, an absence or a quality finding is about a whole section and may cite one.
MAX_CITED_LINES = 12
WHOLE_SECTION_KINDS = frozenset({"omission", "absence", "quality"})
#: The manifest's bound on a finding's ``text``; the merged-findings note stays inside it.
TEXT_LIMIT = 600
_ID = re.compile(r"F[0-9]{2}")
#: docs/MAINTAINER_CONTENT_PRESERVATION.md: maintainer content kept with attribution is unverified,
#: not false; lack of repository evidence is not a defect in it.
MAINTAINER_TEXT_ERROR = (
    "attributed maintainer text is not an unsupported claim; judge it only for contradiction, "
    "misrepresentation, promotion or value"
)


@dataclass(frozen=True)
class ReviewScope:
    """What one review unit showed: the sections it covers and the candidate lines it numbered. A
    finding may name only these sections and cite only these lines (a line the unit did not show was
    printed by the renderer or belongs to another unit)."""

    sections: frozenset[str]
    lines: frozenset[int]
    #: The shown lines that are attributed maintainer text (``scope.maintainer_lines``): kept as
    #: ``PRESERVE_ATTRIBUTED``, so an ``unsupported_claim`` citing only these is a contract error.
    #: Empty for a Lane L review, which has no such disposition.
    maintainer_lines: frozenset[int] = frozenset()


def valid_section_ids(plan: Mapping[str, Any] | None = None) -> frozenset[str]:
    """Every section id a finding may name: the renderer's shell, the plan's, and the two
    whole-document pseudo-sections."""
    planned = {
        str(entry.get("section_id"))
        for entry in (plan or {}).get("sections", [])
        if isinstance(entry, Mapping) and entry.get("section_id")
    }
    return frozenset({*section_ids(), *planned, *DOCUMENT_SECTIONS})


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _cited_section(candidate: str, first: int, last: int) -> str | list[str]:
    """The one section the cited lines belong to, or the reason they do not."""
    owners = section_lines(candidate)
    found = {owners[i] for i in range(first - 1, last)} - {None}
    if len(found) > 1:
        return [
            f"lines {first}-{last} cross more than one section ({', '.join(sorted(found))}); cite lines of one section"
        ]
    if found:
        return found.pop()
    headings = [
        i for i, row in enumerate(candidate.splitlines(), 1) if row.startswith("## ")
    ]
    return "opening" if not headings or last < headings[0] else "structure"


def _hidden(first: int, last: int, rows: list[str], scope: ReviewScope) -> list[int]:
    return [
        n
        for n in range(first, last + 1)
        if rows[n - 1].strip() and n not in scope.lines
    ]


def _numbers(numbers: list[int]) -> str:
    shown = ", ".join(str(n) for n in numbers[:6])
    return shown + (" ..." if len(numbers) > 6 else "")


def resolve_cited_lines(
    reply: Any, candidate_readme: str, scope: ReviewScope | None = None
) -> list[str]:
    """Replace each finding's model-written ``quote`` with the candidate's own text for the lines it
    cites (``lines``: ``[line]`` or ``[first, last]``, 1-based, as the numbered candidate in the
    packet shows them), and, for the kinds that are about the quoted text, set ``section_id`` to the
    section those lines are in. Edits ``reply`` in place, like a ``run_job`` check, and is idempotent,
    so a stored reply replays identically. Returns the reasons a citation cannot be used; a finding
    without ``lines`` is left to ``validate_review_reply``, which still demands a verbatim quote.

    With a ``scope`` (a sectionwise review unit) a line the unit did not show cannot be cited, for
    any kind. A contradiction or an unsupported claim cites at most ``MAX_CITED_LINES`` lines, every
    one shown; an omission, absence or quality finding may cite a whole section, whose first and last
    line must be shown. A whole-section citation of an omission or absence locates the section and is
    not a quote (``quote`` stays empty), so a string the section does contain is never treated as
    quoted by the finding that says it is missing.
    """
    findings = reply.get("findings") if isinstance(reply, Mapping) else None
    if not isinstance(findings, list):
        return []
    rows = candidate_readme.splitlines()
    problems: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("lines"):
            continue
        label = str(finding.get("id", "?"))
        cited = finding["lines"]
        if not isinstance(cited, list) or len(cited) not in (1, 2):
            problems.append(
                f"finding {label}: lines must be one or two line numbers, [line] or [first, last]"
            )
            continue
        if not all(_whole(n) for n in cited):
            problems.append(f"finding {label}: lines must be whole numbers")
            continue
        first, last = cited[0], cited[-1]
        kind = finding.get("claim_kind")
        whole = kind in WHOLE_SECTION_KINDS
        if first < 1 or last < 1:
            problems.append(f"finding {label}: line numbers start at 1")
            continue
        if last < first:
            problems.append(
                f"finding {label}: the first line after the last ({first} > {last})"
            )
            continue
        if last > len(rows):
            problems.append(
                f"finding {label}: the candidate has {len(rows)} lines; lines {first}-{last} do not exist"
            )
            continue
        if not whole and last - first + 1 > MAX_CITED_LINES:
            problems.append(
                f"finding {label}: cite at most {MAX_CITED_LINES} lines; lines {first}-{last} are {last - first + 1}"
            )
            continue
        if not any(row.strip() for row in rows[first - 1 : last]):
            problems.append(f"finding {label}: lines {first}-{last} are blank")
            continue
        if scope is not None:
            if whole:
                ends = sorted({first, last} - scope.lines)
                if ends:
                    problems.append(
                        f"finding {label}: the first and last line of a whole-section citation "
                        f"must be lines you were shown; line {_numbers(ends)} was not shown to you"
                    )
                    continue
            else:
                hidden = _hidden(first, last, rows, scope)
                if hidden:
                    problems.append(
                        f"finding {label}: lines {_numbers(hidden)} were not shown to you "
                        "(renderer-printed text or another review unit); cite only the numbered lines"
                    )
                    continue
                written = [n for n in range(first, last + 1) if rows[n - 1].strip()]
                if (
                    kind == "unsupported_claim"
                    and written
                    and all(n in scope.maintainer_lines for n in written)
                ):
                    # Only when EVERY cited line is the maintainers': a span that also cites an
                    # authored line may carry its claim there, and stays the model's to file.
                    problems.append(
                        f"finding {label}: lines {_numbers(written)} are maintainer_lines - "
                        f"{MAINTAINER_TEXT_ERROR}"
                    )
                    continue
        where = _cited_section(candidate_readme, first, last)
        if isinstance(where, list):
            problems.extend(f"finding {label}: {reason}" for reason in where)
            continue
        if whole and last - first + 1 > MAX_CITED_LINES:
            if kind == "quality":
                finding["quote"] = "\n".join(
                    rows[n - 1]
                    for n in range(first, last + 1)
                    if scope is None or n in scope.lines
                )
            else:
                finding["quote"] = ""
        else:
            finding["quote"] = "\n".join(rows[first - 1 : last])
        if kind not in ("omission", "absence"):
            finding["section_id"] = where
    return problems


#: Top-level key of a reply that records what ``drop_maintainer_unsupported_findings`` removed. Never read
#: by the verdict fold; ``llm_review._unit_record`` copies it into the unit's record so the drop is visible.
CONTRACT_NOTES_KEY = "contract_notes"


def drop_maintainer_unsupported_findings(
    reply: Any, candidate_readme: str, scope: ReviewScope | None = None
) -> list[dict[str, Any]]:
    """Remove each finding the contract itself calls void: an ``unsupported_claim`` whose every cited
    written line is attributed maintainer text (BL-660). ``resolve_cited_lines`` refuses such a
    finding (``MAINTAINER_TEXT_ERROR``), and the whole unit's review used to be lost after the one
    re-ask when the model filed it again (hosted PSD Java run 44952716923, unit u2: finding F01 on
    line 245, rejected twice, so no review at all and the candidate could not be judged).

    Dropping is safe because the finding asserts nothing the contract allows to be asserted: it says
    "no fact supports this maintainer sentence", and kept maintainer text needs no such support
    (docs/MAINTAINER_CONTENT_PRESERVATION.md). What stays untouched, and so still blocks: a finding
    of any other kind on those lines (contradiction, quality, omission, absence), a span that also
    cites an authored line, a line the unit did not show, and every deterministic check. The model's
    own verdict is kept as it is while another finding remains; when the drop leaves a REJECT verdict
    with no finding at all (its only ground was the void one) the unit's verdict is ACCEPT, since
    ``validate_review_reply`` refuses a reject without a finding and a retry would repeat the reply.
    Nothing is hidden: each drop (and a verdict change) is appended to ``reply[CONTRACT_NOTES_KEY]``,
    which the unit's record carries. A reply with no such finding is not touched, so a stored valid
    reply replays identically; idempotent. Returns the notes added by this call."""
    findings = reply.get("findings") if isinstance(reply, dict) else None
    if not isinstance(findings, list) or scope is None or not scope.maintainer_lines:
        return []
    rows = candidate_readme.splitlines()
    kept: list[Any] = []
    notes: list[dict[str, Any]] = []
    for finding in findings:
        cited = finding.get("lines") if isinstance(finding, dict) else None
        if (
            isinstance(finding, dict)
            and finding.get("claim_kind") == "unsupported_claim"
            and isinstance(cited, list)
            and len(cited) in (1, 2)
            and all(_whole(n) for n in cited)
            and 1 <= cited[0] <= cited[-1] <= len(rows)
            and cited[-1] - cited[0] + 1 <= MAX_CITED_LINES
            and not _hidden(cited[0], cited[-1], rows, scope)
        ):
            written = [n for n in range(cited[0], cited[-1] + 1) if rows[n - 1].strip()]
            if written and all(n in scope.maintainer_lines for n in written):
                notes.append(
                    {
                        "rule": "BL-660",
                        "dropped_finding": str(finding.get("id", "?")),
                        "claim_kind": "unsupported_claim",
                        "lines": written,
                        "reason": MAINTAINER_TEXT_ERROR,
                    }
                )
                continue
        kept.append(finding)
    if not notes:
        return []
    verdict = reply.get("verdict")
    if not kept and verdict in REJECT_VERDICTS:
        notes.append(
            {
                "rule": "BL-660",
                "verdict_changed": [verdict, MODEL_ACCEPT],
                "reason": "the reply's only finding was void by the contract; a reject verdict "
                "needs a finding",
            }
        )
        reply["verdict"] = MODEL_ACCEPT
    findings[:] = kept
    reply.setdefault(CONTRACT_NOTES_KEY, []).extend(notes)
    return notes


#: Error text (as ``resolve_cited_lines`` / ``_finding_errors`` word it) -> the class a drop records.
#: Order matters: the first match names the class. Every per-finding contract error is listed here.
_ERROR_CLASSES: tuple[tuple[str, str], ...] = (
    ("must cite at least one product fact", "no_product_fact"),
    ("maintainer_lines", "maintainer_text"),
    ("were not shown to you", "unshown_lines"),
    ("was not shown to you", "unshown_lines"),
    ("cite at most", "span_too_long"),
    ("cross more than one section", "cross_section"),
    ("are blank", "blank_lines"),
    ("do not exist", "lines_out_of_range"),
    ("lines must be", "malformed_lines"),
    ("line numbers start", "malformed_lines"),
    ("the first line after the last", "malformed_lines"),
    ("quote is not", "unlocatable_quote"),
    ("must quote the candidate text", "missing_quote"),
    ("renderer owns", "renderer_owned_quality"),
    ("fills no typed field", "typed_field"),
    ("must fill its typed field", "typed_field"),
    ("fills only its own typed field", "typed_field"),
    ("is text the finding's own quote shows is present", "absence_contradicted_by_quote"),
    ("claim_kind must", "claim_kind"),
    ("criterion must", "criterion"),
    ("causal_stage must", "causal_stage"),
    ("omission", "omission"),
    ("section_id", "section"),
    ("fact_ids", "fact_ids"),
    ("must be a non-empty string", "empty_text"),
    ("must be an object", "not_an_object"),
)


#: The dropped-finding classes that are void by the contract's own text although the finding is
#: well-formed and located (it names shown lines and a quote the candidate holds): it asserts a defect that
#: the contract says cannot be asserted that way, or one its own quote proves false. Only when every
#: dropped finding is of these classes may a reply left with no finding become an ACCEPT. A finding that
#: could not even be located or typed (a line the packet never had, a quote that is not the candidate's,
#: a missing field) leaves the model's REJECT standing without a finding, so the reply stays rejected and
#: retryable: it may have seen a defect it could not point at, and that is never counted clean.
VOID_BY_CONTRACT = frozenset(
    {"no_product_fact", "maintainer_text", "renderer_owned_quality", "absence_contradicted_by_quote"}
)


def _error_class(message: str) -> str:
    for needle, name in _ERROR_CLASSES:
        if needle in message:
            return name
    return "other"


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _repair_finding(
    finding: dict[str, Any],
    *,
    candidate_readme: str,
    facts: FactsDocument,
    sections: Collection[str],
) -> list[str]:
    """Deterministic repairs of one finding's own fields, each a statement the model already made in
    another field (never a new claim). Edits ``finding`` in place; returns what was repaired."""
    done: list[str] = []
    known = {fact.id: fact for fact in facts.facts}

    ids = finding.get("fact_ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        finding["fact_ids"] = []
        done.append("fact_ids was not a list of strings: emptied")
    elif any(i not in known for i in ids):
        unknown = [i for i in ids if i not in known]
        finding["fact_ids"] = [i for i in ids if i in known]
        done.append(f"fact_ids named facts not in the input, removed: {unknown[:4]}")

    for key in ("absent", "unsupported_names"):
        if key in finding and _strings(finding[key]) is None:
            finding[key] = []
            done.append(f"{key} was not a list of strings: emptied")

    text, repair = finding.get("text"), finding.get("repair")
    if _is_text(text) and not _is_text(repair):
        finding["repair"] = text.strip()
        done.append("repair was empty: the finding's text stands as the repair")
    elif _is_text(repair) and not _is_text(text):
        finding["text"] = repair.strip()
        done.append("text was empty: the finding's repair stands as the text")

    if finding.get("causal_stage") not in CAUSAL_STAGES:
        finding["causal_stage"] = "unclear"  # routing metadata only; 'unclear' is the sanctioned unknown
        done.append("causal_stage was not a stage: set to 'unclear'")

    cited = finding.get("lines")
    section = finding.get("section_id")
    rows = candidate_readme.splitlines()
    if (
        (not isinstance(section, str) or section not in sections)
        and isinstance(cited, list)
        and len(cited) in (1, 2)
        and all(_whole(n) for n in cited)
        and 1 <= cited[0] <= cited[-1] <= len(rows)
    ):
        where = _cited_section(candidate_readme, cited[0], cited[-1])
        if isinstance(where, str) and where in sections:
            finding["section_id"] = where
            done.append(f"section_id was not a section of the unit: the cited lines are in {where}")

    omission = finding.get("omission")
    if omission is not None:
        if not isinstance(omission, Mapping) or omission.get("kind") != "omission":
            finding["omission"] = None
            done.append("omission was not an omission object: cleared")
        else:
            fixed = dict(omission)
            ids_ = _strings(fixed.get("missing_ids"))
            quotes = _strings(fixed.get("missing_quotes"))
            fixed["missing_ids"] = [
                i for i in (ids_ or []) if i in known and known[i].polarity == "SUPPORTED"
            ]
            fixed["missing_quotes"] = quotes or []
            if isinstance(finding.get("section_id"), str):
                fixed["section_id"] = finding["section_id"]
            if fixed != dict(omission):
                finding["omission"] = fixed
                done.append("omission: ids that are not SUPPORTED facts of the input removed, section aligned")

    kind = finding.get("claim_kind")
    if kind in CLAIM_KINDS:
        filled = _filled(finding)
        clear = {"absence": ("absent", []), "name_denial": ("unsupported_names", []), "omission": ("omission", None)}
        if kind in UNTYPED_KINDS:
            for field_, value in filled.items():
                if value:
                    finding[clear[field_][0]] = clear[field_][1]
                    done.append(f"a {kind} finding fills no typed field: {field_} cleared")
        else:
            others = [k for k, v in filled.items() if v and k != kind]
            if others and filled[kind]:
                for other in others:
                    finding[clear[other][0]] = clear[other][1]
                    done.append(f"a {kind} finding fills only its own typed field: {other} cleared")
            elif len(others) == 1 and not filled[kind]:
                finding["claim_kind"] = others[0]
                kind = others[0]
                done.append(f"claim_kind relabelled to {others[0]}: the only typed field the finding fills")
        if kind == "omission" and finding.get("criterion") == "factuality":
            fact_ids = finding.get("fact_ids") or []
            if not any(i in known and known[i].kind != "inherited_unit" for i in fact_ids):
                body = finding.get("omission")
                missing = [
                    i for i in (body.get("missing_ids") or [])
                    if isinstance(body, Mapping) and i in known and known[i].kind != "inherited_unit"
                ] if isinstance(body, Mapping) else []
                if missing:
                    finding["fact_ids"] = [*fact_ids, *[i for i in missing if i not in fact_ids]]
                    done.append("fact_ids: the omission's own missing SUPPORTED facts cited")
    return done


def set_aside_void_findings(
    reply: Any,
    candidate_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any] | None = None,
    scope: ReviewScope | None = None,
    max_findings: int = MAX_FINDINGS,
) -> list[dict[str, Any]]:
    """BL-710: one finding that breaks the per-finding contract must not lose the unit's whole review.
    Generalises BL-660 (maintainer-only ``unsupported_claim``) to every contract error
    ``validate_review_reply`` / ``resolve_cited_lines`` can raise on ONE finding (hosted PSD Java run
    44985283929, unit u2: finding F06 'a contradiction finding must cite at least one product fact',
    rejected twice, so the unit and the candidate had no review).

    For each finding: first the repairs that are deterministic (``_repair_finding``: unknown or empty
    ``fact_ids`` emptied, an empty text/repair taken from its sibling, an unknown ``causal_stage`` set to
    'unclear', a section taken from the cited lines, an omission reduced to its SUPPORTED ids, a
    mislabelled typed field relabelled or cleared, an id that is malformed or repeated renumbered);
    a finding that still breaks the contract is dropped, and the drop is recorded. A dropped finding is
    one nothing can check: a contradiction that cites no product fact has nothing to be cleared
    against or confirmed by, a quote that is not in the candidate, lines the unit was not shown (renderer
    text or another unit's), a renderer-owned quality complaint, an unusable span. The deterministic
    claim detectors, the other review units and the second sample judge those lines; nothing here
    clears a finding that is valid. Over ``max_findings`` the first are kept (BL-690 precedent).

    The model's verdict stays while any finding is kept; when every finding was dropped and the verdict
    is a REJECT, it becomes ACCEPT only when every dropped finding was well-formed and located but void
    by the contract (``VOID_BY_CONTRACT``: no product fact cited, maintainer-only, renderer-owned, or
    disproved by its own quote; BL-660 precedent), with that change recorded; if any dropped finding could
    not even be located or typed the reply is left untouched and stays rejected (retryable). A reply the validator accepts is not
    touched (no notes), so a stored valid reply replays identically. Reply-level errors (an invalid
    verdict, ``findings`` not a list, an ACCEPT that carries findings, a REJECT with none to begin with)
    are left to the validator and the re-ask. Edits ``reply`` in place; idempotent. Returns the notes
    added, which ``reply[CONTRACT_NOTES_KEY]`` carries into the unit's record."""
    if not isinstance(reply, dict):
        return []
    findings = reply.get("findings")
    verdict = reply.get("verdict")
    if not isinstance(findings, list) or verdict not in MODEL_VERDICTS:
        return []
    sections = valid_section_ids(plan) if scope is None else scope.sections
    notes: list[dict[str, Any]] = []
    kept: list[Any] = []
    unlocatable = False
    for position, original in enumerate(findings, 1):
        if not isinstance(original, dict):
            notes.append({"rule": "BL-710", "action": "dropped", "finding": f"#{position}",
                          "class": "not_an_object", "reason": "a finding must be an object"})
            unlocatable = True
            continue
        label = str(original.get("id", "?"))
        working = dict(original)
        repairs = _repair_finding(
            working, candidate_readme=candidate_readme, facts=facts, sections=sections
        )
        probe = dict(working)
        probe["id"] = "F01"  # ids are renumbered below; they are not what makes a finding void
        errors = resolve_cited_lines({"findings": [probe]}, candidate_readme, scope)
        if not errors:
            errors = _finding_errors(
                probe, candidate_readme=candidate_readme, facts=facts,
                sections=sections, scoped=scope is not None,
            )
        if errors:
            reasons = [e.split(": ", 1)[-1] for e in errors]
            unlocatable = unlocatable or _error_class(errors[0]) not in VOID_BY_CONTRACT
            notes.append(
                {
                    "rule": "BL-710",
                    "action": "dropped",
                    "finding": label,
                    "claim_kind": original.get("claim_kind"),
                    "class": _error_class(errors[0]),
                    "lines": original.get("lines") if isinstance(original.get("lines"), list) else None,
                    "reason": "; ".join(reasons)[:400],
                }
            )
            continue
        if repairs:
            original.clear()
            original.update(working)
            notes.append({"rule": "BL-710", "action": "repaired", "finding": label, "repairs": repairs})
        kept.append(original)
    if not kept and verdict in REJECT_VERDICTS and unlocatable:
        return []  # a REJECT whose findings could not even be located stays rejected (retryable), untouched
    if len(kept) > max_findings:
        notes.append(
            {"rule": "BL-710", "action": "dropped", "class": "too_many_findings",
             "reason": f"{len(kept) - max_findings} finding(s) after the first {max_findings} set aside; "
                       "the verdict is unchanged and the next review round reports what remains"}
        )
        del kept[max_findings:]
    used = {f["id"] for f in kept if isinstance(f.get("id"), str) and _ID.fullmatch(f["id"])}
    seen: set[str] = set()
    counter = 0
    for finding in kept:
        current = finding.get("id")
        if isinstance(current, str) and _ID.fullmatch(current) and current not in seen:
            seen.add(current)
            continue
        while f"F{counter + 1:02d}" in used:
            counter += 1
        counter += 1
        fresh = f"F{counter:02d}"
        notes.append({"rule": "BL-710", "action": "repaired", "finding": str(current),
                      "repairs": [f"id was malformed or repeated: renumbered {fresh}"]})
        finding["id"] = fresh
        used.add(fresh)
        seen.add(fresh)
    if _strings(reply.get("preserve")) is None:
        reply["preserve"] = []
        notes.append({"rule": "BL-710", "action": "repaired", "finding": "reply",
                      "repairs": ["preserve was not a list of strings: emptied"]})
    dropped = any(n["action"] == "dropped" for n in notes)
    if dropped and not kept and verdict in REJECT_VERDICTS:
        notes.append(
            {"rule": "BL-710", "action": "verdict_changed", "verdict_changed": [verdict, MODEL_ACCEPT],
             "reason": "every finding of the reply was void by the contract; a reject verdict needs a finding"}
        )
        reply["verdict"] = MODEL_ACCEPT
    if not notes:
        return []
    findings[:] = kept
    reply.setdefault(CONTRACT_NOTES_KEY, []).extend(notes)
    return notes


#: Shortest ``text`` (and shortest line) the citation repair will match by content: shorter strings
#: occur in too many lines to say which one a finding is about.
MIN_REPAIR_CHARS = 12


def repair_miscited_lines(
    reply: Any, candidate_readme: str, scope: ReviewScope | None = None
) -> None:
    """Move a single-line citation the contract would refuse to the one shown line that prints the
    finding's own ``text`` (BL-561). The reviewer numbers a line it quotes correctly in ``text`` one or
    two off (hosted audit round 4: the sentence on line 199 cited as the blank line 200, repeated after
    the re-ask, so the unit had no valid review and the whole batch died). The words are the model's, the
    place is arithmetic: when the finding's ``text`` is verbatim in exactly one shown line, that line
    is the one it is about. Applied only where ``resolve_cited_lines`` would refuse the citation, to a
    contradiction or unsupported claim citing one line, and only when the match is unique; a valid
    citation, a whole-section kind, a span and a text that locates nowhere or in several lines are
    untouched, so a stored valid reply replays identically. Edits ``reply`` in place; idempotent."""
    findings = reply.get("findings") if isinstance(reply, Mapping) else None
    if not isinstance(findings, list):
        return
    rows = candidate_readme.splitlines()
    shown = [
        n for n in (sorted(scope.lines) if scope is not None else range(1, len(rows) + 1))
        if 1 <= n <= len(rows) and rows[n - 1].strip()
    ]
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("claim_kind") in WHOLE_SECTION_KINDS:
            continue
        cited = finding.get("lines")
        if not isinstance(cited, list) or not cited or not all(_whole(n) for n in cited):
            continue
        if len(cited) not in (1, 2) or cited[0] != cited[-1]:
            continue
        if not resolve_cited_lines({"findings": [dict(finding)]}, candidate_readme, scope):
            continue
        label, body = _line_label(str(finding.get("text") or ""))
        text = spaced(str(finding.get("text") or ""))
        if len(text) < MIN_REPAIR_CHARS:
            continue
        found = [
            n for n in shown
            if text in spaced(rows[n - 1])
            or (len(spaced(rows[n - 1])) >= MIN_REPAIR_CHARS and spaced(rows[n - 1]) in text)
        ]
        if len(found) == 1:
            finding["lines"] = [found[0]]
            continue
        # BL-630: the packet numbers a line ``0209| ...`` and the reviewer writes ``Line 0209: ...`` in
        # its text but a truncated ``lines: [9]`` (hosted 3D TypeScript run 44924648803: lines 9, 26,
        # 28, 29, 33 for 0209, 0226, 0228, 0229, 0233, so the whole review was lost twice). The label
        # the model itself printed names the line; it is used only when that line is shown and prints
        # the finding's own words once the table or list markup around them is set aside.
        loose = _loosely(body)
        if label in shown and len(loose) >= MIN_REPAIR_CHARS:
            row = _loosely(rows[label - 1])
            if len(row) >= MIN_REPAIR_CHARS and (loose in row or row in loose):
                finding["lines"] = [label]


#: ``Line 0209:`` / ``line 209 -`` / ``0209|`` at the start of a finding's text: the packet's own line label.
_LINE_LABEL = re.compile(r"^\s*(?:lines?\s+)?0*([0-9]{1,6})\s*(?:[:|)\]]|-+|\.\s)\s*", re.IGNORECASE)


def _line_label(text: str) -> tuple[int | None, str]:
    """The line number a finding's text labels itself with, and the text without the label."""
    match = _LINE_LABEL.match(text)
    if match is None or not match.group(1):
        return None, text
    return int(match.group(1)), text[match.end():]


def _loosely(text: str) -> str:
    """``text`` compared without table pipes, list markers, backticks and emphasis, so the sentence a
    finding quotes matches the row or bullet that prints it."""
    stripped = re.sub(r"[|`*_]", " ", text)
    return spaced(re.sub(r"^\s*(?:[-+]|[0-9]+\.)\s+", "", stripped.strip()))


def _repeat_key(finding: Mapping[str, Any]) -> tuple[Any, ...]:
    omission = finding.get("omission")
    return (
        finding.get("claim_kind"),
        finding.get("section_id") if not finding.get("lines") else None,
        tuple(finding.get("lines") or ()),
        tuple(finding.get("absent") or ()),
        tuple(finding.get("unsupported_names") or ()),
        None
        if not isinstance(omission, Mapping)
        else (
            omission.get("section_id"),
            tuple(omission.get("missing_ids") or ()),
            tuple(omission.get("missing_quotes") or ()),
        ),
    )


def merge_repeated_findings(reply: Any) -> None:
    """Fold findings of one claim kind that cite the same lines (or name the same typed claim) into
    the first of them. A repeat adds no defect: iteration 2 saw one reply file the same finding 29
    times. The first finding stays BLOCKING and its text records how many repeats it absorbed. Edits
    ``reply`` in place and is idempotent."""
    findings = reply.get("findings") if isinstance(reply, Mapping) else None
    if not isinstance(findings, list):
        return
    kept: dict[tuple[Any, ...], dict[str, Any]] = {}
    absorbed: dict[tuple[Any, ...], int] = {}
    ordered: list[Any] = []
    for finding in findings:
        if not isinstance(finding, dict):
            ordered.append(finding)
            continue
        key = _repeat_key(finding)
        if key in kept:
            absorbed[key] = absorbed.get(key, 0) + 1
            continue
        kept[key] = finding
        ordered.append(finding)
    for key, count in absorbed.items():
        first = kept[key]
        note = f" (+{count} identical findings merged)"
        text = str(first.get("text", ""))
        if not text.endswith(note):
            first["text"] = text[: TEXT_LIMIT - len(note)] + note
    findings[:] = ordered


def _strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _filled(finding: Mapping[str, Any]) -> dict[str, bool]:
    omission = finding.get("omission")
    omission_filled = isinstance(omission, Mapping) and bool(
        omission.get("missing_ids") or omission.get("missing_quotes")
    )
    return {
        "absence": bool(finding.get("absent")),
        "name_denial": bool(finding.get("unsupported_names")),
        "omission": omission_filled,
    }


def _finding_errors(
    finding: Any,
    *,
    candidate_readme: str,
    facts: FactsDocument,
    sections: Collection[str],
    scoped: bool = False,
) -> list[str]:
    if not isinstance(finding, Mapping):
        return ["a finding must be an object"]
    label = str(finding.get("id", "?"))
    errors: list[str] = []

    def bad(message: str) -> None:
        errors.append(f"finding {label}: {message}")

    if not isinstance(finding.get("id"), str) or not _ID.fullmatch(finding["id"]):
        bad("id must look like F01")
    section = finding.get("section_id")
    if not isinstance(section, str) or section not in sections:
        if scoped:
            bad(
                f"section_id {section!r} is not a section of this review unit "
                f"({', '.join(sorted(sections))})"
            )
        else:
            bad(
                f"section_id must be a shell or plan section or 'structure'; got {section!r}"
            )
        section = None
    if finding.get("causal_stage") not in CAUSAL_STAGES:
        bad(f"causal_stage must be one of {', '.join(CAUSAL_STAGES)}")
    criterion = finding.get("criterion")
    if criterion not in CRITERIA:
        bad(f"criterion must be one of {', '.join(CRITERIA)}")
    for key in ("text", "repair"):
        if not isinstance(finding.get(key), str) or not finding[key].strip():
            bad(f"{key} must be a non-empty string")
    kind = finding.get("claim_kind")
    if kind not in CLAIM_KINDS:
        bad(f"claim_kind must be one of {', '.join(CLAIM_KINDS)}")

    quote = finding.get("quote", "")
    if not isinstance(quote, str):
        bad("quote must be a string")
        quote = ""
    elif quote.strip():
        scope = section_scope(section, candidate_readme) if section else None
        haystack = candidate_readme if scope is None else scope
        if not quote_located(quote, haystack):
            where = (
                "the candidate"
                if scope is None
                else f"the candidate's {section} section"
            )
            bad(
                f"quote is not {where}'s text, character for character: {quote.strip()[:60]!r}"
            )
    elif kind in QUOTED_KINDS:
        bad(
            f"a {kind} finding must quote the candidate text it is about: cite its "
            "`lines` ([line] or [first, last])"
        )

    known = {fact.id: fact for fact in facts.facts}
    fact_ids = _strings(finding.get("fact_ids"))
    if fact_ids is None:
        bad("fact_ids must be a list of strings")
        fact_ids = []
    for fact_id in fact_ids:
        if fact_id not in known:
            bad(f"fact_ids names {fact_id!r}, which is not a fact in the input")
    needs_fact = kind == "contradiction" or (
        criterion == "factuality" and kind not in FACTLESS_KINDS
    )
    if needs_fact and not any(
        fact_id in known and known[fact_id].kind != "inherited_unit"
        for fact_id in fact_ids
    ):
        bad(
            f"a {kind} finding must cite at least one product fact (not only inherited text)"
        )
    if kind == "quality" and section in RENDERER_OWNED:
        bad(
            f"the renderer owns the {section} section's wording and layout, so a quality "
            "finding against it is outside your scope; report a factual error as a "
            "contradiction citing the fact it contradicts"
        )

    absent = _strings(finding.get("absent", []))
    names = _strings(finding.get("unsupported_names", []))
    if absent is None or names is None:
        bad("absent and unsupported_names must be lists of strings")
        absent, names = absent or [], names or []
    omission = finding.get("omission")
    if omission is not None:
        if not isinstance(omission, Mapping) or omission.get("kind") != "omission":
            bad("omission must be null or an object with kind 'omission'")
        else:
            ids = _strings(omission.get("missing_ids"))
            quotes = _strings(omission.get("missing_quotes"))
            if ids is None or quotes is None:
                bad("omission.missing_ids and missing_quotes must be lists of strings")
            else:
                if omission.get("section_id") != section:
                    bad("omission.section_id must equal the finding's own section_id")
                for fact_id in ids:
                    fact = known.get(fact_id)
                    if fact is None:
                        bad(
                            f"omission names {fact_id!r}, which is not a fact in the input"
                        )
                    elif fact.polarity != "SUPPORTED":
                        bad(
                            f"omission names {fact_id!r}, which is {fact.polarity}: the contract "
                            "never lets a section state it, so it is not an omission"
                        )

    if kind in CLAIM_KINDS:
        filled = _filled(finding)
        if kind in UNTYPED_KINDS:
            if any(filled.values()):
                bad(
                    f"a {kind} finding fills no typed field (absent, unsupported_names, "
                    "omission); file the typed claim as its own finding"
                )
        else:
            if not filled[kind]:
                bad(f"a {kind} finding must fill its typed field")
            if any(value for other, value in filled.items() if other != kind):
                bad(
                    f"a {kind} finding fills only its own typed field; other typed claims are mislabelled"
                )
        if kind == "absence" and quote.strip():
            own = spaced(quote)
            for item in absent:
                if spaced(item) and spaced(item) in own:
                    bad(
                        f"absent {item!r} is text the finding's own quote shows is present; "
                        "an absence claim names text the candidate lacks"
                    )
    return errors


def validate_review_reply(
    reply: Any,
    *,
    candidate_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any] | None = None,
    scope: ReviewScope | None = None,
    max_findings: int = MAX_FINDINGS,
) -> list[str]:
    """Why a parsed reply may not be used; empty when it holds. Pure; safe as ``run_job`` checks.
    With a ``scope`` a finding names only that review unit's sections."""
    if not isinstance(reply, Mapping):
        return ["the reply must be one JSON object"]
    errors: list[str] = []
    verdict = reply.get("verdict")
    if verdict not in MODEL_VERDICTS:
        errors.append(f"verdict must be one of {', '.join(MODEL_VERDICTS)}")
    findings = reply.get("findings")
    if not isinstance(findings, list):
        return [*errors, "findings must be a list"]
    if _strings(reply.get("preserve")) is None:
        errors.append("preserve must be a list of strings")
    if len(findings) > max_findings:
        errors.append(f"at most {max_findings} findings; got {len(findings)}")
    if verdict == "ACCEPT" and findings:
        errors.append("an ACCEPT verdict carries no findings")
    if verdict in REJECT_VERDICTS and not findings:
        errors.append(f"a {verdict} verdict carries at least one finding")
    sections = valid_section_ids(plan) if scope is None else scope.sections
    seen: set[str] = set()
    for finding in findings:
        errors.extend(
            _finding_errors(
                finding,
                candidate_readme=candidate_readme,
                facts=facts,
                sections=sections,
                scoped=scope is not None,
            )
        )
        label = finding.get("id") if isinstance(finding, Mapping) else None
        if isinstance(label, str):
            if label in seen:
                errors.append(f"finding {label}: its id repeats an earlier finding")
            seen.add(label)
    return errors


def findings_from_reply(reply: Mapping[str, Any]) -> tuple[Finding, ...]:
    """The BLOCKING findings of a reply that ``validate_review_reply`` accepted."""
    found: list[Finding] = []
    for raw in reply["findings"]:
        omission = raw.get("omission")
        found.append(
            Finding(
                rule=f"llm:{raw['criterion']}",
                source="llm",
                message=raw["text"],
                claim_kind=raw["claim_kind"],
                quote=raw.get("quote", ""),
                finding_id=raw["id"],
                section_id=raw["section_id"],
                causal_stage=raw["causal_stage"],
                criterion=raw["criterion"],
                fact_ids=tuple(raw["fact_ids"]),
                absent=tuple(raw.get("absent", [])),
                unsupported_names=tuple(raw.get("unsupported_names", [])),
                omission=None
                if omission is None
                else OmissionClaim(
                    section_id=omission["section_id"],
                    missing_ids=tuple(omission["missing_ids"]),
                    missing_quotes=tuple(omission["missing_quotes"]),
                ),
                repair=raw["repair"],
            )
        )
    return tuple(found)


def _audited(
    finding: Finding, candidate_readme: str, original_readme: str, facts: FactsDocument
) -> Finding:
    """An unsupported claim with the audit of its distinctive terms recorded as its evidence."""
    if finding.claim_kind != "unsupported_claim":
        return finding
    audit = audit_unsupported_claim(
        finding.quote, facts=facts, original_readme=original_readme
    )
    return replace(finding, evidence=audit)


def review_from_reply(
    reply: Any,
    *,
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any] | None,
    deterministic_findings: Sequence[Finding],
    prompt_version: str,
    model_served: str,
    request_sha256: str,
    reply_sha256: str,
    max_findings: int = MAX_FINDINGS,
    calibration_status: str | None = None,
    unit_reviews: Sequence[Mapping[str, Any]] = (),
    derive: Deriver | None = None,
) -> ReviewVerdict:
    """The verdict for one reply: validate, clear what a registered clearance proves false, fold.
    Raises ``ReviewUnavailable`` (retryable, never an ACCEPT) when the reply breaks the contract.
    For a sectionwise review ``reply`` is the units' merged reply, which may hold more findings than
    one unit's reply may (``max_findings``)."""
    errors = validate_review_reply(
        reply,
        candidate_readme=candidate_readme,
        facts=facts,
        plan=plan,
        max_findings=max_findings,
    )
    if errors:
        raise ReviewUnavailable("the reviewer's reply broke the contract", errors)
    context = ClearanceContext(candidate_readme, original_readme, facts, derive)
    llm_findings = tuple(
        apply_clearances(_audited(f, candidate_readme, original_readme, facts), context)
        for f in findings_from_reply(reply)
    )
    return ReviewVerdict.folded(
        (*deterministic_findings, *llm_findings),
        model_verdict=reply["verdict"],
        prompt_version=prompt_version,
        model_served=model_served,
        request_sha256=request_sha256,
        reply_sha256=reply_sha256,
        calibration_status=calibration_status,
        unit_reviews=unit_reviews,
    )
