"""BL-400: a model flag on a line the renderer prints from SUPPORTED facts is cleared, with a recorded proof.

Hosted targeted re-runs of 2026-11-20 (main 82b8ccb): Aspose.Page FOSS for Python was rejected by the
production review on one ``unsupported_claim`` -- its opening, the sentence the format facts state
("reads EPS, JXR, ... and writes BMP, JPEG, PNG and TIFF files."), which the degrade itself had written and
which no registered clearance can disprove. The M9 audit clears exactly such a line (it re-derives the
README with every authored unit replaced by a sentinel); the seal gate had no equivalent. The clearance here
uses the same predicate (``review.derivation``, one implementation). Every finding text below is the exact
one of a hosted failure record.

Negative controls: an authored sentence is never cleared, a line stating a fact that is not SUPPORTED is
never cleared, a line a register row refutes is never cleared, a fragment of a line is never located, and the
Slides C++ opening (formats the upstream library declares but does not write) is NOT a clearable line: its
format facts were wrong at the source (the extractor now stops reading a declaring header's to-string switch
and the tests as registration), so the line changes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.extractors.platforms.cpp_format_declarations import (
    format_declarations,
)
from repo_presenter.readme.composition.authoring_retry import _fact_true_opening_unit
from repo_presenter.readme.composition.components.identity import (
    product_name_of_repository,
)
from repo_presenter.readme.review.clearances import (
    PROVENANCE_CLEARANCES,
    ClearanceContext,
    apply_clearances,
)
from repo_presenter.readme.review.derivation import (
    derivation,
    lane_r_derivation,
    rederive_lane_r,
)
from repo_presenter.readme.review.findings import (
    PROVENANCE_CLEARANCES_FOR_KIND,
    Finding,
)
from repo_presenter.readme.review.reply import review_from_reply
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _plan
from tests.readme.review.review_support import raw_finding, raw_reply
from tests.readme.validation.test_degrade_claims_bl240 import _fact, _facts_with, _World

#: Aspose.Page FOSS for Python's SUPPORTED format facts (hosted facts of 2026-11-20), as the opening states them.
PAGE_INPUTS = ("eps", "jxr", "png", "ps", "tif", "tiff", "wdp", "xps")
PAGE_OUTPUTS = ("bmp", "jpeg", "png", "tiff")
PAGE_OPENING = (
    "Aspose.3D FOSS for Python reads EPS, JXR, PNG, PS, TIF, TIFF, WDP and XPS files and writes BMP, JPEG, PNG "
    "and TIFF files."
)
ENTERPRISE_URL = "https://products.aspose.com/omr/"
OMR_LINE = (
    f"See [Aspose.3D for Python — Enterprise Edition]({ENTERPRISE_URL}). It adds advanced recognition "
    "algorithms, batch processing, and export to multiple formats including PDF, DOCX, and Excel."
)


def _format_facts(*, unresolved: tuple[str, ...] = ()) -> tuple[Fact, ...]:
    rows = [(f"format:input.{ext}", f".{ext}") for ext in PAGE_INPUTS]
    rows += [(f"format:output.{ext}", f".{ext}") for ext in PAGE_OUTPUTS]
    return tuple(
        _fact(identifier, "format", value, "UNRESOLVED" if identifier in unresolved else "SUPPORTED")
        for identifier, value in rows
    )


def _page_facts(*, unresolved: tuple[str, ...] = ()) -> FactsDocument:
    return _facts_with(*_format_facts(unresolved=unresolved), drop=("format:output.glb", "format:input.obj"))


def _world(tmp_path: Path, facts: FactsDocument, opening: str | None = None) -> _World:
    """A candidate whose opening unit is ``opening`` (default: the format facts' own sentence, as BL-220/BL-350 write it)."""
    units = copy.deepcopy(UNITS)
    unit = next(u for u in units["units"] if u["slot"] == "opening")
    sentence = _fact_true_opening_unit(
        dict(unit), facts=facts, name=product_name_of_repository(facts.repository)
    )
    assert sentence is not None
    unit.update(text=opening if opening is not None else sentence["text"], fact_ids=sentence["fact_ids"])
    return _World(facts, units, _dispositions(), plan=_plan(), tmp=tmp_path)


def _register(tmp_path: Path, *rows: dict[str, Any]) -> Path:
    path = tmp_path / "readme_findings.json"
    path.write_text(json.dumps({"findings": list(rows)}), encoding="utf-8")
    return path


def _context(world: _World, tmp_path: Path, *, register: Path | None = None) -> ClearanceContext:
    path = register or _register(tmp_path)

    def derive(lines: Any) -> Any:
        return lane_r_derivation(
            world.readme, entry=ENTRY, facts=world.facts, plan=world.plan, units=world.units,
            dispositions=world.dispositions, ask=lines, register_path=path,
        )

    return ClearanceContext(world.readme, "", world.facts, derive)


def _flag(quote: str, kind: str = "unsupported_claim", section: str = "opening") -> Finding:
    return Finding(
        rule="llm:factuality", source="llm", claim_kind=kind, message=quote[:80], quote=quote,
        finding_id="F01", section_id=section, causal_stage="S6", criterion="factuality",
        evidence="audit: no registered clearance proves an unsupported claim false",
    )


# --- the exact Page Python failure --------------------------------------------------------------


@pytest.mark.parametrize("kind", ["unsupported_claim", "contradiction"])
def test_the_opening_the_format_facts_state_is_cleared_with_a_recorded_proof(tmp_path: Path, kind: str) -> None:
    world = _world(tmp_path, _page_facts())
    assert PAGE_OPENING in world.readme.splitlines()
    cleared = apply_clearances(_flag(PAGE_OPENING, kind), _context(world, tmp_path))
    assert cleared.status == "CLEARED" and cleared.clearance is not None
    assert cleared.clearance.name == "derived_from_supported_facts"
    [proof] = cleared.clearance.evidence
    assert "printed from SUPPORTED facts by a deterministic stage" in proof
    assert "format:input.eps" in proof and "format:output.tiff" in proof  # the facts it states, cited
    # the proof survives a round trip through the stored verdict and cannot be moved to another finding
    assert Finding.from_record(cleared.to_record()) == cleared
    other = _flag(PAGE_OPENING + " More.", kind)
    with pytest.raises(ValueError, match="does not prove this finding"):
        Finding(**{**other.__dict__, "status": "CLEARED", "clearance": cleared.clearance})


def test_the_whole_review_is_accepted_when_its_only_finding_is_that_opening(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    reply = raw_reply("REJECT_FACTUAL", [raw_finding(
        "unsupported_claim", section_id="opening", quote=PAGE_OPENING, fact_ids=[], criterion="factuality",
    )])
    verdict = review_from_reply(
        reply, candidate_readme=world.readme, original_readme="", facts=world.facts, plan=None,
        deterministic_findings=(), prompt_version="21", model_served="m", request_sha256="a" * 64,
        reply_sha256="b" * 64, derive=_context(world, tmp_path).derive,
    )
    assert verdict.verdict == "ACCEPT"
    [finding] = verdict.findings
    assert finding.status == "CLEARED" and finding.clearance.name == "derived_from_supported_facts"
    # without the caller's re-derivation (the default) nothing is cleared: the flag blocks as before
    blocked = review_from_reply(
        reply, candidate_readme=world.readme, original_readme="", facts=world.facts, plan=None,
        deterministic_findings=(), prompt_version="21", model_served="m", request_sha256="a" * 64,
        reply_sha256="b" * 64,
    )
    assert blocked.verdict == "REJECT" and blocked.blocking_findings[0].status == "BLOCKING"


def test_the_audit_and_the_review_use_one_predicate(tmp_path: Path) -> None:
    """The M9 auditor's re-derivation labels the opening a renderer line citing the format facts, and the
    shared ``derivation`` clears it: the seal-time and audit-time judgments are no longer asymmetric."""
    world = _world(tmp_path, _page_facts())
    rederived = rederive_lane_r(ENTRY, world.facts, world.plan, world.units, world.dispositions)
    number = world.readme.splitlines().index(PAGE_OPENING) + 1
    assert rederived.origins[number - 1]["source"] == "renderer"
    assert "format:output.bmp" in rederived.origins[number - 1]["fact_ids"]
    derived = derivation("R", world.readme, world.facts, rederived, repository=world.facts.repository, ask={number})
    assert number in derived.clearable
    import importlib.util
    import sys

    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "src"))
    spec = importlib.util.spec_from_file_location("run_m9_auditor_bl400", root / "scripts" / "run_m9_auditor.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert script.derivation is derivation and script.keep_reason.__module__ == derivation.__module__


# --- negative controls ----------------------------------------------------------------------------


def test_an_authored_opening_is_never_cleared_even_when_it_resembles_the_fact_sentence(tmp_path: Path) -> None:
    authored = PAGE_OPENING[:-1] + ", and converts them to PDF."
    world = _world(tmp_path, _page_facts(), opening=authored)
    assert authored in world.readme.splitlines()
    assert apply_clearances(_flag(authored), _context(world, tmp_path)).status == "BLOCKING"


def test_an_authored_opening_that_is_a_different_sentence_is_never_cleared(tmp_path: Path) -> None:
    authored = "Aspose.3D FOSS for Python builds scenes with Scene."
    world = _world(tmp_path, _page_facts(), opening=authored)
    assert apply_clearances(_flag(authored), _context(world, tmp_path)).status == "BLOCKING"


def test_a_format_fact_that_is_not_supported_is_never_in_a_cleared_line(tmp_path: Path) -> None:
    # Font Python's shape: ``.woff2`` is UNRESOLVED, so the facts' sentence omits it; an opening that states it
    # is authored text and stays blocking.
    facts = _page_facts(unresolved=("format:output.bmp",))
    world = _world(tmp_path, facts, opening=PAGE_OPENING)  # still lists BMP
    assert apply_clearances(_flag(PAGE_OPENING), _context(world, tmp_path)).status == "BLOCKING"


def test_a_cited_fact_that_turns_out_not_supported_blocks_the_clearance(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    flipped = FactsDocument(
        world.facts.repository, world.facts.source_revision,
        tuple(
            Fact(f.id, f.kind, f.value, f.evidence, polarity="CONTRADICTED", attributes=f.attributes)
            if f.id == "format:output.bmp" else f
            for f in world.facts.facts
        ),
    )
    context = _context(world, tmp_path)
    context = ClearanceContext(
        world.readme, "", flipped,
        lambda lines: lane_r_derivation(
            world.readme, entry=ENTRY, facts=flipped, plan=world.plan, units=world.units,
            dispositions=world.dispositions, ask=lines, register_path=_register(tmp_path),
        ),
    )
    assert apply_clearances(_flag(PAGE_OPENING), context).status == "BLOCKING"


def test_a_line_an_open_register_row_refutes_is_never_cleared(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    row = {"repository": world.facts.repository, "status": "OPEN", "quote": PAGE_OPENING}
    register = _register(tmp_path, row)
    assert apply_clearances(_flag(PAGE_OPENING), _context(world, tmp_path, register=register)).status == "BLOCKING"


def test_a_missing_register_clears_nothing(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    context = _context(world, tmp_path, register=tmp_path / "no-such-register.json")
    assert apply_clearances(_flag(PAGE_OPENING), context).status == "BLOCKING"


def test_a_fragment_of_a_line_and_a_line_that_is_not_in_the_candidate_are_never_located(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    context = _context(world, tmp_path)
    for quote in (PAGE_OPENING[:60], PAGE_OPENING + " It also converts to PDF.", "Not a line of this README."):
        assert apply_clearances(_flag(quote), context).status == "BLOCKING"


def test_a_quote_spanning_a_derived_and_an_authored_line_is_never_cleared(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    rows = world.readme.splitlines()
    authored = next(r for r in rows if r.endswith("Sentence 1 about the API."))
    assert apply_clearances(_flag(f"{PAGE_OPENING}\n{authored}"), _context(world, tmp_path)).status == "BLOCKING"


def test_no_provenance_without_the_caller_and_never_for_other_kinds(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    bare = ClearanceContext(world.readme, "", world.facts)
    assert apply_clearances(_flag(PAGE_OPENING), bare).status == "BLOCKING"
    assert set(PROVENANCE_CLEARANCES) == {"derived_from_supported_facts"}
    assert set(PROVENANCE_CLEARANCES_FOR_KIND) == {"unsupported_claim", "contradiction"}
    for kind in ("quality", "absence", "omission", "name_denial"):
        assert apply_clearances(_flag(PAGE_OPENING, kind), _context(world, tmp_path)).status == "BLOCKING"


def test_a_deterministic_finding_is_never_cleared(tmp_path: Path) -> None:
    world = _world(tmp_path, _page_facts())
    finding = Finding(rule="claim_contradiction", source="deterministic", message=PAGE_OPENING, quote=PAGE_OPENING)
    assert apply_clearances(finding, _context(world, tmp_path)) is finding


# --- OMR / PSD Python: the flagged line is an authored clause, so it is not the clearance's ------------


def test_the_omr_enterprise_clause_is_authored_and_is_never_cleared(tmp_path: Path) -> None:
    """The exact OMR Python failure: the quote joins the renderer's own Enterprise sentence to the authored
    ``It adds ...`` clause on one line. The line is not printed from facts alone (the sentinel render differs),
    so no clearance applies: the clause itself has to change (the degrade's enterprise lever)."""
    units = copy.deepcopy(UNITS)
    units["units"].append({
        "section": "enterprise_relationship", "slot": "context", "fact_ids": ["identity:repository"],
        "text": "which adds advanced recognition algorithms, batch processing, and export to multiple formats "
                "including PDF, DOCX, and Excel.",
    })
    plan = _plan()
    for row in plan["sections"]:
        if row["section_id"] == "enterprise_relationship":
            row["include"] = True
    facts = _facts_with(_fact("link_target:product.enterprise", "link_target", ENTERPRISE_URL, level="platform"))
    world = _World(facts, units, _dispositions(), plan=plan, tmp=tmp_path)
    assert OMR_LINE in world.readme.splitlines()
    finding = _flag(OMR_LINE, section="scope_limitations")
    assert apply_clearances(finding, _context(world, tmp_path)).status == "BLOCKING"


# --- Slides C++: the facts were wrong, so the line must change ------------------------------------------

_SAVE_FORMAT_HEADER = """
#pragma once
namespace Aspose { namespace Slides { namespace Foss {
enum class SaveFormat { PPT, PDF, PPTX, PPTM, SWF, MD };
inline const char* to_string_view(SaveFormat f) {
    switch (f) {
        case SaveFormat::PPT:  return "Ppt";
        case SaveFormat::PDF:  return "Pdf";
        case SaveFormat::PPTX: return "Pptx";
        case SaveFormat::PPTM: return "Pptm";
        case SaveFormat::SWF:  return "Swf";
        case SaveFormat::MD:   return "Md";
    }
}
}}}
"""
_CONFORMANCE_TEST = """
TEST(SaveFormatConformance, NotImplementedThrows) {
    for (auto f : {SaveFormat::PPT, SaveFormat::PDF, SaveFormat::SWF, SaveFormat::MD}) { EXPECT_THROW(save(p, f)); }
}
"""
_EXAMPLE = "int main() { pres.save(out, Aspose::Slides::Foss::SaveFormat::PPTX); }"


def test_a_declaring_headers_own_switch_and_the_tests_are_not_registration(tmp_path: Path) -> None:
    """Aspose.Slides FOSS for C++ (469ce77): 21 ``SaveFormat`` members, six written, 15 refused with an
    exception (``tests/conformance/save_format_conformance_test.cpp`` pins it). The reader counted the header's
    own ``to_string_view`` switch and the conformance test as registrations, so 22 formats were SUPPORTED output
    and the model's flag on the opening was right. Only product code outside the declaring file registers."""
    (tmp_path / "include").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / "include" / "save_format.h").write_text(_SAVE_FORMAT_HEADER, encoding="utf-8")
    (tmp_path / "tests" / "save_format_conformance_test.cpp").write_text(_CONFORMANCE_TEST, encoding="utf-8")
    (tmp_path / "examples" / "main.cpp").write_text(_EXAMPLE, encoding="utf-8")
    paths = ["include/save_format.h", "tests/save_format_conformance_test.cpp", "examples/main.cpp"]
    decls = format_declarations(tmp_path, paths)
    assert {d.extension for d in decls if d.kind == "declaration"} == {".ppt", ".pdf", ".pptx", ".pptm", ".swf", ".md"}
    assert {(d.extension, d.direction) for d in decls if d.kind == "registration"} == {(".pptx", "output")}
