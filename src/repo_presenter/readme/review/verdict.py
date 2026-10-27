"""The reviewer's verdict and the single fold that decides it (plan D5).

``fold_verdict`` is the only function that decides ACCEPT or REJECT. ``ReviewVerdict`` carries the
result, and its ``__post_init__`` re-runs the fold and refuses a verdict that disagrees with it, so
a verdict built, loaded or edited by hand cannot say ACCEPT where the fold would not. A structural
test (``tests/readme/review/test_review_invariants.py``) asserts that no ACCEPT/REJECT value is
assigned anywhere else in the source tree.

The fold, in words. ACCEPT if, and only if, ALL of:

* the reply (if there was one) was contract-valid;
* the model verdict is absent (a deterministic-only review: no model was asked), ACCEPT, or a
  ``REJECT_*`` that returned at least one finding and every finding is CLEARED;
* no deterministic finding blocks (a deterministic finding is always BLOCKING);
* no finding is BLOCKING.

``INSUFFICIENT_EVIDENCE`` blocks, retryably. A ``REJECT_*`` with zero findings blocks: there is
nothing for a clearance to disprove, so it cannot be cleared. An unknown model verdict blocks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from repo_presenter.readme.review.findings import Finding

Verdict = Literal["ACCEPT", "REJECT"]

#: Bump whenever the rule set, a rule's matching logic, a clearance, the contract checks or the
#: fold change meaning (the same contract composition/authoring.py's NORMALISATION_VERSION and
#: composition/renderer.py's RENDERER_VERSION serve for their own stages).
#: "4": the LLM reviewer's finding model, clearance catalogue, contract validation and fold
#: (plans/PLAN_independent_llm_reviewer.md); review_verdict.json schema 2.
#: "5": findings cite candidate lines and code derives the quote and section; an unsupported claim
#: and a quality finding need no product fact; a quality finding against renderer-owned text is a
#: scope error; the unsupported-claim audit; the no-re-roll guard. Reviewer scope only.
REVIEWER_LOGIC_VERSION = "5"
REVIEW_VERDICT_FILENAME = "review_verdict.json"

REJECT_VERDICTS = (
    "REJECT_FACTUAL",
    "REJECT_PRESERVATION",
    "REJECT_PRESENTATION",
    "REJECT_EXAMPLE",
    "REJECT_LIMITATIONS",
    "REJECT_LINKS",
    "REJECT_COHERENCE",
)
MODEL_VERDICTS = ("ACCEPT", *REJECT_VERDICTS, "INSUFFICIENT_EVIDENCE")


@dataclass(frozen=True)
class Fold:
    verdict: Verdict
    retryable: bool
    reason: str


def fold_verdict(
    *,
    model_verdict: str | None,
    findings: Sequence[Finding],
    reply_errors: Sequence[str] = (),
) -> Fold:
    """The one place a verdict is decided. See the module docstring for the rule."""
    if reply_errors:
        return Fold(
            "REJECT",
            True,
            "the reviewer's reply broke the contract: " + reply_errors[0],
        )
    blocking = [finding for finding in findings if finding.blocking]
    deterministic = [
        finding for finding in blocking if finding.source == "deterministic"
    ]
    if deterministic:
        return Fold(
            "REJECT", False, f"{len(deterministic)} deterministic finding(s) block"
        )
    if model_verdict == "INSUFFICIENT_EVIDENCE":
        return Fold(
            "REJECT", True, "the reviewer found the inputs insufficient to review"
        )
    if model_verdict is not None and model_verdict not in MODEL_VERDICTS:
        return Fold("REJECT", True, f"unknown reviewer verdict {model_verdict!r}")
    if blocking:
        return Fold("REJECT", False, f"{len(blocking)} finding(s) block")
    if model_verdict in REJECT_VERDICTS and not any(
        f.source == "llm" for f in findings
    ):
        return Fold(
            "REJECT", False, f"{model_verdict} with no finding: nothing to clear"
        )
    return Fold("ACCEPT", False, "")


class ReviewUnavailable(Exception):
    """No valid review exists for this candidate: the reply broke the contract even after the one
    re-ask, or the provider failed. Retryable, and never ACCEPT: a run with no valid review cannot
    be sealed (plan D4)."""

    retryable = True

    def __init__(self, reason: str, errors: Sequence[str] = ()) -> None:
        super().__init__(reason)
        self.reason = reason
        self.errors = tuple(errors)


@dataclass(frozen=True)
class ReviewVerdict:
    """The reviewer's output for one candidate. ``verdict`` is exactly the fold of the other
    fields; construct with ``ReviewVerdict.folded`` unless the verdict is read back from a file."""

    verdict: Verdict
    findings: tuple[Finding, ...]
    model_verdict: str | None = None
    prompt_version: str | None = None
    model_served: str | None = None
    request_sha256: str | None = None
    reply_sha256: str | None = None

    def __post_init__(self) -> None:
        folded = fold_verdict(model_verdict=self.model_verdict, findings=self.findings)
        if self.verdict != folded.verdict:
            raise ValueError(
                f"verdict {self.verdict!r} does not match fold_verdict of its own findings "
                f"({folded.verdict!r}: {folded.reason})"
            )
        if self.model_verdict is not None and not all(
            (
                self.prompt_version,
                self.model_served,
                self.request_sha256,
                self.reply_sha256,
            )
        ):
            raise ValueError(
                "a verdict from a model review records its prompt version, model served and "
                "request and reply hashes"
            )

    @classmethod
    def folded(
        cls,
        findings: Sequence[Finding],
        *,
        model_verdict: str | None = None,
        prompt_version: str | None = None,
        model_served: str | None = None,
        request_sha256: str | None = None,
        reply_sha256: str | None = None,
    ) -> ReviewVerdict:
        folded = fold_verdict(model_verdict=model_verdict, findings=findings)
        return cls(
            verdict=folded.verdict,
            findings=tuple(findings),
            model_verdict=model_verdict,
            prompt_version=prompt_version,
            model_served=model_served,
            request_sha256=request_sha256,
            reply_sha256=reply_sha256,
        )

    @property
    def fold(self) -> Fold:
        return fold_verdict(model_verdict=self.model_verdict, findings=self.findings)

    @property
    def retryable(self) -> bool:
        return self.fold.retryable

    @property
    def model_reviewed(self) -> bool:
        """Whether a model reviewed this candidate. A deterministic-only verdict is not the
        independent review the mission requires (section 7 step 7)."""
        return self.model_verdict is not None

    @property
    def deterministic_reject_count(self) -> int:
        return sum(1 for finding in self.findings if finding.source == "deterministic")

    @property
    def blocking_findings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.blocking)
