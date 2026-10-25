"""Report, read-only, what filing each committed Handoff would do right now
(DECIDE_NEXT_ISSUE_FILINGS, project/state.yaml).

Scans evidence/build/*/*/handoff.json for typed Handoff records (issues/model.py) and runs each
through issues.file.plan_filing against a real GitApprovalStore (issues/approval.py) rooted at
this repository's own HEAD -- the same read-only decision file_handoff itself makes before any
network call. Never files, searches upstream, or rechecks a defect: ``existing``/``recheck`` are
deliberately not wired here, so every HANDOFF_PENDING handoff refuses for exactly one reason
right now -- no committed ops/issue_approvals/<handoff_id>.json exists yet. That refusal is
itself the proof the gate works: it demonstrates the approval-required path end to end, with no
owner approval recorded, with no accidental filing.

Each pending handoff's own approval_refused reports exactly what the owner would need to commit
(issues/approval.py's ops/issue_approvals/<handoff_id>.json shape) and the evidence_digest that
record must carry.

Usage:
    python scripts/plan_pending_handoffs.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.issues.approval import GitApprovalStore, evidence_digest, handoff_id
from repo_presenter.issues.file import plan_filing
from repo_presenter.issues.model import load_handoff

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO_ROOT / "evidence" / "build"
REPORT_PATH = EVIDENCE_ROOT / "pending_handoffs_plan.json"


def _handoff_paths() -> list[Path]:
    return sorted(EVIDENCE_ROOT.glob("*/*/handoff.json"))


def main() -> None:
    approvals = GitApprovalStore(REPO_ROOT)
    rows: list[dict[str, object]] = []
    for path in _handoff_paths():
        handoff = load_handoff(path)
        plan = plan_filing(handoff, approvals=approvals, expected_repository=handoff.repository)
        rows.append(
            {
                "source": path.relative_to(REPO_ROOT).as_posix(),
                "repository": handoff.repository,
                "status": handoff.status,
                "handoff_id": handoff_id(handoff),
                "evidence_digest": evidence_digest(handoff),
                "title": handoff.suggested_issue_title,
                "ready": plan.ready,
                "already_filed": asdict(plan.already_filed) if plan.already_filed else None,
                "refusal": plan.refusal,
                "approval_refused": plan.approval_refused,
                "approval_path_expected": f"ops/issue_approvals/{handoff_id(handoff)}.json",
            }
        )
        print(f"{handoff.repository}: status={handoff.status} ready={plan.ready} "
              f"refusal={plan.refusal!r}")
    REPORT_PATH.write_text(
        json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {REPORT_PATH} ({len(rows)} handoffs)")


if __name__ == "__main__":
    main()
