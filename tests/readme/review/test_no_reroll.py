"""The no-re-roll invariant (project/state.yaml INDEPENDENT_LLM_REVIEWER.invariant_added_2026_10_27):
a blocking verdict on a given request is never overturned by a fresh, cache-bypassed review of the
same bytes. Replay from the call store is the only second look. Measured stability of a fresh review
is low, so resampling until ACCEPT would be the quiet demotion the mission forbids."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from repo_presenter.core.llm.jobs import CallStore
from repo_presenter.readme.review import llm_review
from repo_presenter.readme.review.llm_review import (
    BLOCKED_FILENAME,
    RerollRefused,
    review_with_model,
)
from tests.readme.review.test_llm_review import (
    CANDIDATE,
    PROMPTS,
    Harness,
    completion,
    finding,
    install,
    reply,
)

SRC = Path(__file__).resolve().parents[3] / "src" / "repo_presenter"
BLOCKING = reply("REJECT_PRESENTATION", finding("quality"))


def blocked_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Harness:
    harness = Harness(tmp_path)
    install(monkeypatch, [completion(BLOCKING)])
    assert harness.review().verdict == "REJECT"
    return harness


def lose_the_cache(harness: Harness) -> None:
    for path in harness.store.directory.glob("*.json"):
        if path.name != BLOCKED_FILENAME:
            path.unlink()


def test_replay_of_a_blocking_verdict_is_allowed_and_makes_no_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = blocked_harness(tmp_path, monkeypatch)
    client = install(monkeypatch, [])
    assert harness.review(invocation="inv-2").verdict == "REJECT"
    assert client.payloads == []


def test_a_fresh_review_of_the_same_request_after_a_blocking_verdict_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = blocked_harness(tmp_path, monkeypatch)
    lose_the_cache(harness)
    client = install(
        monkeypatch, [completion(reply())]
    )  # an ACCEPT is waiting to be rolled
    with pytest.raises(RerollRefused) as raised:
        harness.review(invocation="inv-2")
    assert client.payloads == [] and "blocking verdict" in str(raised.value)


def test_the_record_names_the_request_and_the_candidate_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = blocked_harness(tmp_path, monkeypatch)
    (record,) = json.loads(
        (harness.store.directory / BLOCKED_FILENAME).read_text(encoding="utf-8")
    )["requests"].values()
    assert record["verdict"] == "REJECT" and record["blocking"] == ["F01"]
    assert len(record["candidate_sha256"]) == 64


def test_an_accept_leaves_no_block_so_a_lost_cache_may_be_asked_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = Harness(tmp_path)
    install(monkeypatch, [completion(reply())])
    assert harness.review().verdict == "ACCEPT"
    lose_the_cache(harness)
    install(monkeypatch, [completion(reply())])
    assert harness.review(invocation="inv-2").verdict == "ACCEPT"


def test_changed_candidate_bytes_are_a_new_request_and_may_be_reviewed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = blocked_harness(tmp_path, monkeypatch)
    harness.candidate = CANDIDATE.replace("MIT.", "MIT licence.")
    install(monkeypatch, [completion(reply())])
    assert harness.review(invocation="inv-2").verdict == "ACCEPT"


def test_a_review_that_was_unavailable_is_not_a_blocking_verdict_and_may_be_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repo_presenter.readme.review.verdict import ReviewUnavailable

    harness = Harness(tmp_path)
    bad = completion("not json at all")
    install(monkeypatch, [bad, bad])
    with pytest.raises(ReviewUnavailable):
        harness.review()
    install(monkeypatch, [completion(reply())])
    assert harness.review(invocation="inv-2").verdict == "ACCEPT"


def test_a_different_logic_version_is_a_different_reviewer_and_ignores_the_old_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = blocked_harness(tmp_path, monkeypatch)
    lose_the_cache(harness)
    path = harness.store.directory / BLOCKED_FILENAME
    document = json.loads(path.read_text(encoding="utf-8"))
    document["reviewer_logic_version"] = "an older version"
    path.write_text(json.dumps(document), encoding="utf-8")
    install(monkeypatch, [completion(reply())])
    assert harness.review(invocation="inv-2").verdict == "ACCEPT"


# --- structural: the API has no way to ask for a cache bypass ---------------------------------


def test_the_review_api_has_no_cache_bypass_parameter() -> None:
    names = set(inspect.signature(review_with_model).parameters)
    for forbidden in (
        "fresh",
        "force",
        "bypass",
        "refresh",
        "no_cache",
        "skip_cache",
        "reroll",
    ):
        assert not any(forbidden in name for name in names), names


def test_only_the_cascade_and_the_calibration_adapter_call_the_review() -> None:
    callers = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "review_with_model"
            ):
                callers.add(str(path.relative_to(SRC)).replace("\\", "/"))
    assert callers == {"cascade.py", "readme/review/calibration/reviewers.py"}


def test_a_fresh_store_per_review_exists_only_in_the_calibration_adapter() -> None:
    """The one place a review may start from an empty store is the calibration adapter, which
    re-asks corpus cases (not production candidates) to MEASURE stability."""
    holders = {
        str(path.relative_to(SRC)).replace("\\", "/")
        for path in sorted(SRC.rglob("*.py"))
        if "fresh_store_per_call" in path.read_text(encoding="utf-8")
    }
    assert holders == {"readme/review/calibration/reviewers.py"}


def test_the_guard_is_wired_before_the_provider_is_reachable() -> None:
    source = inspect.getsource(llm_review.review_with_model)
    assert source.index("_refuse_reroll") < source.index("run_job(")
    assert isinstance(CallStore, type)
    assert PROMPTS  # the real manifests are the ones guarded
