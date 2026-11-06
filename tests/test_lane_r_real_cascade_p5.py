"""P5 durable caching proof for Lane R with the REAL pipeline (no stubbed ``run_cascade``).

``tests/test_preflight_wiring.py`` replaces ``present.run_cascade`` with a stub that makes one
request, so Lane R's real model pipeline is never measured there. Here the real
``present._cascade_and_seal`` runs the real ``cascade.run_cascade`` and the real
``seal_candidate`` against a real local repository; only the provider is faked, and every
provider request is counted at the fake client boundary
(``core.llm.jobs.transport.build_client``'s client). ``run_cascade`` is wrapped, not replaced, so
"the pipeline ran" is observed as well as the request count.

The scripted replies are the nine of ``tests/test_cascade.py`` (investigation, reconciliation,
planning, five authoring tasks, one coherence batch) plus one ACCEPT for the independent review,
which is what a sealable candidate needs: a deterministic-only verdict is never sealed. Two
fixture adjustments make the candidate pass its deterministic checks (they change the fixture, not
the pipeline): the live README's three headings match the headings the candidate keeps
(``live_readme_loss``), and the facts carry the install/example evidence and the repository carries
the LICENSE file that BC-02/BC-03/BC-06 require.

Proof flow, as ``tests/test_preflight_wiring.py`` seals Lane R, but through the real code: run 1
seals ACCEPTED; run 2, a fresh process identity over the same call store, replays every job from
the store with zero provider requests and seals READY_FOR_PROPOSAL; run 3 may skip.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import commit_all, head_revision, init_git_repository

from repo_presenter import cascade, present
from repo_presenter.core.candidates import LANE_R
from repo_presenter.core.facts import Evidence, FactsDocument, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.ledger import load_records
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.core.preflight import preflight_decision
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import CONFIG, README, _scripted_replies, _write_registry
from tests.test_lane_l_hosted import (
    PROMPTS,
    accept_reply,
    digest_tree,
    fresh_invocation,
)

#: Measured: nine pipeline stages (investigation, reconciliation, planning, five authoring tasks,
#: one coherence batch) plus the one independent-review request of a sealable candidate.
PIPELINE_STAGE_REQUESTS = 9
COLD_RUN_REQUESTS = PIPELINE_STAGE_REQUESTS + 1

#: The live README, with the three headings the candidate keeps so ``live_readme_loss`` is silent.
LIVE_README = (
    README.replace("# Aspose Widget", "# Aspose.Widget FOSS for Python")
    .replace("## Usage", "## Quick Start")
    .replace("## Limitations", "## Scope and Limitations")
)


def _record(scenario: str, requests: int) -> None:
    """When P5_PROOF_OUT is set, append the measured count (same convention as
    tests/test_preflight_wiring.py); unset, a no-op."""
    import os

    out = os.environ.get("P5_PROOF_OUT")
    if out:
        with open(out, "a", encoding="utf-8") as handle:
            line = json.dumps({"lane": "R-real", "scenario": scenario, "requests": requests})
            handle.write(line + chr(10))


class CountingClient:
    """The fake provider boundary: scripted replies in order, every request counted. A request
    beyond the script is answered ACCEPT rather than raising, so an unexpected extra call shows
    up as a wrong count, never as a masked exception."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.requests = 0
        self.replies: list[Any] = []
        self.reset()

        def create(**payload: Any) -> Any:
            self.requests += 1
            return self.replies.pop(0) if self.replies else accept_reply()

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    def reset(self) -> None:
        """Zero the count and re-arm the full script (each measured run starts from reply one)."""
        self.requests = 0
        self.replies = [*_scripted_replies(), accept_reply()]


class RealWorld:
    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.monkeypatch = monkeypatch
        self.entry = make_entry()
        self.upstream = init_git_repository(root / "upstream")
        (self.upstream / "README.md").write_text(LIVE_README, encoding="utf-8", newline="\n")
        (self.upstream / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        commit_all(self.upstream, "seed")
        self.facts_path = root / "facts.json"
        self.registry = root / "registry.json"
        _write_registry(self.registry, self.entry)
        self.candidates = root / "candidates-root"
        self.workdir = root / "work"
        self.write_facts()
        self.provider = CountingClient(monkeypatch)
        self.cascade_runs = 0
        real_run_cascade = present.run_cascade

        def counting_run_cascade(*args: Any, **kwargs: Any) -> Any:
            self.cascade_runs += 1
            return real_run_cascade(*args, **kwargs)

        monkeypatch.setattr(present, "run_cascade", counting_run_cascade)

    # -- inputs ----------------------------------------------------------------------------------

    def write_facts(self, mutate: Any = None) -> str:
        revision = head_revision(self.upstream)
        facts = []
        for fact in make_facts().facts:
            if fact.id == "install_command:pip":
                fact = replace(fact, evidence=(Evidence("README.md", "manifest; package registry"),))
            elif fact.id == "example:001":
                evidence = Evidence("README.md", "unit inherited_unit:005.code_block: EXECUTED")
                fact = replace(fact, evidence=(evidence,))
            facts.append(mutate(fact) if mutate else fact)
        write_facts(FactsDocument(self.entry.repository, revision, tuple(facts)), self.facts_path)
        return revision

    # -- driving the real entry point ------------------------------------------------------------

    def run(
        self, *, candidates: Path | None = None, prompts: Path | None = None,
        workdir: Path | None = None,
    ) -> BaseException | None:
        """One real ``present._cascade_and_seal`` call; returns the exception it raised, if any."""
        try:
            present._cascade_and_seal(
                repository=self.entry.repository, ecosystem="python", clone_path=self.upstream,
                facts_path=self.facts_path, workdir=workdir or self.workdir,
                candidates_root=candidates or self.candidates, config=CONFIG,
                prompts_path=prompts or PROMPTS, registry_path=self.registry,
            )
        except Exception as exc:  # noqa: BLE001 -- the caller asserts on it
            return exc
        return None

    def measured(self, **kwargs: Any) -> tuple[int, int, BaseException | None]:
        """(provider requests, run_cascade calls, exception) for one run, counted from zero."""
        self.provider.reset()
        before = self.cascade_runs
        error = self.run(**kwargs)
        return self.provider.requests, self.cascade_runs - before, error

    def preflight(self, *, prompts: Path | None = None) -> Any:
        return cascade.preflight_cascade(
            self.entry.repository, self.upstream, facts_path=self.facts_path,
            candidates_root=self.candidates, prompts_path=prompts or PROMPTS,
        )

    # -- the bundle ------------------------------------------------------------------------------

    def bundle(self, candidates: Path | None = None) -> Path:
        lane_root = (
            (candidates or self.candidates) / "candidates" / self.entry.repository.replace("/", "__")
        )
        return lane_root / (lane_root / "CURRENT").read_text(encoding="utf-8").strip()

    def state(self, candidates: Path | None = None) -> str:
        manifest = json.loads((self.bundle(candidates) / "manifest.json").read_text(encoding="utf-8"))
        return manifest["state"]

    # -- the proof flow --------------------------------------------------------------------------

    def seal_first(self) -> None:
        requests, runs, error = self.measured()
        assert error is None, error
        assert (requests, runs) == (COLD_RUN_REQUESTS, 1)
        assert self.state() == "ACCEPTED"

    def seal_proven(self) -> Path:
        """Run 1 (cold, real pipeline, ACCEPTED), then run 2 as a fresh process identity over the
        same call store: every job replays, zero requests, READY_FOR_PROPOSAL."""
        self.seal_first()
        self.monkeypatch.setattr(Invocation, "begin", staticmethod(lambda: fresh_invocation(2)))
        requests, runs, error = self.measured()
        assert error is None, error
        assert (requests, runs) == (0, 1), "the proof run replays the call store"
        assert self.state() == "READY_FOR_PROPOSAL"
        return self.bundle()


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RealWorld:
    return RealWorld(tmp_path, monkeypatch)


# --- (1) cold run ---------------------------------------------------------------------------------


def test_cold_run_executes_the_real_pipeline_and_seals_a_candidate(world: RealWorld) -> None:
    requests, runs, error = world.measured()

    assert error is None, error
    assert runs == 1
    assert requests == COLD_RUN_REQUESTS == 10  # 9 pipeline stages + 1 independent review
    _record("cold_run", requests)
    assert world.state() == "ACCEPTED"
    # Every one of those requests is in the one ledger under the one invocation.
    records = load_records(world.workdir / "cascade" / "llm_cache" / "ledger.jsonl")
    assert len(records) == requests
    assert len({record.invocation_id for record in records}) == 1
    for name in ("investigation.json", "plan.json", "README.coherent.md", "review_verdict.json"):
        assert (world.workdir / "cascade" / name).is_file(), name


# --- (2) warm, unchanged --------------------------------------------------------------------------


def test_warm_unchanged_rerun_makes_zero_requests_and_does_not_call_run_cascade(
    world: RealWorld,
) -> None:
    bundle = world.seal_proven()
    before = digest_tree(bundle)

    requests, runs, error = world.measured()

    assert error is None, error
    assert (requests, runs) == (0, 0)
    _record("warm_unchanged_rerun", requests)
    assert digest_tree(bundle) == before  # the proven bundle stays exactly as sealed
    assert world.preflight().can_skip_provider_call is True


def test_an_unproven_accepted_bundle_does_not_skip(world: RealWorld) -> None:
    """Between run 1 and the proof run the preflight must not skip (that would withhold the
    proof); the pipeline that then runs is answered entirely from the call store (seal_proven)."""
    world.seal_first()
    decision = world.preflight()
    assert decision.can_skip_provider_call is False
    assert "READY_FOR_PROPOSAL" in decision.reason


# --- (3) cold runner and evicted cache -------------------------------------------------------------


def test_cold_runner_with_only_the_restored_bundle_makes_zero_requests(
    world: RealWorld, tmp_path: Path
) -> None:
    """A fresh hosted runner: a new working directory with no call store at all, and only the
    bundle that bundle_store restores into a new candidates root. Mirrors the Lane R assertion of
    tests/test_preflight_wiring.py (a skip), here with the real pipeline behind it."""
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    restored = tmp_path / "restored"
    shutil.copytree(world.candidates, restored)
    shutil.rmtree(world.candidates)
    shutil.rmtree(world.workdir)

    requests, runs, error = world.measured(candidates=restored, workdir=tmp_path / "fresh-work")

    assert error is None, error
    assert (requests, runs) == (0, 0)
    _record("cold_runner", requests)
    assert digest_tree(world.bundle(restored)) == before


def test_evicted_call_store_with_the_proven_bundle_makes_zero_requests(world: RealWorld) -> None:
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    shutil.rmtree(world.workdir / "cascade" / "llm_cache")
    assert not (world.workdir / "cascade" / "llm_cache").exists()

    requests, runs, error = world.measured()

    assert error is None, error
    assert (requests, runs) == (0, 0)
    _record("evicted_cache", requests)
    assert digest_tree(bundle) == before


def test_cold_runner_with_neither_bundle_nor_cache_fails_closed_to_the_full_pipeline(
    world: RealWorld, tmp_path: Path
) -> None:
    """Nothing restored at all: there is nothing to prove a skip against, so the whole real
    pipeline runs and asks the provider every question again."""
    world.seal_proven()
    requests, runs, error = world.measured(
        candidates=tmp_path / "empty-candidates", workdir=tmp_path / "fresh-work"
    )
    assert error is None, error
    assert (requests, runs) == (COLD_RUN_REQUESTS, 1)
    _record("cold_runner_nothing_restored", requests)


def test_evicted_call_store_with_an_unproven_bundle_asks_the_provider_again(
    world: RealWorld,
) -> None:
    """The one case where the cache is load-bearing: an ACCEPTED (not yet proven) bundle plus an
    evicted call store cannot replay, so the pipeline pays for every request again."""
    world.seal_first()
    shutil.rmtree(world.workdir / "cascade" / "llm_cache")

    requests, runs, error = world.measured()

    assert runs == 1
    assert requests == COLD_RUN_REQUESTS, (requests, error)
    _record("evicted_cache_unproven", requests)


# --- (4) corrupt evidence --------------------------------------------------------------------------


def test_corrupt_evidence_reruns_the_pipeline_never_a_silent_skip(world: RealWorld) -> None:
    bundle = world.seal_proven()
    (bundle / "plan.json").write_bytes(b'{"tampered": true}\n')
    assert world.preflight().can_skip_provider_call is False

    requests, runs, error = world.measured()

    # The intact call store answers every job, so this rerun is a measured replay: the real
    # pipeline ran (it is a rerun, not a skip) and the provider was not needed.
    assert runs == 1, "a corrupt proven bundle must reopen the real pipeline"
    _record("corrupt_evidence_cache_intact", requests)
    assert requests == 0, (requests, error)


def test_corrupt_evidence_with_an_evicted_call_store_asks_the_provider_again(
    world: RealWorld,
) -> None:
    bundle = world.seal_proven()
    (bundle / "plan.json").write_bytes(b'{"tampered": true}\n')
    shutil.rmtree(world.workdir / "cascade" / "llm_cache")

    requests, runs, error = world.measured()

    assert runs == 1
    assert requests > 0, (requests, error)  # never a silent skip
    assert requests == COLD_RUN_REQUESTS, requests
    _record("corrupt_evidence", requests)


@pytest.mark.parametrize(
    "damage", ["empty_current", "dangling_current", "bad_dependencies", "bad_manifest"]
)
def test_every_kind_of_unreadable_evidence_makes_the_pipeline_run(
    world: RealWorld, damage: str
) -> None:
    bundle = world.seal_proven()
    if damage == "empty_current":
        (bundle.parent / "CURRENT").write_text("", encoding="utf-8")
    elif damage == "dangling_current":
        (bundle.parent / "CURRENT").write_text("0" * 40, encoding="utf-8")
    elif damage == "bad_dependencies":
        (bundle / "dependencies.json").write_text("not json", encoding="utf-8")
    else:
        (bundle / "manifest.json").write_text("{", encoding="utf-8")

    assert world.preflight().can_skip_provider_call is False
    _, runs, _ = world.measured()
    assert runs == 1


# --- (5) negative controls: a changed consumed input defeats the skip ------------------------------


def test_changed_upstream_readme_defeats_the_skip(world: RealWorld) -> None:
    world.seal_proven()
    assert world.preflight().can_skip_provider_call is True  # the control: it did skip

    (world.upstream / "README.md").write_text(LIVE_README + "\nMore text.\n", encoding="utf-8")
    commit_all(world.upstream, "readme change")
    world.write_facts()  # facts for the new revision

    decision = world.preflight()
    assert decision.can_skip_provider_call is False
    assert decision.changed, decision

    _, runs, _ = world.measured()
    assert runs == 1  # the real pipeline was entered; the changed README is never skipped over


def test_changed_facts_defeat_the_skip(world: RealWorld) -> None:
    world.seal_proven()
    assert world.preflight().can_skip_provider_call is True

    world.write_facts(
        lambda fact: replace(fact, value="MIT-0") if fact.id == "license:spdx" else fact
    )

    decision = world.preflight()
    assert decision.can_skip_provider_call is False
    assert decision.changed, decision

    _, runs, _ = world.measured()
    assert runs == 1


def test_changed_consumed_prompt_recertifies_without_regenerating(world: RealWorld, tmp_path: Path) -> None:
    world.seal_proven()
    prompts = tmp_path / "prompts-edited"
    shutil.copytree(PROMPTS, prompts)
    target = prompts / "repository_investigation.yaml"
    target.write_bytes(target.read_bytes() + b"\n# edited\n")

    decision = world.preflight(prompts=prompts)
    assert decision.can_skip_provider_call is False
    assert decision.changed, decision

    # Owner ruling R10: a mechanism change alone (here a prompt) never regenerates a sealed candidate;
    # the seal is re-certified from its stored outputs with zero provider calls, so the cascade does
    # not run. The change is still reported (decision.changed above) as provenance.
    _, runs, _ = world.measured(prompts=prompts)
    assert runs == 0


def test_the_proven_real_bundle_is_the_one_case_that_skips(world: RealWorld) -> None:
    bundle = world.seal_proven()
    decision = world.preflight()
    assert decision.can_skip_provider_call is True
    assert decision.unchecked_scopes == () and decision.changed == ()
    # The legacy call without current dependencies never skips, even over a real proven bundle.
    legacy = preflight_decision(
        candidates_root=world.candidates, repository=world.entry.repository, lane=LANE_R,
        current_source_revision=bundle.name,
    )
    assert legacy.can_skip_provider_call is False
