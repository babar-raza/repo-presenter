"""BL-075: the M9 seeder gives control slots only to seals whose zero-call re-certification is RECERTIFIED
(stale seals may still carry a seed), and the scorer prints the not-recertified split beside the raw
false-flag figure (thresholds unchanged). Against the real records of round 43593733280, where the writer
passed at 0/20 false flags while the scorer reported 7/27 because 7 stale Lane R controls were included.
Fake keys and seal histories only; no network, no real secret."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, encrypt_seed_manifest
from repo_presenter.core.state.bundle_store import SealRecord

REPO = Path(__file__).resolve().parents[1]
ROUND = json.loads((REPO / "tests" / "fixtures" / "m9" / "round_43593733280_controls.json").read_text("utf-8"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seeder = _load("run_m9_seeder")
scorer = _load("run_m9_scorer")

README = """# {name} FOSS

{name} FOSS does a thing with `{name}Widget`, which has 4 public types organized into one
module and exposes `{name}Widget.render` for building output.

## Classes

| Class | Description |
|---|---|
| `{name}Widget` | The main widget object exposed by this library. |
| `{name}Options` | Configuration options for `{name}Widget`. |

## Installation

```bash
pip install {name}-foss
```
"""


def _real_by_lane() -> dict[str, list]:
    """The round's 46 real (repository, lane, revision) candidates as seals with a seedable README."""
    by_lane: dict[str, list] = {"L": [], "R": []}
    for record in sorted(ROUND["records"], key=lambda r: (r["lane"], r["repository"])):
        name = record["repository"].split("/")[1].replace(".", "")
        seal = SealRecord(repository=record["repository"], lane=record["lane"], commit="c" * 40,
                          revision=record["revision"], manifest_state="ACCEPTED", dependencies={}, review=None,
                          readme=README.format(name=name).encode())
        by_lane[record["lane"]].append((record["repository"], seal))
    return by_lane


RECERTIFIED = {(r["repository"], r["lane"], r["revision"]) for r in ROUND["records"] if r["recertified"]}


def test_no_control_slot_goes_to_a_seal_that_does_not_recertify() -> None:
    by_lane = _real_by_lane()
    for salt in (0, 1, 43593733280):
        index, manifest = seeder.build_seed_plan(by_lane, salt, frozenset(), RECERTIFIED)
        shapes = {m["case_id"]: m["shape"] for m in manifest}
        controls = [e for e in index if shapes[e["case_id"]] == CLEAN_SHAPE]
        assert controls and all((e["repository"], e["lane"], e["revision"]) in RECERTIFIED for e in controls)
        # every stale Lane R seal is still audit material: it carries a seed
        stale = [e for e in index if (e["repository"], e["lane"], e["revision"]) not in RECERTIFIED]
        assert len(stale) == 12 and all(shapes[e["case_id"]] != CLEAN_SHAPE for e in stale)
        assert sum(1 for lane in ("L", "R") for e in index
                   if e["lane"] == lane and shapes[e["case_id"]] != CLEAN_SHAPE) >= 2 * seeder.MIN_PER_LANE


def test_negative_control_without_the_filter_stale_seals_get_control_slots() -> None:
    by_lane = _real_by_lane()
    index, manifest = seeder.build_seed_plan(by_lane, 0, frozenset())
    shapes = {m["case_id"]: m["shape"] for m in manifest}
    assert any(shapes[e["case_id"]] == CLEAN_SHAPE
               and (e["repository"], e["lane"], e["revision"]) not in RECERTIFIED for e in index)


def test_the_seeder_fails_closed_when_recertification_cannot_run(monkeypatch, tmp_path) -> None:
    def broken(remote: str = "origin"):
        raise RuntimeError("state remote unreachable")

    monkeypatch.setattr(seeder, "seal_history", lambda **_: {})
    monkeypatch.setattr(seeder, "recertified_seals", broken)
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--out-dir", str(tmp_path), "--dry-run"])
    assert seeder.main() == 1


def _raw_manifest() -> list[dict]:
    return [
        {"case_id": r["case_id"], "candidate_id": f"{r['repository']}@{r['lane']}@{r['revision']}",
         "shape": CLEAN_SHAPE if r["role"] == "clean_control" else "A",
         "operator": "clean_control" if r["role"] == "clean_control" else "count_mismatch",
         "line": None if r["role"] == "clean_control" else 1}
        for r in ROUND["records"]
    ]


def _findings() -> list:
    return [scorer.Finding(candidate_id=f["candidate_id"], claim=f["claim"], verdict=f["verdict"],
                           path=f["path"], line=int(f["line"])) for f in ROUND["control_findings"]]


def test_the_scorer_prints_the_not_recertified_split_of_round_43593733280() -> None:
    raw = _raw_manifest()
    stale = scorer.not_recertified_controls(raw, RECERTIFIED)
    assert len(stale) == 7
    result = scorer.score(scorer.key_manifest_by_case_id(raw), _findings(), stale)
    # the raw gate figure is unchanged: 7 of 27 ...
    assert result["false_flag_rate"] == {"matched": 7, "total": 27, "rate": 7 / 27}
    # ... and beside it, the population the acceptance writer judged: 0 of 20 (all 7 flags on stale seals)
    split = result["false_flag_split"]
    assert split["recertified_controls"] == {"matched": 0, "total": 20, "rate": 0.0}
    assert split["not_recertified_controls"] == {"matched": 7, "total": 7, "rate": 1.0}
    assert split["controls_not_recertified"] == stale
    assert scorer.render_split(result) == (
        "false-flag (raw): 7/27; recertified controls 0/20, not-recertified controls 7/7"
    )


def test_without_the_split_the_scorecard_is_as_before() -> None:
    raw = _raw_manifest()
    result = scorer.score(scorer.key_manifest_by_case_id(raw), _findings())
    assert "false_flag_split" not in result
    assert scorer.render_split(result).endswith("not-recertified split: not computed")


@pytest.mark.parametrize("broken", [False, True])
def test_scorer_main_writes_the_split_and_never_fails_on_it(monkeypatch, tmp_path, broken: bool) -> None:
    key = b"\x05" * 32
    manifest_path = tmp_path / "seed_manifest.enc"
    manifest_path.write_bytes(encrypt_seed_manifest(_raw_manifest(), key))
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(ROUND["control_findings"]), encoding="utf-8")

    def recertified(remote: str = "origin"):
        if broken:
            raise RuntimeError("no remote")
        return RECERTIFIED

    monkeypatch.setattr(scorer, "recertified_seals", recertified)
    monkeypatch.setenv("AUDIT_SEED_KEY", key.hex())
    out = tmp_path / "scorecard.json"
    monkeypatch.setattr("sys.argv", ["run_m9_scorer.py", "--manifest", str(manifest_path),
                                     "--findings", str(findings_path), "--out", str(out)])
    assert scorer.main() == 0
    card = json.loads(out.read_text(encoding="utf-8"))
    assert card["false_flag_rate"]["matched"] == 7
    assert ("false_flag_split" in card) is (not broken)
