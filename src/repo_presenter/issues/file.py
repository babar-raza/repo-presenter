"""The gated write: file a ``HANDOFF_PENDING`` handoff as a real GitHub issue.

Ported (ADAPT, the file_handoff/plan_filing half only) from the old repo's current
``components/issues/file.py``, 2026-10-24, per the owner's ruling that this repository adopts the
old repo's real, production-proven issue-automation model
(``project/state.yaml``'s ``DECIDE_NEXT_ISSUE_FILINGS``, ``docs/DECISION_LOG.md``'s 2026-10-24
entry). This REPLACES this module's own earlier, simpler ``file_issue``/``FileResult`` (which took
a plain boolean ``authorized`` argument the caller had to prove some other way) with the shape the
owner specifically asked to keep intact: ``file_handoff`` takes a typed ``Handoff``
(``issues/model.py``) and checks ``verify_approval`` (``issues/approval.py``) itself, via an
injected ``ApprovalStore``, before any dedup lookup or create call.

Every one of these must hold before this module ever calls ``github/client.py``'s
``create_issue``:

1. The registry write gate (``core/registry/write_gate.py``): the target is listed, active and
   permits the ``issue_filing`` effect. The caller holds a ``WritePermit`` and must hand it to
   ``file_handoff``; a ``dry_run`` or ``disabled`` entry can never obtain one.
2. ``write_authorized(environment)`` -- the kill switch. The owner-controlled repository variable
   ``AUTHORIZATION_VARIABLE`` must be set to a truthy value. It can disable every write by being
   unset or changed; it can never, alone, authorize one.
3. A write-scoped token is actually supplied, and its provenance is verified by the caller's own
   ``verify_token`` (``github/token_provenance.py``).
4. A per-handoff owner approval record (``issues/approval.py``: ``ops/issue_approvals/
   <handoff-id>.json``) exists for this exact handoff, names its target repository, matches the
   handoff's current evidence digest, and has not expired. A changed handoff, or a missing or
   expired record, is refused before any network call.
5. The target is the handoff's own recorded repository: a well-formed ``owner/name``, and (when
   the caller states one) the repository the caller is operating on.

Two further guards hold even with every gate open:

- Duplicate filing is refused twice over. A handoff whose ``status`` is not ``HANDOFF_PENDING`` is
  never filed, and -- because a scheduled run starts from a fresh checkout whose artifact may
  still read ``HANDOFF_PENDING`` -- the caller may inject ``existing`` to search the target for an
  issue whose body already carries this defect's fingerprint marker. Such an issue is recorded as
  the handoff's ``issue_ref`` and never re-filed. An inconclusive search refuses the filing rather
  than assuming absence.
- The defect may be rechecked against the repository's current state immediately before the write
  via an injected ``recheck``; a stale or inconclusive finding is never turned into a live issue.

A lost response is reconciled, not repeated. When the create call's outcome is unknown (the
connection dropped, a timeout, a 5xx, a 201 with no body: ``IssueOutcomeUnknownError``), the issue
may exist although no answer arrived. ``file_handoff`` then searches the target for the
fingerprint marker (via ``existing``) before anything else: found, the issue is recorded as this
handoff's (``reconciled``); absent, the create is attempted once more (``max_attempts``); a search
that cannot complete ends the filing as an error without a second POST.

NOT ported this pass, deliberately: ``close_handoff``/``comment_on_filed``/``plan_close``/
``plan_close_gated`` (the old repo's own "file-and-close" workflow step) -- they need a separate
``close_approval.py`` and a ``redetect.py``-shaped ``RedetectionResult`` with more fields than
``file_handoff`` itself needs, neither read yet. Tracked as its own follow-on in
``project/state.yaml``, not guessed at here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from repo_presenter.github.client import (
    IssueOutcomeUnknownError,
    WriteFn,
    create_issue,
    default_post,
)
from repo_presenter.github.errors import RepositoryMetadataError
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.core.registry.write_gate import WritePermit
from repo_presenter.issues.approval import (
    ApprovalStore,
    evidence_digest,
    handoff_id,
    is_valid_repository,
    verify_approval,
)
from repo_presenter.issues.model import Handoff, IssueRef

AUTHORIZATION_VARIABLE = "REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

_NOT_AUTHORIZED_REASON = (
    f"kill switch engaged: {AUTHORIZATION_VARIABLE} is not 1, so every write is disabled "
    "(setting it never authorizes a filing by itself - each handoff also needs its own approval "
    "record)"
)
_NO_APPROVAL_SOURCE_REASON = "no approval record source configured - refusing to file"
_NO_TOKEN_REASON = "no write-scoped token available"

# One attempt plus one retry, and the retry only after a conclusive search found no issue.
MAX_CREATE_ATTEMPTS = 2


class RecheckResult(Protocol):
    """The narrow shape ``file_handoff``'s own ``recheck`` actually reads. Deliberately narrower
    than the old repo's full ``redetect.RedetectionResult`` (not ported here -- see module
    docstring): any object with these two attributes satisfies this protocol structurally, so a
    future, fuller redetection result can be passed here unchanged once that module exists."""

    still_fires: bool | None
    note: str


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only while the owner's kill switch ``AUTHORIZATION_VARIABLE`` is set to a truthy
    value. Absence, an empty string, or any other value disables writes -- fail closed. A
    ``True`` here is necessary and never sufficient: filing also needs the handoff's own approval
    record."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


def fingerprint_marker(defect_fingerprint: str) -> str:
    """The hidden marker every filed body carries, so the target repository itself records which
    defect an issue is for."""
    return f"<!-- repository-presenter-defect: {defect_fingerprint} -->"


def body_with_marker(handoff: Handoff) -> str:
    """The suggested body, with the fingerprint marker appended once when a handoff does not
    already carry it."""
    marker = fingerprint_marker(handoff.defect_fingerprint)
    body = handoff.suggested_issue_body
    if marker in body:
        return body
    return f"{body.rstrip()}\n\n{marker}\n"


def _split(repository: str) -> tuple[str, str]:
    owner, name = repository.split("/", 1)
    return owner, name


@dataclass(frozen=True)
class FileResult:
    """The outcome of one ``file_handoff`` call.

    ``filed`` is ``True`` only when a real ``POST /repos/{owner}/{repo}/issues`` call succeeded
    and returned an issue GitHub actually created. ``issue_ref`` is also set when an existing
    upstream issue was recognised as this defect's (``filed`` stays ``False``): the caller then
    records the handoff as ``FILED`` without another write. ``error`` marks an authorized write
    that GitHub rejected or could not be reached; every other non-filing is a refusal named in
    ``reason``.
    """

    repository: str
    defect_fingerprint: str
    authorized: bool
    filed: bool
    reason: str
    issue_ref: IssueRef | None
    error: bool = False
    # ``True`` when the create call's answer was lost and a search of the target found the issue
    # it had made: ``issue_ref`` is set, ``filed`` stays ``False`` (no POST was confirmed).
    reconciled: bool = False


@dataclass(frozen=True)
class FilingPlan:
    """What filing one handoff would do, decided by read-only checks alone."""

    repository: str
    defect_fingerprint: str
    title: str
    refusal: str | None
    already_filed: IssueRef | None
    handoff_id: str = ""
    evidence_digest: str = ""
    approval_refused: bool = False

    @property
    def ready(self) -> bool:
        return self.refusal is None and self.already_filed is None


def _not_pending_reason(status: str) -> str:
    return (
        f"status is {status!r}, not HANDOFF_PENDING - only a pending handoff may be filed "
        "(this is the duplicate-filing guard: an already-FILED handoff is never re-filed)"
    )


def _target_refusal(handoff: Handoff, expected_repository: str | None) -> str | None:
    if not is_valid_repository(handoff.repository):
        return f"handoff target {handoff.repository!r} is not a valid owner/name"
    if (
        expected_repository is not None
        and handoff.repository.casefold() != expected_repository.casefold()
    ):
        return (
            f"target mismatch: handoff targets {handoff.repository}, but this run operates on "
            f"{expected_repository} - refusing to file outside the recorded target"
        )
    return None


def plan_filing(
    handoff: Handoff,
    *,
    existing: Callable[[], IssueRef | None] | None = None,
    recheck: Callable[[], RecheckResult] | None = None,
    approvals: ApprovalStore | None = None,
    now: Callable[[], datetime] | None = None,
    expected_repository: str | None = None,
    token_check: Callable[[], str | None] | None = None,
) -> FilingPlan:
    """Decide whether ``handoff`` would be filed, using only read calls.

    The target and the owner's per-handoff approval record are checked first, from committed
    files alone, so a handoff nobody approved never causes a network call. ``approvals`` is
    required: a plan with no approval source is a refusal.

    ``existing`` searches the target for an issue already carrying this fingerprint; ``recheck``
    re-runs the handoff's own check at the current revision. Both may raise
    :class:`RepositoryMetadataError`, which is reported as an inconclusive refusal, never assumed
    away. Neither is consulted for a handoff that is not ``HANDOFF_PENDING``.
    """

    def _plan(
        refusal: str | None, already: IssueRef | None = None, *, refused: bool = False
    ) -> FilingPlan:
        return FilingPlan(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            title=handoff.suggested_issue_title,
            refusal=refusal,
            already_filed=already,
            handoff_id=handoff_id(handoff) if is_valid_repository(handoff.repository) else "",
            evidence_digest=evidence_digest(handoff),
            approval_refused=refused,
        )

    if handoff.status != "HANDOFF_PENDING":
        return _plan(_not_pending_reason(handoff.status))

    target_refusal = _target_refusal(handoff, expected_repository)
    if target_refusal is not None:
        return _plan(target_refusal)

    if approvals is None:
        return _plan(_NO_APPROVAL_SOURCE_REASON, refused=True)
    verdict = verify_approval(handoff, approvals, now=now)
    if not verdict.approved:
        return _plan(verdict.reason, refused=True)

    if token_check is not None:  # provenance of the write token, before any upstream lookup
        token_refusal = token_check()
        if token_refusal is not None:
            return _plan(token_refusal)

    if existing is not None:
        try:
            found = existing()
        except RepositoryMetadataError as exc:
            return _plan(
                f"upstream lookup inconclusive ({exc}) - refusing to file without proof that "
                "no issue for this defect exists"
            )
        if found is not None:
            return _plan(None, already=found)

    if recheck is not None:
        result = recheck()
        if result.still_fires is False:
            return _plan(
                "recheck: this handoff's own triggering_check no longer fires at the "
                f"repository's current state ({result.note}) - refusing to file a stale finding"
            )
        if result.still_fires is None:
            return _plan(
                f"recheck: inconclusive ({result.note}) - refusing to file without a fresh "
                "confirmation that the defect still fires"
            )
    return _plan(None)


def file_handoff(
    handoff: Handoff,
    *,
    token: str | None,
    environment: Mapping[str, str],
    create: WriteFn = default_post,
    existing: Callable[[], IssueRef | None] | None = None,
    recheck: Callable[[], RecheckResult] | None = None,
    approvals: ApprovalStore | None = None,
    now: Callable[[], datetime] | None = None,
    expected_repository: str | None = None,
    permit: WritePermit,
    verify_token: Callable[[str], TokenDecision],
    max_attempts: int = MAX_CREATE_ATTEMPTS,
) -> FileResult:
    """File ``handoff`` as a real GitHub issue -- but only past every gate in this module's own
    docstring. Every early return below makes no network call at all.

    ``permit`` is the registry write gate's proof (``core/registry/write_gate.py``): the target is
    listed, active and permits ``issue_filing``. ``verify_token`` proves the write token's
    provenance (``github/token_provenance.py``); a hand-set or wrongly-scoped token is refused
    before any lookup or POST, at the caller's own discretion (this function only calls what is
    given it)."""
    if permit.effect != "issue_filing" or permit.entry.repository != handoff.repository:
        raise ValueError("the write permit does not clear this effect for this repository")

    def _refuse(authorized: bool, reason: str, *, error: bool = False) -> FileResult:
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=authorized,
            filed=False,
            reason=reason,
            issue_ref=None,
            error=error,
        )

    if not write_authorized(environment):
        return _refuse(False, _NOT_AUTHORIZED_REASON)

    if not token:
        return _refuse(True, _NO_TOKEN_REASON)

    def _token_check() -> str | None:
        decision = verify_token(token)
        return None if decision.ok else f"write token refused ({decision.code}): {decision.reason}"

    plan = plan_filing(
        handoff,
        existing=existing,
        recheck=recheck,
        approvals=approvals,
        now=now,
        expected_repository=expected_repository,
        token_check=_token_check,
    )
    if plan.already_filed is not None:
        found = plan.already_filed
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=True,
            filed=False,
            reason=(
                f"already filed upstream as #{found.number} ({found.url}) - recorded, not re-filed"
            ),
            issue_ref=found,
        )
    if plan.refusal is not None:
        return _refuse(True, plan.refusal)

    owner, name = _split(handoff.repository)
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            created = create_issue(
                owner,
                name,
                title=handoff.suggested_issue_title,
                body=body_with_marker(handoff),
                token=token,
                write=create,
            )
        except IssueOutcomeUnknownError as exc:
            # The issue may exist. Look before anything else is written (reconcile an uncertain
            # remote effect before retrying).
            if existing is None:
                return _refuse(
                    True,
                    f"{exc} - no upstream search is configured to reconcile it, so it is not "
                    "retried",
                    error=True,
                )
            try:
                landed = existing()
            except RepositoryMetadataError as search_exc:
                return _refuse(
                    True,
                    f"{exc} - the outcome cannot be reconciled because the upstream search "
                    f"failed ({search_exc}); not retried",
                    error=True,
                )
            if landed is not None:
                return FileResult(
                    repository=handoff.repository,
                    defect_fingerprint=handoff.defect_fingerprint,
                    authorized=True,
                    filed=False,
                    reason=(
                        f"the create response was lost ({exc}); reconciled: the issue exists "
                        f"upstream as #{landed.number} ({landed.url}) - recorded, not re-filed"
                    ),
                    issue_ref=landed,
                    reconciled=True,
                )
            if attempt >= max_attempts:
                return _refuse(
                    True,
                    f"{exc} - after {attempt} attempt(s) no issue for this defect exists upstream",
                    error=True,
                )
            continue
        except RepositoryMetadataError as exc:
            return _refuse(True, str(exc), error=True)
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=True,
            filed=True,
            reason="filed",
            issue_ref=IssueRef(number=created.number, url=created.url),
        )
    raise AssertionError("unreachable: the loop returns on every path")  # pragma: no cover
