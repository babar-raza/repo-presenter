"""BL-084: every hosted present run's failures are classified at the source, recorded on the cell's
durable failure ref, aggregated into a portfolio Pareto, and read by the cohort planner to hold a
cell whose last failure is entirely in classes the current code has not touched. Zero provider
calls. The log fixtures in tests/fixtures/failures/ are real excerpts of hosted present runs (the
lane steps' report lines and the settle step's arguments), cut by run id."""

from __future__ import annotations

import inspect
import io
import json
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from support import init_git_repository

from repo_presenter import failures, present
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repo_presenter.readme.review.findings import Finding

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "failures"
WORKFLOWS = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT))

from scripts.select_scheduled_cohort import plan_cohort, render_summary  # noqa: E402


def _records(run_id: str) -> dict[str, dict[str, Any]]:
    text = (FIXTURES / f"run_{run_id}.log").read_text(encoding="utf-8")
    return {r["lane"]: r for r in failures.records_from_log(text, run_id=run_id)}


# --------------------------------------------------------------------------- classification of real logs


def test_email_net_claim_contradictions_classify_as_member_kind() -> None:
    record = _records("43520977467")["R"]
    assert record["repository"] == "aspose-email-foss/Aspose.Email-FOSS-for-.Net"
    assert record["outcome"] == "failure" and record["durable_state"] == "INVALIDATED"
    assert record["source_revision"].startswith("59125b47")
    assert set(record["classes"]) == {"claim_contradiction|unresolved|member_kind"}
    finding = record["findings"][0]
    assert finding["quote"].startswith("| `MapiAttachment` | MapiAttachment class represents")
    # Location from the quote's own shape, never an origin claim.
    assert finding["origin"] == {"kind": "unresolved", "id": "api_table_row:MapiAttachment"}
    # Repair attempts are kept with outcome and reason.
    outcomes = {(r["label"], r["outcome"]) for r in record["repairs"]}
    assert ("BC-14", "unrepairable") in outcomes and ("BC-14", "repaired") in outcomes
    assert all(r["reason"] or r["outcome"] == "repaired" for r in record["repairs"])


def test_deterministic_only_blocking_check_is_a_validation_finding() -> None:
    record = _records("43520974296")["R"]
    assert set(record["classes"]) == {"BC-05|unresolved|section_fit"}
    assert record["findings"][0]["source"] == "validation"
    assert "no LLM review" in record["failure"]["detail"]


def test_job_error_without_findings_is_its_own_class() -> None:
    record = _records("43516334907")["R"]
    assert set(record["classes"]) == {"job_error|job_error|JobError:section_authoring_output_truncated_at"}
    assert record["failure"]["kind"] == "JobError" and not record["failure"]["transient"]


def test_lane_r_success_and_lane_l_detector_failure_in_one_run() -> None:
    records = _records("43525320899")
    assert records["R"]["outcome"] == "success" and records["R"]["classes"] == {}
    lane_l = records["L"]
    assert set(lane_l["classes"]) == {"lane_l_unrepaired_defect|lane_l_correction|format_overclaim"}
    assert lane_l["classes"]["lane_l_unrepaired_defect|lane_l_correction|format_overclaim"]["findings"] == 2
    assert lane_l["findings"][0]["quote"] == 'i1["An existing CFB container (file or bytes)"]'
    assert lane_l["durable_state"] == "FAILED_INTERNAL"


def test_inherited_unit_named_by_the_check_and_a_noop_proof_error() -> None:
    records = _records("43473790998")
    assert records["R"]["classes"]["BC-17|inherited_unit|technical_content"]["origins"][0].startswith(
        "inherited_unit:050.table"
    )
    assert "BC-05|inherited_unit|superseded_unstated" in records["R"]["classes"]
    assert set(records["L"]["classes"]) == {"job_error|job_error|NoOpProofError:LEDGER_NO_RECORDS"}


def test_the_repair_ledgers_facts_defect_attributes_the_renderer() -> None:
    record = _records("43513037866")["R"]
    signature = "BC-18|renderer_fact|misleading_claim"
    assert signature in record["classes"]
    assert record["classes"][signature]["origins"] == ["public_symbol:aspose.cells_foss.workbook.save"]
    assert record["findings"][0]["quote"].startswith("- `Save`: Saves the workbook")


@pytest.mark.parametrize(
    ("rule", "text", "expected"),
    [
        ("claim_contradiction", "line 129 (COMPOSING): the README calls `a.b` a field ('x'), but", "member_kind"),
        ("claim_contradiction", "line 3 (COMPOSING): the README says `E` is thrown, but implementation:never_thrown.e states", "never_thrown"),
        ("claim_contradiction", "line 9 (COMPOSING): the README claims .dae output, but format:output.dae is reachable only through a stub", "stub_format"),
        ("claim_contradiction", "line 1 (COMPOSING): something nobody tabled yet about `X`", "something_nobody_tabled_yet"),
        ("BC-17", "inherited_unit:027.paragraph holds h2 'A', which ... loses (section_coverage): keep", "section_coverage"),
        ("BC-07", "heading '### Export a workbook' is not in title case: 'workbook'", "title_case"),
        ("llm:factuality", "The library does not support X", "-"),
    ],
)
def test_sub_rules(rule: str, text: str, expected: str) -> None:
    assert failures.sub_rule(rule, text) == expected


def test_job_error_kinds_and_transience() -> None:
    assert failures.job_error_kind("attempt under version set abc123: NoOpProofError: [LEDGER_NO_RECORDS] x")[1] == "LEDGER_NO_RECORDS"
    assert failures.is_transient("model output was rejected ... (retryable: a re-run asks the model again)")
    assert not failures.is_transient("JobError: section_authoring: output truncated")


# --------------------------------------------------------------------------- hosted records from outputs


def _fact(fact_id: str, kind: str, value: str, **attributes: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", "x"),), attributes=attributes or None)  # type: ignore[arg-type]


def _workdir(tmp_path: Path) -> Path:
    workdir = tmp_path / ".present-work"
    out = workdir / "cascade"
    out.mkdir(parents=True)
    write_facts(
        FactsDocument(
            "o/n", "a" * 40,
            (
                _fact("public_symbol:o.widget", "public_symbol", "o.Widget", docstring="Builds widgets from their parts quickly."),
                _fact("inherited_unit:004.paragraph", "inherited_unit", "The maintainers wrote this paragraph about installing."),
                _fact("example:001", "example", "widget = Widget()\nwidget.save('out.bin')"),
            ),
        ),
        workdir / "facts.json",
    )
    (out / "content_units.coherent.json").write_text(json.dumps({"units": [
        {"section": "api_reference", "slot": "type:public_symbol:o.gadget", "text": "Gadget holds the parts of a widget."},
    ]}))
    (out / "plan.json").write_text(json.dumps({"quick_start_example_id": "example:001", "additional_example_ids": []}))
    (out / "repairs.json").write_text(json.dumps({"attempts": {"x": {
        "label": "BC-18", "outcome": "unrepairable", "stage": "S6", "section_id": "api_reference",
        "reason": "facts defect: ...", "facts_defects": [{"quote": "- `Old`: Prints the old thing.", "fact_ids": ["public_symbol:o.old"]}],
    }}}))
    findings = [
        Finding(rule="claim_contradiction", source="deterministic", claim_kind="contradiction",
                message="line 4 (COMPOSING): the README calls `Gadget.parts` a field", quote="| `Gadget` | Gadget holds the parts of a widget. |"),
        Finding(rule="claim_contradiction", source="deterministic", claim_kind="contradiction",
                message="line 9 (COMPOSING): the README calls `Widget.build` a field", quote="| `Widget` | Builds widgets from their parts quickly. |"),
        Finding(rule="live_readme_loss", source="deterministic", claim_kind="omission",
                message="live README content lost without an accounting disposition: code block 'x'",
                quote="The maintainers wrote this paragraph about installing."),
        Finding(rule="llm:factuality", source="llm", claim_kind="unsupported_claim", message="wrong",
                quote="widget.save('out.bin')", finding_id="F01", section_id="quick_start"),
    ]
    failures.keep_blocking(out, SimpleNamespace(blocking_findings=findings))
    (out / "validation.json").write_text(json.dumps({"checks": [
        {"id": "BC-18", "verdict": "FAIL", "failures": [{"detail": "open finding (confirmed false claim: x) still printed: The README text '- `Old`: Prints the old thing.' is false", "section_id": "api_reference"}]},
        {"id": "BC-07", "verdict": "FAIL", "failures": [{"detail": "kept as written but ends with a colon", "unit_id": "inherited_unit:004.paragraph"}]},
        {"id": "BC-01", "verdict": "PASS", "failures": []},
    ]}))
    return workdir


def test_a_hosted_record_resolves_every_printing_origin(tmp_path: Path) -> None:
    workdir = _workdir(tmp_path)
    path = failures.write_local_record(
        workdir=workdir, repository="o/n", lane="R", exit_code=1, durable_state="INVALIDATED",
        failure_detail="attempt under version set abc: PresentFailure: independent review returned REJECT",
        failure_classification="validation_failed", version_set="abc",
    )
    record = json.loads(path.read_text())
    origins = {f["label"]: f["origin"] for f in record["findings"]}
    by_quote = {f["quote"][:12]: f["origin"] for f in record["findings"]}
    assert by_quote["| `Gadget` |"] == {"kind": "authored_unit", "id": "api_reference.type:public_symbol:o.gadget"}
    assert by_quote["| `Widget` |"] == {"kind": "renderer_fact", "id": "public_symbol:o.widget"}
    assert by_quote["The maintain"] == {"kind": "inherited_unit", "id": "inherited_unit:004.paragraph"}
    assert origins["F01"] == {"kind": "planned_example", "id": "example:001"}
    assert by_quote["- `Old`: Pri"] == {"kind": "renderer_fact", "id": "public_symbol:o.old"}
    assert "BC-07|inherited_unit|trailing_colon" in record["classes"]
    assert "BC-01" not in json.dumps(record["classes"])
    assert record["repairs"][0]["facts_defects"][0]["fact_ids"] == ["public_symbol:o.old"]


def test_a_success_record_has_no_class(tmp_path: Path) -> None:
    path = failures.write_local_record(
        workdir=_workdir(tmp_path), repository="o/n", lane="R", exit_code=0, durable_state="ACCEPTED"
    )
    record = json.loads(path.read_text())
    assert record["outcome"] == "success" and record["classes"] == {} and record["failure"] is None


def test_present_keeps_the_rejected_findings_and_writes_the_record() -> None:
    cascade = inspect.getsource(present._cascade_and_seal)
    lane_l = inspect.getsource(present._lane_l_and_seal)
    for source in (cascade, lane_l):
        assert source.index("keep_blocking(result.out_dir, verdict)") < source.index("raise PresentFailure")
    main = inspect.getsource(present.main)
    assert "write_local_record(" in main and main.index("write_local_record(") > main.index("run_present(")


def test_the_reject_path_writes_blocking_findings_before_raising(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    finding = Finding(rule="claim_contradiction", source="deterministic", claim_kind="contradiction",
                      message="line 1 (COMPOSING): x", quote="q")
    verdict = SimpleNamespace(verdict="REJECT", blocking_findings=[finding], findings=[finding], model_reviewed=False)
    out = tmp_path / "cascade"
    monkeypatch.setattr(present, "preflight_cascade", lambda *a, **k: SimpleNamespace(can_skip_provider_call=False, recertify=False, reason="-"))
    monkeypatch.setattr(present, "run_cascade", lambda *a, **k: SimpleNamespace(review_verdict=verdict, out_dir=out))
    monkeypatch.setattr(present, "blocked_predicate", lambda v: "blocked")
    with pytest.raises(present.PresentFailure), redirect_stdout(io.StringIO()):
        present._cascade_and_seal(
            repository="o/n", ecosystem="python", clone_path=tmp_path, facts_path=tmp_path / "f.json",
            workdir=tmp_path, candidates_root=tmp_path, config=None, prompts_path=tmp_path, registry_path=tmp_path,
        )
    kept = json.loads((out / failures.BLOCKING_FILENAME).read_text())
    assert kept["findings"][0]["rule"] == "claim_contradiction"


# --------------------------------------------------------------------------- the durable ref, publish, pareto


def _finalized(run_id: str, at: str, **kw: Any) -> dict[str, Any]:
    record = _records(run_id)[kw.pop("lane", "R")]
    return failures.finalize(record, run_id=run_id, at=at, code=kw.pop("code", "c1"), root=ROOT)


def test_the_ref_write_and_read_keep_the_latest_run_and_a_history(tmp_path: Path) -> None:
    remote = str(init_git_repository(tmp_path / "state"))
    older = _finalized("43473803090", "2026-11-13T17:32:00Z")
    newer = _finalized("43513037866", "2026-11-13T21:42:00Z", code="c2")
    failures.publish_record(newer, remote=remote, token=None)
    failures.publish_record(older, remote=remote, token=None)  # a backfilled older run never wins
    failures.publish_record(newer, remote=remote, token=None)  # re-publishing a run changes nothing
    (document,) = failures.read_cells(remote=remote, token=None)
    assert document["repository"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET" and document["lane"] == "R"
    assert document["latest"]["run_id"] == "43513037866"
    assert [h["run_id"] for h in document["history"]] == ["43473803090", "43513037866"]
    assert failures.parse_failure_ref(failures.failure_ref("a/b", "L")) == ("a/b", "L")


def test_pareto_ranks_by_cells_and_marks_classes_new_since_the_previous_code() -> None:
    docs = failures.documents_from_records([
        _finalized("43520977467", "2026-11-13T22:38:00Z", code="new"),
        _finalized("43473803090", "2026-11-13T17:32:00Z", code="old"),
        _finalized("43513037866", "2026-11-13T21:42:00Z", code="new"),
    ])
    result = failures.pareto(docs)
    signatures = [row["signature"] for row in result["classes"]]
    assert result["cells"] == 2 and result["failing_cells"] == 2
    new = {row["signature"]: row["new"] for row in result["classes"]}
    assert new["claim_contradiction|unresolved|member_kind"] is True
    # BC-18 renderer misleading_claim was seen under the old code (Cells .NET, run 43473803090's
    # history entry is older code) -- not new.
    assert "BC-18|renderer_fact|misleading_claim" in signatures
    assert "claim_contradiction \\| unresolved \\| member_kind" in failures.render_pareto(result)


def test_the_publish_cli_writes_records_a_job_error_and_the_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote = str(init_git_repository(tmp_path / "state"))
    workdir = _workdir(tmp_path)
    failures.write_local_record(workdir=workdir, repository="o/n", lane="R", exit_code=1, durable_state="INVALIDATED",
                                failure_detail="PresentFailure: x")
    monkeypatch.chdir(ROOT)
    summary = tmp_path / "summary.md"
    with redirect_stdout(io.StringIO()):
        status = failures.main([
            "publish", "--remote", remote, "--repository", "o/n", "--lanes", "R,L",
            "--outcome", "R=failure", "--outcome", "L=failure", "--facts-result", "success",
            "--run-id", "999", "--main-sha", "f" * 40, "--source-revision", "a" * 40,
            "--workdir", str(workdir), "--summary", str(summary),
        ])
    assert status == 0
    cells = {d["lane"]: d for d in failures.read_cells(remote=remote, token=None)}
    assert cells["R"]["latest"]["run_id"] == "999" and cells["R"]["latest"]["code"]
    assert set(cells["L"]["latest"]["classes"]) == {"job_error|job_error|LaneStepFailure:the_lane_step_ended"}
    assert all(item["scope"] for item in cells["R"]["latest"]["classes"].values())
    text = summary.read_text()
    assert "### Failure classes (this run)" in text and "claim_contradiction" in text
    out = io.StringIO()
    with redirect_stdout(out):
        assert failures.main(["pareto", "--remote", remote, "--json"]) == 0
    assert json.loads(out.getvalue())["failing_cells"] == 2


def test_a_facts_failure_records_a_job_error_for_each_lane(tmp_path: Path) -> None:
    with redirect_stdout(io.StringIO()):
        status = failures.main([
            "publish", "--repository", "o/n", "--lanes", "R,L", "--outcome", "R=skipped", "--outcome", "L=skipped",
            "--facts-result", "failure", "--run-id", "1", "--workdir", str(tmp_path), "--summary", str(tmp_path / "s.md"),
        ])
    assert status == 0
    assert (tmp_path / "s.md").read_text().count("job_error \\| FactsJobFailure:the_facts_job_ended") == 2


# --------------------------------------------------------------------------- planner hold


NOW = datetime(2026, 11, 13, 23, 0, tzinfo=UTC)


def _entry(repository: str) -> Any:
    return SimpleNamespace(repository=repository, ecosystem="net", active=True)


def _ledger(repository: str, run_id: str, code: str, revision: str) -> dict[str, Any]:
    return {"entries": [{
        "kind": "settle", "id": "cohort-1-1-1", "repository": repository, "outcomes": {"R": "failure"},
        "sealed": [], "code": code, "source_revision": revision, "at": "2026-11-13T21:00:00+00:00",
        "run_url": f"https://github.com/o/r/actions/runs/{run_id}",
    }]}


def _plan(known: Any, *, head: str = "rev1", run_id: str = "77", code: str = "new-code") -> dict[str, Any]:
    repository = "o/n"
    return plan_cohort(
        entries={repository: _entry(repository)}, authorized_repos={repository}, certifications={},
        ledger=_ledger(repository, run_id, "old-code", "rev1"), terminals=[], code=code,
        head=lambda _r: head, now=NOW, known=known,
    )


def test_unchanged_classes_hold_and_a_changed_scope_releases() -> None:
    record = _finalized("43520977467", "2026-11-13T22:38:00Z")
    scope_now = lambda paths: failures.scope_fingerprint(paths, ROOT, "HEAD")  # noqa: E731
    assert failures.unchanged_classes(record, scope_now) == ["claim_contradiction|unresolved|member_kind"]
    assert failures.unchanged_classes(record, lambda paths: "changed") is None
    transient = failures.finalize(
        failures.build_record(repository="o/n", lane="R", outcome="failure",
                              failure_detail="no valid independent review (retryable: a re-run asks the reviewer again)"),
        run_id="1", code="c", root=ROOT,
    )
    assert failures.unchanged_classes(transient, scope_now) is None


def test_the_planner_holds_a_known_failure_and_says_why() -> None:
    known = {("o/n", "R"): {"run_id": "77", "source_revision": "rev1", "classes": ["X|a|b", "Y|c|d"]}}
    plan = _plan(known)
    assert all("R" not in run["lanes"] for run in plan["runs"])  # Lane L, never attempted, still runs
    (skipped,) = [s for s in plan["skipped"] if s["lane"] == "R"]
    assert skipped["category"] == "known_failure"
    assert skipped["reason"] == "held: last failure in classes X|a|b, Y|c|d; waiting for a fix"
    plan["failure_pareto"] = [{"signature": "X|a|b", "cells": 1, "findings": 3, "new": True}]
    summary = render_summary(plan)
    assert "### Held on a known failure (1)" in summary
    assert "held: last failure in classes X|a|b, Y|c|d; waiting for a fix" in summary
    assert "### Failure classes (latest record per cell)" in summary


@pytest.mark.parametrize(
    ("kwargs", "why"),
    [
        ({"head": "rev2"}, "upstream moved"),
        ({"run_id": "78"}, "the record is not about the last attempt"),
    ],
)
def test_the_planner_releases_when_the_inputs_moved(kwargs: dict[str, str], why: str) -> None:
    known = {("o/n", "R"): {"run_id": "77", "source_revision": "rev1", "classes": ["X|a|b"]}}
    plan = _plan(known, **kwargs)
    assert any("R" in run["lanes"] for run in plan["runs"]), why


def test_without_a_record_the_planner_dispatches_as_before() -> None:
    assert any("R" in run["lanes"] for run in _plan(None)["runs"])
    # Same code fingerprint: the existing idempotent skip still applies first.
    plan = _plan(None, code="old-code")
    assert any(s["category"] == "idempotent" for s in plan["skipped"])


# --------------------------------------------------------------------------- workflow structure


def _workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def test_the_present_job_classifies_every_run_after_the_lanes() -> None:
    steps = _workflow("present.yml")["jobs"]["present"]["steps"]
    names = [step.get("name", "") for step in steps]
    index = names.index("Classify this run's failures")
    step = steps[index]
    assert step["if"] == "always()"
    assert index > names.index("Present (Lane L)") and index > names.index("Present (Lane R)")
    assert "python -m repo_presenter.failures publish" in step["run"]
    assert '--summary "$GITHUB_STEP_SUMMARY"' in step["run"]
    assert step["env"]["REPOSITORY_PRESENTER_STATE_TOKEN"] == "${{ github.token }}"
    assert not any("secrets." in str(value) for value in step["env"].values())


def test_the_supervisor_tick_shows_failure_classes_next_to_the_backlog() -> None:
    doc = _workflow("supervisor-tick.yml")
    assert doc["permissions"]["contents"] == "read"
    (step,) = [s for s in doc["jobs"]["tick"]["steps"] if "doctor" in s.get("name", "")]
    run = step["run"]
    assert run.index('echo "### Backlog"') < run.index('echo "### Failure classes"') < run.index("for cmd in")
    assert "python -m repo_presenter.failures pareto" in run
    assert step["env"]["REPOSITORY_PRESENTER_STATE_TOKEN"] == "${{ github.token }}"
