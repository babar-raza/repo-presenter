"""gatectl.changed_paths/check_scope: a merge commit that introduces no content of its own (its
tree equals a parent that already contains every other parent -- GitHub's merge commit for a PR
whose base had not moved) is not an unattributed commit. Without this, every card re-verified
after a PR merge failed scope with "claims neither this card nor the supervisor" for a commit
that changes nothing. A merge that discards or combines content must still be flagged."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import gatectl

CARD = {"id": "TC-X", "gate": "G", "write_paths": ["notes/**"]}


def _repo(tmp_path, monkeypatch) -> callable:
    def g(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True,
                              text=True).stdout.strip()

    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "a.md").write_text("a\n")
    g("add", "notes/a.md")
    g("commit", "-q", "-m", "base")
    real_git = gatectl.git
    monkeypatch.setattr(gatectl, "git", lambda *a, cwd=None: real_git(*a, cwd=tmp_path))
    monkeypatch.setattr(gatectl, "commits_recorded_for", lambda cid: set())
    return g


def _tagged_branch(g, tmp_path, text="b\n"):
    g("checkout", "-q", "-b", "feature")
    (tmp_path / "notes" / "a.md").write_text(text)
    g("commit", "-q", "-am", "work (G/TC-X)")
    g("checkout", "-q", "main")


def test_a_noop_pr_merge_is_not_unattributed(tmp_path, monkeypatch):
    g = _repo(tmp_path, monkeypatch)
    base = g("rev-parse", "HEAD")
    _tagged_branch(g, tmp_path)
    g("merge", "-q", "--no-ff", "-m", "Merge pull request #1", "feature")
    assert gatectl.is_content_noop_merge("HEAD") is True
    ok, changed, violations = gatectl.check_scope(CARD, base, "HEAD")
    assert ok, violations
    assert changed == ["notes/a.md"]


def test_negative_control_a_content_discarding_merge_is_still_unattributed(tmp_path, monkeypatch):
    g = _repo(tmp_path, monkeypatch)
    base = g("rev-parse", "HEAD")
    _tagged_branch(g, tmp_path)
    g("merge", "-q", "--no-ff", "-s", "ours", "-m", "Merge discarding the work", "feature")
    assert gatectl.is_content_noop_merge("HEAD") is False
    ok, _, violations = gatectl.check_scope(CARD, base, "HEAD")
    assert not ok and any("claims neither" in v for v in violations), violations


def test_negative_control_a_two_sided_merge_is_still_unattributed(tmp_path, monkeypatch):
    g = _repo(tmp_path, monkeypatch)
    base = g("rev-parse", "HEAD")
    _tagged_branch(g, tmp_path)
    (tmp_path / "notes" / "c.md").write_text("main moved\n")
    g("add", "notes/c.md")
    g("commit", "-q", "-m", "main moved (G/TC-X)")
    g("merge", "-q", "--no-ff", "-m", "Merge pull request #2", "feature")
    assert gatectl.is_content_noop_merge("HEAD") is False
    ok, _, violations = gatectl.check_scope(CARD, base, "HEAD")
    assert not ok and any("claims neither" in v for v in violations), violations


def test_an_ordinary_commit_is_never_a_noop_merge(tmp_path, monkeypatch):
    g = _repo(tmp_path, monkeypatch)
    assert gatectl.is_content_noop_merge(g("rev-parse", "HEAD")) is False
