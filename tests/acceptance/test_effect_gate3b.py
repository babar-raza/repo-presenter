"""TC-013 action item 4 / REQ-ACCEPT-003: `propose.effect` gate 3b now reads the acceptance
contract instead of the frozen reviewer-calibration file. `repo_presenter.propose.effect.classify`
is monkeypatched (the same style the module's own existing test suite uses for
`load_calibration`) so these tests exercise the gate in isolation, without needing real
`data/acceptance_calibration.json`/`data/acceptance_responsibility.json` fixtures or a live
GitHub call - every later gate in `propose_candidate` still runs unmodified."""

from __future__ import annotations

from typing import Any

import pytest
from support import make_permit

from repo_presenter.acceptance.record import (
    DELIVERED,
    INDEPENDENTLY_ACCEPTED,
    LIVE_VERIFIED,
    PROVISIONALLY_ACCEPTED,
    PUBLICATION_READY,
)
from repo_presenter.authorization.refusals import Refusal
from repo_presenter.propose import effect
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"

ACCEPTED_REVIEW = ReviewVerdict.folded(
    (),
    model_verdict="ACCEPT",
    prompt_version="17",
    model_served="qwen3-next",
    request_sha256="a" * 64,
    reply_sha256="b" * 64,
    calibration_status="PASSED",
)


def _must_not_run(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("a gate after acceptance certification was reached")


def _propose(**overrides: object) -> effect.ProposalEffectResult:
    fields: dict[str, object] = dict(
        repository=REPOSITORY,
        readme_text="# README\n",
        source_revision="0" * 40,
        base_branch="main",
        token="ghs_write",
        environment={effect.AUTHORIZATION_VARIABLE: "1"},
        review=ACCEPTED_REVIEW,
        permit=make_permit(REPOSITORY),
        load_authorization=_must_not_run,
        recheck_source=_must_not_run,
        verify_token=_must_not_run,
        pr_title="t",
        pr_body="b",
    )
    fields.update(overrides)
    return effect.propose_candidate(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "stuck_state",
    ["generated", "sealed", "deterministically-validated", PROVISIONALLY_ACCEPTED],
)
def test_a_candidate_stuck_below_independently_accepted_is_refused_with_acceptance_not_certified(
    monkeypatch: pytest.MonkeyPatch, stuck_state: str
) -> None:
    """The exact case the card asks for: a candidate at `provisionally-accepted` - every
    mechanism-level check passing, but with no audit - is never proposed, and neither is anything
    even further from it (generated/sealed/deterministically-validated)."""
    monkeypatch.setattr(effect, "classify", lambda *a, **k: stuck_state)
    result = _propose()
    assert result.effected is False
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED
    assert stuck_state in result.reason


def test_independently_accepted_alone_is_not_yet_the_publish_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`independently-accepted` is NOT in `PUBLISHABLE_STATES` - the card's own progression puts
    `publication-ready` (and later) above it; gate 3b must still refuse here. This is also the
    negative control's exact target: a mutation collapsing `independently-accepted` into
    `provisionally-accepted` must not change this outcome (it is already refused either way), so
    the state-chain unit tests in test_record.py are what actually prove the mutation is caught -
    this test instead pins that INDEPENDENTLY_ACCEPTED alone never satisfies gate 3b."""
    monkeypatch.setattr(effect, "classify", lambda *a, **k: INDEPENDENTLY_ACCEPTED)
    result = _propose()
    assert result.effected is False
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED


@pytest.mark.parametrize("ready_state", [PUBLICATION_READY, DELIVERED, LIVE_VERIFIED])
def test_a_publishable_state_passes_gate_3b_through_to_the_next_gate(
    monkeypatch: pytest.MonkeyPatch, ready_state: str
) -> None:
    """Once classify() reports `publication-ready` or later, gate 3b lets the call through to the
    next gate (the write-scoped token check) - proven by refusing there instead, with a token of
    `None`, rather than at gate 3b."""
    monkeypatch.setattr(effect, "classify", lambda *a, **k: ready_state)
    result = _propose(token=None)
    assert result.effected is False
    assert result.reason_code == Refusal.NO_WRITE_TOKEN


def test_gate_3b_runs_before_the_write_scoped_token_check_and_makes_no_network_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def recording_classify(*args: Any, **kwargs: Any) -> str:
        calls.append(("classify", args, kwargs))
        return PROVISIONALLY_ACCEPTED

    monkeypatch.setattr(effect, "classify", recording_classify)
    result = _propose()
    assert result.effected is False
    assert result.reason_code == Refusal.ACCEPTANCE_NOT_CERTIFIED
    assert len(calls) == 1
    (_, args, kwargs) = calls[0]
    assert args[0] == REPOSITORY
    # mechanism_verdicts is passed as a keyword derived from the review's own pr_eligible flag -
    # proof that gate 3b still looks at the review, not just the repository name.
    assert "mechanism_verdicts" in kwargs
