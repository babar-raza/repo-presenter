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
