"""BL-760/761 (R47, WP-6): the review page is rebuilt and hosted by Actions, and review feedback becomes a backlog item
on the runner without a Claude session. Zero-call and offline: what only a hosted run proves (the push, the Pages
deploy, the issue event) is recorded in the backlog as unproven (R41)."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fi = _load("feedback_intake", ROOT / "scripts" / "review_page" / "feedback_intake.py")
rr = _load("run_request_wp6", ROOT / "scripts" / "run_request.py")


def _wf(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _on(wf: dict) -> dict:
    return wf.get("on") or wf[True]


ENTRY = {"id": "01f8407ca9", "verdict": "changes", "note": "Scope section is wrong.\n\nSecond paragraph.",
         "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET", "lane": "R", "revision": "52b0f00ebf28",
         "seal": "03b940a46f7b", "updatedAt": "2026-11-13T15:47:48.944Z"}
BACKLOG_HEAD = """# backlog
items:
  - id: BL-001
    title: "x"
    type: task
    source: "s"
    priority: P1
    status: open
    implementation_path: "p"
    acceptance: "a"
    updated: "2026-11-22"
"""


def _issue(entry=ENTRY, labels=("review-feedback",), assoc="OWNER", number=7):
    body = "Review feedback\n\n<!-- review-feedback " + json.dumps(entry) + " -->\n"
    return {"number": number, "html_url": f"https://github.com/o/r/issues/{number}", "body": body,
            "labels": [{"name": n} for n in labels], "author_association": assoc}


def _backlog(tmp_path: Path) -> Path:
    path = tmp_path / "backlog.yaml"
    path.write_text(BACKLOG_HEAD, encoding="utf-8")
    return path


# --- intake -------------------------------------------------------------------------------------------------------

def test_an_owner_issue_becomes_one_valid_backlog_item(tmp_path):
    backlog = _backlog(tmp_path)
    result = fi.apply([fi.from_issue(_issue())], backlog, "2026-11-22")
    assert [f["item"] for f in result["filed"]] == [fi.item_id(fi.validate(ENTRY))]
    doc = yaml.safe_load(backlog.read_text(encoding="utf-8"))
    item = doc["items"][-1]
    assert item["type"] == "feedback" and item["status"] == "open" and item["priority"] == "P1"
    assert "Scope section is wrong." in item["source"] and "R47" in item["source"]
    assert "aspose-3d-foss/Aspose.3D-FOSS-for-.NET Lane R" in item["title"]
    sys.path.insert(0, str(ROOT / "ops" / "checks"))
    import backlog_check  # noqa: PLC0415
    assert backlog_check.problems(doc) == []


def test_filing_is_idempotent_and_a_changed_note_files_a_new_item(tmp_path):
    backlog = _backlog(tmp_path)
    entry = fi.from_issue(_issue())
    assert len(fi.apply([entry], backlog, "2026-11-22")["filed"]) == 1
    again = fi.apply([entry], backlog, "2026-11-22")
    assert again["filed"] == [] and again["skipped"][0]["reason"] == "already filed"
    changed = fi.from_issue(_issue({**ENTRY, "note": "Different request."}))
    assert len(fi.apply([changed], backlog, "2026-11-22")["filed"]) == 1
    assert len(yaml.safe_load(backlog.read_text(encoding="utf-8"))["items"]) == 3


def test_two_identical_entries_in_one_batch_file_once(tmp_path):
    backlog = _backlog(tmp_path)
    entry = fi.from_issue(_issue())
    assert len(fi.apply([entry, dict(entry)], backlog, "2026-11-22")["filed"]) == 1


def test_a_bare_approval_asks_for_nothing(tmp_path):
    backlog = _backlog(tmp_path)
    entry = fi.validate({**ENTRY, "verdict": "approve", "note": ""})
    result = fi.apply([entry], backlog, "2026-11-22")
    assert result["filed"] == [] and "approval" in result["skipped"][0]["reason"]
    assert backlog.read_text(encoding="utf-8") == BACKLOG_HEAD


@pytest.mark.parametrize("issue, fragment", [
    (_issue(labels=("bug",)), "lacks the review-feedback label"),
    (_issue(assoc="NONE"), "not owner/member/collaborator"),
    (_issue(assoc="CONTRIBUTOR"), "not owner/member/collaborator"),
    ({**_issue(), "pull_request": {"url": "x"}}, "pull request"),
    ({**_issue(), "body": "no block here"}, "no review-feedback block"),
    ({**_issue(), "body": "<!-- review-feedback {not json} -->"}, "not JSON"),
    (_issue({**ENTRY, "id": "../etc"}), "10-hex"),
    (_issue({**ENTRY, "verdict": "maybe"}), "verdict"),
    (_issue({**ENTRY, "repository": "a b/c"}), "owner/name"),
    (_issue({**ENTRY, "lane": "X"}), "lane"),
    (_issue({**ENTRY, "seal": "zz"}), "seal"),
    (_issue({**ENTRY, "note": "x" * 5000}), "at most"),
    ({**_issue(), "body": "<!-- review-feedback {} -->"}, "10-hex"),
])
def test_hostile_or_malformed_issues_are_rejected(issue, fragment):
    with pytest.raises(fi.Rejected, match=fragment):
        fi.from_issue(issue)


def test_hostile_note_text_cannot_break_the_yaml(tmp_path):
    backlog = _backlog(tmp_path)
    note = 'line1\n  - id: BL-EVIL\n    status: done\n"quote" \\ backslash: {x}\n# comment'
    fi.apply([fi.from_issue(_issue({**ENTRY, "note": note}))], backlog, "2026-11-22")
    items = yaml.safe_load(backlog.read_text(encoding="utf-8"))["items"]
    assert [i["id"] for i in items][0] == "BL-001" and len(items) == 2 and items[1]["status"] == "open"
    assert note.strip() in items[1]["source"]


def test_cli_issue_event_sweep_and_snapshot(tmp_path):
    backlog = _backlog(tmp_path)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"action": "opened", "issue": _issue()}), encoding="utf-8")
    run = lambda *a: json.loads(subprocess.run([sys.executable, str(ROOT / "scripts/review_page/feedback_intake.py"),
                                                "--backlog", str(backlog), "--today", "2026-11-22", *a],
                                               capture_output=True, text=True, check=True).stdout)
    assert len(run("--issue-event", str(event))["filed"]) == 1
    sweep = tmp_path / "issues.json"  # `gh api --paginate --slurp`: a list of pages
    other = {**ENTRY, "id": "24f3fd9414", "note": "Second candidate problem"}
    sweep.write_text(json.dumps([[_issue(), _issue(other, number=8), _issue(assoc="NONE", number=9)]]), encoding="utf-8")
    result = run("--issues-json", str(sweep))
    assert [s["reason"] for s in result["skipped"]] == ["already filed"]
    assert len(result["filed"]) == 1 and len(result["rejected"]) == 1
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "31596948d1.json").write_text(json.dumps({k: v for k, v in ENTRY.items() if k != "id"}), encoding="utf-8")
    (snap / "bad.json").write_text("{}", encoding="utf-8")
    result = run("--snapshot-dir", str(snap))
    assert len(result["filed"]) == 1 and result["rejected"][0]["source"] == "bad.json"
    assert result["filed"][0]["source_url"] == "artifact-db:feedback/31596948d1"


# --- the page's feedback button -------------------------------------------------------------------------------------

def test_template_and_build_wire_the_feedback_repository():
    template = (ROOT / "scripts/review_page/template.html").read_text(encoding="utf-8")
    build = (ROOT / "scripts/review_page/build.py").read_text(encoding="utf-8")
    assert template.count("__FEEDBACK_REPO__") == 1 and 'page.replace("__FEEDBACK_REPO__"' in build
    assert "review-feedback" in template and "labels" in template
    # the JSON block in the issue body is what feedback_intake.py parses: same marker name on both sides
    assert "<!-- review-feedback " in template and fi._MARKER.pattern.startswith("<!--")


# --- run requests -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("job", ["review-page", "feedback-intake"])
def test_run_request_jobs_take_no_field(job):
    ok = ["run-request.json"]
    assert rr.validate({"job": job}, [], ok, True) == {"job": job, "repository": "", "ecosystem": "", "lane": ""}
    with pytest.raises(rr.RequestError, match="takes no other field"):
        rr.validate({"job": job, "repository": "x/y"}, [], ok, True)
    execute = _wf("run-request-execute.yml")["jobs"][job]
    assert execute["needs"] == "validate" and execute["if"] == f"needs.validate.outputs.job == '{job}'"
    assert execute["uses"] == f"./.github/workflows/{job}.yml" and "secrets" not in execute


# --- workflows ---------------------------------------------------------------------------------------------------

def test_review_page_workflow_shape():
    wf = _wf("review-page.yml")
    on = _on(wf)
    assert {"workflow_call", "workflow_dispatch", "schedule", "workflow_run"} <= set(on)
    assert on["workflow_run"]["workflows"] == ["recertify"] and on["workflow_run"]["branches"] == ["main"]
    text = (WORKFLOWS / "review-page.yml").read_text(encoding="utf-8")
    assert "secrets." not in text and "GPT_OSS" not in text
    build, publish, pages = wf["jobs"]["build"], wf["jobs"]["publish"], wf["jobs"]["pages"]
    assert build["permissions"] == {"contents": "read"}
    assert "github.event.workflow_run.conclusion == 'success'" in build["if"]
    assert "scripts/review_page/build.py" in "\n".join(s.get("run", "") for s in build["steps"])
    checkout = [s for s in build["steps"] if str(s.get("uses", "")).startswith("actions/checkout")][0]
    assert checkout["with"]["ref"] == "main"
    assert publish["permissions"] == {"contents": "write"} and publish["needs"] == "build"
    assert not [s for s in publish["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert "refs/heads/review-page" in "\n".join(s.get("run", "") for s in publish["steps"])
    assert pages["if"] == "vars.REVIEW_PAGE_PAGES == 'true'"  # an opt-in; absent Pages never fails the workflow
    assert pages["permissions"] == {"pages": "write", "id-token": "write"}


def test_feedback_intake_workflow_never_puts_issue_text_in_a_shell():
    wf = _wf("feedback-intake.yml")
    on = _on(wf)
    assert on["issues"]["types"] == ["opened", "edited", "labeled", "reopened"] and "schedule" in on
    job = wf["jobs"]["intake"]
    assert "review-feedback" in job["if"]
    assert job["permissions"] == {"contents": "write", "issues": "write", "pull-requests": "write"}
    text = (WORKFLOWS / "feedback-intake.yml").read_text(encoding="utf-8")
    assert "secrets." not in text
    assert not re.search(r"\$\{\{\s*github\.event\.(issue|comment)", text.replace(
        "contains(github.event.issue.labels.*.name", ""), re.I)
    assert "github.event.issue.body" not in text and "github.event.issue.title" not in text
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert "ops/checks/backlog_check.py" in run and run.index("backlog_check") < run.index("git push")
    checkout = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout")][0]
    assert checkout["with"]["ref"] == "main"
