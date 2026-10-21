"""Gateway configuration read from the process environment, never from a file.

Ported (REUSE, near-verbatim) from the old repository-presenter project's ``core/config.py`` per
migration/reuse-manifest.yaml ("readme/composition/" entry); only the import path and the
old repo's own internal item-tracker reference (``OWNER-02``) are adapted away.

The owner provides ``GPT_OSS_ENDPOINT`` (the OpenAI-compatible base URL) and ``GPT_OSS_API_KEY``
as process environment variables; no ``.env`` file is read or required. ``GPT_OSS_MODEL`` is an
optional override of a manifest's default route, for local experimentation only. A missing
variable fails closed with a ``ConfigError``. The key is excluded from every repr.

This taskcard (2026-10-21) confirmed ``GPT_OSS_ENDPOINT`` and ``GPT_OSS_API_KEY`` ARE present as
named environment variables in this agent's own execution environment (checked by name only, per
instruction -- their values were never read, logged, or sent anywhere). Whether that endpoint is
reachable from wherever this code eventually runs, and whether it still serves a model this
repository's own (not-yet-written) prompt manifests would route to, was NOT verified live: no
``prompts/*.yaml`` governed-prompt-manifest system exists in this repository yet (that pull is a
separate, not-yet-done taskcard -- see ``core/llm/prompts.py``'s own module docstring), so there is
no real ``LoadedManifest`` to send a real request with yet. See ``core/llm/jobs.py``'s own module
docstring for exactly what is mechanism-only versus actually wired to fire.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from repo_presenter.core.errors import ConfigError

ENDPOINT_VARIABLE = "GPT_OSS_ENDPOINT"
API_KEY_VARIABLE = "GPT_OSS_API_KEY"
MODEL_VARIABLE = "GPT_OSS_MODEL"
RESUME_PREDICATE = (
    f"{ENDPOINT_VARIABLE} and {API_KEY_VARIABLE} are present in the process environment"
)
# One request's total budget at the gateway. The old repository calibrated this from its own
# production ledger (783 successful provider calls; see the old repo's core/config.py for the
# fitted latency formula and the measured 355.4s longest successful call) -- that empirical
# calibration does not transfer to this repository, which has made no provider calls yet, so the
# figure is kept as the old repo's own measured ceiling with headroom rather than re-derived here.
DEFAULT_TIMEOUT_SECONDS = 900.0


@dataclass(frozen=True)
class GatewayConfig:
    """Where the gateway is and how to authenticate; the key is excluded from every repr."""

    base_url: str
    api_key: str = field(repr=False)
    model_override: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).netloc


def load_gateway_config(environment: Mapping[str, str]) -> GatewayConfig:
    """Read the gateway variables from ``environment``; absence fails closed."""
    endpoint = (environment.get(ENDPOINT_VARIABLE) or "").strip()
    api_key = (environment.get(API_KEY_VARIABLE) or "").strip()
    missing = [
        name
        for name, value in ((ENDPOINT_VARIABLE, endpoint), (API_KEY_VARIABLE, api_key))
        if not value
    ]
    if missing:
        raise ConfigError(
            f"{' and '.join(missing)} not set in the process environment; "
            f"resume when {RESUME_PREDICATE}"
        )
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ConfigError(f"{ENDPOINT_VARIABLE} is not an absolute http(s) URL")
    override = (environment.get(MODEL_VARIABLE) or "").strip() or None
    return GatewayConfig(endpoint.rstrip("/"), api_key, override)
