"""A "N public types ... listed below" count over fewer rows is made true by stating both (BL-065).

The README text is verbatim: ``tests/fixtures/listed_count/*_api_reference.md`` are the "API
Reference" sections of the live READMEs sealed for Lane L (``README.original.md`` of
aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp seal 51d077c2ad1b and aspose-html-foss/
Aspose.HTML-FOSS-for-Python seal c1526e9d7b92). The facts are built from those tables with the
seals' own numbers: every row's type is public except the rows those seals' ``absent_type_row``
edits removed (8 and 5), and the totals are the sealed facts' (195 and 303 public types). Both
seals failed re-certification on rule (h) after BL-065 (197 stated / 189 listed; 303 / 238).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from repo_presenter.lane_l_review import holdout_findings, net_improvement
from repo_presenter.readme.correction.detectors.listed_type_count import listed_type_count
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.surface_claims import states_listed_count

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "listed_count"
CPP = (FIXTURES / "cells_cpp_api_reference.md").read_text(encoding="utf-8")
HTML = (FIXTURES / "html_python_api_reference.md").read_text(encoding="utf-8")
CPP_ABSENT = {
    "AutoFilterCustomFilterCollection_Iterator",
    "AutoFilterSortConditionCollection_Iterator",
    "BitReader",
    "FilterColumnCollection_Iterator",
    "XmlParser",
    "HuffmanTable",
    "ParsedNumericFormat",
    "Workbook_Impl",
}
HTML_ABSENT = {
    "CSSDeclarationBlock",
    "BrowsingContext",
    "WindowEventLoop",
    "ModuleLoadPolicy",
    "BreakHints",
}
_ROW = re.compile(r"^\|\s*`([^`|]+)`\s*\|", re.MULTILINE)
TAIL = "\n## Documentation & Resources\n\nSee the reference.\n"


def _facts(make_facts: Any, make_fact: Any, section: str, absent: set[str], total: int) -> Any:
    names = list(dict.fromkeys(n for n in _ROW.findall(section) if n not in absent))
    names += [f"Unlisted{i}" for i in range(total - len(names))]
    assert len(names) == total
    return make_facts(
        *(
            make_fact(
                f"public_symbol:pkg.{name.lower()}",
                f"pkg.{name}",
                evidence=((f"src/{name}.h", f"line 1; class; {name}"),),
                attributes={"symbol_kind": "class"},
            )
            for name in names
        )
    )


def _cpp(make_context: Any, make_facts: Any, make_fact: Any, *extra: Any) -> Any:
    facts = _facts(make_facts, make_fact, CPP, CPP_ABSENT, 195)
    return make_context("# Aspose.Cells FOSS for C++\n\n" + CPP + TAIL, [*facts, *extra])


def _html(make_context: Any, make_facts: Any, make_fact: Any) -> Any:
    facts = _facts(make_facts, make_fact, HTML, HTML_ABSENT, 303)
    return make_context("# Aspose.HTML FOSS for Python\n\n" + HTML + TAIL, facts)


def _listed_findings(readme: str, facts: Any) -> list[str]:
    return [f.detail for f in claim_findings(readme, facts) if "rows that follow" in f.detail]


def test_cells_cpp_total_becomes_the_facts_count_and_the_sentence_states_the_rows(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = _cpp(make_context, make_facts, make_fact)
    edits = listed_type_count(ctx).edits
    assert [(e.original, e.replacement) for e in edits] == [
        ("197", "195"),
        ("is listed below", "has 189 of them listed below"),
    ]
    assert all(e.kind == "FALSE_CLAIM_FIX" and e.fact_ids for e in edits)
    result = correct(ctx)
    assert "full public surface — 195 public types — has 189 of them listed below" in (
        result.corrected
    )
    # R14: every live row the facts support is still there; only the 8 absent rows went.
    assert len(_ROW.findall(result.corrected)) == 189
    assert _listed_findings(result.corrected, ctx.facts) == []
    # Without this detector's edits (the sealed candidate), rule (h) fails the sentence.
    removed_only = ctx.readme
    for edit in sorted(
        (e for e in result.edits if e.detector == "absent_type_row"), key=lambda e: -e.start
    ):
        removed_only = removed_only[: edit.start] + removed_only[edit.end :]
    assert _listed_findings(removed_only, ctx.facts)


def test_html_python_total_stays_the_facts_303_and_the_sentence_says_238_are_listed(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = _html(make_context, make_facts, make_fact)
    edits = listed_type_count(ctx).edits
    assert [(e.original, e.replacement) for e in edits] == [
        ("listed below", "238 of them listed below")
    ]
    result = correct(ctx)
    assert "exposes 303 public types in total, 238 of them listed below by module" in (
        result.corrected
    )
    assert len(_ROW.findall(result.corrected)) == 238
    assert _listed_findings(result.corrected, ctx.facts) == []
    deterministic, idempotent = is_stable(ctx, result)
    assert deterministic and idempotent
    assert net_improvement(ctx, result)
    assert holdout_findings(ctx, result, deterministic=True) == []


def test_cells_cpp_failing_example_is_an_r21_residual_once_the_run_is_a_net_improvement(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    failing = make_fact(
        "example:002",
        '#include "aspose/cells_foss/Workbook.h"',
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "lines 174-187; unit"),
            ("receipts.json", "example 2: FAILED; error: no match for 'operator[]'"),
        ),
    )
    ctx = _cpp(make_context, make_facts, make_fact, failing)
    result = correct(ctx)
    deterministic, idempotent = is_stable(ctx, result)
    assert deterministic and idempotent
    assert net_improvement(ctx, result)  # no contradiction introduced: L-03 and L-05 pass
    findings = holdout_findings(ctx, result, deterministic=deterministic)
    assert findings == []
    assert [r["kind"] for r in findings.residuals] == ["unrepaired_defect"]
    assert findings.residuals[0]["detail"].startswith("failing_example")


def test_a_count_that_matches_its_rows_or_says_so_already_is_left_alone(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = _facts(make_facts, make_fact, "| `A` | a |\n| `B` | b |\n| `C` | c |\n", set(), 3)
    table = "| Type | Description |\n|---|---|\n| `A` | a |\n| `B` | b |\n| `C` | c |\n"
    for sentence in (
        "The library exposes 3 public types in total, listed below.",
        "The library exposes 3 public types in total, 2 of them listed below.",
    ):
        readme = f"## API Reference\n\n{sentence}\n\n" + table
        if "2 of them" in sentence:
            readme = readme.replace("| `C` | c |\n", "")
        ctx = make_context(readme, facts)
        assert listed_type_count(ctx).edits == ()


def test_are_listed_fails_closed_and_the_validator_finding_stays(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = _facts(make_facts, make_fact, "| `A` | a |\n| `B` | b |\n", set(), 3)
    readme = (
        "## API Reference\n\nThe 3 public types are listed below.\n\n"
        "| Type | Description |\n|---|---|\n| `A` | a |\n| `B` | b |\n"
    )
    ctx = make_context(readme, facts)
    assert listed_type_count(ctx).edits == ()
    assert _listed_findings(readme, ctx.facts)


def test_a_total_above_the_facts_is_kept_when_it_was_not_the_tables_own_count(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    # 5 stated over 2 rows, facts 3: the maintainers' total may count unrecorded kinds; only the
    # listed number is stated.
    facts = _facts(make_facts, make_fact, "| `A` | a |\n| `B` | b |\n", set(), 3)
    readme = (
        "## API Reference\n\nThe library exposes 5 public types in total, listed below.\n\n"
        "| Type | Description |\n|---|---|\n| `A` | a |\n| `B` | b |\n"
    )
    ctx = make_context(readme, facts)
    assert [(e.original, e.replacement) for e in listed_type_count(ctx).edits] == [
        ("listed below", "2 of them listed below")
    ]


def test_the_validator_accepts_only_the_stated_listed_number() -> None:
    assert states_listed_count("303 public types in total, 238 of them listed below", 238)
    assert states_listed_count("1,203 public types, of which 1,100 are listed below", 1100)
    assert not states_listed_count("303 public types in total, 237 of them listed below", 238)
    assert not states_listed_count("303 public types in total, listed below", 238)
