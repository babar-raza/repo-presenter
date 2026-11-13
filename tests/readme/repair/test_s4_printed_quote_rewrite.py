"""S4 repair: a quoted prose unit the repair keeps printing as written is folded to VERIFIED_REWRITE.

Measured (aspose-3d-foss/Aspose.3D-FOSS-for-Java, hosted Lane R run 43394954743): the reviewer
quoted an inherited Enterprise paragraph printed as VERIFIED_MOVE in scope_limitations ("It adds
broader format support (including glTF, FBX, USD, ..."); both asks of the S4 patch handed back
VERIFIED_MOVE, ``reject_printed_quote`` refused each, and the candidate stayed REJECTed. After the
bounded asks the unit is now folded to VERIFIED_REWRITE with no further model call, re-judged by
the batch's own checks, and stored; the section's authoring job then re-authors it from facts and
BC-05 still requires its must-carry substance. Offline, on the Font Python fixture
``test_s4_repair`` uses (its 101.paragraph stands in for the quoted prose unit).
"""

from __future__ import annotations

import copy
from typing import Any

from repo_presenter.readme.composition.authoring import _placed_units
from repo_presenter.readme.repair.loop import repair_defect
from repo_presenter.readme.repair.targeted import Defect
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import Finding, ReviewVerdict
from repo_presenter.readme.validation.supersession import obligation_failures
from repo_presenter.core.llm.prompts import load_manifests
from tests.readme.repair.test_s4_repair import (
    AFTER,
    PLAN,
    PROMPTS_PATH,
    STORED,
    _by_unit,
    _Case,
    _entry,
    _reply,
    case,  # noqa: F401 - the fixture
)

QUOTE = "machine-readable variable-font compatibility"
SECTION = "scope_limitations"


def _defect(case: _Case) -> Defect:
    finding = Finding(
        rule="unsupported_claim",
        source="deterministic",
        message="the paragraph claims capabilities no fact supports",
        evidence="",
        quote=QUOTE,
    )
    [defect] = build_defects(
        ReviewVerdict(verdict="REJECT", findings=(finding,)),
        units=[],
        plan=PLAN,
        dispositions=STORED,
        facts=case.facts,
        ecosystem="python",
        repairer=load_manifests(PROMPTS_PATH)["targeted_repair"].sha256,
    )
    return defect


def _kept(fingerprint: str, disposition: str = "VERIFIED_MOVE") -> dict[str, Any]:
    return _reply(
        fingerprint,
        _entry(AFTER, disposition, SECTION, [], "kept as written in the limitations"),
    )


def test_the_quoted_paragraph_kept_twice_is_folded_to_a_rewrite_without_a_third_call(
    case: _Case,
) -> None:
    defect = _defect(case)
    assert defect.stage == "S4"
    client = case.script([_kept(defect.fingerprint), _kept(defect.fingerprint)])

    assert repair_defect(case.rc, defect, case.repairs) is True

    assert client.chat.completions.replies == []  # both asks spent, no third call made
    attempt = case.repairs.attempts[defect.fingerprint]
    assert attempt["outcome"] == "repaired"
    stored = case.stored_now()
    unit = _by_unit(stored)[AFTER]
    assert unit["disposition"] == "VERIFIED_REWRITE"
    assert unit["destination_section"] == SECTION  # rewritten where the reply put it, not dropped
    assert unit["rationale"].startswith("Re-authored from the facts")
    # Every other unit is the stored batch's own.
    others = {k: v for k, v in _by_unit(stored).items() if k != AFTER}
    assert others == {k: v for k, v in _by_unit(case.stage).items() if k != AFTER}
    # The section's authoring job is handed the unit to re-author from facts.
    assert AFTER in _placed_units(stored, SECTION)


def test_a_reply_leaving_the_quoted_unit_out_folds_the_stored_disposition(case: _Case) -> None:
    """The stored 101.paragraph is VERIFIED_PRESERVE (in key_capabilities); a reply that declares
    no unit leaves it printed as written (the merge keeps the stored entry), so the fold is applied
    to a copy of the stored entry, where it already is."""
    defect = _defect(case)
    empty = _reply(defect.fingerprint)
    case.script([empty, copy.deepcopy(empty)])

    assert repair_defect(case.rc, defect, case.repairs) is True

    unit = _by_unit(case.stored_now())[AFTER]
    assert unit["disposition"] == "VERIFIED_REWRITE"
    assert unit["destination_section"] == "key_capabilities"
    assert unit["fact_ids"] == ["dependency:optional.mcp.mcp-1.0"]


def test_an_attributed_quoted_unit_is_not_re_authored_from_facts(case: _Case) -> None:
    """PRESERVE_ATTRIBUTED is unverified content: it is never folded to a rewrite from facts."""
    defect = _defect(case)
    before = copy.deepcopy(case.stage)
    case.script(
        [
            _kept(defect.fingerprint, "PRESERVE_ATTRIBUTED"),
            _kept(defect.fingerprint, "PRESERVE_ATTRIBUTED"),
        ]
    )

    assert repair_defect(case.rc, defect, case.repairs) is False

    attempt = case.repairs.attempts[defect.fingerprint]
    assert attempt["outcome"] == "unrepairable"
    assert "still PRESERVE_ATTRIBUTED, which prints the quoted text" in attempt["reason"]
    assert case.stored_now() == before


def test_bc05_still_requires_the_substance_of_a_rewritten_unit() -> None:
    """The fold changes only the disposition; BC-05's obligation check judges VERIFIED_REWRITE
    exactly as before, so a rewrite that drops must-carry substance is still a loss."""
    from tests.readme.validation.test_supersession_obligations import _candidate, _fact, _row

    facts = [
        _fact("public_symbol:widget", "public_symbol", "Foo.Widget"),
        _fact(
            "inherited_unit:001.table",
            "inherited_unit",
            "| `Widget` | Represents a widget and its drawing surface. |",
        ),
    ]
    lost = _candidate(facts, [_row("inherited_unit:001.table", "VERIFIED_REWRITE")], "nothing")
    assert [f.unit for f in obligation_failures(lost)] == ["inherited_unit:001.table"]
