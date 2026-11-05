"""ops/checks/owner_decision_record.py: a dated owner record whose ref resolves to OTHER content.

2026-11-05: TC-004's record lives inside docs/DECISION_LOG.md itself. Its own line contained its
anchor, so the record satisfied itself and the card's negative control ("ref=" -> "ref=BROKEN-")
could never break the check. The record's own line is no longer evidence for itself.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "ops" / "checks" / "owner_decision_record.py"


def run(cwd: Path, target: str, prefix: str) -> int:
    return subprocess.run(
        [sys.executable, str(CHECK), target, prefix], cwd=cwd, capture_output=True
    ).returncode


def repo(tmp_path: Path, log: str, other: str | None = None) -> Path:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "DECISION_LOG.md").write_text(log, encoding="utf-8")
    if other is not None:
        (tmp_path / "docs" / "OTHER.md").write_text(other, encoding="utf-8")
    return tmp_path


RULING = "## 2026-11-05: ruling\nAnchor: OWNER-RULING-X recorded here.\n"
RECORD = "OWNER_RULING: 2026-11-05 ref=OWNER-RULING-X\n"


def test_a_record_in_the_log_resolves_to_the_entry_it_names(tmp_path):
    root = repo(tmp_path, RULING + RECORD)
    assert run(root, "docs/DECISION_LOG.md", "OWNER_RULING:") == 0


def test_a_record_in_the_log_cannot_satisfy_itself(tmp_path):
    root = repo(tmp_path, "## nothing else\n" + RECORD)
    assert run(root, "docs/DECISION_LOG.md", "OWNER_RULING:") == 1


def test_the_negative_control_now_breaks_a_record_kept_in_the_log(tmp_path):
    mutated = (RULING + RECORD).replace("ref=", "ref=BROKEN-")
    root = repo(tmp_path, mutated)
    assert run(root, "docs/DECISION_LOG.md", "OWNER_RULING:") == 1


def test_a_record_in_another_file_still_resolves_against_the_log(tmp_path):
    root = repo(tmp_path, RULING, other=RECORD)
    assert run(root, "docs/OTHER.md", "OWNER_RULING:") == 0
    broken = repo(tmp_path / "b", RULING, other=RECORD.replace("ref=", "ref=BROKEN-"))
    assert run(broken, "docs/OTHER.md", "OWNER_RULING:") == 1
