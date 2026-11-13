"""The independent review of a Lane L candidate: the FINAL README, not only the edit delta.

Mission section 6: "independent retention and factual-review gates must judge the final README, not
only the edit delta. A successful deterministic patch is not automatically a high-quality README or
a candidate approved for PR." A correction whose every edit is individually evidenced can still
leave a README that states something false elsewhere, lose something, or break; so the verdict here
is on the whole corrected text, against the live README it was made from and the verified facts
(``plans/PLAN_lane_l_hosted.md`` L5).

Deterministic holdouts run first and are model-free; any one blocks, and a blocked run asks the
model nothing (the cascade's own rule, ``plan D7``: once per candidate version, only when nothing
cheaper already rejects it):

* ``lane_l_confinement``: the corrected text equals the original with exactly the listed edits
  applied and nothing else changed, re-proved here from the edit list, not trusted from the
  engine's own report;
* ``lane_l_nondeterministic``: a second run of the engine over the same inputs gave other bytes, so
  no zero-drift rerun could ever be proven;
* ``claim_contradiction``: no claim in the final README (version, install command, publication)
  contradicts a verified fact, via the reviewer's own rule over the final text. R21: a contradiction
  the LIVE README already carried, which no edit of this run touched or created, is a RESIDUAL
  when (and only when) the run is a strict net improvement (:func:`net_improvement`); a
  contradiction that is new in the corrected text always blocks;
* ``live_readme_loss``: nothing of the live README (a heading, a fenced block, a link target, a
  verified install command) is missing from the final README unless an evidenced edit accounts for
  it, via the reviewer's own rule with the edits as the accounting dispositions;
* ``lane_l_unrepaired_defect``: a defect a detector found and no deterministic edit could repair
  (``report.defect_findings``); the run is refused and Lane R is recommended.

Only a candidate that clears all of those reaches the independent LLM review
(``readme.review.llm_review.review_with_model``, the same job, prompt, route and fold Lane R uses).
Its verdict is final: this module decides nothing, folds nothing and clears nothing; it builds the
inputs and returns the reviewer's own ``ReviewVerdict``. A reviewer that cannot be reached raises
``ReviewUnavailable`` (retryable, never ACCEPT).

``plan`` is empty (Lane L plans no sections), so a finding's section is the shell section its cited
lines fall in, or ``opening``/``structure``; ``dispositions`` are the edits, so the reviewer knows
which text was changed and under which facts.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.readme.correction.apply import apply_edits, confinement_violations
from repo_presenter.readme.correction.detectors.glance_layout import (
    LAYOUT_ONLY_DETECTORS,
)
from repo_presenter.readme.correction.engine import correct
from repo_presenter.readme.correction.model import Context, CorrectionResult
from repo_presenter.readme.correction.report import (
    RULE_UNREPAIRED_DEFECT,
    correction_dispositions,
    defect_findings,
    unrepaired_defects,
)
from repo_presenter.readme.review.applied_edits import applied_edit_rows
from repo_presenter.readme.review.independent_reviewer import (
    Finding,
    ReviewVerdict,
    claim_contradiction_rule,
    live_readme_loss_rule,
)
from repo_presenter.readme.review.llm_review import review_with_model

#: Bump whenever a holdout, the accounting of edits as dispositions, or the call into the reviewer
#: changes meaning. A Lane L bundle records it as ``components.correction_review``: the reviewer
#: scope, so a bump rechecks the review and regenerates nothing.
LANE_L_REVIEW_VERSION = "4"
HOLDOUTS_FILENAME = "holdouts.json"

RULE_CONFINEMENT = "lane_l_confinement"
RULE_NONDETERMINISTIC = "lane_l_nondeterministic"
RULE_CLAIMS = "claim_contradiction"
RULE_LOSS = "live_readme_loss"

#: check id -> (name, the rule whose findings fail it). Order is the document's order.
_CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "L-01",
        "Every change is a listed, evidenced edit; the text outside them is unchanged",
        RULE_CONFINEMENT,
    ),
    (
        "L-02",
        "A second run of the correction over the same inputs gives the same bytes",
        RULE_NONDETERMINISTIC,
    ),
    ("L-03", "No claim in the final README contradicts a verified fact", RULE_CLAIMS),
    (
        "L-04",
        "Nothing of the live README is lost unless an evidenced edit accounts for it",
        RULE_LOSS,
    ),
    (
        "L-05",
        "An unrepaired defect blocks unless this run is itself a net improvement (R21)",
        RULE_UNREPAIRED_DEFECT,
    ),
)
IDEMPOTENT_CHECK = (
    "L-06",
    "A run over the corrected text finds nothing further to correct (recorded, not blocking)",
)


def confinement_findings(original: str, result: CorrectionResult) -> list[Finding]:
    """Re-prove from the edit list alone that ``result.corrected`` is ``original`` plus exactly the
    edits. The spans are recomputed here (``apply_edits``), never read from the engine's result."""
    rebuilt, spans = apply_edits(original, result.edits)
    problems = confinement_violations(original, result.corrected, result.edits, spans)
    if rebuilt != result.corrected:
        problems = [
            *problems,
            "the corrected text is not the original with the edits applied",
        ]
    return [
        Finding(
            rule=RULE_CONFINEMENT,
            source="deterministic",
            message=f"the correction is not confined to its edits: {problem}",
            evidence=problem,
        )
        for problem in problems
    ]


def nondeterminism_findings(deterministic: bool) -> list[Finding]:
    if deterministic:
        return []
    return [
        Finding(
            rule=RULE_NONDETERMINISTIC,
            source="deterministic",
            message=(
                "two runs of the correction engine over the same README, facts and tree gave "
                "different bytes: no byte-identical rerun can be proven"
            ),
            evidence="correct() is not deterministic over these inputs",
        )
    ]


def net_improvement(
    ctx: Context,
    result: CorrectionResult,
    compute: Callable[[Context], CorrectionResult] = correct,
) -> bool:
    """R21 (TC-025 point 4, replacing the old all-or-nothing L-05), defined strictly:

    1. at least one evidenced CONTENT edit was made (zero edits is never an improvement: there is
       nothing to point to; a layout-only redraw, ``LAYOUT_ONLY_DETECTORS``, is applied but never
       the improvement residual content defects ride on -- 2026-11-13, Aspose.3D-FOSS-for-.NET
       Lane L, whose L-03/L-05 failures a lone diagram redraw would otherwise have carried);
    2. the corrected text is the original plus exactly those edits and nothing else
       (:func:`confinement_findings`, re-proved here from the edit list);
    3. a second detector pass over the corrected text (``compute``, the engine's own ``correct``
       by default, re-run here rather than trusted) finds no defect absent from what the first
       pass already reported -- an edit that fixes one defect while creating another is not an
       improvement;
    4. the claim-vs-fact contradictions of the corrected text are a sub-multiset of those of the
       live README: no edit created a contradiction.

    This is the one signal that decides whether a pre-existing unrepaired defect or contradiction
    may be carried as a RESIDUAL (recorded in ``holdouts.json``, surfaced in the pull request
    description, never printed into the README) rather than block this run outright. The
    ``corrections.json`` ``outcome`` field (``report.outcome_of``) keeps stating the honest,
    unconditional ``REFUSED_LANE_R_RECOMMENDED`` when a defect remains -- that record never
    changes.
    """
    if not any(edit.detector not in LAYOUT_ONLY_DETECTORS for edit in result.edits):
        return False
    if confinement_findings(ctx.readme, result):
        return False
    # The facts an edit cites still describe the ORIGINAL README; re-running a detector against
    # the CORRECTED text with those same (now one-sided) facts can manufacture its own finding
    # purely because the text it already fixed no longer matches what the fact says to look for
    # (``broken_link`` rerun on its own repaired line is the real case this excludes) -- that is
    # an artifact of stale facts, never a defect the edit introduced. A defect citing exactly the
    # same evidence an edit already acted on is excluded from the "after" count for that reason;
    # anything else the rerun finds is a genuinely new defect and fails this.
    fixed_fact_ids = {fact_id for edit in result.edits for fact_id in edit.fact_ids}
    after = compute(dataclasses.replace(ctx, readme=result.corrected))
    before_keys = {(finding.detector, finding.reason) for finding in unrepaired_defects(result)}
    after_keys = {
        (finding.detector, finding.reason)
        for finding in unrepaired_defects(after)
        if not (set(finding.fact_ids) & fixed_fact_ids)
    }
    if after_keys - before_keys:
        return False
    _carried, introduced = split_claim_contradictions(ctx, result)
    return not introduced


def split_claim_contradictions(
    ctx: Context, result: CorrectionResult
) -> tuple[list[Finding], list[Finding]]:
    """``(carried, introduced)``: the corrected text's claim contradictions split into those the
    live README already had (matched one-for-one by their detail text, so a SECOND copy of a
    pre-existing contradiction counts as introduced) and those that are new."""
    before = Counter(f.evidence for f in claim_contradiction_rule(ctx.readme, ctx.facts))
    carried: list[Finding] = []
    introduced: list[Finding] = []
    for finding in claim_contradiction_rule(result.corrected, ctx.facts):
        if before[finding.evidence] > 0:
            before[finding.evidence] -= 1
            carried.append(finding)
        else:
            introduced.append(finding)
    return carried, introduced


class HoldoutFindings(list):
    """The blocking holdout findings (a plain ``list`` of ``Finding``, so every existing caller
    keeps working) plus ``residuals``: the pre-existing defects and contradictions a net-improving
    run carries instead of blocking on. ``holdouts_document`` records them."""

    residuals: list[dict[str, Any]]

    def __init__(self, findings: Sequence[Finding] = (), residuals: Sequence[dict[str, Any]] = ()):
        super().__init__(findings)
        self.residuals = list(residuals)


def _residual_row(kind: str, rule: str, detail: str, line: int | None, quote: str) -> dict[str, Any]:
    return {"kind": kind, "rule": rule, "detail": detail, "line": line, "quote": quote[:160]}


def _line_of(message: str) -> int | None:
    """The README line a ``claim_contradiction`` message names (``"line 255 (COMPOSING): ..."``)."""
    head = message.split(" ", 2)
    return int(head[1]) if len(head) > 1 and head[0] == "line" and head[1].isdigit() else None


def holdout_findings(
    ctx: Context, result: CorrectionResult, *, deterministic: bool
) -> HoldoutFindings:
    """Every deterministic finding against the final README, in the document order of the checks,
    with the residuals a net-improving run carries (``.residuals``).

    When this run is a strict net improvement (:func:`net_improvement`), a defect the engine could
    not repair (``RULE_UNREPAIRED_DEFECT``) and a claim contradiction the live README already had
    (and no edit touched or created) no longer block: each becomes a residual row, recorded in
    ``holdouts.json`` and surfaced in the pull request description, never in the README. A
    contradiction that is NEW in the corrected text blocks always. When the run is not a net
    improvement (no edit, a new defect, a broken confinement) nothing changes: every finding
    blocks, exactly as before.
    """
    dispositions = correction_dispositions(ctx, result.edits)
    improved = net_improvement(ctx, result)
    claims = claim_contradiction_rule(result.corrected, ctx.facts)
    residuals: list[dict[str, Any]] = []
    if improved:
        carried, claims = split_claim_contradictions(ctx, result)
        for finding in carried:
            residuals.append(
                _residual_row(
                    "claim_contradiction", RULE_CLAIMS, finding.evidence,
                    _line_of(finding.message), finding.quote,
                )
            )
        for defect in unrepaired_defects(result):
            residuals.append(
                _residual_row(
                    "unrepaired_defect", RULE_UNREPAIRED_DEFECT,
                    f"{defect.detector}: {defect.reason}", defect.line, defect.text,
                )
            )
    findings = [
        *confinement_findings(ctx.readme, result),
        *nondeterminism_findings(deterministic),
        *claims,
        *live_readme_loss_rule(
            ctx.readme, result.corrected, facts=ctx.facts, dispositions=dispositions
        ),
    ]
    if not improved:
        findings.extend(defect_findings(result))
    return HoldoutFindings(findings, residuals)


def holdouts_document(
    findings: Sequence[Finding], *, idempotent: bool, source_revision: str
) -> dict[str, Any]:
    """The holdouts as a validation-shaped document (``checks`` with ``id``/``name``/``verdict``/
    ``details``): what the sealed bundle records and what the reviewer is shown as context."""
    checks: list[dict[str, Any]] = []
    for check_id, name, rule in _CHECKS:
        details = [finding.message for finding in findings if finding.rule == rule]
        checks.append(
            {
                "id": check_id,
                "name": name,
                "verdict": "FAIL" if details else "PASS",
                "details": details,
            }
        )
    checks.append(
        {
            "id": IDEMPOTENT_CHECK[0],
            "name": IDEMPOTENT_CHECK[1],
            "verdict": "PASS" if idempotent else "FAIL",
            "details": []
            if idempotent
            else ["the engine would make further corrections to its own output"],
        }
    )
    failed = sum(1 for check in checks if check["verdict"] == "FAIL")
    document: dict[str, Any] = {
        "schema_version": 1,
        "lane": "L",
        "review_logic_version": LANE_L_REVIEW_VERSION,
        "source_revision": source_revision,
        "checks": checks,
        "summary": {"pass": len(checks) - failed, "fail": failed},
    }
    residuals = list(getattr(findings, "residuals", ()))
    if residuals:
        # R21: pre-existing defects/contradictions this net-improving run did not touch and could
        # not repair. Internal record and pull request description only; never README text (R9).
        document["residuals"] = residuals
    return document


def review_correction(
    *,
    ctx: Context,
    result: CorrectionResult,
    findings: Sequence[Finding],
    holdouts: Mapping[str, Any],
    prompts: PromptRegistry,
    config: GatewayConfig,
    ledger: Ledger,
    store: CallStore,
    context: JobContext,
    facts: FactsDocument,
) -> ReviewVerdict:
    """The verdict on the final README. ``findings`` are :func:`holdout_findings`: any one rejects
    without a model call. Otherwise the independent reviewer reads the final README against the
    live one and the facts; ``ReviewUnavailable`` propagates when no valid review exists."""
    if findings:
        return ReviewVerdict.folded(findings)
    applied = applied_edit_rows(result.edits, facts)
    return review_with_model(
        prompts=prompts,
        config=config,
        ledger=ledger,
        store=store,
        context=context,
        candidate_readme=result.corrected,
        original_readme=ctx.readme,
        facts=facts,
        plan={"sections": []},
        dispositions=correction_dispositions(ctx, result.edits),
        # The derivation of each value a detector computed from SUPPORTED facts rides with the
        # holdouts the reviewer reads, never into the recorded holdouts document: it is the
        # evidence for the edited line, not part of the sealed record.
        validation={**holdouts, "applied_edits": applied} if applied else holdouts,
        deterministic_findings=(),
        # Lane L's README is the maintainers' own text plus minimal evidenced edits, not rendered
        # from facts: installation, license, fenced code and tables are exactly what the model
        # must be able to review here, unlike Lane R's renderer-printed sections.
        rendered=False,
    )
