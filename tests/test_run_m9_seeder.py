"""The M9 hosted seeder script (scripts/run_m9_seeder.py): real seal selection, real seed.py
operators, real encryption -- tested here with a FAKE seal_history (no network, no real
AUDIT_SEED_KEY), never the live repository or a real secret.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, decrypt_seed_manifest
from repo_presenter.core.state.bundle_store import SealRecord

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_m9_seeder", REPO / "scripts" / "run_m9_seeder.py")
run_m9_seeder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_m9_seeder)

README_TEMPLATE = """# {name} FOSS

{name} FOSS does a thing with `{name}Widget`, which has 4 public types organized into one
module and exposes `{name}Widget.render` for building output.

## Classes

| Class | Description |
|---|---|
| `{name}Widget` | The main widget object exposed by this library. |
| `{name}Options` | Configuration options for `{name}Widget`. |

## Installation

Install from the registry:

```bash
pip install {name}-foss
```
"""


def _seal(name: str, lane: str, i: int) -> SealRecord:
    return SealRecord(
        repository=f"own:{name}",
        lane=lane,
        commit="c" * 40,
        revision=f"{i:04d}" + "a" * 36,
        manifest_state="ACCEPTED",
        dependencies={},
        review=None,
        readme=README_TEMPLATE.format(name=name).encode("utf-8"),
    )


def _fake_history(n_per_lane: int = 12) -> dict:
    history = {}
    for lane in ("L", "R"):
        for i in range(n_per_lane):
            key = (f"own:repo-{lane}-{i}", lane)
            history[key] = [_seal(f"repo-{lane}-{i}", lane, i)]
    return history


def test_select_candidates_groups_by_lane_from_seal_history(monkeypatch):
    monkeypatch.setattr(run_m9_seeder, "seal_history", lambda **_: _fake_history())
    by_lane = run_m9_seeder.select_candidates()
    assert len(by_lane["L"]) == 12
    assert len(by_lane["R"]) == 12


def test_select_candidates_skips_seals_with_no_readme_or_an_error(monkeypatch):
    history = _fake_history(n_per_lane=1)
    broken_key = ("own:broken", "L")
    history[broken_key] = [
        SealRecord(
            repository="own:broken", lane="L", commit="c" * 40, revision="r" * 40,
            manifest_state="ACCEPTED", dependencies={}, review=None, readme=None,
        )
    ]
    erroring_key = ("own:erroring", "L")
    history[erroring_key] = [
        SealRecord(
            repository="own:erroring", lane="L", commit="c" * 40, revision="e" * 40,
            manifest_state="ACCEPTED", dependencies={}, review=None,
            readme=b"# x", error="could not verify",
        )
    ]
    monkeypatch.setattr(run_m9_seeder, "seal_history", lambda **_: history)
    by_lane = run_m9_seeder.select_candidates()
    repos = {repo for repo, _seal in by_lane["L"]}
    assert "own:broken" not in repos
    assert "own:erroring" not in repos
    assert "own:repo-L-0" in repos


def test_build_seed_plan_reaches_at_least_20_seeded_from_36_real_shaped_candidates():
    by_lane = {"L": [], "R": []}
    for lane in ("L", "R"):
        for i in range(18):
            by_lane[lane].append((f"own:{lane}-{i}", _seal(f"{lane}widget{i}", lane, i)))
    case_index, manifest = run_m9_seeder.build_seed_plan(by_lane)
    assert len(case_index) == 36
    seeded = [m for m in manifest if m["shape"] != CLEAN_SHAPE]
    clean = [m for m in manifest if m["shape"] == CLEAN_SHAPE]
    assert len(seeded) >= 20
    assert len(clean) >= 1  # some clean controls for the false-flag-rate measurement


def test_build_seed_plan_is_deterministic_given_the_same_seal_history():
    by_lane = {"L": [(f"own:x{i}", _seal(f"x{i}", "L", i)) for i in range(10)], "R": []}
    index1, manifest1 = run_m9_seeder.build_seed_plan(by_lane)
    index2, manifest2 = run_m9_seeder.build_seed_plan(by_lane)
    assert index1 == index2
    assert manifest1 == manifest2


def test_main_writes_candidates_index_and_encrypted_manifest_with_a_matching_commitment(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(run_m9_seeder, "seal_history", lambda **_: _fake_history(n_per_lane=12))
    key = b"\x07" * 32
    monkeypatch.setenv("AUDIT_SEED_KEY", key.hex())
    monkeypatch.setattr(
        "sys.argv", ["run_m9_seeder.py", "--out-dir", str(tmp_path)]
    )
    rc = run_m9_seeder.main()
    assert rc == 0

    candidates_dir = tmp_path / "candidates"
    index = json.loads((tmp_path / "case_index.json").read_text(encoding="utf-8"))
    assert len(index) == 24
    for entry in index:
        assert (candidates_dir / f"{entry['case_id']}.md").is_file()
        # The public index names the real repository/lane/revision (the auditor needs this);
        # it names nothing about which case is seeded.
        assert "repository" in entry and "lane" in entry and "revision" in entry

    blob = (tmp_path / "seed_manifest.enc").read_bytes()
    committed = (tmp_path / "commitment.sha256").read_text(encoding="utf-8").strip()
    import hashlib

    assert hashlib.sha256(blob).hexdigest() == committed

    manifest = decrypt_seed_manifest(blob, key)
    assert len(manifest) == 24
    assert {m["case_id"] for m in manifest} == {e["case_id"] for e in index}


def test_main_fails_closed_with_no_audit_seed_key(monkeypatch, tmp_path):
    monkeypatch.setattr(run_m9_seeder, "seal_history", lambda **_: _fake_history(n_per_lane=12))
    monkeypatch.delenv("AUDIT_SEED_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--out-dir", str(tmp_path)])
    rc = run_m9_seeder.main()
    assert rc == 1
    assert not (tmp_path / "candidates").exists()


def test_dry_run_selects_and_plans_but_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(run_m9_seeder, "seal_history", lambda **_: _fake_history(n_per_lane=12))
    monkeypatch.setattr(
        "sys.argv", ["run_m9_seeder.py", "--out-dir", str(tmp_path), "--dry-run"]
    )
    rc = run_m9_seeder.main()
    assert rc == 0
    assert not (tmp_path / "candidates").exists()
    assert not (tmp_path / "seed_manifest.enc").exists()


def test_a_different_salt_rotates_which_candidates_are_controls_so_a_burned_batch_is_not_repeated():
    by_lane = {"L": [], "R": []}
    for lane in ("L", "R"):
        for i in range(12):
            by_lane[lane].append((f"own:{lane}-{i}", _seal(f"{lane}widget{i}", lane, i)))

    def controls(salt):
        _index, manifest = run_m9_seeder.build_seed_plan(by_lane, salt)
        return {m["case_id"] for m in manifest if m["shape"] == CLEAN_SHAPE}

    assert controls(0) != controls(1) and controls(1) != controls(2)
    assert run_m9_seeder.build_seed_plan(by_lane, 0) == run_m9_seeder.build_seed_plan(by_lane, 0)


def test_the_blind_batch_never_seeds_the_reorder_shape_that_can_leave_a_coherent_document():
    by_lane = {"L": [(f"own:{i}", _seal(f"w{i}", "L", i)) for i in range(30)], "R": []}
    _index, manifest = run_m9_seeder.build_seed_plan(by_lane)
    assert {m["shape"] for m in manifest} <= {"A", "D", "D9", "D14", CLEAN_SHAPE}
