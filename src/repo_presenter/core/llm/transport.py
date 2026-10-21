"""The gateway transport: the official ``openai`` SDK against the configured base URL.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``core/llm/transport.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).

``build_client`` is the one place a client is built and the one seam tests replace with a client
over a mock transport, so nothing else ever reaches the network. Retries are the project's own
(core/retry.py), so the SDK's are off. Failures are reported by status or by exception class only;
a response body can echo a request and is never repeated.

This is the actual network call-site ``core/llm/jobs.py``'s ``run_job`` fires through -- real,
unmodified from the old repository, pointed at whatever ``GatewayConfig`` it is given. Whether it
*can* actually reach a model from this environment is a question of whether ``GPT_OSS_ENDPOINT``/
``GPT_OSS_API_KEY`` are set (``core/config.py``) and a prompt manifest exists to drive it (neither
of which this taskcard built or exercised live -- see ``jobs.py``'s own module docstring).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, OpenAI

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import GatewayError


@dataclass(frozen=True)
class ModelEntry:
    id: str
    owned_by: str | None = None


@dataclass(frozen=True)
class ModelCatalog:
    """What ``GET /models`` listed, in ID order."""

    base_url: str
    models: tuple[ModelEntry, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(model.id for model in self.models)


def build_client(config: GatewayConfig) -> OpenAI:
    """One SDK client for ``config``; the key travels only in the SDK's bearer header."""
    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout_seconds,
        max_retries=0,
    )


def list_models(config: GatewayConfig) -> ModelCatalog:
    """The gateway's live model catalog; any failure is a GatewayError naming only the status."""
    client = build_client(config)
    try:
        page = client.models.list()
    except APIStatusError as exc:
        raise GatewayError(
            f"GET {config.base_url}/models answered HTTP {exc.status_code}"
        ) from None
    except APIConnectionError as exc:
        raise GatewayError(f"gateway {config.host} unreachable: {type(exc).__name__}") from None
    entries = sorted(
        (ModelEntry(model.id, getattr(model, "owned_by", None)) for model in page.data),
        key=lambda entry: entry.id,
    )
    if not entries:
        raise GatewayError(f"GET {config.base_url}/models listed no models")
    return ModelCatalog(config.base_url, tuple(entries))


@dataclass(frozen=True)
class SeedProbe:
    """What one model does with a ``seed``, from two identical bounded calls."""

    model: str
    accepted: bool
    deterministic: bool | None
    detail: str


_PROBE_MAX_TOKENS = 24


def probe_seed(config: GatewayConfig, model: str) -> SeedProbe:
    """Two identical bounded completions carrying the same ``seed``, compared byte for byte."""
    client = build_client(config)
    messages = _liveness_messages()
    replies: list[str] = []
    for _ in range(2):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=_PROBE_MAX_TOKENS,
                temperature=0,
                seed=1,
            )
        except APIStatusError as exc:
            return SeedProbe(model, False, None, f"HTTP {exc.status_code}")
        except APIConnectionError as exc:
            raise GatewayError(f"gateway {config.host} unreachable: {type(exc).__name__}") from None
        choices = completion.choices or []
        if not choices:
            return SeedProbe(model, True, None, "accepted, no content returned")
        replies.append(choices[0].message.content or "")
    deterministic = replies[0] == replies[1]
    return SeedProbe(
        model,
        True,
        deterministic,
        "honoured" if deterministic else "accepted, non-deterministic",
    )


@dataclass(frozen=True)
class AvailabilityProbe:
    """One model's availability: whether it answered, and how it failed when it did not."""

    model: str
    available: bool
    detail: str


def _liveness_messages() -> list[dict[str, str]]:
    return [{"role": "user", "content": "ping"}]


_PROBE_SCHEMA_NAME = "availability_probe"
_PROBE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"status": {"type": "string", "enum": ["ok"]}},
    "required": ["status"],
    "additionalProperties": False,
}
_AVAILABILITY_MAX_TOKENS = 16
_AVAILABILITY_TIMEOUT_SECONDS = 120.0


def _satisfies_probe_schema(content: str) -> bool:
    try:
        output = json.loads(content)
    except json.JSONDecodeError:
        return False
    return Draft202012Validator(_PROBE_SCHEMA).is_valid(output)


def probe_availability(config: GatewayConfig, model: str) -> AvailabilityProbe:
    """One tiny strict json_schema completion; passes only on HTTP 200 with schema-valid content."""
    client = build_client(config).with_options(timeout=_AVAILABILITY_TIMEOUT_SECONDS, max_retries=0)
    response_format: dict[str, Any] = {
        "type": "json_schema",
        "json_schema": {"name": _PROBE_SCHEMA_NAME, "schema": _PROBE_SCHEMA, "strict": True},
    }
    try:
        completion = client.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=_liveness_messages(),
            max_tokens=_AVAILABILITY_MAX_TOKENS,
            temperature=0,
            response_format=response_format,
        )
    except APIStatusError as exc:
        return AvailabilityProbe(model, False, f"HTTP {exc.status_code}")
    except APITimeoutError:
        return AvailabilityProbe(model, False, "timeout")
    except APIConnectionError as exc:
        return AvailabilityProbe(model, False, type(exc).__name__)
    except APIError as exc:
        return AvailabilityProbe(model, False, type(exc).__name__)
    choices = completion.choices or []
    content = (choices[0].message.content or "") if choices else ""
    if not content:
        return AvailabilityProbe(model, False, "HTTP 200, no content")
    if not _satisfies_probe_schema(content):
        return AvailabilityProbe(model, False, "HTTP 200, content not schema-valid")
    return AvailabilityProbe(model, True, "HTTP 200, schema-valid")
