"""BL-077: a repair is accepted only when its revision no longer prints the false claim.

Built from the four hosted Lane R runs that failed after repair (43489976823 3D .NET, 43489981024
3D Python, 43489984973 Cells .NET, 43489988826 Cells C++). Each recorded a repair as "repaired"
whose revision still printed the claim its rule refuses, or a sibling one, and the final check
rejected the candidate:

* Cells .NET: BC-14 "repaired" as "... demonstrating usage of Aspose.Cells FOSS for .NET version
  26.10.0.0" -- the samples-use-the-package claim reworded, which rule (j7) did not read.
* Cells C++: BC-02 "repaired" by a VERIFIED_PRESERVE of the code block printing
  ``cmake --build build``, the build no run proved.
* 3D .NET / Python: never-thrown exceptions still said to be thrown, and the Core API rows the
  renderer prints from the types' docstrings ("Exception thrown when rendering driver fails.").

The guard (``loop.reject_still_failing``) re-judges every revision by the BC-02/BC-14/BC-18
functions on its render, the packet names the facts the rule text cites
(``targeted.contradicting_facts``), and the renderer prints a fact-true row for a never-thrown
type (``renderer._not_thrown_marked``). Zero provider calls.
"""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.loop import (
    RepairContext,
    dispositions_composer,
    owned_failures,
    reject_still_failing,
    section_composer,
)
from repo_presenter.readme.repair.targeted import (
    Defect,
    RepairLedger,
    contradicting_facts,
    repair_packet,
)
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.code_path_claims import (
    NOT_THROWN_DESCRIPTION,
    refuted_thrown_description,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.repair.test_accounting import (
    ENTRY,
    UNITS,
    _dispositions,
    _entry,
    _facts,
    _plan,
    _unit,
)

PROMPTS_PATH = Path(__file__).resolve().parents[3] / "prompts"


def _fact(fact_id: str, kind: str, value: str, detail: str = "", **attributes: str) -> Fact:
    return Fact(
        fact_id,
        kind,
        value,
        (Evidence("src/x", detail),),
        polarity="SUPPORTED",
        attributes=attributes or None,
    )


def _never_thrown(member: str) -> Fact:
    """The real ``implementation`` fact shape (extractor output for 3D Python / Cells C++)."""
    short = member.rsplit(".", 1)[-1]
    return _fact(
        f"implementation:never_thrown.{member.lower()}",
        "implementation",
        f"{member} is never thrown or constructed by the library's own code (declared only)",
        "line 9; no product source throws, constructs or uses the type outside its own declaration",
        aspect="never_thrown",
        member=member,
        type=short,
    )


def _exception(member: str, docstring: str) -> Fact:
    return _fact(
        f"public_symbol:{member.lower()}",
        "public_symbol",
        member,
        "line 1; class; public by name",
        symbol_kind="class",
        docstring=docstring,
    )


#: The real 3D Python Core API rows of hosted run 43489981024 (type, docstring), each refused by
#: claim_contradiction against ``implementation:never_thrown.*``.
THREED_PYTHON_ROWS = [
    ("aspose.threed.ExportException", "Exceptions when Aspose.3D failed to export the scene to file."),
    ("aspose.threed.ImportException", "Exception when Aspose.3D failed to open the specified source."),
    ("aspose.threed.ParseException", "Exception when Aspose.3D failed to parse the input."),
    ("aspose.threed.TrialException", "This is raised in Scene.Open/Scene.Save when no licenses are applied."),
    ("aspose.threed.render.DriverException", "Exception thrown when rendering driver fails."),
    ("aspose.threed.render.InitializationException", "Exception thrown when rendering initialization fails."),
    ("aspose.threed.render.ShaderException", "Exception thrown when shader compilation/linking fails."),
]


def _threed_facts(*, never_thrown: bool = True) -> FactsDocument:
    base = _facts()
    extra: list[Fact] = []
    for member, docstring in THREED_PYTHON_ROWS:
        extra.append(_exception(member, docstring))
        if never_thrown:
            extra.append(_never_thrown(member))
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


# --- B: the renderer does not print a docstring the facts refute ------------------------------


@pytest.mark.parametrize(("member", "docstring"), THREED_PYTHON_ROWS)
def test_each_real_never_thrown_docstring_is_refuted(member: str, docstring: str) -> None:
    facts = _threed_facts()
    assert refuted_thrown_description(member, docstring, facts) == (
        f"implementation:never_thrown.{member.lower()}"
    )
    assert refuted_thrown_description(member, NOT_THROWN_DESCRIPTION, facts) is None


def test_a_thrown_type_keeps_its_docstring() -> None:
    facts = _threed_facts(never_thrown=False)
    member, docstring = THREED_PYTHON_ROWS[4]
    assert refuted_thrown_description(member, docstring, facts) is None


def test_the_core_api_rows_print_a_fact_true_description_and_pass_the_rule() -> None:
    facts = _threed_facts()
    readme = render_readme(ENTRY, facts, _plan(), UNITS, _dispositions())
    for member, docstring in THREED_PYTHON_ROWS:
        name = member.rsplit(".", 1)[-1]
        assert f"| `{name}` | {NOT_THROWN_DESCRIPTION} |" in readme
        assert docstring not in readme
    assert not [f for f in claim_findings(readme, facts) if "is thrown, but" in f.detail]


def test_negative_control_without_the_fact_the_docstring_is_printed_and_the_rule_is_silent() -> None:
    facts = _threed_facts(never_thrown=False)
    readme = render_readme(ENTRY, facts, _plan(), UNITS, _dispositions())
    assert "| `DriverException` | Exception thrown when rendering driver fails. |" in readme
    assert NOT_THROWN_DESCRIPTION not in readme


def test_negative_control_the_old_row_is_what_the_rule_refuses() -> None:
    facts = _threed_facts()
    row = "| `DriverException` | Exception thrown when rendering driver fails. |"
    details = [f.detail for f in claim_findings(row, facts)]
    assert any("`DriverException` is thrown" in d for d in details)


# --- A: rule (j7) reads the reworded samples claim --------------------------------------------


def _cells_net_facts() -> FactsDocument:
    """The real Cells .NET package and sample-reference facts (re-extracted at f71fe55)."""
    base = make_facts()
    return FactsDocument(
        base.repository,
        base.source_revision,
        (
            *(f for f in base.facts if f.id != "package:name"),
            _fact("package:name", "package", "Aspose.Cells.FOSS"),
            _fact("package:version", "package", "26.10.0.0"),
            _fact("package:published_version", "package", "26.10.0", registry="nuget"),
            _fact(
                "project_file:samples.product_reference",
                "project_file",
                "all 15 sample projects reference the product project by ProjectReference; "
                "none references the published package",
                aspect="sample_reference",
                package="Aspose.Cells.FOSS",
                package_reference="0",
                project_reference="15",
                samples="15",
            ),
        ),
    )


SAMPLES_LINK = "- **[samples/](samples/README.md)** — "
#: The text before repair, the BC-18 repair's revision, and the BC-14 repair's revision (run
#: 43489984973's ``repairs.json`` as its log printed it).
SAMPLES_BEFORE = (
    "The samples directory contains example projects demonstrating how to use "
    "`Aspose.Cells.FOSS` version 26.10.0 to work with spreadsheet files in .NET applications."
)
SAMPLES_GOOD = (
    "The samples directory contains example projects demonstrating usage of Aspose.Cells FOSS "
    "for .NET via a local project reference."
)
SAMPLES_REWORDED = (
    "The samples directory contains example projects demonstrating usage of Aspose.Cells FOSS "
    "for .NET version 26.10.0.0."
)


def _samples_findings(text: str) -> list[str]:
    return [
        f.detail
        for f in claim_findings(SAMPLES_LINK + text, _cells_net_facts())
        if "samples use the published package" in f.detail
    ]


def test_the_samples_rule_reads_the_reworded_claim() -> None:
    assert _samples_findings(SAMPLES_BEFORE)
    assert _samples_findings(SAMPLES_REWORDED)
    assert not _samples_findings(SAMPLES_GOOD)


def test_the_samples_rule_ignores_another_package_version() -> None:
    assert not _samples_findings("The samples use Newtonsoft.Json version 13.0.1.")


# --- A: the guard re-judges a revision before it is accepted ----------------------------------

THROW_DETAIL = (
    "the README says `ExportException` is thrown, but "
    "implementation:never_thrown.aspose.threed.exportexception states no library code throws or "
    "constructs it (it is only declared): drop the claim or say it is unused"
)


def _context(facts: FactsDocument, units: dict[str, Any], dispositions: dict[str, Any]) -> RepairContext:
    return RepairContext(
        entry=ENTRY,
        facts=facts,
        prompts=None,  # type: ignore[arg-type]
        config=None,  # type: ignore[arg-type]
        ledger=None,  # type: ignore[arg-type]
        store=None,  # type: ignore[arg-type]
        context=None,  # type: ignore[arg-type]
        investigation={},
        dispositions=dispositions,
        plan=_plan(),
        tasks=[],
        name="Aspose.3D FOSS",
        units=units,
    )


def _scope_units(text: str) -> dict[str, Any]:
    units = copy.deepcopy(UNITS)
    for unit in units["units"]:
        if unit["section"] == "scope_limitations":
            unit["text"] = text
    return units


def _review_defect(detail: str) -> Defect:
    """A deterministic claim_contradiction finding as ``defect_bridge`` hands it to the repair."""
    return Defect(
        "fp-claim",
        "review",
        "claim_contradiction:0",
        "scope_limitations",
        "S6",
        {
            "id": "claim_contradiction:0",
            "criterion": "claim_contradiction",
            "quote": "Export failures raise `ExportException`.",
            "message": f"line 80 (COMPOSING): {detail}",
            "evidence": detail,
        },
    )


def _s6_guard(claimed: str) -> Any:
    facts = _threed_facts()
    rc = _context(facts, _scope_units(claimed), _dispositions())
    task = SimpleNamespace(section_id="scope_limitations", slots=("scope",))
    original = {"units": [{"slot": "scope", "text": claimed, "fact_ids": ["identity:repository"]}]}
    return reject_still_failing(
        lambda revised: [], rc, _review_defect(THROW_DETAIL), original, section_composer(rc, task)
    )


def _scope(text: str) -> dict[str, Any]:
    return {"units": [{"slot": "scope", "text": text, "fact_ids": ["identity:repository"]}]}


def test_the_defect_names_its_own_rule_failure() -> None:
    assert owned_failures(_review_defect(THROW_DETAIL)) == {("BC-14", THROW_DETAIL): 1}


def test_a_reworded_revision_that_still_claims_the_throw_is_rejected_with_the_rule_text() -> None:
    guard = _s6_guard("Export failures raise `ExportException`.")
    errors = guard(_scope("When an export fails, the library throws `ExportException`."))
    assert errors == [
        f"revised_output: BC-14 still fails on this revision, which is the defect: {THROW_DETAIL}"
    ]


def test_a_revision_that_drops_the_claim_is_accepted() -> None:
    guard = _s6_guard("Export failures raise `ExportException`.")
    assert guard(_scope("The package writes GLB only.")) == []


def test_a_revision_that_adds_a_sibling_false_claim_is_rejected() -> None:
    guard = _s6_guard("Export failures raise `ExportException`.")
    errors = guard(
        _scope("The package writes GLB only; a bad file raises `ParseException`.")
    )
    assert len(errors) == 1
    assert errors[0].startswith("revised_output: this revision makes BC-14 fail: ")
    assert "`ParseException` is thrown" in errors[0]


def test_the_stage_checks_still_run_first() -> None:
    facts = _threed_facts()
    rc = _context(facts, _scope_units("x"), _dispositions())
    task = SimpleNamespace(section_id="scope_limitations", slots=("scope",))
    guard = reject_still_failing(
        lambda revised: ["stage says no"], rc, _review_defect(THROW_DETAIL), _scope("x"),
        section_composer(rc, task),
    )
    assert guard(_scope("anything")) == ["stage says no"]


# --- A: the S4 shape of Cells C++ (BC-02 "repaired" by VERIFIED_PRESERVE) ----------------------

CMAKE_BLOCK = "```bash\ncmake -S Aspose.Cells.Foss.Cpp -B build\ncmake --build build\n```"


def _cmake_facts() -> FactsDocument:
    base = _facts()
    cmake = Fact(
        "install_command:cmake",
        "install_command",
        "cmake -S Aspose.Cells.Foss.Cpp -B build\ncmake --build build",
        (
            Evidence(
                "CMakeLists.txt",
                "source build for the CMake project the manifest declares; C++ has no package "
                "registry to install from",
            ),
            Evidence("CMakeLists.txt", "package registry: none could not be read"),
        ),
        polarity="UNRESOLVED",
        attributes={"source_checkout_unverified": "no build exited 0: failed"},
    )
    return FactsDocument(
        base.repository,
        base.source_revision,
        (*base.facts, cmake, _unit("020.code_block", CMAKE_BLOCK)),
    )


def _cmake_plan() -> dict[str, Any]:
    plan = _plan()
    for section in plan["sections"]:
        if section["section_id"] == "development_testing":
            section["include"] = True
    return plan


def _cmake_dispositions(disposition: str, fact_ids: list[str]) -> dict[str, Any]:
    rows = _dispositions()
    rows["dispositions"].append(
        _entry("020.code_block", disposition, "development_testing" if disposition != "OMIT_UNSUPPORTED" else None, fact_ids)
    )
    return rows


def test_a_kept_block_printing_the_unproven_build_is_not_a_bc02_repair() -> None:
    facts = _cmake_facts()
    kept = _cmake_dispositions("VERIFIED_PRESERVE", [])
    readme = render_readme(ENTRY, facts, _cmake_plan(), UNITS, kept)
    assert "cmake --build build" in readme
    rc = _context(facts, UNITS, kept)
    rc = RepairContext(**{**rc.__dict__, "plan": _cmake_plan()})
    from repo_presenter.readme.validation.install import install_failures
    from repo_presenter.readme.validation.failures import Candidate

    failures = install_failures(
        Candidate(ENTRY, facts, _cmake_plan(), UNITS, kept, readme, None, facts.source_revision, None, (), [])
    )
    assert failures, "the fixture must reproduce the hosted BC-02 failure"
    detail = failures[0].detail
    defect = Defect(
        "fp-bc02",
        "validation",
        "BC-02",
        None,
        "S4",
        {
            "id": "BC-02",
            "failures": [
                {"detail": detail, "unit_id": "inherited_unit:020.code_block", "causal_stage": "RECONCILING"}
            ],
        },
    )
    original = {"dispositions": [row for row in kept["dispositions"] if row["unit_id"].endswith("020.code_block")]}
    guard = reject_still_failing(lambda revised: [], rc, defect, original, dispositions_composer(rc))
    # The logged reply: VERIFIED_PRESERVE of the same block (moved within development_testing).
    errors = guard(copy.deepcopy(original))
    assert errors == [f"revised_output: BC-02 still fails on this revision, which is the defect: {detail}"]
    omitted = {
        "dispositions": [
            _entry("020.code_block", "OMIT_UNSUPPORTED", None, ["install_command:cmake"])
        ]
    }
    assert guard(omitted) == []


# --- A: the packet carries the fact the rule holds the claim to -------------------------------


def test_the_packet_names_the_contradicting_fact() -> None:
    facts = _threed_facts()
    defect = _review_defect(THROW_DETAIL)
    named = contradicting_facts(defect, facts)
    assert [record["id"] for record in named] == [
        "implementation:never_thrown.aspose.threed.exportexception"
    ]
    assert named[0]["value"].endswith("(declared only)")
    packet = repair_packet(ENTRY, defect, _scope("x"), facts, (), {"type": "object"})
    assert packet["defect"]["contradicting_facts"] == named


def test_a_defect_naming_no_fact_leaves_the_packet_as_it_was() -> None:
    facts = _threed_facts()
    defect = _review_defect("the README says something no fact names")
    packet = repair_packet(ENTRY, defect, _scope("x"), facts, (), {"type": "object"})
    assert "contradicting_facts" not in packet["defect"]


def test_the_samples_fact_and_the_unproven_build_are_named() -> None:
    samples = contradicting_facts(
        Defect("f", "validation", "BC-14", "documentation_resources", "S6", {
            "id": "BC-14",
            "failures": [{"detail": (
                "the README says the samples use the published package, but "
                "project_file:samples.product_reference states all 15 sample projects reference "
                "the product project by ProjectReference; none references the published package: "
                "say they build against the source project"
            )}],
        }),
        _cells_net_facts(),
    )
    assert [r["id"] for r in samples] == ["project_file:samples.product_reference"]
    build = contradicting_facts(
        Defect("f", "validation", "BC-02", None, "S4", {
            "id": "BC-02",
            "failures": [{"detail": (
                "install_command:cmake: the README prints 'cmake --build build', the source build "
                "of a project whose build no run proved (no build exited 0: failed)"
            )}],
        }),
        _cmake_facts(),
    )
    assert [r["id"] for r in build] == ["install_command:cmake"]
    assert build[0]["polarity"] == "UNRESOLVED"


# --- the S9 loop keys its repairs against the composition the next round reproduces ----------


def test_a_partial_restore_does_not_orphan_the_rounds_repairs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Hosted runs 43489976823 / 43489984973: a partial restore was kept, the section repairs were
    keyed against the restore's tasks, the next round recomposed from raw reconciliation, served
    the pre-repair sections from the store, and the final README printed the pre-repair quotes."""
    fresh = {"dispositions": [], "_tag": "fresh"}
    reconciliations: list[int] = []
    overrides: list[Any] = []
    real_compose = cascade_module._compose

    def compose(**kwargs: Any):
        overrides.append(kwargs.get("dispositions_override"))
        return real_compose(**kwargs)

    monkeypatch.setattr(cascade_module, "_compose", compose)
    monkeypatch.setattr(
        cascade_module, "_run_reconciliation", lambda **kw: (reconciliations.append(1), fresh)[1]
    )
    monkeypatch.setattr(cascade_module, "_run_planning", lambda **kw: {"sections": []})
    monkeypatch.setattr(cascade_module, "_run_authoring", lambda **kw: {"units": []})
    monkeypatch.setattr(cascade_module, "_run_coherence", lambda **kw: {"units": []})
    monkeypatch.setattr(cascade_module, "render_readme", lambda *a, **kw: "README\n")
    monkeypatch.setattr(cascade_module, "authoring_tasks", lambda *a, **kw: [])
    monkeypatch.setattr(cascade_module, "validate_candidate", lambda *a, **kw: {})
    monkeypatch.setattr(cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(()))

    def restore(settled: Any, **kwargs: Any):
        restored = cascade_module.replace(
            settled.composed, dispositions={"dispositions": [], "_tag": "restored"},
            planned_dispositions={"dispositions": [], "_tag": "restored"},
        )
        failing = {"checks": [{"id": "BC-14", "verdict": "FAIL", "details": ["x"]}]}
        return cascade_module._Settled(restored, failing, settled.verdict, settled.rounds)

    monkeypatch.setattr(cascade_module, "_restore_lost_content", restore)
    rounds: list[int] = []
    monkeypatch.setattr(
        cascade_module, "_settle_defects",
        lambda **kw: (rounds.append(1), [SimpleNamespace(stage="S6")] if len(rounds) == 1 else [])[1],
    )
    keyed: list[Any] = []
    monkeypatch.setattr(
        cascade_module, "_repair_defects",
        lambda **kw: (keyed.append(kw["composed"].planned_dispositions or kw["composed"].dispositions), True)[1],
    )
    prompts = load_manifests(PROMPTS_PATH)
    entry, document = make_entry(), make_facts()
    out_dir = tmp_path / "cascade"
    cascade_module._settle_s9(
        entry=entry, document=document, investigation={}, ecosystem=entry.ecosystem,
        tree_paths=[], original_bytes=b"# Original\n", original="# Original\n", out_dir=out_dir,
        prompts=prompts, config=None, ledger=Ledger(out_dir / "llm_cache" / "ledger.jsonl"),
        store=CallStore(out_dir / "llm_cache" / "calls"),
        context=JobContext(repository=entry.repository, source_revision=document.source_revision),
        repairs=RepairLedger(out_dir / "repairs.json", composition="c"), max_rounds=3,
    )
    # The repair was keyed against the composition the calls were made from (fresh), not the
    # restore's, and the next round recomposed from exactly those dispositions.
    assert keyed == [fresh]
    assert overrides == [None, fresh]
    assert reconciliations == [1]
