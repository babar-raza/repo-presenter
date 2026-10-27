"""Stage S10 inside ``run_cascade``, offline (plan D7): when the model reviews, what it may reject,
how a rejection is repaired, and where the repair stops.

Each test drives the real cascade over the fixture ``tests/test_cascade.py`` defines through a
scripted client. That fixture's own deterministic verdict is REJECT (heading losses in deterministic
sections), so the two deterministic gates are replaced with a clean pass where a test needs the
model to be asked at all; the tests that hold the gates in place use the real ones and prove the
model is then never asked. The S10 job itself, the repair and the ledger are the real ones.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.cascade import run_cascade
from repo_presenter.core.facts import write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.ledger import load_records
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.repair.targeted import (
    REPAIRS_FILENAME,
    RepairLedger,
    defect_fingerprint,
)
from repo_presenter.readme.review.defect_bridge import RULESET_VERSION
from repo_presenter.readme.review.independent_reviewer import (
    ReviewVerdict,
    load_review_verdict,
)
from repo_presenter.readme.review.llm_review import blocked_predicate
from repo_presenter.readme.review.verdict import ReviewUnavailable
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.repair.test_loop import (
    QUOTE,
    REPAIRED_TEXT,
    _coherence_echo,
    _opening_repair_reply,
    _registry,
)
from tests.test_cascade import CONFIG, README, _completion, _scripted_replies

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "prompts"
REPAIRER = load_manifests(PROMPTS_PATH)["targeted_repair"].sha256


@pytest.fixture(autouse=True)
def _fixed_git_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cascade_module,
        "run_git",
        lambda *a, **k: SimpleNamespace(stdout="f" * 40 + "\n"),
    )


@pytest.fixture
def clean_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    """No deterministic rule and no blocking check rejects: the precondition of S10 (plan D7)."""
    monkeypatch.setattr(
        cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(())
    )
    monkeypatch.setattr(cascade_module, "blocking_failures", lambda validation: [])


class Replies:
    """The scripted provider: every reply, in call order, with the model that served it."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *replies: Any) -> None:
        self.replies = list(replies)
        self.payloads: list[dict[str, Any]] = []

        def create(**payload: Any) -> Any:
            self.payloads.append(payload)
            return self.replies.pop(0)

        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        monkeypatch.setattr(
            jobs_module.transport, "build_client", lambda config: client
        )

    @property
    def reviewer_calls(self) -> int:
        return sum(1 for payload in self.payloads if payload["model"] == "gpt-oss")


def authored() -> list[Any]:
    """The nine authoring-side replies of tests/test_cascade.py's fixture."""
    return _scripted_replies()


def review_reply(verdict: str = "ACCEPT", *findings: dict[str, Any]) -> Any:
    return _completion(
        {"verdict": verdict, "findings": list(findings), "preserve": []},
        model="gpt-oss",
    )


def opening_finding(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "F01",
        "section_id": "opening",
        "causal_stage": "S6",
        "criterion": "specificity",
        "claim_kind": "quality",
        "text": "the opening is generic prose",
        "quote": QUOTE,
        "fact_ids": [],
        "repair": "say what the library does",
    }
    base.update(overrides)
    return base


class Run:
    def __init__(self, tmp_path: Path) -> None:
        plugin_for("python")
        self.entry = make_entry()
        self.clone = tmp_path / "clone"
        self.clone.mkdir()
        (self.clone / "README.md").write_text(README, encoding="utf-8", newline="\n")
        self.facts_path = tmp_path / "facts.json"
        write_facts(make_facts(), self.facts_path)
        self.registry = _registry(tmp_path)
        self.out = tmp_path / "out"

    def cascade(self, **kwargs: Any) -> Any:
        return run_cascade(
            self.entry.repository,
            "python",
            self.clone,
            facts_path=self.facts_path,
            out_dir=self.out,
            config=CONFIG,
            registry_path=self.registry,
            max_rounds=1,
            **kwargs,
        )

    def verdict_file(self) -> ReviewVerdict:
        return load_review_verdict(self.out / "review_verdict.json")

    def fingerprint(self, section: str, criterion: str, stage: str = "S6") -> str:
        return defect_fingerprint(
            "review", section, stage, criterion, f"{RULESET_VERSION}|{REPAIRER}"
        )


@pytest.fixture
def run(tmp_path: Path) -> Run:
    return Run(tmp_path)


# ---------------------------------------------------------------------------
# When the model is asked
# ---------------------------------------------------------------------------


def test_the_model_reviews_a_clean_candidate_once_on_the_one_ledger(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(monkeypatch, *authored(), review_reply())
    result = run.cascade()

    assert provider.replies == []
    assert result.provider_calls == 10 and provider.reviewer_calls == 1
    verdict = result.review_verdict
    assert verdict.verdict == "ACCEPT" and verdict.model_reviewed
    assert verdict.prompt_version == "15" and verdict.model_served == "gpt-oss"
    assert run.verdict_file() == verdict
    records = load_records(run.out / "llm_cache" / "ledger.jsonl")
    assert {record.invocation_id for record in records} == {
        result.invocation.invocation_id
    }
    assert [r.job for r in records if r.stage == "S10"] == ["independent_review"]
    assert (
        records[-1].job == "independent_review"
        and records[-1].effective_model == "gpt-oss"
    )


def test_a_deterministic_rejection_is_never_sent_to_the_model(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = Replies(monkeypatch, *authored())
    result = run.cascade()  # the fixture's real deterministic verdict is REJECT
    assert result.review_verdict.verdict == "REJECT"
    assert not result.review_verdict.model_reviewed
    assert (
        result.provider_calls == 9
        and provider.reviewer_calls == 0
        and provider.replies == []
    )
    assert not run.verdict_file().model_reviewed


def test_a_failing_blocking_check_is_never_sent_to_the_model(
    run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(())
    )
    provider = Replies(monkeypatch, *authored())
    result = run.cascade()  # the fixture's real validation fails BC-02/03/06
    assert result.validation["summary"]["fail"] > 0
    assert not result.review_verdict.model_reviewed
    assert result.provider_calls == 9 and provider.reviewer_calls == 0


def test_an_unavailable_review_raises_and_leaves_only_an_unsealable_verdict(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    broken = _completion(
        {"verdict": "ACCEPT", "findings": [opening_finding()], "preserve": []},
        "gpt-oss",
    )
    provider = Replies(monkeypatch, *authored(), broken, broken)
    with pytest.raises(ReviewUnavailable) as raised:
        run.cascade()
    assert raised.value.retryable
    assert provider.reviewer_calls == 2  # the review and its one re-ask, nothing more
    assert not run.verdict_file().model_reviewed  # the deterministic file cannot seal


# ---------------------------------------------------------------------------
# Repair routing and its bound
# ---------------------------------------------------------------------------


def repaired_pass(fingerprint: str, text: str, before: str = QUOTE) -> list[Any]:
    """The repair call for the opening and the coherence pass the repaired unit makes necessary."""
    return [
        _completion(_opening_repair_reply(fingerprint, before, text)),
        _completion(_coherence_echo(text)),
    ]


def test_a_blocking_finding_is_repaired_by_its_causal_stage_then_re_reviewed(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    fingerprint = run.fingerprint("opening", "specificity")
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(fingerprint, REPAIRED_TEXT),
        review_reply(),
    )
    result = run.cascade()

    assert provider.replies == []
    # nine authored calls, review, one repair, the re-asked coherence pass, the re-review
    assert result.provider_calls == 13 and provider.reviewer_calls == 2
    assert (
        result.review_verdict.verdict == "ACCEPT"
        and result.review_verdict.model_reviewed
    )
    assert result.rounds == 2
    ledger = RepairLedger(run.out / REPAIRS_FILENAME)
    assert ledger.attempts[fingerprint]["outcome"] == "repaired"
    assert ledger.attempts[fingerprint]["stage"] == "S6"
    assert REPAIRED_TEXT in (run.out / "README.coherent.md").read_text(encoding="utf-8")
    # the repair was handed the reviewer's own claim, not just a quote
    repair_payload = next(
        p
        for p in provider.payloads
        if p["response_format"]["json_schema"]["name"] == "targeted_repair"
    )
    assert "say what the library does" in repair_payload["messages"][1]["content"]
    assert '"claim_kind": "quality"' in repair_payload["messages"][1]["content"]


def test_a_finding_that_returns_after_its_repair_is_not_retried_and_the_candidate_is_blocked(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    fingerprint = run.fingerprint("opening", "specificity")
    again = opening_finding(quote=REPAIRED_TEXT)
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(fingerprint, REPAIRED_TEXT),
        review_reply("REJECT_PRESENTATION", again),
    )
    result = run.cascade()

    assert (
        provider.replies == []
    )  # one fingerprint, one attempt: no third repair is asked
    assert result.provider_calls == 13
    verdict = result.review_verdict
    assert verdict.verdict == "REJECT" and verdict.model_reviewed
    assert run.verdict_file() == verdict
    assert RepairLedger(run.out / REPAIRS_FILENAME).attempts[fingerprint][
        "re_raised"
    ] == ["F01"]
    assert "F01 [quality] in opening" in blocked_predicate(verdict)


def test_repair_rounds_stop_at_the_bound_and_the_candidate_is_blocked(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    first = run.fingerprint("opening", "specificity")
    other = opening_finding(id="F01", criterion="coherence", quote=REPAIRED_TEXT)
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(first, REPAIRED_TEXT),
        review_reply(
            "REJECT_COHERENCE", other
        ),  # a different defect, but the bound is 1
    )
    result = run.cascade(review_repair_rounds=1)

    assert provider.replies == []
    assert result.provider_calls == 13 and provider.reviewer_calls == 2
    assert result.review_verdict.verdict == "REJECT"
    assert [f.criterion for f in result.review_verdict.blocking_findings] == [
        "coherence"
    ]


def test_two_repair_rounds_then_blocked_with_the_exact_predicate(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    first = run.fingerprint("opening", "specificity")
    second = run.fingerprint("opening", "coherence")
    second_text = "This lets a reader turn its output into a finished file in one step."
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(first, REPAIRED_TEXT),
        review_reply(
            "REJECT_COHERENCE",
            opening_finding(criterion="coherence", quote=REPAIRED_TEXT),
        ),
        *repaired_pass(second, second_text, before=REPAIRED_TEXT),
        review_reply(
            "REJECT_COHERENCE",
            opening_finding(
                criterion="links", quote=second_text, text="a third complaint"
            ),
        ),
    )
    result = run.cascade()

    assert (
        provider.replies == []
    )  # the third rejection is not repaired: the bound is two rounds
    # nine authored calls + 3 reviews + 2 repairs + 2 re-asked coherence passes
    assert result.provider_calls == 16 and provider.reviewer_calls == 3
    verdict = result.review_verdict
    assert verdict.verdict == "REJECT" and verdict.model_reviewed
    assert second_text in (run.out / "README.coherent.md").read_text(encoding="utf-8")
    assert "F01 [quality] in opening blocks until" in blocked_predicate(verdict)
    assert result.rounds == 3


def test_a_finding_no_stage_can_revise_is_recorded_unrepairable_and_blocks(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply(
            "REJECT_PRESENTATION",
            opening_finding(section_id="structure", causal_stage="unclear", quote=""),
        ),
    )
    result = run.cascade()

    assert provider.replies == []
    assert (
        result.provider_calls == 10
    )  # no repair was attempted, so no re-review either
    assert result.review_verdict.verdict == "REJECT"
    attempts = RepairLedger(run.out / REPAIRS_FILENAME).attempts
    assert [entry["outcome"] for entry in attempts.values()] == ["unrepairable"]
