"""Close / re-detection: transition a ``FILED`` handoff to ``RESOLVED_UPSTREAM`` only when
independent re-detection confirms the defect no longer reproduces -- never on say-so alone, and
never on the mere ABSENCE of contrary evidence.

2026-11-04 (TC-010, corrected 2026-11-04 by the P0 follow-up directive section 7). ``file.py``'s
own comment states this step was "NOT ported this pass, deliberately" from the legacy
repository -- confirmed absent. This is new code on the same ``Handoff`` model; it reuses
``model.write_handoff`` for persistence rather than inventing a second writer.

The directive's own finding: the first version of this module treated a triggering fact that had
disappeared entirely (extraction failure, a renamed check id, incomplete toolchain evidence) as
equivalent to a verified fix, because ``redetect()`` returned a bare ``bool`` with only two
states. Missing evidence is not proof a defect was fixed -- it is exactly as unsafe to close on
as no evidence at all. ``redetect()`` now returns one of three distinct outcomes, and only
``VERIFIED_RESOLVED`` -- the fact still exists and is no longer ``CONTRADICTED`` -- may complete
a ``reason="completed"`` close; both ``STILL_REPRODUCES`` and the new ``NOT_VERIFIABLE`` refuse
it identically.

Remote closure (stage 11): ``close_handoff(..., remote=RemoteClose(...))`` additionally comments
on and closes the upstream issue, behind the same gates as filing. See ``RemoteClose``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from repo_presenter.core.facts import Fact
from repo_presenter.core.registry.write_gate import WritePermit
from repo_presenter.github.client import (
    FetchFn,
    WriteFn,
    close_issue,
    comment_issue,
    default_fetch,
    default_patch,
    default_post,
    issue_has_comment_with_marker,
)
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues.approval import (
    BOT_MARKERS,
    CLOCK_SKEW,
    MAX_APPROVAL_LIFETIME,
    ApprovalError,
    ApprovalProvenanceError,
    ApprovalStore,
    handoff_id,
    is_valid_repository,
    parse_timestamp,
    verify_approval,
)
from repo_presenter.issues.file import write_authorized
from repo_presenter.issues.model import CloseReason, Handoff, write_handoff

RedetectionOutcome = Literal["VERIFIED_RESOLVED", "STILL_REPRODUCES", "NOT_VERIFIABLE"]


class CloseRefusal(ValueError):
    """A close was requested but the evidence does not support it."""


def redetect(handoff: Handoff, current_facts_by_id: dict[str, Fact]) -> RedetectionOutcome:
    """Re-run the exact check that originally triggered this handoff against a fresh facts
    document and classify the result:

    - ``VERIFIED_RESOLVED``: the fact still exists and is no longer ``CONTRADICTED`` -- a real,
      positive re-detection that the defect is gone.
    - ``STILL_REPRODUCES``: the fact still exists and is still ``CONTRADICTED`` -- not fixed.
    - ``NOT_VERIFIABLE``: the fact is absent from the current facts document entirely (removed
      check, renamed id, an extraction or toolchain gap). Absence is not evidence of a fix, so
      this is its own distinct, unresolved outcome -- never folded into ``VERIFIED_RESOLVED``.

    Looked up by ``handoff.triggering_check.id`` (the real, readable fact id discovery.py
    preserved there) -- never by ``defect_fingerprint``, which is a one-way sha256 digest
    (approval.py's own handoff_id() contract) and cannot be used to look anything back up."""
    current = current_facts_by_id.get(handoff.triggering_check.id)
    if current is None:
        return "NOT_VERIFIABLE"
    if current.polarity == "CONTRADICTED":
        return "STILL_REPRODUCES"
    return "VERIFIED_RESOLVED"


class CloseApprovalStore(Protocol):
    """Where 'not planned' close approvals come from; same contract as ``ApprovalStore.read``.
    The identifier is ``<handoff_id>.close``. No production store is wired yet."""

    def read(self, identifier: str) -> str | None: ...


_CLOSE_APPROVAL_FIELDS = frozenset(
    {
        "handoff_id",
        "repository",
        "close_reason",
        "reason_text",
        "approver",
        "approved_at",
        "expires_at",
    }
)


@dataclass(frozen=True)
class RemoteClose:
    """Everything a REMOTE close needs beyond the local re-verification: the same gates as
    filing (kill switch, write token + provenance, registry permit for ``issue_close``, the
    handoff's owner approval, target repository), plus ``close_approvals`` for 'not planned'.
    ``comment``/``patch`` are the injected transports (the defaults are the guarded real ones)."""

    token: str | None
    environment: Mapping[str, str]
    permit: WritePermit
    approvals: ApprovalStore
    verify_token: Callable[[str], TokenDecision]
    close_approvals: CloseApprovalStore | None = None
    now: Callable[[], datetime] | None = None
    expected_repository: str | None = None
    comment: WriteFn = default_post
    patch: WriteFn = default_patch
    #: The read transport for the comment-idempotency check (a GET; never a write).
    fetch: FetchFn = default_fetch


@dataclass(frozen=True)
class CloseOutcome:
    handoff: Handoff
    commented: bool
    closed_remote: bool
    #: True when the closing comment was already on the issue (a retry after a partial failure), so
    #: none was posted again; ``commented`` is then False for this run.
    comment_already_present: bool = False


def _read_close_approval(handoff: Handoff, remote: RemoteClose) -> tuple[str, str]:
    """``(reason_text, approver)`` from a valid 'not planned' close approval, or raise
    :class:`CloseRefusal`."""

    def deny(why: str) -> CloseRefusal:
        return CloseRefusal(f"remote close refused: close approval refused: {why}")

    if remote.close_approvals is None:
        raise deny("no close approval source configured ('not planned' needs an explicit one)")
    ident = handoff_id(handoff) + ".close"
    try:
        text = remote.close_approvals.read(ident)
    except ApprovalProvenanceError as exc:
        raise deny(f"provenance unverifiable ({exc})") from exc
    if text is None:
        raise deny(f"no close approval record for {ident}")
    try:
        loaded = json.loads(text)
        if not isinstance(loaded, dict) or set(loaded) != _CLOSE_APPROVAL_FIELDS:
            raise ApprovalError("must be an object with exactly the documented fields")
        for field in ("handoff_id", "repository", "close_reason", "reason_text", "approver"):
            if not isinstance(loaded[field], str) or not loaded[field].strip():
                raise ApprovalError(f"{field} must be a non-empty string")
        approved_at = parse_timestamp(loaded["approved_at"], "approved_at")
        expires_at = parse_timestamp(loaded["expires_at"], "expires_at")
    except (json.JSONDecodeError, ApprovalError) as exc:
        raise deny(f"malformed ({exc})") from exc
    if loaded["handoff_id"] != handoff_id(handoff):
        raise deny("names a different handoff")
    if loaded["repository"].casefold() != handoff.repository.casefold():
        raise deny("names a different repository")
    if loaded["close_reason"] != "not planned":
        raise deny(f"close_reason is {loaded['close_reason']!r}, not 'not planned'")
    approver = loaded["approver"].strip()
    if any(m in approver.lower() for m in BOT_MARKERS):
        raise deny("approver must be a person, not a bot or workflow identity")
    if expires_at <= approved_at or expires_at - approved_at > MAX_APPROVAL_LIFETIME:
        raise deny("invalid validity window")
    moment = (remote.now or (lambda: datetime.now(UTC)))()
    if approved_at > moment + CLOCK_SKEW:
        raise deny("dated in the future")
    if moment >= expires_at:
        raise deny(f"expired at {expires_at.isoformat()}")
    return loaded["reason_text"].strip(), approver


def _remote_gates(
    handoff: Handoff, reason: CloseReason, remote: RemoteClose
) -> tuple[str | None, str | None]:
    """Run every gate before any write. Returns ``(reason_text, approver)`` for 'not planned'
    (``(None, None)`` for 'completed'); raises :class:`CloseRefusal` on the first failed gate."""
    if handoff.issue_ref is None:
        raise CloseRefusal("remote close refused: the handoff has no issue_ref to close")
    if (
        remote.permit.effect != "issue_close"
        or remote.permit.entry.repository != handoff.repository
    ):
        raise CloseRefusal(
            "remote close refused: the write permit does not clear issue_close for this repository"
        )
    if not write_authorized(remote.environment):
        raise CloseRefusal("remote close refused: kill switch engaged (every write is disabled)")
    if not remote.token:
        raise CloseRefusal("remote close refused: no write-scoped token available")
    decision = remote.verify_token(remote.token)
    if not decision.ok:
        raise CloseRefusal(f"remote close refused: write token refused ({decision.reason})")
    if not is_valid_repository(handoff.repository):
        raise CloseRefusal(f"remote close refused: {handoff.repository!r} is not owner/name")
    if (
        remote.expected_repository is not None
        and handoff.repository.casefold() != remote.expected_repository.casefold()
    ):
        raise CloseRefusal(
            f"remote close refused: target mismatch ({handoff.repository} vs "
            f"{remote.expected_repository})"
        )
    verdict = verify_approval(handoff, remote.approvals, now=remote.now)
    if not verdict.approved:
        raise CloseRefusal(f"remote close refused: {verdict.reason}")
    if reason == "not planned":
        return _read_close_approval(handoff, remote)
    return None, None


def _bullets(entries: tuple) -> list[str]:  # type: ignore[type-arg]
    return [f"- {e.path}" + (f": {e.detail}" if e.detail else "") for e in entries]


def closing_marker(handoff: Handoff, reason: CloseReason) -> str:
    """The hidden marker that makes the closing comment idempotent across retries: one per
    (defect fingerprint, close reason), invisible in the rendered issue."""
    return f"<!-- repo-presenter:closing-comment:{handoff.defect_fingerprint}:{reason} -->"


def _closing_comment(
    handoff: Handoff,
    reason: CloseReason,
    current: Fact | None,
    reason_text: str | None,
    approver: str | None,
) -> str:
    if reason == "completed":
        lines = [
            (
                "Resolved: independent re-detection reports VERIFIED_RESOLVED for "
                f"`{handoff.triggering_check.id}` (it no longer reproduces)."
            ),
            "",
            f"Original claim: {handoff.claim}",
        ]
        if current is not None:
            lines += ["", f"Current state: {current.value}", *_bullets(current.evidence)]
        lines += ["", "Original evidence:", *_bullets(handoff.evidence)]
    else:
        lines = [
            f"Closing as not planned (approved by {approver}): {reason_text}",
            "",
            f"Original claim: {handoff.claim}",
        ]
    return "\n".join(lines) + "\n\n" + closing_marker(handoff, reason) + "\n"


def close_handoff_with_outcome(
    handoff: Handoff,
    *,
    current_facts_by_id: dict[str, Fact],
    reason: CloseReason,
    path: Path,
    remote: RemoteClose | None = None,
) -> CloseOutcome:
    """``close_handoff`` that also reports whether the upstream issue was commented on/closed."""
    if handoff.status != "FILED":
        raise CloseRefusal(f"cannot close a handoff in status {handoff.status!r}; only FILED")
    if reason == "completed":
        outcome = redetect(handoff, current_facts_by_id)
        if outcome == "STILL_REPRODUCES":
            raise CloseRefusal(
                "reason='completed' requires re-detection to confirm the defect no longer "
                "reproduces, but the triggering fact is still CONTRADICTED"
            )
        if outcome == "NOT_VERIFIABLE":
            raise CloseRefusal(
                "reason='completed' requires re-detection to report VERIFIED_RESOLVED, but the "
                "triggering check "
                f"{handoff.triggering_check.id!r} is absent from the current facts document "
                "(extraction failure, a renamed check, or incomplete toolchain evidence); "
                "absence of the fact is not proof the defect was fixed"
            )
    commented = closed_remote = already_present = False
    if remote is not None:
        # Every gate first (nothing is written, locally or upstream, on a refusal); then the
        # evidence comment; then the close. The local file is written last, so a failed upstream
        # call leaves the handoff FILED to be retried.
        reason_text, approver = _remote_gates(handoff, reason, remote)
        assert handoff.issue_ref is not None
        owner, name = handoff.repository.split("/", 1)
        number = handoff.issue_ref.number
        current = current_facts_by_id.get(handoff.triggering_check.id)
        # Idempotent across a partial failure (comment posted, close failed): read the issue's
        # comments first and post only if this closing comment is not already there. An
        # incomplete read raises, leaving the handoff FILED to retry -- never a guessed "absent".
        already_present = issue_has_comment_with_marker(
            owner, name, number, closing_marker(handoff, reason),
            token=remote.token, fetch=remote.fetch,
        )
        if not already_present:
            comment_issue(
                owner,
                name,
                number,
                body=_closing_comment(handoff, reason, current, reason_text, approver),
                token=remote.token or "",
                write=remote.comment,
            )
            commented = True
        close_issue(owner, name, number, reason=reason, token=remote.token or "", write=remote.patch)
        closed_remote = True
    resolved = replace(handoff, status="RESOLVED_UPSTREAM", close_reason=reason)
    write_handoff(resolved, path)
    return CloseOutcome(resolved, commented, closed_remote, already_present)


def close_handoff(
    handoff: Handoff,
    *,
    current_facts_by_id: dict[str, Fact],
    reason: CloseReason,
    path: Path,
    remote: RemoteClose | None = None,
) -> Handoff:
    """Transition ``FILED`` -> ``RESOLVED_UPSTREAM``. Only a ``FILED`` handoff may be closed
    (nothing was ever opened upstream for ``HANDOFF_PENDING``/``HANDOFF_ACKNOWLEDGED`` to
    close). ``reason="completed"`` additionally requires re-detection to report
    ``VERIFIED_RESOLVED``; ``reason="not planned"`` (a check-version change, a false positive, or
    an owner-authorized withdrawal) does not re-detect, since there is nothing left to re-detect
    against by definition -- locally that is all it takes (pinned in test_close_remote.py).

    With ``remote`` supplied the upstream issue is also commented on (evidence of resolution, or
    the approved reason) and closed, but only after the local checks above AND every gate in
    :class:`RemoteClose`; a 'not planned' remote close additionally needs a close approval
    record with a recorded reason. Any refusal raises :class:`CloseRefusal` having written
    nothing anywhere. Without ``remote`` no network call is ever made."""
    return close_handoff_with_outcome(
        handoff,
        current_facts_by_id=current_facts_by_id,
        reason=reason,
        path=path,
        remote=remote,
    ).handoff
