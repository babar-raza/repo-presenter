"""BL-660: an ``unsupported_claim`` whose only cited lines are attributed maintainer text is void by the
contract's own text (``MAINTAINER_TEXT_ERROR``). Hosted PSD Java run 44952716923 lost unit u2's whole review
because the model filed one on line 245, twice. The finding is dropped with a recorded note; anything the
contract still lets the model assert on those lines stays."""

from __future__ import annotations

import copy

from repo_presenter.readme.review.llm_review import _unit_record, review_checks
from repo_presenter.readme.review.reply import (
    CONTRACT_NOTES_KEY,
    ReviewScope,
    drop_maintainer_unsupported_findings,
    resolve_cited_lines,
)
from repo_presenter.readme.review.sectionwise import ReviewUnit
from tests.readme.review.review_support import FACTS, raw_reply
from tests.readme.review.test_scoped_contract import CANDIDATE, FIRST, cited, scope


def maintained(*maintainer: int) -> ReviewScope:
    unit = scope("key_capabilities")
    return ReviewScope(unit.sections, unit.lines, frozenset(maintainer))


def _reply(verdict: str = "REJECT_FACTUAL", *findings: dict) -> dict:
    return raw_reply(verdict, list(findings))


def _checks(reply: dict, unit: ReviewScope) -> list[str]:
    return review_checks(reply, candidate_readme=CANDIDATE, facts=FACTS, plan={}, scope=unit, changed=None)


def test_the_hosted_shape_yields_a_valid_review_instead_of_a_lost_one() -> None:
    unit = maintained(FIRST)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, fact_ids=[]))
    assert resolve_cited_lines(copy.deepcopy(reply), CANDIDATE, unit)  # the hosted refusal
    assert _checks(reply, unit) == []
    assert reply["findings"] == [] and reply["verdict"] == "ACCEPT"
    rules = [note["rule"] for note in reply[CONTRACT_NOTES_KEY]]
    assert rules == ["BL-660", "BL-660"]
    assert reply[CONTRACT_NOTES_KEY][0]["dropped_finding"] == "F01"
    assert reply[CONTRACT_NOTES_KEY][1]["verdict_changed"] == ["REJECT_FACTUAL", "ACCEPT"]


def test_the_drop_is_recorded_on_the_unit_record_and_is_idempotent() -> None:
    unit = maintained(FIRST)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, fact_ids=[]))
    assert _checks(reply, unit) == []
    once = copy.deepcopy(reply)
    assert _checks(reply, unit) == []
    assert reply == once  # a stored reply replays identically
    record = _unit_record(ReviewUnit(2, ("key_capabilities",), (FIRST, FIRST + 1)), "r" * 64,
                          reply=reply, reply_sha256="s" * 64)
    assert record[CONTRACT_NOTES_KEY] == reply[CONTRACT_NOTES_KEY]
    clean = _unit_record(ReviewUnit(1, ("key_capabilities",), (FIRST,)), "r" * 64,
                         reply=raw_reply("ACCEPT"), reply_sha256="s" * 64)
    assert CONTRACT_NOTES_KEY not in clean


def test_a_span_of_maintainer_lines_is_dropped_too() -> None:
    unit = maintained(FIRST, FIRST + 1)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, FIRST + 1, fact_ids=[]))
    assert _checks(reply, unit) == [] and reply["findings"] == []


def test_another_valid_finding_keeps_the_verdict_and_stays_blocking() -> None:
    unit = maintained(FIRST)
    real = cited("contradiction", FIRST + 3, criterion="factuality")
    real["id"] = "F02"
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, fact_ids=[]), real)
    assert _checks(reply, unit) == []
    assert [f["id"] for f in reply["findings"]] == ["F02"]
    assert reply["verdict"] == "REJECT_FACTUAL"
    assert len(reply[CONTRACT_NOTES_KEY]) == 1


# --- negative controls: nothing the contract lets the model assert is dropped -------------------------


def test_contradiction_quality_and_other_kinds_on_maintainer_lines_stay() -> None:
    unit = maintained(FIRST)
    for kind, extra in (("contradiction", {"criterion": "factuality"}), ("quality", {})):
        reply = _reply("REJECT_FACTUAL", cited(kind, FIRST, **extra))
        assert drop_maintainer_unsupported_findings(reply, CANDIDATE, unit) == []
        assert len(reply["findings"]) == 1 and CONTRACT_NOTES_KEY not in reply


def test_a_span_that_also_cites_an_authored_line_stays() -> None:
    unit = maintained(FIRST)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, FIRST + 1, fact_ids=[]))
    assert drop_maintainer_unsupported_findings(reply, CANDIDATE, unit) == []
    assert len(reply["findings"]) == 1


def test_an_unsupported_claim_on_an_authored_line_stays() -> None:
    unit = maintained(FIRST)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST + 2, fact_ids=[]))
    assert drop_maintainer_unsupported_findings(reply, CANDIDATE, unit) == []
    assert _checks(reply, unit) == [] and len(reply["findings"]) == 1


def test_without_maintainer_lines_or_scope_nothing_is_dropped() -> None:
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", FIRST, fact_ids=[]))
    assert drop_maintainer_unsupported_findings(reply, CANDIDATE, maintained()) == []
    assert drop_maintainer_unsupported_findings(reply, CANDIDATE, None) == []
    assert len(reply["findings"]) == 1


def test_a_line_the_unit_did_not_show_is_still_refused_not_dropped() -> None:
    unit = maintained(FIRST)
    reply = _reply("REJECT_FACTUAL", cited("unsupported_claim", 1, fact_ids=[]))
    assert drop_maintainer_unsupported_findings(reply, CANDIDATE, unit) == []
    assert _checks(reply, unit)  # a hidden-line citation is still a contract error


def test_a_malformed_citation_is_left_to_the_contract() -> None:
    unit = maintained(FIRST)
    for lines in ([], [FIRST, FIRST, FIRST], ["x"], [0], [9999], [FIRST + 1, FIRST]):
        finding = cited("unsupported_claim", fact_ids=[])
        finding["lines"] = lines
        reply = _reply("REJECT_FACTUAL", finding)
        assert drop_maintainer_unsupported_findings(reply, CANDIDATE, unit) == []
        assert len(reply["findings"]) == 1


def test_an_insufficient_evidence_verdict_is_never_turned_into_an_accept() -> None:
    unit = maintained(FIRST)
    reply = _reply("INSUFFICIENT_EVIDENCE", cited("unsupported_claim", FIRST, fact_ids=[]))
    drop_maintainer_unsupported_findings(reply, CANDIDATE, unit)
    assert reply["verdict"] == "INSUFFICIENT_EVIDENCE"
