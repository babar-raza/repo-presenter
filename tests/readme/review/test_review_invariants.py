"""V3: fold invariants, proved two ways. An exhaustive check over small finding sets proves that
ACCEPT implies every finding is CLEARED by a registered clearance that still holds when re-run; a
structural check over the source tree proves no ACCEPT/REJECT value is assigned outside the fold
and no CLEARED status is constructed outside the registered-clearance path."""

from __future__ import annotations

import ast
import itertools
from dataclasses import replace
from pathlib import Path

from repo_presenter.readme.review.clearances import CLEARANCES, apply_clearances
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import (
    MODEL_VERDICTS,
    REJECT_VERDICTS,
    ReviewVerdict,
    fold_verdict,
)
from tests.readme.review.review_support import context, llm, rule_finding

SRC = Path(__file__).resolve().parents[3] / "src" / "repo_presenter"
REVIEW = SRC / "readme" / "review"


# ---------------------------------------------------------------------------
# exhaustive fold property
# ---------------------------------------------------------------------------


def _pool() -> list[Finding]:
    ctx = context()
    pool = [
        rule_finding(),
        llm("quality", finding_id="F01"),
        llm("contradiction", finding_id="F02", quote="Renders a Widget to PNG"),
        llm("absence", finding_id="F03", absent=("PluginHost",)),
        llm("absence", finding_id="F04", absent=("quantum teleport mode",)),
        llm("name_denial", finding_id="F05", unsupported_names=("Widget",)),
        llm("name_denial", finding_id="F06", unsupported_names=("Gadget",)),
        llm("absence", finding_id="F07", absent=("SvgExporter",)),
    ]
    return [apply_clearances(finding, ctx) for finding in pool]


def test_the_pool_mixes_cleared_and_blocking_findings() -> None:
    statuses = {finding.status for finding in _pool()}
    assert statuses == {"BLOCKING", "CLEARED"}


def _still_holds(finding: Finding) -> bool:
    """Re-derive the clearance from scratch: the stored proof is the proof a registered clearance
    produces for the finding as it was before clearing."""
    assert finding.clearance is not None
    original = replace(finding, status="BLOCKING", clearance=None)
    return CLEARANCES[finding.clearance.name](original, context()) == finding.clearance


def test_accept_implies_every_finding_is_cleared_by_a_registered_clearance() -> None:
    pool = _pool()
    model_verdicts = [None, *MODEL_VERDICTS, "LGTM"]
    accepts = 0
    total = 0
    for size in range(4):
        for combo in itertools.combinations(pool, size):
            for model_verdict in model_verdicts:
                for errors in ((), ("a contract error",)):
                    total += 1
                    folded = fold_verdict(
                        model_verdict=model_verdict, findings=combo, reply_errors=errors
                    )
                    if folded.verdict != "ACCEPT":
                        continue
                    accepts += 1
                    assert not errors
                    assert (
                        model_verdict is None
                        or model_verdict == "ACCEPT"
                        or (model_verdict in REJECT_VERDICTS)
                    )
                    for finding in combo:
                        assert finding.source == "llm"
                        assert finding.status == "CLEARED"
                        assert finding.clearance is not None
                        assert finding.clearance.name in CLEARANCES
                        assert _still_holds(finding)
                    if model_verdict in REJECT_VERDICTS:
                        assert combo, (
                            "a REJECT with no finding must never fold to ACCEPT"
                        )
    assert total > 2000 and accepts > 50


def test_the_fold_blocks_exactly_when_something_blocks() -> None:
    """The converse, so the fold is neither always-ACCEPT nor always-REJECT: a verdict is ACCEPT
    whenever the reply is valid, the model did not ask for retry, nothing blocks and a model
    REJECT has at least one finding to have cleared."""
    pool = _pool()
    for size in range(4):
        for combo in itertools.combinations(pool, size):
            for model_verdict in [
                None,
                "ACCEPT",
                *REJECT_VERDICTS,
                "INSUFFICIENT_EVIDENCE",
            ]:
                folded = fold_verdict(model_verdict=model_verdict, findings=combo)
                clean = all(f.status == "CLEARED" for f in combo)
                if (
                    model_verdict == "INSUFFICIENT_EVIDENCE"
                    or model_verdict in REJECT_VERDICTS
                    and not combo
                ):
                    expected = "REJECT"
                else:
                    expected = "ACCEPT" if clean else "REJECT"
                assert folded.verdict == expected, (model_verdict, combo)


def test_a_returned_reject_never_becomes_accept_without_a_clearance_for_each_finding() -> (
    None
):
    for finding in _pool():
        verdict = fold_verdict(
            model_verdict="REJECT_FACTUAL", findings=(finding,)
        ).verdict
        assert (verdict == "ACCEPT") == (finding.status == "CLEARED")


def test_every_verdict_object_is_the_fold_of_its_fields() -> None:
    for size in range(3):
        for combo in itertools.combinations(_pool(), size):
            verdict = ReviewVerdict.folded(combo)
            assert (
                verdict.verdict
                == fold_verdict(model_verdict=None, findings=combo).verdict
            )


# ---------------------------------------------------------------------------
# structural checks over the source tree
# ---------------------------------------------------------------------------


def _parse(path: Path) -> ast.Module:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent  # type: ignore[attr-defined]
    return tree


def _ancestors(node: ast.AST) -> list[ast.AST]:
    chain = []
    while hasattr(node, "parent"):
        node = node.parent  # type: ignore[attr-defined]
        chain.append(node)
    return chain


def _constants(value: str) -> list[tuple[Path, ast.Constant]]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Constant) and node.value == value:
                found.append((path, node))
    return found


def _is_comparison(node: ast.AST) -> bool:
    return any(isinstance(a, ast.Compare) for a in _ancestors(node))


def _is_literal_type(node: ast.AST) -> bool:
    return any(
        isinstance(a, ast.Subscript) and getattr(a.value, "id", "") == "Literal"
        for a in _ancestors(node)
    )


def _enclosing(node: ast.AST) -> str | None:
    for ancestor in _ancestors(node):
        if isinstance(ancestor, ast.FunctionDef):
            return ancestor.name
    return None


def _assigned_name(node: ast.AST) -> str | None:
    for ancestor in _ancestors(node):
        if isinstance(ancestor, ast.Assign) and isinstance(
            ancestor.targets[0], ast.Name
        ):
            return ancestor.targets[0].id
    return None


def test_no_verdict_value_is_assigned_outside_the_fold() -> None:
    """Every "ACCEPT"/"REJECT" literal in the source is a comparison, a type, the model-verdict
    vocabulary, or inside ``fold_verdict`` -- never a value handed to a verdict."""
    offenders = []
    for value in ("ACCEPT", "REJECT"):
        for path, node in _constants(value):
            if _is_comparison(node) or _is_literal_type(node):
                continue
            if (
                _enclosing(node) == "fold_verdict"
                or _assigned_name(node) == "MODEL_VERDICTS"
            ):
                continue
            offenders.append(f"{path.relative_to(SRC)}:{node.lineno} {value!r}")
    assert offenders == []


def test_no_verdict_object_is_built_with_a_literal_verdict() -> None:
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "ReviewVerdict"
            ):
                for keyword in node.keywords:
                    assert not (
                        keyword.arg == "verdict"
                        and isinstance(keyword.value, ast.Constant)
                    ), f"{path}:{node.lineno}"


def test_the_fold_is_the_only_function_that_decides_a_verdict() -> None:
    """Exactly one function constructs a ``Fold`` and it is ``fold_verdict``."""
    makers = set()
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Fold":
                makers.add((path.name, _enclosing(node)))
    assert makers == {("verdict.py", "fold_verdict")}


def test_a_cleared_status_is_constructed_only_by_the_registered_clearance_path() -> (
    None
):
    offenders = []
    for path, node in _constants("CLEARED"):
        if _is_comparison(node) or _is_literal_type(node):
            continue
        if (path.name, _enclosing(node)) == ("clearances.py", "apply_clearances"):
            continue
        offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert offenders == []


def test_clearance_proofs_are_sealed_only_by_the_four_registered_functions() -> None:
    callers = set()
    constructors = set()
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", "")
            if name == "_seal_clearance":
                callers.add((path.name, _enclosing(node)))
            if name == "Clearance":
                constructors.add((path.name, _enclosing(node)))
    assert callers == {
        ("clearances.py", "absence_present"),
        ("clearances.py", "absence_unsourced"),
        ("clearances.py", "names_supported"),
        ("clearances.py", "omission_present"),
    }
    assert constructors == {
        ("findings.py", "_seal_clearance"),
        ("findings.py", "from_record"),
    }


def test_each_registered_clearance_seals_a_proof_under_its_own_name() -> None:
    tree = _parse(REVIEW / "clearances.py")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "_seal_clearance"
        ):
            first = node.args[0]
            assert isinstance(first, ast.Constant)
            assert first.value == _enclosing(node)
    assert set(CLEARANCES) == {fn.__name__ for fn in CLEARANCES.values()}


def test_no_clearance_reads_a_quote_against_a_fact_value() -> None:
    """Plan D3's explicit exclusion, checked structurally: no clearance function touches a
    finding's quote to compare it with a fact. The only use of ``quote`` in clearances.py is the
    absence guard that refuses to clear a string the finding itself quotes."""
    tree = _parse(REVIEW / "clearances.py")
    uses = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "quote":
            uses.append(_enclosing(node))
    assert set(uses) <= {"_claims"}
