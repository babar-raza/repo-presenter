"""The calibration harness: run a reviewer over the corpus, measure it, and gate it (plan D9 V5).

A *reviewer* is any callable from a ``Case`` to a ``ReviewOutcome``; the harness neither knows nor
cares whether it is a stub, a scripted model or the live gateway. ``run_corpus`` asks it about every
case (and again for each repeat), also recording what the deterministic stage alone would have done
with the case (``pre_llm``: the rules of ``review_candidate`` and any NEW blocking check), because in
production a candidate those reject never reaches the model. Two recalls follow:

* ``llm`` recall: the reviewer's own verdicts, whatever the deterministic stage would have done;
* ``pipeline`` recall: the deterministic stage OR the reviewer rejects (what a sealed candidate
  actually faces).

A rejection counts as a catch only when it is *on target*: one of its blocking findings names the
injected or recorded defect (``Case.targets``). A reviewer that rejects a candidate for a reason
that has nothing to do with the defect has not found the defect, and a gate it passed that way
would measure its habit of rejecting, not its judgment. The plan's literal recall (any rejection)
is reported beside it.

``UNAVAILABLE`` (no valid review obtainable) is neither an ACCEPT nor a catch: it never counts in
a numerator and always counts in the denominator, so an unreliable reviewer cannot look good.

The gates are the plan's initial targets. A gate with no measurement (no case of its class was
asked) FAILS: a criterion nobody measured has not been met. A reviewer that accepts everything or
rejects everything fails the corpus gate by construction (mission section 11) and is tested to.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from repo_presenter.readme.review.calibration.corpus import (
    Case,
    deterministic_rules,
    new_blocking_checks,
)
from repo_presenter.readme.review.calibration.mutations import (
    HIGH_SEVERITY_CLASSES,
    OPERATORS,
)
from repo_presenter.readme.review.calibration.outcomes import (
    ACCEPT,
    REJECT,
    UNAVAILABLE,
)

RECALL_TARGET = 0.90
FALSE_REJECT_LIMIT = 0.10
JSON_VALID_TARGET = 0.90
STABILITY_TARGET = 0.90


#: The two tiers of the gate (project/state.yaml INDEPENDENT_LLM_REVIEWER.gate_semantics_decision).
PIPELINE = "pipeline"
LLM_ONLY = "llm_only"
#: Every defect label and the tier that owns it. A label is a mutation operator, or ``real:<class>``
#: for a defect found in a real candidate. Tier 1 (``PIPELINE``): code decides it, so the
#: deterministic stage plus the reviewer must reach the recall target. Tier 2 (``LLM_ONLY``): only a
#: judgment can, so the reviewer alone must. A new operator has no tier until someone assigns one.
DEFECT_TIERS: dict[str, str] = {
    "contradict_version": PIPELINE,
    "contradict_package_name": PIPELINE,
    "contradict_format": PIPELINE,
    "break_install_command": PIPELINE,
    "drop_section": PIPELINE,
    "invent_api_name": PIPELINE,
    "duplicate_paragraph": PIPELINE,
    "real:broken_install": PIPELINE,
    "real:duplicate_paragraph": PIPELINE,
    "inject_unsupported_claim": LLM_ONLY,
    "add_promotional_filler": LLM_ONLY,
    "real:unsupported_claim": LLM_ONLY,
    "real:contradiction": LLM_ONLY,
}


class BudgetExhausted(Exception):
    """The provider-call cap is reached; the run stops and reports what it has."""


@dataclass(frozen=True)
class ReviewOutcome:
    verdict: str
    #: Physical provider calls this review spent (0 for a stub or a cache replay).
    calls: int = 0
    #: Whether the first reply parsed and matched the schema / the whole contract; ``None`` when
    #: no reply was sent (a stub, or a cache replay).
    first_reply_json_valid: bool | None = None
    first_reply_contract_valid: bool | None = None
    blocking_kinds: tuple[str, ...] = ()
    #: The blocking findings' quote and text, normalised (``evidence_text``): what the reviewer
    #: said its rejection was about.
    evidence: tuple[str, ...] = ()
    #: The text the blocking findings cite (their derived quotes alone), normalised.
    quotes: tuple[str, ...] = ()
    cleared: int = 0
    model_served: str = ""
    detail: str = ""
    #: A sectionwise review makes one logical call per review unit: how many units sent a first
    #: reply, and how many of those were schema-valid and contract-valid. ``0`` for a stub.
    unit_replies: int = 0
    unit_json_valid: int = 0
    unit_contract_valid: int = 0
    #: Prompt plus completion tokens of the physical attempts, and the review units asked.
    tokens: int = 0
    units: int = 0


Reviewer = Callable[[Case], ReviewOutcome]


def evidence_text(*parts: str) -> str:
    """``parts`` as one lower-case, single-spaced string with plain hyphens."""
    joined = " || ".join(parts).lower().replace("‑", "-")
    return " ".join(joined.split())


def on_target(case: Case, outcome: ReviewOutcome) -> bool:
    """Whether ``outcome`` rejects ``case`` FOR ITS DEFECT. A defect with text of its own (an injected
    claim, a wrong version, a removed span) is caught only by a finding whose cited lines hold that
    text: words a finding shares with the defect's keywords can come from any line about the same
    topic (iteration 3's smoke run counted a finding about another sentence as the catch). A defect
    that is an absence (a dropped section) has no text to cite and is located by its keywords. A
    case with neither is scored on the verdict alone."""
    if outcome.verdict != REJECT:
        return False
    if case.defect_text:
        wanted = evidence_text(case.defect_text)
        return any(wanted in quote for quote in outcome.quotes)
    if not case.targets:
        return True
    return any(target in text for text in outcome.evidence for target in case.targets)


def defect_label(case: Case) -> str | None:
    """The defect a case injects or records: its operator, ``real:<class>`` for a real defect, and
    ``None`` for a clean twin. A label with no tier is an error: assign it in ``DEFECT_TIERS``."""
    if case.role in {"clean", "unscored_twin"}:
        return None
    label = case.operator if case.operator else f"real:{case.klass}"
    if label not in DEFECT_TIERS:
        raise ValueError(f"defect {label!r} has no tier: assign one in DEFECT_TIERS")
    return label


@dataclass(frozen=True)
class PreLLM:
    rules: tuple[str, ...]
    checks: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.rules or self.checks)


@dataclass(frozen=True)
class CaseResult:
    case: Case
    pre: PreLLM
    outcomes: tuple[ReviewOutcome, ...]

    @property
    def llm_verdict(self) -> str:
        return self.outcomes[0].verdict

    @property
    def pipeline_verdict(self) -> str:
        return REJECT if self.pre.blocked else self.llm_verdict


@dataclass(frozen=True)
class Run:
    results: tuple[CaseResult, ...]
    stopped: str = ""


def pre_llm(case: Case) -> PreLLM:
    rules = tuple(
        rule for rule in deterministic_rules(case) if rule not in case.baseline_rules
    )
    return PreLLM(rules, new_blocking_checks(case))


def run_corpus(cases: Sequence[Case], reviewer: Reviewer, *, repeats: int = 1) -> Run:
    """Ask ``reviewer`` about every case ``repeats`` times. A ``BudgetExhausted`` ends the run;
    the cases already answered are kept."""
    results: list[CaseResult] = []
    for case in cases:
        pre = pre_llm(case)
        outcomes: list[ReviewOutcome] = []
        try:
            for _ in range(repeats):
                outcomes.append(reviewer(case))
        except BudgetExhausted as error:
            if outcomes:
                results.append(CaseResult(case, pre, tuple(outcomes)))
            return Run(tuple(results), stopped=str(error))
        results.append(CaseResult(case, pre, tuple(outcomes)))
    return Run(tuple(results))


@dataclass(frozen=True)
class ClassStats:
    n: int = 0
    llm_rejected: int = 0
    pipeline_rejected: int = 0
    unavailable: int = 0
    llm_on_target: int = 0
    pipeline_on_target: int = 0

    def llm_recall(self) -> float | None:
        """Rejections of any kind (the plan's literal recall)."""
        return self.llm_rejected / self.n if self.n else None

    def pipeline_recall(self) -> float | None:
        return self.pipeline_rejected / self.n if self.n else None

    def llm_target_recall(self) -> float | None:
        """Rejections that name the injected or recorded defect."""
        return self.llm_on_target / self.n if self.n else None

    def pipeline_target_recall(self) -> float | None:
        return self.pipeline_on_target / self.n if self.n else None


@dataclass(frozen=True)
class Metrics:
    per_class: dict[str, ClassStats] = field(default_factory=dict)
    per_defect: dict[str, ClassStats] = field(default_factory=dict)
    clean_n: int = 0
    clean_llm_rejected: int = 0
    clean_pipeline_rejected: int = 0
    clean_unavailable: int = 0
    clean_accepted: int = 0
    first_replies: int = 0
    first_reply_json_valid: int = 0
    first_reply_contract_valid: int = 0
    repeated_cases: int = 0
    stable_cases: int = 0
    calls: int = 0
    cases_asked: int = 0
    content_loss_accepted: int = 0
    content_loss_n: int = 0
    #: Repaired twins of recorded defects whose deterministic context is stale: asked, reported,
    #: never part of the false-reject gate.
    unscored_n: int = 0
    unscored_llm_rejected: int = 0
    tokens: int = 0
    units: int = 0

    @property
    def tokens_per_case(self) -> float | None:
        return self.tokens / self.cases_asked if self.cases_asked else None

    @property
    def false_reject_rate(self) -> float | None:
        return self.clean_llm_rejected / self.clean_n if self.clean_n else None

    @property
    def pipeline_false_reject_rate(self) -> float | None:
        return self.clean_pipeline_rejected / self.clean_n if self.clean_n else None

    @property
    def approved_yield(self) -> float | None:
        """The share of clean candidates the whole pipeline approves."""
        return self.clean_accepted / self.clean_n if self.clean_n else None

    @property
    def json_valid_first_reply_rate(self) -> float | None:
        return (
            self.first_reply_json_valid / self.first_replies
            if self.first_replies
            else None
        )

    @property
    def contract_valid_first_reply_rate(self) -> float | None:
        return (
            self.first_reply_contract_valid / self.first_replies
            if self.first_replies
            else None
        )

    @property
    def stability(self) -> float | None:
        return self.stable_cases / self.repeated_cases if self.repeated_cases else None

    @property
    def content_loss_rate(self) -> float | None:
        """The share of content-loss mutants the whole pipeline APPROVES (lower is better)."""
        return (
            self.content_loss_accepted / self.content_loss_n
            if self.content_loss_n
            else None
        )

    @property
    def calls_per_case(self) -> float | None:
        return self.calls / self.cases_asked if self.cases_asked else None


def compute_metrics(run: Run) -> Metrics:
    per_class: dict[str, list[int]] = {}
    per_defect: dict[str, list[int]] = {}
    clean_n = clean_llm = clean_pipe = clean_unavailable = clean_accepted = 0
    first = first_json = first_contract = 0
    repeated = stable = calls = asked = 0
    tokens = units = 0
    loss_accepted = loss_n = 0
    unscored_n = unscored_rejected = 0
    for result in run.results:
        case = result.case
        asked += 1
        calls += sum(outcome.calls for outcome in result.outcomes)
        for outcome in result.outcomes:
            tokens += outcome.tokens
            units += outcome.units
            if outcome.unit_replies:
                first += outcome.unit_replies
                first_json += outcome.unit_json_valid
                first_contract += outcome.unit_contract_valid
            elif outcome.first_reply_json_valid is not None:
                first += 1
                first_json += bool(outcome.first_reply_json_valid)
                first_contract += bool(outcome.first_reply_contract_valid)
        if len(result.outcomes) > 1:
            repeated += 1
            stable += len({outcome.verdict for outcome in result.outcomes}) == 1
        if case.role == "unscored_twin":
            unscored_n += 1
            unscored_rejected += result.llm_verdict == REJECT
            continue
        if case.role == "clean":
            clean_n += 1
            clean_llm += result.llm_verdict == REJECT
            clean_pipe += result.pipeline_verdict == REJECT
            clean_unavailable += result.llm_verdict == UNAVAILABLE
            clean_accepted += result.pipeline_verdict == ACCEPT
            continue
        hit = on_target(case, result.outcomes[0])
        label = defect_label(case)
        for table, key in ((per_class, case.klass or "?"), (per_defect, label or "?")):
            stats = table.setdefault(key, [0, 0, 0, 0, 0, 0])
            stats[0] += 1
            stats[1] += result.llm_verdict == REJECT
            stats[2] += result.pipeline_verdict == REJECT
            stats[3] += result.llm_verdict == UNAVAILABLE
            stats[4] += hit
            stats[5] += result.pre.blocked or hit
        if case.klass == "content_loss":
            loss_n += 1
            loss_accepted += result.pipeline_verdict == ACCEPT
    return Metrics(
        per_class={k: ClassStats(*v) for k, v in sorted(per_class.items())},
        per_defect={k: ClassStats(*v) for k, v in sorted(per_defect.items())},
        clean_n=clean_n,
        clean_llm_rejected=clean_llm,
        clean_pipeline_rejected=clean_pipe,
        clean_unavailable=clean_unavailable,
        clean_accepted=clean_accepted,
        first_replies=first,
        first_reply_json_valid=first_json,
        first_reply_contract_valid=first_contract,
        repeated_cases=repeated,
        stable_cases=stable,
        calls=calls,
        cases_asked=asked,
        content_loss_accepted=loss_accepted,
        content_loss_n=loss_n,
        unscored_n=unscored_n,
        unscored_llm_rejected=unscored_rejected,
        tokens=tokens,
        units=units,
    )


@dataclass(frozen=True)
class GateResult:
    name: str
    value: float | None
    threshold: float
    direction: str  # ">=" or "<="
    passed: bool
    n: int

    def line(self) -> str:
        shown = "not measured" if self.value is None else f"{self.value:.2f}"
        verdict = "PASS" if self.passed else "FAIL"
        return f"{verdict} {self.name}: {shown} (need {self.direction} {self.threshold:.2f}, n={self.n})"


def _gate(
    name: str, value: float | None, threshold: float, direction: str, n: int
) -> GateResult:
    if value is None:
        passed = False
    elif direction == ">=":
        passed = value >= threshold
    else:
        passed = value <= threshold
    return GateResult(name, value, threshold, direction, passed, n)


def evaluate_gates(
    metrics: Metrics, *, scope: str = "llm", basis: str = "target"
) -> list[GateResult]:
    """The plan's gates over ``metrics``. ``scope`` is ``"llm"`` (the reviewer's own verdicts) or
    ``"pipeline"`` (deterministic stage plus reviewer) for recall and false-reject; ``basis`` is
    ``"target"`` (a catch must name the defect) or ``"verdict"`` (any rejection counts)."""
    gates: list[GateResult] = []
    for klass in HIGH_SEVERITY_CLASSES:
        stats = metrics.per_class.get(klass, ClassStats())
        if basis == "target":
            recall = (
                stats.llm_target_recall()
                if scope == "llm"
                else stats.pipeline_target_recall()
            )
        else:
            recall = stats.llm_recall() if scope == "llm" else stats.pipeline_recall()
        gates.append(_gate(f"recall[{klass}]", recall, RECALL_TARGET, ">=", stats.n))
    false_reject = (
        metrics.false_reject_rate
        if scope == "llm"
        else metrics.pipeline_false_reject_rate
    )
    gates.append(
        _gate(
            "false_reject_rate", false_reject, FALSE_REJECT_LIMIT, "<=", metrics.clean_n
        )
    )
    gates.append(
        _gate(
            "json_valid_first_reply",
            metrics.json_valid_first_reply_rate,
            JSON_VALID_TARGET,
            ">=",
            metrics.first_replies,
        )
    )
    gates.append(
        _gate(
            "stability",
            metrics.stability,
            STABILITY_TARGET,
            ">=",
            metrics.repeated_cases,
        )
    )
    return gates


def corpus_gate_passes(
    metrics: Metrics, *, scope: str = "llm", basis: str = "target"
) -> bool:
    """Whether every gate passes. A reviewer that accepts everything fails the recall gates; one
    that rejects everything fails the false-reject gate."""
    return all(
        gate.passed for gate in evaluate_gates(metrics, scope=scope, basis=basis)
    )


@dataclass(frozen=True)
class TierReport:
    """Both tiers of the gate, with the reviewer-alone numbers of tier 1 beside its pipeline gate."""

    pipeline: tuple[GateResult, ...]
    llm_only: tuple[GateResult, ...]
    shared: tuple[GateResult, ...]
    #: label -> the reviewer's own on-target recall for each tier-1 class (reported, never gated).
    reviewer_alone: dict[str, float | None]

    @property
    def status(self) -> str:
        """``PASSED``: every gate. ``LIMITS_ONLY``: every tier-1 and shared gate and some tier-2
        recall below target, which the owner may accept as declared limits (code never records that
        acceptance). Otherwise ``NOT_PASSED``."""
        if not all(g.passed for g in (*self.pipeline, *self.shared)):
            return "NOT_PASSED"
        return "PASSED" if all(g.passed for g in self.llm_only) else "LIMITS_ONLY"


def evaluate_tiers(metrics: Metrics) -> TierReport:
    """The two-tier gate over ``metrics``. Every mutation operator is required (its class must have
    been asked); a real-defect label is gated when the corpus holds one."""
    required = {label for label in OPERATORS if label in DEFECT_TIERS}
    labels = sorted(required | {l for l in metrics.per_defect if l in DEFECT_TIERS})
    pipeline: list[GateResult] = []
    llm_only: list[GateResult] = []
    alone: dict[str, float | None] = {}
    for label in labels:
        stats = metrics.per_defect.get(label, ClassStats())
        if DEFECT_TIERS[label] == PIPELINE:
            pipeline.append(
                _gate(
                    f"pipeline[{label}]",
                    stats.pipeline_target_recall(),
                    RECALL_TARGET,
                    ">=",
                    stats.n,
                )
            )
            alone[label] = stats.llm_target_recall()
        else:
            llm_only.append(
                _gate(
                    f"reviewer_alone[{label}]",
                    stats.llm_target_recall(),
                    RECALL_TARGET,
                    ">=",
                    stats.n,
                )
            )
    shared = [
        gate
        for gate in evaluate_gates(metrics)
        if gate.name in {"false_reject_rate", "json_valid_first_reply", "stability"}
    ]
    return TierReport(tuple(pipeline), tuple(llm_only), tuple(shared), alone)
