"""TC-013 action item 5 / owner ruling R10: ``data/reviewer_calibration.json`` is frozen at
iteration 5 (status NOT_PASSED) and nothing this repository ships may ever write PASSED into it
again. This package never touches that file at all (it reads/writes its OWN, separate
``data/acceptance_calibration.json``) - asserted here the same way
``tests/readme/review/test_calibration_status.py`` already asserts no source file writes it."""

from __future__ import annotations

import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "repo_presenter"
DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "reviewer_calibration.json"

_WRITERS = re.compile(r"write_text|write_bytes|\.write\(|json\.dump\(|open\([^)]*['\"][wax]\+?b?['\"]")


def test_no_source_file_writes_the_frozen_reviewer_calibration_file() -> None:
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "reviewer_calibration" not in text:
            continue
        if _WRITERS.search(text):
            offenders.append(path.relative_to(SRC).as_posix())
    assert offenders == []


_IMPORTS_THE_FROZEN_READER = re.compile(
    r"^\s*(?:from|import)\s+[\w.]*calibration_status", re.MULTILINE
)


def test_this_cards_own_acceptance_package_never_imports_the_frozen_reader() -> None:
    """record.py builds a NEW, parallel contract - it never imports the frozen
    ``readme.review.calibration_status`` reader module (mentioning it by name in a docstring,
    to explain what is being replaced, is fine; importing or calling it is not)."""
    acceptance_dir = SRC / "acceptance"
    for path in acceptance_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not _IMPORTS_THE_FROZEN_READER.search(text), path
        assert "load_calibration(" not in text


def test_the_committed_frozen_file_is_still_status_not_passed_at_iteration_5() -> None:
    """A guard, not a new requirement: this card's closeout promises the frozen file is
    "unchanged and untouched by this card" - if some other, unrelated change ever flips it to
    PASSED, that is the exact outcome R10 forbids, and this test fails loudly either way."""
    document = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert document["status"] != "PASSED"


def test_propose_effect_no_longer_imports_the_frozen_reader() -> None:
    """Gate 3b (TC-013) now reads the acceptance contract instead of
    readme.review.calibration_status.load_calibration - the frozen reader is no longer imported
    by the one write effect this repository has (mentioning the old module by name in a comment,
    to document what was replaced, is fine; importing or calling it is not)."""
    effect_path = SRC / "propose" / "effect.py"
    text = effect_path.read_text(encoding="utf-8")
    assert not _IMPORTS_THE_FROZEN_READER.search(text)
    assert "load_calibration(" not in text
    assert "from repo_presenter.acceptance.record import" in text
