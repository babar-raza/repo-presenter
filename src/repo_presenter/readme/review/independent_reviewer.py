"""This repository's own independent, non-authoring reviewer (Gate A, mission section 11:
"independent non-authoring criticism that can veto, with no quiet demotion").

BUILD_INDEPENDENT_REVIEWER (``project/state.yaml``) found the old repository's ``review.py``/
``judge.py`` disqualified from a verbatim port: ``judge.py`` depends on a sealed bundle/manifest
layout this repository does not have, and ``review.py`` is a 2,996-line, 21-version module built
on top of a repair loop (``repair/rounds.py``) and renderer-chrome string matches this repository
also does not have. Only one pattern survives the port, named explicitly in
``migration/reuse-manifest.yaml`` entry #1: the DETERMINISTIC_RULES / JUDGMENT_RULES split, where
a deterministic rule may refute a candidate (``Finding.refuted_by``) and a judgment rule may only
annotate -- it can never fold a REJECT back to ACCEPT. That split is rebuilt from scratch here,
against this repository's own evidence shapes, not ported. (Superseded by reviewer logic "4":
see ``readme.review.findings`` -- there is no annotate-only tier any more; every LLM finding
blocks until a registered clearance proves it false, and the one fold is
``readme.review.verdict.fold_verdict``.)

The old repository's own measured incident (``docs/MISSION_AUTHORITY.md``'s "critical fact":
pre-2026-10-10, 27/30 real REJECT findings were wrongly folded to ACCEPT whenever a finding's
quoted span happened to also match a literal SUPPORTED fact value elsewhere in the candidate) is
why the fold is deliberately isolated in ``readme.review.verdict.fold_verdict`` and structurally
cannot be subverted: ``ReviewVerdict.__post_init__`` re-runs the fold and ``Finding.__post_init__``
refuses a CLEARED finding without a valid clearance proof -- enforced by construction, not by
convention.

Scope (deliberately bounded, per the mission's P1 "smallest working... + independent verifier"
discipline -- see ``project/state.yaml``'s ``BUILD_INDEPENDENT_REVIEWER`` card for the full
reasoning). Every rule is deterministic and reuses an already-proven primitive where one exists:

- ``claim_contradiction``: a factual holdout, via ``readme.validation.claims.claim_findings``.
- ``duplicate_opening_paragraph``: a preservation holdout, via
  ``readme.composition.authoring.preserved_opening_text`` + ``readme.composition.coverage.states_all``.
- ``duplicate_paragraph``: the same prose paragraph (120 characters or more) printed twice; the model
  caught none of four injected repeats in iteration 2, and a repeat is provable by comparing text.
- ``disposition_coverage``: every inherited unit has exactly one disposition, names no unknown unit,
  and a kept unit's text is printed in the README (the old ``judge.py`` J4 clause, rebuilt here as
  a rule over this repository's own evidence shapes).
- ``live_readme_loss``: the candidate loses no live heading, fenced block, link target or verified
  install command unless a disposition accounts for it (the old ``judge.py`` J6 clause, ported as a
  rule). Unlike the old clause it does not depend on the live README's position in a hard-coded
  standard: it applies to every repository, because the mission makes the live README the
  reference for what must be kept.
- The LLM reviewer's pure-code core lives beside this module (``findings``, ``clearances``,
  ``reply``, ``verdict``, ``verdict_io``); this module keeps the deterministic rules and
  re-exports the names its callers import. The old repository's demotion/second-read machinery
  (``readme/review/independent/review.py``) is not ported; see ``migration/reuse-manifest.yaml``
  for the per-function disposition.
- No repair hand-off: a REJECT verdict is advisory-and-blocking (it is read by
  ``propose.effect.propose_candidate`` as a required gate -- see that module) but does not feed
  ``readme.repair.targeted``'s defect-classification layer yet. That remains open, deliberately,
  per ``BUILD_INDEPENDENT_REVIEWER``'s next_step: "decide where this repository hands a REJECT
  finding" is still unresolved and is not decided implicitly by this file.
- No forest-acceptance breadth yet (mission section 11's full differential-fixture suite across
  every ecosystem/size/defect-class combination). That is explicitly a mission P2 "generalize by
  failure class, not anecdote" activity, run *after* a first proof on real evidence -- which is
  what this module's own test file demonstrates, using exactly the real, previously-encountered
  cases already on record in this project (the ninth- and sixth-cascade duplicate-opening
  fixtures already proven in ``tests/readme/composition/test_authoring.py``).

Running this reviewer against this repository's existing 36 Lane L / 34 Lane R candidates is a
first-ever independent review pass, not a reseal of already-accepted work: per the owner's own
2026-10-24 correction (``project/state.yaml``'s ``owner_review_status`` note), none of those
candidates carry owner acceptance, and none of them have ever been checked by any independent
reviewer before now (``SALVAGE_INVENTORY_2026_10_23`` found zero review/judge/acceptance code in
this repository). A REJECT this module finds against one of them is a new finding against
mission non-negotiable #3 ("consumed-scope invalidation only"), not a global reseal: nothing
re-opens other than the one candidate actually found defective.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.authoring import preserved_opening_text
from repo_presenter.readme.composition.coverage import (
    carries_hard_tokens,
    partly_printed,
    states_all,
)
from repo_presenter.readme.composition.list_coverage import list_items, missing_items
from repo_presenter.readme.evidence.facts.links import extract_links
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.matching import plain
from repo_presenter.readme.review.scope import reviewable_lines
from repo_presenter.readme.review.verdict import (
    REVIEW_VERDICT_FILENAME,
    REVIEWER_LOGIC_VERSION,
    ReviewUnavailable,
    ReviewVerdict,
    Verdict,
    fold_verdict,
)
from repo_presenter.readme.review.verdict_io import (
    ReviewVerdictError,
    load_review_verdict,
    write_review_verdict,
)
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.text import section_texts

#: The reviewer's public surface: callers import the finding model, verdict, fold and verdict-file
#: functions from here (cascade, present, repair, propose, scripts).
__all__ = [
    "REVIEWER_LOGIC_VERSION",
    "REVIEW_VERDICT_FILENAME",
    "Finding",
    "ReviewUnavailable",
    "ReviewVerdict",
    "ReviewVerdictError",
    "Verdict",
    "claim_contradiction_rule",
    "disposition_coverage_rule",
    "duplicate_opening_paragraph_rule",
    "duplicate_paragraph_rule",
    "fold_verdict",
    "heading_printed",
    "live_readme_loss_rule",
    "load_review_verdict",
    "review_candidate",
    "unprinted_kept_units",
    "write_review_verdict",
]


def claim_contradiction_rule(readme_text: str, facts: FactsDocument) -> list[Finding]:
    """Factual holdout (mission section 11: "adversarial factual... holdouts"). Reuses
    ``readme.validation.claims.claim_findings`` verbatim -- the claim-vs-fact contradiction
    detector this repository already has, independently proven, rather than re-deriving it."""
    lines = readme_text.splitlines()
    findings = []
    for finding in claim_findings(readme_text, facts):
        quote = lines[finding.line] if 0 <= finding.line < len(lines) else ""
        findings.append(
            Finding(
                rule="claim_contradiction",
                source="deterministic",
                claim_kind="contradiction",
                message=f"line {finding.line} ({finding.stage}): {finding.detail}",
                evidence=finding.detail,
                quote=quote,
            )
        )
    return findings


def duplicate_opening_paragraph_rule(
    units: Sequence[Mapping[str, Any]],
    *,
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
) -> list[Finding]:
    """Preservation / previous-regression holdout (mission section 11: "...preservation
    holdouts"). The exact, previously-encountered defect class this project's
    ``recover_opening_duplicates_preserved`` partially corrects inline during authoring -- this
    rule re-checks the *final* persisted output independently, using the same underlying
    primitives (``preserved_opening_text``, ``states_all``) but never trusting that the inline
    guard actually fired or succeeded."""
    preserved = preserved_opening_text(dispositions, facts)
    if not preserved:
        return []
    for unit in units:
        if unit.get("section") != "opening":
            continue
        text = unit.get("text")
        if not isinstance(text, str) or not text:
            continue
        if states_all(preserved, text) or states_all(text, preserved):
            return [
                Finding(
                    rule="duplicate_opening_paragraph",
                    source="deterministic",
                    message=(
                        "the 'opening' unit restates the inherited preserved paragraph placed "
                        "beside it rather than adding genuinely new content"
                    ),
                    evidence=f"preserved={preserved!r} authored={text!r}",
                    quote=text,
                )
            ]
        break
    return []


#: Shortest prose paragraph a repeat is a defect for: a short sentence is repeated legitimately.
MIN_DUPLICATE_CHARS = 120
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def duplicate_paragraph_rule(readme_text: str) -> list[Finding]:
    """Preservation holdout: the candidate does not print the same author-written prose paragraph
    twice. Paragraphs are read from the lines a reviewer may be shown (``review.scope``: no fence,
    table, heading, HTML or renderer-owned section), a list item is not a paragraph, and the texts are
    compared as a reader sees them (Markdown syntax, case and spacing aside)."""
    rows = readme_text.splitlines()
    paragraphs: list[list[str]] = []
    previous = None
    for number in reviewable_lines(readme_text):
        row = rows[number - 1]
        if _LIST_ITEM.match(row):
            previous = None
            continue
        if previous is not None and number == previous + 1:
            paragraphs[-1].append(row)
        else:
            paragraphs.append([row])
        previous = number
    seen: dict[str, list[str]] = {}
    for lines in paragraphs:
        text = "\n".join(lines)
        key = " ".join(plain(text).casefold().split())
        if len(key) >= MIN_DUPLICATE_CHARS:
            seen.setdefault(key, []).append(text)
    return [
        Finding(
            rule="duplicate_paragraph",
            source="deterministic",
            message="the candidate prints the same prose paragraph more than once",
            evidence=f"the paragraph occurs {len(copies)} times",
            quote=copies[0],
        )
        for copies in seen.values()
        if len(copies) > 1
    ]


#: Kept units must print verbatim (judge.py J4); these dispositions account for a live loss (J6).
KEPT_DISPOSITIONS: frozenset[str] = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
ACCOUNTING_DISPOSITIONS: frozenset[str] = frozenset(
    {
        "SUPERSEDE_REDUNDANT",
        "CORRECT_WITH_EVIDENCE",
        "VERIFIED_REWRITE",
        "OMIT_UNSUPPORTED",
    }
)

_MARKDOWN = MarkdownIt("commonmark").enable(["table", "strikethrough"])
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _squeezed(text: str) -> str:
    return " ".join(text.split())


def _heading_key(text: str) -> str:
    """A heading's comparison form: letters and digits only, lower case, ``&`` read as ``and``.
    The renderer re-levels and re-cases headings, which is not a loss of their text."""
    return _NON_ALNUM.sub(" ", text.casefold().replace("&", " and ")).strip()


def _code(text: str) -> str:
    """A fenced block or command as a reader compares it: line ends and trailing spaces aside."""
    return "\n".join(
        line.rstrip() for line in text.replace("\r\n", "\n").splitlines()
    ).strip()


def _inline_text(inline: Token) -> str:
    parts: list[str] = []
    for child in inline.children or []:
        if child.type in {"text", "code_inline", "image"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts).strip()


@dataclass(frozen=True)
class _Markdown:
    headings: tuple[str, ...]
    fences: tuple[str, ...]


def _read_markdown(text: str) -> _Markdown:
    tokens = _MARKDOWN.parse(text)
    headings: list[str] = []
    fences: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            headings.append(_inline_text(tokens[index + 1]))
        elif token.type == "fence":
            fences.append(_code(token.content))
    return _Markdown(tuple(headings), tuple(fences))


def _inherited_units(facts: FactsDocument) -> dict[str, str]:
    return {
        fact.id: fact.value for fact in facts.facts if fact.kind == "inherited_unit"
    }


def _dispositions_list(dispositions: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = dispositions.get("dispositions", [])
    return [row for row in rows if isinstance(row, Mapping)]


def heading_printed(unit_text: str, readme_text: str) -> bool:
    """Whether a README heading has the same comparison form as the inherited heading
    ``unit_text``: the one test ``live_readme_loss_rule`` loses a heading by."""
    wanted = _heading_key(unit_text.lstrip("#").strip())
    return any(
        _heading_key(text) == wanted for text in _read_markdown(readme_text).headings
    )


def _list_items_stated(
    unit_text: str, destination: str | None, readme_text: str
) -> bool:
    """Whether a kept list the renderer printed in part is retained: at least one item is in the
    README as written, and every item is in the README, by its link when it has one, else by its
    subject words in the destination section. BC-05's own standard for a list the renderer prints
    only in part, because it prints just the items the section's own content does not already
    state (``validation.units._dropped_list_failures``).

    A list with no item printed as written is not this case: it is wholly restated, and the S9
    accounting supersedes it without changing the render. Here that would delete the items that
    are printed, so the list is judged retained instead."""
    if destination is None:
        return False
    squeezed = _squeezed(readme_text)
    if not any(_squeezed(item) in squeezed for item in list_items(unit_text)):
        return False
    stated = section_texts(readme_text).get(destination, "")
    return not missing_items(
        unit_text,
        stated,
        by_link=destination == "documentation_resources",
        document_text=readme_text,
    )


def _kept_text_printed(
    unit_text: str,
    unit_id: str,
    readme_text: str,
    destination: str | None = None,
) -> bool:
    if unit_id.endswith(".heading"):
        # A heading is printed only as a heading. A substring match would call
        # "### Convert a Lambert Material to PBR" printed because the README says
        # "### Convert a Lambert Material to PBR Material", while live_readme_loss_rule (which
        # compares whole headings) reports it lost: the two rules must agree.
        return heading_printed(unit_text, readme_text)
    if _squeezed(unit_text) in _squeezed(readme_text):
        return True
    # A list is retained when every one of its items is: the renderer prints only the items its
    # section does not already state, so a fully stated list is rarely one verbatim block.
    if unit_id.endswith(".list") and _list_items_stated(
        unit_text, destination, readme_text
    ):
        return True
    # Placement (``composition/coverage.py``'s own ``uncovered``/``uncovered_block``) may keep a
    # paragraph or table only in part, printing just the sentences a destination section -- or a
    # section it is read together with (``placement.py``'s "also") -- does not already state,
    # verbatim. That is not a silent drop: the same shape is recognized here, independently of the
    # renderer's own fact-ID bookkeeping, by the same sentence-overlap test placement rests its
    # drop on (``states_all``, already proven for ``duplicate_opening_paragraph``) -- guarded by
    # two things placement's own trim always leaves true of a genuine remainder, never of a unit
    # entirely paraphrased away: every link or command the unit carries is still somewhere in the
    # document (``hard_tokens``), and at least one sentence of it is printed word for word, not
    # merely restated (``partly_printed``) -- so a unit nothing of which actually survives is still
    # correctly judged lost, not waved through on a family resemblance.
    if unit_id.rsplit(".", 1)[-1] not in {"paragraph", "list", "table"}:
        return False
    carries_all = carries_hard_tokens(unit_text, readme_text)
    return (
        carries_all
        and partly_printed(unit_text, readme_text)
        and states_all(readme_text, unit_text)
    )


def unprinted_kept_units(
    readme_text: str,
    *,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
) -> list[tuple[str, str]]:
    """``(unit_id, disposition)`` for each kept unit whose text the README does not print: the
    one test ``disposition_coverage_rule`` judges by, shared with the stage that accounts for
    such a unit (``readme.repair.accounting``) so the two can never disagree about "printed"."""
    units = _inherited_units(facts)
    return [
        (unit, str(row.get("disposition")))
        for row in _dispositions_list(dispositions)
        if row.get("disposition") in KEPT_DISPOSITIONS
        and (unit := str(row.get("unit_id", ""))) in units
        and not _kept_text_printed(
            units[unit], unit, readme_text, row.get("destination_section")
        )
    ]


def disposition_coverage_rule(
    readme_text: str,
    *,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
) -> list[Finding]:
    """Preservation holdout (judge.py J4): every inherited unit has exactly one disposition, no
    disposition names a unit the facts do not carry, and every kept unit's text is printed in the
    README. Each defect is a deterministic refutation: the candidate is provably incomplete."""
    units = _inherited_units(facts)
    rows = _dispositions_list(dispositions)
    counts = Counter(str(row.get("unit_id", "")) for row in rows)
    problems: list[tuple[str, str]] = []
    for unit in units:
        if counts.get(unit, 0) != 1:
            problems.append(
                (unit, f"{unit} has {counts.get(unit, 0)} dispositions, not one")
            )
    for unit in counts:
        if unit not in units:
            problems.append(
                (unit, f"{unit} is named by a disposition but is not an inherited unit")
            )
    for unit, disposition in unprinted_kept_units(
        readme_text, facts=facts, dispositions=dispositions
    ):
        message = (
            f"{unit} is kept ({disposition}) but its text is not printed in the README"
        )
        problems.append((units[unit], message))
    return [
        Finding(
            rule="disposition_coverage",
            source="deterministic",
            claim_kind="omission",
            message=message,
            evidence=message,
            quote=quote,
        )
        for quote, message in problems
    ]


def _accounting_units(
    facts: FactsDocument, dispositions: Mapping[str, Any]
) -> list[str]:
    """The text of every inherited unit whose disposition accounts for a loss: an accounting
    disposition that cites at least one fact and states a rationale. A kept, deferred or
    non-content disposition, or one without evidence, accounts for nothing.

    A heading is NOT an exception to this, deliberately: tests/readme/review/
    test_preservation_rules.py::test_live_loss_is_not_accounted_for_without_evidence_or_by_a_kept_disposition
    already proves a dropped heading with no fact_ids must still be reported lost, the same as a
    paragraph. Tried and reverted a broad heading exemption (measured live, aspose-cells-foss/
    Aspose.Cells-FOSS-for-Go, run 41079947007: a "## Project Structure" heading dropped with no
    fact_ids) -- the right fix for that real case is forcing reconciliation to land on real
    evidence the same way every other uncited omission in this chain was fixed (a repair attempt,
    not a quieter bar), not exempting the one kind the existing test says must not be exempt.
    """
    units = _inherited_units(facts)
    return [
        units[str(row.get("unit_id"))]
        for row in _dispositions_list(dispositions)
        if row.get("disposition") in ACCOUNTING_DISPOSITIONS
        and row.get("fact_ids")
        and str(row.get("rationale", "")).strip()
        and str(row.get("unit_id")) in units
    ]


def live_readme_loss_rule(
    original_readme: str,
    readme_text: str,
    *,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
) -> list[Finding]:
    """Preservation holdout (judge.py J6): the candidate loses nothing of the live README that a
    disposition does not account for. Lost means a live heading no candidate heading matches, a
    live fenced block no candidate fence contains, a live link target no candidate link has, or a
    live line equal to a SUPPORTED install command that the candidate does not contain."""
    accounting = _accounting_units(facts, dispositions)
    accounted_headings = {
        _heading_key(unit.lstrip("#")) for unit in accounting if unit.startswith("#")
    }

    def accounted(needle: str) -> bool:
        return any(needle in _code(unit) for unit in accounting)

    old = _read_markdown(original_readme)
    new = _read_markdown(readme_text)
    new_headings = {_heading_key(text) for text in new.headings}
    lost: list[tuple[str, str]] = []
    for text in old.headings:
        key = _heading_key(text)
        if key not in new_headings and key not in accounted_headings:
            lost.append((text, f"heading {text!r}"))
    for fence in old.fences:
        if not any(fence in other for other in new.fences) and not accounted(fence):
            lost.append(
                (fence, f"code block {fence.splitlines()[0][:50] if fence else ''!r}")
            )
    new_targets = {link.href.rstrip("/") for link in extract_links(readme_text)}
    for link in extract_links(original_readme):
        target = link.href.rstrip("/")
        if target not in new_targets and not accounted(link.href):
            lost.append((link.href, f"link {link.href}"))
    candidate_text = _code(readme_text)
    for command in _verified_install_commands(facts, original_readme):
        if command not in candidate_text and not accounted(command):
            lost.append((command, f"command {command!r}"))
    return [
        Finding(
            rule="live_readme_loss",
            source="deterministic",
            claim_kind="omission",
            message=f"live README content lost without an accounting disposition: {label}",
            evidence=label,
            quote=quote,
        )
        for quote, label in lost
    ]


def _verified_install_commands(facts: FactsDocument, live: str) -> list[str]:
    text = _code(live)
    commands = {
        _code(fact.value)
        for fact in facts.facts
        if fact.kind == "install_command" and fact.polarity == "SUPPORTED"
    }
    return sorted(command for command in commands if command and command in text)


def review_candidate(
    *,
    readme_text: str,
    units: Sequence[Mapping[str, Any]],
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
    original_readme: str,
) -> ReviewVerdict:
    """Run every registered rule against one rendered candidate and fold the result. ``units``
    is the final persisted ``section_authoring`` output (post S8 coherence, pre-render) -- the
    same durable evidence this repository already keeps per cascade; ``readme_text`` is the
    rendered markdown produced from it; ``original_readme`` is the live README the candidate was
    made from, which the preservation rule needs and which must never be silently absent."""
    findings: list[Finding] = [
        *claim_contradiction_rule(readme_text, facts),
        *duplicate_opening_paragraph_rule(
            units, dispositions=dispositions, facts=facts
        ),
        *duplicate_paragraph_rule(readme_text),
        *disposition_coverage_rule(readme_text, facts=facts, dispositions=dispositions),
        *live_readme_loss_rule(
            original_readme, readme_text, facts=facts, dispositions=dispositions
        ),
    ]
    return ReviewVerdict.folded(findings)
