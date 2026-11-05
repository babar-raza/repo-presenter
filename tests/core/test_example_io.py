"""Input-vs-output file literals (core/example_io.py, ported from aspose.org's example
verification). 2026-11-05: a fixture staged under a literal the example WRITES made Aspose.PDF for
Python's ``document.save("hello.pdf")`` raise FileExistsError -- 19 of that README's 37 CONTRADICTED
examples."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.example_io import input_fixture_names, literal_roles
from repo_presenter.extractors.platforms.python_examples import stage_fixtures

HELLO = (
    "from aspose_pdf import Document, PageSize\n\n"
    "with Document() as document:\n"
    "    page = document.pages.add(PageSize.A4)\n"
    '    document.save("hello.pdf")\n'
)


def test_a_saved_file_is_an_output_and_an_opened_one_an_input():
    code = 'doc = Document("input.pdf")\nwb = load_workbook("data.xlsx")\ndoc.save("out.pdf")\n'
    assert input_fixture_names(code) == ["input.pdf", "data.xlsx"]
    assert literal_roles(code)["out.pdf"] == {"output"}


def test_a_name_both_read_and_written_is_never_staged():
    code = 'doc = Document("report.pdf")\ndoc.save("report.pdf")\n'
    assert input_fixture_names(code) == []


def test_an_unclassifiable_literal_is_not_guessed():
    assert input_fixture_names('path = "sample.pdf"\n') == []
    assert literal_roles('path = "sample.pdf"\n')["sample.pdf"] == {"unknown"}


def test_words_match_whole_not_as_substrings():
    # "target" contains "get", "address" contains "add": neither makes the literal an input.
    assert input_fixture_names('target_address = "x.pdf"\n') == []


def test_absolute_and_parent_paths_are_dropped():
    assert input_fixture_names('open("/etc/x.txt")\nopen("../y.txt")\nopen("z.txt")\n') == ["z.txt"]


def _tree(tmp_path: Path) -> tuple[Path, list[str]]:
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "sample.pdf").write_bytes(b"%PDF-1.4 sample")
    return root, ["tests/sample.pdf"]


def test_the_verifier_no_longer_stages_a_file_the_example_creates(tmp_path):
    root, tree = _tree(tmp_path)
    work = tmp_path / "run"
    work.mkdir()
    assert stage_fixtures(HELLO, root, tree, work) == []
    assert not (work / "hello.pdf").exists()


def test_the_verifier_still_stages_a_file_the_example_opens(tmp_path):
    root, tree = _tree(tmp_path)
    work = tmp_path / "run"
    work.mkdir()
    bindings = stage_fixtures('doc = Document("input.pdf")\ndoc.save("out.pdf")\n', root, tree, work)
    assert [b.literal for b in bindings] == ["input.pdf"]
    assert (work / "input.pdf").read_bytes() == b"%PDF-1.4 sample"
    assert not (work / "out.pdf").exists()


def test_a_python_constructor_taking_the_literal_reads_it():
    assert input_fixture_names('doc = Document("input.pdf")\n') == ["input.pdf"]
    assert input_fixture_names('doc = ap.Document("input.pdf")\n') == ["input.pdf"]
    # ... but not when the capitalised call is a save target or the literal is not its argument.
    assert input_fixture_names('Document().save("out.pdf")\n') == []


def test_files_opened_for_writing_or_created_are_outputs():
    # Each was classified INPUT by the rules as ported (findings reported to aspose.org).
    for code in (
        'with open("out.txt", "w") as f:\n    f.write("x")\n',
        'with open("log.txt", mode="a") as f:\n    pass\n',
        'Writer w = new FileWriter("out.txt");\n',
        'let f = File::create("out.txt")?;\n',
        'f, _ := os.Create("out.xlsx")\n',
    ):
        assert input_fixture_names(code) == [], code
    assert input_fixture_names('with open("in.txt") as f:\n    f.read()\n') == ["in.txt"]
    assert input_fixture_names('with open("in.bin", "rb") as f:\n    pass\n') == ["in.bin"]


def test_the_aspose_org_original_misclassifies_exactly_as_reported(monkeypatch):
    """docs/ASPOSE_ORG_EXAMPLE_VERIFIER_FINDINGS.md: with this port's local fixes switched off the
    rules are aspose.org's, and each reported finding reproduces."""
    import re

    from repo_presenter.core import example_io

    monkeypatch.setattr(
        example_io,
        "_OUTPUT_WORDS",
        frozenset({"save", "write", "export", "output", "dump", "store"}),
    )
    monkeypatch.setattr(example_io, "_CONSTRUCTOR_CALL", re.compile(r"(?!)"))
    monkeypatch.setattr(example_io, "_OPEN_CALL", re.compile(r"(?!)"))
    roles = example_io.literal_roles
    assert roles('Writer w = new FileWriter("out.txt");\n') == {"out.txt": {"input"}}  # 1
    assert roles('let f = File::create("out.txt")?;\n') == {"out.txt": {"input"}}  # 2
    assert roles('with open("out.txt", "w") as f:\n    pass\n') == {"out.txt": {"input"}}  # 3
    assert roles('doc = Document("in.pdf")\n') == {"in.pdf": {"unknown"}}  # 4
    assert roles('doc.save(\n    "out.pdf",\n)\n') == {"out.pdf": {"unknown"}}  # 5


def test_the_verifier_still_stages_what_it_cannot_classify(tmp_path):
    """The four examples the stricter aspose.org rule regressed (measured 2026-11-05): an
    unclassifiable literal is still staged; only a written one never is."""
    root, tree = _tree(tmp_path)
    for code, wanted in (
        ('with PdfExtractor() as e:\n    e.bind_pdf("input.pdf")\n', ["input.pdf"]),
        ('editor.concatenate(["part-1.pdf", "part-2.pdf"], "merged.pdf")\n',
         ["part-1.pdf", "part-2.pdf", "merged.pdf"]),
        (
            (
                'for path in ("report.pdf", "legacy.pdf"):\n    doc = aw.Document(path)\n'
                '    doc.save(f"{path}.out", aw.SaveFormat.PDF)\n'
            ),
            ["report.pdf", "legacy.pdf"],
        ),
    ):
        work = tmp_path / f"run{len(wanted)}{len(code)}"
        work.mkdir()
        staged = {b.literal for b in stage_fixtures(code, root, tree, work)}
        assert staged == set(wanted), code


def test_a_failure_on_a_substitute_input_is_inconclusive_not_a_contradiction():
    """2026-11-05: an example given the smallest repository PDF in place of its ``template.pdf``
    failed with KeyError and was recorded CONTRADICTED; issue discovery would have proposed it."""
    from repo_presenter.core.examples import FixtureBinding
    from repo_presenter.extractors.platforms.python_examples import (
        _substitute_inconclusive,
    )

    substitute = FixtureBinding("template.pdf", "tests/sample.pdf")
    same_name = FixtureBinding("template.pdf", "tests/template.pdf")
    produced = FixtureBinding("overview.png", "page-1.png", produced_by=8)

    outcome, detail = _substitute_inconclusive("FAILED", "KeyError", [substitute])
    assert outcome == "NEEDS_INPUT" and "tests/sample.pdf for template.pdf" in detail
    assert _substitute_inconclusive("FAILED", "KeyError", [produced])[0] == "NEEDS_INPUT"
    # The example's own named file, or no fixture at all: a real failure stays a failure.
    assert _substitute_inconclusive("FAILED", "KeyError", [same_name]) == ("FAILED", "KeyError")
    assert _substitute_inconclusive("FAILED", "KeyError", []) == ("FAILED", "KeyError")
    # An error no input can cause stays a failure even on a substitute.
    assert _substitute_inconclusive("FAILED", "NameError", [substitute]) == ("FAILED", "NameError")
    # Only failures are reconsidered.
    assert _substitute_inconclusive("EXECUTED", "exit 0", [substitute]) == ("EXECUTED", "exit 0")
