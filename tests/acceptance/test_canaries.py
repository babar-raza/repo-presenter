"""TC-024 part d / design doc 2026-11-06-acceptance-redesign.md I5: per-candidate canaries.

Before a candidate seals, it is run through every applicable, already-built mutation operator
(``readme.review.calibration.mutations``, the calibration harness's own fixtures -- reused here,
not reinvented) and the deterministic rule that owns that operator's defect class must still
reject the mutated text. ``readme.bundle.seal.candidate_canaries`` is the mechanism; this file
proves it against real operators/rules (no model call, no network) and proves the result is the
right shape to become ``AcceptanceRecord.canaries`` (TC-013's schema: "the acceptance record
carries canary ids and outcomes; a record without them is not an acceptance").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.acceptance.record import AcceptanceRecord, build_record, classify_record
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.readme.bundle.seal import (
    CANARY_OPERATORS,
    SealInputs,
    candidate_canaries,
)
from tests.readme.composition.synthetic import make_entry, make_facts

LONG_PARAGRAPH = (
    "This widget library renders every supported shape to PNG and SVG with a single call, and "
    "the renderer preserves color fidelity across every output format it supports today."
)
assert len(LONG_PARAGRAPH) >= 120  # the operator's and the rule's own shared threshold


def _inputs(out_dir: Path) -> SealInputs:
    """Just enough of ``SealInputs`` for ``candidate_canaries``, which reads only ``entry``,
    ``source_revision`` and ``facts`` -- the rest are placeholders no canary operator in
    ``CANARY_OPERATORS`` ever touches."""
    return SealInputs(
        entry=make_entry(),
        source_revision="r" * 40,
        facts=make_facts(),
        prompts=None,  # type: ignore[arg-type]
        out_dir=out_dir,
        facts_path=out_dir / "facts.json",
        candidates_root=out_dir,
        provider_calls=0,
        invocation=Invocation.begin(),
    )


# --- the canary mechanism itself -----------------------------------------------------------------


def test_a_readme_with_a_repeated_long_paragraph_admits_the_canary_and_it_is_caught(
    tmp_path: Path,
) -> None:
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)
    assert outcomes == {"duplicate_paragraph": True}


def test_a_readme_with_no_long_paragraph_admits_no_canary_at_all(tmp_path: Path) -> None:
    """The operator finds nowhere to inject its mutation (no paragraph reaches the threshold) --
    the canary is left OUT of the result, never recorded as a vacuous ``True``."""
    readme = "# Widget\n\nShort paragraph.\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)
    assert outcomes == {}


def test_every_declared_canary_operator_is_actually_exercised_by_the_fixture_above(
    tmp_path: Path,
) -> None:
    """A guard against ``CANARY_OPERATORS`` silently growing an operator this file never proves
    admits a mutation: every declared operator must appear in the first test's outcome."""
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)
    assert set(outcomes) == set(CANARY_OPERATORS)


def test_candidate_canaries_makes_no_provider_or_network_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Canaries are a deterministic, zero-call mechanism (TC-024's closeout: "this card does not
    itself make any new provider call"). Any attempt to build a gateway client would raise."""
    from repo_presenter.core.llm import jobs as jobs_module

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("candidate_canaries made a provider call")

    monkeypatch.setattr(jobs_module.transport, "build_client", forbidden)
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    assert candidate_canaries(_inputs(tmp_path), readme) == {"duplicate_paragraph": True}


# --- feeding into TC-013's acceptance record -----------------------------------------------------


def test_canary_outcomes_feed_acceptance_records_canaries_field_and_all_caught_is_required(
    tmp_path: Path,
) -> None:
    """TC-013's own contract (``AcceptanceRecord.canaries_caught``): every recorded canary must be
    caught, or the candidate never reaches ``provisionally-accepted``. The mechanism this file
    proves (``candidate_canaries``) produces exactly the ``{id: bool}`` shape that field expects."""
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)

    caught = AcceptanceRecord(repository="org/widget", lane="R", canaries=outcomes)
    assert caught.canaries_caught is True

    # a canary that, hypothetically, was NOT caught (not something this project's own detector
    # ever does for this operator -- that is duplicate_paragraph_rule's own test's job -- but the
    # acceptance record's gate must still block on one if it ever happened)
    missed = AcceptanceRecord(repository="org/widget", lane="R", canaries={**outcomes, "duplicate_paragraph": False})
    assert missed.canaries_caught is False


def test_a_record_with_no_canaries_recorded_is_vacuously_caught_but_a_real_candidate_always_has_some(
    tmp_path: Path,
) -> None:
    """``AcceptanceRecord.canaries_caught`` is vacuously ``True`` on ``{}`` (TC-013's own design:
    "no canary run means nothing was missed") -- but this file's own fixture candidate always
    admits at least one real canary, so the vacuous case is never what actually ships."""
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)
    assert outcomes  # the fixture is not accidentally the vacuous case
    assert AcceptanceRecord(repository="org/widget", lane="R", canaries={}).canaries_caught is True


def test_build_record_with_real_canary_outcomes_satisfies_part_b_and_c_of_provisional_criteria(
    tmp_path: Path,
) -> None:
    """``build_record``/``classify_record`` (TC-013) read ``canaries`` exactly as
    ``candidate_canaries`` produces it -- end to end, without re-deriving either module's own
    logic here. Certificates are deliberately left unsatisfied (TC-022a/TC-022b's job, out of
    this card's scope), so the ceiling is ``sealed``/``deterministically-validated``, not
    ``provisionally-accepted`` -- this test only proves (b)+(c) of
    ``AcceptanceRecord.provisional_criteria_met``, not (a)."""
    readme = f"# Widget\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}\n"
    outcomes = candidate_canaries(_inputs(tmp_path), readme)

    record = build_record(
        "org/widget",
        "R",
        sealed=True,
        deterministically_validated=True,
        mechanism_verdicts={"lane_r_pipeline": True},
        canaries=outcomes,
        calibration_path=tmp_path / "no_such_calibration.json",
        responsibility_path=tmp_path / "no_such_responsibility.json",
    )
    assert record.mechanism_verdicts_pass is True
    assert record.canaries_caught is True
    assert record.certificates.complete is False  # (a) is deliberately out of reach here
    assert classify_record(record) == "deterministically-validated"
