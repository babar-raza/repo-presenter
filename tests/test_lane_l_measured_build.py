"""``build_lane_l_facts`` connects an ecosystem's own measured build to the facts stage.

Before this, ``extract_facts(..., build=...)`` was always called with ``build=None``, so BC-02 said
"no build exited 0: not attempted" for every C++/Node/TypeScript repository (Aspose.Cells FOSS for
C++, hosted, 2026-11-11) whether or not its build works.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_presenter import lane_l
from repo_presenter.core.errors import ExecutionUnavailableError
from repo_presenter.core.examples import MeasuredBuild


class _Plugin:
    def __init__(self, build: Any = None) -> None:
        if build is not None:
            self.verify_build = build


def test_an_ecosystem_that_drives_no_build_passes_none(tmp_path: Path) -> None:
    manifest = tmp_path / "pyproject.toml"
    assert lane_l._measured_build(_Plugin(), tmp_path, manifest, tmp_path) is None


def test_no_manifest_means_no_build_to_measure(tmp_path: Path) -> None:
    plugin = _Plugin(lambda root, manifest, workspace: MeasuredBuild(True, "cmake --build .", "ok"))
    assert lane_l._measured_build(plugin, tmp_path, None, tmp_path) is None


def test_the_plugins_measured_build_is_what_the_facts_stage_receives(tmp_path: Path) -> None:
    manifest = tmp_path / "CMakeLists.txt"
    seen: list[tuple[Path, Path, Path]] = []

    def build(root: Path, manifest: Path, workspace: Path) -> MeasuredBuild:
        seen.append((root, manifest, workspace))
        return MeasuredBuild(True, "cmake -S . -B build\ncmake --build build", "succeeded")

    result = lane_l._measured_build(_Plugin(build), tmp_path, manifest, tmp_path / "ws")
    assert result == MeasuredBuild(True, "cmake -S . -B build\ncmake --build build", "succeeded")
    assert seen == [(tmp_path, manifest, tmp_path / "ws")]


def test_a_harness_that_cannot_start_is_not_attempted_never_a_crash_or_a_pass(
    tmp_path: Path,
) -> None:
    def build(root: Path, manifest: Path, workspace: Path) -> MeasuredBuild:
        raise ExecutionUnavailableError("no process")

    result = lane_l._measured_build(
        _Plugin(build), tmp_path, tmp_path / "CMakeLists.txt", tmp_path
    )
    assert result is not None and result.verified is False
    assert result.summary.startswith("not attempted")
