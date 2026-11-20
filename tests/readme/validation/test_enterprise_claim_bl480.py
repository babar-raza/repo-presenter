"""BL-480: the Enterprise clause that carries the maintainers' own paragraph is withheld by the
last-resort degrade, as a recorded R14 decision, when the independent review faults it.

The flagged text is the exact one of the hosted Lane R failure records of 2026-11-20 (Slides C++
run 44691775045 on main 400eb72; the same shape on OMR Python 44645155538 / 44656583285): one line
that joins the renderer's own "See [... Enterprise Edition](url)." sentence to the authored clause
"It adds ...". On every cell whose live README has an Enterprise paragraph the clause cites that
paragraph (the must-carry carrier), which BL-350's inherited guard refused, so its lever never ran.
Negative controls: a clause no review faulted, the renderer's sentence alone, a quote elsewhere, a
different must-carry unit.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.validation.must_correct import (
    DEGRADE_RECORDS_KEY,
    ENTERPRISE_CLAIM_RATIONALE,
    ENTERPRISE_CLAIM_RULE,
)
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _entry, _plan
from tests.readme.validation.test_degrade_claims_bl240 import _fact, _facts_with, _ids, _World
from tests.readme.validation.test_degrade_single_claim_bl350 import _degrade, _plan_with

URL = "https://products.aspose.com/slides/cpp/"
# the fixture product is Aspose.3D FOSS for Python; the sentence shape is the Slides C++ record's
SHELL = f"See [Aspose.3D for Python — Enterprise Edition]({URL})."
ADDS = (
    "It adds broader format support (including PDF, HTML, and image export), charts, animations, "
    "and full commercial support."
)
PARAGRAPH = (
    "These limitations don't apply to\n"
    f"[Aspose.Slides for C++ — Enterprise Edition]({URL}), which adds\n"
    "broader format support (including PDF, HTML, and image export), charts, animations, and full\n"
    "commercial support."
)
INHERITED = "inherited_unit:103.paragraph"


def _world(tmp_path: Path, *, cite: tuple[str, ...] = (INHERITED,), adds: str = ADDS) -> _World:
    units = copy.deepcopy(UNITS)
    units["units"].append(
        {"section": "enterprise_relationship", "slot": "context", "text": adds, "fact_ids": list(cite)}
    )
    facts = _facts_with(
        _fact("link_target:product.enterprise", "link_target", URL, level="platform"),
        Fact(INHERITED, "inherited_unit", PARAGRAPH, (Evidence("README.md", "lines 828-831"),)),
    )
    dispositions = _dispositions(
        **{
            "103.paragraph": _entry(
                "103.paragraph", "SUPERSEDE_REDUNDANT", "enterprise_relationship",
                ["link_target:product.enterprise"],
            )
        }
    )
    for row in dispositions["dispositions"]:
        if row["unit_id"] == "103.paragraph":
            row["unit_id"] = INHERITED
    return _World(facts, units, dispositions, plan=_plan_with("enterprise_relationship"), tmp=tmp_path)


def test_the_world_prints_the_exact_flagged_line(tmp_path: Path) -> None:
    assert f"{SHELL} {ADDS}" in _world(tmp_path).readme


def test_the_clause_that_carries_the_maintainers_paragraph_is_withheld_on_a_recorded_decision(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path)
    before = _ids(world.judge()[0])
    degraded = _degrade(world, tmp_path, (f"{SHELL} {ADDS}", "scope_limitations"))
    assert degraded is not None, "BL-350's inherited guard refused the one lever that applies"
    assert _ids(degraded.validation) <= before  # BC-17 accounts for the omitted paragraph
    # BC-04 owes the section no unit once the clause is withheld (BL-350's lever was also discarded here)
    bc04 = [d for c in degraded.validation["checks"] if c["id"] == "BC-04" for d in c.get("details") or []]
    assert not [d for d in bc04 if d.startswith("enterprise_relationship")]
    readme = degraded.composed.readme
    assert SHELL in readme  # the renderer's own fact-true sentence stays
    assert "It adds" not in readme and "broader format support" not in readme
    # R9: no provenance or attribution wording is printed for the omission
    assert not {"maintainer", "originally", "previously", "removed"} & set(readme.lower().split())
    assert not [u for u in degraded.composed.coherent_units["units"] if u["section"] == "enterprise_relationship"]
    # R14: the decision is recorded in the units and in the paragraph's disposition
    records = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    [withheld] = [r for r in records if r["action"] == "enterprise_context_withheld"]
    assert withheld["rule"] == ENTERPRISE_CLAIM_RULE == "BL-480" and withheld["inherited_units"] == [INHERITED]
    [omitted] = [r for r in records if r["action"] == "inherited_unit_omitted"]
    assert omitted["rule"] == "BL-480" and omitted["slot"] == INHERITED
    [row] = [r for r in degraded.composed.dispositions["dispositions"] if r["unit_id"] == INHERITED]
    assert row["disposition"] == "OMIT_UNSUPPORTED" and row["destination_section"] is None
    assert row["rationale"] == ENTERPRISE_CLAIM_RATIONALE and row["fact_ids"] == ["link_target:product.enterprise"]


def test_the_owner_is_found_by_position_when_the_quote_and_the_unit_text_differ(tmp_path: Path) -> None:
    # OMR Python: the lever answered "printed_text_withheld" (no owner found) for the same line
    world = _world(tmp_path)
    quote = f"{SHELL} It adds broader format support, charts and animations, and commercial support."
    degraded = _degrade(world, tmp_path, (quote, "scope_limitations"))
    assert degraded is not None and SHELL in degraded.composed.readme
    assert "It adds" not in degraded.composed.readme


def test_an_enterprise_clause_no_review_faulted_is_printed_as_before(tmp_path: Path) -> None:
    world = _world(tmp_path)
    assert _degrade(world, tmp_path, ("It documents nothing this README prints at all, really.", "scope_limitations")) is None
    assert f"{SHELL} {ADDS}" in world.readme


def test_the_renderers_own_sentence_alone_is_never_withheld(tmp_path: Path) -> None:
    world = _world(tmp_path)
    assert _degrade(world, tmp_path, (SHELL, "scope_limitations")) is None


def test_a_must_carry_unit_in_another_slot_is_still_refused_without_a_recorded_decision(
    tmp_path: Path,
) -> None:
    units = copy.deepcopy(UNITS)
    opening = next(u for u in units["units"] if u["slot"] == "opening")
    flagged = "Aspose.3D FOSS for Python also renders scenes on a GPU in real time."
    opening["text"] = flagged
    opening["fact_ids"] = ["inherited_unit:001.heading"]
    world = _World(_facts_with(), units, _dispositions(), tmp=tmp_path)
    assert _degrade(world, tmp_path, (flagged, "opening")) is None


def test_a_non_enterprise_sentence_is_withheld_alone_and_the_enterprise_clause_is_untouched(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path)
    opening = next(u for u in world.units["units"] if u["slot"] == "opening")
    keep, flagged = "Aspose.3D FOSS for Python builds scenes.", "It also ships a GPU backend that renders live."
    opening["text"] = f"{keep} {flagged}"
    world = _World(world.facts, world.units, world.dispositions, plan=world.plan, tmp=tmp_path)
    degraded = _degrade(world, tmp_path, (flagged, "opening"))
    assert degraded is not None
    assert "GPU" not in degraded.composed.readme and f"{SHELL} {ADDS}" in degraded.composed.readme


def test_the_clause_the_degrade_withholds_is_a_global_lever_not_a_per_candidate_one() -> None:
    assert cascade_module.MAX_DEGRADE_PASSES >= 3
    assert "contradict" not in ENTERPRISE_CLAIM_RATIONALE.lower()  # honest: unverifiable, not refuted
    assert "no longer" in ENTERPRISE_CLAIM_RATIONALE  # the wording BC-17 reads as a recorded omission


def test_the_slot_is_owed_unless_the_degrade_recorded_the_clause_withheld(tmp_path: Path) -> None:
    from repo_presenter.readme.composition.authoring import (
        ENTERPRISE_CLAIM_OMISSION_REASON,
        api_row_fallback_slots,
        authoring_tasks,
    )

    world = _world(tmp_path)
    [task] = [t for t in authoring_tasks(ENTRY, world.facts, {}, world.dispositions, world.plan)
              if t.section_id == "enterprise_relationship"]
    item = {"fact_id": "link_target:product.enterprise", "section": "enterprise_relationship"}
    assert api_row_fallback_slots({"omitted": []}, task) == frozenset()
    assert api_row_fallback_slots({"omitted": [{**item, "reason": "any other reason"}]}, task) == frozenset()
    assert api_row_fallback_slots(
        {"omitted": [{**item, "reason": ENTERPRISE_CLAIM_OMISSION_REASON}]}, task
    ) == frozenset({"context"})
    other = [t for t in authoring_tasks(ENTRY, world.facts, {}, world.dispositions, world.plan)
             if t.section_id != "enterprise_relationship"][0]
    assert api_row_fallback_slots(
        {"omitted": [{**item, "reason": ENTERPRISE_CLAIM_OMISSION_REASON}]}, other
    ) == frozenset()
