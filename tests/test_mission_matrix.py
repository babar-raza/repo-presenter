"""The mission matrix must validate and must refuse an overclaiming row."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "checks"))
import mission_matrix  # noqa: E402


def test_matrix_is_valid():
    assert mission_matrix.check() == []


def test_overclaim_is_refused(tmp_path):
    data = yaml.safe_load((ROOT / "project" / "mission_matrix.yaml").read_text(encoding="utf-8"))
    data["rows"][0]["status"] = "COMPLETE"
    path = tmp_path / "m.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert any("COMPLETE without" in e for e in mission_matrix.check(path))
