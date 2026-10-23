"""The typed reasons a write effect refuses, in one place.

Trimmed from the old repo's ``core/authorization/refusals.py``: only the codes this repository's
issue-filing slice and registry write gate can actually raise are kept (the candidate-bundle and
correction-gate codes belong to components not pulled yet).
"""

from __future__ import annotations

from enum import StrEnum


class Refusal(StrEnum):
    # Write-token provenance (repo_presenter.github.token_provenance).
    TOKEN_NOT_INSTALLATION = "token_not_installation"
    TOKEN_WRONG_SCOPE = "token_wrong_scope"
    TOKEN_UNVERIFIABLE = "token_unverifiable"
    # The owner kill switch and credential presence (repo_presenter.issues.file).
    WRITE_NOT_ENABLED = "write_not_enabled"
    NO_WRITE_TOKEN = "no_write_token"
    # Duplicate filing (repo_presenter.issues.dedup / repo_presenter.issues.file).
    ALREADY_FILED = "already_filed"
    # The registry write gate (repo_presenter.core.registry.write_gate), ported 2026-10-23.
    REGISTRY_NOT_LISTED = "registry_not_listed"
    REGISTRY_DISABLED = "registry_disabled"
    REGISTRY_DRY_RUN = "registry_dry_run"
    REGISTRY_INACTIVE = "registry_inactive"


class WriteRefusedError(Exception):
    """A write was refused before any remote effect; ``code`` is the typed reason."""

    exit_code = 3

    def __init__(self, code: Refusal, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
