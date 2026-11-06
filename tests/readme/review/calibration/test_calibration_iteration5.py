"""Iteration 5 tooling: the zero-call estimate, the resumable journal, pre-registration, the Lane L
bundle loader and unscored seen twins. Every test drives a scripted client; nothing is sent."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from repo_presenter.core.facts import FactsDocument, write_facts
from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.estimate import (
    case_requests,
    estimate_run,
)
from repo_presenter.readme.review.calibration.harness import (
    UNAVAILABLE,
    run_corpus,
)
from repo_presenter.readme.review.calibration.record import merge_repeats
from repo_presenter.readme.review.calibration.registration import (
    RegistrationMismatch,
    registered_cases,
    registration_document,
)
from repo_presenter.readme.review.calibration.reviewers import (
    LiveReviewer,
    ReviewJournal,
    physical_calls,
)
from repo_presenter.readme.review.calibration.sources import (
    load_lane_l_bundle_candidate,
)
from tests.readme.review.calibration.synthetic import FACTS, make_source
from tests.readme.review.calibration.test_calibration_live import (
    ACCEPT_REPLY,
    CONFIG,
    PROMPTS,
    completion,
    install,
)


def corpus(tmp_path: Path):
    return build_corpus([Base(make_source(tmp_path))])


def live(tmp_path: Path, *, cap: int = 100, fresh: bool = False, store: str = "t", journal=True):
    return LiveReviewer(
        prompts=PROMPTS,
        config=CONFIG,
        ledger_path=tmp_path / "ledger.jsonl",
        store_dir=tmp_path / "calls" / store,
        cap=cap,
        fresh_store_per_call=fresh,
        journal=ReviewJournal(tmp_path / "journal.jsonl") if journal else None,
    )


def test_the_estimate_counts_exactly_the_requests_a_live_run_sends(tmp_path, monkeypatch):
    cases = corpus(tmp_path)
    stability = cases[:2]
    estimate = estimate_run(
        cases,
        stability,
        PROMPTS,
        store_dir=tmp_path / "calls" / "t",
        stability_dir=tmp_path / "calls" / "t-stability",
    )
    client = install(monkeypatch, [completion(ACCEPT_REPLY)] * 200)
    run = run_corpus(cases, live(tmp_path))
    first_pass = client.requests
    merge_repeats(run, run_corpus(stability, live(tmp_path, fresh=True, store="t-stability"), repeats=3))
    # every reply is valid, so every request is one call: the estimate is exact, not a bound
    assert estimate.first_pass_new == first_pass
    assert estimate.stability_new == client.requests - first_pass
    assert estimate.requests == client.requests == physical_calls(tmp_path / "ledger.jsonl")
    assert estimate.first_pass_units > estimate.first_pass_new  # mutants replay unchanged units
    assert estimate.expected_calls >= estimate.requests and estimate.worst_case == 2 * estimate.requests


def test_after_a_complete_run_the_estimate_of_a_rerun_is_zero(tmp_path, monkeypatch):
    cases = corpus(tmp_path)
    install(monkeypatch, [completion(ACCEPT_REPLY)] * 200)
    run_corpus(cases, live(tmp_path))
    journal = ReviewJournal(tmp_path / "journal.jsonl")
    again = estimate_run(
        cases,
        [],
        PROMPTS,
        store_dir=tmp_path / "calls" / "t",
        stability_dir=tmp_path / "calls" / "t-stability",
        journaled=journal.keys(),
    )
    assert again.requests == 0 and again.first_pass_units > 0


def test_the_estimate_uses_the_live_reviews_own_request_hashes(tmp_path, monkeypatch):
    clean = corpus(tmp_path)[0]
    install(monkeypatch, [completion(ACCEPT_REPLY)] * 5)
    live(tmp_path)(clean)
    stored = {p.name[:12] for p in (tmp_path / "calls" / "t").glob("*.json") if "." not in p.stem}
    assert {h[:12] for h in case_requests(clean, PROMPTS)} == stored


def test_an_interrupted_run_resumes_without_spending_a_call_twice(tmp_path, monkeypatch):
    cases = corpus(tmp_path)
    uninterrupted = tmp_path / "whole"
    uninterrupted.mkdir()
    client = install(monkeypatch, [completion(ACCEPT_REPLY)] * 200)
    run_corpus(cases, live(uninterrupted))
    needed = client.requests

    client = install(monkeypatch, [completion(ACCEPT_REPLY)] * 200)
    stopped = run_corpus(cases, live(tmp_path, cap=2))
    assert stopped.stopped and physical_calls(tmp_path / "ledger.jsonl") == 2
    resumed = run_corpus(cases, live(tmp_path, cap=100))
    assert not resumed.stopped and len(resumed.results) == len(cases)
    assert physical_calls(tmp_path / "ledger.jsonl") == needed == client.requests


def test_a_resumed_review_that_was_unavailable_is_not_asked_again(tmp_path, monkeypatch):
    clean = corpus(tmp_path)[0]
    client = install(monkeypatch, [completion(""), completion("")] * 10)
    first = live(tmp_path)(clean)
    spent = client.requests
    assert first.verdict == UNAVAILABLE and spent >= 2
    # without the journal the unit is re-asked (its reply was never stored) ...
    live(tmp_path, journal=False)(clean)
    assert client.requests > spent
    # ... with it, the recorded outcome comes back, first-reply flags and calls included
    spent = client.requests
    again = live(tmp_path)(clean)
    assert client.requests == spent
    assert again == first and again.first_reply_json_valid is False and again.calls == first.calls


def test_a_journaled_repeat_is_keyed_by_its_fresh_store(tmp_path, monkeypatch):
    clean = corpus(tmp_path)[0]
    client = install(monkeypatch, [completion(ACCEPT_REPLY)] * 20)
    run_corpus([clean], live(tmp_path, fresh=True, store="s"), repeats=3)
    spent = client.requests
    assert spent == 3 * len(case_requests(clean, PROMPTS))
    rerun = run_corpus([clean], live(tmp_path, fresh=True, store="s"), repeats=3)
    assert client.requests == spent and len(rerun.results[0].outcomes) == 3
    # a fourth repeat is a new review and is asked
    run_corpus([clean], live(tmp_path, fresh=True, store="s"), repeats=4)
    assert client.requests > spent


def test_a_registration_round_trips_and_refuses_a_changed_corpus(tmp_path):
    cases = corpus(tmp_path)
    document = json.loads(json.dumps(registration_document(cases, cases[:2], corpus_size=len(cases))))
    selected, stability = registered_cases(document, cases)
    assert [c.case_id for c in selected] == [c.case_id for c in cases]
    assert [c.case_id for c in stability] == [c.case_id for c in cases[:2]]
    changed = [replace(cases[0], source=replace(cases[0].source, readme=cases[0].readme + "x\n")), *cases[1:]]
    with pytest.raises(RegistrationMismatch, match="readme_sha256"):
        registered_cases(document, changed)
    relabelled = [replace(cases[1], expected="ACCEPT") if i == 1 else c for i, c in enumerate(cases)]
    with pytest.raises(RegistrationMismatch, match="expected"):
        registered_cases(document, relabelled)
    with pytest.raises(RegistrationMismatch, match="not in the built corpus"):
        registered_cases(document, cases[:-1])
    with pytest.raises(ValueError, match="stability"):
        registration_document(cases[:1], cases[1:2], corpus_size=len(cases))


def test_an_unscored_reason_keeps_the_twin_asked_but_out_of_the_false_reject_gate(tmp_path):
    cases = build_corpus([Base(make_source(tmp_path), unscored_reason="asked in iteration 4")])
    twin = cases[0]
    assert twin.role == "unscored_twin" and "iteration 4" in twin.note
    assert all(c.role in {"mutant", "real_defect"} for c in cases[1:])


def lane_l_bundle(tmp_path: Path, revision: str = "c" * 40) -> Path:
    directory = tmp_path / "lane-l" / revision
    facts = FactsDocument("aspose-email-foss/Aspose.Email-FOSS-for-.Net", revision, FACTS.facts)
    write_facts(facts, directory / "facts.json")
    (directory / "README.md").write_text("# Corrected\n\nText.\n", encoding="utf-8")
    (directory / "README.original.md").write_text("# Live\n\nText.\n", encoding="utf-8")
    return directory


def test_a_lane_l_bundle_is_its_sealed_readme_against_its_own_original_and_facts(tmp_path):
    source = load_lane_l_bundle_candidate(lane_l_bundle(tmp_path), name="lanel:x")
    assert source.rendered is False and source.readme.startswith("# Corrected")
    assert source.original.startswith("# Live") and source.ecosystem == "net"
    assert source.validation == {"summary": {}, "checks": []}


def test_a_lane_l_bundle_whose_facts_are_for_another_revision_is_refused(tmp_path):
    directory = lane_l_bundle(tmp_path)
    moved = directory.parent / ("d" * 40)
    directory.rename(moved)
    with pytest.raises(ValueError, match="facts are for"):
        load_lane_l_bundle_candidate(moved, name="lanel:x")
