"""P5 durable caching, wired (TC-008a): both lanes skip the provider call when every consumed
scope equals a verified, PROVEN sealed bundle, and fail closed otherwise.

Every scenario counts provider requests at the real provider-call boundary
(``core.llm.jobs.transport.build_client``'s client), never by reading a log or a print.

Lane L is driven end to end through the real CLI (``present.main``) against the real git-ref
durable-state backend, with the real correction engine, reviewer, seal and bundle verification;
only the provider is faked. Lane R is driven through the real ``present._cascade_and_seal`` entry
with a real sealed Lane R bundle (``seal_candidate`` twice, the second a fresh zero-call process,
exactly the proof flow) and the real ``cascade.preflight_cascade``; ``run_cascade`` itself (nine
scripted model stages, covered by ``tests/test_cascade.py``) is replaced by a stub that makes ONE
request through the same fake provider boundary and then stops, so that "the pipeline ran" is a
measured request count rather than an assumption.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import commit_all, head_revision, init_git_repository

from repo_presenter import cascade, present
from repo_presenter.core.candidates import LANE_R, verify_bundle
from repo_presenter.core.facts import FactsDocument, read_facts, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.core.preflight import preflight_decision
from repo_presenter.readme.bundle import seal as seal_module
from repo_presenter.readme.bundle.seal import SealInputs, seal_candidate
from tests.readme.bundle.test_seal import (
    _append_cache_reuse_record,
    _fresh_invocation,
    _out_dir,
)
from tests.readme.composition.synthetic import make_entry
from tests.test_lane_l_hosted import (
    CLEAN_README,
    PROMPTS,
    Hosted,
    Provider,
    accept_reply,
    digest_tree,
    fresh_invocation,
    restore_state,
)


def _record(lane: str, scenario: str, requests: int) -> None:
    """When P5_PROOF_OUT is set, append the measured provider-request count for this scenario
    (the supervisor's call_count_proof generator reads these; unset, this is a no-op)."""
    import json
    import os

    out = os.environ.get("P5_PROOF_OUT")
    if out:
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"lane": lane, "scenario": scenario, "requests": requests}) + chr(10))


# --- Lane L: six named scenarios through the real CLI ---------------------------------------------


def _proven_lane_l(hosted: Hosted, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Run 1 seals (ACCEPTED); run 2, a fresh process with the call store restored, proves the
    no-op (READY_FOR_PROPOSAL). Returns the proven bundle's byte digests."""
    first = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("run1", hosted.facts("run1")) == 0
    assert first.calls >= 1
    monkeypatch.setattr(Invocation, "begin", staticmethod(lambda: fresh_invocation(2)))
    restore_state(hosted, "run1", "run2")
    replay = Provider(monkeypatch)
    assert hosted.lane_l("run2", hosted.facts("run2")) == 0
    assert replay.calls == 0
    assert hosted.manifest()["state"] == "READY_FOR_PROPOSAL"
    return digest_tree(hosted.bundle())


def _skipped(capsys: pytest.CaptureFixture[str]) -> bool:
    out = capsys.readouterr().out
    assert "preflight (Lane L):" in out
    return "preflight (Lane L): skip=True" in out


def test_lane_l_warm_unchanged_rerun_makes_exactly_zero_provider_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hosted = Hosted(tmp_path, monkeypatch)
    proven = _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()

    provider = Provider(monkeypatch)  # any request raises
    assert hosted.lane_l("run3", hosted.facts("run3")) == 0

    assert provider.calls == 0
    _record('L','warm_unchanged_rerun',provider.calls)
    assert _skipped(capsys)
    assert digest_tree(hosted.bundle()) == proven  # the proven bundle is left exactly as sealed
    record = hosted.record("L")
    assert record is not None and record.state == "READY_FOR_PROPOSAL"


def test_lane_l_cold_runner_with_only_the_restored_bundle_makes_zero_provider_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fresh hosted runner: new working directory, no call store at all, only the bundle that
    ``bundle_store`` restores into a new candidates root."""
    hosted = Hosted(tmp_path, monkeypatch)
    proven = _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()
    restored = tmp_path / "restored-candidates"
    shutil.copytree(hosted.candidates, restored)
    shutil.rmtree(hosted.candidates)
    hosted.candidates = restored
    for old in tmp_path.glob("work-*"):
        shutil.rmtree(old)

    provider = Provider(monkeypatch)
    assert hosted.lane_l("cold", hosted.facts("cold")) == 0

    assert provider.calls == 0
    _record('L','cold_runner',provider.calls)
    assert _skipped(capsys)
    assert digest_tree(hosted.bundle()) == proven


def test_lane_l_evicted_actions_cache_makes_zero_provider_requests_while_a_bundle_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The Actions cache holding the call stores is gone; the sealed bundle is not. Before this
    card the rerun asked the model again (test_without_the_restored_call_store_...)."""
    hosted = Hosted(tmp_path, monkeypatch)
    proven = _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()
    for store in tmp_path.glob("work-*/lane-l/llm_cache"):
        shutil.rmtree(store)
    assert not list(tmp_path.glob("work-*/lane-l/llm_cache"))

    provider = Provider(monkeypatch)
    assert hosted.lane_l("evicted", hosted.facts("evicted")) == 0

    assert provider.calls == 0
    _record('L','evicted_cache',provider.calls)
    assert _skipped(capsys)
    assert digest_tree(hosted.bundle()) == proven


def test_lane_l_changed_input_re_executes_the_targeted_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two changed consumed inputs, measured separately. (a) The review prompt is a MECHANISM
    version: owner rule 2026-11-06, a version bump never regenerates a seal -- the sealed
    candidate is re-certified under current code with zero provider requests. (b) The live
    README (a new revision) is an INPUT: the correction and the review rerun."""
    hosted = Hosted(tmp_path, monkeypatch)
    _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()

    # (a) the review prompt changes: re-certified, not regenerated; zero requests.
    prompts = tmp_path / "prompts-edited"
    shutil.copytree(PROMPTS, prompts)
    review = prompts / "independent_review.yaml"
    review.write_bytes(review.read_bytes() + b"\n# edited\n")
    provider = Provider(monkeypatch)  # any request raises
    argv = hosted.args("cascade", "prompt", "--state-remote", str(hosted.remote), lane="L")
    argv[argv.index("--prompts") + 1] = str(prompts)
    hosted.facts("prompt")
    assert present.main(argv) == 0
    out = capsys.readouterr().out
    assert "preflight (Lane L): skip=False" in out and "recertify (Lane L): RECERTIFIED" in out
    assert provider.calls == 0, provider.calls
    assert hosted.manifest()["recertified_from"]["state"] == "READY_FOR_PROPOSAL"

    # (b) the README changes upstream (a new revision): the correction and review rerun.
    (hosted.upstream / "README.md").write_bytes(CLEAN_README.encode() + b"\nMore text.\n")
    commit_all(hosted.upstream, "readme change")
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("readme", hosted.facts("readme")) == 0
    assert not _skipped(capsys)
    assert provider.calls == EXPECTED_REVIEW_REQUESTS, provider.calls
    assert hosted.manifest()["revision"] == head_revision(hosted.upstream)


#: The independent review of one Lane L candidate is a single provider request when the model
#: ACCEPTs at once (measured, not assumed: both reruns above must make exactly this many).
EXPECTED_REVIEW_REQUESTS = 1


def test_lane_l_unrelated_input_change_is_a_no_op_with_zero_provider_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Consumed-scope invalidation: a prompt Lane L never ran (Lane R's investigation prompt)
    changes; Lane L's sealed record does not name it, so nothing reopens."""
    hosted = Hosted(tmp_path, monkeypatch)
    proven = _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()
    prompts = tmp_path / "prompts-unrelated"
    shutil.copytree(PROMPTS, prompts)
    unrelated = prompts / "repository_investigation.yaml"
    unrelated.write_bytes(unrelated.read_bytes() + b"\n# a Lane R only prompt changed\n")

    provider = Provider(monkeypatch)
    argv = hosted.args("cascade", "unrel", "--state-remote", str(hosted.remote), lane="L")
    argv[argv.index("--prompts") + 1] = str(prompts)
    hosted.facts("unrel")
    assert present.main(argv) == 0

    assert provider.calls == 0
    assert _skipped(capsys)
    assert digest_tree(hosted.bundle()) == proven


def test_lane_l_corrupt_evidence_fails_closed_and_the_provider_is_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hosted = Hosted(tmp_path, monkeypatch)
    _proven_lane_l(hosted, monkeypatch)
    capsys.readouterr()
    readme = hosted.bundle() / "README.md"
    readme.write_bytes(readme.read_bytes() + b"tampered\n")

    provider = Provider(monkeypatch, default=accept_reply())
    hosted.lane_l("corrupt", hosted.facts("corrupt"))

    assert not _skipped(capsys)
    _record('L','corrupt_evidence',provider.calls)
    assert provider.calls == EXPECTED_REVIEW_REQUESTS, provider.calls  # never a skip


# --- Lane R: the real preflight and the real present entry ----------------------------------------


class CountingProvider:
    """The fake provider boundary for Lane R; every request is counted."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.requests = 0

        def create(**payload: Any) -> Any:
            self.requests += 1
            return accept_reply()

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    def ask(self) -> None:
        jobs_module.transport.build_client(None).chat.completions.create(model="m", messages=[])


class LaneRWorld:
    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.entry = make_entry()
        self.upstream = init_git_repository(root / "upstream")
        (self.upstream / "README.md").write_text("# Widget\n\nA widget.\n", encoding="utf-8")
        commit_all(self.upstream, "seed")
        self.candidates = root / "candidates-root"
        self.facts_path = root / "facts.json"
        self.provider = CountingProvider(monkeypatch)
        self.ran: list[int] = []

        def stub_run_cascade(*args: Any, **kwargs: Any) -> Any:
            self.ran.append(1)
            self.provider.ask()  # the one request the stub pipeline makes at the boundary
            raise present.PresentFailure("stub pipeline ran")

        monkeypatch.setattr(present, "run_cascade", stub_run_cascade)

    def write_facts(self) -> str:
        revision = head_revision(self.upstream)
        write_facts(FactsDocument(self.entry.repository, revision, ()), self.facts_path)
        return revision

    def merged_facts(self, revision: str) -> FactsDocument:
        return cascade._document_with_inherited_units(
            self.entry.repository, read_facts(self.facts_path), revision, self.upstream
        )

    def seal_first(self) -> tuple[SealInputs, Path]:
        revision = self.write_facts()
        invocation = Invocation.begin()
        out_dir = _out_dir(self.root, invocation.invocation_id)
        inputs = SealInputs(
            entry=self.entry, source_revision=revision, facts=self.merged_facts(revision),
            prompts=load_manifests(PROMPTS), out_dir=out_dir, facts_path=self.facts_path,
            candidates_root=self.candidates, provider_calls=1, invocation=invocation,
        )
        result = seal_candidate(inputs)
        assert result.state == "ACCEPTED"
        return inputs, result.bundle

    def seal_proven(self) -> Path:
        inputs, bundle = self.seal_first()
        fresh = _fresh_invocation()
        _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
        rerun = SealInputs(
            entry=inputs.entry, source_revision=inputs.source_revision, facts=inputs.facts,
            prompts=inputs.prompts, out_dir=inputs.out_dir, facts_path=inputs.facts_path,
            candidates_root=inputs.candidates_root, provider_calls=0, invocation=fresh,
        )
        assert seal_candidate(rerun).state == "READY_FOR_PROPOSAL"
        return bundle

    def run_stage(self, *, candidates: Path | None = None, prompts: Path | None = None) -> None:
        try:
            present._cascade_and_seal(
                repository=self.entry.repository, ecosystem="python",
                clone_path=self.upstream, facts_path=self.facts_path,
                workdir=self.root / "work", candidates_root=candidates or self.candidates,
                config=None, prompts_path=prompts or PROMPTS,
                registry_path=self.root / "unused-registry.json",
            )
        except present.PresentFailure as exc:
            assert "stub pipeline ran" in str(exc)

    def preflight(self) -> Any:
        return cascade.preflight_cascade(
            self.entry.repository, self.upstream, facts_path=self.facts_path,
            candidates_root=self.candidates, prompts_path=PROMPTS,
        )


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LaneRWorld:
    return LaneRWorld(tmp_path, monkeypatch)


def test_lane_r_warm_unchanged_rerun_makes_zero_requests(world: LaneRWorld) -> None:
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    world.run_stage()
    assert world.provider.requests == 0 and world.ran == []
    _record('R','warm_unchanged_rerun',world.provider.requests)
    assert digest_tree(bundle) == before


def test_lane_r_cold_runner_and_evicted_cache_make_zero_requests(
    world: LaneRWorld, tmp_path: Path
) -> None:
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    shutil.rmtree(world.root / "out" / "llm_cache")  # the evicted call store
    restored = tmp_path / "restored"
    shutil.copytree(world.candidates, restored)
    shutil.rmtree(world.candidates)
    world.run_stage(candidates=restored)  # a cold runner: only the restored bundle exists
    assert world.provider.requests == 0 and world.ran == []
    _record('R','cold_runner',world.provider.requests)
    _record('R','evicted_cache',world.provider.requests)
    assert digest_tree(restored / bundle.relative_to(world.candidates)) == before


def test_lane_r_changed_input_re_executes_exactly_once(world: LaneRWorld) -> None:
    world.seal_proven()
    (world.upstream / "README.md").write_text("# Widget\n\nChanged.\n", encoding="utf-8")
    commit_all(world.upstream, "change")
    world.write_facts()
    world.run_stage()
    assert world.ran == [1] and world.provider.requests == 1


def test_lane_r_changed_prompt_with_a_seal_that_cannot_recertify_re_executes_exactly_once(
    world: LaneRWorld, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A prompt change alone routes to re-certification (tests/test_recertify.py proves the
    zero-call path on a real candidate); this synthetic seal cannot be re-certified (its
    repository is in no registry), so -- and only so -- the generation pipeline runs once."""
    world.seal_proven()
    prompts = tmp_path / "prompts-edited"
    shutil.copytree(PROMPTS, prompts)
    target = prompts / "repository_investigation.yaml"
    target.write_bytes(target.read_bytes() + b"\n# edited\n")
    world.run_stage(prompts=prompts)
    assert world.ran == [1] and world.provider.requests == 1
    assert "recertify (Lane R): not possible" in capsys.readouterr().out


def test_lane_r_unrelated_input_change_is_a_no_op(
    world: LaneRWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Lane L correction engine's version is not a Lane R consumed input."""
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    monkeypatch.setattr(seal_module, "CORRECTION_ENGINE_VERSION", "not-the-sealed-version")
    world.run_stage()
    assert world.provider.requests == 0 and world.ran == []
    assert digest_tree(bundle) == before


def test_lane_r_corrupt_evidence_fails_closed(world: LaneRWorld) -> None:
    bundle = world.seal_proven()
    (bundle / "plan.json").write_bytes(b'{"tampered": true}\n')
    with pytest.raises(Exception, match="plan.json"):
        verify_bundle(bundle, LANE_R)
    world.run_stage()
    assert world.ran == [1] and world.provider.requests == 1
    _record('R','corrupt_evidence',world.provider.requests)


def test_lane_r_unproven_accepted_bundle_still_runs_the_pipeline(world: LaneRWorld) -> None:
    """An ACCEPTED bundle has not had its no-op proven; skipping would withhold the proof."""
    world.seal_first()
    world.run_stage()
    assert world.ran == [1] and world.provider.requests == 1


# --- the decision module itself ---------------------------------------------------------------------


def test_the_legacy_call_without_current_dependencies_never_skips(world: LaneRWorld) -> None:
    bundle = world.seal_proven()
    decision = preflight_decision(
        candidates_root=world.candidates, repository=world.entry.repository, lane=LANE_R,
        current_source_revision=bundle.name,
    )
    assert decision.can_skip_provider_call is False


@pytest.mark.parametrize(
    "damage", ["empty_current", "dangling_current", "bad_dependencies", "bad_manifest"]
)
def test_every_kind_of_unreadable_evidence_fails_closed(world: LaneRWorld, damage: str) -> None:
    bundle = world.seal_proven()
    lane_root = bundle.parent
    if damage == "empty_current":
        (lane_root / "CURRENT").write_text("", encoding="utf-8")
    elif damage == "dangling_current":
        (lane_root / "CURRENT").write_text("0" * 40, encoding="utf-8")
    elif damage == "bad_dependencies":
        (bundle / "dependencies.json").write_text("not json", encoding="utf-8")
    else:
        (bundle / "manifest.json").write_text("{", encoding="utf-8")
    decision = world.preflight()
    assert decision.can_skip_provider_call is False
    assert decision.reason


def test_the_proven_lane_r_bundle_is_the_one_case_that_skips(world: LaneRWorld) -> None:
    world.seal_proven()
    decision = world.preflight()
    assert decision.can_skip_provider_call is True
    assert decision.unchecked_scopes == () and decision.changed == ()
