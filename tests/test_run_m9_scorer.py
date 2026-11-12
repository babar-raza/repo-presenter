"""The M9 hosted scorer script (scripts/run_m9_scorer.py): real decryption, real score.py
math, tested with a FAKE manifest/key (never a real secret).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, encrypt_seed_manifest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_m9_scorer", REPO / "scripts" / "run_m9_scorer.py")
run_m9_scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_m9_scorer)

KEY = b"\x09" * 32

MANIFEST = [
    {"candidate_id": "own:a@L@rev1", "shape": "A", "operator": "count_mismatch", "line": 5},
    {"candidate_id": "own:b@L@rev2", "shape": "D14", "operator": "add_promotional_filler", "line": 12},
    {"candidate_id": "own:c@L@rev3", "shape": CLEAN_SHAPE, "operator": "clean_control", "line": None},
    {"candidate_id": "own:d@L@rev4", "shape": CLEAN_SHAPE, "operator": "clean_control", "line": None},
]


def _write_findings(path: Path, findings: list[dict]) -> None:
    path.write_text(json.dumps(findings), encoding="utf-8")


def test_score_computes_seeded_recall_and_false_flag_rate_correctly():
    # Catches own:a (right candidate+line), misses own:b entirely, correctly leaves c/d alone.
    findings = [
        run_m9_scorer.Finding(candidate_id="own:a@L@rev1", claim="x", verdict="false",
                               path="src/x.py", line=5),
    ]
    result = run_m9_scorer.score(MANIFEST, findings)
    assert result["seeded_recall"] == {"matched": 1, "total": 2, "rate": 0.5}
    assert result["false_flag_rate"] == {"matched": 0, "total": 2, "rate": 0.0}
    assert result["defective_accepted_rate"] is None


def test_score_counts_a_false_flag_on_a_clean_control():
    findings = [
        run_m9_scorer.Finding(candidate_id="own:a@L@rev1", claim="x", verdict="false",
                               path="src/x.py", line=5),
        run_m9_scorer.Finding(candidate_id="own:b@L@rev2", claim="y", verdict="unverifiable",
                               path="src/y.py", line=12),
        run_m9_scorer.Finding(candidate_id="own:c@L@rev3", claim="z", verdict="false",
                               path="src/z.py", line=1),
    ]
    result = run_m9_scorer.score(MANIFEST, findings)
    assert result["seeded_recall"] == {"matched": 2, "total": 2, "rate": 1.0}
    assert result["false_flag_rate"] == {"matched": 1, "total": 2, "rate": 0.5}


def test_main_decrypts_the_real_manifest_and_writes_the_scorecard(monkeypatch, tmp_path):
    manifest_path = tmp_path / "seed_manifest.enc"
    manifest_path.write_bytes(encrypt_seed_manifest(MANIFEST, KEY))

    findings_path = tmp_path / "findings.json"
    _write_findings(findings_path, [
        {"candidate_id": "own:a@L@rev1", "claim": "x", "verdict": "false",
         "path": "src/x.py", "line": 5},
    ])

    out_path = tmp_path / "scorecard.json"
    monkeypatch.setenv("AUDIT_SEED_KEY", KEY.hex())
    monkeypatch.setattr("sys.argv", [
        "run_m9_scorer.py",
        "--manifest", str(manifest_path),
        "--findings", str(findings_path),
        "--out", str(out_path),
    ])
    rc = run_m9_scorer.main()
    assert rc == 0
    result = json.loads(out_path.read_text(encoding="utf-8"))
    assert result["seeded_recall"]["matched"] == 1
    assert result["seeded_recall"]["total"] == 2


def test_main_fails_closed_with_no_audit_seed_key(monkeypatch, tmp_path):
    manifest_path = tmp_path / "seed_manifest.enc"
    manifest_path.write_bytes(encrypt_seed_manifest(MANIFEST, KEY))
    findings_path = tmp_path / "findings.json"
    _write_findings(findings_path, [])
    monkeypatch.delenv("AUDIT_SEED_KEY", raising=False)
    monkeypatch.setattr("sys.argv", [
        "run_m9_scorer.py",
        "--manifest", str(manifest_path),
        "--findings", str(findings_path),
        "--out", str(tmp_path / "out.json"),
    ])
    rc = run_m9_scorer.main()
    assert rc == 1
    assert not (tmp_path / "out.json").exists()


def test_main_fails_closed_on_the_wrong_key(monkeypatch, tmp_path):
    manifest_path = tmp_path / "seed_manifest.enc"
    manifest_path.write_bytes(encrypt_seed_manifest(MANIFEST, KEY))
    findings_path = tmp_path / "findings.json"
    _write_findings(findings_path, [])
    monkeypatch.setenv("AUDIT_SEED_KEY", (b"\x0a" * 32).hex())
    monkeypatch.setattr("sys.argv", [
        "run_m9_scorer.py",
        "--manifest", str(manifest_path),
        "--findings", str(findings_path),
        "--out", str(tmp_path / "out.json"),
    ])
    import pytest

    with pytest.raises(ValueError):
        run_m9_scorer.main()
