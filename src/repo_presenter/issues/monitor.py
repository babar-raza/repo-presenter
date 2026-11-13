"""The issue-management pilot's periodic maintenance cycle (owner ruling R39, 2026-11-13).

For one pilot repository (``data/issue_pilot.json``; anything else is refused before any read):

1. **Record / import (dedup).** Read the repository's issues; every issue authored by the
   presenter App (``repository-presenter[bot]``) whose body carries a defect fingerprint marker
   (``issues/dedup.parse_fingerprint``, this project's or the old project's prefix) is recorded
   as a typed :class:`~repo_presenter.issues.model.Handoff` (``FILED``, or ``RESOLVED_UPSTREAM``
   when closed), keyed by ``(repository, fingerprint)`` exactly like filing's dedup ledger. Two
   issues with one fingerprint are one record; the lowest number is canonical, the others are
   listed as duplicates and never touched. An issue whose fingerprint has a committed
   reproduction (``data/issue_reproductions/``, matching issue number) is *verifiable*; any other
   is recorded "unverifiable: monitored, never auto-closed".
2. **Re-verify.** The sandbox job's raw observations (``issues/reproduce.py``) are validated as
   hostile input and classified by the committed predicates into a ``Fact``;
   ``issues/close.redetect`` turns it into VERIFIED_RESOLVED / STILL_REPRODUCES / NOT_VERIFIABLE.
3. **Decide** (:func:`decide`, pure): open + resolved -> CLOSE (completed, with the revision and
   output digest as evidence); open + still reproduces -> a dated "still reproduces at <rev>"
   comment only when one is due (no statement for ``recheck_comment_interval_days`` and the
   revision moved, or none for ``unchanged_revision_comment_interval_days``); closed + reproduces
   again -> REOPEN, once per revision, never an issue a maintainer closed as not planned or
   re-closed after a reopen; NOT_VERIFIABLE and unverifiable records -> nothing.
4. **Act** through the existing guarded primitives (``github/client.py``: the pilot grant allows
   only comments and state changes on existing issues), each guarded by a hidden marker read back
   from the issue first, so a replayed cycle never posts twice. Live writes need ALL of: pilot
   ``mode: live``; at least one recorded dry-run cycle (the first hosted cycle is always a dry
   run); the owner's kill switch (``issues/file.write_authorized``); an App installation token
   whose reach is exactly this repository (``token_provenance.verify_installation_token``).
   Otherwise the cycle is a dry run: it reports what it WOULD do and writes nothing upstream.
5. **Record** the cycle durably on the state remote
   (``refs/repository-presenter-state/issues/<owner>__<name>``, ``GitJsonRef`` compare-and-swap):
   the records, the occurrence ledger (``issues/track.record_event``) and one audit row per
   cycle with every observation, decision and action.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol

from repo_presenter.core.errors import StateBackendError
from repo_presenter.core.facts import Fact
from repo_presenter.github.client import (
    FetchFn,
    WriteFn,
    close_issue,
    comment_issue,
    default_fetch,
    default_patch,
    default_post,
    get_issue,
    list_issue_comments,
    list_issues,
    reopen_issue,
)
from repo_presenter.github.errors import RepositoryMetadataError
from repo_presenter.github.token_provenance import (
    APP_INSTALLATION_TOKEN_ENV_VAR,
    TokenDecision,
    verify_installation_token,
)
from repo_presenter.issues.close import RedetectionOutcome, closing_marker, redetect
from repo_presenter.issues.dedup import parse_fingerprint
from repo_presenter.issues.file import write_authorized
from repo_presenter.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
    handoff_from_dict,
    handoff_to_dict,
)
from repo_presenter.issues.pilot import (
    PilotEntry,
    Reproduction,
    ReproductionSet,
    load_reproductions,
    require_pilot,
)
from repo_presenter.issues.reproduce import (
    CheckObservation,
    Checks,
    ChecksError,
    classify,
    load_checks,
)
from repo_presenter.issues.track import entry_from_dict, entry_to_dict, record_event

STATE_SCHEMA_VERSION = 1
STATE_REF_PREFIX = "refs/repository-presenter-state/issues/"
CHECK_VERSION = "r39-pilot-1"
MAX_CYCLES_KEPT = 400
MAX_COMMENT_OUTPUT_CHARS = 2_000
Action = Literal["CLOSE", "COMMENT_STILL_REPRODUCES", "REOPEN", "NONE"]
_REVISION_IN_BODY = re.compile(r"Revision `([0-9a-f]{40})`")


def state_ref(repository: str) -> str:
    owner, name = repository.split("/", 1)
    return f"{STATE_REF_PREFIX}{owner}__{name}"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


# --------------------------------------------------------------------------- upstream issues


@dataclass(frozen=True)
class Issue:
    number: int
    url: str
    title: str
    body: str
    author: str
    state: str
    state_reason: str | None
    created_at: str
    closed_by: str | None = None


def issue_from_api(item: Mapping[str, Any], closed_by: str | None = None) -> Issue | None:
    number, url = item.get("number"), item.get("html_url")
    if not isinstance(number, int) or not isinstance(url, str):
        return None
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    reason = item.get("state_reason")
    return Issue(
        number=number,
        url=url,
        title=str(item.get("title") or ""),
        body=str(item.get("body") or ""),
        author=str(user.get("login") or ""),
        state="closed" if item.get("state") == "closed" else "open",
        state_reason=reason if isinstance(reason, str) else None,
        created_at=str(item.get("created_at") or ""),
        closed_by=closed_by,
    )


# --------------------------------------------------------------------------- recording / dedup


def _status_fields(issue: Issue) -> dict[str, Any]:
    if issue.state != "closed":
        return {"status": "FILED", "close_reason": None}
    reason = "not planned" if issue.state_reason == "not_planned" else "completed"
    return {"status": "RESOLVED_UPSTREAM", "close_reason": reason}


def handoff_for_issue(repository: str, fingerprint: str, issue: Issue, spec: Reproduction | None) -> Handoff:
    """The typed record of one imported issue. ``spec`` None -> unverifiable."""
    if spec is not None:
        revision = spec.recorded_revision
        check = TriggeringCheck(id=spec.check_id, version=CHECK_VERSION, causal_stage="EXTRACTING")
        evidence = tuple(EvidenceEntry(path=p, detail=d) for p, d in spec.evidence)
        defect_class: str | None = spec.defect_class
    else:
        found = _REVISION_IN_BODY.search(issue.body)
        revision = found.group(1) if found else "unknown"
        check = TriggeringCheck(
            id=f"unverifiable:issue-{issue.number}", version=CHECK_VERSION, causal_stage="EXTRACTING"
        )
        evidence = (
            EvidenceEntry(
                path=issue.url,
                detail="no reproducible check is recorded for this issue: monitored, never auto-closed",
            ),
        )
        defect_class = None
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision=revision,
        defect_fingerprint=fingerprint,
        triggering_check=check,
        evidence=evidence,
        claim=issue.title or f"issue #{issue.number}",
        suggested_issue_title=issue.title or f"issue #{issue.number}",
        suggested_issue_body=issue.body,
        issue_ref=IssueRef(number=issue.number, url=issue.url),
        defect_class=defect_class,
        **_status_fields(issue),
    )


@dataclass(frozen=True)
class RecordView:
    fingerprint: str
    issue: Issue
    handoff: Handoff
    verifiable: bool
    reason: str
    duplicates: tuple[int, ...] = ()
    spec: Reproduction | None = None


def record_issues(
    repository: str,
    issues: list[Issue],
    reproductions: ReproductionSet,
    *,
    bot_login: str,
    known: Mapping[str, Any] | None = None,
) -> tuple[list[RecordView], list[str]]:
    """Pure recording + dedup. Returns the canonical records and report notes (ignored issues,
    reproductions with no upstream issue)."""
    notes: list[str] = []
    groups: dict[str, list[Issue]] = {}
    for issue in sorted(issues, key=lambda i: i.number):
        if issue.author != bot_login:
            continue
        fingerprint = parse_fingerprint(issue.body)
        if fingerprint is None:
            notes.append(f"#{issue.number}: authored by {bot_login} but carries no single defect marker; not managed")
            continue
        groups.setdefault(fingerprint, []).append(issue)
    specs = reproductions.by_fingerprint()
    views: list[RecordView] = []
    for fingerprint, group in groups.items():
        previous = (known or {}).get(fingerprint) or {}
        canonical = next((i for i in group if i.number == previous.get("issue_number")), group[0])
        duplicates = tuple(i.number for i in group if i.number != canonical.number)
        spec = specs.get(fingerprint)
        if spec is not None and spec.issue_number != canonical.number:
            reason = (
                f"the recorded reproduction names issue #{spec.issue_number}, not #{canonical.number}: "
                "unverifiable, monitored, never auto-closed"
            )
            spec = None
        elif spec is None:
            reason = "no reproducible check recorded: unverifiable, monitored, never auto-closed"
        else:
            reason = f"reproduction {spec.check_id}"
        views.append(
            RecordView(
                fingerprint=fingerprint,
                issue=canonical,
                handoff=handoff_for_issue(repository, fingerprint, canonical, spec),
                verifiable=spec is not None,
                reason=reason,
                duplicates=duplicates,
                spec=spec,
            )
        )
    for fingerprint, spec in specs.items():
        if fingerprint not in groups:
            notes.append(f"reproduction {spec.check_id} (#{spec.issue_number}) has no presenter issue upstream")
    return views, notes


# --------------------------------------------------------------------------- decisions


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str


def decide(
    *,
    verifiable: bool,
    outcome: RedetectionOutcome | None,
    issue_state: str,
    state_reason: str | None,
    closed_by_bot: bool,
    reopened_revisions: tuple[str, ...],
    revision: str | None,
    last_statement_at: datetime | None,
    last_statement_revision: str | None,
    now: datetime,
    interval_days: int,
    unchanged_interval_days: int,
) -> Decision:
    """The one maintenance decision for one record. Pure."""
    if not verifiable:
        return Decision("NONE", "unverifiable: monitored, never auto-closed")
    if outcome is None or outcome == "NOT_VERIFIABLE" or revision is None:
        return Decision("NONE", "re-check NOT_VERIFIABLE at this revision: no change made")
    if issue_state == "open":
        if outcome == "VERIFIED_RESOLVED":
            return Decision("CLOSE", f"verified resolved at {revision[:12]}")
        since = now - last_statement_at if last_statement_at else None
        moved = last_statement_revision != revision
        if since is None:
            return Decision("COMMENT_STILL_REPRODUCES", "still reproduces; no dated statement recorded yet")
        if moved and since >= timedelta(days=interval_days):
            return Decision(
                "COMMENT_STILL_REPRODUCES",
                f"still reproduces at a new revision {revision[:12]} ({since.days} days since the last statement)",
            )
        if since >= timedelta(days=unchanged_interval_days):
            return Decision(
                "COMMENT_STILL_REPRODUCES",
                f"still reproduces; {since.days} days since the last statement",
            )
        due = last_statement_at + timedelta(days=interval_days if moved else unchanged_interval_days)
        return Decision(
            "NONE",
            f"still reproduces at {revision[:12]}; last statement {last_statement_at.date()} "
            f"at {str(last_statement_revision)[:12]}; next dated re-check due {due.date()}",
        )
    # closed
    if outcome == "VERIFIED_RESOLVED":
        return Decision("NONE", "closed and still resolved")
    if state_reason == "not_planned":
        return Decision("NONE", "reproduces, but a maintainer closed it as not planned: left closed, monitored")
    if reopened_revisions and not closed_by_bot:
        return Decision("NONE", "reproduces, but a maintainer re-closed it after a reopen: left closed, monitored")
    if revision in reopened_revisions:
        return Decision("NONE", f"already reopened once at {revision[:12]}")
    return Decision("REOPEN", f"closed as fixed, but reproduces again at {revision[:12]}")


# --------------------------------------------------------------------------- comment bodies


def recheck_prefix(fingerprint: str) -> str:
    return f"<!-- repo-presenter:recheck:{fingerprint}:"


def recheck_marker(fingerprint: str, revision: str, day: str) -> str:
    return f"{recheck_prefix(fingerprint)}{revision}:{day} -->"


def reopen_marker(fingerprint: str, revision: str) -> str:
    return f"<!-- repo-presenter:reopen:{fingerprint}:{revision} -->"


def _observed(observation: CheckObservation | None, toolchain: Mapping[str, Any]) -> list[str]:
    if observation is None:
        return []
    text = observation.output.strip()
    if len(text) > MAX_COMMENT_OUTPUT_CHARS:
        text = "…\n" + text[-MAX_COMMENT_OUTPUT_CHARS:]
    node = toolchain.get("node") or "unknown"
    return [
        f"The reproduction in this issue was run again (`npm install`, `npm run build`, Node.js {node}) and printed:",
        "",
        "```",
        text.replace("```", "'''"),
        "```",
        "",
        f"Output digest: `{observation.output_digest}`.",
    ]


def comment_body(
    action: Action, view: RecordView, revision: str, day: str,
    observation: CheckObservation | None, toolchain: Mapping[str, Any],
) -> str:
    if action == "CLOSE":
        head = (
            f"Re-checked on {day} at revision `{revision}`: this defect no longer reproduces "
            "(the output matches the expected result), so this issue is closed as completed."
        )
        marker = closing_marker(view.handoff, "completed")
    elif action == "REOPEN":
        head = f"Re-checked on {day} at revision `{revision}`: this defect reproduces again, so this issue is reopened."
        marker = reopen_marker(view.fingerprint, revision)
    else:
        head = f"Re-checked on {day} at revision `{revision}`: this defect still reproduces."
        marker = recheck_marker(view.fingerprint, revision, day)
    return "\n".join([head, "", *_observed(observation, toolchain), "", marker]) + "\n"


# --------------------------------------------------------------------------- the cycle


@dataclass(frozen=True)
class Planned:
    view: RecordView
    outcome: RedetectionOutcome | None
    fact: Fact | None
    observation: CheckObservation | None
    decision: Decision
    last_statement_at: str | None
    last_statement_revision: str | None


@dataclass
class ActionResult:
    issue_number: int
    action: Action
    performed: bool = False
    note: str = ""
    error: str | None = None
    marker: str | None = None


@dataclass
class Context:
    repository: str
    entry: PilotEntry
    reproductions: ReproductionSet
    now: datetime
    revision: str | None
    checks: Checks | None
    checks_note: str | None
    fetch: FetchFn = default_fetch
    post: WriteFn = default_post
    patch: WriteFn = default_patch
    read_token: str | None = None
    write_token: str | None = None
    notes: list[str] = field(default_factory=list)


def _latest_statement(
    record: Mapping[str, Any], view: RecordView, comments: list[dict[str, Any]], bot_login: str
) -> tuple[datetime | None, str | None]:
    """The most recent dated statement on the issue: our state's, a re-check comment read back
    from upstream (survives a lost state write), or the issue's own filing (its recorded revision)."""
    candidates: list[tuple[datetime, str | None]] = []
    stored = record.get("last_statement") if isinstance(record, Mapping) else None
    if isinstance(stored, Mapping) and _parse(stored.get("at")):
        candidates.append((_parse(stored.get("at")), stored.get("revision")))  # type: ignore[arg-type]
    prefix = recheck_prefix(view.fingerprint)
    for comment in comments:
        body = comment.get("body")
        user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
        if not isinstance(body, str) or prefix not in body or user.get("login") != bot_login:
            continue
        at = _parse(comment.get("created_at"))
        found = re.search(re.escape(prefix) + r"([0-9a-f]{40}):", body)
        if at:
            candidates.append((at, found.group(1) if found else None))
    filed = _parse(view.issue.created_at)
    if filed:
        candidates.append((filed, view.handoff.source_revision))
    if not candidates:
        return None, None
    return max(candidates, key=lambda c: c[0])


def plan_cycle(
    doc: Mapping[str, Any], ctx: Context, issues: list[Issue], comments: Mapping[int, list[dict[str, Any]]]
) -> tuple[list[Planned], list[str]]:
    records = doc.get("records") if isinstance(doc.get("records"), dict) else {}
    views, notes = record_issues(
        ctx.repository, issues, ctx.reproductions, bot_login=ctx.entry.bot_login, known=records
    )
    planned: list[Planned] = []
    for view in views:
        record = records.get(view.fingerprint) or {}
        observation = fact = outcome = None
        if view.verifiable and view.spec is not None:
            if ctx.checks is not None:
                observation = ctx.checks.observations.get(view.fingerprint)
            fact = classify(view.spec, observation)
            outcome = redetect(view.handoff, {fact.id: fact} if fact else {})
        last_at, last_rev = _latest_statement(record, view, comments.get(view.issue.number, []), ctx.entry.bot_login)
        reopened = tuple(record.get("reopened_revisions") or ())
        decision = decide(
            verifiable=view.verifiable,
            outcome=outcome,
            issue_state=view.issue.state,
            state_reason=view.issue.state_reason,
            closed_by_bot=view.issue.closed_by == ctx.entry.bot_login,
            reopened_revisions=reopened,
            revision=ctx.revision if ctx.checks is not None else None,
            last_statement_at=last_at,
            last_statement_revision=last_rev,
            now=ctx.now,
            interval_days=ctx.entry.recheck_comment_interval_days,
            unchanged_interval_days=ctx.entry.unchanged_revision_comment_interval_days,
        )
        planned.append(
            Planned(view, outcome, fact, observation, decision,
                    _iso(last_at) if last_at else None, last_rev)
        )
    return planned, notes


def execute(planned: list[Planned], ctx: Context, *, live: bool) -> list[ActionResult]:
    """Perform (live) or only describe (dry run) each decided action. Every write is preceded by a
    read-back of the issue's comments for its marker, so a replay never posts twice."""
    owner, name = ctx.repository.split("/", 1)
    day = ctx.now.date().isoformat()
    results: list[ActionResult] = []
    toolchain = ctx.checks.toolchain if ctx.checks else {}
    for item in planned:
        action = item.decision.action
        result = ActionResult(item.view.issue.number, action)
        results.append(result)
        if action == "NONE":
            result.note = item.decision.reason
            continue
        assert ctx.revision is not None
        body = comment_body(action, item.view, ctx.revision, day, item.observation, toolchain)
        result.marker = body.rstrip().rsplit("\n", 1)[-1]
        if not live:
            result.note = f"dry run: would {action} #{item.view.issue.number} ({item.decision.reason})"
            continue
        if item.view.issue.author != ctx.entry.bot_login:  # never touch a human's issue
            result.error = "refused: the issue is not authored by the pilot's App identity"
            continue
        number = item.view.issue.number
        try:
            existing = list_issue_comments(owner, name, number, token=ctx.write_token, fetch=ctx.fetch)
            present = any(isinstance(c.get("body"), str) and result.marker in c["body"] for c in existing)
            if not present:
                comment_issue(owner, name, number, body=body, token=ctx.write_token or "", write=ctx.post)
            if action == "CLOSE":
                close_issue(owner, name, number, reason="completed", token=ctx.write_token or "", write=ctx.patch)
            elif action == "REOPEN":
                reopen_issue(owner, name, number, token=ctx.write_token or "", write=ctx.patch)
        except RepositoryMetadataError as exc:
            result.error = str(exc)[:300]
            continue
        result.performed = True
        result.note = f"{action} #{number}" + (" (comment already present, not re-posted)" if present else "")
    return results


def live_blockers(
    entry: PilotEntry, doc: Mapping[str, Any], environment: Mapping[str, str], token: TokenDecision | None
) -> list[str]:
    """Why this cycle may NOT write upstream (empty = it may)."""
    blockers = []
    if entry.mode != "live":
        blockers.append(f"pilot mode is {entry.mode!r} in data/issue_pilot.json (live writes need 'live')")
    if int(doc.get("dry_run_cycles") or 0) < 1:
        blockers.append("no dry-run cycle is recorded yet: the first hosted cycle is always a dry run")
    if not write_authorized(environment):
        blockers.append("kill switch REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED is not set to 1")
    if token is None:
        blockers.append("no App installation token was minted for this run")
    elif not token.ok:
        blockers.append(f"App installation token refused: {token.reason}")
    return blockers


def apply_cycle(
    doc: Mapping[str, Any] | None,
    ctx: Context,
    planned: list[Planned],
    results: list[ActionResult],
    *,
    mode: str,
    run_key: str,
    blockers: list[str],
    notes: list[str],
) -> dict[str, Any]:
    """The new state document. Pure and idempotent: re-applying the same ``run_key`` changes
    nothing, so GitJsonRef's compare-and-swap retries are safe."""
    base: dict[str, Any] = json.loads(json.dumps(doc)) if isinstance(doc, Mapping) else {}
    base.setdefault("schema_version", STATE_SCHEMA_VERSION)
    base.setdefault("repository", ctx.repository)
    base.setdefault("records", {})
    base.setdefault("ledger", [])
    base.setdefault("cycles", [])
    base.setdefault("dry_run_cycles", 0)
    base.setdefault("live_cycles", 0)
    if any(c.get("run") == run_key for c in base["cycles"]):
        return base
    now = _iso(ctx.now)
    ledger = tuple(entry_from_dict(e) for e in base["ledger"])
    by_number = {r.issue_number: r for r in results}
    rows = []
    for item in planned:
        view = item.view
        record = dict(base["records"].get(view.fingerprint) or {})
        result = by_number.get(view.issue.number)
        handoff = view.handoff
        if result and result.performed and result.action == "CLOSE":
            handoff = replace(handoff, status="RESOLVED_UPSTREAM", close_reason="completed")
        elif result and result.performed and result.action == "REOPEN":
            handoff = replace(handoff, status="FILED", close_reason=None)
        stored = json.loads(json.dumps(handoff_to_dict(handoff)))
        handoff_from_dict(stored, path=Path(state_ref(ctx.repository)))  # fail closed on a bad shape
        if not record:
            ledger = record_event(ledger, handoff.key, revision=handoff.source_revision, observed_at=now,
                                  issue_number=view.issue.number, event="IMPORTED")
        record.update(
            {
                "issue_number": view.issue.number,
                "issue_url": view.issue.url,
                "issue_state": "closed" if result and result.performed and result.action == "CLOSE"
                else "open" if result and result.performed and result.action == "REOPEN" else view.issue.state,
                "verifiable": view.verifiable,
                "verification": view.reason,
                "duplicates": list(view.duplicates),
                "handoff": stored,
            }
        )
        record.setdefault("reopened_revisions", [])
        if item.last_statement_at:
            record["last_statement"] = {"at": item.last_statement_at, "revision": item.last_statement_revision}
        if view.verifiable:
            record["last_check"] = {
                "at": now,
                "revision": ctx.revision if ctx.checks is not None else None,
                "outcome": item.outcome,
                "output_digest": item.observation.output_digest if item.observation else None,
            }
        if result and result.performed and ctx.revision:
            event = {"CLOSE": "CLOSED", "REOPEN": "REOPENED", "COMMENT_STILL_REPRODUCES": "RECHECK_COMMENTED"}[result.action]
            ledger = record_event(ledger, handoff.key, revision=ctx.revision, observed_at=now,
                                  issue_number=view.issue.number, event=event, marker=result.marker)  # type: ignore[arg-type]
            if result.action == "COMMENT_STILL_REPRODUCES":
                record["last_statement"] = {"at": now, "revision": ctx.revision}
            if result.action == "CLOSE":
                record["closed_by_us"] = {"at": now, "revision": ctx.revision}
            if result.action == "REOPEN" and ctx.revision not in record["reopened_revisions"]:
                record["reopened_revisions"].append(ctx.revision)
        base["records"][view.fingerprint] = record
        rows.append(
            {
                "issue": view.issue.number,
                "state": view.issue.state,
                "verifiable": view.verifiable,
                "outcome": item.outcome,
                "output_digest": item.observation.output_digest if item.observation else None,
                "decision": item.decision.action,
                "reason": item.decision.reason,
                "performed": bool(result and result.performed),
                "error": result.error if result else None,
                "note": result.note if result else "",
            }
        )
    base["ledger"] = [entry_to_dict(e) for e in ledger]
    base["cycles"].append(
        {
            "run": run_key,
            "at": now,
            "mode": mode,
            "revision": ctx.revision,
            "checks": ctx.checks_note or ("ok" if ctx.checks else "none"),
            "live_blockers": blockers,
            "notes": notes,
            "rows": rows,
        }
    )
    base["cycles"] = base["cycles"][-MAX_CYCLES_KEPT:]
    base["dry_run_cycles" if mode == "dry_run" else "live_cycles"] += 1
    return base


def render_summary(
    ctx: Context, planned: list[Planned], results: list[ActionResult], *, mode: str,
    blockers: list[str], notes: list[str], state_note: str,
) -> str:
    by_number = {r.issue_number: r for r in results}
    title = "DRY RUN: nothing was written upstream" if mode == "dry_run" else "LIVE"
    lines = [
        f"## Issue maintenance: {ctx.repository} ({title})",
        "",
        f"- Upstream revision checked: `{ctx.revision or 'unknown'}`; checks: {ctx.checks_note or ('ok' if ctx.checks else 'none')}",
        f"- Records: {len(planned)} (verifiable {sum(p.view.verifiable for p in planned)})",
        f"- State: {state_note}",
    ]
    if blockers:
        lines += ["- Live writes blocked because:", *[f"  - {b}" for b in blockers]]
    lines += ["", "| Issue | State | Re-check | Decision | Result |", "|---|---|---|---|---|"]
    for item in planned:
        r = by_number.get(item.view.issue.number)
        outcome = item.outcome or ("unverifiable" if not item.view.verifiable else "n/a")
        result = (r.error and f"ERROR {r.error}") or (r.note if r else "")
        lines.append(
            f"| #{item.view.issue.number} | {item.view.issue.state} | {outcome} | "
            f"{item.decision.action} | {result.replace('|', '/')} |"
        )
    if notes:
        lines += ["", "Notes:", *[f"- {n}" for n in notes]]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- stores / CLI


class Store(Protocol):
    def read(self) -> tuple[str | None, object]: ...

    def update(self, mutate: Callable[[Any], Any]) -> Any: ...


class FileStore:
    """A local JSON file with the GitJsonRef interface (local runs and tests)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.label = f"the local state file {path.name} (not the state remote)"

    def read(self) -> tuple[str | None, object]:
        if not self.path.exists():
            return None, None
        return "local", json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, mutate: Callable[[Any], Any]) -> Any:
        new = mutate(self.read()[1])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return new

    def __enter__(self) -> FileStore:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def upstream_head(repository: str, timeout: float = 60) -> str | None:
    """The default branch's head, read with ``git ls-remote`` (no checkout, no upstream code)."""
    try:
        done = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    first = done.stdout.split()
    return first[0] if done.returncode == 0 and first and re.fullmatch(r"[0-9a-f]{40}", first[0]) else None


def run_cycle(
    repository: str,
    *,
    store: Store,
    checks_payload: Any,
    environment: Mapping[str, str],
    run_key: str,
    now: datetime | None = None,
    head: str | None = None,
    fetch: FetchFn = default_fetch,
    post: WriteFn = default_post,
    patch: WriteFn = default_patch,
    verify_token: Callable[[str, str], TokenDecision] = verify_installation_token,
    pilot_path: Path | None = None,
    reproductions: ReproductionSet | None = None,
) -> tuple[str, dict[str, Any]]:
    """One whole cycle. Returns ``(summary markdown, new state document)``."""
    entry = require_pilot(repository, pilot_path)  # the allowlist enforcement point
    repository = entry.repository
    reproductions = reproductions or load_reproductions(repository)
    moment = now or datetime.now(UTC)
    checks: Checks | None = None
    checks_note: str | None = None
    if checks_payload is None:
        checks_note = "no checks artifact (the reproduce job failed or was skipped): every re-check is NOT_VERIFIABLE"
    elif head is None:
        checks_note = "the upstream head could not be resolved here: checks not trusted, every re-check is NOT_VERIFIABLE"
    else:
        try:
            checks = load_checks(checks_payload, repository=repository, reproductions=reproductions,
                                 expected_revision=head)
        except ChecksError as exc:
            checks_note = f"{exc}: every re-check is NOT_VERIFIABLE"
    token_value = environment.get(APP_INSTALLATION_TOKEN_ENV_VAR, "").strip()
    decision = verify_token(repository, token_value) if token_value else None
    read_token = token_value if decision and decision.ok else (environment.get("GITHUB_TOKEN") or None)
    ctx = Context(
        repository=repository, entry=entry, reproductions=reproductions, now=moment,
        revision=checks.revision if checks else head, checks=checks, checks_note=checks_note,
        fetch=fetch, post=post, patch=patch, read_token=read_token,
        write_token=token_value if decision and decision.ok else None,
    )
    _, current = store.read()
    doc = current if isinstance(current, dict) else {}
    owner, name = repository.split("/", 1)
    raw = list_issues(owner, name, token=read_token, fetch=fetch)
    issues: list[Issue] = []
    comments: dict[int, list[dict[str, Any]]] = {}
    for item in raw:
        issue = issue_from_api(item)
        if issue is None or issue.author != entry.bot_login:
            continue
        if issue.state == "closed":
            detail = get_issue(owner, name, issue.number, token=read_token, fetch=fetch)
            closed_by = detail.get("closed_by") if isinstance(detail.get("closed_by"), dict) else {}
            issue = replace(issue, closed_by=closed_by.get("login"))
        issues.append(issue)
        if issue.state == "open":
            comments[issue.number] = list_issue_comments(owner, name, issue.number, token=read_token, fetch=fetch)
    planned, notes = plan_cycle(doc, ctx, issues, comments)
    blockers = live_blockers(entry, doc, environment, decision)
    mode = "live" if not blockers else "dry_run"
    results = execute(planned, ctx, live=mode == "live")
    try:
        new_doc = store.update(
            lambda current: apply_cycle(current, ctx, planned, results, mode=mode, run_key=run_key,
                                        blockers=blockers, notes=notes)
        )
        state_note = f"cycle {run_key} recorded on {getattr(store, 'label', None) or state_ref(repository)}"
    except (StateBackendError, OSError) as exc:  # the summary must still say what happened upstream
        new_doc = apply_cycle(doc, ctx, planned, results, mode=mode, run_key=run_key,
                              blockers=blockers, notes=notes)
        state_note = f"FAILED to record the cycle ({type(exc).__name__}: {str(exc)[:200]})"
    summary = render_summary(ctx, planned, results, mode=mode, blockers=blockers, notes=notes,
                             state_note=state_note)
    return summary, new_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R39 pilot issue maintenance cycle")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--remote", help="state remote URL (refs/repository-presenter-state/issues/*)")
    group.add_argument("--state-file", type=Path, help="local state file instead of the remote")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    require_pilot(args.repository)
    payload = None
    if args.checks.exists():
        try:
            payload = json.loads(args.checks.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {"unreadable": True}
    head = upstream_head(args.repository)
    if args.state_file:
        store_cm: Any = FileStore(args.state_file)
    else:
        from repo_presenter.core.state.git_backend import GitJsonRef

        store_cm = GitJsonRef(state_ref(args.repository), remote=args.remote,
                              token=os.environ.get("REPOSITORY_PRESENTER_STATE_TOKEN") or None)
    with store_cm as store:
        summary, doc = run_cycle(args.repository, store=store, checks_payload=payload,
                                 environment=os.environ, run_key=args.run_id, head=head)
    print(summary)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(summary)
    last = doc.get("cycles", [{}])[-1]
    return 1 if any(row.get("error") for row in last.get("rows", [])) else 0


if __name__ == "__main__":
    sys.exit(main())
