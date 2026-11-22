"""BL-701: an Enterprise clause that cites no fact stating what it claims is withheld at generation.

The real shape is the round-6 audit flag on the hosted-sealed Slides .NET candidate (line 722): the clause "The
commercial product adds features not implemented in this package, such as advanced animation editing, slide master
customization, and support for additional output formats." cites ten ``identity`` / ``package`` facts and no fact
that says what the commercial product adds. The same shape is stored on PSD Java, OCR .NET and Font Python (a zero-call
scan of the 36 stored Enterprise units: 4 cite only naming facts; the 28 others cite the maintainers' paragraph).
Negative controls: a clause that cites an inherited unit, another fact kind, a different section's unit, an empty
text, and the re-judgement of a sealed candidate (``withhold_unsupported`` off) are all untouched.
"""

from __future__ import annotations

import copy
from dataclasses import replace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.authoring import (
    ENTERPRISE_CLAIM_OMISSION_REASON,
    ENTERPRISE_NAMING_ONLY_REASON,
    SectionTask,
    api_row_fallback_slots,
    enterprise_clause_unsupported,
    unit_checks,
    withhold_unsupported_enterprise_clause,
)
from tests.readme.composition.synthetic import make_facts

CLAUSE = (
    "The commercial product adds features not implemented in this package, such as advanced animation editing, "
    "slide master customization, and support for additional output formats."
)
PARAGRAPH = "inherited_unit:103.paragraph"


def _facts():
    base = make_facts()
    extra = (
        Fact(PARAGRAPH, "inherited_unit", "The commercial edition adds PDF export.", (Evidence("README.md", "line 9"),)),
        Fact("link_target:product.enterprise", "link_target", "https://products.aspose.com/x/net/", (Evidence("README.md", "l"),)),
    )
    return replace(base, facts=(*base.facts, *extra))


def _ids(facts, kind: str, limit: int = 3) -> list[str]:
    return [f.id for f in facts.facts if f.kind == kind][:limit]


def _output(facts, cited: list[str], text: str = CLAUSE, section: str = "enterprise_relationship") -> dict:
    return {"units": [{"section": section, "slot": "context", "text": text, "fact_ids": cited}], "omitted": []}


def _task(section: str = "enterprise_relationship", ids=frozenset()) -> SectionTask:
    return SectionTask(section, {}, frozenset(ids), ("context",))


def test_the_slides_dotnet_shape_is_withheld_and_recorded() -> None:
    facts = _facts()
    naming = [*_ids(facts, "identity"), *_ids(facts, "package"), "link_target:product.enterprise"]
    assert naming and all(i in {f.id for f in facts.facts} for i in naming)
    output = _output(facts, naming)
    task = _task(ids=naming)
    assert enterprise_clause_unsupported(output["units"][0], facts)
    assert withhold_unsupported_enterprise_clause(output, task, facts)
    assert output["units"] == []
    [record] = output["omitted"]
    assert record["section"] == "enterprise_relationship" and record["fact_id"] == "link_target:product.enterprise"
    assert record["reason"] == ENTERPRISE_NAMING_ONLY_REASON
    assert record["reason"].startswith(ENTERPRISE_CLAIM_OMISSION_REASON)
    # the section's one slot is then owed no unit (BC-04), exactly as after the BL-480 degrade
    assert api_row_fallback_slots(output, task) == frozenset({"context"})


def test_unit_checks_withholds_only_when_asked_and_never_on_rejudgement() -> None:
    facts = _facts()
    naming = _ids(facts, "identity")
    task = _task(ids=naming)
    sealed = _output(facts, naming)
    unit_checks(copy.deepcopy(sealed), task, facts, "Aspose.Widget FOSS", register=False, values=False)
    judged = copy.deepcopy(sealed)
    unit_checks(judged, task, facts, "Aspose.Widget FOSS", register=False, values=False)
    assert judged["units"] == sealed["units"] and judged["omitted"] == []  # re-certification: untouched (R10)
    generated = copy.deepcopy(sealed)
    unit_checks(generated, task, facts, "Aspose.Widget FOSS", register=False, values=False, withhold_unsupported=True)
    assert generated["units"] == [] and generated["omitted"][0]["reason"] == ENTERPRISE_NAMING_ONLY_REASON


def test_a_clause_citing_no_fact_at_all_is_withheld_too() -> None:
    facts = _facts()
    output = _output(facts, [])
    assert withhold_unsupported_enterprise_clause(output, _task(), facts)
    assert output["units"] == []


def test_a_clause_that_cites_the_maintainers_paragraph_is_never_withheld() -> None:
    facts = _facts()
    output = _output(facts, [PARAGRAPH, *_ids(facts, "identity", 1)])
    before = copy.deepcopy(output)
    assert not enterprise_clause_unsupported(output["units"][0], facts)
    assert not withhold_unsupported_enterprise_clause(output, _task(ids=[PARAGRAPH]), facts)
    assert output == before


def test_a_clause_that_cites_a_fact_of_another_kind_is_never_withheld() -> None:
    facts = _facts()
    other = next(f.id for f in facts.facts if f.kind not in {"identity", "package", "inherited_unit", "link_target"})
    output = _output(facts, [other, *_ids(facts, "identity", 1)])
    assert not withhold_unsupported_enterprise_clause(output, _task(ids=[other]), facts)
    assert len(output["units"]) == 1 and output["omitted"] == []


def test_another_section_and_an_empty_text_are_never_touched() -> None:
    facts = _facts()
    naming = _ids(facts, "identity")
    elsewhere = _output(facts, naming, section="opening")
    assert not withhold_unsupported_enterprise_clause(elsewhere, _task("opening"), facts)
    assert len(elsewhere["units"]) == 1
    empty = _output(facts, naming, text="  ")
    assert not enterprise_clause_unsupported(empty["units"][0], facts)
    other_slot = _output(facts, naming)
    other_slot["units"][0]["slot"] = "capability:1"
    assert not withhold_unsupported_enterprise_clause(other_slot, _task(), facts)
