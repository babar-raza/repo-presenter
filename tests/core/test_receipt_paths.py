"""A receipt never carries the machine that produced it, and never loses the diagnostic."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.receipt_paths import scrub_machine_paths

HOSTED = (
    "/home/runner/work/repo-presenter/repo-presenter/Program.cs(3,41): error CS1503: "
    "Argument 2: cannot convert from 'Aspose.ThreeD.FileFormat' to "
    "'System.Threading.CancellationToken'"
)
CLEAN = (
    "Program.cs(3,41): error CS1503: Argument 2: cannot convert from "
    "'Aspose.ThreeD.FileFormat' to 'System.Threading.CancellationToken'"
)


def test_the_hosted_runner_path_reduces_to_the_file_line_and_column() -> None:
    assert scrub_machine_paths(HOSTED) == CLEAN


def test_a_runner_path_goes_even_when_no_caller_named_it() -> None:
    for prefix in (
        "/home/runner/work/_temp/abc/example_003/",
        "/tmp/pytest-of-user/pytest-0/run/",
        "/Users/someone/Library/Caches/",
        "/private/var/folders/xy/T/",
        "/github/workspace/",
    ):
        assert scrub_machine_paths(f"{prefix}Program.cs(3,41): error CS1503: x") == (
            "Program.cs(3,41): error CS1503: x"
        )


@pytest.mark.parametrize(
    "path",
    [
        "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\run\\example_003\\",
        "D:/a/repo-presenter/repo-presenter/",
        "c:\\Users\\Some.One\\runs\\",
        "C:\\\\Users\\\\babar\\\\run\\\\",
        "\\\\?\\C:\\Users\\babar\\very\\deep\\",
    ],
)
def test_a_windows_path_in_either_spelling_goes(path: str) -> None:
    assert scrub_machine_paths(f"{path}Program.cs(1,9): error CS0246: x") == (
        "Program.cs(1,9): error CS0246: x"
    )


def test_a_named_base_goes_in_every_spelling_longest_first(tmp_path: Path) -> None:
    checkout = tmp_path / "work" / "repo"
    run_dir = checkout / "runs" / "example_001"
    run_dir.mkdir(parents=True)
    for printed in (
        str(run_dir),
        run_dir.as_posix(),
        str(run_dir.resolve()),
        str(run_dir).replace("\\", "/").replace("/", "\\"),
    ):
        separator = chr(92) if chr(92) in printed else "/"
        text = f"{printed}{separator}Program.cs(1,9): error CS1: x"
        assert scrub_machine_paths(text, run_dir, checkout) == (
            "Program.cs(1,9): error CS1: x"
        )


def test_a_relative_base_no_longer_leaves_the_working_directory_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hosted run 40474666141: the run directory was relative, so removing its relative
    spelling first left the checkout root in front of the file name."""
    monkeypatch.chdir(tmp_path)
    relative = Path("runs") / "example_003"
    (tmp_path / relative).mkdir(parents=True)
    printed = (tmp_path / relative).resolve() / "Program.cs"
    for _ in range(3):
        assert (
            scrub_machine_paths(f"{printed}(3,41): error CS1503: x", relative)
            == "Program.cs(3,41): error CS1503: x"
        )


def test_the_part_of_a_path_below_a_named_base_is_kept(tmp_path: Path) -> None:
    checkout = tmp_path / "work" / "repo"
    checkout.mkdir(parents=True)
    text = f"{checkout / 'src' / 'Widget.cs'}(4,2): error CS0103: x"
    scrubbed = scrub_machine_paths(text, checkout)
    assert scrubbed.replace(chr(92), "/") == "src/Widget.cs(4,2): error CS0103: x"


@pytest.mark.parametrize(
    "text",
    [
        "Program.cs(3,41): error CS1503: Argument 2: cannot convert from 'string' to 'int'",
        "Program.cs(1,9): error CS0246: The type or namespace name 'Widget' could not be found",
        "error CS1002: ; expected",
        "Build FAILED.\n    0 Warning(s)\n    1 Error(s)",
        "error CS0019: Operator '/' cannot be applied to operands of type 'int' and 'string'",
        "warning: see https://learn.microsoft.com/dotnet/csharp/language-reference/error/cs0246",
        "Use either System.IO/Path or System.Text and/or System.Linq",
        "",
    ],
)
def test_text_without_a_machine_path_is_unchanged(text: str) -> None:
    assert scrub_machine_paths(text) == text


def test_an_error_code_and_message_survive_scrubbing_in_every_shape(
    tmp_path: Path,
) -> None:
    message = "error CS1503: Argument 2: cannot convert from 'A.B' to 'C.D'"
    for prefix in (
        "/home/runner/work/r/r/",
        "C:\\Users\\x\\r\\",
        f"{tmp_path.as_posix()}/",
    ):
        scrubbed = scrub_machine_paths(f"{prefix}Program.cs(3,41): {message}", tmp_path)
        assert scrubbed == f"Program.cs(3,41): {message}"


def test_every_ecosystem_verifier_reduces_a_checkout_path_to_the_file_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repo_presenter.extractors.platforms import (
        cpp_examples,
        go_examples,
        java_examples,
        net_examples,
        python_examples,
        rust_examples,
    )
    from repo_presenter.extractors.surface import npm_build

    monkeypatch.chdir(tmp_path)
    run = Path("runs") / "example_001"
    noisy = "/home/runner/work/repo-presenter/repo-presenter/main.go:3:5: undefined: x"
    expected = "main.go:3:5: undefined: x"
    assert go_examples._scrub(noisy, run, tmp_path) == expected
    assert rust_examples._scrub(noisy, run) == expected
    assert java_examples._scrub(noisy, run, tmp_path) == expected
    assert cpp_examples._scrub(noisy, run, tmp_path) == expected
    assert npm_build.scrub(noisy, run) == expected
    assert net_examples._scrub(noisy, run) == expected
    assert python_examples._redact(noisy, run, tmp_path) == expected
    resolved = (tmp_path / run).resolve().as_posix()
    assert python_examples._redact(f"File {resolved}/example.py", run) == (
        "File <workspace>/example.py"
    )
