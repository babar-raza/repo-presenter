#!/usr/bin/env python
"""Review-page feedback intake that runs on the GitHub runner, without a Claude session (R47, BL-761).

The hosted review page (docs/REVIEW_PAGE.md) cannot write to the Claude artifact `db`, so its "Save feedback" button
opens a prefilled GitHub issue (label `review-feedback`) whose body carries one machine-readable block:

    <!-- review-feedback {"id": "...", "verdict": "changes", "note": "...", "repository": "o/n", ...} -->

This script turns such issues (or a snapshot directory of the artifact-db entries, one `<id>.json` each, the format the
session watcher has used so far) into `project/backlog.yaml` items of type `feedback`. Everything read is hostile
input: only the owner, a member or a collaborator may file; fields are validated against fixed shapes; an item is
keyed by a hash of (candidate id, verdict, note), so a re-run never files the same feedback twice and a *changed*
note files a new item (R47: "new or changed entry").

    python scripts/review_page/feedback_intake.py --issue-event "$GITHUB_EVENT_PATH"      # one `issues` event
    python scripts/review_page/feedback_intake.py --issues-json issues.json               # `gh api` list of issues
    python scripts/review_page/feedback_intake.py --snapshot-dir <dir>                    # artifact-db snapshot files

It edits the backlog file only (appending items); committing, branching and the pull request are the workflow's.
Prints one JSON object: {"filed": [...], "skipped": [...]}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKLOG = ROOT / "project" / "backlog.yaml"
LABEL = "review-feedback"
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
VERDICTS = {"approve", "changes", "reject", ""}
MAX_NOTE = 4000
_MARKER = re.compile(r"<!--\s*review-feedback\s*(\{.*?\})\s*-->", re.S)
_ID = re.compile(r"^[0-9a-f]{10}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_HEX = re.compile(r"^[0-9a-f]{7,40}$")
KEY_PREFIX = "feedback-key:"


class Rejected(ValueError):
    """The input is not a valid feedback entry; the message says why."""


def validate(raw: object) -> dict:
    """The entry with only known, shape-checked fields, or `Rejected`."""
    if not isinstance(raw, dict):
        raise Rejected("feedback is not a JSON object")
    entry = {
        "id": raw.get("id"), "verdict": raw.get("verdict", "") or "", "note": raw.get("note", "") or "",
        "repository": raw.get("repository"), "lane": raw.get("lane"),
        "revision": raw.get("revision"), "seal": raw.get("seal"), "updatedAt": raw.get("updatedAt") or "",
    }
    if not isinstance(entry["id"], str) or not _ID.match(entry["id"]):
        raise Rejected("id must be the 10-hex candidate id")
    if entry["verdict"] not in VERDICTS:
        raise Rejected(f"verdict {entry['verdict']!r} not in {sorted(VERDICTS)}")
    if not isinstance(entry["note"], str) or len(entry["note"]) > MAX_NOTE:
        raise Rejected(f"note must be text of at most {MAX_NOTE} characters")
    if not isinstance(entry["repository"], str) or not _REPO.match(entry["repository"]):
        raise Rejected("repository must be owner/name")
    if entry["lane"] not in ("R", "L"):
        raise Rejected("lane must be R or L")
    for field in ("revision", "seal"):
        if not isinstance(entry[field], str) or not _HEX.match(entry[field]):
            raise Rejected(f"{field} must be a hex commit prefix")
    if not isinstance(entry["updatedAt"], str) or len(entry["updatedAt"]) > 40:
        raise Rejected("updatedAt must be a short timestamp string")
    entry["note"] = entry["note"].replace("\r\n", "\n").strip()
    return entry


def key(entry: dict) -> str:
    """Stable identity of this exact feedback (candidate, verdict, note); a changed note is a new key."""
    return hashlib.sha1(f"{entry['id']}|{entry['verdict']}|{entry['note']}".encode()).hexdigest()[:10]


def actionable(entry: dict) -> bool:
    """A bare approval is acknowledged, not filed: it asks for nothing."""
    return bool(entry["note"]) or entry["verdict"] in ("changes", "reject")


def from_issue(issue: dict) -> dict:
    """The validated entry carried by one issue; `Rejected` when it is not owner feedback."""
    labels = {(label.get("name") if isinstance(label, dict) else label) for label in issue.get("labels") or []}
    if LABEL not in labels:
        raise Rejected(f"issue lacks the {LABEL} label")
    if issue.get("pull_request"):
        raise Rejected("a pull request is not feedback")
    if issue.get("author_association") not in TRUSTED:
        raise Rejected(f"author_association {issue.get('author_association')!r} is not owner/member/collaborator")
    found = _MARKER.search(issue.get("body") or "")
    if not found:
        raise Rejected("no review-feedback block in the issue body")
    try:
        entry = validate(json.loads(found.group(1)))
    except json.JSONDecodeError as exc:
        raise Rejected(f"the review-feedback block is not JSON: {exc}") from exc
    entry["source_url"] = str(issue.get("html_url") or "")
    return entry


def from_snapshot(directory: Path) -> tuple[list[dict], list[dict]]:
    """Entries of an artifact-db snapshot (`<candidate id>.json` per document); (entries, rejections)."""
    entries, rejected = [], []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw.setdefault("id", path.stem)
            entry = validate(raw)
            entry["source_url"] = f"artifact-db:feedback/{path.stem}"
            entries.append(entry)
        except (Rejected, json.JSONDecodeError) as exc:
            rejected.append({"source": path.name, "reason": str(exc)})
    return entries, rejected


def _q(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def item_id(entry: dict) -> str:
    return f"BL-FB-{entry['id']}-{key(entry)[:6]}"


def render_item(entry: dict, today: str) -> str:
    """One backlog entry in the file's own style (2-space list indent, JSON-quoted scalars: valid YAML)."""
    verdict = entry["verdict"] or "note only"
    where = f"{entry['repository']} Lane {entry['lane']} (revision {entry['revision']}, seal {entry['seal']})"
    note = entry["note"] or "(no note; verdict only)"
    title = f"Review feedback on {where}: {verdict}: {note.splitlines()[0][:140]}"
    source = (f"owner review feedback via the hosted README Candidate Review page (R47), {entry['updatedAt'] or today}, "
              f"{entry['source_url'] or 'no url'}; {KEY_PREFIX} {key(entry)}; verbatim note: {note}")
    lines = [
        f"  - id: {item_id(entry)}",
        f"    title: {_q(title)}",
        "    type: feedback",
        f"    source: {_q(source)}",
        "    priority: P1",
        "    status: open",
        "    implementation_path: " + _q(
            "R47 cycle, started at filing: investigate portfolio-wide (R36, R41: is it a class across both lanes and all "
            "candidates?), execute the class fix through the governed pipeline (R38), verify every candidate under the "
            "new code, then rebuild and host the review page (review-page workflow)"),
        "    acceptance: " + _q(
            "(1) the class behind the note is named with the evidence for it; (2) the fix lands on main with a test; "
            "(3) a portfolio-wide re-verification is recorded ('reverified: <run id>, lane R x/y, lane L x/y'); "
            "(4) the review page is rebuilt by the review-page workflow and the owner can see the result"),
        "    next_action: " + _q("supervisor: start investigation now (R47); do not wait for the next planning pass"),
        f"    updated: {_q(today)}",
    ]
    return "\n".join(lines) + "\n"


def apply(entries: list[dict], backlog: Path, today: str) -> dict:
    """Append one item per new actionable entry; skip what the backlog already holds (by key)."""
    text = backlog.read_text(encoding="utf-8")
    filed, skipped, add = [], [], []
    for entry in entries:
        k = key(entry)
        if not actionable(entry):
            skipped.append({"id": entry["id"], "key": k, "reason": "approval without a note asks for nothing"})
        elif f"{KEY_PREFIX} {k}" in text or any(f"{KEY_PREFIX} {k}" in a for a in add):
            skipped.append({"id": entry["id"], "key": k, "reason": "already filed"})
        else:
            add.append(render_item(entry, today))
            filed.append({"id": entry["id"], "key": k, "item": item_id(entry), "source_url": entry["source_url"]})
    if add:
        backlog.write_text(text.rstrip("\n") + "\n\n" + "\n".join(add), encoding="utf-8")
    return {"filed": filed, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--issue-event", type=Path, help="a GitHub `issues` event payload (GITHUB_EVENT_PATH)")
    source.add_argument("--issues-json", type=Path, help="a JSON list of issues (`gh api .../issues`)")
    source.add_argument("--snapshot-dir", type=Path, help="a directory of artifact-db feedback documents")
    parser.add_argument("--backlog", type=Path, default=BACKLOG)
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args(argv)
    entries: list[dict] = []
    rejected: list[dict] = []
    if args.snapshot_dir:
        entries, rejected = from_snapshot(args.snapshot_dir)
    else:
        raw = json.loads((args.issue_event or args.issues_json).read_text(encoding="utf-8"))
        issues = [raw["issue"]] if args.issue_event else raw
        # `gh api --paginate --slurp` gives a list of pages (each a list of issues): flatten it.
        issues = [i for page in issues for i in (page if isinstance(page, list) else [page])]
        for issue in issues:
            try:
                entries.append(from_issue(issue))
            except Rejected as exc:
                rejected.append({"source": issue.get("html_url") or issue.get("number"), "reason": str(exc)})
    result = apply(entries, args.backlog, args.today)
    result["rejected"] = rejected
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
