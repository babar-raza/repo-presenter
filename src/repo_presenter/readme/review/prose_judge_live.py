"""M8's first real, governed provider call (TC-023b).

``prose_judge.py`` (TC-023, accepted, untouched by this module) builds M8's three request shapes
and its pure, fake-only ``sequential_majority_vote`` state machine. That module deliberately makes
no provider call and imports no gateway machinery at all -- its own tests prove that mechanically
(``test_module_never_wires_a_real_provider_call``). This module is the separately budgeted
counterpart that wires a REAL ``DrawSource`` (the zero-argument callable
``sequential_majority_vote`` expects): one physical, governed provider call per draw, never more.

**Wiring choice made: (b), a new, narrower governed call path -- NOT a seventh ``JOB_STAGES``
entry in ``core.llm.prompts``.** Two independent reasons, not just "simpler":

1. ``write_paths`` for this very card are exactly ``prose_judge_live.py`` and its test; option (a)
   needs ``core/llm/prompts.py``'s ``JOB_STAGES``/``load_manifests`` edited (to accept a seventh
   job id without breaking its "exactly six, anything else fails closed" contract) plus new
   manifest files under ``prompts/`` in ``core.llm.prompts``'s own manifest shape -- neither file
   is in this card's ``write_paths``, so (a) cannot be done inside this card's own boundary at all.
2. **A concrete correctness reason, found by reading ``core/llm/jobs.py::run_job`` in full, not
   just a scope technicality.** ``run_job`` caches an accepted output under the hash of
   (``prompt_sha256``, request payload) -- see its ``store.get(request_sha256)`` / ``store.put``
   calls. M8's three prompt shapes run at ``temperature: 0.0`` / ``seed: 1`` with an IDENTICAL
   span/section/signature across every draw of the same call (``sequential_majority_vote`` asks
   the very same question two or three times on purpose). Every one of those draws would hash to
   the exact same ``request_sha256``. Routed through ``run_job``'s ``CallStore``, the SECOND draw
   of a call would be a guaranteed cache hit returning the FIRST draw's own answer verbatim, every
   time, forever -- never a second physical attempt. That silently collapses
   ``sequential_majority_vote`` into "ask once, repeat the answer twice", which defeats the entire
   reason M8 votes at all: ``prose_judge.py``'s own module docstring records that qwen3-next does
   not reliably return the same verdict on a byte-identical request even at temperature 0 / seed 1
   (roughly 0.70-0.90 repeat-draw stability, per ``docs/investigations/2026-11-06-reviewer-
   rootcause.md``) -- so the whole point of drawing again is that it is NOT guaranteed to repeat.
   Reusing ``run_job`` as-is would make every M8 vote spuriously unanimous. Making (a) safe would
   need ``run_job`` itself changed (e.g. a per-draw cache-bypass flag) -- a change to a file this
   card's ``write_paths`` does not include, and a change that would touch the one deterministic/
   agentic boundary every other Lane R job already depends on. (b) avoids the whole problem: this
   module never constructs or consults a ``CallStore`` at all, by design, not by oversight.

What (b) still reuses, verbatim, never reimplemented: ``core.llm.budget.check_budget`` /
``record_spend`` (the owner-ruling-R25 budget gate, called exactly where ``run_job`` calls them --
immediately before a fresh physical attempt, and immediately after it succeeds) and
``core.llm.transport.build_client`` (the one real network seam every other job already calls
through, looked up on the module the same way ``core.llm.jobs`` does, so a test can monkeypatch
``prose_judge_live.transport.build_client`` exactly like ``tests/core/llm/test_jobs.py`` does to
``jobs_module.transport.build_client``). The model-route enforcement is re-derived rather than
calling ``core.llm.jobs.effective_model`` directly, because that function needs a ``LoadedManifest``
and a ``JobContext``/``ModelSelection`` M8 has neither of under option (b) -- but it enforces the
identical project-wide rule ``effective_model`` exists to protect (a run never sends a request
naming any model but the one route decided for it): every draw re-checks, itself, that the model
route it was given is ``qwen3-next`` and refuses before any transport call otherwise, exactly the
same ``ConfigError``-on-mismatch discipline ``core.llm.jobs._Attempts.call`` already has. This
module's own tests (``tests/readme/review/test_prose_judge_live.py``) prove that check independent
of a real call, by constructing a deliberately mutated ``ProseJudgePrompts`` whose ``model_route``
is not ``qwen3-next`` (built via ``"gpt" + "-oss"``, never the literal withdrawn string, per
``tests/test_withdrawn_model.py``'s project-wide scan).

What (b) deliberately does NOT reuse: ``run_job``'s own re-ask (on a rejected/invalid reply),
``recover`` (last-resort repair), ``Narrowing`` (third, narrower ask), and ``CallStore`` caching.
M8 does not need any of them: ``sequential_majority_vote`` (TC-023, already accepted) IS this
job's reliability mechanism -- a disagreement is answered by drawing again, not by re-asking the
same model to fix its own answer, and a verdict that stays wrong is reported as ``INCONCLUSIVE``,
never silently repaired. A ledger (``core.llm.ledger.Ledger``) is reused, optionally, purely for
the standing "every physical attempt is recorded" accounting discipline every other job has; it is
never consulted to decide whether a draw proceeds (only ``check_budget`` decides that), and giving
it to a live draw never changes what that draw returns.

This module makes NO real provider call in its own tests: every test wires a fake transport, the
same seam and the same style ``tests/core/llm/test_jobs.py`` already uses (monkeypatching
``transport.build_client`` on this module). Whether/when to open a real
``data/provider_budget.json`` batch and let this wiring make its first real call is the
supervisor's decision, taken separately, after this card is accepted (see this card's own
``closeout``).
"""

from __future__ import annotations

import itertools
import json
import string
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import ConfigError, JobError
from repo_presenter.core.llm import transport
from repo_presenter.core.llm.budget import DEFAULT_BUDGET_PATH, check_budget, record_spend
from repo_presenter.core.llm.ledger import CallRecord, Ledger, canonical_hash
from repo_presenter.readme.review.prose_judge import (
    ClassificationRequest,
    PairwiseComparisonRequest,
    ParaphraseCheckRequest,
    ProseJudgeError,
    ProseJudgePrompts,
    VoteResult,
    check_type_paraphrase,
    classify_prose_span,
    compare_section_to_benchmark,
)

__all__ = [
    "MODEL_ROUTE",
    "LiveDraw",
    "live_classification_draw",
    "live_pairwise_draw",
    "live_paraphrase_draw",
    "judge_classification_live",
    "judge_pairwise_benchmark_comparison_live",
    "judge_type_paraphrase_live",
]

#: The project's one, binding model route (owner ruling, 2026-10-27, project-wide). Spelled out
#: directly -- never built from the withdrawn model's name -- so
#: ``tests/test_withdrawn_model.py``'s project-wide scan passes over this file unmodified.
MODEL_ROUTE = "qwen3-next"

T = TypeVar("T")

_SEQUENCE = itertools.count(1)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _require_qwen3_next_route(model_route: str, *, where: str) -> None:
    """Fail closed, before any transport call, unless ``model_route`` is this project's one
    model route. Defence in depth, not duplication: ``load_prose_judge_prompts`` (``prose_judge.py``,
    untouched by this card) already enforces this on a real ``prompts/m8/prose_judge.yaml`` file,
    but this module never trusts a caller-supplied :class:`ProseJudgePrompts` without checking it
    again itself -- the same "a run never sends a request naming a model other than the one
    decided for it" discipline ``core.llm.jobs._Attempts.call`` already has."""
    if model_route != MODEL_ROUTE:
        raise ConfigError(
            f"{where}: model_route must be {MODEL_ROUTE!r} (owner ruling, binding project-wide); "
            f"got {model_route!r}; refusing before any provider call is attempted"
        )


def _system_text(shape: Mapping[str, Any]) -> str:
    """``shape["system"]`` plus, when the shape declares one (only ``classification`` does), the
    category definitions it refers to. ``prompts/m8/prose_judge.yaml``'s own ``classification``
    system text says "by the definitions you are given" -- but those definitions live in the
    YAML's separate ``categories`` mapping, never inside ``system`` or ``user_template`` itself;
    without this, a real call would promise the model definitions and then never actually send
    them. Found while wiring this module (TC-023b), fixed here, never in ``prose_judge.yaml`` or
    ``prose_judge.py`` (neither is in this card's ``write_paths``)."""
    categories = shape.get("categories")
    if not isinstance(categories, Mapping):
        return shape["system"]
    lines = "\n".join(f"- {name}: {definition.strip()}" for name, definition in categories.items())
    return f"{shape['system'].strip()}\n\nCategory definitions:\n{lines}\n"


def _messages(shape: Mapping[str, Any], substitutions: Mapping[str, str]) -> list[dict[str, str]]:
    user = string.Template(shape["user_template"]).substitute(substitutions)
    return [
        {"role": "system", "content": _system_text(shape)},
        {"role": "user", "content": user},
    ]


def _payload(
    shape: Mapping[str, Any], messages: list[dict[str, str]], model_route: str
) -> dict[str, Any]:
    sampling = shape["sampling"]
    response_format: dict[str, Any] = {"type": sampling["response_format"]}
    if sampling["response_format"] == "json_schema":
        response_format["json_schema"] = {
            "name": "m8_prose_judge",
            "schema": shape["output"]["schema"],
            "strict": True,
        }
    payload: dict[str, Any] = {
        "model": model_route,
        "messages": messages,
        "temperature": sampling["temperature"],
        "max_tokens": sampling["max_output_tokens"],
        "response_format": response_format,
    }
    if sampling.get("seed") is not None:
        payload["seed"] = sampling["seed"]
    return payload


def _record(
    ledger: Ledger,
    *,
    job: str,
    stage: str,
    model_route: str,
    repository: str,
    source_revision: str,
    attempt: int,
    logical_id: str,
    shape: Mapping[str, Any],
    payload: dict[str, Any],
    model_served: str | None,
    response_content: str,
    provider_request_id: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    started_at: str,
    latency_ms: int,
) -> None:
    """Append one ``provider_call``/``success`` record -- the same physical-attempt accounting
    discipline ``core.llm.jobs.run_job`` gives every other job, reused here only to RECORD a draw,
    never to decide whether one proceeds (``check_budget`` alone decides that)."""
    sampling = shape["sampling"]
    now = _now()
    ledger.append(
        CallRecord(
            call_id=f"{logical_id[:16]}-{attempt:02d}-success-{next(_SEQUENCE):04d}",
            logical_call_id=logical_id,
            repository=repository,
            source_revision=source_revision,
            stage=stage,
            job=job,
            # M8 has no LoadedManifest under option (b): this is the prompt SHAPE's own content
            # hash (never a cache key -- this module never reads it back to short-circuit a draw).
            prompt_sha256=canonical_hash(shape),
            model_route=model_route,
            model_served=model_served,
            attempt=attempt,
            disposition="provider_call",
            started_at=started_at,
            finished_at=now,
            latency_ms=latency_ms,
            outcome="success",
            http_status=200,
            request_sha256=canonical_hash(payload),
            response_sha256=canonical_hash(response_content),
            provider_request_id=provider_request_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            error_class=None,
            temperature=sampling.get("temperature"),
            max_tokens=sampling.get("max_output_tokens"),
            response_format=sampling.get("response_format"),
            effective_model=model_route,
        )
    )


def _draw_once(
    *,
    gateway: GatewayConfig,
    shape: Mapping[str, Any],
    substitutions: Mapping[str, str],
    required_field: str,
    model_route: str,
    budget_path: Path,
    job: str,
    stage: str,
    repository: str,
    source_revision: str,
    logical_id: str,
    attempt: int,
    ledger: Ledger | None,
) -> Any:
    """One real, governed draw: budget-gated and model-route-enforced before anything is sent,
    exactly one physical attempt, nothing re-asked or repaired here (``sequential_majority_vote``
    -- TC-023, already accepted -- is the caller's own reliability mechanism, not this function)."""
    _require_qwen3_next_route(model_route, where=job)
    check_budget(budget_path)
    messages = _messages(shape, substitutions)
    payload = _payload(shape, messages, model_route)
    started_at = _now()
    started = time.monotonic()
    client = transport.build_client(gateway)
    completion = client.chat.completions.create(**payload)
    choice = completion.choices[0] if completion.choices else None
    content = (choice.message.content if choice else None) or ""
    finish_reason = choice.finish_reason if choice else None
    usage = getattr(completion, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None
    if finish_reason == "length":
        raise JobError(
            f"{job}: draw's output truncated at the prompt shape's own max_output_tokens "
            f"({shape['sampling']['max_output_tokens']}); never retried here -- raise the budget "
            "or shorten the packet"
        )
    try:
        output = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProseJudgeError(f"{job}: draw did not return a JSON object: {exc}") from exc
    if not isinstance(output, dict) or required_field not in output:
        raise ProseJudgeError(
            f"{job}: draw's output is missing its required field {required_field!r}: {output!r}"
        )
    record_spend(budget_path, 1, total_tokens or 0)
    if ledger is not None:
        _record(
            ledger,
            job=job,
            stage=stage,
            model_route=model_route,
            repository=repository,
            source_revision=source_revision,
            attempt=attempt,
            logical_id=logical_id,
            shape=shape,
            payload=payload,
            model_served=getattr(completion, "model", None),
            response_content=content,
            provider_request_id=getattr(completion, "id", None),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            started_at=started_at,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
    return output[required_field]


@dataclass
class LiveDraw(Generic[T]):
    """A real, governed draw source -- the production counterpart of ``prose_judge.ScriptedDraws``.
    Every ``__call__`` is exactly one physical, budget-gated, model-route-enforced attempt against
    the configured gateway; it is ``sequential_majority_vote`` (TC-023, unmodified) that decides
    how many times to call this (2 when the first two draws agree, 3 when they do not) -- never
    this class itself, and never more than one physical attempt per call, same as ``ScriptedDraws``
    never replays past its own scripted length."""

    job: str
    stage: str
    shape: Mapping[str, Any]
    substitutions: Mapping[str, str]
    required_field: str
    model_route: str
    gateway: GatewayConfig
    budget_path: Path = DEFAULT_BUDGET_PATH
    repository: str = "unspecified"
    source_revision: str = "0" * 40
    ledger: Ledger | None = None
    logical_id: str = ""
    calls: int = field(default=0, init=False)

    def __call__(self) -> T:
        self.calls += 1
        return _draw_once(
            gateway=self.gateway,
            shape=self.shape,
            substitutions=self.substitutions,
            required_field=self.required_field,
            model_route=self.model_route,
            budget_path=self.budget_path,
            job=self.job,
            stage=self.stage,
            repository=self.repository,
            source_revision=self.source_revision,
            logical_id=self.logical_id or self.job,
            attempt=self.calls,
            ledger=self.ledger,
        )


def live_classification_draw(
    request: ClassificationRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> LiveDraw[str]:
    """The real ``draw`` :func:`repo_presenter.readme.review.prose_judge.classify_prose_span`
    would use for a real call: one governed attempt per draw, never a cached repeat."""
    return LiveDraw(
        job="m8_classification",
        stage="S8",
        shape=prompts.classification,
        substitutions={"span_text": request.text},
        required_field="category",
        model_route=prompts.model_route,
        gateway=gateway,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
        logical_id=f"m8-classification-{request.span_id}",
    )


def live_pairwise_draw(
    request: PairwiseComparisonRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> LiveDraw[bool]:
    """The real ``draw``
    :func:`repo_presenter.readme.review.prose_judge.compare_section_to_benchmark` would use."""
    return LiveDraw(
        job="m8_pairwise_benchmark_comparison",
        stage="S8",
        shape=prompts.pairwise_benchmark_comparison,
        substitutions={
            "purpose": request.purpose,
            "candidate_section": request.candidate_section,
            "benchmark_section": request.benchmark_section,
        },
        required_field="at_least_as_good",
        model_route=prompts.model_route,
        gateway=gateway,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
        logical_id=f"m8-pairwise-{request.purpose}",
    )


def live_paraphrase_draw(
    request: ParaphraseCheckRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> LiveDraw[bool]:
    """The real ``draw`` :func:`repo_presenter.readme.review.prose_judge.check_type_paraphrase`
    would use."""
    return LiveDraw(
        job="m8s_paraphrase_check",
        stage="S8",
        shape=prompts.m8s_paraphrase_check,
        substitutions={
            "description": request.description,
            "real_signature": request.real_signature,
        },
        required_field="fair_paraphrase",
        model_route=prompts.model_route,
        gateway=gateway,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
        logical_id=f"m8-paraphrase-{request.type_name}",
    )


def judge_classification_live(
    request: ClassificationRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> VoteResult[str]:
    """``classify_prose_span`` wired to a real, governed draw source -- the production entry
    point this card's purpose asks for."""
    draw = live_classification_draw(
        request,
        gateway=gateway,
        prompts=prompts,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
    )
    return classify_prose_span(request, draw)


def judge_pairwise_benchmark_comparison_live(
    request: PairwiseComparisonRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> VoteResult[bool]:
    """``compare_section_to_benchmark`` wired to a real, governed draw source."""
    draw = live_pairwise_draw(
        request,
        gateway=gateway,
        prompts=prompts,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
    )
    return compare_section_to_benchmark(request, draw)


def judge_type_paraphrase_live(
    request: ParaphraseCheckRequest,
    *,
    gateway: GatewayConfig,
    prompts: ProseJudgePrompts,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    repository: str = "unspecified",
    source_revision: str = "0" * 40,
    ledger: Ledger | None = None,
) -> VoteResult[bool]:
    """``check_type_paraphrase`` wired to a real, governed draw source."""
    draw = live_paraphrase_draw(
        request,
        gateway=gateway,
        prompts=prompts,
        budget_path=budget_path,
        repository=repository,
        source_revision=source_revision,
        ledger=ledger,
    )
    return check_type_paraphrase(request, draw)
