"""BL-240: the last-resort, recorded degrade of one flagged authored sentence, row or inherited unit.

Every flagged text is the exact one of a hosted Lane R failure record of 2026-11-18 (runs 44349049455
3D .NET/Transform, 44349019101 3D Python/Scene, 44349044054 3D Java/.fbx, 44349039315 Words .NET):
the model's repair was refused or returned the same text twice, and the candidate failed whole for
one sentence. Each shape is shown withheld at its origin with an R14 record, then passing the check
that flagged it; negative controls show a passing README, a must-carry unit and a worse outcome are
left exactly as they were.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import authoring_tasks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.independent_reviewer import review_candidate
from repo_presenter.readme.validation import must_correct
from repo_presenter.readme.validation.blocking import blocking_failures, validate_candidate
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.must_correct import (
    DEGRADE_RECORDS_KEY,
    DEGRADED_QUOTES_KEY,
    ClaimFlag,
    claim_flags,
    degrade_claims,
    verdict_flags,
)
from tests.readme.repair.test_accounting import (
    ENTRY,
    UNITS,
    _dispositions,
    _entry,
    _facts,
    _plan,
    _unit,
)

SCENE = (
    "The Scene class provides high-level methods such as Scene.open() and Scene.save() to load and "
    "write 3D content, and exposes properties like Scene.root_node, Scene.animation_clips, "
    "Scene.asset_info, Scene.clear, Scene.create_animation_clip, and Scene.get_animation_clip for "
    "scene graph management and animation handling."
)
TRANSFORM = (
    "Transform class provides transformation properties including Euler angles, geometric "
    "rotation, scaling, translation, and property access."
)
FBX = "The library can import `.fbx` files and can export `.fbx` files."


def _type(value: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}", "public_symbol", value,
        (Evidence("x.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "signature": f"class {value.rsplit('.', 1)[-1]}"},
    )


def _member(owner: str, name: str, kind: str) -> Fact:
    value = f"{owner}.{name}"
    attributes = {"symbol_kind": "method", "member_kind": kind, "signature": f"def {name}(self)"}
    if kind == "property":
        attributes["settable"] = "true"
    return Fact(
        f"public_symbol:{value.lower()}", "public_symbol", value,
        (Evidence("x.py", "line 2; method; public by name"),), attributes=attributes,
    )


def _fact(identifier: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str) -> Fact:
    return Fact(identifier, kind, value, (Evidence("src/x"),), polarity=polarity, attributes=attributes or None)  # type: ignore[arg-type]


def _facts_with(*extra: Fact, drop: tuple[str, ...] = ()) -> FactsDocument:
    base = _facts()
    return FactsDocument(
        base.repository, base.source_revision,
        (*[f for f in base.facts if f.id not in drop], *extra),
    )


def _scene_facts() -> FactsDocument:
    scene = "aspose.threed.Scene"
    return _facts_with(
        _type(scene),
        *[_member(scene, n, "property") for n in ("root_node", "animation_clips", "asset_info")],
        *[_member(scene, n, "method") for n in ("clear", "create_animation_clip", "get_animation_clip", "open", "save")],
        drop=("public_symbol:aspose.threed.scene",),
    )


def _units_with(slot_prefix: str, text: str) -> dict[str, Any]:
    units = copy.deepcopy(UNITS)
    for unit in units["units"]:
        if unit["slot"].startswith(slot_prefix):
            unit["text"] = text
    return units


class _World:
    """One rendered candidate judged by the real validators and deterministic reviewer."""

    def __init__(self, facts: FactsDocument, units: dict[str, Any], dispositions: dict[str, Any],
                 plan: dict[str, Any] | None = None, tmp: Path | None = None) -> None:
        self.facts, self.units, self.dispositions = facts, units, dispositions
        self.plan = plan or _plan()
        self.tmp = tmp
        self.readme = render_readme(ENTRY, facts, self.plan, units, dispositions)

    def judge(self, readme: str | None = None) -> tuple[dict[str, Any], Any]:
        readme = readme if readme is not None else self.readme
        tasks = authoring_tasks(ENTRY, self.facts, {}, self.dispositions, self.plan)
        candidate = cascade_module._candidate(
            ENTRY, self.facts, self.plan, self.units, self.dispositions, readme, [], tasks, benchmark=""
        )
        validation = validate_candidate(candidate, self.tmp or Path("."), [])
        verdict = review_candidate(
            readme_text=readme, units=self.units["units"], facts=self.facts,
            dispositions=self.dispositions, original_readme="",
        )
        return validation, verdict

    def settled(self) -> cascade_module._Settled:
        validation, verdict = self.judge()
        tasks = authoring_tasks(ENTRY, self.facts, {}, self.dispositions, self.plan)
        composed = cascade_module._Composition(
            self.dispositions, self.plan, self.units, self.units, self.readme, tasks, [], None
        )
        return cascade_module._Settled(composed, validation, verdict, 1)


def _ids(validation: dict[str, Any]) -> set[str]:
    return {c["id"] for c in blocking_failures(validation)}


def _degrade(world: _World, tmp_path: Path) -> cascade_module._Settled | None:
    settled = world.settled()
    return cascade_module._degrade_settled(
        settled, settled.verdict, entry=ENTRY, document=world.facts, investigation={},
        tree_paths=[], original="", out_dir=tmp_path,
    )


# --- authored: 3D Python Scene.clear (BC-14, claim_contradiction x3, repair 'unrepairable') ----


def test_a_hub_that_is_only_the_member_kind_sentence_falls_back_to_the_fact_true_row(
    tmp_path: Path,
) -> None:
    world = _World(_scene_facts(), _units_with("hub:", SCENE), _dispositions(), tmp=tmp_path)
    assert "BC-14" in _ids(world.judge()[0]) and "exposes properties like" in world.readme
    degraded = _degrade(world, tmp_path)
    assert degraded is not None
    assert "BC-14" not in _ids(degraded.validation)
    assert not [f for f in degraded.verdict.blocking_findings if f.rule == "claim_contradiction"]
    assert "exposes properties like" not in degraded.composed.readme
    assert "Defined as `class Scene`." in degraded.composed.readme  # the renderer's fact-true row
    [omitted] = degraded.composed.coherent_units["omitted"]
    assert omitted["fact_id"] == "public_symbol:aspose.threed.scene" and "BL-240" in omitted["reason"]
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["rule"] == "BL-240" and record["action"] == "api_row_fallback"
    # the artifacts the seal reads carry the decision
    assert json.loads((tmp_path / "content_units.coherent.json").read_text())[DEGRADE_RECORDS_KEY]
    assert (tmp_path / "README.coherent.md").read_text() == degraded.composed.readme


# --- authored: 3D .NET Transform / Euler (BC-14 rule o) ----------------------------------------


def _transform_facts() -> FactsDocument:
    owner = "aspose.threed.Transform"
    return _facts_with(
        _type(owner),
        *[_member(owner, n, "property") for n in ("translation", "scaling", "rotation", "transform_matrix")],
    )


def test_only_the_flagged_sentence_of_a_longer_unit_is_withheld(tmp_path: Path) -> None:
    other = "Scene holds the graph and its nodes."
    world = _World(
        _transform_facts(), _units_with("hub:", f"{other} {TRANSFORM}"), _dispositions(), tmp=tmp_path
    )
    [flag, *_] = claim_flags(world.readme, world.facts)
    assert flag.quote.startswith("`Transform` class provides") and other not in flag.quote
    assert "Euler" in flag.detail
    degraded = _degrade(world, tmp_path)
    assert degraded is not None and "BC-14" not in _ids(degraded.validation)
    assert "Euler" not in degraded.composed.readme and "holds the graph and its nodes." in degraded.composed.readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "sentence_withheld"


# --- inherited: 3D Java .fbx input/output claims reachable only through a stub (BC-14) ----------


def _fbx_world(tmp_path: Path, *, cite: bool = False) -> _World:
    facts = _facts_with(
        _fact("format:input.fbx", "format", ".fbx", "UNRESOLVED", code_path="stub"),
        _fact("format:output.fbx", "format", ".fbx", "UNRESOLVED", code_path="stub"),
        _unit("007.paragraph", FBX),
    )
    dispositions = _dispositions()
    dispositions["dispositions"].append(_entry("007.paragraph", "VERIFIED_PRESERVE", "scope_limitations", []))
    units = copy.deepcopy(UNITS)
    if cite:
        units["units"][0]["fact_ids"] = ["inherited_unit:007.paragraph"]
    return _World(facts, units, dispositions, tmp=tmp_path)


def test_an_inherited_unit_claiming_a_stub_format_is_omitted_with_a_record(tmp_path: Path) -> None:
    world = _fbx_world(tmp_path)
    flags = claim_flags(world.readme, world.facts)
    assert {f.unit for f in flags} == {"inherited_unit:007.paragraph"}
    assert any("claims .fbx input" in f.detail for f in flags)
    assert any("claims .fbx output" in f.detail for f in flags)
    degraded = _degrade(world, tmp_path)
    assert degraded is not None and "BC-14" not in _ids(degraded.validation)
    assert ".fbx" not in degraded.composed.readme
    [row] = [
        r for r in degraded.composed.dispositions["dispositions"]
        if r["unit_id"] == "inherited_unit:007.paragraph"
    ]
    assert row["disposition"] == "OMIT_UNSUPPORTED" and row["destination_section"] is None
    assert row["fact_ids"] == ["format:input.fbx"]  # an omission cites the fact that shows why
    assert "BL-240" in row["rationale"] and "contradict" in row["rationale"]
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "inherited_unit_omitted" and record["slot"] == "inherited_unit:007.paragraph"
    # the omission is a decision every reader accepts: the recertification fold leaves it alone
    from repo_presenter.recertify import current_dispositions

    again = current_dispositions(degraded.composed.dispositions, world.facts, degraded.composed.plan)
    assert [r for r in again["dispositions"] if r["unit_id"] == row["unit_id"]] == [row]


def test_a_must_carry_inherited_unit_is_never_omitted(tmp_path: Path) -> None:
    world = _fbx_world(tmp_path, cite=True)  # an authored unit cites it: it is its carrier
    plan, units, dispositions, records = degrade_claims(
        world.plan, world.units, world.dispositions, claim_flags(world.readme, world.facts), world.facts
    )
    assert records == [] and dispositions == world.dispositions and units == world.units
    assert _degrade(world, tmp_path) is None  # nothing applies: exactly as it was


def test_an_authored_unit_citing_an_inherited_unit_is_not_dropped_whole() -> None:
    unit = {"slot": "capability:1", "section": "key_capabilities", "text": FBX,
            "fact_ids": ["inherited_unit:007.paragraph"]}
    plan, units, records = {"core_capabilities": [{"title": "T"}]}, {"units": [unit], "omitted": []}, []
    flags = [ClaimFlag(FBX, "d", "BC-14")]
    _p, new_units, _d, records = degrade_claims(plan, units, {"dispositions": []}, flags, _facts())
    assert records == [] and new_units["units"] == [unit]


# --- authored capability: the Export bullet of 3D Python (.dae output, stub) -----------------------


def test_a_capability_that_is_only_the_flagged_text_leaves_the_plan() -> None:
    row = "It exports scenes to `.3mf`, `.dae`, `.glb`, `.gltf`, `.obj`, and `.stl` formats using `Scene.save()`."
    facts = _facts_with(
        _fact("format:output.dae", "format", ".dae", "UNRESOLVED", code_path="stub"),
        _fact("format:input.dae", "format", ".dae"),
        *[_fact(f"format:output.{x}", "format", f".{x}") for x in ("3mf", "gltf", "obj", "stl")],
    )
    units = _units_with("capability:2", row)
    plan = _plan()
    readme = render_readme(ENTRY, facts, plan, units, _dispositions())
    flags = claim_flags(readme, facts)
    assert flags and all(".dae output" in f.detail for f in flags)
    new_plan, new_units, _d, records = degrade_claims(plan, units, _dispositions(), flags, facts)
    assert [r["action"] for r in records] == ["capability_dropped"]
    assert len(new_plan["core_capabilities"]) == len(plan["core_capabilities"]) - 1
    assert row not in [u["text"] for u in new_units["units"]]
    assert not [f for f in claim_findings(render_readme(ENTRY, facts, new_plan, new_units, _dispositions()), facts)
                if ".dae output" in f.detail]


# --- printed text no unit owns: a Core API row the renderer prints from the docstring ------------


def test_a_docstring_row_flagged_by_a_check_prints_its_fact_true_description() -> None:
    owner = "aspose.threed.Transform"
    docstring = TRANSFORM
    typ = Fact(
        f"public_symbol:{owner.lower()}", "public_symbol", owner,
        (Evidence("x.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "signature": "class Transform", "docstring": docstring},
    )
    facts = _facts_with(typ, *[_member(owner, n, "property") for n in ("translation", "scaling")])
    plan, units, dispositions = _plan(), copy.deepcopy(UNITS), _dispositions()
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    flags = claim_flags(readme, facts)
    assert flags and "Euler" in flags[0].detail and flags[0].quote.startswith("| `Transform` |")
    new_plan, new_units, _d, records = degrade_claims(plan, units, dispositions, flags, facts)
    assert [r["action"] for r in records] == ["printed_text_withheld"]
    assert new_units[DEGRADED_QUOTES_KEY] == [flags[0].quote]
    out = render_readme(ENTRY, facts, new_plan, new_units, dispositions)
    assert "Euler" not in out and "| `Transform` |" in out  # the row stays, described by the facts


# --- negative controls ------------------------------------------------------------------------


def test_a_passing_readme_is_never_touched(tmp_path: Path) -> None:
    world = _World(_facts(), copy.deepcopy(UNITS), _dispositions(), tmp=tmp_path)
    assert claim_flags(world.readme, world.facts) == []
    assert degrade_claims(world.plan, world.units, world.dispositions, [], world.facts)[3] == []
    assert _degrade(world, tmp_path) is None
    assert not (tmp_path / "content_units.coherent.json").exists()


def test_a_degrade_that_adds_a_failing_check_is_not_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = _World(_scene_facts(), _units_with("hub:", SCENE), _dispositions(), tmp=tmp_path)
    real = cascade_module._judge_restore

    def worse(*args: Any, **kwargs: Any) -> Any:
        readme, tasks, accounted, dispositions, validation, verdict = real(*args, **kwargs)
        validation = copy.deepcopy(validation)
        validation["checks"].append({"id": "BC-99", "verdict": "FAIL", "details": ["new"], "failures": []})
        return readme, tasks, accounted, dispositions, validation, verdict

    monkeypatch.setattr(cascade_module, "_judge_restore", worse)
    assert _degrade(world, tmp_path) is None
    assert not (tmp_path / "README.coherent.md").exists()


def test_verdict_flags_read_only_model_findings_that_call_a_statement_false() -> None:
    from repo_presenter.readme.review.findings import Finding

    quote = "The library can export `.fbx` files and read every format."
    llm = Finding(rule="factuality", source="llm", claim_kind="contradiction", message="m", quote=quote,
                  finding_id="F1", section_id="opening", causal_stage="S6", criterion="c")
    quality = Finding(rule="specificity", source="llm", claim_kind="quality", message="m", quote=quote,
                      finding_id="F2", section_id="opening", causal_stage="S6", criterion="c")
    det = Finding(rule="claim_contradiction", source="deterministic", claim_kind="contradiction",
                  message="m", evidence="e", quote=quote)
    assert [f.quote for f in verdict_flags([llm, quality, det])] == [quote]


# --- BL-210 wired into the hosted cascade: the register correction before the seal --------------

CHART = "Chart chart = doc.FirstSection.Body.Shapes[0].Chart;"


def _register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *quotes: str) -> None:
    register = tmp_path / "findings.json"
    rows = [
        {
            "repository": ENTRY.repository, "description": "confirmed", "evidence": "x:1@abc",
            "route": "lane_r", "status": "OPEN", "first_seen_at": "2026-11-13", "quote": quote,
            "truth": "the source says otherwise",
        }
        for quote in quotes
    ]
    register.write_text(json.dumps({"schema_version": 1, "findings": rows}), encoding="utf-8")
    monkeypatch.setattr(must_correct, "DEFAULT_FINDINGS_PATH", register)


def _example(identifier: str, code: str) -> Fact:
    return Fact(identifier, "example", code, (Evidence("README.md", "example"),), "SUPPORTED")


def test_the_register_correction_of_a_planned_example_runs_in_the_cascade_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Words .NET (run 44349039315): ``Chart chart = doc.FirstSection.Body.Shapes[0].Chart;`` is a
    confirmed false line of the Quick Start example; hosted generation printed it, as only
    re-certification applied BL-210's correction."""
    _register(tmp_path, monkeypatch, CHART)
    facts = _facts_with(
        _example("example:001", f"var doc = new Document();\n{CHART}\n"),
        _example("example:002", 'var doc = new Document();\ndoc.Save("a.docx");\n'),
    )
    plan = _plan()
    for section in plan["sections"]:
        if section["section_id"] in ("quick_start", "additional_examples"):
            section["include"] = True
    plan.update(quick_start_example_id="example:001", second_quick_start_example_id=None,
                additional_example_ids=["example:002"])
    units = copy.deepcopy(UNITS)
    units["units"] += [
        {"section": "quick_start", "slot": "lead_in", "text": "Creates a document and reads its chart.",
         "fact_ids": ["example:001"]},
        {"section": "additional_examples", "slot": "workflow:example:002",
         "text": "Saves a document to DOCX.", "fact_ids": ["example:002"]},
    ]
    world = _World(facts, units, _dispositions(), plan=plan, tmp=tmp_path)
    assert CHART in world.readme and "BC-18" in _ids(world.judge()[0])
    degraded = _degrade(world, tmp_path)
    assert degraded is not None and "BC-18" not in _ids(degraded.validation)
    assert CHART not in degraded.composed.readme
    assert degraded.composed.plan["quick_start_example_id"] == "example:002"
    [record] = degraded.composed.coherent_units["register_corrections"]
    assert record["rule"] == "BL-210" and record["action"] == "example_replaced"


# --- Words .NET: a register quote that spans two API table rows -----------------------------------

SPANNING = "| `DigitalSignatureUtil` | Provides methods for signing document. |\n| `SignOptions` |"


def _documented(name: str, docstring: str) -> Fact:
    value = f"aspose.words.{name}"
    return Fact(
        f"public_symbol:{value.lower()}", "public_symbol", value,
        (Evidence("x.cs", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "signature": f"class {name}", "docstring": docstring},
    )


def test_a_quote_spanning_two_api_rows_replaces_the_row_it_prints_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Words .NET (run 44349039315): BC-18 on ``| `DigitalSignatureUtil` | Provides methods for
    signing document. |`` plus the start of the next row, which the repair called a "facts defect"."""
    _register(tmp_path, monkeypatch, SPANNING)
    facts = _facts_with(
        _documented("DigitalSignatureUtil", "Provides methods for signing document."),
        _documented("SignOptions", "Options for signing."),
        drop=("public_symbol:aspose.threed.scene",),
    )
    plan = _plan(hubs=False)
    world = _World(facts, copy.deepcopy(UNITS), _dispositions(), plan=plan, tmp=tmp_path)
    assert "Provides methods for signing document." not in world.readme
    assert "BC-18" not in _ids(world.judge()[0])
    assert "| `SignOptions` | Options for signing. |" in world.readme  # the row it only begins stays
    assert "| `DigitalSignatureUtil` |" in world.readme  # the type stays, described by the facts


def test_a_one_row_quote_and_an_unrelated_table_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _register(tmp_path, monkeypatch, "| `Other` | Not printed anywhere. |\n| `More` |")
    facts = _facts_with(_documented("DigitalSignatureUtil", "Provides methods for signing document."))
    world = _World(facts, copy.deepcopy(UNITS), _dispositions(), plan=_plan(hubs=False), tmp=tmp_path)
    assert "| `DigitalSignatureUtil` | Provides methods for signing document. |" in world.readme


def test_text_two_units_both_print_is_ambiguous_and_left_alone() -> None:
    twice = "It also ships a GPU backend for rendering."
    units = {"units": [
        {"slot": "capability:1", "section": "key_capabilities", "text": twice, "fact_ids": []},
        {"slot": "capability:2", "section": "key_capabilities", "text": twice, "fact_ids": []},
    ], "omitted": []}
    plan = {"core_capabilities": [{"title": "A"}, {"title": "B"}]}
    new_plan, new_units, _d, records = degrade_claims(
        plan, units, {"dispositions": []}, [ClaimFlag(twice, "d", "BC-14")], _facts()
    )
    assert records == [] and new_units["units"] == units["units"] and new_plan == plan
