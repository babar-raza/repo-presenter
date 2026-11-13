"""data/benchmarks.json stays in agreement with data/registry.json: one entry per repository,
honestly marked, never a guessed live_upstream_readme_refresh without a cited source."""

from __future__ import annotations

import json
from pathlib import Path

from support import REPO_ROOT

from repo_presenter.core.registry.benchmarks import (
    BENCHMARK_STATUSES,
    check_coverage,
    load_benchmarks,
    load_registry_repositories,
)

REGISTRY_PATH = REPO_ROOT / "data" / "registry.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "benchmarks.json"


def test_the_real_committed_benchmarks_document_is_consistent_with_the_registry():
    """The actual, committed data/benchmarks.json: every active registry repository has exactly
    one entry, no entry names an unknown repository, and nothing is marked
    live_upstream_readme_refresh without evidence. The one check this card's checker exists for."""
    assert check_coverage(REGISTRY_PATH, BENCHMARKS_PATH) == []


def test_every_benchmark_status_is_one_of_the_three_honest_values():
    document = load_benchmarks(BENCHMARKS_PATH)
    for entry in document["entries"]:
        assert entry["benchmark_status"] in BENCHMARK_STATUSES


def test_no_entry_claims_live_upstream_readme_refresh_without_a_citable_source():
    """Never guess: a live_upstream_readme_refresh entry must cite something, in evidence."""
    document = load_benchmarks(BENCHMARKS_PATH)
    for entry in document["entries"]:
        if entry["benchmark_status"] == "live_upstream_readme_refresh":
            assert str(entry.get("evidence") or "").strip(), entry["repository"]


def test_the_document_carries_the_r2_ruling_and_a_meaning_sentence():
    document = load_benchmarks(BENCHMARKS_PATH)
    assert "R2" in document["ruling"]
    assert document["meaning"]


def test_load_registry_repositories_matches_the_real_registry():
    repos = load_registry_repositories(REGISTRY_PATH)
    assert len(repos) == 41  # R34 (2026-11-13): 36 plus OCR .NET, OMR Python, PSD Java, Words Java, Cells PHP
    assert "aspose-3d-foss/Aspose.3D-FOSS-for-.NET" in repos


# --- check_coverage against synthetic documents: every problem class it must catch -------------


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _registry(tmp_path: Path, repos: list[str]) -> Path:
    return _write(
        tmp_path,
        "registry.json",
        {"schema_version": 1, "entries": [{"repository": r} for r in repos]},
    )


def _benchmarks(tmp_path: Path, entries: list[dict]) -> Path:
    return _write(
        tmp_path,
        "benchmarks.json",
        {"schema_version": 1, "ruling": "R2", "meaning": "m", "entries": entries},
    )


def test_a_consistent_synthetic_pair_has_no_problems(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a", "o/b"])
    benchmarks = _benchmarks(
        tmp_path,
        [
            {"repository": "o/a", "benchmark_status": "unknown", "evidence": "x", "checked": "2026-11-07"},
            {
                "repository": "o/b",
                "benchmark_status": "no_benchmark_claimed",
                "evidence": "",
                "checked": "2026-11-07",
            },
        ],
    )
    assert check_coverage(registry, benchmarks) == []


def test_a_registry_repository_with_no_benchmark_entry_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a", "o/b"])
    benchmarks = _benchmarks(
        tmp_path,
        [
            {"repository": "o/a", "benchmark_status": "unknown", "evidence": "x", "checked": "d"},
        ],
    )
    problems = check_coverage(registry, benchmarks)
    assert any("o/b" in p and "missing" in p for p in problems)


def test_a_benchmark_entry_for_an_unknown_repository_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a"])
    benchmarks = _benchmarks(
        tmp_path,
        [
            {"repository": "o/a", "benchmark_status": "unknown", "evidence": "x", "checked": "d"},
            {"repository": "o/ghost", "benchmark_status": "unknown", "evidence": "x", "checked": "d"},
        ],
    )
    problems = check_coverage(registry, benchmarks)
    assert any("o/ghost" in p for p in problems)


def test_a_duplicate_benchmark_entry_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a"])
    benchmarks = _benchmarks(
        tmp_path,
        [
            {"repository": "o/a", "benchmark_status": "unknown", "evidence": "x", "checked": "d"},
            {"repository": "o/a", "benchmark_status": "unknown", "evidence": "x", "checked": "d"},
        ],
    )
    problems = check_coverage(registry, benchmarks)
    assert any("o/a" in p and "2 benchmark entries" in p for p in problems)


def test_an_invalid_benchmark_status_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a"])
    benchmarks = _benchmarks(
        tmp_path,
        [{"repository": "o/a", "benchmark_status": "definitely_true", "evidence": "", "checked": "d"}],
    )
    problems = check_coverage(registry, benchmarks)
    assert any("definitely_true" in p for p in problems)


def test_a_live_upstream_claim_with_no_evidence_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a"])
    benchmarks = _benchmarks(
        tmp_path,
        [
            {
                "repository": "o/a",
                "benchmark_status": "live_upstream_readme_refresh",
                "evidence": "",
                "checked": "d",
            }
        ],
    )
    problems = check_coverage(registry, benchmarks)
    assert any("evidence is empty" in p for p in problems)


def test_entries_not_a_list_is_reported(tmp_path: Path):
    registry = _registry(tmp_path, ["o/a"])
    benchmarks = _write(
        tmp_path, "benchmarks.json", {"schema_version": 1, "entries": {"o/a": {}}}
    )
    problems = check_coverage(registry, benchmarks)
    assert problems and "list" in problems[0]


def test_an_unreadable_registry_is_reported_not_raised(tmp_path: Path):
    registry = tmp_path / "missing.json"
    benchmarks = _benchmarks(tmp_path, [])
    problems = check_coverage(registry, benchmarks)
    assert problems and "cannot read registry" in problems[0]
