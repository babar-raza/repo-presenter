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
against this repository's own evidence shapes, not ported.

The old repository's own measured incident (``docs/MISSION_AUTHORITY.md``'s "critical fact":
pre-2026-10-10, 27/30 real REJECT findings were wrongly folded to ACCEPT whenever a finding's
quoted span happened to also match a literal SUPPORTED fact value elsewhere in the candidate) is
why the fold logic here is deliberately isolated in ``_fold`` and structurally cannot be
subverted by a judgment rule: ``Finding.__post_init__`` raises if a ``"judgment"``-kind finding
ever carries a ``refuted_by`` -- the invariant is enforced by construction, not by convention.

Scope of v1 (deliberately bounded, per the mission's P1 "smallest working... + independent
verifier" discipline -- see ``project/state.yaml``'s ``BUILD_INDEPENDENT_REVIEWER`` card for the
full reasoning):

- Two deterministic rules only, both reusing already-proven, already-tested primitives rather
  than re-deriving detection logic (the mission's own reuse discipline): a factual holdout
  (``claim_contradiction``, via ``readme.validation.claims.claim_findings``) and a preservation/
  previous-regression holdout (``duplicate_opening_paragraph``, via
  ``readme.composition.authoring.preserved_opening_text`` +
  ``readme.composition.coverage.states_all`` -- the exact primitives the duplicate-opening
  defect's own partial fix already uses, called here independently of the authoring pipeline's
  own inline guard, against the final persisted output).
- No judgment rules are registered yet. The extension point (``Finding.kind == "judgment"``)
  exists and is structurally safe to add to, but no LLM-backed holdout ships in v1 -- a known,
  explicitly recorded gap, not a silent one (mirrors the project's existing
  ``known_gaps_for_future_work`` pattern).
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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.authoring import preserved_opening_text
from repo_presenter.readme.composition.coverage import states_all
from repo_presenter.readme.validation.claims import claim_findings

RuleKind = Literal["deterministic", "judgment"]
Verdict = Literal["ACCEPT", "REJECT"]


@dataclass(frozen=True)
class Refutation:
    """Why a deterministic rule refuted the candidate. Only a deterministic rule may produce
    one; see ``Finding.__post_init__``."""

    rule: str
    evidence: str


@dataclass(frozen=True)
class Finding:
    """One rule's output against one candidate. A ``"judgment"``-kind finding may only annotate:
    it is a construction error, not a runtime check, for one to carry a ``refuted_by`` -- the
    old repository's fold-to-ACCEPT bug is made structurally unreachable here rather than merely
    avoided by convention."""

    rule: str
    kind: RuleKind
    message: str
    refuted_by: Refutation | None = None
    # The literal flagged text, when one exists -- not a paraphrase. readme.review.defect_bridge
    # matches this against composition/placement.py's placed_texts() to tell an authoring (S6)
    # defect from one over content the candidate inherited verbatim (S4); that distinction
    # cannot be guessed from `rule`/`kind` alone (project/state.yaml's
    # root_cause_traced_2026_10_24: the real aspose-font-foss/Python case was inherited, not
    # authored, and a naive always-S6 router would have misrouted it).
    quote: str = ""

    def __post_init__(self) -> None:
        if self.kind == "judgment" and self.refuted_by is not None:
            raise ValueError(
                f"judgment rule {self.rule!r} may not carry a refutation -- judgment rules "
                "annotate only, they can never fold a REJECT to ACCEPT or vice versa"
            )


def _fold(findings: Sequence[Finding]) -> Verdict:
    """The one place a verdict is decided. REJECT if, and only if, at least one finding carries
    a ``refuted_by`` -- no other field or rule kind can influence this. Isolated in its own
    function so it can be tested directly and adversarially, independent of which rules ran."""
    return "REJECT" if any(finding.refuted_by is not None for finding in findings) else "ACCEPT"


@dataclass(frozen=True)
class ReviewVerdict:
    """The reviewer's output for one candidate. ``verdict`` is exactly ``_fold(findings)`` --
    never recomputed or overridden elsewhere."""

    verdict: Verdict
    findings: tuple[Finding, ...]

    @property
    def deterministic_reject_count(self) -> int:
        return sum(1 for finding in self.findings if finding.refuted_by is not None)


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
                kind="deterministic",
                message=f"line {finding.line} ({finding.stage}): {finding.detail}",
                refuted_by=Refutation(rule="claim_contradiction", evidence=finding.detail),
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
                    kind="deterministic",
                    message=(
                        "the 'opening' unit restates the inherited preserved paragraph placed "
                        "beside it rather than adding genuinely new content"
                    ),
                    refuted_by=Refutation(
                        rule="duplicate_opening_paragraph",
                        evidence=f"preserved={preserved!r} authored={text!r}",
                    ),
                    quote=text,
                )
            ]
        break
    return []


def review_candidate(
    *,
    readme_text: str,
    units: Sequence[Mapping[str, Any]],
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
) -> ReviewVerdict:
    """Run every registered rule against one rendered candidate and fold the result. ``units``
    is the final persisted ``section_authoring`` output (post S8 coherence, pre-render) -- the
    same durable evidence this repository already keeps per cascade; ``readme_text`` is the
    rendered markdown produced from it. Both are required so a factual check can read the
    rendered prose and a structural check can read the pre-render units without re-parsing
    markdown back into units."""
    findings: list[Finding] = [
        *claim_contradiction_rule(readme_text, facts),
        *duplicate_opening_paragraph_rule(units, dispositions=dispositions, facts=facts),
    ]
    return ReviewVerdict(verdict=_fold(findings), findings=tuple(findings))
