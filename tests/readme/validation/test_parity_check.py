"""BC-17 (R2 parity) blocks a candidate that loses published-README content, with exactly the
parity gate's exemptions; the S4 patch refuses a reply that keeps the loss; Lane L cannot lose
content outside an evidenced edit by construction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from repo_presenter.readme import parity_gate as pg
from repo_presenter.readme.correction.model import (
    BROKEN_LINK,
    FALSE_CLAIM_FIX,
    Edit,
    InvalidEditError,
)
from repo_presenter.readme.reconciliation.patch import (
    PatchScope,
    _loss_units,
    patch_checks,
)
from repo_presenter.readme.validation.blocking import CHECK_NAMES, JUDGES
from repo_presenter.readme.validation.parity import PARITY_LOSS_MARKER, parity_failures
from tests.readme import test_parity_gate as fx

QUICK_UNIT = "inherited_unit:003.code_block"
PROMO = ("OMIT_UNSUPPORTED", [], "promotional build instruction")


def check_candidate(readme=None, facts=None, dispositions=None, bench=None):
    """A ``validation.failures.Candidate`` as far as BC-17 reads one."""
    facts = fx.base_facts() if facts is None else facts
    rows = fx.rows() if dispositions is None else dispositions
    return SimpleNamespace(
        readme=fx.benchmark() if readme is None else readme,
        benchmark_readme=fx.benchmark() if bench is None else bench,
        facts=SimpleNamespace(
            facts=[
                SimpleNamespace(
                    id=f["id"], kind=f["kind"], value=f["value"],
                    polarity=f["polarity"], attributes=f["attributes"],
                )
                for f in facts
            ]
        ),
        dispositions={"dispositions": list(rows)},
    )


def without_quick_start_block(text: str) -> str:
    return text.replace(f"{fx.FENCE}csharp\n{fx.QUICK}{fx.FENCE}\n", "")


def test_bc17_is_a_registered_blocking_check():
    assert JUDGES["BC-17"] is parity_failures and "BC-17" in CHECK_NAMES


def test_identical_candidate_passes():
    assert parity_failures(check_candidate()) == []


def test_no_benchmark_means_nothing_to_lose():
    assert parity_failures(check_candidate(bench="")) == []


def test_promotional_omission_of_a_code_block_blocks_as_reconciling_with_its_unit():
    # Imaging .NET Lane R: <ProjectReference .../> given OMIT_UNSUPPORTED "promotional".
    failures = parity_failures(
        check_candidate(
            without_quick_start_block(fx.benchmark()),
            dispositions=fx.rows(**{QUICK_UNIT: PROMO}),
        )
    )
    assert [(f.stage, f.unit) for f in failures] == [("RECONCILING", QUICK_UNIT)]
    assert PARITY_LOSS_MARKER in failures[0].detail
    assert "code_blocks" in failures[0].detail


@pytest.mark.parametrize(
    "row,facts",
    [
        (("NON_CONTENT", [], ""), None),
        (("CORRECT_WITH_EVIDENCE", [], ""), None),
        (("OMIT_UNSUPPORTED", [], "the build step is obsolete since 2.0"), None),
        (
            ("OMIT_UNSUPPORTED", ["example:001"], "wrong"),
            fx.base_facts(example_polarity="CONTRADICTED"),
        ),
    ],
)
def test_evidenced_omissions_are_exempt(row, facts):
    assert (
        parity_failures(
            check_candidate(
                without_quick_start_block(fx.benchmark()),
                facts=facts,
                dispositions=fx.rows(**{QUICK_UNIT: row}),
            )
        )
        == []
    )


def test_contradicted_example_fact_exempts_the_block():
    assert (
        parity_failures(
            check_candidate(
                without_quick_start_block(fx.benchmark()),
                facts=fx.base_facts(example_polarity="CONTRADICTED"),
                dispositions=fx.rows(**{QUICK_UNIT: PROMO}),
            )
        )
        == []
    )


def test_install_replaced_by_the_verified_command_is_exempt():
    bench = fx.benchmark().replace("dotnet add package Foo.Bar", "dotnet add package Foo.Old")
    assert parity_failures(check_candidate(bench=bench)) == []


def test_version_replaced_by_the_verified_version_is_exempt():
    bench = fx.benchmark().replace("version 1.2.3", "version 1.2.0")
    assert parity_failures(check_candidate(bench=bench)) == []


def test_maintainer_diagram_is_exempt_when_the_renderer_draws_one():
    diagram = f"{fx.FENCE}mermaid\ngraph TD\n  A --> B\n{fx.FENCE}\n"
    bench = fx.benchmark() + "\n" + diagram
    drawn = fx.benchmark() + "\n" + f"{fx.FENCE}mermaid\ngraph LR\n  X --> Y\n{fx.FENCE}\n"
    assert parity_failures(check_candidate(drawn, bench=bench)) == []
    assert parity_failures(check_candidate(bench=bench))  # without its own diagram it is owed


def test_a_lost_item_no_unit_holds_fails_at_extraction():
    bench = fx.benchmark() + "\nSee [the guide](https://guide.example.com/x).\n"
    failures = parity_failures(check_candidate(bench=bench))
    assert [(f.stage, f.unit) for f in failures] == [("EXTRACTING", None)]


def test_a_lost_section_fails_on_its_losing_units():
    readme = fx._without_support(fx.benchmark())
    failures = parity_failures(
        check_candidate(
            readme, dispositions=fx.rows(**{"inherited_unit:007.paragraph": "SUPERSEDE_REDUNDANT"})
        )
    )
    assert ("RECONCILING", "inherited_unit:007.paragraph") in [(f.stage, f.unit) for f in failures]


# --- one standard: the parity gate and the check agree on every fixture ------------------------

AGREEMENT = [
    {},
    {"readme": without_quick_start_block(fx.benchmark()), "dispositions": fx.rows(**{QUICK_UNIT: PROMO})},
    {"readme": without_quick_start_block(fx.benchmark()), "facts": fx.base_facts(example_polarity="CONTRADICTED")},
    {"readme": fx._without_support(fx.benchmark())},
    {
        "readme": fx._without_support(fx.benchmark()),
        "dispositions": fx.rows(**{"inherited_unit:007.paragraph": "NON_CONTENT"}),
    },
    {"readme": fx.benchmark().replace("[the docs](https://docs.example.com/foo)", "the docs")},
    {"readme": fx.benchmark().replace("Requires version 1.2.3.", "")},
    {"readme": fx.benchmark().replace("dotnet add package Foo.Bar", "dotnet add package Other")},
]


@pytest.mark.parametrize("case", AGREEMENT)
def test_parity_gate_and_bc17_agree(case):
    sealed = fx.cand(
        case.get("readme"), facts=case.get("facts"), dispositions=case.get("dispositions")
    )
    result = pg.evaluate("o/n", sealed, fx.benchmark())
    gate_lost = [
        detail
        for d in result.dimensions
        if d.name in pg.CONTENT_DIMENSIONS
        for detail in d.details
    ]
    failures = parity_failures(
        check_candidate(case.get("readme"), case.get("facts"), case.get("dispositions"))
    )
    assert bool(gate_lost) == bool(failures)
    losses = pg.content_losses(sealed, fx.benchmark())
    assert len(losses) == len(gate_lost)
    assert {f.unit for f in failures} == {u for loss in losses for u in loss.units} | (
        {None} if any(not loss.units for loss in losses) else set()
    )


# --- the S4 repair refuses a reply that keeps the loss ------------------------------------------


def _scope(contradicted=frozenset()):
    return PatchScope(
        batch_id="b1", unit_ids=(QUICK_UNIT,), shown={}, contract={}, deferred=frozenset(),
        holdable=("quick_start", "installation"), parity_lost=frozenset({QUICK_UNIT}),
        contradicted=frozenset(contradicted),
    )


def _reply(disposition, fact_ids=(), rationale=""):
    return {
        "dispositions": [
            {
                "unit_id": QUICK_UNIT,
                "disposition": disposition,
                "fact_ids": list(fact_ids),
                "rationale": rationale,
            }
        ]
    }


@pytest.mark.parametrize("disposition", ["OMIT_UNSUPPORTED", "SUPERSEDE_REDUNDANT", "DEFER_UNRESOLVED"])
def test_a_reply_that_keeps_the_item_lost_is_refused(disposition):
    errors = patch_checks(_scope(), None)(_reply(disposition, rationale="promotional"))
    assert errors and f"still {disposition}" in errors[0]


def test_a_reply_that_keeps_or_evidences_the_omission_passes():
    for disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE", "PRESERVE_ATTRIBUTED", "NON_CONTENT"):
        assert patch_checks(_scope(), None)(_reply(disposition)) == []
    cited = _reply("OMIT_UNSUPPORTED", ["example:001"], "wrong")
    assert patch_checks(_scope({"example:001"}), None)(cited) == []
    assert patch_checks(_scope(), None)(cited)  # the cited fact is not CONTRADICTED


def test_the_loss_is_judged_after_normalisation():
    def normaliser(revised):
        for entry in revised["dispositions"]:
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
        return []

    errors = patch_checks(_scope(), normaliser)(_reply("VERIFIED_PRESERVE"))
    assert errors and "still SUPERSEDE_REDUNDANT" in errors[0]


def test_only_parity_failures_mark_a_unit_parity_lost():
    record = {
        "failures": [
            {"unit_id": QUICK_UNIT, "detail": f"{QUICK_UNIT} holds x, {PARITY_LOSS_MARKER}"},
            {"unit_id": "inherited_unit:009.paragraph", "detail": "has 2 dispositions"},
        ]
    }
    assert _loss_units(record, PARITY_LOSS_MARKER) == {QUICK_UNIT}
    assert _loss_units(record) == set()


# --- Lane L: no loss outside an evidenced edit, by construction ---------------------------------


@pytest.mark.parametrize("kind", [BROKEN_LINK, FALSE_CLAIM_FIX])
def test_lane_l_edit_without_evidence_cannot_exist(kind):
    with pytest.raises(InvalidEditError):
        Edit(kind, "d", 0, 3, "abc", "xyz", (), "r")


def test_lane_l_every_evidenced_edit_accounts_for_what_it_removes():
    edit = {"original": "https://docs.example.com/foo", "detector": "BROKEN_LINK", "fact_ids": ["link_target:001"]}
    readme = fx.benchmark().replace("[the docs](https://docs.example.com/foo)", "the docs")
    result = pg.evaluate("o/n", fx.cand(readme, lane="L", edits=[edit]), fx.benchmark())
    assert {d.name: d.passed for d in result.dimensions}["technical_content"]
