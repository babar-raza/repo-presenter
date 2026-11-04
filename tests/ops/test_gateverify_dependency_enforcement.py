"""Real negative-control tests for the 2026-11-04 state-machine corrections to
ops/gateverify.py, demanded directly by the owner's directive: an accepted-looking receipt must
not bypass a blocked prerequisite; a card must not depend on itself; cycles and missing
dependency IDs must be rejected; previously-accepted downstream cards must lose eligibility when
a required upstream gate is genuinely invalidated (superseded); and the READY/IN_PROGRESS
deadlock (a diagnostic verify run permanently blocking a card that was never actually dispatched)
must be fixed without stranding real in-progress work.

compute_rows()/find_dependency_graph_problems()/find_duplicate_card_ids() are pure functions
(no git, no filesystem beyond what's passed in), extracted specifically so these can run against
synthetic cards/receipts without touching this repository's own real taskcards or git state.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))

import gateverify  # noqa: E402


def card(cid: str, depends_on: list[str] | None = None, requires_owner_decision: bool = False) -> dict:
    return {"id": cid, "gate": "G", "depends_on": depends_on or [],
            "requires_owner_decision": requires_owner_decision}


def receipt(accepted: bool, card_sha256: str = "sha-current", reason: str = "", head_rev: str = "deadbeef"):
    return {"accepted": accepted, "card_sha256": card_sha256, "reason": reason,
            "head_rev": head_rev, "gate": "G", "generated_at": "2026-11-04T00:00:00Z"}


def raw_for(receipts: dict[str, dict | None], stale: set[str] | None = None, attempts: dict[str, int] | None = None):
    stale = stale or set()
    attempts = attempts or {}
    return {
        cid: {"receipt": r, "attempt": attempts.get(cid, 0), "stale": cid in stale}
        for cid, r in receipts.items()
    }


# --------------------------------------------------------------------------
# dependency enforcement before acceptance -- the core defect report
# --------------------------------------------------------------------------
def test_accepted_receipt_cannot_bypass_unmet_prerequisite():
    """TC-A depends on TC-B. TC-A's OWN receipt claims accepted=True (simulating a forged or
    stale-but-genuinely-positive receipt). TC-B has no accepting receipt at all. TC-A must NOT
    be ACCEPTED -- this is the exact defect the directive reported as confirmed, not theoretical."""
    cards = {"TC-A": card("TC-A", depends_on=["TC-B"]), "TC-B": card("TC-B")}
    raw = raw_for({"TC-A": receipt(True), "TC-B": receipt(False, reason="not done yet")})
    rows, accepted = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    by_id = {r["id"]: r for r in rows}
    assert "TC-A" not in accepted
    assert by_id["TC-A"]["status"] == "AWAITING_PREREQUISITE"
    assert "TC-B" in by_id["TC-A"]["blocker"]["summary"]


def test_transitive_prerequisite_enforcement_three_levels():
    """TC-C depends on TC-B depends on TC-A. Only TC-A is genuinely accepted. TC-B and TC-C both
    claim accepted=True in their own receipts. Neither may count -- enforcement must be
    transitive, not one hop."""
    cards = {"TC-A": card("TC-A"), "TC-B": card("TC-B", depends_on=["TC-A"]),
             "TC-C": card("TC-C", depends_on=["TC-B"])}
    raw = raw_for({"TC-A": receipt(False), "TC-B": receipt(True), "TC-C": receipt(True)})
    rows, accepted = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    assert accepted == set()
    by_id = {r["id"]: r for r in rows}
    assert by_id["TC-B"]["status"] == "AWAITING_PREREQUISITE"
    assert by_id["TC-C"]["status"] == "AWAITING_PREREQUISITE"


def test_real_chain_accepts_correctly_when_every_link_is_genuine():
    """Positive control for the two negative tests above: when every link in the chain is
    genuinely accepted, the whole chain must actually resolve to ACCEPTED -- otherwise the fix
    would just be a blanket refusal, not real dependency enforcement."""
    cards = {"TC-A": card("TC-A"), "TC-B": card("TC-B", depends_on=["TC-A"]),
             "TC-C": card("TC-C", depends_on=["TC-B"])}
    raw = raw_for({"TC-A": receipt(True), "TC-B": receipt(True), "TC-C": receipt(True)})
    rows, accepted = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    assert accepted == {"TC-A", "TC-B", "TC-C"}
    assert all(r["status"] == "ACCEPTED" for r in rows)


def test_superseded_upstream_invalidates_downstream_without_touching_unrelated_cards():
    """TC-B (accepted, then superseded) must stop counting toward TC-A's (depends on TC-B)
    eligibility. TC-X, an unrelated card with no dependency on TC-B, must be unaffected --
    'do not invalidate unrelated cards' (directive 3.1)."""
    cards = {"TC-A": card("TC-A", depends_on=["TC-B"]), "TC-B": card("TC-B"), "TC-X": card("TC-X")}
    raw = raw_for({"TC-A": receipt(True), "TC-B": receipt(True), "TC-X": receipt(True)})
    rows, accepted = gateverify.compute_rows(
        cards, raw, dispatched=set(), attempts={}, latest_kind={"TC-B": "supersede"}
    )
    by_id = {r["id"]: r for r in rows}
    assert by_id["TC-B"]["status"] == "SUPERSEDED"
    assert "TC-B" not in accepted
    assert by_id["TC-A"]["status"] == "AWAITING_PREREQUISITE"
    assert "TC-A" not in accepted
    assert by_id["TC-X"]["status"] == "ACCEPTED"
    assert "TC-X" in accepted


# --------------------------------------------------------------------------
# stale-receipt binding
# --------------------------------------------------------------------------
def test_stale_receipt_is_not_trusted_as_accepted():
    """A receipt whose card_sha256 no longer matches the current card content (the card was
    edited after the receipt was generated -- e.g. a check quietly weakened) must not count as
    ACCEPTED, and must not let a downstream card treat it as satisfied."""
    cards = {"TC-A": card("TC-A", depends_on=["TC-B"]), "TC-B": card("TC-B")}
    raw = raw_for({"TC-A": receipt(True), "TC-B": receipt(True)}, stale={"TC-B"})
    rows, accepted = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    by_id = {r["id"]: r for r in rows}
    assert by_id["TC-B"]["status"] == "STALE_RECEIPT"
    assert "TC-B" not in accepted
    assert by_id["TC-A"]["status"] == "AWAITING_PREREQUISITE"


# --------------------------------------------------------------------------
# the READY/IN_PROGRESS deadlock fix
# --------------------------------------------------------------------------
def test_undispatched_failed_verification_stays_pickupable_not_stuck_in_progress():
    """A card that was `verify`-checked for diagnostic purposes ONLY (never actually
    `instruct --kind dispatch`ed) and whose checks correctly failed because the feature does not
    exist yet must be VERIFICATION_FAILED, included in the ready-like set -- not IN_PROGRESS,
    which would wrongly imply a worker is already assigned and permanently remove it from the
    supervisor's selectable queue. This is the exact 'ready cards: none' deadlock the directive
    reported as a real, reproduced defect."""
    cards = {"TC-A": card("TC-A")}
    raw = raw_for({"TC-A": receipt(False, reason="feature not implemented yet")})
    rows, _ = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    assert rows[0]["status"] == "VERIFICATION_FAILED"
    assert gateverify.ready_cards_from_rows(rows) == ["TC-A"]


def test_actually_dispatched_card_is_in_progress_not_ready():
    """The flip side: a card that WAS actually dispatched (a real worker assignment recorded)
    and has not yet concluded must show IN_PROGRESS and must NOT be offered again by
    ready_cards_from_rows -- the fix must not turn every failure into 'go pick this up again'
    regardless of whether someone is already working on it."""
    cards = {"TC-A": card("TC-A")}
    raw = raw_for({"TC-A": receipt(False, reason="still working")}, attempts={"TC-A": 1})
    rows, _ = gateverify.compute_rows(cards, raw, dispatched={"TC-A"}, attempts={"TC-A": 1}, latest_kind={})
    assert rows[0]["status"] == "IN_PROGRESS"
    assert gateverify.ready_cards_from_rows(rows) == []


def test_three_failed_dispatched_attempts_is_failed_internal_not_ready():
    """A card dispatched and reworked three times without passing must be FAILED_INTERNAL, per
    the existing escalation ladder (ops/SUPERVISOR.md) -- not silently folded into the
    now-broader ready-like set."""
    cards = {"TC-A": card("TC-A")}
    raw = raw_for({"TC-A": receipt(False, reason="still broken")}, attempts={"TC-A": 3})
    rows, _ = gateverify.compute_rows(cards, raw, dispatched={"TC-A"}, attempts={"TC-A": 3}, latest_kind={})
    assert rows[0]["status"] == "FAILED_INTERNAL"
    assert gateverify.ready_cards_from_rows(rows) == []


def test_owner_decision_card_is_not_silently_offered_as_ready_work():
    """A card marked requires_owner_decision must surface as AWAITING_OWNER_DECISION, not
    VERIFICATION_FAILED/READY -- the directive's own distinction between a routine engineering
    gap an agent can go work on and a decision only a human can make. It must NOT appear in the
    ready-like set (the supervisor must not treat 'go get an owner decision' as something to
    retry automatically)."""
    cards = {"TC-A": card("TC-A", requires_owner_decision=True)}
    raw = raw_for({"TC-A": receipt(False, reason="owner has not decided yet")})
    rows, _ = gateverify.compute_rows(cards, raw, dispatched=set(), attempts={}, latest_kind={})
    assert rows[0]["status"] == "AWAITING_OWNER_DECISION"
    assert gateverify.ready_cards_from_rows(rows) == []


# --------------------------------------------------------------------------
# graph integrity: self-dependency, missing IDs, cycles
# --------------------------------------------------------------------------
def test_self_dependency_rejected():
    cards = {"TC-A": card("TC-A", depends_on=["TC-A"])}
    problems = gateverify.find_dependency_graph_problems(cards)
    assert any("TC-A: depends_on includes itself" in p for p in problems)


def test_missing_dependency_id_rejected():
    cards = {"TC-A": card("TC-A", depends_on=["TC-NONEXISTENT"])}
    problems = gateverify.find_dependency_graph_problems(cards)
    assert any("unknown card 'TC-NONEXISTENT'" in p for p in problems)


def test_two_card_cycle_rejected():
    cards = {"TC-A": card("TC-A", depends_on=["TC-B"]), "TC-B": card("TC-B", depends_on=["TC-A"])}
    problems = gateverify.find_dependency_graph_problems(cards)
    assert any("dependency cycle" in p for p in problems)


def test_three_card_cycle_rejected():
    cards = {"TC-A": card("TC-A", depends_on=["TC-B"]), "TC-B": card("TC-B", depends_on=["TC-C"]),
             "TC-C": card("TC-C", depends_on=["TC-A"])}
    problems = gateverify.find_dependency_graph_problems(cards)
    assert any("dependency cycle" in p for p in problems)


def test_acyclic_diamond_shape_produces_no_problems():
    """Positive control: a real, legitimate diamond dependency (two cards both depending on one
    root, one card depending on both) must NOT be flagged as a cycle -- the detector must not be
    so aggressive it rejects valid graphs."""
    cards = {
        "TC-ROOT": card("TC-ROOT"),
        "TC-L": card("TC-L", depends_on=["TC-ROOT"]),
        "TC-R": card("TC-R", depends_on=["TC-ROOT"]),
        "TC-TOP": card("TC-TOP", depends_on=["TC-L", "TC-R"]),
    }
    assert gateverify.find_dependency_graph_problems(cards) == []


# --------------------------------------------------------------------------
# duplicate card IDs (all_cards() keys by declared id, silently losing a collision)
# --------------------------------------------------------------------------
def test_duplicate_card_id_across_two_files_is_detected(tmp_path, monkeypatch):
    import gatectl

    taskcards = tmp_path / "taskcards"
    taskcards.mkdir()
    (taskcards / "TC-001.yaml").write_text("id: TC-001\ngate: G\n", encoding="utf-8")
    (taskcards / "TC-001b.yaml").write_text("id: TC-001\ngate: G\n", encoding="utf-8")
    monkeypatch.setattr(gatectl, "TASKCARDS", taskcards)
    monkeypatch.setattr(gateverify, "TASKCARDS", taskcards)
    problems = gateverify.find_duplicate_card_ids()
    assert any("duplicate card id 'TC-001'" in p for p in problems)


def test_no_duplicates_among_this_repositorys_real_cards():
    """Positive control, against the real repository state: the actual
    project/taskcards/*.yaml files in this repo must have zero duplicate IDs today."""
    import gatectl

    assert gateverify.find_duplicate_card_ids() == []
    assert gateverify.find_dependency_graph_problems(gatectl.all_cards()) == []
