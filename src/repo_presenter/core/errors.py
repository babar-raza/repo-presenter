"""Typed failures of the presenter, mapped to CLI exit codes.

Exit codes: 0 success, 1 validation or policy failure, 2 usage or configuration error,
3 safety refusal (allow-list, git safety, secret canary). A class is added here only together
with the stage that raises it.

Ported (REUSE, near-verbatim) from the old repository-presenter project's ``core/errors.py``
per migration/reuse-manifest.yaml, trimmed to the classes the ported extraction layer actually
raises (``ConfigError``); the remaining old-repo classes (state/CAS/gateway/job/git-safety
errors) belong to stages not yet pulled into this repository and are not reproduced here.
"""

from __future__ import annotations


class PresenterError(Exception):
    """Base of every typed failure; ``exit_code`` is what the CLI returns for it."""

    exit_code = 1


class ConfigError(PresenterError):
    """A configuration or data file is missing or malformed; the run fails closed."""

    exit_code = 2


class GatewayError(PresenterError):
    """The LLM gateway refused, failed, or answered unusably; no job runs on a guess.

    Ported (ADD, 2026-10-21) alongside the Lane R composition/reconciliation/core.llm pull
    (migration/reuse-manifest.yaml "readme/composition/" entry): needed by
    ``core/llm/jobs.py``'s ``run_job`` boundary.
    """


class JobError(PresenterError):
    """A job's output was rejected after its one bounded re-ask, or the provider failed for good."""


class ProviderCallBudgetError(GatewayError):
    """This process reached its provider-call ceiling (``core/llm/ledger.py``'s
    ``PROVIDER_CALL_BUDGET``); the refused call is never sent, so the run stops with no further
    spend and fails closed."""


class NotAllowlistedError(PresenterError):
    """A repository outside the registry allow-list; refused before any network or git operation.

    Ported (ADD, 2026-10-21) alongside ``core/registry/loader.py``.
    """

    exit_code = 3


class GitSafetyError(PresenterError):
    """A clone could not be made, pinned, or proven push-disabled; analysis never starts.

    Ported (ADD, 2026-10-23) alongside ``core/git_safety/clone.py``. Drafted once before, on
    the day ``core/git_safety/git.py`` was pulled, then reverted because git.py itself never
    raises it -- only clone.py does. Re-added now that clone.py is actually being pulled.
    """

    exit_code = 3


class RepositorySnapshotError(GitSafetyError):
    """The immutable repository view is absent or drifted while a transaction used it.

    Ported (ADD, 2026-10-25) alongside ``core/snapshot/capture.py``, step 2 of
    ``plans/PLAN_bundle_integrity_and_noop_proof.md``.
    """
