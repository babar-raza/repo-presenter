"""BL-543: a model flag on the maintainers' paragraph whose type count the renderer corrected is cleared
by the count's own provenance, only when the flag is about the count.

Hosted Lane R HTML Python refresh (run 44775079471): the kept paragraph inherited_unit:046 ("The library
exposes 243 public types in total, listed below by module, with curated highlights following.") prints in
API Reference with the count corrected to the facts' computation, 303 (``correct_stated_type_counts``;
303 SUPPORTED class and enum facts). The review's F01 called it an ``unsupported_claim``: "303" occurs in
no fact value and not in the original README. The derivation refused the line twice over: it is
maintainers' text, which no deterministic stage "owns", and its "listed below" test demanded rows ``==`` the
count (HTML's 517 table rows are the member tables under 303 types) where BC-14 holds ``listed < stated``.
The BL-240 degrade could not withhold it either (the paragraph carries API identifiers, so omitting it adds
BC-17: ``blocking load 0 -> 3 is not lower``), so the cell ended REJECT on a count the facts prove.

Negative controls: a flag that is not about the count, a count the facts do not compute, rows that do not
reach the total, and a paragraph the renderer did not correct are never cleared.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.clearances import ClearanceContext, apply_clearances
from repo_presenter.readme.review.derivation import (
    count_provenance,
    flag_is_about_count,
    lane_r_derivation,
)
from repo_presenter.readme.review.findings import Finding
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _plan
from tests.readme.validation.test_degrade_claims_bl240 import _facts_with, _member, _type

PARAGRAPH = "The library exposes {n} public types in total, listed below by module, with curated highlights following."
INHERITED = "inherited_unit:046.paragraph"
TYPES = [f"aspose.threed.T{i}" for i in range(5)]


def _world(stated: int = 243, *, disposition: str = "VERIFIED_PRESERVE") -> dict[str, Any]:
    facts = _facts_with(
        *[_type(t) for t in TYPES], *[_member(t, "m", "method") for t in TYPES],
        Fact(INHERITED, "inherited_unit", PARAGRAPH.format(n=stated), (Evidence("README.md"),), polarity="SUPPORTED"),
        drop=("public_symbol:aspose.threed.scene",),
    )
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        {"unit_id": INHERITED, "disposition": disposition, "destination_section": "api_reference",
         "fact_ids": [], "rationale": "kept as written"}
    )
    plan, units = _plan(hubs=False), copy.deepcopy(UNITS)
    return {"facts": facts, "plan": plan, "units": units, "dispositions": dispositions,
            "readme": render_readme(ENTRY, facts, plan, units, dispositions)}


def _context(world: dict[str, Any], readme: str | None = None, tmp: Path | None = None) -> ClearanceContext:
    register = (tmp or Path(".")) / "readme_findings.json"
    if tmp is not None:
        register.write_text(json.dumps({"findings": []}), encoding="utf-8")
    text = readme if readme is not None else world["readme"]

    def derive(lines: Any) -> Any:
        return lane_r_derivation(
            text, entry=ENTRY, facts=world["facts"], plan=world["plan"], units=world["units"],
            dispositions=world["dispositions"], ask=lines, register_path=register,
        )

    return ClearanceContext(text, "", world["facts"], derive)


def _flag(message: str, quote: str) -> Finding:
    return Finding(
        rule="llm:factuality", source="llm", claim_kind="unsupported_claim", message=message, quote=quote,
        finding_id="F01", section_id="api_reference", causal_stage="S6", criterion="factuality",
        evidence="audit: distinctive terms ['5']; in no SUPPORTED fact value and not in the original README",
    )


def _line(world: dict[str, Any]) -> str:
    return next(r for r in world["readme"].splitlines() if "public types in total" in r)


def test_the_paragraph_prints_with_the_corrected_count(tmp_path: Path) -> None:
    world = _world()
    assert _line(world) == PARAGRAPH.format(n=5)  # 243 -> 5, the facts' own computation


def test_a_flag_about_the_count_is_cleared_with_its_provenance(tmp_path: Path) -> None:
    world = _world()
    line = _line(world)
    cleared = apply_clearances(_flag(line, line), _context(world, tmp=tmp_path))
    assert cleared.status == "CLEARED"
    assert cleared.clearance is not None and "K05 verified: 5 public types" in " ".join(cleared.clearance.evidence)


def test_a_flag_on_another_statement_of_the_paragraph_is_not_cleared(tmp_path: Path) -> None:
    world = _world()
    flagged = apply_clearances(
        _flag("The curated highlights following are not described anywhere.", _line(world)),
        _context(world, tmp=tmp_path),
    )
    assert flagged.status != "CLEARED" and flagged.blocking


def test_a_count_the_facts_do_not_compute_is_not_cleared(tmp_path: Path) -> None:
    world = _world()
    wrong = world["readme"].replace(PARAGRAPH.format(n=5), PARAGRAPH.format(n=9))
    line = PARAGRAPH.format(n=9)
    flagged = apply_clearances(_flag(line, line), _context(world, wrong, tmp=tmp_path))
    assert flagged.status != "CLEARED"


def test_rows_that_do_not_reach_the_total_are_not_cleared(tmp_path: Path) -> None:
    world = _world()
    rows = world["readme"].splitlines()
    short = "\n".join(r for r in rows if not r.startswith(("| `T3`", "| `T4`")))
    line = _line(world)
    assert apply_clearances(_flag(line, line), _context(world, short, tmp=tmp_path)).status != "CLEARED"


def test_an_uncorrected_paragraph_is_not_the_renderers_to_clear(tmp_path: Path) -> None:
    world = _world(stated=5)  # the maintainers' own count was already right: nothing was corrected
    line = _line(world)
    assert apply_clearances(_flag(line, line), _context(world, tmp=tmp_path)).status != "CLEARED"


@pytest.mark.parametrize(("rows", "stated", "verified"), [(517, 303, True), (303, 303, True), (302, 303, False), (0, 303, False)])
def test_the_listed_rows_must_reach_the_total_as_bc14_holds_them(rows: int, stated: int, verified: bool) -> None:
    facts = _facts_with(*[_type(f"aspose.threed.T{i}") for i in range(stated)], drop=("public_symbol:aspose.threed.scene",))
    text = [PARAGRAPH.format(n=stated), "", *[f"| `Row{i}` | d |" for i in range(rows)]]
    assert bool(count_provenance(text, 1, facts)) is verified


def test_only_a_flag_that_states_the_count_is_about_it() -> None:
    row = PARAGRAPH.format(n=303)
    assert flag_is_about_count("The library exposes 303 public types in total.", row)
    assert flag_is_about_count("claims 303 types", row)
    assert not flag_is_about_count("The DOM tree can be queried and mutated directly.", row)
    assert not flag_is_about_count("The library exposes 243 public types.", row)
