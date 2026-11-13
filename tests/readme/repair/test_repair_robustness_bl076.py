"""BL-076: the repair failure classes of hosted Lane R runs 43473807336 (Cells C++), 43473803090
(Cells .NET), 43473790998 (3D .NET) and 43473796319 (3D Python), from their real logged shapes.

* R1 -- a stored S4 batch broke its own contract: the unproven-build omission's code-written
  rationale (228 characters) exceeded the reconciliation contract's ``maxLength`` 160, so every
  merged patch was rejected "revised_output.dispositions[19].rationale: '...' is too long".
* R2/R3 -- a BC-18 quote is README text, carrying the code spans the renderer adds to an authored
  unit, so it never matched the unit that printed it; only the first failure quote of a merged
  validation record was routed; and a line the renderer printed from a fact's docstring was sent
  to the model, which answered unchanged (the no-op refusal) or was recorded "no stored
  disposition ...". Renderer-printed lines are now facts defects, recorded with no call.
* R4 -- a maintainers' table/list holding rows the findings register confirmed false could be
  neither kept (BC-18) nor superseded (BC-05/BC-17); it now prints without exactly those rows.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from repo_presenter.cascade import DEFAULT_PROMPTS_PATH
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.reconciliation import dispositions as disp
from repo_presenter.readme.repair import loop as loop_module
from repo_presenter.readme.repair.restore_units import restore_lost_units
from repo_presenter.readme.repair.targeted import Defect, RepairLedger, validation_defects
from repo_presenter.readme.validation import must_correct
from repo_presenter.readme_findings import FindingRecord

# --- R1: rationale bound ---------------------------------------------------------------------

#: Verbatim from run 43473807336's log (the rationale the old fold wrote).
LOGGED_RATIONALE = (
    "The build steps in this block are contradicted by the measured build of this checkout, which "
    "did not exit 0 (BC-02 forbids presenting an unproven source build); the Installation section "
    "states only what the repository documents."
)


def _contract() -> dict[str, Any]:
    return load_manifests(DEFAULT_PROMPTS_PATH)["source_reconciliation"].manifest.output.schema_


def test_every_code_written_omission_rationale_fits_the_contract() -> None:
    limit = _contract()["properties"]["dispositions"]["items"]["properties"]["rationale"][
        "maxLength"
    ]
    assert limit == disp._RATIONALE_LIMIT
    for text in (
        disp.UNPROVEN_BUILD_RATIONALE,
        disp.NO_MANIFEST_RATIONALE,
        disp.UNPUBLISHED_RATIONALE,
    ):
        assert len(text) <= limit, text
    # BC-17 reads "contradicted" as the mark of an evidence-backed omission (parity_gate).
    assert "ontradicted" in disp.UNPROVEN_BUILD_RATIONALE
    assert "ontradicted" in disp.NO_MANIFEST_RATIONALE


def _batch(rationale: str) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:060.code_block",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": ["install_command:source"],
                "rationale": rationale,
            }
        ]
    }


def test_the_logged_stored_rationale_is_bounded_honestly() -> None:
    stored = _batch(LOGGED_RATIONALE)
    rationale_schema = _contract()["properties"]["dispositions"]["items"]["properties"][
        "rationale"
    ]
    validator = Draft202012Validator(rationale_schema)
    assert list(validator.iter_errors(LOGGED_RATIONALE))  # the logged rejection
    assert disp.bound_rationales(stored) == ["inherited_unit:060.code_block"]
    bounded = stored["dispositions"][0]["rationale"]
    assert not list(validator.iter_errors(bounded))
    assert bounded.startswith("The build steps in this block are contradicted")
    assert bounded.endswith("...")


def test_a_rationale_within_the_bound_is_byte_identical() -> None:
    # RECOVERED_COVERAGE_RATIONALE is matched exactly (placement_errors), trailing space included.
    stored = _batch(disp.RECOVERED_COVERAGE_RATIONALE)
    assert disp.bound_rationales(stored) == []
    assert stored["dispositions"][0]["rationale"] == disp.RECOVERED_COVERAGE_RATIONALE


def test_a_repair_reply_rejected_only_for_its_rationale_length_is_bounded() -> None:
    recover = loop_module.bounding_rationales(None)
    reply = {"revised_output": _batch(LOGGED_RATIONALE)}
    assert recover(reply) is reply
    assert len(reply["revised_output"]["dispositions"][0]["rationale"]) <= 160
    assert recover({"revised_output": _batch("short")}) is None


# --- R2/R3: mapping a BC-18 quote to what printed it -----------------------------------------

#: Cells C++ (run 43473807336): the authored Scope and Limitations unit as stored (no code spans)
#: and the register quote as the README prints it.
CPP_LIMITATION = (
    "Only .xlsx (OOXML) is supported for load and save. LoadFormat and SaveFormat each declare a "
    "single Xlsx member, and saving to any other format throws UnsupportedFeatureException."
)
CPP_QUOTE = "`LoadFormat` and `SaveFormat` each declare a single Xlsx member"
#: Cells .NET (run 43473803090): the authored samples link unit, its register quote, and a member
#: bullet the renderer prints from ``public_symbol:aspose.cells_foss.style.borders``'s docstring.
NET_SAMPLES = (
    "The samples directory contains example projects demonstrating how to use Aspose.Cells.FOSS "
    "version 26.10.0 to work with spreadsheet files in .NET applications."
)
NET_SAMPLES_QUOTE = "example projects demonstrating how to use `Aspose.Cells.FOSS` version 26.10.0"
BORDERS_QUOTE = "- `Borders`: Gets or sets border settings."
FONT_QUOTE = "- `Font`: Gets or sets the font settings."
BORDERS = "public_symbol:aspose.cells_foss.style.borders"
FONT = "public_symbol:aspose.cells_foss.style.font"

SCOPE = SectionTask("scope_limitations", {}, frozenset(), ("scope", "limitation:1"))
DOCS = SectionTask("documentation_resources", {}, frozenset(), ("link:link_target:019",))
API = SectionTask("api_reference", {}, frozenset(), ("intro", "hub:public_symbol:style"))
STORED = {
    SCOPE.label: {"units": [{"slot": "limitation:1", "text": CPP_LIMITATION}]},
    DOCS.label: {"units": [{"slot": "link:link_target:019", "text": NET_SAMPLES}]},
    API.label: {
        "units": [
            {"slot": "intro", "text": "The main entry points."},
            {"slot": "hub:public_symbol:style", "text": "The Style class formats cells."},
        ]
    },
}


def _symbol(fact_id: str, value: str, docstring: str) -> Fact:
    return Fact(
        fact_id,
        "public_symbol",
        value,
        (Evidence("src/Aspose.Cells_FOSS/Style.cs", "line 73; method"),),
        attributes={"docstring": docstring, "symbol_kind": "method"},
    )


FACTS = FactsDocument(
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "f" * 40,
    (
        _symbol(BORDERS, "Aspose.Cells_FOSS.Style.Borders", "Gets or sets border settings."),
        _symbol(FONT, "Aspose.Cells_FOSS.Style.Font", "Gets or sets the font settings."),
    ),
)


class _Store:
    def get(self, key: str) -> dict[str, Any] | None:
        return STORED.get(key)


@pytest.fixture()
def rc(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(loop_module, "reconciliation_batches", lambda facts, tokens: {})
    monkeypatch.setattr(loop_module, "placements", lambda *args, **kwargs: [])
    monkeypatch.setattr(loop_module, "patch_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(loop_module, "_task_key", lambda rc, loaded, task: task.label)
    manifest = SimpleNamespace(sampling=SimpleNamespace(max_output_tokens=1000))
    prompts = {
        "source_reconciliation": SimpleNamespace(manifest=manifest),
        "targeted_repair": SimpleNamespace(manifest=manifest),
        "section_authoring": None,
    }
    return SimpleNamespace(
        tasks=[API, SCOPE, DOCS],
        store=_Store(),
        facts=FACTS,
        plan={},
        dispositions={},
        investigation={},
        entry=SimpleNamespace(ecosystem="dotnet"),
        prompts=prompts,
    )


def _failure(quote: str, section: str | None, unit: str | None = None) -> dict[str, Any]:
    return {
        "section_id": section,
        "causal_stage": "RECONCILING" if unit else "COMPOSING",
        "detail": f"open finding still printed: {quote}",
        **({"unit_id": unit} if unit else {}),
        "quote": quote,
        "instruction": f"correct {quote}",
    }


def _bc18(*failures: dict[str, Any], stage: str = "RECONCILING") -> list[Defect]:
    validation = {
        "validator_version": "v",
        "checks": [
            {
                "id": "BC-18",
                "name": "must-correct",
                "verdict": "FAIL",
                "causal_stage": stage,
                "details": [f["detail"] for f in failures],
                "failures": list(failures),
            }
        ],
    }
    return validation_defects(validation, {"api_reference", "scope_limitations", "documentation_resources"})


def _recording(seen: list[Any]) -> Any:
    def fake(rc: Any, defect: Defect, task: SectionTask, repairs: Any, named: Any = ()) -> bool:
        seen.append((task.label, [f["quote"] for f in loop_module._quoted_findings(defect.record)]))
        repairs.record(defect, "repaired", changes=[{"after": "x"}])
        return True

    return fake


def test_a_quote_with_renderer_code_spans_maps_to_its_authored_unit(
    rc: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Any] = []
    monkeypatch.setattr(loop_module, "_repair_task", _recording(seen))
    (unitless,) = [
        d
        for d in _bc18(
            _failure("inherited", None, "inherited_unit:050.list"),
            _failure(CPP_QUOTE, "scope_limitations"),
        )
        if d.record["failures"][0].get("unit_id") is None
    ]
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert loop_module.repair_defect(rc, unitless, repairs) is True
    assert seen == [(SCOPE.label, [CPP_QUOTE])]


def test_every_failure_quote_of_a_merged_group_is_routed_and_renderer_lines_are_facts_defects(
    rc: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cells .NET's unit-less S4 group: it led with the renderer-printed Borders bullet, so the
    authored samples quote behind it was never routed."""
    seen: list[Any] = []
    monkeypatch.setattr(loop_module, "_repair_task", _recording(seen))
    (unitless,) = [
        d
        for d in _bc18(
            _failure("It runs on Windows", None, "inherited_unit:005.paragraph"),
            _failure(BORDERS_QUOTE, "api_reference"),
            _failure(FONT_QUOTE, "api_reference"),
            _failure(NET_SAMPLES_QUOTE, "documentation_resources"),
        )
        if d.record["failures"][0].get("unit_id") is None
    ]
    assert unitless.record["quote"] == BORDERS_QUOTE  # only the first quote is the record's own
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert loop_module.repair_defect(rc, unitless, repairs) is True
    assert seen == [(DOCS.label, [NET_SAMPLES_QUOTE])]
    entry = repairs.attempts[unitless.fingerprint]
    assert entry["outcome"] == "repaired"
    assert entry["facts_defects"] == [
        {"quote": BORDERS_QUOTE, "fact_ids": [BORDERS]},
        {"quote": FONT_QUOTE, "fact_ids": [FONT]},
    ]
    assert f"printed by the renderer from fact {BORDERS}" in entry["reason"]


def test_an_s6_defect_of_renderer_printed_lines_only_makes_no_call(
    rc: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The no-op class: api_reference's BC-18 lines were all member bullets from facts."""

    def never(*args: Any, **kwargs: Any) -> bool:
        raise AssertionError("a renderer-printed line must never reach the model")

    monkeypatch.setattr(loop_module, "_repair_task", never)
    (defect,) = _bc18(
        _failure(BORDERS_QUOTE, "api_reference"),
        _failure(FONT_QUOTE, "api_reference"),
        stage="COMPOSING",
    )
    assert defect.stage == "S6" and defect.section_id == "api_reference"
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert loop_module.repair_defect(rc, defect, repairs) is False
    entry = repairs.attempts[defect.fingerprint]
    assert entry["outcome"] == "unrepairable"
    assert [item["fact_ids"] for item in entry["facts_defects"]] == [[BORDERS], [FONT]]
    assert entry["reason"].startswith("facts defect:")


def test_a_quote_nothing_prints_and_no_fact_renders_stays_as_before(
    rc: Any, tmp_path: Any
) -> None:
    (unitless,) = [
        d
        for d in _bc18(
            _failure("inherited", None, "inherited_unit:050.list"),
            _failure("text nothing prints", "api_reference"),
        )
        if d.record["failures"][0].get("unit_id") is None
    ]
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert loop_module.repair_defect(rc, unitless, repairs) is False
    entry = repairs.attempts[unitless.fingerprint]
    assert "no stored disposition" in entry["reason"]
    assert "facts_defects" not in entry


def test_the_unit_a_code_spanned_quote_names_may_change() -> None:
    original = STORED[SCOPE.label]
    assert loop_module._flagged_slots(original, [CPP_QUOTE]) == {"limitation:1"}
    guarded = loop_module.keep_unflagged_units(lambda revised: [], original, [CPP_QUOTE])
    revised = {"units": [{"slot": "limitation:1", "text": "Only .xlsx is supported."}]}
    assert guarded(revised) == []


# --- R4: a kept table/list without exactly its register-false rows ---------------------------

#: 3D .NET 050.table (run 43473790998), real rows; the FileFormat and Chunk rows are OPEN register
#: quotes.
TABLE_3D_NET = "\n".join(
    [
        "| Class | Description |",
        "|---|---|",
        "| `AnimationChannel` | Stores a sequence of keyframes and provides `Add(time, value)` to "
        "insert new keyframe data. |",
        "| `Chunk` | Represents a 3DS chunk header. |",
        "| `FileFormat` | File format registry — `Detect`/`GetFormatByExtension` plus per-format "
        "static members (`WavefrontOBJ`, `STLBinary`, `GLTF2`, `Collada`, `Discreet3DS`, "
        "`Microsoft3MF`) used with `Scene.Save()`/`FromFile()`. |",
    ]
)
CHUNK_QUOTE = "`Chunk` | Represents a 3DS chunk header. |"
FILEFORMAT_QUOTE = (
    "per-format static members (`WavefrontOBJ`, `STLBinary`, `GLTF2`, `Collada`, `Discreet3DS`, "
    "`Microsoft3MF`)"
)
#: 3D Python 010.list (run 43473796319), its register-false item and a true one.
LIST_3D_PY = (
    "- Triangulate arbitrary polygon data into triangle fans with\n"
    "  `Mesh.polygons`, or convert an existing mesh with `PolygonModifier.triangulate()`.\n"
    "- Read and write `.3mf` scenes."
)
TRIANGULATE_QUOTE = "Triangulate arbitrary polygon data into triangle fans"


def test_a_table_prints_without_exactly_its_register_false_rows() -> None:
    printed = must_correct.withheld_form(
        "inherited_unit:050.table", TABLE_3D_NET, [CHUNK_QUOTE, FILEFORMAT_QUOTE]
    )
    assert "Chunk" not in printed and "STLBinary" not in printed
    assert "`Add(time, value)`" in printed and printed.startswith("| Class | Description |")
    assert must_correct.omission_holds(
        "inherited_unit:050.table", TABLE_3D_NET, [CHUNK_QUOTE, FILEFORMAT_QUOTE]
    )
    # A table every body row of which is false is withheld, never kept empty.
    assert not must_correct.omission_holds(
        "inherited_unit:050.table", "\n".join(TABLE_3D_NET.split("\n")[:2] + [
            "| `Chunk` | Represents a 3DS chunk header. |"
        ]), [CHUNK_QUOTE]
    )


def test_a_list_prints_without_exactly_its_register_false_item() -> None:
    printed = must_correct.withheld_form("inherited_unit:010.list", LIST_3D_PY, [TRIANGULATE_QUOTE])
    assert printed == "- Read and write `.3mf` scenes."
    assert must_correct.withheld_text_holds(
        "inherited_unit:010.list", LIST_3D_PY, [TRIANGULATE_QUOTE], "Mesh.polygons"
    )


def _register(monkeypatch: pytest.MonkeyPatch, repository: str, *quotes: str) -> list[str]:
    rows = {}
    for quote in quotes:
        row = FindingRecord(
            repository, f"confirmed false claim: {quote}", "src/x.cs:1@0", "lane_r", "OPEN", "2026-11-13",
            quote=quote, truth="it is not",
        )
        rows[row.citation_id()] = row
    monkeypatch.setattr(must_correct, "open_finding_citations", lambda repo, path=None: rows)
    return list(rows)


def test_the_zero_call_restore_keeps_the_table_citing_its_register_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
    cited = _register(monkeypatch, repository, CHUNK_QUOTE, FILEFORMAT_QUOTE)
    unit = Fact(
        "inherited_unit:050.table", "inherited_unit", TABLE_3D_NET,
        (Evidence("README.md", None),), attributes={"section": "Aspose.3D FOSS for .NET > API"},
    )
    facts = FactsDocument(repository, "0" * 40, (unit,))
    stored = {
        "dispositions": [
            {
                "unit_id": unit.id,
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "api_reference",
                "fact_ids": [],
                "rationale": "The Core API table lists these types.",
            }
        ]
    }
    restored, changes = restore_lost_units(stored, facts, [unit.id], ["api_reference"])
    (entry,) = restored["dispositions"]
    assert changes and entry["disposition"] == "PRESERVE_ATTRIBUTED"
    assert entry["destination_section"] == "api_reference"
    assert entry["fact_ids"] == cited
    # What the renderer will print for it: the true rows, without the confirmed-false ones.
    quotes = must_correct.cited_finding_quotes(entry["fact_ids"], repository)
    printed = must_correct.withheld_rows_form(unit.id, TABLE_3D_NET, quotes)
    assert CHUNK_QUOTE not in printed and "Add(time, value)" in printed
