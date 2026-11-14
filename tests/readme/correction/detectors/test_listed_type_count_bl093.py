"""BL-093: rule (h) and ``listed_type_count`` v2 read every listing verb, not only "listed".

``tests/fixtures/listed_count/pdf_python_api_reference.md`` is verbatim the API reference section of
aspose-pdf-foss/Aspose-PDF-FOSS-for-Python's live README at 02b0c0e4 (``README.original.md`` of Lane L
seal 3d91633f, M9 control 8aecb5): "277 public types are organized by module below" over 288 type
rows. The facts are the seal's numbers: 385 public types; the four rows the seal's
``absent_type_row`` edits removed name no public type, so 284 rows are left. The sealed candidate
said "385 public types are organized by module below" over those 284 rows.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from repo_presenter.readme.correction.detectors.listed_type_count import listed_type_count
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.surface_claims import _LISTED_HERE

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "listed_count"
PDF = (FIXTURES / "pdf_python_api_reference.md").read_text(encoding="utf-8")
PDF_ABSENT = {"Codestream", "Jpeg2000Error", "MQDecoder", "TagTree"}
_ROW = re.compile(r"^\|\s*`([^`|]+)`\s*\|", re.MULTILINE)
TAIL = "\n## Documentation & Resources\n\nSee the reference.\n"


def _context(make_context: Any, make_facts: Any, make_fact: Any, section: str = PDF, total: int = 385) -> Any:
    names = list(dict.fromkeys(n for n in _ROW.findall(section) if n not in PDF_ABSENT))
    names += [f"Unlisted{i}" for i in range(total - len(names))]
    facts = make_facts(*(
        make_fact(f"public_symbol:pkg.{name.lower()}", f"pkg.{name}",
                  evidence=((f"src/pkg/{name}.py", f"line 1; class; {name}"),), attributes={"symbol_kind": "class"})
        for name in names
    ))
    return make_context("# Aspose.PDF FOSS for Python\n\n" + section + TAIL, facts)


def _listed_findings(readme: str, facts: Any) -> list[str]:
    return [f.detail for f in claim_findings(readme, facts) if "rows that follow" in f.detail]


def test_pdf_python_total_is_the_facts_385_and_the_sentence_says_284_are_organized_below(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = _context(make_context, make_facts, make_fact)
    assert [(e.original, e.replacement) for e in listed_type_count(ctx).edits] == [
        ("are organized", "— 284 of them organized")
    ]
    result = correct(ctx)
    assert "385 public types — 284 of them organized by module below." in result.corrected
    assert len(_ROW.findall(result.corrected)) == 284  # R14: only the four absent rows went
    assert _listed_findings(result.corrected, ctx.facts) == []
    deterministic, idempotent = is_stable(ctx, result)
    assert deterministic and idempotent


def test_rule_h_now_fails_the_sealed_sentence_lane_r_reads_the_same_rule(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = _context(make_context, make_facts, make_fact)
    sealed = ctx.readme.replace("277 public types are organized", "385 public types are organized")
    for name in PDF_ABSENT:
        sealed = re.sub(rf"(?m)^\|\s*`{name}`\s*\|.*\n", "", sealed)
    assert len(_ROW.findall(sealed)) == 284
    assert _listed_findings(sealed, ctx.facts)  # BC-14 rule (h): 385 stated, 284 listed


def test_negative_controls(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    # every live row is a public type and the total is the rows: nothing to state, no finding
    names = list(dict.fromkeys(_ROW.findall(PDF)))
    ctx = _context(make_context, make_facts, make_fact, total=len(names) - len(PDF_ABSENT))
    whole = ctx.readme.replace("277 public types are organized", f"{len(names)} public types are organized")
    assert _listed_findings(whole, ctx.facts) == []
    # a listing verb pointing at a document elsewhere is not a claim about the rows that follow
    for text in ("documented in the API reference linked below", "shown on the reference page below",
                 "the full documentation is linked below",
                 "summarized in the module-grouped table below"):  # a summary need not hold every type (O6)
        assert _LISTED_HERE.search(text) is None, text
    # "listed" still reads as before; the new verbs read the same way
    for text in ("is listed below", "are grouped by namespace below",
                 "shown in the tables below", "shown below"):
        assert _LISTED_HERE.search(text).group(0) == text
