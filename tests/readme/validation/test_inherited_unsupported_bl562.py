"""BL-562: an inherited maintainers' sentence the facts do not support, whose unit also carries other required
identifiers, is withheld without losing them (hosted Lane R refresh, PSD Java run 44898282006).

The two texts are the exact ones of that run, both from the live README of the pinned revision (d808d1db):
F01, the API Reference introduction ("... returns editable per-layer metadata through its getLayers method")
and F06, the maintainers' type-table row for ``ChannelInformation`` ("... is always `Raw`").
The independent review found no fact that supports either, and withholding them added BC-17 (the unit also
carried ``getLayers()``; the table also carried every other row), so both stayed blocking.

Each lever is shown against the real validators, with negative controls: a text no check flags is never
withheld, a flagged text that is the whole unit keeps the earlier lever, an identifier another sentence
still prints is not repeated, and a withholding without the recorded decision is still a BC-17 loss.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import authoring_tasks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import ReviewVerdict
from repo_presenter.readme.validation import must_correct
from repo_presenter.readme.validation.blocking import blocking_failures, validate_candidate
from repo_presenter.readme.validation.must_correct import (
    DEGRADE_WITHHELD_KEY,
    ClaimFlag,
    degrade_claims,
    verdict_flags,
)
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _entry, _facts, _plan, _unit

PKG = "org.aspose.psd"
ROW = (
    "| `ChannelInformation` | Describes one layer channel: its channel id and data length; the compression "
    "value it reports for a loaded channel is always `Raw`. |"
)
OTHER_ROWS = (
    "| `PsdImage` | Entry point for loading a PSD. |",
    "| `Layer` | One layer of the image. |",
)
TABLE = "\n".join(["| Class | Description |", "| --- | --- |", OTHER_ROWS[0], ROW, OTHER_ROWS[1]])
PARAGRAPH = (
    "`PsdImage` is the library's entry point and `Layer` carries the editable per-layer metadata it returns "
    "from `getLayers()`; `ResourceBlock` and `PsdLoadException` cover image resources and load errors."
)
LEAD = "Aspose.PSD FOSS for Java reads and writes PSD files."
F01 = (
    "The `PsdImage` class serves as the library's entry point and returns editable per-layer metadata through "
    "its getLayers method. The `Layer` class carries the per-layer metadata, while `ResourceBlock` and "
    "`PsdLoadException` cover image resources and load errors."
)
ORIGINAL = f"# Old\n\n## API Reference\n\n{PARAGRAPH}\n\n{TABLE}\n"


def _symbol(name: str, kind: str = "class", owner: str = "", member_kind: str = "") -> Fact:
    value = f"{PKG}.{owner + '.' if owner else ''}{name}"
    attributes = {"symbol_kind": kind, "signature": f"public {kind} {name}"}
    if member_kind:
        attributes["member_kind"] = member_kind
    return Fact(
        f"public_symbol:{value.lower()}", "public_symbol", value,
        (Evidence("x.java", "line 1; public by declaration"),), attributes=attributes,
    )


def _enum_member() -> Fact:
    return Fact(
        f"enum_member:{PKG}.compressionmethod.raw".lower(), "enum_member", f"{PKG}.CompressionMethod.Raw",
        (Evidence("x.java", "line 3"),), "SUPPORTED",
    )


def _facts_of() -> FactsDocument:
    base = _facts()
    drop = {"public_symbol:aspose.threed.scene"}
    return FactsDocument(
        base.repository, base.source_revision,
        (
            *[f for f in base.facts if f.id not in drop],
            *[_symbol(n) for n in ("PsdImage", "Layer", "ChannelInformation", "ResourceBlock", "PsdLoadException")],
            _symbol("getLayers", "method", owner="PsdImage", member_kind="method"),
            _enum_member(),
            _unit("010.paragraph", PARAGRAPH),
            _unit("011.table", TABLE),
        ),
    )


CLEAN = (
    "`PsdImage` returns `Layer` objects from getLayers; `ResourceBlock` and `PsdLoadException` cover image "
    "resources and load errors."
)


def _world(*, intro: str | None = CLEAN, table: bool = True, cite: bool = True) -> tuple[Any, ...]:
    facts = _facts_of()
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        _entry("010.paragraph", "VERIFIED_REWRITE", "api_reference", ["public_symbol:org.aspose.psd.psdimage"])
    )
    if table:
        dispositions["dispositions"].append(_entry("011.table", "PRESERVE_ATTRIBUTED", "api_reference", []))
    units = copy.deepcopy(UNITS)
    if intro is not None:
        for unit in units["units"]:
            if unit["slot"] == "intro":
                unit["text"] = intro
                unit["fact_ids"] = (["inherited_unit:010.paragraph"] if cite else []) + [
                    "public_symbol:org.aspose.psd.psdimage", "public_symbol:org.aspose.psd.layer",
                    "public_symbol:org.aspose.psd.resourceblock", "public_symbol:org.aspose.psd.psdloadexception",
                ]
    plan = _plan(hubs=False)
    return facts, plan, units, dispositions, render_readme(ENTRY, facts, plan, units, dispositions)


def _checks(facts: Any, plan: Any, units: Any, dispositions: Any, readme: str, tmp_path: Path) -> dict[str, list[str]]:
    tasks = authoring_tasks(ENTRY, facts, {}, dispositions, plan)
    candidate = cascade_module._candidate(
        ENTRY, facts, plan, units, dispositions, readme, [], tasks, benchmark=ORIGINAL
    )
    validation = validate_candidate(candidate, tmp_path, [])
    return {c["id"]: list(c.get("details") or []) for c in blocking_failures(validation)}


def _degrade(world: tuple[Any, ...], flags: list[ClaimFlag]) -> tuple[Any, Any, Any, list[dict[str, Any]], str]:
    facts, plan, units, dispositions, readme = world
    new_plan, new_units, new_disp, records = degrade_claims(plan, units, dispositions, flags, facts, readme=readme)
    return new_plan, new_units, new_disp, records, render_readme(ENTRY, facts, new_plan, new_units, new_disp)


def _flag(quote: str) -> ClaimFlag:
    return ClaimFlag(quote, "no fact supports it", "llm:factuality")


# --- F06: one row of the maintainers' table, the rest of the table kept ----------------------------


def test_the_flagged_row_is_withheld_and_every_other_row_of_the_table_still_prints(tmp_path: Path) -> None:
    world = _world()
    assert ROW in world[4] and not _checks(*world, tmp_path).get("BC-17")
    _plan_, units, disp, records, readme = _degrade(world, [_flag(ROW)])
    assert [(r["rule"], r["action"], r["slot"]) for r in records] == [
        ("BL-562", "inherited_text_withheld", "inherited_unit:011.table")
    ]
    assert ROW not in readme and "always `Raw`" not in readme
    assert all(row in readme for row in OTHER_ROWS)  # the rest of the unit is the maintainers' text, kept
    [row] = [r for r in disp["dispositions"] if r["unit_id"] == "inherited_unit:011.table"]
    assert row["disposition"] == "PRESERVE_ATTRIBUTED" and row[DEGRADE_WITHHELD_KEY] == [ROW]  # kept, not omitted
    assert "ChannelInformation" in readme  # the type is still in the Core API table, described by its facts
    assert not _checks(world[0], world[1], units, disp, readme, tmp_path).get("BC-17")


def test_without_the_recorded_decision_dropping_the_row_is_still_a_bc17_loss(tmp_path: Path) -> None:
    # negative control: the same README, the disposition without the record
    world = _world()
    _p, units, disp, _r, readme = _degrade(world, [_flag(ROW)])
    stripped = copy.deepcopy(disp)
    for row in stripped["dispositions"]:
        row.pop(DEGRADE_WITHHELD_KEY, None)
    failures = _checks(world[0], world[1], units, stripped, readme, tmp_path)
    assert any("Raw" in detail for detail in failures.get("BC-17", []))


def test_a_row_no_check_flags_is_never_withheld(tmp_path: Path) -> None:
    world = _world()
    _p, units, disp, records, readme = _degrade(world, [_flag(OTHER_ROWS[1])])
    assert [r["slot"] for r in records] == ["inherited_unit:011.table"]
    assert ROW in readme and OTHER_ROWS[1] not in readme  # only the flagged row goes
    _p, units, disp, records, readme = _degrade(world, [])
    assert records == [] and readme == world[4] and disp == world[3]


def test_a_flag_that_is_the_whole_table_keeps_the_whole_unit_omission(tmp_path: Path) -> None:
    world = _world()
    _p, _u, disp, records, readme = _degrade(world, [_flag(TABLE)])
    assert [r["action"] for r in records] == ["inherited_unit_omitted"]
    [row] = [r for r in disp["dispositions"] if r["unit_id"] == "inherited_unit:011.table"]
    assert row["disposition"] == "OMIT_UNSUPPORTED" and DEGRADE_WITHHELD_KEY not in row
    assert ROW not in readme


def test_a_sentence_of_a_kept_maintainers_paragraph_is_withheld_alone() -> None:
    first, second = "The loader reads PSD files.", "It always returns editable layers."
    facts = _facts_of()
    facts = FactsDocument(
        facts.repository, facts.source_revision, (*facts.facts, _unit("012.paragraph", f"{first} {second}"))
    )
    dispositions = _dispositions()
    dispositions["dispositions"].append(_entry("012.paragraph", "VERIFIED_PRESERVE", "api_reference", []))
    plan, units = _plan(hubs=False), copy.deepcopy(UNITS)
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    assert second in readme
    new_plan, new_units, new_disp, records = degrade_claims(plan, units, dispositions, [_flag(second)], facts, readme=readme)
    out = render_readme(ENTRY, facts, new_plan, new_units, new_disp)
    assert [r["action"] for r in records] == ["inherited_text_withheld"]
    assert first in out and second not in out


# --- F01: an authored sentence restating a maintainers' paragraph ----------------------------------


def test_the_sentence_is_withheld_and_the_identifier_only_it_printed_is_kept(tmp_path: Path) -> None:
    world = _world(intro=f"{LEAD} {F01}")
    assert "editable per-layer metadata" in world[4]
    _p, units, disp, records, readme = _degrade(world, [_flag(F01)])
    assert [(r["rule"], r["action"], r["slot"]) for r in records] == [("BL-240", "sentence_rewritten", "intro")]
    assert "editable" not in readme.split("## API Reference")[1].split("<details>")[0]
    assert LEAD in readme  # the sentence before it is printed as written
    assert "The public API includes the `getLayers` method of `PsdImage`." in readme
    [intro] = [u for u in units["units"] if u["slot"] == "intro"]
    assert "public_symbol:org.aspose.psd.psdimage.getlayers" in intro["fact_ids"]
    assert "inherited_unit:010.paragraph" in intro["fact_ids"]  # still the carrier of the maintainers' paragraph
    assert not _checks(world[0], world[1], units, disp, readme, tmp_path).get("BC-17")


def test_plain_withholding_of_that_sentence_is_the_bc17_loss_the_clause_prevents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # negative control: the earlier lever (no clause) drops the sentence and loses getLayers()
    monkeypatch.setattr(must_correct, "_identifier_clause", lambda *a, **k: ("", []))
    facts, plan, units, dispositions, readme = _world(intro=f"{LEAD} {F01}")
    new_plan, new_units, new_disp, _records = degrade_claims(
        plan, units, dispositions, [_flag(F01)], facts, readme=readme
    )
    out = render_readme(ENTRY, facts, new_plan, new_units, new_disp)
    failures = _checks(facts, new_plan, new_units, new_disp, out, tmp_path)
    assert any("getLayers" in detail for detail in failures.get("BC-17", []))


def test_an_identifier_another_sentence_still_prints_is_not_repeated(tmp_path: Path) -> None:
    kept = "Call getLayers to list the layers."
    world = _world(intro=f"{kept} {F01}")
    _p, units, disp, records, readme = _degrade(world, [_flag(F01)])
    assert [r["action"] for r in records] == ["sentence_withheld"]
    assert "The public API includes" not in readme and kept in readme


def test_the_clause_does_not_depend_on_the_unit_citing_the_maintainers_paragraph(tmp_path: Path) -> None:
    # the benchmark's identifiers are owed whichever unit carries them (BC-17 reads the published README)
    world = _world(intro=f"{LEAD} {F01}", cite=False)
    _p, units, disp, records, readme = _degrade(world, [_flag(F01)])
    assert [r["action"] for r in records] == ["sentence_rewritten"]
    assert "The public API includes the `getLayers` method of `PsdImage`." in readme
    assert not _checks(world[0], world[1], units, disp, readme, tmp_path).get("BC-17")


def test_an_identifier_the_maintainers_never_wrote_is_not_added() -> None:
    sentence = "The `PsdImage` class exposes an editable `getHistory` view of every layer."
    facts = _facts_of()
    facts = FactsDocument(
        facts.repository, facts.source_revision,
        (*facts.facts, _symbol("getHistory", "method", owner="PsdImage", member_kind="method")),
    )
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        _entry("010.paragraph", "VERIFIED_REWRITE", "api_reference", ["public_symbol:org.aspose.psd.psdimage"])
    )
    plan, units = _plan(hubs=False), copy.deepcopy(UNITS)
    for unit in units["units"]:
        if unit["slot"] == "intro":
            unit["text"] = f"{LEAD} {sentence}"
            unit["fact_ids"] = ["inherited_unit:010.paragraph", "public_symbol:org.aspose.psd.psdimage"]
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    _p, _u, _d, records = degrade_claims(plan, units, dispositions, [_flag(sentence)], facts, readme=readme)
    assert [r["action"] for r in records] == ["sentence_withheld"]  # getHistory is not in the maintainers' text


def test_a_flagged_carrier_paragraph_keeps_its_identifiers_instead_of_being_refused(tmp_path: Path) -> None:
    world = _world(intro=F01)  # the unit is nothing but the flagged paragraph and cites the maintainers' unit
    _p, units, disp, records, readme = _degrade(world, [_flag(F01)])
    assert [r["action"] for r in records] == ["unit_rewritten"]
    assert "editable" not in readme.split("<details>")[0]
    assert "The public API includes the `getLayers` method of `PsdImage`." in readme
    assert not _checks(world[0], world[1], units, disp, readme, tmp_path).get("BC-17")


def test_a_flagged_carrier_with_no_identifier_to_keep_is_left_for_the_checks() -> None:
    plain = "Everything here is editable."
    world = _world(intro=plain)
    _p, units, _d, records, _readme = _degrade(world, [_flag(plain)])
    assert records == [] and [u for u in units["units"] if u["slot"] == "intro"][0]["text"] == plain


# --- through the cascade's own step ----------------------------------------------------------------


def test_the_cascade_degrade_keeps_the_candidate_that_withholds_the_row(tmp_path: Path) -> None:
    facts, plan, units, dispositions, readme = _world()
    tasks = authoring_tasks(ENTRY, facts, {}, dispositions, plan)
    candidate = cascade_module._candidate(ENTRY, facts, plan, units, dispositions, readme, [], tasks, benchmark=ORIGINAL)
    validation = validate_candidate(candidate, tmp_path, [])
    finding = Finding(
        rule="factuality", source="llm", claim_kind="unsupported_claim", message="no fact", quote=ROW,
        finding_id="F06", section_id="api_reference", causal_stage="S6", criterion="factuality",
    )
    assert [f.quote for f in verdict_flags([finding])] == [ROW]
    verdict = ReviewVerdict.folded([finding])
    composed = cascade_module._Composition(dispositions, plan, units, units, readme, tasks, [], None)
    settled = cascade_module._Settled(composed, validation, verdict, 1)
    degraded = cascade_module._degrade_settled(
        settled, verdict, entry=ENTRY, document=facts, investigation={}, tree_paths=[], original=ORIGINAL,
        out_dir=tmp_path,
    )
    assert degraded is not None
    assert ROW not in degraded.composed.readme and OTHER_ROWS[0] in degraded.composed.readme
    assert not [c for c in blocking_failures(degraded.validation) if c["id"] == "BC-17"]
    [row] = [r for r in degraded.composed.dispositions["dispositions"] if r["unit_id"] == "inherited_unit:011.table"]
    assert row[DEGRADE_WITHHELD_KEY] == [ROW]
    assert (tmp_path / "dispositions.json").read_text(encoding="utf-8").count(DEGRADE_WITHHELD_KEY) == 1
