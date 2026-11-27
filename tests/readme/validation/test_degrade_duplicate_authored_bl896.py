"""BL-896: a paragraph two authored units both print is withheld from all but the first copy.

Real data: hosted Words Java Lane R run 45337646762, ``duplicate_paragraph`` "the paragraph occurs 2 times"
("The primary entry point is `Document` ... The library ships 1566 public types organized into 36
modules."); the degrade ended "nothing kept (1 flag(s) tried)" because the flag matched two authored units and
the ambiguity guard (right for a claim, wrong for a repeat) refused it.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.validation.must_correct import ClaimFlag, degrade_claims
from tests.readme.repair.test_accounting import _dispositions, _facts, _plan

PARAGRAPH = (
    "The primary entry point is Document, loaded from a file or stream or created empty, and edited through "
    "its node tree or the cursor-based DocumentBuilder. The library ships 1566 public types in 36 modules."
)


def _units(first: str, second: str) -> dict[str, Any]:
    return {
        "units": [
            {"section": "overview", "slot": "summary", "text": first, "fact_ids": []},
            {"section": "api_reference", "slot": "intro", "text": second, "fact_ids": []},
        ],
        "omitted": [],
    }


def _degrade(units: dict[str, Any], readme: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    flag = ClaimFlag(PARAGRAPH, "the candidate prints the same prose paragraph more than once", "duplicate_paragraph")
    _plan_out, out, _disp, records = degrade_claims(
        _plan(), units, _dispositions(), [flag], _facts(), readme=readme
    )
    return out, records


def test_two_authored_copies_leave_exactly_the_first_printing() -> None:
    readme = f"## A\n\n{PARAGRAPH}\n\n## B\n\n{PARAGRAPH}\n"
    out, records = _degrade(_units(PARAGRAPH, PARAGRAPH), readme)
    assert [u["slot"] for u in out["units"]] == ["summary"]
    assert [r["action"] for r in records] == ["duplicate_unit_dropped"]
    assert records[0]["slot"] == "intro"


def test_an_authored_copy_beside_a_printed_one_outside_the_units_all_go() -> None:
    readme = f"{PARAGRAPH}\n\n{PARAGRAPH}\n\n{PARAGRAPH}\n"
    out, records = _degrade(_units(PARAGRAPH, PARAGRAPH), readme)
    assert out["units"] == []
    assert len(records) == 2


def test_negative_control_a_claim_two_units_print_is_still_refused() -> None:
    flag = ClaimFlag(PARAGRAPH, "unsupported", "BC-17")
    _p, out, _d, records = degrade_claims(
        _plan(), _units(PARAGRAPH, PARAGRAPH), _dispositions(), [flag], _facts(), readme=PARAGRAPH
    )
    assert len(out["units"]) == 2 and records == []
