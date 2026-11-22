"""What FILING one committed handoff would do right now: a read-only, zero-call dry-run report.

Owner feedback R50 (2026-11-22), WP-4/WP-5: the issue system must be exercisable end to end on the
TeX Python defect (approved 2026-10-16, never filed, fixed upstream 2026-11-06). The monitor
(``issues/monitor.py``) covers the re-verify / close half; this covers the file half. It makes no
network call and writes nothing: every gate that would stand between the handoff and a real
``POST /repos/<owner>/<name>/issues`` is evaluated and reported on its own (not first-failure
only), next to the issue the filing would produce (title, labelled body with the fingerprint
marker, labels) and the dedup verdict against the records on hand.

Gates reported, each independent (``issues/file.py`` enforces the same set in order):

1. registry write gate (``core/registry/write_gate.py``): ``issue_filing`` needs ``issues_mode: file``
   (absent, derived from ``mode``); a ``dry_run`` entry can never obtain a permit.
2. upstream write allowlist (``data/upstream_write_allowlist.json``) and the R39 pilot grant, via
   the same ``github/client.py`` request guard every write passes (the pilot never creates).
3. the kill switch variable ``REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED`` (necessary, never sufficient).
4. the per-handoff owner approval record (committed, digest-bound, expiring, at most 30 days).
5. dedup: the committed reproduction/simulated records, an optional monitor state document, and an
   optional list of upstream issues (``--issues-file``; none is read from the network here).
6. staleness: when a checks artifact is supplied, the defect's own recorded reproduction is
   re-classified; a handoff whose defect no longer reproduces is refused ("stale finding").

Usage (all offline)::

    python -m repo_presenter.issues.filing_report \\
        --handoff data/issue_handoffs/<id>.json [--approval-file <record.json>] \\
        [--checks checks.json --head <40-hex>] [--now 2026-11-22T00:00:00Z]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.authorization.refusals import WriteRefusedError
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry.write_gate import require_write_permitted
from repo_presenter.github.client import (
    API_ROOT,
    UpstreamWriteForbiddenError,
    authorize_request,
)
from repo_presenter.issues.approval import (
    ApprovalStore,
    approval_relative_path,
    evidence_digest,
    handoff_id,
    verify_approval,
)
from repo_presenter.issues.dedup import body_with_marker, parse_fingerprint
from repo_presenter.issues.file import (
    AUTHORIZATION_VARIABLE,
    plan_filing,
    write_authorized,
)
from repo_presenter.issues.labels import labels_for
from repo_presenter.issues.model import Handoff, IssueRef, load_handoff
from repo_presenter.issues.pilot import PilotError, load_reproductions
from repo_presenter.issues.reproduce import ChecksError, classify, load_checks

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "data" / "registry.json"


class _FileApprovals:
    """An approval record read from one given file (evidence runs only; the real gate reads a
    committed git ref through ``GitApprovalStore``)."""

    def __init__(self, path: Path | None) -> None:
        self.path = path

    def read(self, identifier: str) -> str | None:
        if self.path is None or not self.path.exists():
            return None
        return self.path.read_text(encoding="utf-8")


def _gate_registry(registry_path: Path, repository: str) -> dict[str, Any]:
    try:
        require_write_permitted(load_registry(registry_path), repository, "issue_filing")
    except WriteRefusedError as exc:
        return {"gate": "registry write gate (issue_filing)", "open": False, "reason": str(exc)}
    return {"gate": "registry write gate (issue_filing)", "open": True, "reason": "issues_mode is file"}


def _gate_allowlist(repository: str, title: str, body: str, labels: tuple[str, ...]) -> dict[str, Any]:
    try:
        authorize_request(
            "POST", f"{API_ROOT}/repos/{repository}/issues", {"title": title, "body": body, "labels": list(labels)}
        )
    except UpstreamWriteForbiddenError as exc:
        return {"gate": "upstream write allowlist / R39 pilot request guard", "open": False, "reason": str(exc)}
    return {"gate": "upstream write allowlist / R39 pilot request guard", "open": True, "reason": "allowed"}


def build_report(
    handoff: Handoff,
    *,
    approvals: ApprovalStore,
    environment: Mapping[str, str],
    now: datetime,
    registry_path: Path = REGISTRY_PATH,
    issues: list[dict[str, Any]] | None = None,
    state_doc: Mapping[str, Any] | None = None,
    checks_payload: Any = None,
    head: str | None = None,
) -> dict[str, Any]:
    """The whole dry-run report as a JSON-serialisable dict. Never raises for a refusal."""
    labels = labels_for(handoff)
    body = body_with_marker(handoff.suggested_issue_body, handoff.defect_fingerprint)
    gates = [
        _gate_registry(registry_path, handoff.repository),
        _gate_allowlist(handoff.repository, handoff.suggested_issue_title, body, labels),
        {
            "gate": f"kill switch {AUTHORIZATION_VARIABLE}",
            "open": write_authorized(environment),
            "reason": "set to 1" if write_authorized(environment) else "not set to 1 (necessary, never sufficient)",
        },
    ]
    verdict = verify_approval(handoff, approvals, now=lambda: now)
    gates.append(
        {
            "gate": f"owner approval ({approval_relative_path(handoff_id(handoff))})",
            "open": verdict.approved,
            "reason": verdict.reason,
        }
    )

    # dedup against every record on hand
    found: list[str] = []
    tracked = ""
    fingerprint = handoff.defect_fingerprint
    try:
        reproduction_set = load_reproductions(handoff.repository)
    except PilotError:
        reproduction_set = None
    if reproduction_set is not None and fingerprint in reproduction_set.by_fingerprint():
        spec = reproduction_set.by_fingerprint()[fingerprint]
        if fingerprint in reproduction_set.simulated_by_fingerprint():
            # A tracked-but-never-filed record is NOT an upstream issue: it must not block the
            # filing (it would hide exactly the defect this report exists to show), only be noted.
            tracked = f"committed reproduction {spec.check_id} tracks this defect as a SIMULATED record (never filed)"
        else:
            found.append(f"committed reproduction {spec.check_id} (issue #{spec.issue_number})")
    if state_doc and fingerprint in (state_doc.get("records") or {}):
        record = state_doc["records"][fingerprint]
        text = (
            f"monitor state record (issue #{record.get('issue_number')}, "
            f"{'simulated, ' if record.get('simulated') else ''}state {record.get('issue_state')})"
        )
        if record.get("simulated"):
            tracked = (tracked + "; " if tracked else "") + text
        else:
            found.append(text)
    upstream_match: IssueRef | None = None
    for item in issues or []:
        if parse_fingerprint(str(item.get("body") or "")) == fingerprint:
            upstream_match = IssueRef(number=int(item["number"]), url=str(item["html_url"]))
            found.append(f"upstream issue #{upstream_match.number}")
            break

    # staleness (the recheck the filing path runs immediately before the write)
    recheck_note = "no checks artifact supplied: the recorded finding was not re-run"
    still_fires: bool | None = None
    if checks_payload is not None and reproduction_set is not None and head:
        try:
            checks = load_checks(
                checks_payload, repository=handoff.repository, reproductions=reproduction_set,
                expected_revision=head,
            )
            recorded = reproduction_set.by_fingerprint().get(fingerprint)
            fact = classify(recorded, checks.observations.get(fingerprint)) if recorded else None
            if fact is None:
                recheck_note = f"re-run at {head[:12]}: NOT_VERIFIABLE"
            else:
                still_fires = fact.polarity == "CONTRADICTED"
                recheck_note = (
                    f"re-run at {head[:12]}: the defect "
                    f"{'still reproduces' if still_fires else 'no longer reproduces'}"
                )
        except ChecksError as exc:
            recheck_note = str(exc)

    class _Recheck:
        def __init__(self) -> None:
            self.still_fires = still_fires
            self.note = recheck_note

    plan = plan_filing(
        handoff,
        existing=(lambda: upstream_match) if issues is not None else None,
        recheck=(lambda: _Recheck()) if checks_payload is not None else None,
        approvals=approvals,
        now=lambda: now,
        expected_repository=handoff.repository,
    )
    refusals = [g for g in gates if not g["open"]]
    if plan.refusal:
        refusals_text = [plan.refusal]
    else:
        refusals_text = []
    return {
        "schema_version": 1,
        "repository": handoff.repository,
        "handoff_id": handoff_id(handoff),
        "evidence_digest": evidence_digest(handoff),
        "source_revision": handoff.source_revision,
        "mode": "dry run: no network call, nothing written",
        "action": "REFUSED" if (refusals or refusals_text) else ("DEDUP" if found else "FILE"),
        "issue": {"title": handoff.suggested_issue_title, "labels": list(labels), "body": body},
        "gates": gates,
        "dedup": {
            "existing_records": found,
            "simulated_tracking": tracked or None,
            "verdict": "an issue for this defect exists: never re-filed" if found else "no upstream issue found",
        },
        "recheck": recheck_note,
        "plan_filing": {
            "action": plan.action,
            "refusal": plan.refusal,
            "already_filed": None if plan.already_filed is None else {"number": plan.already_filed.number},
        },
        "refusals": [g["reason"] for g in refusals] + refusals_text,
    }


def render(report: Mapping[str, Any]) -> str:
    lines = [
        f"## Filing dry run: {report['repository']} ({report['mode']})",
        "",
        f"- Handoff `{report['handoff_id']}` at revision `{report['source_revision']}`",
        f"- Planned action: **{report['action']}**",
        f"- Title: {report['issue']['title']}",
        f"- Labels: {', '.join(report['issue']['labels'])}",
        f"- Dedup: {report['dedup']['verdict']}" + "".join(f"; {r}" for r in report["dedup"]["existing_records"])
        + (f" (note: {report['dedup']['simulated_tracking']})" if report["dedup"]["simulated_tracking"] else ""),
        f"- Recheck: {report['recheck']}",
        "",
        "| Gate | Open | Reason |",
        "|---|---|---|",
    ]
    for g in report["gates"]:
        lines.append(f"| {g['gate']} | {'yes' if g['open'] else 'NO'} | {str(g['reason']).replace('|', '/')} |")
    lines += ["", "Issue body that would be posted (marker last):", ""]
    lines += [f"> {ln}" for ln in report["issue"]["body"].splitlines()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--approval-file", type=Path, help="an approval record to verify (default: none committed)")
    parser.add_argument("--checks", type=Path, help="checks artifact (issues/reproduce.py) for the staleness recheck")
    parser.add_argument("--head", help="40-hex revision the checks artifact must carry")
    parser.add_argument("--issues-file", type=Path, help="JSON list of upstream issues (API shape); none is fetched")
    parser.add_argument("--state-file", type=Path, help="monitor state document to dedup against")
    parser.add_argument("--now", help="ISO time (default: now)")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    handoff = load_handoff(args.handoff)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    report = build_report(
        handoff,
        approvals=_FileApprovals(args.approval_file),
        environment=os.environ,
        now=now,
        issues=json.loads(args.issues_file.read_text(encoding="utf-8")) if args.issues_file else None,
        state_doc=json.loads(args.state_file.read_text(encoding="utf-8")) if args.state_file else None,
        checks_payload=json.loads(args.checks.read_text(encoding="utf-8")) if args.checks else None,
        head=args.head,
    )
    print(render(report))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
