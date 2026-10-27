"""The hosted ``present`` gate on the independent model review (plan D4, D7): a verdict no model
produced never seals, a rejected candidate names what would unblock it, and an unobtainable
review is recorded as a transient failure. The cascade and the seal are replaced by spies; the
durable transaction is the real one against a disposable local remote."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import init_git_repository

from repo_presenter import present
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.present import PresentFailure, run_present
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import ReviewUnavailable, ReviewVerdict
from tests.test_present import REPO, _entry

MODEL_ACCEPT = ReviewVerdict.folded(
    (),
    model_verdict="ACCEPT",
    prompt_version="15",
    model_served="gpt-oss",
    request_sha256="a" * 64,
    reply_sha256="b" * 64,
)
DETERMINISTIC_ACCEPT = ReviewVerdict.folded(())
MODEL_REJECT = ReviewVerdict.folded(
    (
        Finding(
            rule="llm:specificity",
            source="llm",
            message="generic",
            claim_kind="quality",
            finding_id="F01",
            section_id="opening",
            causal_stage="S6",
            criterion="specificity",
        ),
    ),
    model_verdict="REJECT_PRESENTATION",
    prompt_version="15",
    model_served="gpt-oss",
    request_sha256="a" * 64,
    reply_sha256="b" * 64,
)
FAILING = {"checks": [{"id": "BC-02", "verdict": "FAIL", "details": ["no evidence"]}]}
PASSING = {"checks": [{"id": "BC-02", "verdict": "PASS", "details": []}]}


class Spy:
    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, verdict: ReviewVerdict, validation: Any
    ) -> None:
        self.sealed: list[Any] = []
        result = SimpleNamespace(
            review_verdict=verdict,
            validation=validation,
            entry=None,
            source_revision="r",
            document=None,
            out_dir=Path("."),
            facts_path=Path("facts.json"),
            provider_calls=1,
            invocation=None,
        )
        monkeypatch.setattr(present, "run_cascade", lambda *a, **k: result)
        monkeypatch.setattr(present, "load_manifests", lambda path: None)
        monkeypatch.setattr(
            present, "seal_candidate", lambda inputs: self.sealed.append(inputs)
        )

    def run(self, tmp_path: Path) -> None:
        present._cascade_and_seal(
            repository=REPO,
            ecosystem="python",
            clone_path=tmp_path,
            facts_path=tmp_path / "facts.json",
            workdir=tmp_path,
            candidates_root=tmp_path,
            config=None,  # type: ignore[arg-type]
            prompts_path=tmp_path,
            registry_path=tmp_path,
        )


def test_a_model_reviewed_accept_seals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spy = Spy(monkeypatch, MODEL_ACCEPT, PASSING)
    spy.run(tmp_path)
    assert len(spy.sealed) == 1


def test_a_deterministic_only_accept_can_never_seal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spy = Spy(monkeypatch, DETERMINISTIC_ACCEPT, FAILING)
    with pytest.raises(PresentFailure) as raised:
        spy.run(tmp_path)
    assert spy.sealed == []
    assert "no independent model review" in str(raised.value)
    assert "BC-02" in str(
        raised.value
    )  # the check that kept the model from being asked


def test_a_rejected_candidate_names_the_exact_predicate_that_would_unblock_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spy = Spy(monkeypatch, MODEL_REJECT, PASSING)
    with pytest.raises(PresentFailure) as raised:
        spy.run(tmp_path)
    assert spy.sealed == []
    assert "F01 [quality] in opening blocks until" in str(raised.value)


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "state-remote")


def test_an_unavailable_review_is_a_recorded_transient_failure_and_seals_nothing(
    remote: Path, tmp_path: Path
) -> None:
    entry = _entry()

    def pipeline() -> None:
        raise ReviewUnavailable(
            "the reviewer's reply broke the contract after the one re-ask",
            ["finding F01: quote is not the candidate's text, character for character"],
        )

    with GitStateBackend(remote=str(remote)) as backend:
        exit_code = run_present(
            backend=backend,
            entry=entry,
            candidates_root=tmp_path / "work",
            holder_id="present:run-r1",
            workflow_run_id="run-r1",
            pipeline=pipeline,
        )
        record = backend.load(REPO)

    assert exit_code == 1
    assert (
        record is not None
        and record.state == "FAILED_INTERNAL"
        and record.lease is None
    )
    assert record.failure is not None
    assert record.failure.classification == "transient"
    assert (
        "retryable" in record.failure.detail
        and "nothing was sealed" in record.failure.detail
    )
    assert "quote is not" in record.failure.detail
    assert not (tmp_path / "work").exists()
