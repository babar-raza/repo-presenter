"""Scheme v2 of gateverify.checker_fileset_sha256: a file consumed only through marker_check.py is
hashed as the marker lines it consumes. Unrelated appends (an append-only decision log) must not
stale an acceptance that never read them; changing the consumed marker must. Scheme v1 (whole
file) is kept for receipts written before v2 and is the negative control here."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import gateverify

CARD = {"checks": [{"command": 'python ops/checks/marker_check.py docs/LOG.md "DECISION_X:"'}]}
BASE = "intro\nDECISION_X: adopted\nolder entry\n"


def _with_files(monkeypatch, files: dict[str, str]) -> None:
    def fake_git(*args):
        if args[0] == "show":
            path = args[1].split(":", 1)[1]
            if path in files:
                return 0, files[path], ""
            return 128, "", "missing"
        raise AssertionError(args)

    monkeypatch.setattr(gateverify, "git", fake_git)


def digest(monkeypatch, text, scheme):
    _with_files(monkeypatch, {"docs/LOG.md": text})
    return gateverify.checker_fileset_sha256(CARD, "HEAD", scheme)


def test_v2_ignores_an_unrelated_append(monkeypatch):
    assert digest(monkeypatch, BASE, "v2") == digest(monkeypatch, BASE + "\nnew unrelated decision\n", "v2")


def test_v1_whole_file_hash_would_have_gone_stale_on_that_append(monkeypatch):
    """Negative control: this is the defect v2 removes."""
    assert digest(monkeypatch, BASE, "v1") != digest(monkeypatch, BASE + "\nnew unrelated decision\n", "v1")


def test_v2_changes_when_the_marker_line_is_removed(monkeypatch):
    assert digest(monkeypatch, BASE, "v2") != digest(monkeypatch, "intro\nolder entry\n", "v2")


def test_v2_changes_when_the_marker_line_text_is_altered(monkeypatch):
    assert digest(monkeypatch, BASE, "v2") != digest(monkeypatch, BASE.replace("adopted", "REVOKED"), "v2")


def test_v2_changes_when_the_marker_is_duplicated(monkeypatch):
    assert digest(monkeypatch, BASE, "v2") != digest(monkeypatch, BASE + "DECISION_X: again\n", "v2")


def test_v2_missing_file_is_distinct(monkeypatch):
    _with_files(monkeypatch, {})
    missing = gateverify.checker_fileset_sha256(CARD, "HEAD", "v2")
    assert missing != digest(monkeypatch, BASE, "v2")


def test_a_file_also_read_by_another_check_is_still_hashed_whole(monkeypatch):
    card = {
        "checks": [
            {"command": 'python ops/checks/marker_check.py docs/LOG.md "DECISION_X:"'},
            {"command": "python ops/checks/other.py docs/LOG.md"},
        ]
    }
    _with_files(monkeypatch, {"docs/LOG.md": BASE, "ops/checks/other.py": "x"})
    a = gateverify.checker_fileset_sha256(card, "HEAD", "v2")
    _with_files(monkeypatch, {"docs/LOG.md": BASE + "unrelated\n", "ops/checks/other.py": "x"})
    assert a != gateverify.checker_fileset_sha256(card, "HEAD", "v2")


def test_a_legacy_receipt_is_compared_with_the_v1_scheme(monkeypatch):
    _with_files(monkeypatch, {"docs/LOG.md": BASE})
    monkeypatch.setattr(gateverify, "load_card_at_rev", lambda cid, rev: (CARD, "cardsha"))
    v1 = gateverify.checker_fileset_sha256(CARD, "HEAD", "v1")
    receipt = {"card_sha256": "cardsha", "checker_fileset_sha256": v1}  # no scheme field -> v1
    assert gateverify.card_is_stale("X", receipt) is False
    _with_files(monkeypatch, {"docs/LOG.md": BASE + "append\n"})
    assert gateverify.card_is_stale("X", receipt) is True
    v2 = gateverify.checker_fileset_sha256(CARD, "HEAD", "v2")
    fresh = {"card_sha256": "cardsha", "checker_fileset_sha256": v2, "checker_fileset_scheme": "v2"}
    _with_files(monkeypatch, {"docs/LOG.md": BASE + "append\nmore\n"})
    assert gateverify.card_is_stale("X", fresh) is False
