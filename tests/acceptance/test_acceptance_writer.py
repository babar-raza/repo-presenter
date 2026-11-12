"""The hosted acceptance writer (scripts/run_acceptance_writer.py): pure gate + record logic and
the local dry-run path. No key, no network, no gh."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("run_acceptance_writer", _ROOT / "scripts" / "run_acceptance_writer.py")
writer = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(writer)

SEEDED_SHAPE = "unsupported_claim"


def _manifest(n_seeded: int = 10, n_clean: int = 10) -> list[dict]:
    seeded = [{"candidate_id": f"s{i}", "shape": SEEDED_SHAPE, "line": 10 + i} for i in range(n_seeded)]
    clean = [{"candidate_id": f"c{i}", "shape": CLEAN_SHAPE} for i in range(n_clean)]
    return seeded + clean


def _case_index(manifest: list[dict]) -> list[dict]:
    return [
        {"case_id": m["candidate_id"], "repository": f"org/repo-{m['candidate_id']}", "lane": "R", "revision": f"rev-{m['candidate_id']}"}
        for m in manifest
    ]


def _catch_all(manifest: list[dict]) -> list[dict]:
    return [
        {"candidate_id": m["candidate_id"], "claim": "x", "verdict": "false", "path": "README.md", "line": m["line"]}
        for m in manifest if m["shape"] != CLEAN_SHAPE
    ]


def _certified(case_index: list[dict]) -> dict:
    return {(c["repository"], c["lane"]): (c["revision"], True) for c in case_index}


def _build(manifest, findings, recert=None, case_index=None):
    case_index = case_index if case_index is not None else _case_index(manifest)
    return writer.build_records_document("42", case_index, manifest, findings, recert if recert is not None else _certified(case_index))


def test_a_passing_audit_passes_only_the_unflagged_clean_controls():
    manifest = _manifest()
    doc = _build(manifest, _catch_all(manifest))
    assert doc["batch_passed"] is True and doc["failed_reasons"] == []
    by_role = {}
    for r in doc["records"]:
        by_role.setdefault(r["role"], []).append(r)
    assert all(r["audit_passed"] for r in by_role["clean_control"])
    assert not any(r["audit_passed"] for r in by_role["seeded"])  # a seeded copy is never a candidate


def test_a_clean_control_the_auditor_flagged_does_not_pass_even_when_the_batch_does():
    manifest = _manifest()
    findings = _catch_all(manifest) + [
        {"candidate_id": "c0", "claim": "x", "verdict": "unverifiable", "path": "README.md", "line": 3}
    ]
    doc = _build(manifest, findings)
    assert doc["batch_passed"] is True  # 1/10 false flag is exactly the 0.10 limit
    passed = {r["case_id"] for r in doc["records"] if r["audit_passed"]}
    assert "c0" not in passed and "c1" in passed


def test_low_seeded_recall_fails_every_record_and_says_why():
    manifest = _manifest()
    doc = _build(manifest, _catch_all(manifest)[:5])
    assert doc["batch_passed"] is False
    assert any("seeded recall" in why for why in doc["failed_reasons"])
    assert not any(r["audit_passed"] for r in doc["records"])


def test_a_false_flag_rate_above_ten_percent_fails_every_record():
    manifest = _manifest()
    findings = _catch_all(manifest) + [
        {"candidate_id": f"c{i}", "claim": "x", "verdict": "false", "path": "README.md", "line": 1} for i in range(2)
    ]
    doc = _build(manifest, findings)
    assert doc["batch_passed"] is False
    assert any("false-flag" in why for why in doc["failed_reasons"])
    assert not any(r["audit_passed"] for r in doc["records"])


@pytest.mark.parametrize("bad", [
    {"candidate_id": "s0", "verdict": "maybe", "path": "README.md", "line": 3},
    {"candidate_id": "s0", "verdict": "false", "path": "", "line": 3},
    {"candidate_id": "s0", "verdict": "false", "path": "README.md", "line": 0},
])
def test_structurally_invalid_evidence_fails_the_batch(bad):
    manifest = _manifest()
    doc = _build(manifest, [*_catch_all(manifest), bad])
    assert doc["batch_passed"] is False
    assert any("evidence validity" in why for why in doc["failed_reasons"])


def test_an_empty_seeded_or_clean_population_fails_closed_instead_of_passing_vacuously():
    for manifest in (_manifest(n_seeded=0), _manifest(n_clean=0)):
        doc = _build(manifest, _catch_all(manifest))
        assert doc["batch_passed"] is False
        assert not any(r["audit_passed"] for r in doc["records"])


def test_a_seal_that_no_longer_matches_the_audited_revision_is_not_validated():
    manifest = _manifest()
    case_index = _case_index(manifest)
    recert = {(c["repository"], c["lane"]): ("some-other-revision", True) for c in case_index}
    doc = _build(manifest, _catch_all(manifest), recert, case_index)
    assert all(r["deterministically_validated"] is False for r in doc["records"])


def test_a_seal_that_fails_recertification_is_not_validated():
    manifest = _manifest()
    case_index = _case_index(manifest)
    recert = {(c["repository"], c["lane"]): (c["revision"], False) for c in case_index}
    doc = _build(manifest, _catch_all(manifest), recert, case_index)
    assert all(r["deterministically_validated"] is False for r in doc["records"])


def test_the_dry_run_cli_writes_a_dry_run_document_without_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT_SEED_KEY", raising=False)
    manifest = _manifest()
    case_index = _case_index(manifest)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "findings.json").write_text(json.dumps(_catch_all(manifest)), encoding="utf-8")
    (tmp_path / "case_index.json").write_text(json.dumps(case_index), encoding="utf-8")
    out = tmp_path / "acceptance-records-7.json"
    code = writer.main(
        ["--seed-run-id", "7", "--manifest", str(tmp_path / "manifest.json"), "--findings", str(tmp_path / "findings.json"),
         "--case-index", str(tmp_path / "case_index.json"), "--out", str(out), "--dry-run"],
        recertify=lambda: _certified(case_index),
    )
    assert code == 0
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["dry_run"] is True and document["schema"] == writer.SCHEMA


def test_the_real_mode_refuses_to_run_without_the_audit_key(tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT_SEED_KEY", raising=False)
    for name in ("m.enc", "f.json", "c.json"):
        (tmp_path / name).write_text("[]", encoding="utf-8")
    code = writer.main(
        ["--seed-run-id", "7", "--manifest", str(tmp_path / "m.enc"), "--findings", str(tmp_path / "f.json"),
         "--case-index", str(tmp_path / "c.json"), "--out", str(tmp_path / "o.json")],
        recertify=lambda: {},
    )
    assert code == 1 and not (tmp_path / "o.json").exists()


def test_a_manifest_in_the_seeders_real_shape_is_joined_to_findings_by_case_id(tmp_path):
    """The seeder writes {case_id: <hash>, candidate_id: 'repo@lane@rev', ...}; auditors name a
    candidate by case_id. Joining on the manifest's own candidate_id scored recall 0.000 on the
    first real run (2026-11-12), so the writer must re-key by case_id before scoring."""
    manifest, index, findings = [], [], []
    for i in range(10):
        case_id, repo = f"seeded{i:02d}", f"org/repo-s{i}"
        manifest.append({"case_id": case_id, "candidate_id": f"{repo}@R@rev{i}", "shape": SEEDED_SHAPE, "line": 5 + i})
        index.append({"case_id": case_id, "repository": repo, "lane": "R", "revision": f"rev{i}"})
        findings.append({"candidate_id": case_id, "claim": "x", "verdict": "false", "path": f"{case_id}.md", "line": 5 + i})
    for i in range(10):
        case_id, repo = f"clean{i:02d}", f"org/repo-c{i}"
        manifest.append({"case_id": case_id, "candidate_id": f"{repo}@R@rev{i}", "shape": CLEAN_SHAPE})
        index.append({"case_id": case_id, "repository": repo, "lane": "R", "revision": f"rev{i}"})
    paths = {n: tmp_path / f"{n}.json" for n in ("manifest", "findings", "index", "out")}
    paths["manifest"].write_text(json.dumps(manifest))
    paths["findings"].write_text(json.dumps(findings))
    paths["index"].write_text(json.dumps(index))
    recert = {(e["repository"], e["lane"]): (e["revision"], True) for e in index}
    rc = writer.main(
        ["--seed-run-id", "9", "--manifest", str(paths["manifest"]), "--findings", str(paths["findings"]),
         "--case-index", str(paths["index"]), "--out", str(paths["out"]), "--dry-run"],
        recertify=lambda: recert,
    )
    doc = json.loads(paths["out"].read_text())
    assert rc == 0 and doc["gates"]["seeded_recall"]["matched"] == 10
    assert doc["batch_passed"] is True
    assert {r["case_id"] for r in doc["records"] if r["audit_passed"]} == {f"clean{i:02d}" for i in range(10)}


def _flag(case_id: str, line: int = 3, verdict: str = "false") -> dict:
    return {"candidate_id": case_id, "claim": "x", "verdict": verdict, "path": "README.md", "line": line}


def _adjudicated(manifest, flags, adjudications):
    case_index = _case_index(manifest)
    return writer.build_records_document(
        "42", case_index, manifest, _catch_all(manifest) + flags, _certified(case_index), adjudications=adjudications
    )


def test_a_flag_on_a_clean_control_confirmed_by_an_independent_check_fails_that_candidate_not_the_auditor():
    manifest = _manifest(n_seeded=10, n_clean=10)
    doc = _adjudicated(manifest, [_flag("c0")], [{"candidate_id": "c0", "line": 3, "adjudication": "confirmed"}])
    assert doc["batch_passed"] is True and doc["gates"]["false_flag_rate"]["matched"] == 0
    verdicts = {r["case_id"]: r["audit_passed"] for r in doc["records"] if r["role"] == "clean_control"}
    assert verdicts["c0"] is False and all(v for k, v in verdicts.items() if k != "c0")


def test_a_refuted_flag_counts_against_the_auditor_but_does_not_block_the_candidate():
    manifest = _manifest(n_seeded=10, n_clean=20)
    doc = _adjudicated(manifest, [_flag("c0")], [{"candidate_id": "c0", "line": 3, "adjudication": "refuted"}])
    assert doc["gates"]["false_flag_rate"]["matched"] == 1
    assert next(r for r in doc["records"] if r["case_id"] == "c0")["audit_passed"] is True


def test_an_unadjudicated_flag_still_counts_against_the_auditor_and_blocks_the_candidate():
    manifest = _manifest(n_seeded=10, n_clean=20)
    doc = _adjudicated(manifest, [_flag("c0")], [])
    assert doc["gates"]["false_flag_rate"]["matched"] == 1
    assert next(r for r in doc["records"] if r["case_id"] == "c0")["audit_passed"] is False


def test_an_adjudication_for_a_different_line_or_a_garbage_verdict_changes_nothing():
    manifest = _manifest(n_seeded=10, n_clean=20)
    doc = _adjudicated(
        manifest, [_flag("c0")],
        [{"candidate_id": "c0", "line": 9, "adjudication": "confirmed"}, {"candidate_id": "c0", "line": 3, "adjudication": "yes"}],
    )
    assert doc["gates"]["false_flag_rate"]["matched"] == 1


def test_the_document_names_the_seeded_defects_the_auditors_missed():
    manifest = _manifest(n_seeded=10, n_clean=10)
    findings = [f for f in _catch_all(manifest) if f["candidate_id"] != "s3"]
    case_index = _case_index(manifest)
    doc = writer.build_records_document("42", case_index, manifest, findings, _certified(case_index))
    assert [m["case_id"] for m in doc["missed_seeded"]] == ["s3"] and doc["batch_passed"] is True
