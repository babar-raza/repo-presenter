"""BL-350: the last-resort degrade reaches the single-claim shapes BL-240 left standing.

Every flagged text is the exact one of a hosted Lane R failure record of 2026-11-19 (frozen-code
passes 1 and 2, main 9476c1b): the closing Enterprise sentence of Scope (OMR Python 44589968814,
HTML Python 44588563439, PSD Python 44589326365), a Documentation and Resources line the maintainers
describe (HTML Python, PDF .NET 44588986899), an opening that is only the flagged statement (Slides
C++ 44589458757, Font Python 44588412674), and Words Java's opening rejected for ``C# ``
(44590092142). Each shape is shown withheld at its origin with an R14 record and then passing the
checks; negative controls show what is never touched.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import forbidden_text_pattern, unit_checks
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import ReviewVerdict
from repo_presenter.readme.validation.must_correct import DEGRADE_RECORDS_KEY
from tests.readme.composition import test_api_row_fallback as api_fixture
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _plan
from tests.readme.validation.test_degrade_claims_bl240 import _fact, _facts_with, _ids, _World

ENTERPRISE_URL = "https://products.aspose.com/omr/"
SHELL = f"See [Aspose.3D for Python — Enterprise Edition]({ENTERPRISE_URL})."
OMR_ADDS = (
    "It adds advanced recognition algorithms, batch processing, and export to multiple formats "
    "including PDF, DOCX, and Excel."
)
HTML_ADDS = (
    "It adds full `CSS` selector and pseudo-class coverage, constraint validation, image and PDF "
    "rendering, and unrestricted JavaScript execution."
)
REF = "https://reference.aspose.org/html/python/"
REF_LINE = (
    f"- **[Full API reference]({REF})** — the complete, browsable reference for all 303 public types."
)
SLIDES_OPENING = (
    "Aspose.Slides FOSS for Cpp reads and writes presentations in Microsoft PowerPoint formats "
    "including `.ppt`, `.pptx`, `.pptm`, `.pps`, `.ppsx`, `.ppsm`, `.pot`, `.potx`, and `.potm`. "
    "It converts presentations to other formats such as `.pdf`, `.html`, `.html5`, `.xml`, `.xps`, "
    "`.tiff`, `.gif`, `.swf`, `.htm`, `.md`, `.odp`, `.otp`, and `.fodp`. It supports adding and "
    "managing comments, comment authors, and replies, as well as setting document properties and "
    "custom properties."
)


def _llm(quote: str, section: str, kind: str = "unsupported_claim") -> Finding:
    return Finding(
        rule="factuality", source="llm", claim_kind=kind, message=quote[:80], quote=quote,
        finding_id="F01", section_id=section, causal_stage="S6", criterion="c",
        evidence="audit: no registered clearance proves an unsupported claim false",
    )


def _degrade(world: _World, tmp_path: Path, *quotes: tuple[str, str]) -> Any:
    """The cascade's degrade step on ``world`` with the model reviewer's finding on each quote."""
    verdict = ReviewVerdict.folded(findings=tuple(_llm(q, section) for q, section in quotes))
    return cascade_module._degrade_settled(
        world.settled(), verdict, entry=ENTRY, document=world.facts, investigation={},
        tree_paths=[], original="", out_dir=tmp_path,
    )


def _plan_with(*sections: str) -> dict[str, Any]:
    plan = _plan()
    for row in plan["sections"]:
        if row["section_id"] in sections:
            row["include"] = True
    return plan


# --- OMR / HTML / PSD Python: the authored clause after the Enterprise Edition sentence ----------


def _enterprise_world(tmp_path: Path, adds: str, *, cite: str | None = None) -> _World:
    units = copy.deepcopy(UNITS)
    unit = {"section": "enterprise_relationship", "slot": "context", "text": adds,
            "fact_ids": [cite or "identity:repository"]}
    units["units"].append(unit)
    facts = _facts_with(
        _fact("link_target:product.enterprise", "link_target", ENTERPRISE_URL, level="platform")
    )
    return _World(facts, units, _dispositions(), plan=_plan_with("enterprise_relationship"), tmp=tmp_path)


@pytest.mark.parametrize(
    ("adds", "quote"),
    [
        (OMR_ADDS, f"{SHELL} {OMR_ADDS}"),  # OMR: the quote spans the shell sentence and the clause
        (HTML_ADDS, f"{SHELL} {HTML_ADDS}"),
        (HTML_ADDS, HTML_ADDS),  # a quote of the authored sentence alone
        (OMR_ADDS.replace("It adds", "which adds"), f"{SHELL} {OMR_ADDS}"),  # printed raised: "It adds"
    ],
)
def test_the_authored_enterprise_clause_is_withheld_and_the_fact_true_sentence_stays(
    tmp_path: Path, adds: str, quote: str
) -> None:
    world = _enterprise_world(tmp_path, adds)
    assert SHELL in world.readme and quote.replace("`", "") in world.readme.replace("`", "")
    before = _ids(world.judge()[0])
    degraded = _degrade(world, tmp_path, (quote, "scope_limitations"))
    assert degraded is not None
    assert _ids(degraded.validation) <= before
    assert SHELL in degraded.composed.readme  # the renderer's own closing sentence stays
    assert "It adds" not in degraded.composed.readme and "advanced recognition" not in degraded.composed.readme
    assert not [u for u in degraded.composed.coherent_units["units"] if u["section"] == "enterprise_relationship"]
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["rule"] == "BL-240" and record["action"] == "enterprise_context_withheld"
    assert record["slot"] == "context" and record["section"] == "enterprise_relationship"
    assert json.loads((tmp_path / "content_units.coherent.json").read_text())[DEGRADE_RECORDS_KEY]


def test_an_enterprise_clause_that_carries_an_inherited_unit_is_withheld_on_a_recorded_decision(
    tmp_path: Path,
) -> None:
    # BL-480 replaces BL-350's refusal: the maintainers' own Enterprise paragraph is must-carry
    # (R14), so the clause is withheld only as a recorded decision (tests/.../test_enterprise_claim_bl480.py
    # holds the full shape); here the inherited unit has no placed disposition, so nothing is rewritten
    world = _enterprise_world(tmp_path, OMR_ADDS, cite="inherited_unit:004.list")
    degraded = _degrade(world, tmp_path, (f"{SHELL} {OMR_ADDS}", "scope_limitations"))
    assert degraded is not None and "It adds" not in degraded.composed.readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["rule"] == "BL-480" and record["inherited_units"] == ["inherited_unit:004.list"]


def test_a_quote_the_enterprise_clause_does_not_print_changes_nothing(tmp_path: Path) -> None:
    world = _enterprise_world(tmp_path, OMR_ADDS)
    assert _degrade(world, tmp_path, ("It adds nothing this README prints at all, really.", "scope_limitations")) is None


# --- HTML Python / PDF .NET: a Documentation and Resources line the maintainers describe ---------


def _docs_world(tmp_path: Path) -> _World:
    facts = _facts_with(
        Fact(
            "link_target:003", "link_target", REF,
            (Evidence("README.md", "line 9; external; text 'Full API reference'"), Evidence("README.md", "RESOLVED")),
            polarity="SUPPORTED",
        ),
        # the maintainers' list spells its dash differently from the printed line: the quote matches
        # no inherited unit verbatim, so only the printed line can be answered
        Fact(
            "inherited_unit:009.list", "inherited_unit",
            REF_LINE.replace("** — ", "** - ") + "\n- **[How-to](https://kb.example.com/3d)** — task-focused answers.",
            (Evidence("README.md"),), polarity="SUPPORTED",
        ),
    )
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        {"unit_id": "inherited_unit:009.list", "disposition": "VERIFIED_PRESERVE",
         "destination_section": "documentation_resources", "fact_ids": ["link_target:003"], "rationale": "r"}
    )
    plan = _plan()
    plan["links"].append({"link_fact_id": "link_target:003", "section_id": "documentation_resources"})
    return _World(facts, copy.deepcopy(UNITS), dispositions, plan=plan, tmp=tmp_path)


def test_a_flagged_described_resource_line_keeps_its_link_with_the_fact_true_description(
    tmp_path: Path,
) -> None:
    world = _docs_world(tmp_path)
    assert REF_LINE in world.readme
    before = _ids(world.judge()[0])
    degraded = _degrade(world, tmp_path, (REF_LINE, "documentation_resources"))
    assert degraded is not None and _ids(degraded.validation) <= before
    readme = degraded.composed.readme
    assert "all 303 public types" not in readme
    assert f"- **[Full API reference]({REF})** — The complete, browsable reference for the public API." in readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "printed_text_withheld" and record["findings"] == ["factuality"]


def test_an_unflagged_described_resource_line_is_printed_as_before(tmp_path: Path) -> None:
    world = _docs_world(tmp_path)
    assert _degrade(world, tmp_path, ("- an unrelated sentence the README never prints.", "documentation_resources")) is None
    assert REF_LINE in world.readme


# --- Slides C++ / Font Python: an opening that is only the flagged statement ----------------------


def _opening_world(tmp_path: Path, text: str, *, cite: str | None = None) -> _World:
    units = copy.deepcopy(UNITS)
    opening = next(u for u in units["units"] if u["slot"] == "opening")
    opening["text"] = text
    if cite:
        opening["fact_ids"] = [cite]
    return _World(_facts_with(), units, _dispositions(), tmp=tmp_path)


def test_an_opening_that_is_all_flagged_prints_the_format_facts_sentence(tmp_path: Path) -> None:
    world = _opening_world(tmp_path, SLIDES_OPENING)
    assert SLIDES_OPENING.replace("`", "") in world.readme.replace("`", "")
    degraded = _degrade(world, tmp_path, (SLIDES_OPENING, "opening"))
    assert degraded is not None and _ids(degraded.validation) <= _ids(world.judge()[0])
    assert "converts presentations" not in degraded.composed.readme
    assert "Aspose.3D FOSS for Python reads OBJ files and writes GLB files." in degraded.composed.readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "opening_fact_true" and record["slot"] == "opening"
    [opening] = [u for u in degraded.composed.coherent_units["units"] if u["slot"] == "opening"]
    assert sorted(opening["fact_ids"]) == ["format:input.obj", "format:output.glb"]  # it cites what it says


def test_a_truncated_quote_of_a_whole_opening_is_answered_the_same_way(tmp_path: Path) -> None:
    # Font Python: the reviewer's quote of the opening is cut off inside its last sentence
    text = (
        "It opens TrueType fonts using the loader. It creates static instances from variable "
        "fonts. It renders visual specimens with the preview builder."
    )
    world = _opening_world(tmp_path, text)
    cut = text[: text.rindex("builder") - 3]
    degraded = _degrade(world, tmp_path, (cut, "opening"))
    assert degraded is not None
    assert "It opens TrueType" not in degraded.composed.readme or "builder" not in degraded.composed.readme


def test_one_flagged_sentence_of_an_opening_is_still_withheld_alone(tmp_path: Path) -> None:
    keep = "Aspose.3D FOSS for Python builds scenes."
    flagged = "It also ships a GPU backend that renders in real time."
    world = _opening_world(tmp_path, f"{keep} {flagged}")
    degraded = _degrade(world, tmp_path, (flagged, "opening"))
    assert degraded is not None
    assert keep in degraded.composed.readme and "GPU" not in degraded.composed.readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "sentence_withheld"  # BL-240's lever, not the facts sentence


def test_an_opening_that_carries_an_inherited_unit_is_never_replaced(tmp_path: Path) -> None:
    world = _opening_world(tmp_path, SLIDES_OPENING, cite="inherited_unit:001.heading")
    assert _degrade(world, tmp_path, (SLIDES_OPENING, "opening")) is None


def test_an_opening_is_left_when_the_facts_state_no_format(tmp_path: Path) -> None:
    facts = _facts_with(drop=("format:output.glb", "format:input.obj"))
    units = copy.deepcopy(UNITS)
    next(u for u in units["units"] if u["slot"] == "opening")["text"] = SLIDES_OPENING
    world = _World(facts, units, _dispositions(), tmp=tmp_path)
    assert _degrade(world, tmp_path, (SLIDES_OPENING, "opening")) is None  # nothing is invented


# --- the passes -------------------------------------------------------------------------------


def test_the_degrade_may_run_more_than_twice_but_is_bounded() -> None:
    assert 3 <= cascade_module.MAX_DEGRADE_PASSES <= 5


# --- Words Java: "text contains a Markdown heading ('#')" -------------------------------------


def _opening_errors(text: str) -> list[str]:
    facts = api_fixture._facts()
    task = api_fixture._task(facts, "opening")
    output = {
        "units": [{"section": "opening", "slot": "opening", "text": text, "fact_ids": ["identity:repository"]}],
        "omitted": [],
    }
    name = api_fixture.product_name(api_fixture.make_entry())
    return [
        e for e in unit_checks(output, task, facts, name, dispositions=api_fixture._dispositions())
        if "Markdown" in e
    ]


def test_c_sharp_in_the_middle_of_a_unit_is_not_a_markdown_heading() -> None:
    assert _opening_errors("The library ports the C# API of Aspose.Words to Java and reads DOCX files.") == []
    assert _opening_errors("It reads files. # is only a symbol here.") == []


@pytest.mark.parametrize("text", ["# Title of the library", "## Title of the library", "###### Deep heading"])
def test_a_heading_at_the_start_of_a_unit_is_still_refused(text: str) -> None:
    assert _opening_errors(text) == ["unit opening: text contains a Markdown heading ('#')"]


def test_the_schema_pattern_agrees_with_the_check() -> None:
    pattern = re.compile(forbidden_text_pattern())
    assert pattern.match("The port of the C# API reads DOCX files.")
    assert not pattern.match("## Heading")
    assert not pattern.match("# Heading")
    assert not pattern.match("- a list item")
    assert not pattern.match("text with a | table")
