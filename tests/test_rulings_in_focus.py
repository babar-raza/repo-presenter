"""Owner rulings stay in focus (2026-11-13): every session and agent must go through docs/RULINGS.md first.

Fails CI if the rulings file, its pointers at the top of AGENTS.md and CLAUDE.md, the SessionStart hook that prints
it, or any ruling recorded in the top authority goes missing from it."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULINGS = ROOT / "docs" / "RULINGS.md"


def test_the_rulings_file_exists_and_states_the_goal_and_checklist() -> None:
    text = " ".join(RULINGS.read_text(encoding="utf-8").replace("**", "").split())
    assert "at least 25 certified candidates in each lane" in text
    assert "Before you do anything, check" in text


def test_every_ruling_in_the_top_authority_is_in_the_rulings_file() -> None:
    goals = (ROOT / "docs" / "CONSOLIDATED_GOALS_2026-11-06.md").read_text(encoding="utf-8")
    ids = sorted({int(m) for m in re.findall(r"^\| R(\d+) \|", goals, re.M)})
    assert ids and ids[-1] >= 37
    text = RULINGS.read_text(encoding="utf-8")
    missing = [f"R{i}" for i in ids if not re.search(rf"\bR{i}\b", text)]
    assert not missing, f"rulings missing from docs/RULINGS.md: {missing}"


def test_agents_and_claude_md_point_to_the_rulings_first() -> None:
    for name in ("AGENTS.md", "CLAUDE.md"):
        head = "\n".join((ROOT / name).read_text(encoding="utf-8").splitlines()[:6])
        assert "docs/RULINGS.md" in head, f"{name} must reference docs/RULINGS.md in its first lines"


def test_every_session_starts_by_printing_the_rulings() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        hook.get("command", "")
        for group in settings.get("hooks", {}).get("SessionStart", [])
        for hook in group.get("hooks", [])
    ]
    assert any("docs/RULINGS.md" in command for command in commands)
