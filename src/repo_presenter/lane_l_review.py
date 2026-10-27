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
  contradicts a verified fact, via the reviewer's own rule over the final text;
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

from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.readme.correction.apply import apply_edits, confinement_violations
from repo_presenter.readme.correction.model import Context, CorrectionResult
from repo_presenter.readme.correction.report import (
    RULE_UNREPAIRED_DEFECT,
    correction_dispositions,
    defect_findings,
)
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
LANE_L_REVIEW_VERSION = "1"
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
    ("L-05", "Every defect a detector found was repaired", RULE_UNREPAIRED_DEFECT),
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


def holdout_findings(
    ctx: Context, result: CorrectionResult, *, deterministic: bool
) -> list[Finding]:
    """Every deterministic finding against the final README, in the document order of the checks."""
    dispositions = correction_dispositions(ctx, result.edits)
    return [
        *confinement_findings(ctx.readme, result),
        *nondeterminism_findings(deterministic),
        *claim_contradiction_rule(result.corrected, ctx.facts),
        *live_readme_loss_rule(
            ctx.readme, result.corrected, facts=ctx.facts, dispositions=dispositions
        ),
        *defect_findings(result),
    ]


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
    return {
        "schema_version": 1,
        "lane": "L",
        "review_logic_version": LANE_L_REVIEW_VERSION,
        "source_revision": source_revision,
        "checks": checks,
        "summary": {"pass": len(checks) - failed, "fail": failed},
    }


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
        validation=holdouts,
        deterministic_findings=(),
        # Lane L's README is the maintainers' own text plus minimal evidenced edits, not rendered
        # from facts: installation, license, fenced code and tables are exactly what the model
        # must be able to review here, unlike Lane R's renderer-printed sections.
        rendered=False,
    )
