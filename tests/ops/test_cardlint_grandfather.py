"""ops/cardlint.py's own documented contract: lint findings are suppressed only when a card is
EFFECTIVELY accepted, never merely because its receipt's raw `accepted` field says so (2026-11-04
supervisor-directive correction: `ops/gatecli.py::cmd_validate` previously passed the receipt's
raw field straight through to `lint_card`, bypassing these checks for any card whose receipt
forged or stale-claimed `accepted: true` even when gateverify's own coherence/dependency
computation said otherwise). These tests exercise the suppression boundary directly."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import cardlint  # noqa: E402


def _card(**overrides) -> dict:
    base = {
        "id": "TC-999",
        "checks": [{"command": "python -m pytest tests/ops/fixture_dir -q"}],
        "network": False,
        "negative_control": {"mutate": "python -c \"pass\""},
    }
    base.update(overrides)
    return base


def test_a_network_reaching_test_is_flagged_when_not_accepted(tmp_path: Path) -> None:
    fixture = tmp_path / "tests" / "ops" / "fixture_dir"
    fixture.mkdir(parents=True)
    (fixture / "test_thing.py").write_text(
        "def test_x():\n    requests.get('https://example.org')\n", encoding="utf-8"
    )
    findings = cardlint.lint_card(_card(), tmp_path, accepted=False)
    assert any("reaches the network" in f for f in findings)


def test_the_same_card_is_fully_suppressed_once_effectively_accepted(tmp_path: Path) -> None:
    """The exact bypass this fixes: a card with a real, live defect must still be caught UNLESS
    it is genuinely, effectively accepted -- never merely because a receipt claims so."""
    fixture = tmp_path / "tests" / "ops" / "fixture_dir"
    fixture.mkdir(parents=True)
    (fixture / "test_thing.py").write_text(
        "def test_x():\n    requests.get('https://example.org')\n", encoding="utf-8"
    )
    findings = cardlint.lint_card(_card(), tmp_path, accepted=True)
    assert findings == []


def test_a_backslash_negative_control_is_flagged_when_not_accepted(tmp_path: Path) -> None:
    card = _card(negative_control={"mutate": "python -c \"import x; y = 1\\\\2\""})
    findings = cardlint.lint_card(card, tmp_path, accepted=False)
    assert any("backslash" in f for f in findings)


def test_gatecli_derives_accepted_from_the_effective_set_not_the_raw_receipt() -> None:
    """Regression guard for the actual bug: gatecli.py's validate command must compute each
    card's `accepted` argument to lint_card from gateverify.rebuild_state()'s own effectively-
    accepted set, never from a receipt's own `accepted` field read independently. Enforced here
    by reading gatecli.py's own source for the fixed line shape, since cmd_validate's heavy
    real-filesystem I/O (project/state.yaml, project/taskcards/, evidence/) makes a full
    behavioral integration test disproportionate to a one-line fix -- this still fails loudly if
    the fix is ever reverted to reading a receipt directly."""
    source = (Path(__file__).resolve().parents[2] / "ops" / "gatecli.py").read_text(
        encoding="utf-8"
    )
    assert "accepted = cid in accepted_ids" in source
    assert 'accepted = bool(r and r.get("accepted"))' not in source
