"""A value a deterministic Lane L edit computed from SUPPORTED facts is evidenced by its derivation.

Evidence (hosted Lane L runs under version set 78b73646d86d, 2026-11-09): PDF FOSS for Python had
``stale_type_count`` rewrite a count to 385 and Cells FOSS for Go to 28; the independent review faulted
the edited line ("385 public types ...") as an unsupported claim because the number is a count of type
facts and appears in no fact *value*. The packet now carries each applied edit's derivation, and a
finding whose only unevidenced term is that edit's own replacement is a contract error quoted back
in the one re-ask. Every other term must still be evidenced; nothing is cleared.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.applied_edits import (
    applied_edit_rows,
    applied_edits_for_lines,
    evidenced_edit_errors,
)
from repo_presenter.readme.review.llm_review import review_checks

ORIGINAL = "# Widget\n\nDocs.\n\nWidget wraps 243 public types by module.\n\nSee RELEASE.md.\n"
CANDIDATE = ORIGINAL.replace("243 public", "385 public")
CHANGED = frozenset({5})


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("src/w.py"),), polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/widget",
    "a" * 40,
    (
        _fact("public_symbol:a", "public_symbol", "Alpha"),
        _fact("public_symbol:b", "public_symbol", "Beta"),
        _fact("format:svg", "format", "SVG"),
        _fact("public_symbol:ghost", "public_symbol", "Ghost", "CONTRADICTED"),
    ),
)


def _edit(**overrides: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "detector": "stale_type_count",
        "original": "243",
        "replacement": "385",
        "rationale": "the facts record 385 type-level public symbols",
        "fact_ids": ("public_symbol:a", "public_symbol:b"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _finding(lines: list[int], kind: str = "unsupported_claim") -> dict[str, Any]:
    return {"id": "F01", "claim_kind": kind, "lines": lines}


def _errors(output: dict[str, Any], edits: list[SimpleNamespace], candidate: str = CANDIDATE) -> list[str]:
    return evidenced_edit_errors(
        output,
        rows=applied_edit_rows(edits, FACTS),
        candidate_readme=candidate,
        original_readme=ORIGINAL,
        facts=FACTS,
        changed=CHANGED,
    )


def test_only_derived_edits_citing_supported_facts_are_listed() -> None:
    assert [r["replacement"] for r in applied_edit_rows([_edit()], FACTS)] == ["385"]
    assert applied_edit_rows([_edit(fact_ids=())], FACTS) == []
    assert applied_edit_rows([_edit(fact_ids=("public_symbol:ghost",))], FACTS) == []
    assert applied_edit_rows([_edit(detector="enterprise_edition_naming")], FACTS) == []


def test_the_edit_is_attached_to_the_changed_line_it_wrote() -> None:
    rows = applied_edit_rows([_edit()], FACTS)
    (found,) = applied_edits_for_lines(rows, CANDIDATE, [5])
    assert found["lines"] == [5] and found["fact_ids"] == ["public_symbol:a", "public_symbol:b"]
    assert applied_edits_for_lines(rows, CANDIDATE, [3, 7]) == []
    assert applied_edits_for_lines(rows, "Widget has 3850 public types.\n", [1]) == []


def test_a_finding_that_faults_only_the_edits_own_number_is_a_contract_error() -> None:
    (error,) = _errors({"findings": [_finding([5])]}, [_edit()])
    assert "stale_type_count" in error and "'243' -> '385'" in error and "public_symbol:a" in error


def test_a_number_the_edit_did_not_write_still_blocks() -> None:
    other = CANDIDATE.replace("by module", "in 77 modules")
    assert _errors({"findings": [_finding([5])]}, [_edit()], other) == []
    # the number the edit wrote sits elsewhere than the cited line: nothing to attach
    assert _errors({"findings": [_finding([3])]}, [_edit()]) == []


def test_an_edit_line_quote_with_another_unevidenced_number_still_blocks() -> None:
    mixed = ORIGINAL.replace("243 public types", "385 public types in 91 modules")
    assert _errors({"findings": [_finding([5])]}, [_edit()], mixed) == []


def test_other_finding_kinds_and_other_reasons_are_untouched() -> None:
    assert _errors({"findings": [_finding([5], "contradiction")]}, [_edit()]) == []
    assert _errors({"findings": [{"id": "F01", "claim_kind": "unsupported_claim", "lines": []}]}, [_edit()]) == []
    assert _errors({"findings": [_finding([5])]}, []) == []


def test_review_checks_quotes_the_error_back_only_for_lane_l_edit_scope() -> None:
    output = {
        "findings": [
            {
                "id": "F01",
                "claim_kind": "unsupported_claim",
                "lines": [5],
                "text": "385 is not supported",
                "quote": "x",
            }
        ]
    }
    rows = applied_edit_rows([_edit()], FACTS)
    common: dict[str, Any] = {"candidate_readme": CANDIDATE, "facts": FACTS, "plan": {"sections": []}}
    scoped = review_checks(
        dict(output), **common, changed=CHANGED, applied=rows, original_readme=ORIGINAL
    )
    assert scoped and "deterministic edit stale_type_count" in scoped[0]
    unscoped = review_checks(dict(output), **common)
    assert not any("deterministic edit" in e for e in unscoped)
