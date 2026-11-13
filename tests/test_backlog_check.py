"""R40: the backlog checker passes on the committed backlog and refuses done-without-evidence, duplicates and gaps."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("backlog_check", Path(__file__).resolve().parent.parent / "ops" / "checks" / "backlog_check.py")
bc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bc)  # type: ignore[union-attr]

GOOD = {"id": "BL-1", "title": "t", "type": "task", "source": "owner", "priority": "P1", "status": "open",
        "implementation_path": "p", "acceptance": "a", "evidence": []}


def test_the_committed_backlog_passes() -> None:
    assert bc.main() == 0


def test_done_without_evidence_is_refused() -> None:
    assert any("done without evidence" in p for p in bc.problems({"items": [dict(GOOD, status="done")]}))


def test_duplicates_unknown_dependencies_and_missing_fields_are_refused() -> None:
    found = bc.problems({"items": [GOOD, dict(GOOD), dict(GOOD, id="BL-2", source="", depends_on=["BL-9"])]})
    assert any("duplicate id BL-1" in p for p in found)
    assert any("BL-2: missing source" in p for p in found)
    assert any("unknown item BL-9" in p for p in found)
