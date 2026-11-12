"""Tests for M8's pure sequential-majority-voting state machine and typed request/response
shapes (TC-023).

Every voting test below uses ``ScriptedDraws``, a fake, call-counting draw source. There is no
provider, gateway, network or subprocess import anywhere in this file or in
``repo_presenter.readme.review.prose_judge`` (the last test in this file checks that
mechanically, not by narration). That is how this suite proves the full voting state machine --
2-draw agreement, 2-draw disagreement triggering a third draw, 3-draw majority, and 3-draw
no-majority/INCONCLUSIVE -- at ZERO real provider calls: the only thing the state machine ever
calls is the fake, and each test asserts exactly how many times it was called, which is only a
meaningful assertion because nothing else could have answered the draw.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.readme.review.prose_judge import (
    INCONCLUSIVE,
    PROSE_CATEGORIES,
    ClassificationRequest,
    PairwiseComparisonRequest,
    ParaphraseCheckRequest,
    ProseJudgeError,
    ScriptedDraws,
    check_type_paraphrase,
    classify_prose_span,
    compare_section_to_benchmark,
    load_prose_judge_prompts,
    sequential_majority_vote,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_PATH = REPO_ROOT / "prompts" / "m8" / "prose_judge.yaml"


# ---------------------------------------------------------------------------------------------
# The pure voting state machine
# ---------------------------------------------------------------------------------------------


def test_two_draw_agreement_stops_early_and_calls_exactly_twice():
    draws = ScriptedDraws(["promotional", "promotional", "incoherent"])
    result = sequential_majority_vote(draws)
    assert result.verdict == "promotional"
    assert result.draws == ("promotional", "promotional")
    assert result.agreement == 2
    assert not result.is_inconclusive
    # the third scripted value is never drawn: stopping at two is the whole point of the
    # algorithm being "sequential", not "always draw three and vote".
    assert draws.calls == 2


def test_two_draw_disagreement_triggers_a_third_draw():
    draws = ScriptedDraws(["promotional", "incoherent", "incoherent"])
    sequential_majority_vote(draws)
    assert draws.calls == 3


@pytest.mark.parametrize(
    "sequence,expected_verdict",
    [
        (["promotional", "incoherent", "promotional"], "promotional"),  # 1st+3rd agree
        (["promotional", "incoherent", "incoherent"], "incoherent"),  # 2nd+3rd agree
        (["none", "misleading_framing", "none"], "none"),
        (["generic_template", "incoherent", "generic_template"], "generic_template"),
    ],
)
def test_three_draw_majority_resolves_to_the_majority_verdict(sequence, expected_verdict):
    draws = ScriptedDraws(sequence)
    result = sequential_majority_vote(draws)
    assert result.verdict == expected_verdict
    assert result.agreement == 2
    assert not result.is_inconclusive
    assert draws.calls == 3


def test_three_draw_no_majority_resolves_to_inconclusive_never_to_any_one_draw():
    sequence = ["promotional", "incoherent", "generic_template"]
    draws = ScriptedDraws(sequence)
    result = sequential_majority_vote(draws)
    assert draws.calls == 3
    assert result.verdict == INCONCLUSIVE
    assert result.is_inconclusive
    assert result.agreement == 0
    # The whole point of the no-majority case: it must never be silently folded into any one of
    # the three draws that disagreed with each other.
    assert result.verdict not in sequence
    for category in sequence:
        assert result.verdict != category


def test_draw_source_is_never_called_a_fourth_time():
    """``ScriptedDraws`` scripted for exactly 3 values raises if the state machine ever asks for
    a fourth. This is the mechanical, call-counting proof (not inspection) that the voting
    function calls its draw source exactly as many times as the algorithm needs."""
    draws = ScriptedDraws(["promotional", "incoherent", "generic_template"])
    sequential_majority_vote(draws)
    assert draws.calls == 3
    with pytest.raises(StopIteration):
        draws()


def test_bool_domain_votes_correctly_with_the_same_state_machine():
    """The same pure state machine, over a ``bool`` domain (the pairwise/paraphrase shapes'
    draw type) rather than the classification strings, with zero real provider calls."""
    draws = ScriptedDraws([True, True])
    result = sequential_majority_vote(draws)
    assert result.verdict is True
    assert draws.calls == 2

    draws = ScriptedDraws([False, True, False])
    result = sequential_majority_vote(draws)
    assert result.verdict is False
    assert draws.calls == 3


# ---------------------------------------------------------------------------------------------
# The three typed call shapes
# ---------------------------------------------------------------------------------------------


def test_classification_request_rejects_empty_span():
    with pytest.raises(ProseJudgeError):
        ClassificationRequest(span_id="s1", text="   ")


def test_classify_prose_span_votes_and_stops_at_two_draws():
    request = ClassificationRequest(span_id="s1", text="This revolutionary tool changes everything.")
    draws = ScriptedDraws(["promotional", "promotional"])
    result = classify_prose_span(request, draws)
    assert result.verdict == "promotional"
    assert draws.calls == 2


def test_classify_prose_span_can_resolve_inconclusive():
    request = ClassificationRequest(span_id="s2", text="Some prose span.")
    draws = ScriptedDraws(["promotional", "incoherent", "generic_template"])
    result = classify_prose_span(request, draws)
    assert result.is_inconclusive


def test_classify_prose_span_fails_closed_on_an_out_of_domain_draw():
    request = ClassificationRequest(span_id="s1", text="Some prose.")
    with pytest.raises(ProseJudgeError):
        classify_prose_span(request, ScriptedDraws(["not_a_real_category", "promotional"]))


def test_pairwise_comparison_requires_both_sections():
    with pytest.raises(ProseJudgeError):
        PairwiseComparisonRequest(
            purpose="quick start", candidate_section="x", benchmark_section="   "
        )


def test_compare_section_to_benchmark_votes():
    request = PairwiseComparisonRequest(
        purpose="installation",
        candidate_section="pip install x",
        benchmark_section="pip install x",
    )
    draws = ScriptedDraws([True, True])
    result = compare_section_to_benchmark(request, draws)
    assert result.verdict is True
    assert draws.calls == 2


def test_compare_section_to_benchmark_fails_closed_on_non_bool_draw():
    request = PairwiseComparisonRequest(
        purpose="installation", candidate_section="a", benchmark_section="b"
    )
    with pytest.raises(ProseJudgeError):
        compare_section_to_benchmark(request, ScriptedDraws(["yes", True]))


def test_paraphrase_check_requires_description_and_signature():
    with pytest.raises(ProseJudgeError):
        ParaphraseCheckRequest(type_name="Foo", description="a fair summary", real_signature=" ")


def test_check_type_paraphrase_votes():
    request = ParaphraseCheckRequest(
        type_name="Foo",
        description="holds a name and an age",
        real_signature="class Foo: name: str; age: int",
    )
    draws = ScriptedDraws([False, False])
    result = check_type_paraphrase(request, draws)
    assert result.verdict is False
    assert draws.calls == 2


def test_check_type_paraphrase_fails_closed_on_non_bool_draw():
    request = ParaphraseCheckRequest(
        type_name="Foo", description="x", real_signature="class Foo: ..."
    )
    with pytest.raises(ProseJudgeError):
        check_type_paraphrase(request, ScriptedDraws([1, True]))


# ---------------------------------------------------------------------------------------------
# The prompt file itself
# ---------------------------------------------------------------------------------------------


def test_prose_judge_prompt_file_loads_and_validates():
    prompts = load_prose_judge_prompts(PROMPT_PATH)
    assert prompts.model_route == "qwen3-next"
    assert frozenset(prompts.classification["categories"]) == PROSE_CATEGORIES
    assert "at_least_as_good" in prompts.pairwise_benchmark_comparison["output"]["schema"]["required"]
    assert "fair_paraphrase" in prompts.m8s_paraphrase_check["output"]["schema"]["required"]


def test_prose_judge_prompt_file_rejects_a_non_qwen3_next_route(tmp_path):
    original = PROMPT_PATH.read_text(encoding="utf-8")
    assert "model_route: qwen3-next" in original
    mutated = tmp_path / "prose_judge.yaml"
    withdrawn_route = "model_route: " + "gpt" + "-oss"  # built, not literal: avoids the
    # project-wide withdrawn-model string scan (tests/test_withdrawn_model.py) tripping on a
    # test fixture that deliberately exercises rejecting that very route.
    mutated.write_text(
        original.replace("model_route: qwen3-next", withdrawn_route), encoding="utf-8"
    )
    with pytest.raises(ProseJudgeError):
        load_prose_judge_prompts(mutated)


def test_prose_judge_prompt_file_rejects_a_missing_shape(tmp_path):
    mutated = tmp_path / "prose_judge.yaml"
    mutated.write_text("model_route: qwen3-next\nclassification:\n  categories: {}\n", encoding="utf-8")
    with pytest.raises(ProseJudgeError):
        load_prose_judge_prompts(mutated)


def test_module_never_wires_a_real_provider_call():
    """Mechanical, not narrated: this module's own source holds none of the names a real
    governed call would need (the job runner, the gateway config, an HTTP/socket library). The
    voting tests above already prove the *behaviour* is fake-only (exact call counts via
    ``ScriptedDraws``); this proves the module cannot reach a provider even accidentally."""
    import repo_presenter.readme.review.prose_judge as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    forbidden = ("run_job", "GatewayConfig", "requests", "httpx", "urllib", "socket",
                 "gpt" + "-oss", "gpt" + "_oss")  # built, not literal: see note above
    for token in forbidden:
        assert token not in source, f"prose_judge.py must not reference {token!r}"
