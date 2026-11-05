"""Scheme v3 of gateverify.checker_fileset_sha256: a file consumed only through
owner_decision_record.py is hashed as the lines that check consumes -- the PREFIX lines of its
target, plus the docs/DECISION_LOG.md lines containing the record's ref= anchor (resolved at the
hashed revision). Unrelated appended decision-log entries must not stale an acceptance that never
read them (TC-004 keeps its record in the decision log itself); removing, altering or
duplicating the record or its referenced entry must. Schemes v1/v2 (target hashed whole, decision
log not hashed at all unless named) are kept for older receipts and are the negative control."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import gateverify

LOG = "docs/DECISION_LOG.md"
SCRIPT = "ops/checks/owner_decision_record.py"
IN_LOG = {"checks": [{"command": f"python {SCRIPT} {LOG} RULING_X:"}]}
ELSEWHERE = {"checks": [{"command": f"python {SCRIPT} docs/INVENTORY.md DISPOSITION_X:"}]}
ENTRY = "## 2026-11-05: owner decisions (ANCHOR-X)\nbody of the referenced entry\n"
LOG_BASE = "intro\n" + ENTRY + "RULING_X: 2026-11-05 ref=ANCHOR-X\nolder entry\n"
INV_BASE = "inventory\nDISPOSITION_X: 2026-11-05 ref=ANCHOR-X\nmore inventory\n"
SEPARATE_LOG = "intro\n" + ENTRY + "older entry\n"


def _with_files(monkeypatch, files: dict[str, str]) -> None:
    files = {SCRIPT: "checker source", **files}

    def fake_git(*args):
        if args[0] == "show":
            path = args[1].split(":", 1)[1]
            if path in files:
                return 0, files[path], ""
            return 128, "", "missing"
        raise AssertionError(args)

    monkeypatch.setattr(gateverify, "git", fake_git)


def digest(monkeypatch, card, files, scheme="v3"):
    _with_files(monkeypatch, files)
    return gateverify.checker_fileset_sha256(card, "HEAD", scheme)


def in_log(monkeypatch, text, scheme="v3"):
    return digest(monkeypatch, IN_LOG, {LOG: text}, scheme)


def elsewhere(monkeypatch, inv, log, scheme="v3"):
    return digest(monkeypatch, ELSEWHERE, {"docs/INVENTORY.md": inv, LOG: log}, scheme)


# --- record kept in the decision log itself (TC-004's shape) ---------------------------------


def test_v3_ignores_an_unrelated_appended_entry(monkeypatch):
    assert in_log(monkeypatch, LOG_BASE) == in_log(monkeypatch, LOG_BASE + "\n## 2026-11-06: unrelated\n")


def test_v2_whole_file_hash_would_have_gone_stale_on_that_append(monkeypatch):
    """Negative control: this is the defect v3 removes."""
    assert in_log(monkeypatch, LOG_BASE, "v2") != in_log(monkeypatch, LOG_BASE + "\n## unrelated\n", "v2")


def test_v3_changes_when_the_record_is_removed(monkeypatch):
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, LOG_BASE.replace("RULING_X: 2026-11-05 ref=ANCHOR-X\n", ""))


def test_v3_changes_when_the_record_is_altered(monkeypatch):
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, LOG_BASE.replace("2026-11-05 ref", "2026-11-04 ref"))
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, LOG_BASE.replace("ref=", "ref=BROKEN-"))


def test_v3_changes_when_the_record_is_duplicated(monkeypatch):
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, LOG_BASE + "RULING_X: 2026-11-05 ref=ANCHOR-X\n")


def test_falsifier_an_altered_anchor_line_changes_the_digest(monkeypatch):
    """The referenced entry's own anchor line is consumed: rewording it must stale the receipt."""
    altered = LOG_BASE.replace("owner decisions (ANCHOR-X)", "owner decisions REVOKED (ANCHOR-X)")
    assert altered != LOG_BASE
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, altered)


def test_v3_changes_when_the_anchor_line_is_removed_or_duplicated(monkeypatch):
    removed = LOG_BASE.replace("## 2026-11-05: owner decisions (ANCHOR-X)\n", "")
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, removed)
    assert in_log(monkeypatch, LOG_BASE) != in_log(monkeypatch, LOG_BASE + "see also ANCHOR-X\n")


# --- record kept in a separate target file (TC-002's shape) ----------------------------------


def test_v3_separate_target_ignores_unrelated_edits_to_either_file(monkeypatch):
    a = elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG)
    assert a == elsewhere(monkeypatch, INV_BASE + "unrelated inventory row\n", SEPARATE_LOG)
    assert a == elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG + "## 2026-11-06: unrelated\n")


def test_v3_separate_target_record_changes_change_the_digest(monkeypatch):
    a = elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG)
    assert a != elsewhere(monkeypatch, INV_BASE.replace("DISPOSITION_X: 2026-11-05 ref=ANCHOR-X\n", ""), SEPARATE_LOG)
    assert a != elsewhere(monkeypatch, INV_BASE.replace("ref=", "ref=BROKEN-"), SEPARATE_LOG)
    assert a != elsewhere(monkeypatch, INV_BASE + "DISPOSITION_X: 2026-11-05 ref=ANCHOR-X\n", SEPARATE_LOG)


def test_v3_separate_target_consumes_the_decision_log_anchor_even_though_no_command_names_it(monkeypatch):
    altered = SEPARATE_LOG.replace("owner decisions (ANCHOR-X)", "owner decisions REVOKED (ANCHOR-X)")
    assert elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG) != elsewhere(monkeypatch, INV_BASE, altered)
    missing = digest(monkeypatch, ELSEWHERE, {"docs/INVENTORY.md": INV_BASE})
    assert missing != elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG)


def test_v2_never_noticed_the_referenced_entry_changing(monkeypatch):
    """Negative control: under v2 a separate-target record's decision-log entry was not hashed."""
    altered = SEPARATE_LOG.replace("owner decisions (ANCHOR-X)", "owner decisions REVOKED (ANCHOR-X)")
    assert elsewhere(monkeypatch, INV_BASE, SEPARATE_LOG, "v2") == elsewhere(monkeypatch, INV_BASE, altered, "v2")


def test_the_anchor_is_resolved_at_the_hashed_revision(monkeypatch):
    """Repointing ref= to another real entry changes which decision-log lines are consumed."""
    log = SEPARATE_LOG + "## 2026-11-06: other decision (ANCHOR-Y)\n"
    a = elsewhere(monkeypatch, INV_BASE, log)
    b = elsewhere(monkeypatch, INV_BASE.replace("ANCHOR-X", "ANCHOR-Y"), log)
    assert a != b
    edited_y = log.replace("other decision (ANCHOR-Y)", "other decision, amended (ANCHOR-Y)")
    assert b != elsewhere(monkeypatch, INV_BASE.replace("ANCHOR-X", "ANCHOR-Y"), edited_y)
    assert a == elsewhere(monkeypatch, INV_BASE, edited_y)


def test_the_checker_script_itself_is_still_hashed_whole(monkeypatch):
    a = in_log(monkeypatch, LOG_BASE)
    _with_files(monkeypatch, {LOG: LOG_BASE, SCRIPT: "checker source, weakened"})
    assert a != gateverify.checker_fileset_sha256(IN_LOG, "HEAD", "v3")


def test_a_file_also_read_by_another_check_is_still_hashed_whole(monkeypatch):
    card = {"checks": IN_LOG["checks"] + [{"command": f"python ops/checks/other.py {LOG}"}]}
    a = digest(monkeypatch, card, {LOG: LOG_BASE, "ops/checks/other.py": "x"})
    assert a != digest(monkeypatch, card, {LOG: LOG_BASE + "unrelated\n", "ops/checks/other.py": "x"})


def test_marker_checks_keep_their_line_wise_treatment_under_v3(monkeypatch):
    card = {"checks": [{"command": f'python ops/checks/marker_check.py {LOG} "DECISION_Y:"'}]}
    base = "intro\nDECISION_Y: adopted\n"
    assert digest(monkeypatch, card, {LOG: base}) == digest(monkeypatch, card, {LOG: base + "unrelated\n"})
    assert digest(monkeypatch, card, {LOG: base}) != digest(monkeypatch, card, {LOG: base.replace("adopted", "REVOKED")})


def test_v2_receipts_are_still_compared_with_the_v2_scheme(monkeypatch):
    _with_files(monkeypatch, {LOG: LOG_BASE})
    monkeypatch.setattr(gateverify, "load_card_at_rev", lambda cid, rev: (IN_LOG, "cardsha"))
    v2 = gateverify.checker_fileset_sha256(IN_LOG, "HEAD", "v2")
    receipt = {"card_sha256": "cardsha", "checker_fileset_sha256": v2, "checker_fileset_scheme": "v2"}
    assert gateverify.card_is_stale("X", receipt) is False
    _with_files(monkeypatch, {LOG: LOG_BASE + "append\n"})
    assert gateverify.card_is_stale("X", receipt) is True
    v3 = gateverify.checker_fileset_sha256(IN_LOG, "HEAD", "v3")
    fresh = {"card_sha256": "cardsha", "checker_fileset_sha256": v3, "checker_fileset_scheme": "v3"}
    _with_files(monkeypatch, {LOG: LOG_BASE + "append\nmore\n"})
    assert gateverify.card_is_stale("X", fresh) is False
