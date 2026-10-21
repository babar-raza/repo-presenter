"""Run one governed job: render its packet, call the gateway, validate and bind the output.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``core/llm/jobs.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry) -- the single
deterministic/agentic boundary the whole Lane R pipeline calls through. See this taskcard's final
report for the full provider-boundary finding; summarised here as a standing note on the module:

**What this targets.** The old repository's own ``core/config.py`` documents a single, fixed
provider shape: one owner-provided, OpenAI-*compatible* HTTP endpoint (``GPT_OSS_ENDPOINT`` +
``GPT_OSS_API_KEY``, read by ``core/config.py``), called through the official ``openai`` Python
SDK (``core/llm/transport.py``'s ``build_client``/``_complete``, unchanged below) -- never
api.openai.com itself, and never Anthropic/Claude. The old repo's own in-code comments name the
model actually served through it as ``qwen3-next`` (a self-hosted/gateway-served open model,
consistent with the ``GPT_OSS_*`` variable names). This file, ``transport.py``, ``fallback.py``,
``ledger.py``, ``narrowing.py``, ``binding.py``, ``prompts.py`` and ``config.py`` are ported
verbatim (import paths only adapted) -- the MECHANISM is faithful and unmodified.

**Whether it can fire here.** This taskcard confirmed, by environment-variable NAME only (values
never read, logged or transmitted), that ``GPT_OSS_ENDPOINT`` and ``GPT_OSS_API_KEY`` ARE present
in this agent's own execution environment. ``core/config.py.load_gateway_config`` will therefore
resolve a real ``GatewayConfig`` here. What is NOT in this repository yet is a real
``prompts/*.yaml`` governed-prompt-manifest system (``core/llm/prompts.py``'s own ``load_manifests``
needs a ``prompts/`` directory that does not exist here -- that is prompt *content*, a separate,
not-yet-done taskcard, not mechanism) -- so there is no real ``LoadedManifest`` to hand ``run_job``
in production yet. ``run_job``'s call-site itself needed NO new abstraction to be made pluggable:
it already takes its ``LoadedManifest``, ``GatewayConfig`` and ``CallStore`` as plain caller-
supplied arguments (nothing hardwires a specific manifest or endpoint), so a caller that builds a
real manifest and points ``config`` at a real ``GatewayConfig`` exercises the real network path
through ``transport.build_client``/``openai`` today, unmodified. This port's own tests exercise the
caching/re-ask/recover/narrow machinery hermetically, with a hand-built ``PromptManifest`` and a
fake ``_complete``-equivalent (monkeypatching ``transport.build_client``), never a live network
call -- see ``tests/readme/composition/test_jobs.py``. No part of this port fabricates a working
call where none exists: the mechanism is real and wired to a real provider; what is missing is
prompt content, not a transport, a cache, or a retry/repair boundary.

A job is one manifest plus one packet. The runner renders the manifest's templates with the
packet, sends one chat completion at the manifest's route and sampling contract, parses the JSON
object it returns, validates it against the manifest's output schema, and binds every cited ID to
the facts. A rejected output earns exactly one re-ask that quotes the rejection; a second
rejection fails the job closed, unless the job passes a ``Narrowing``: one further, narrower ask
for only the part of the second reply still wrong, the rest kept as given. Every physical attempt
is recorded in the ledger. An accepted output is stored under the hash of the request that
produced it, so the same request in a later run reuses it with zero provider calls and a
``cache_reuse`` ledger record.
"""

from __future__ import annotations

import copy
import functools
import itertools
import json
import re
import string
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from openai import APIConnectionError, APIStatusError, APITimeoutError

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import ConfigError, JobError
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm import transport
from repo_presenter.core.llm.binding import (
    add_silent_units,
    binding_errors,
    drop_unknown_finding_ids,
    fill_silent_units,
    fold_duplicate_units,
    resolve_symbol_ids,
    silent_unit_ids,
)
from repo_presenter.core.llm.fallback import ModelSelection
from repo_presenter.core.llm.ledger import CallRecord, Ledger, canonical_hash
from repo_presenter.core.llm.narrowing import Narrowing
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.core.retry import RetryableOperationError, run_with_retry

CALLS_DIRNAME = "calls"
_TRANSIENT_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})

# The gateway's own strict response_format.json_schema decoding does not need the schema restated
# as text in the system message too (it is already enforced structurally by response_format and
# re-validated by Draft202012Validator); below this count an enum stays inline in the system
# message as a convenience, above it only its size is shown.
_PROMPT_ENUM_INLINE_LIMIT = 50


def _prompt_schema(node: Any, omitted: list[int]) -> Any:
    """A copy of a schema (or any JSON-like value inside one) for system-message *text* only.

    Every ``enum`` array longer than ``_PROMPT_ENUM_INLINE_LIMIT`` is replaced by its size, never
    its members - ``omitted`` collects each count so ``render_messages`` can tell the model the
    substitution happened. ``response_format`` and re-validation both call ``schema_for`` directly
    and never pass through here, so what actually constrains and judges a reply is always the
    untouched, full schema; this function only shortens the redundant plain-text restatement.
    """
    if isinstance(node, dict):
        rendered: dict[str, Any] = {}
        for key, value in node.items():
            if key == "enum" and isinstance(value, list) and len(value) > _PROMPT_ENUM_INLINE_LIMIT:
                omitted.append(len(value))
                rendered[key] = (
                    f"<{len(value)} allowed values, enforced by the request's response_format "
                    "and re-validated on reply; omitted here to keep this prompt copy short>"
                )
            else:
                rendered[key] = _prompt_schema(value, omitted)
        return rendered
    if isinstance(node, list):
        return [_prompt_schema(item, omitted) for item in node]
    return node


@dataclass(frozen=True)
class JobContext:
    """Where a run's calls belong, and which model each route answers with for the whole run."""

    repository: str
    source_revision: str
    models: ModelSelection | None = None


def effective_model(manifest: LoadedManifest, context: JobContext) -> str:
    """The model this run's calls of ``manifest`` name: the run's selection, else the primary."""
    route = manifest.manifest.model_route
    return route if context.models is None else context.models.model_for(route)


@dataclass(frozen=True)
class JobResult:
    job: str
    output: dict[str, Any]
    request_sha256: str
    attempts: int
    provider_calls: int
    cache_reused: bool
    model_served: str | None
    total_tokens: int | None


@dataclass(frozen=True)
class _Reply:
    content: str
    model: str | None
    request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None = None


class CallStore:
    """Accepted outputs keyed by request hash, under the transaction directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, request_sha256: str) -> Path:
        return self.directory / f"{request_sha256[:12]}.json"

    def get(self, request_sha256: str) -> dict[str, Any] | None:
        output = self.record(request_sha256).get("output")
        return output if isinstance(output, dict) else None

    def record(self, request_sha256: str) -> dict[str, Any]:
        """The stored record (job, model_served, output), or an empty mapping."""
        path = self.path(request_sha256)
        if not path.is_file():
            return {}
        stored = json.loads(path.read_text(encoding="utf-8"))
        return stored if isinstance(stored, dict) else {}

    def put(
        self, request_sha256: str, job: str, model_served: str | None, output: dict[str, Any]
    ) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"job": job, "model_served": model_served, "output": output}
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        self.path(request_sha256).write_bytes(text.encode("utf-8"))

    def reject(
        self,
        request_sha256: str,
        attempt: int,
        job: str,
        content: str,
        errors: list[str],
        *,
        stage: str = "",
    ) -> Path:
        """Keep a rejected reply beside the store, so a rejection can be read, never guessed."""
        self.directory.mkdir(parents=True, exist_ok=True)
        suffix = f"-{stage}" if stage else ""
        path = self.directory / f"{request_sha256[:12]}.rejected-{attempt}{suffix}.json"
        payload = {"job": job, "attempt": attempt, "rejection": errors, "content": content}
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        path.write_bytes(text.encode("utf-8"))
        return path

    def record_repairs(
        self,
        request_sha256: str,
        attempt: int,
        job: str,
        changes: Sequence[Mapping[str, Any]],
    ) -> Path:
        """Keep, beside the store, what a job's last-resort ``recover`` changed in the reply it
        accepted."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{request_sha256[:12]}.repaired-{attempt}.json"
        payload = {
            "job": job,
            "attempt": attempt,
            "source": "recover",
            "outcome": "repaired",
            "request_sha256": request_sha256,
            "changes": [dict(change) for change in changes],
        }
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        path.write_bytes(text.encode("utf-8"))
        return path


def schema_for(manifest: LoadedManifest, call_schema: dict[str, Any] | None) -> dict[str, Any]:
    """The schema this call is judged by: the manifest's, or the one the job specialised for it."""
    return manifest.manifest.output.schema_ if call_schema is None else call_schema


def render_messages(
    manifest: LoadedManifest,
    packet: Mapping[str, Any],
    call_schema: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """The system and user messages for ``packet``; the packet must match the manifest exactly."""
    fields = manifest.manifest.packet
    expected = fields.names
    given = frozenset(packet)
    if given != expected:
        missing = sorted(expected - given)
        extra = sorted(given - expected)
        raise ConfigError(
            f"packet for {manifest.manifest.prompt_id} does not match its manifest "
            f"(missing {missing}, unexpected {extra})"
        )
    rendered: dict[str, str] = {}
    for field in fields.fields:
        value = packet[field.name]
        if field.type == "json":
            rendered[field.name] = json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False)
        elif isinstance(value, str):
            rendered[field.name] = value
        else:
            raise ConfigError(f"packet field {field.name} must be a string")
    user = string.Template(manifest.manifest.user_template).substitute(rendered)
    omitted: list[int] = []
    condensed = _prompt_schema(schema_for(manifest, call_schema), omitted)
    schema = json.dumps(condensed, indent=1, sort_keys=True)
    preface = manifest.manifest.schema_preface.strip()
    if omitted:
        preface = (
            f"{preface} (some `enum` fields below show a count of allowed values instead of "
            "listing them - every one of them is still enforced exactly, at decode and again on "
            "reply, from this same schema; only this text copy is shortened)"
        )
    system = f"{manifest.manifest.system.rstrip()}\n\n{preface}\n{schema}\n"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def request_payload(
    manifest: LoadedManifest,
    messages: list[dict[str, str]],
    call_schema: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """The chat-completion request; ``json_schema`` makes the gateway enforce the output shape."""
    sampling = manifest.manifest.sampling
    response_format: dict[str, Any] = {"type": sampling.response_format}
    if sampling.response_format == "json_schema":
        response_format["json_schema"] = {
            "name": manifest.manifest.prompt_id,
            "schema": schema_for(manifest, call_schema),
            "strict": True,
        }
    payload: dict[str, Any] = {
        "model": manifest.manifest.model_route if model is None else model,
        "messages": messages,
        "temperature": sampling.temperature,
        "max_tokens": sampling.max_output_tokens,
        "response_format": response_format,
    }
    if sampling.seed is not None:
        payload["seed"] = sampling.seed
    return payload


def _complete(config: GatewayConfig, payload: dict[str, Any]) -> _Reply:
    # Looked up on the module so the test seam that swaps the client applies here too.
    client = transport.build_client(config)
    completion = client.chat.completions.create(**payload)
    usage = completion.usage
    choice = completion.choices[0] if completion.choices else None
    return _Reply(
        content=(choice.message.content if choice else None) or "",
        model=completion.model,
        request_id=completion.id,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
        finish_reason=choice.finish_reason if choice else None,
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


_SEQUENCE = itertools.count(1)


def _call_id(logical_id: str, attempt: int, outcome: str, started_at: str) -> str:
    """One ID per physical attempt or explicit reuse event, unique by construction."""
    stamp = re.sub(r"[^0-9T]", "", started_at.split("+", 1)[0])
    return f"{logical_id[:16]}-{attempt:02d}-{outcome}-{stamp}-{next(_SEQUENCE):04d}"


class _Attempts:
    """Physical-attempt accounting for one logical call."""

    def __init__(
        self,
        manifest: LoadedManifest,
        context: JobContext,
        ledger: Ledger,
        logical_id: str,
        model: str | None = None,
    ) -> None:
        self.manifest = manifest
        self.context = context
        self.ledger = ledger
        self.logical_id = logical_id
        self.model = effective_model(manifest, context) if model is None else model
        self.count = 0
        self.last_model: str | None = None
        self.last_tokens: int | None = None

    def call(self, config: GatewayConfig, payload: dict[str, Any]) -> _Reply:
        if payload.get("model") != self.model:
            raise ConfigError(
                f"{self.manifest.manifest.prompt_id}: request names {payload.get('model')!r} but "
                f"this run decided {self.model!r}; a run never switches models mid-run"
            )
        self.ledger.reserve_provider_call()
        self.count += 1
        started_at = _now()
        started = time.monotonic()
        try:
            reply = _complete(config, payload)
        except APIStatusError as exc:
            self._record(
                payload, started_at, started, "http_error", exc.status_code, type(exc).__name__
            )
            if exc.status_code in _TRANSIENT_STATUSES:
                retry_after = exc.response.headers.get("Retry-After")
                raise RetryableOperationError(
                    f"HTTP {exc.status_code}",
                    retry_after_seconds=float(retry_after) if retry_after else None,
                ) from None
            raise JobError(
                f"{self.manifest.manifest.prompt_id}: gateway answered HTTP {exc.status_code}"
            ) from None
        except APITimeoutError as exc:
            self._record(payload, started_at, started, "timeout", None, type(exc).__name__)
            raise RetryableOperationError("timeout") from None
        except APIConnectionError as exc:
            self._record(payload, started_at, started, "connection_error", None, type(exc).__name__)
            raise RetryableOperationError(type(exc).__name__) from None
        self.last_model = reply.model
        self.last_tokens = reply.total_tokens
        self._record(payload, started_at, started, "success", 200, None, reply)
        return reply

    def record_invalid(self, error_class: str, rejection: Sequence[str] = ()) -> None:
        """Mark the last successful attempt's output as rejected without a new call."""
        record = self._base(None, _now(), 0, "response_invalid", 200, error_class)
        self.ledger.append(replace(record, rejection=tuple(rejection)))

    def _record(
        self,
        payload: dict[str, Any],
        started_at: str,
        started: float,
        outcome: str,
        status: int | None,
        error_class: str | None,
        reply: _Reply | None = None,
    ) -> None:
        latency = int((time.monotonic() - started) * 1000)
        record = self._base(payload, started_at, latency, outcome, status, error_class, reply)
        self.ledger.append(record)

    def _base(
        self,
        payload: dict[str, Any] | None,
        started_at: str,
        latency_ms: int,
        outcome: str,
        status: int | None,
        error_class: str | None,
        reply: _Reply | None = None,
    ) -> CallRecord:
        request_sha256 = (
            canonical_hash({"prompt_sha256": self.manifest.sha256, "payload": payload})
            if payload is not None
            else self.logical_id
        )
        return CallRecord(
            call_id=_call_id(self.logical_id, self.count, outcome, started_at),
            logical_call_id=self.logical_id,
            repository=self.context.repository,
            source_revision=self.context.source_revision,
            stage=self.manifest.manifest.stage,
            job=self.manifest.manifest.prompt_id,
            prompt_sha256=self.manifest.sha256,
            model_route=self.manifest.manifest.model_route,
            model_served=reply.model if reply else self.last_model,
            effective_model=self.model,
            attempt=self.count,
            disposition="provider_call",
            started_at=started_at,
            finished_at=_now(),
            latency_ms=latency_ms,
            outcome=outcome,  # type: ignore[arg-type]
            http_status=status,
            request_sha256=request_sha256,
            response_sha256=canonical_hash(reply.content) if reply else None,
            provider_request_id=reply.request_id if reply else None,
            prompt_tokens=reply.prompt_tokens if reply else None,
            completion_tokens=reply.completion_tokens if reply else None,
            total_tokens=reply.total_tokens if reply else None,
            error_class=error_class,
            temperature=self.manifest.manifest.sampling.temperature,
            max_tokens=self.manifest.manifest.sampling.max_output_tokens,
            response_format=self.manifest.manifest.sampling.response_format,
            derived_via_reask=self.count > 1,
        )


Checks = Callable[[dict[str, Any]], list[str]]
Narrow = Callable[[Sequence[str]], tuple[Mapping[str, Any], dict[str, Any] | None]]


_ENUM_SHOWN = 12


def _schema_message(error: Any) -> str:
    """A schema error's text, with a long ``enum`` shown as its first few values and a count."""
    allowed = error.validator_value if error.validator == "enum" else None
    if not isinstance(allowed, list) or len(allowed) <= _ENUM_SHOWN:
        return str(error.message)
    return (
        f"{error.instance!r} is not one of {allowed[:_ENUM_SHOWN]!r} "
        f"(and {len(allowed) - _ENUM_SHOWN} more allowed values; cite only an offered ID)"
    )


def schema_error_lines(error: Any) -> list[str]:
    """A schema error as the lines the re-ask quotes: ``path: message``."""
    context = list(getattr(error, "context", None) or [])
    if error.validator not in {"anyOf", "oneOf"} or not context:
        return [f"{error.json_path}: {_schema_message(error)}"]
    branches: dict[Any, list[Any]] = {}
    for sub in context:
        head = sub.schema_path[0] if sub.schema_path else 0
        branches.setdefault(head, []).append(sub)
    closest = min(
        branches.values(),
        key=lambda errors: (any(e.validator == "type" for e in errors), len(errors)),
    )
    return [
        line
        for sub in sorted(closest, key=lambda e: e.json_path)
        for line in schema_error_lines(sub)
    ]


def _parse(
    manifest: LoadedManifest,
    content: str,
    facts: FactsDocument,
    checks: Checks | None = None,
    call_schema: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        output = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, [f"output is not a JSON object: {exc.msg} at position {exc.pos}"]
    if not isinstance(output, dict):
        return None, ["output is not a JSON object"]
    validator = Draft202012Validator(schema_for(manifest, call_schema))
    errors = [
        line
        for error in sorted(validator.iter_errors(output), key=lambda error: error.json_path)
        for line in schema_error_lines(error)
    ]
    schema_valid = not errors
    resolve_symbol_ids(output, facts)  # a symbol cited by its read path binds to its fact
    if manifest.manifest.output.binding == "finding_ids":
        drop_unknown_finding_ids(output, facts)  # an invented pointer is no evidence at all
    if manifest.manifest.output.binding == "unit_ids":
        fold_duplicate_units(output)  # a repeated disposition answers nothing the first lacked
    errors.extend(binding_errors(output, facts, manifest.manifest.output.binding))
    if schema_valid and checks is not None:
        errors.extend(checks(output))
    return (output if not errors else None), errors


def request_hash(
    manifest: LoadedManifest,
    packet: Mapping[str, Any],
    call_schema: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> str:
    """The store key ``run_job`` would compute for this exact packet, without calling anything."""
    messages = render_messages(manifest, packet, call_schema)
    payload = request_payload(manifest, messages, call_schema, model=model)
    return canonical_hash({"prompt_sha256": manifest.sha256, "payload": payload})


def run_job(
    manifest: LoadedManifest,
    packet: Mapping[str, Any],
    *,
    config: GatewayConfig,
    facts: FactsDocument,
    ledger: Ledger,
    store: CallStore,
    context: JobContext,
    checks: Checks | None = None,
    call_schema: dict[str, Any] | None = None,
    recover: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    narrow: Narrow | Narrowing | None = None,
) -> JobResult:
    """The accepted output of one job, from the store when the same request was accepted before.

    ``checks`` are the job's own rules beyond schema and binding; they may normalise the output
    in place before judging it, and their errors are quoted back in the one re-ask exactly like
    the others. What the checks accept is what is stored - the folded output, which is why a
    stored output is re-judged without ``call_schema`` (below).

    ``recover`` is a last-resort, job-specific correction: it runs only after the FINAL attempt is
    still rejected, on that exact raw reply, and only when the reply parsed as a JSON object. Its
    return, if not ``None``, is re-validated from scratch through the same schema, binding and
    ``checks`` every other attempt goes through before it can be accepted - never accepted on
    ``recover``'s own say-so.

    ``narrow`` is one further, narrower ask for the part of the second reply that is still wrong.
    """
    job = manifest.manifest.prompt_id
    model = effective_model(manifest, context)
    messages = render_messages(manifest, packet, call_schema)
    payload = request_payload(manifest, messages, call_schema, model=model)
    request_sha256 = canonical_hash({"prompt_sha256": manifest.sha256, "payload": payload})
    stored = store.get(request_sha256)
    if stored is not None:
        output, _rejection = _parse(manifest, json.dumps(stored), facts, checks, None)
        now = _now()
        reuse = CallRecord(
            call_id=_call_id(request_sha256, 0, "cache_reuse", now),
            logical_call_id=request_sha256,
            repository=context.repository,
            source_revision=context.source_revision,
            stage=manifest.manifest.stage,
            job=job,
            prompt_sha256=manifest.sha256,
            model_route=manifest.manifest.model_route,
            model_served=None,
            effective_model=model,
            attempt=0,
            disposition="cache_reuse",
            started_at=now,
            finished_at=now,
            latency_ms=0,
            outcome="cache_reuse",
            http_status=None,
            request_sha256=request_sha256,
            response_sha256=canonical_hash(output if output is not None else stored),
            provider_request_id=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            error_class=None,
            temperature=manifest.manifest.sampling.temperature,
            max_tokens=manifest.manifest.sampling.max_output_tokens,
            response_format=manifest.manifest.sampling.response_format,
            derived_via_reask=False,
        )
        if output is None:
            ledger.append(
                replace(
                    reuse,
                    call_id=_call_id(request_sha256, 0, "cache_stale", now),
                    disposition="cache_stale",
                    outcome="cache_stale",
                    error_class="OutputRejected",
                )
            )
        else:
            if output != stored:
                model_served = store.record(request_sha256).get("model_served")
                store.put(request_sha256, job, model_served, output)
            ledger.append(reuse)
            return JobResult(job, output, request_sha256, 0, 0, True, None, None)

    attempts = _Attempts(manifest, context, ledger, request_sha256, model)
    narrowing = _narrowing(narrow, manifest, facts)
    current = payload
    rejection: list[str] = []
    recovered_rejection: list[str] = []
    first_reply = ""
    narrowed_units: list[str] = []
    repeated_units: list[str] = []
    merged_so_far = ""
    for ask in (1, 2, 3):
        if ask == 3:
            if not narrowed_units or narrowing is None:
                break
            narrowed_packet, narrowed_schema = narrowing.ask(
                narrowed_units, merged_so_far, rejection, repeated_units
            )
            current = request_payload(
                manifest,
                render_messages(manifest, narrowed_packet, narrowed_schema),
                narrowed_schema,
                model=model,
            )
        reply = run_with_retry("llm_call", functools.partial(attempts.call, config, current))
        if reply.finish_reason == "length":
            truncated = ("output truncated at the manifest's max_output_tokens",)
            store.reject(request_sha256, ask, job, reply.content, list(truncated))
            attempts.record_invalid("TruncatedOutput", truncated)
            raise JobError(
                f"{job}: output truncated at the manifest's max_output_tokens "
                f"({manifest.manifest.sampling.max_output_tokens}); raise the budget or bound "
                "the output, never retry"
            )
        content = reply.content
        earlier_reply = first_reply
        if ask == 2 and manifest.manifest.output.binding == "unit_ids":
            content = _complete_from_first_reply(content, first_reply)
        elif ask == 3 and narrowing is not None:
            content = narrowing.merge(merged_so_far, content, narrowed_units)
        first_reply = reply.content
        output, rejection = _parse(manifest, content, facts, checks, call_schema)
        if output is not None:
            store.put(request_sha256, job, reply.model, output)
            return JobResult(
                job,
                output,
                request_sha256,
                attempts.count,
                attempts.count,
                False,
                reply.model,
                attempts.last_tokens,
            )
        attempts.record_invalid("OutputRejected", rejection)
        store.reject(request_sha256, ask, job, reply.content, rejection)
        if ask == 1:
            current = _re_ask(manifest, payload, reply.content, rejection)
        else:
            if ask == 2 and narrowing is not None:
                narrowed_units = narrowing.pending(content, rejection)
                if narrowed_units and narrowing.repeated is not None:
                    repeated_units = narrowing.repeated(earlier_reply, content, narrowed_units)
                if narrowed_units:
                    merged_so_far = content
                    continue
            if recover is not None:
                candidates = [(content, "fix")]
                if ask == 3 and merged_so_far and merged_so_far != content:
                    candidates.append((merged_so_far, "fix-second"))
                for candidate, stage in candidates:
                    try:
                        raw = json.loads(candidate)
                    except json.JSONDecodeError:
                        raw = None
                    before = copy.deepcopy(raw)  # ``recover`` corrects in place
                    corrected = recover(raw) if isinstance(raw, dict) else None
                    if corrected is None:
                        continue
                    fixed, fixed_rejection = _parse(
                        manifest, json.dumps(corrected), facts, checks, None
                    )
                    if fixed is not None:
                        store.put(request_sha256, job, reply.model, fixed)
                        store.record_repairs(
                            request_sha256, ask, job, repair_changes(before, corrected)
                        )
                        return JobResult(
                            job,
                            fixed,
                            request_sha256,
                            attempts.count,
                            attempts.count,
                            False,
                            reply.model,
                            attempts.last_tokens,
                        )
                    store.reject(
                        request_sha256,
                        ask,
                        job,
                        json.dumps(corrected),
                        fixed_rejection,
                        stage=stage,
                    )
                    recovered_rejection = recovered_rejection or fixed_rejection
    asked = (
        f"three times (the third a narrowed ask for {narrowing.subject})"
        if narrowed_units and narrowing is not None
        else "twice"
    )
    message = f"{job}: output rejected {asked}; last rejection: {'; '.join(rejection)}"
    if recovered_rejection:
        message += f"; recover's correction was rejected too: {'; '.join(recovered_rejection)}"
    raise JobError(message)


def _narrowing(
    narrow: Narrow | Narrowing | None, manifest: LoadedManifest, facts: FactsDocument
) -> Narrowing | None:
    """The :class:`Narrowing` a ``narrow`` argument stands for: itself, or - for the plain callable
    that serves a ``unit_ids`` job - the narrowed ask for the inherited units still silent."""
    if narrow is None or isinstance(narrow, Narrowing):
        return narrow
    if manifest.manifest.output.binding != "unit_ids":
        return None
    return Narrowing(
        pending=lambda content, _rejection: _silent_units(content, facts),
        ask=lambda units, _content, _rejection, _repeated: narrow(units),
        merge=lambda merged, narrowed, units: _add_narrowed_units(narrowed, merged, units),
    )


_CHANGE_VALUE_LIMIT = 2000  # characters of a replaced value kept in a repair record


def repair_changes(before: Any, after: Any) -> list[dict[str, Any]]:
    """What a ``recover`` changed, as one entry per changed leaf."""
    changes: list[dict[str, Any]] = []

    def walk(old: Any, new: Any, path: tuple[str, ...]) -> None:
        if old == new:
            return
        if isinstance(old, dict) and isinstance(new, dict) and old.keys() == new.keys():
            for key in old:
                walk(old[key], new[key], (*path, str(key)))
            return
        if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
            for index, (a, b) in enumerate(zip(old, new, strict=True)):
                walk(a, b, (*path, str(index)))
            return
        change: dict[str, Any] = {
            "id": f"R{len(changes) + 1:02d}",
            "path": ".".join(path),
            "before": _shown(old),
            "after": _shown(new),
        }
        if len(path) >= 2 and path[0] == "units" and path[1].isdigit():
            units = after.get("units") if isinstance(after, dict) else None
            if isinstance(units, list) and int(path[1]) < len(units):
                slot = (
                    units[int(path[1])].get("slot")
                    if isinstance(units[int(path[1])], dict)
                    else None
                )
                if isinstance(slot, str):
                    change["slot"] = slot
        changes.append(change)

    walk(before, after, ())
    return changes


def _shown(value: Any) -> Any:
    text = (
        value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    )
    return text if len(text) <= _CHANGE_VALUE_LIMIT else text[:_CHANGE_VALUE_LIMIT] + "..."


def _silent_units(content: str, facts: FactsDocument) -> list[str]:
    """The inherited units ``content`` leaves without a disposition; empty when ``content`` is not
    a JSON object."""
    try:
        return silent_unit_ids(json.loads(content), facts)
    except json.JSONDecodeError:
        return []


def _add_narrowed_units(narrowed: str, merged: str, silent: Sequence[str]) -> str:
    """``merged`` extended with the ``silent`` units' entries from the ``narrowed`` reply."""
    try:
        base, extra = json.loads(merged), json.loads(narrowed)
    except json.JSONDecodeError:
        return merged
    return json.dumps(add_silent_units(base, extra, frozenset(silent)))


def _complete_from_first_reply(content: str, first: str) -> str:
    """``content`` with the units it is silent on filled from the first reply."""
    try:
        revised, original = json.loads(content), json.loads(first)
    except json.JSONDecodeError:
        return content
    completed = fill_silent_units(revised, original)
    return content if completed == revised else json.dumps(completed)


def _re_ask(
    manifest: LoadedManifest, payload: dict[str, Any], previous: str, errors: list[str]
) -> dict[str, Any]:
    """The same request plus the rejected output and the manifest's correction, once."""
    template = string.Template(manifest.manifest.rejection_template)
    correction = template.substitute(errors="\n- ".join(errors)).strip()
    messages = [
        *payload["messages"],
        {"role": "assistant", "content": previous},
        {"role": "user", "content": correction},
    ]
    return {**payload, "messages": messages}
