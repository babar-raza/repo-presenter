"""The owner withdrew one chat model (2026-10-27): the system uses qwen3-next only. No route,
manifest, source file, script or test may name that model id again. The gateway credential
variables ``GPT_OSS_ENDPOINT`` / ``GPT_OSS_API_KEY`` / ``GPT_OSS_MODEL`` are names of credentials,
not of the model, and are spelled with underscores."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.llm.prompts import load_manifests

ROOT = Path(__file__).resolve().parents[1]
WITHDRAWN = "gpt" + "-oss"
SCANNED = ("src", "prompts", "scripts", "tests", ".github")
SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"}
#: Recorded output of past runs, not code, routes or fixtures.
HISTORICAL = ("_lane_r_output", "_lane_l_output", "__pycache__")


def scanned_files() -> list[Path]:
    return [
        path
        for name in SCANNED
        for path in sorted((ROOT / name).rglob("*"))
        if path.is_file()
        and path.suffix in SUFFIXES
        and not any(part in HISTORICAL for part in path.parts)
    ]


def test_the_withdrawn_model_id_appears_in_no_source_manifest_script_or_test() -> None:
    assert scanned_files(), "the scan found nothing to scan"
    offenders = [
        str(path.relative_to(ROOT))
        for path in scanned_files()
        if WITHDRAWN in path.read_text(encoding="utf-8", errors="replace").lower()
    ]
    assert offenders == []


def test_every_manifest_routes_to_the_one_model() -> None:
    registry = load_manifests(ROOT / "prompts")
    assert set(registry.routes().values()) == {"qwen3-next"}
    for loaded in registry.manifests.values():
        assert WITHDRAWN not in loaded.path.read_text(encoding="utf-8").lower()
