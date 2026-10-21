"""Configured secrets and the redaction every bounded execution's output passes through.

Ported (ADAPT, trimmed) from the old repository-presenter project's ``core/secrets.py`` per
migration/reuse-manifest.yaml. ``redact`` and the secret-shaped-value pattern it uses are carried
verbatim: ``core/execution.py`` calls it on every subprocess's stdout/stderr before a receipt is
built, so a live credential value is never written into a fact's evidence. The old file's
``find_secret_leaks`` (a candidate-bundle leak canary keyed on ``core/candidates.py``'s
``CANDIDATES_DIRNAME``) and ``stage_transaction_for_upload`` are NOT ported here: both depend on
``core/candidates.py`` (bundle/transaction machinery this repository has not pulled), and neither is
on the path ``core/execution.py`` needs. Port them together with ``core/candidates.py`` if/when a
bundle-leak canary is built.

The process environment names the secrets the runtime is configured with: the variables listed in
``.env.example`` and any variable whose name ends in a secret-bearing suffix. The leak is reported
by variable name and file path only; the value itself is never echoed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

SECRET_VARIABLES = frozenset(
    {
        "GPT_OSS_API_KEY",
        "GH_TOKEN",
        "GH_METADATA_WRITE_TOKEN",
        "GH_ISSUES_WRITE_TOKEN",
        "GH_PROPOSAL_WRITE_TOKEN",
        "GH_CANDIDATES_WRITE_TOKEN",
        "GH_APP_ID",
        "GH_APP_PRIVATE_KEY",
        "GH_APP_CLIENT_ID",
        "GH_APP_CLIENT_SECRET",
        "GH_APP_WEBHOOK_SECRET",
    }
)
SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
MIN_SECRET_LENGTH = 8


@dataclass(frozen=True)
class ConfiguredSecret:
    """One secret the runtime is configured with. Its value never appears in a repr."""

    variable: str
    value: bytes = field(repr=False)


@dataclass(frozen=True)
class SecretLeak:
    """A configured secret's value found verbatim inside a candidate bundle file."""

    variable: str
    path: Path


def configured_secrets(environment: Mapping[str, str]) -> tuple[ConfiguredSecret, ...]:
    """Return the secrets configured in ``environment``, in variable-name order."""
    found = []
    for name in sorted(environment):
        if name not in SECRET_VARIABLES and not name.endswith(SECRET_SUFFIXES):
            continue
        value = environment[name]
        if len(value) >= MIN_SECRET_LENGTH:
            found.append(ConfiguredSecret(name, value.encode("utf-8")))
    return tuple(found)


_SECRET_LIKE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(sk-[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(ghp_[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(ghu_[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(AIzaSy[A-Za-z0-9_-]{10,})"
    r"|(Bearer\s+[A-Za-z0-9._-]{20,})"
    r"|([?&](api_key|token|key|access_token)=[^\s&]{8,})",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"


def redact(text: str, live_secret_values: Sequence[str] = ()) -> str:
    """Mask secret-shaped values and every live secret value before text is persisted."""
    result = _SECRET_LIKE_PATTERN.sub(REDACTED, text)
    for secret in live_secret_values:
        if secret:
            result = result.replace(secret, REDACTED)
    return result


def scan_for_secrets(directory: Path, secrets: Sequence[ConfiguredSecret]) -> list[SecretLeak]:
    """Return every (variable, file) pair where a secret's value appears under ``directory``."""
    if not secrets or not directory.is_dir():
        return []
    leaks: list[SecretLeak] = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        data = path.read_bytes()
        leaks.extend(SecretLeak(s.variable, path) for s in secrets if s.value in data)
    return leaks
