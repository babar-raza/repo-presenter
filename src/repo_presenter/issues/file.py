"""The gated write: file one upstream-defect issue, after a fresh dedup search.

Ported (trimmed) from the old repo's ``components/issues/file.py``. The old module gates a create
behind five things: a registry write gate, an owner kill-switch environment variable, a verified
write-scoped token, a per-handoff owner approval record on disk, and a target match -- plus a
remote dedup search and a reconciliation retry when a create's outcome is ambiguous
(``IssueOutcomeUnknownError``).

This pull keeps the two gates this repository's slice can prove today without the approval-record
and registry infrastructure those other gates depend on (not pulled yet, see
``migration/reuse-manifest.yaml``):

1. ``write_authorized`` -- the same owner kill-switch pattern (an environment variable must be set
   to a truthy value; unset/empty/anything else disables every write).
2. The remote dedup search (``repo_presenter.issues.dedup.check_dedup``) runs before every create,
   never skipped -- an already-filed defect is recorded, never re-filed.

The per-handoff approval-record gate and the registry write-gate are NOT ported: this module's
caller is expected to supply its own proof of per-issue owner authorization (the ``authorized``
argument), exactly as this repository's filing script does for the one issue proven end to end in
this pull.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from repo_presenter.github.client import (
    CreatedIssue,
    FetchFn,
    WriteFn,
    create_issue,
    default_fetch,
    default_post,
)
from repo_presenter.issues.dedup import body_with_marker, check_dedup

AUTHORIZATION_VARIABLE = "REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only while the owner's kill switch ``AUTHORIZATION_VARIABLE`` is set to a truthy
    value. Absence, an empty string, or any other value disables writes -- fail closed. A ``True``
    here is necessary and never sufficient: a caller must also pass its own per-issue
    ``authorized=True`` to :func:`file_issue`."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


@dataclass(frozen=True)
class FileResult:
    """The outcome of one :func:`file_issue` call.

    ``filed`` is ``True`` only when a real ``POST /repos/{owner}/{repo}/issues`` call succeeded and
    returned an issue GitHub actually created. ``issue_ref`` is also set when an existing upstream
    issue was recognised as this defect's (``filed`` stays ``False``): the caller records the
    defect as already handled without another write.
    """

    repository: str
    defect_fingerprint: str
    filed: bool
    reason: str
    issue_ref: CreatedIssue | None


def file_issue(
    owner: str,
    name: str,
    *,
    title: str,
    body: str,
    defect_fingerprint: str,
    token: str | None,
    authorized: bool,
    fetch: FetchFn = default_fetch,
    write: WriteFn = default_post,
) -> FileResult:
    """File one issue against ``owner/name``, after a fresh dedup search, if authorized.

    ``authorized`` is the caller's own proof that an owner has approved filing this exact issue
    (the old repo's per-handoff approval record, not ported here -- see module docstring); it is
    checked alongside the kill switch, never inferred from a token's mere presence. No network call
    is made at all when either is false... except the dedup search itself always runs first when
    authorized, so a defect already on the target is recognised before any create is attempted.
    """
    repository = f"{owner}/{name}"
    if not authorized:
        return FileResult(repository, defect_fingerprint, False, "not authorized to file", None)
    if not token:
        return FileResult(
            repository, defect_fingerprint, False, "no write-scoped token available", None
        )
    existing = check_dedup(owner, name, defect_fingerprint, token=token, fetch=fetch)
    if existing is not None:
        return FileResult(
            repository,
            defect_fingerprint,
            False,
            f"already filed upstream as #{existing.number} ({existing.url}) - recorded, not "
            "re-filed",
            existing,
        )
    created = create_issue(
        owner, name, title=title, body=body_with_marker(body, defect_fingerprint), token=token, write=write
    )
    return FileResult(repository, defect_fingerprint, True, "filed", created)
