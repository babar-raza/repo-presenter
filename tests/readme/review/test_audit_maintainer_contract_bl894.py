"""BL-894: the whole-document M9 audit honours the production review's maintainer-line contract.

Audit round 12 (seed run 45129080547) flagged its one Lane R clean control, the PDF TypeScript seal 851c1a6a
(sealed by hosted run 45074125387), on seven ``unsupported_claim`` findings that were all kept-verbatim maintainers'
text. Five (lines 4751, 4753 to 4756) are exactly the BL-890 class: ``VERIFIED_PRESERVE`` into
``scope_limitations`` citing only ``public_symbol`` facts, which ``scope.maintainer_lines`` marks and the
production review voids; the audit reviews with ``rendered=False``, which never computes those lines. The audit now
clears an ``unsupported_claim`` row on a maintainer line, row by row, with the same predicate.

Negative controls (each keeps its flag): any other claim kind, a line that is not a maintainer line (authored, or a
seeded mutation of a kept line), a flag already supported, an unlocated flag, and no derivation at all.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from repo_presenter.readme.review.derivation import Derivation

REPO = Path(__file__).resolve().parents[3]

TEXT = "# T\n\nAuthored sentence.\n- **Reader.** Reader neither recomputes nor draws these barcodes.\n- **Other.** Stream payloads are not decoded.\n"


def _auditor():
    spec = importlib.util.spec_from_file_location("run_m9_auditor_bl894", REPO / "scripts" / "run_m9_auditor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(line: int, kind: str = "unsupported_claim", *, verdict: str = "unverifiable", source: str = "llm",
         located: bool = True) -> dict:
    return {"candidate_id": "c1", "claim": f"[{kind}] something", "verdict": verdict, "path": "c1.md", "line": line,
            "evidence": "audit: no registered clearance", "located": located, "source": source}


def _derivation(maintainer: set[int]) -> Derivation:
    return Derivation(derivable=frozenset(), underived=frozenset(), maintainer=frozenset(maintainer))


def _verdicts(rows: list[dict], maintainer: set[int]) -> list[str]:
    out = _auditor().apply_derivation("c1", TEXT, rows, _derivation(maintainer))
    return [r["verdict"] for r in out]


def test_an_unsupported_claim_on_a_maintainer_line_is_cleared_by_the_contract() -> None:
    out = _auditor().apply_derivation("c1", TEXT, [_row(4), _row(5)], _derivation({4, 5}))
    assert [r["verdict"] for r in out] == ["supported", "supported"]
    assert all(r["cleared_by"] == "maintainer_contract" and "maintainer_lines" in r["evidence"] for r in out)


def test_each_row_is_judged_alone_so_a_quote_that_reaches_an_authored_line_still_flags() -> None:
    assert _verdicts([_row(3), _row(4)], {4}) == ["unverifiable", "supported"]


def test_negative_controls_keep_the_flag() -> None:
    for kind in ("contradiction", "quality", "omission", "absence", "name_denial"):
        assert _verdicts([_row(4, kind)], {4}) == ["unverifiable"], kind
    assert _verdicts([_row(3)], {4}) == ["unverifiable"]  # authored line, not a maintainer line
    assert _verdicts([_row(4)], set()) == ["unverifiable"]  # a seeded mutation of a kept line is not marked
    assert _verdicts([_row(4, located=False)], {4}) == ["unverifiable"]
    rows = [_row(4, "contradiction", verdict="false")]
    assert _verdicts(rows, {4}) == ["false"]


def test_no_derivation_changes_nothing() -> None:
    rows = [_row(4)]
    assert _auditor().apply_derivation("c1", TEXT, rows, None) == rows


def test_the_deterministic_underived_finding_is_unaffected() -> None:
    row = _row(4, source="deterministic")
    assert _verdicts([row], {4}) == ["unverifiable"]


def test_the_seals_maintainer_lines_are_what_the_audit_clears() -> None:
    """The set the audit receives is ``scope.maintainer_lines`` over the seal's own facts and dispositions: the
    BL-890 limitation bullets, and nothing for Lane L."""
    from tests.readme.review.test_scoped_contract import (
        CANDIDATE, FIRST, _limits_facts, _verified,
    )
    from repo_presenter.readme.review.scope import maintainer_lines

    marked = maintainer_lines(CANDIDATE, _limits_facts(), _verified("VERIFIED_PRESERVE", "scope_limitations", "public_symbol:document.open"))
    assert marked == {FIRST, FIRST + 1}
    assert maintainer_lines(CANDIDATE, _limits_facts(), _verified("VERIFIED_PRESERVE", "api_reference")) == frozenset()
