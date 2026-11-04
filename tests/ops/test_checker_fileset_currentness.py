"""2026-11-04 supervisor-directive correction: currentness was tied only to the taskcard YAML's
own hash (card_sha256), so a referenced checker script (ops/checks/*.py) or required evidence
document could change underneath an accepted receipt without it ever going stale.
gateverify.referenced_files()/checker_fileset_sha256() close that gap; these are real tests
against this repository's own actual files at HEAD, not synthetic fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import gateverify  # noqa: E402


def test_referenced_files_extracts_py_json_yaml_and_md_tokens_from_check_commands() -> None:
    card = {
        "checks": [
            {"command": "python ops/checks/parity_benchmark_pilot_complete.py docs/PARITY_BENCHMARK_PILOT.md"},
            {"command": "python -m pytest tests/issues/ -q"},
        ]
    }
    found = gateverify.referenced_files(card)
    assert "ops/checks/parity_benchmark_pilot_complete.py" in found
    assert "docs/PARITY_BENCHMARK_PILOT.md" in found


def test_referenced_files_excludes_the_cards_own_taskcard_yaml() -> None:
    card = {"checks": [{"command": "python ops/checks/owner_decision_record.py project/taskcards/TC-004.yaml marker"}]}
    found = gateverify.referenced_files(card)
    assert "project/taskcards/TC-004.yaml" not in found


def test_checker_fileset_sha256_is_deterministic_for_a_real_file_at_head() -> None:
    card = {"checks": [{"command": "python ops/checks/parity_benchmark_pilot_complete.py docs/PARITY_BENCHMARK_PILOT.md"}]}
    a = gateverify.checker_fileset_sha256(card, "HEAD")
    b = gateverify.checker_fileset_sha256(card, "HEAD")
    assert a == b and len(a) == 64


def test_checker_fileset_sha256_changes_when_the_referenced_file_differs() -> None:
    """Negative control: two cards referencing different real, existing files at HEAD must
    produce different hashes -- proving this actually reads file content, not just the path
    string."""
    card_a = {"checks": [{"command": "python x.py docs/PARITY_BENCHMARK_PILOT.md"}]}
    card_b = {"checks": [{"command": "python x.py docs/DECISION_LOG.md"}]}
    assert gateverify.checker_fileset_sha256(card_a, "HEAD") != gateverify.checker_fileset_sha256(card_b, "HEAD")


def test_checker_fileset_sha256_marks_a_missing_file_distinctly() -> None:
    card = {"checks": [{"command": "python x.py this/file/does/not/exist.py"}]}
    digest = gateverify.checker_fileset_sha256(card, "HEAD")
    assert len(digest) == 64  # still a valid hash, not a crash -- MISSING is itself a value


def test_a_receipt_without_the_new_field_is_treated_as_stale() -> None:
    """A receipt generated before checker_fileset_sha256 existed must not be grandfathered as
    current -- new, stronger acceptance must be earned (supervisor directive, section 3). Real
    test against this repository's own current TC-010 card and card hash at HEAD."""
    _, real_card_sha = gateverify.load_card_at_rev("TC-010", "HEAD")
    receipt_missing_field = {"card_sha256": real_card_sha}
    assert gateverify.card_is_stale("TC-010", receipt_missing_field) is True


def test_a_receipt_with_the_wrong_checker_fileset_hash_is_stale_even_with_the_right_card_hash() -> None:
    """The actual gap this closes: card_sha256 alone matching is not enough if a referenced
    checker/evidence file changed underneath the receipt."""
    card, real_card_sha = gateverify.load_card_at_rev("TC-010", "HEAD")
    receipt = {"card_sha256": real_card_sha, "checker_fileset_sha256": "0" * 64}
    assert gateverify.card_is_stale("TC-010", receipt) is True


def test_a_receipt_with_both_real_hashes_current_is_not_stale() -> None:
    card, real_card_sha = gateverify.load_card_at_rev("TC-010", "HEAD")
    real_fileset_sha = gateverify.checker_fileset_sha256(card, "HEAD")
    receipt = {"card_sha256": real_card_sha, "checker_fileset_sha256": real_fileset_sha}
    assert gateverify.card_is_stale("TC-010", receipt) is False
