"""BL-440: an explicit ``refresh`` of a sealed Lane R cell.

``present`` on a certified sealed cell takes a zero-call path (skip or re-certify-instead) and
``seal_candidate`` records a later difference beside a proven seal instead of replacing it, so no
existing seal can ever be re-made under newer code. ``--refresh`` (run request ``"refresh": true``,
Lane R only) bypasses both zero-call paths, runs the full generation and seals the new candidate
only when it passed every gate. Everything here is zero-call: the provider is the counting fake.
"""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from repo_presenter import present
from repo_presenter.core.candidates import CURRENT_FILENAME
from repo_presenter.readme.bundle.seal import BUNDLE_MANIFEST_NAME, seal_candidate
from tests.readme.bundle.test_seal import _append_cache_reuse_record, _fresh_invocation, _inputs
from tests.test_lane_l_hosted import digest_tree
from tests.test_preflight_wiring import LaneRWorld

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_request_bl440", REPO / "scripts" / "run_request.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

REGISTRY = [{"repository": "o/n", "ecosystem": "rust"}]
OK = ["run-request.json"]
REQ = {"job": "present", "repository": "o/n", "ecosystem": "rust", "lane": "R"}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LaneRWorld:
    return LaneRWorld(tmp_path, monkeypatch)


def _stage(world: LaneRWorld, **extra: Any) -> BaseException | None:
    try:
        present._cascade_and_seal(
            repository=world.entry.repository, ecosystem="python", clone_path=world.upstream,
            facts_path=world.facts_path, workdir=world.root / "work",
            candidates_root=world.candidates, config=None,
            prompts_path=Path(__file__).resolve().parents[1] / "prompts",
            registry_path=world.root / "unused-registry.json", **extra,
        )
    except Exception as exc:  # noqa: BLE001
        return exc
    return None


def _current(world: LaneRWorld) -> bytes:
    return (world.candidates / "candidates" / world.entry.repository.replace("/", "__")
            / CURRENT_FILENAME).read_bytes()


# (a) refresh=false is the unchanged behaviour ------------------------------------------------------


def test_refresh_defaults_to_false_and_the_zero_call_skip_is_unchanged(world: LaneRWorld) -> None:
    import inspect

    assert inspect.signature(present._cascade_and_seal).parameters["refresh"].default is False
    bundle = world.seal_proven()
    before = digest_tree(bundle)
    assert _stage(world) is None
    assert _stage(world, refresh=False) is None
    assert world.ran == [] and world.provider.requests == 0
    assert digest_tree(bundle) == before


# (b) refresh=true bypasses both zero-call paths ----------------------------------------------------


def test_refresh_bypasses_the_skip_and_the_recertify_instead_paths(
    world: LaneRWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.seal_proven()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a refresh must not consult a zero-call path")

    monkeypatch.setattr(present, "preflight_cascade", forbidden)
    monkeypatch.setattr(present, "recertify_instead", forbidden)
    error = _stage(world, refresh=True)
    assert isinstance(error, present.PresentFailure) and "stub pipeline ran" in str(error)
    assert world.ran == [1] and world.provider.requests == 1  # the generation really ran


def test_refresh_drops_the_restored_call_store_so_the_generation_calls_the_provider(
    world: LaneRWorld,
) -> None:
    cache = world.root / "work" / "cascade" / "llm_cache"
    cache.mkdir(parents=True)
    (cache / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
    world.seal_proven()
    _stage(world, refresh=True)
    assert not cache.exists()


def test_a_refresh_is_lane_r_only(tmp_path: Path) -> None:
    with pytest.raises(present.ConfigError):
        present._lane_and_seal("L", refresh=True)
    assert present.main(["--lane", "L", "--refresh", "--repository", "o/n", "--ecosystem", "rust"]) != 0


# (c) a failing refresh leaves the seal and the CURRENT pointer exactly as they were ----------------


def test_a_failing_refresh_leaves_the_existing_seal_and_pointer_untouched(world: LaneRWorld) -> None:
    bundle = world.seal_proven()
    before, pointer = digest_tree(bundle), _current(world)
    manifest = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    assert _stage(world, refresh=True) is not None
    assert digest_tree(bundle) == before and _current(world) == pointer
    assert not any(p.name.startswith(".") for p in bundle.parent.iterdir() if p.is_dir())


def test_a_rejected_refresh_candidate_raises_before_anything_is_sealed(
    world: LaneRWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = world.seal_proven()
    before, pointer = digest_tree(bundle), _current(world)
    verdict = SimpleNamespace(verdict="REJECT", blocking_findings=[], findings=[], model_reviewed=True)
    monkeypatch.setattr(
        present, "run_cascade",
        lambda *a, **k: SimpleNamespace(review_verdict=verdict, out_dir=world.root / "work" / "cascade"),
    )
    for name in ("keep_blocking", "report_findings", "report_repairs"):
        monkeypatch.setattr(present, name, lambda *a, **k: None)
    monkeypatch.setattr(present, "blocked_predicate", lambda v: "blocked")
    error = _stage(world, refresh=True)
    assert isinstance(error, present.PresentFailure) and "nothing sealed" in str(error)
    assert digest_tree(bundle) == before and _current(world) == pointer


# the seal writer: a passing refresh is a NEW seal, a failing one never reaches it ------------------


def _proven(tmp_path: Path) -> Any:
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(replace(inputs, invocation=fresh, provider_calls=0))
    assert proven.state == "READY_FOR_PROPOSAL"
    return inputs, proven


def test_a_passing_refresh_replaces_a_proven_seal_as_a_new_accepted_seal(tmp_path: Path) -> None:
    inputs, proven = _proven(tmp_path)
    (inputs.out_dir / "plan.json").write_text('{"core_capabilities": ["new"]}\n', encoding="utf-8")
    later = _fresh_invocation(1)
    _append_cache_reuse_record(inputs.out_dir, later.invocation_id)

    # without refresh the difference is only recorded beside the proven seal (unchanged behaviour)
    plain = replace(inputs, invocation=later, provider_calls=0)
    assert seal_candidate(plain).state == "VALID_UPDATE_AVAILABLE"
    assert (proven.bundle / "plan.json").read_bytes() == b'{"core_capabilities": []}\n'

    result = seal_candidate(replace(plain, refresh=True))
    assert result.state == "ACCEPTED" and result.no_op_proof is None
    assert (result.bundle / "plan.json").read_bytes() == b'{"core_capabilities": ["new"]}\n'
    manifest = json.loads((result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["superseded"]["refresh"] is True
    assert manifest["superseded"]["previous_state"] in ("READY_FOR_PROPOSAL", "VALID_UPDATE_AVAILABLE")
    assert manifest["superseded"]["previous_sealed_by"]


def test_a_refresh_identical_to_the_seal_leaves_it_exactly_as_it_was(tmp_path: Path) -> None:
    inputs, proven = _proven(tmp_path)
    before = digest_tree(proven.bundle)
    again = replace(inputs, invocation=_fresh_invocation(2), provider_calls=3, refresh=True)
    result = seal_candidate(again)  # a no-op, never the "proof needs zero calls" error
    assert result.state == "READY_FOR_PROPOSAL"
    assert digest_tree(proven.bundle) == before


# (d) the planner never passes refresh ---------------------------------------------------------------


def test_the_scheduled_planner_and_its_dispatch_never_pass_refresh() -> None:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "present.yml").read_text(encoding="utf-8"))
    cohort = workflow["jobs"]["cohort"]
    for step in cohort["steps"]:
        assert "refresh" not in str(step.get("run", "")).lower(), step.get("name")
    for path in (REPO / "scripts").glob("*cohort*.py"), (REPO / "scripts").glob("scheduled_execution_gate.py"):
        for file in path:
            assert "refresh" not in file.read_text(encoding="utf-8").lower(), file
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert triggers["workflow_dispatch"]["inputs"]["refresh"]["default"] is False
    assert triggers["workflow_call"]["inputs"]["refresh"]["default"] is False
    # no workflow but present.yml and its one validated caller mentions refresh at all
    for other in (REPO / ".github" / "workflows").glob("*.yml"):
        if other.name not in ("present.yml", "run-request-execute.yml"):
            assert "refresh" not in other.read_text(encoding="utf-8").lower(), other.name


def test_the_lane_r_step_adds_the_flag_only_from_the_refresh_input() -> None:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "present.yml").read_text(encoding="utf-8"))
    step = next(s for s in workflow["jobs"]["present"]["steps"] if s.get("id") == "lane_r")
    assert step["env"]["INPUT_REFRESH"] == "${{ inputs.refresh && 'true' || 'false' }}"
    assert '--refresh' in step["run"] and '"$INPUT_REFRESH" = "true"' in step["run"]
    lane_l = next(s for s in workflow["jobs"]["present"]["steps"] if s.get("id") == "lane_l")
    assert "refresh" not in json.dumps(lane_l).lower()
    caller = yaml.safe_load((REPO / ".github" / "workflows" / "run-request-execute.yml").read_text(encoding="utf-8"))
    assert caller["jobs"]["present"]["with"]["refresh"] == "${{ needs.validate.outputs.refresh == 'true' }}"


# (e) request validation ----------------------------------------------------------------------------


def test_a_refresh_request_validates_only_as_true_with_lane_r_on_a_present_job() -> None:
    assert rr.validate(REQ, REGISTRY, OK, True) == {
        "job": "present", "repository": "o/n", "ecosystem": "rust", "lane": "R"
    }
    assert rr.validate({**REQ, "refresh": False}, REGISTRY, OK, True) == rr.validate(REQ, REGISTRY, OK, True)
    assert rr.validate({**REQ, "refresh": True}, REGISTRY, OK, True)["refresh"] == "true"


@pytest.mark.parametrize(
    "request_, fragment",
    [
        ({**REQ, "lane": "L", "refresh": True}, "Lane R only"),
        ({**REQ, "lane": "both", "refresh": True}, "Lane R only"),
        ({k: v for k, v in REQ.items() if k != "lane"} | {"refresh": True}, "Lane R only"),
        ({**REQ, "refresh": "true"}, "JSON boolean"),
        ({**REQ, "refresh": 1}, "JSON boolean"),
        ({"job": "mint", "refresh": True}, "takes no other field"),
        ({"job": "recertify", "refresh": True}, "takes no other field"),
        ({"job": "cohort", "refresh": True}, "takes no other field"),
        ({"job": "count", "refresh": True}, "takes no other field"),
        ({"job": "issues", "refresh": True}, "takes no other field"),
    ],
)
def test_refresh_is_refused_for_other_lanes_job_types_and_non_booleans(request_: Any, fragment: str) -> None:
    with pytest.raises(rr.RequestError, match=fragment):
        rr.validate(request_, REGISTRY, OK, True)


def test_refresh_is_refused_for_audit_jobs() -> None:
    context = rr.AuditContext()
    for job in rr.AUDIT_JOBS:
        with pytest.raises(rr.RequestError):
            rr.validate({"job": job, "refresh": True}, REGISTRY, OK, True, context)
