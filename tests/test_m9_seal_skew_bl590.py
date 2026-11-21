"""BL-590: the M9 audit re-derives a case from the seal its TEXT was taken from, not from the newest seal of the
revision.

Hosted round 44904444359 (audit seeded 12:32, audited ~16:00): PSD Python Lane R (a clean control, re-sealed 15:20)
had 13 lines flagged "no deterministic stage writes this line", OCR .NET (re-sealed 12:45) 6, every one a line the
NEWER seal's render does not reproduce under the older frozen text. Zero-call replay on the stored seals reproduces
exactly those lines (PSD Python [38-42, 291, 314, 318, ... 338]) with the newest seal and none with the seal the text
came from. Negative controls: a seeded text still picks its seal, and the seeded line is still underived; with one
seal, or with no text, the latest seal is used as before.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from repo_presenter.core.state.bundle_store import seal_matching_text

REPO = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auditor = _load("run_m9_auditor")
writer = _load("run_acceptance_writer")

OLD = "\n".join(f"line {n}" for n in range(1, 41)) + "\n"
NEW = OLD.replace("line 7\n", "line seven, refreshed\n").replace("line 30\n", "line thirty, refreshed\n")


def _seal(readme: str, commit: str, bundle: Path | None = Path("x")) -> SimpleNamespace:
    return SimpleNamespace(revision="r1", bundle=bundle, error="", commit=commit, readme=readme.encode())


def test_the_seal_the_text_was_taken_from_wins_over_a_newer_seal():
    old, new = _seal(OLD, "old"), _seal(NEW, "new")
    assert seal_matching_text([old, new], OLD) is old
    assert seal_matching_text([old, new], NEW) is new


def test_identical_readmes_take_the_latest():
    first, second = _seal(OLD, "a"), _seal(OLD, "b")
    assert seal_matching_text([first, second], OLD) is second


def test_a_seeded_text_picks_the_seal_it_differs_from_least():
    old, new = _seal(OLD, "old"), _seal(NEW, "new")
    seeded = OLD.replace("line 3\n", "line 3 It is an incredibly powerful solution.\n")
    assert seal_matching_text([old, new], seeded) is old
    seeded_new = NEW.replace("line 3\n", "line 3 It is an incredibly powerful solution.\n")
    assert seal_matching_text([old, new], seeded_new) is new


def test_a_tie_takes_the_latest_and_no_readme_is_none():
    a, b = _seal("x\n", "a"), _seal("y\n", "b")
    assert seal_matching_text([a, b], "z\n") is b
    assert seal_matching_text([SimpleNamespace(readme=None)], "z\n") is None
    assert seal_matching_text([], "z\n") is None


def test_the_auditor_binds_a_case_to_its_text_and_defaults_to_the_latest():
    old, new = _seal(OLD, "old"), _seal(NEW, "new")
    history = {("o/a", "R"): [old, new]}
    assert auditor.seal_for(history, "o/a", "R", "r1", OLD) is old
    assert auditor.seal_for(history, "o/a", "R", "r1", NEW) is new
    assert auditor.seal_for(history, "o/a", "R", "r1") is new  # no text: the seeder's rule, the latest
    assert auditor.seal_for({("o/a", "R"): [old]}, "o/a", "R", "r1", NEW) is old  # one seal: nothing to choose
    with pytest.raises(auditor.AuditError, match="no readable seal"):
        auditor.seal_for({("o/a", "R"): [_seal(OLD, "old", None)]}, "o/a", "R", "r1", OLD)


def test_the_writer_reads_the_evidence_of_the_seal_the_text_came_from(tmp_path, monkeypatch):
    from repo_presenter.core import facts as facts_module

    def bundle(name: str, readme: str) -> Path:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "README.md").write_text(readme, encoding="utf-8")
        return directory

    monkeypatch.setattr(facts_module, "read_facts", lambda path: SimpleNamespace(source=Path(path).parent.name))
    old = _seal(OLD, "old", bundle("old", OLD))
    new = _seal(NEW, "new", bundle("new", NEW))
    index = [{"case_id": "c1", "repository": "o/a", "lane": "L", "revision": "r1"}]
    history = {("o/a", "L"): [old, new]}
    certified = {("o/a", "L"): ("r1", True)}
    bound = writer.case_evidence(index, history, certified, texts={"c1": OLD})["c1"]
    assert bound.sealed == OLD and bound.facts.source == "old"
    latest = writer.case_evidence(index, history, certified)["c1"]
    assert latest.sealed == NEW and latest.facts.source == "new"
