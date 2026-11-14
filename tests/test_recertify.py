"""Re-certification instead of regeneration (owner rule, 2026-11-06).

"we sealed some candidates and then a candidate caused version bump, and all previous sealed
candidates were lost, and number dropped to 0 ... I do not want that." Every candidate is held to
the SAME current standards, and a version bump never invalidates a seal or forces regeneration.

The candidate under test is a REAL sealed candidate (Email .NET, both lanes, sealed 2026-11-06),
stored as ``tests/fixtures/recertify/email_net.json.gz`` with the upstream README and tree at its
revision. It is re-sealed here through the real ``seal_candidate`` (with a one-record ledger), so
every bundle is a genuine seal; a "renderer N" seal is made by sealing with the renderer version
recorded as N. Every re-certification runs with the provider boundary rigged to raise.
"""

from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import commit_all, init_git_repository

from repo_presenter import present, recertify
from repo_presenter.core.candidates import LANE_L, LANE_R, verify_bundle
from repo_presenter.core.facts import FactsDocument, read_facts, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.core.preflight import PreflightDecision
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.state.bundle_store import publish_bundle, seal_history
from repo_presenter.core.version_set import current_fingerprint, fingerprint
from repo_presenter.readme.bundle import seal as seal_module
from repo_presenter.readme.bundle.seal import SealInputs, seal_candidate
from repo_presenter.readme.composition.placement import ATTRIBUTION_LINE
from repo_presenter.readme.validation import blocking
from repo_presenter.readme.validation.failures import Failure
from repo_presenter.readme.validation.public_text import internal_markers
from repo_presenter.recertify import (
    OUTCOME_NEEDS_REPAIR,
    OUTCOME_RECERTIFIED,
    Recertification,
    SourceSnapshot,
)
from tests.readme.bundle.test_seal import _LEDGER_RECORD

REPO = Path(__file__).resolve().parents[1]
PROMPTS = REPO / "prompts"
REGISTRY = REPO / "data" / "registry.json"
FIXTURE = json.loads(gzip.decompress((REPO / "tests/fixtures/recertify/email_net.json.gz").read_bytes()))
REPOSITORY = FIXTURE["repository"]

_SPEC = importlib.util.spec_from_file_location(
    "portfolio_delivery_count_recertify", REPO / "ops" / "checks" / "portfolio_delivery_count.py"
)
pdc = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = pdc
_SPEC.loader.exec_module(pdc)

from repo_presenter.readme.review.calibration_status import Calibration

# --- fixtures -----------------------------------------------------------------------------------


@pytest.fixture
def no_provider(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every way a provider call (or a call-store read standing in for one) could happen raises."""
    attempts: list[str] = []

    def forbidden(name: str):
        def raise_(*_args: Any, **_kwargs: Any) -> Any:
            attempts.append(name)
            raise AssertionError(f"re-certification made a provider/call-store access: {name}")
        return raise_

    monkeypatch.setattr(jobs_module.transport, "build_client", forbidden("build_client"))
    monkeypatch.setattr(jobs_module, "_complete", forbidden("_complete"))
    monkeypatch.setattr(jobs_module, "run_job", forbidden("run_job"))
    monkeypatch.setattr(jobs_module.CallStore, "get", forbidden("CallStore.get"))
    monkeypatch.setattr(jobs_module.CallStore, "record", forbidden("CallStore.record"))
    return attempts


def entry() -> Any:
    return require_listed(load_registry(REGISTRY), REPOSITORY)


def source() -> SourceSnapshot:
    return SourceSnapshot(
        tree_paths=tuple(FIXTURE["source"]["tree_paths"]),
        readme=FIXTURE["source"]["readme"].encode("utf-8"),
    )


def _ledger(out_dir: Path, invocation_id: str) -> None:
    cache = out_dir / "llm_cache"
    cache.mkdir(parents=True)
    record = {**_LEDGER_RECORD, "invocation_id": invocation_id}
    (cache / "ledger.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")


def _facts(root: Path, revision: str | None = None) -> tuple[FactsDocument, Path]:
    path = root / "facts.json"
    path.write_text(json.dumps(FIXTURE["facts"]), encoding="utf-8")
    document = read_facts(path)
    if revision is not None:
        from dataclasses import replace

        facts = tuple(
            replace(fact, value=revision) if fact.id == "identity:revision" else fact
            for fact in document.facts
        )
        document = FactsDocument(document.repository, revision, facts)
        write_facts(document, path)
    return document, path


def seal_lane_r(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    renderer: str | None = None,
    readme: str | None = None,
    revision: str | None = None,
    candidates_root: Path | None = None,
) -> Path:
    """A genuine Lane R seal of the fixture's stored outputs; ``renderer`` records an older
    renderer version in the seal (the version set it was "made under")."""
    stored = FIXTURE["lane_r"]
    out_dir = root / "out-r"
    out_dir.mkdir(parents=True)
    for name in ("plan.json", "dispositions.json", "content_units.json",
                 "content_units.coherent.json", "investigation.json", "review_verdict.json"):
        (out_dir / name).write_text(stored[name], encoding="utf-8", newline="\n")
    (out_dir / "README.coherent.md").write_text(readme or stored["README.md"], encoding="utf-8", newline="\n")
    (out_dir / "README.patch.diff").write_text("", encoding="utf-8")
    invocation = Invocation.begin()
    _ledger(out_dir, invocation.invocation_id)
    document, facts_path = _facts(root, revision)
    with monkeypatch.context() as patch:
        if renderer is not None:
            patch.setattr(seal_module, "RENDERER_VERSION", renderer)
        result = seal_candidate(SealInputs(
            entry=entry(), source_revision=revision or FIXTURE["revision"], facts=document,
            prompts=load_manifests(PROMPTS), out_dir=out_dir, facts_path=facts_path,
            candidates_root=candidates_root or root / "sealed", provider_calls=1,
            invocation=invocation,
        ))
    return result.bundle


def seal_lane_l(root: Path, monkeypatch: pytest.MonkeyPatch, *, detector_bump: bool = True) -> Path:
    stored = FIXTURE["lane_l"]
    out_dir = root / "out-l"
    out_dir.mkdir(parents=True)
    (out_dir / "README.corrected.md").write_text(stored["README.md"], encoding="utf-8", newline="\n")
    (out_dir / "README.original.md").write_text(stored["README.original.md"], encoding="utf-8", newline="\n")
    (out_dir / "README.patch.diff").write_text("", encoding="utf-8")
    for name in ("corrections.json", "holdouts.json", "review_verdict.json"):
        (out_dir / name).write_text(stored[name], encoding="utf-8", newline="\n")
    invocation = Invocation.begin()
    _ledger(out_dir, invocation.invocation_id)
    document, facts_path = _facts(root)
    with monkeypatch.context() as patch:
        if detector_bump:
            patch.setattr(seal_module, "CORRECTION_ENGINE_VERSION", "older-engine")
        result = seal_candidate(SealInputs(
            entry=entry(), source_revision=FIXTURE["revision"], facts=document,
            prompts=load_manifests(PROMPTS), out_dir=out_dir, facts_path=facts_path,
            candidates_root=root / "sealed", provider_calls=1, invocation=invocation,
            lane=LANE_L,
        ))
    return result.bundle


def _calibration_for(bundle: Path) -> Calibration:
    review = json.loads((bundle / "review_verdict.json").read_text(encoding="utf-8"))
    return Calibration("PASSED", reviewer_logic_version=str(review["reviewer_logic_version"]),
                       prompt_version=str(review["prompt_version"]))


def _passed_review(bundle: Path) -> dict:
    review = json.loads((bundle / "review_verdict.json").read_text(encoding="utf-8"))
    return {**review, "calibration_status": "PASSED"}


def _evidence(bundle: Path, lane: str, commit: str = "c" * 40, review: dict | None = None):
    deps = json.loads((bundle / "dependencies.json").read_text(encoding="utf-8"))
    return pdc.SealedEvidence(
        source="durable-ref", manifest={"state": "ACCEPTED"},
        review=review or _passed_review(bundle), readme=(bundle / "README.md").read_bytes(),
        version_set=fingerprint(deps, lane), commit=commit,
    )


def _no_github(_args: list[str]) -> bytes | None:
    raise AssertionError("no GitHub call expected")


# --- TC-024: the seal-path contract's _model_accept -----------------------------------------------


def test_model_accept_rejects_a_deterministic_only_verdict() -> None:
    """A deterministic-only ACCEPT (no model ever asked) never re-certifies as accepted -- the
    one invariant present.py's own "no LLM review...never sealed" refusal protects at seal time,
    mirrored here for a STORED review being re-read."""
    assert recertify._model_accept({"verdict": "ACCEPT", "model_verdict": None}) is False
    assert recertify._model_accept({"verdict": "ACCEPT"}) is False
    assert recertify._model_accept(None) is False
    assert recertify._model_accept({}) is False


def test_model_accept_rejects_a_non_accept_verdict() -> None:
    assert recertify._model_accept({"verdict": "REJECT", "model_verdict": "ACCEPT"}) is False


def test_model_accept_no_longer_requires_the_old_reviewers_own_accept() -> None:
    """TC-024's actual behavior change: ``verdict == "ACCEPT"`` already means (by
    ``readme.review.verdict.fold_verdict``'s own invariant) that any ``REJECT_*`` the old
    reviewer's one call returned was deterministically cleared -- non-negotiable 5 is enforced
    there, not by also demanding the old reviewer's single call said ACCEPT outright. The OLD
    ``_model_accept`` (``verdict == "ACCEPT" and model_verdict == "ACCEPT"``) would have rejected
    this; TC-024's accepts it."""
    assert recertify._model_accept(
        {"verdict": "ACCEPT", "model_verdict": "REJECT_PRESENTATION"}
    ) is True


def test_model_accept_rejects_a_unit_m8_marked_reject_or_inconclusive() -> None:
    base = {"verdict": "ACCEPT", "model_verdict": "ACCEPT"}
    assert recertify._model_accept(
        {**base, "unit_reviews": [{"unit": "u1", "m8": {"status": "reject"}}]}
    ) is False
    assert recertify._model_accept(
        {**base, "unit_reviews": [{"unit": "u1", "m8": {"status": "inconclusive"}}]}
    ) is False


def test_model_accept_accepts_unit_m8_not_run_ok_or_absent() -> None:
    """Every status this card's own code can actually produce today (no real M8 provider call is
    wired yet -- TC-023's own scope boundary, owner ruling R26) reads as "no objection", and a
    seal made before this card (no ``"m8"`` key at all) is read the same way."""
    base = {"verdict": "ACCEPT", "model_verdict": "ACCEPT"}
    assert recertify._model_accept(
        {**base, "unit_reviews": [{"unit": "u1", "m8": {"status": "not_run"}}]}
    ) is True
    assert recertify._model_accept(
        {**base, "unit_reviews": [{"unit": "u1", "m8": {"status": "ok"}}]}
    ) is True
    assert recertify._model_accept(
        {**base, "unit_reviews": [{"unit": "u1"}]}  # no "m8" key at all (a pre-TC-024 seal)
    ) is True
    assert recertify._model_accept(base) is True  # no unit_reviews at all


# --- D1: renderer N -> N+1, zero calls, still counts ----------------------------------------------


def test_a_seal_under_renderer_n_recertifies_under_n_plus_1_with_zero_calls_and_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    current_renderer = seal_module.RENDERER_VERSION
    bundle = seal_lane_r(tmp_path, monkeypatch, renderer=str(int(current_renderer) - 1))
    sealed_deps = json.loads((bundle / "dependencies.json").read_text(encoding="utf-8"))
    assert sealed_deps["components"]["renderer"] == str(int(current_renderer) - 1)
    current = current_fingerprint(LANE_R, load_manifests(PROMPTS))
    assert fingerprint(sealed_deps, LANE_R) != current  # sealed under a different version set

    rec = recertify.recertify_bundle(
        bundle, LANE_R, entry=entry(), source=source(), current_version_set=current,
        seal_commit="c" * 40,
    )
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    assert rec.provider_calls == 0 and no_provider == []
    assert rec.certified and not rec.sealed_by_current

    # the re-certified seal: current version set, LLM outputs and review carried over unchanged
    written = recertify.write_recertified(
        bundle, rec, candidates_root=tmp_path / "recertified", prompts=load_manifests(PROMPTS),
        seal_commit="c" * 40,
    )
    assert verify_bundle(written, LANE_R)["recertified_from"]["commit"] == "c" * 40
    new_deps = json.loads((written / "dependencies.json").read_text(encoding="utf-8"))
    assert fingerprint(new_deps, LANE_R) == current
    assert new_deps["facts"] == sealed_deps["facts"] and new_deps["source"] == sealed_deps["source"]
    for name in ("plan.json", "dispositions.json", "content_units.coherent.json",
                 "review_verdict.json", "ledger.jsonl", "facts.json"):
        assert (written / name).read_bytes() == (bundle / name).read_bytes(), name
    provenance = json.loads((written / "recertification.json").read_text(encoding="utf-8"))
    assert provenance["recertified_from"]["version_set"] == fingerprint(sealed_deps, LANE_R)
    assert provenance["provider_calls"] == 0
    assert (bundle / "manifest.json").is_file()  # the original seal is untouched

    # ... and it counts: the version set is provenance, never a reason for zero
    outs = pdc.outcomes_for_lane(
        REPOSITORY, LANE_R, None, [_evidence(bundle, LANE_R)], [], current,
        _calibration_for(bundle), {}, _no_github, certification=rec,
    )
    summary = pdc.summarize(outs, _calibration_for(bundle))["lane_r"]
    assert summary[pdc.ACCEPTED] == 1 and summary["recertified"] == 1


# --- D2: the old attribution line is removed by re-rendering --------------------------------------


def test_a_seal_carrying_the_old_attribution_line_recertifies_and_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    stored = FIXTURE["lane_r"]["README.md"]
    first_break = stored.index("\n\n") + 2
    with_line = stored[:first_break] + ATTRIBUTION_LINE + "\n\n" + stored[first_break:]
    bundle = seal_lane_r(tmp_path, monkeypatch, renderer="35", readme=with_line)
    assert internal_markers((bundle / "README.md").read_text(encoding="utf-8"))  # BC-07 would fail it

    rec = recertify.recertify_bundle(bundle, LANE_R, entry=entry(), source=source(),
                                     current_version_set="current", seal_commit="c" * 40)
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    assert rec.readme_changed and internal_markers(rec.readme.decode("utf-8")) == []
    assert no_provider == []
    outs = pdc.certified_outcomes(REPOSITORY, LANE_R, None, [_evidence(bundle, LANE_R)], rec,
                                  _calibration_for(bundle), {}, _no_github)
    assert outs[0].independently_accepted


# --- D3: a new check fails -> NEEDS_REPAIR, the original seal still exists -------------------------


def _new_failing_check(monkeypatch: pytest.MonkeyPatch) -> None:
    judges = dict(blocking.JUDGES)
    judges["BC-99"] = lambda _candidate: [Failure("COMPOSING", "a newly enforced defect")]
    monkeypatch.setattr(blocking, "JUDGES", judges)
    monkeypatch.setitem(blocking.CHECK_NAMES, "BC-99", "a new check")


def _remote_with_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    remote = init_git_repository(tmp_path / "state-remote")
    bundle = seal_lane_r(tmp_path, monkeypatch, renderer="35")
    publish_bundle(REPOSITORY, LANE_R, bundle.parent, remote=str(remote))
    return remote


def _recertify_remote(remote: Path, scratch: Path) -> tuple[list[Recertification], dict]:
    history = seal_history(remote=str(remote), scratch=scratch)
    results = recertify.recertify_history(
        history, entries={REPOSITORY: entry()}, fetch=lambda _repo, _rev: source(),
        current={LANE_R: "current", LANE_L: "current-l"},
    )
    return results, history


def test_a_seal_failing_a_new_check_is_needs_repair_and_its_original_seal_still_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    remote = _remote_with_seal(tmp_path, monkeypatch)
    _new_failing_check(monkeypatch)
    results, history = _recertify_remote(remote, tmp_path / "scratch")
    [rec] = results
    assert rec.outcome == OUTCOME_NEEDS_REPAIR and rec.failing_checks == ("BC-99",)
    assert any("a newly enforced defect" in d for d in rec.details)
    with pytest.raises(recertify.RecertifyError):
        recertify.write_recertified(history[(REPOSITORY, LANE_R)][-1].bundle, rec,
                                    candidates_root=tmp_path / "x", prompts=load_manifests(PROMPTS))
    after = seal_history(remote=str(remote))[(REPOSITORY, LANE_R)]
    assert len(after) == 1 and after[0].commit == rec.seal_commit and after[0].counted
    assert no_provider == []


def test_the_lane_l_seal_recertifies_under_a_new_engine_version_with_zero_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    bundle = seal_lane_l(tmp_path, monkeypatch)
    rec = recertify.recertify_bundle(bundle, LANE_L, entry=entry(), source=source(),
                                     current_version_set=current_fingerprint(LANE_L, load_manifests(PROMPTS)))
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    assert not rec.sealed_by_current and no_provider == []
    written = recertify.write_recertified(bundle, rec, candidates_root=tmp_path / "r",
                                          prompts=load_manifests(PROMPTS))
    deps = json.loads((written / "dependencies.json").read_text(encoding="utf-8"))
    assert fingerprint(deps, LANE_L) == current_fingerprint(LANE_L, load_manifests(PROMPTS))


# --- D4: a prompt-version bump alone re-certifies; the cascade is never called ---------------------


def _clone_of_fixture(root: Path) -> tuple[Path, str]:
    clone = init_git_repository(root / "upstream", with_commit=False)
    for path in FIXTURE["source"]["tree_paths"]:
        target = clone / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"")
    (clone / "README.md").write_bytes(FIXTURE["source"]["readme"].encode("utf-8"))
    return clone, commit_all(clone, "fixture tree")


def test_a_prompt_version_bump_alone_recertifies_and_never_runs_the_cascade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    clone, revision = _clone_of_fixture(tmp_path)
    candidates = tmp_path / "candidates-root"
    bundle = seal_lane_r(tmp_path, monkeypatch, revision=revision, candidates_root=candidates)
    sealed_manifest = (bundle / "manifest.json").read_bytes()

    def cascade_must_not_run(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the generation cascade ran for a mechanism-only change")

    monkeypatch.setattr(present, "run_cascade", cascade_must_not_run)
    prompts = tmp_path / "prompts-bumped"
    import shutil

    shutil.copytree(PROMPTS, prompts)
    authoring = prompts / "section_authoring.yaml"
    authoring.write_bytes(authoring.read_bytes() + b"\n# a prompt bump\n")

    decision = present.preflight_cascade(
        REPOSITORY, clone, facts_path=tmp_path / "facts.json", candidates_root=candidates,
        prompts_path=prompts,
    )
    assert decision.recertify and not decision.can_skip_provider_call, decision.reason
    assert decision.changed == ("prompts.section_authoring",)

    present._cascade_and_seal(
        repository=REPOSITORY, ecosystem="net", clone_path=clone,
        facts_path=tmp_path / "facts.json", workdir=tmp_path / "work",
        candidates_root=candidates, config=None, prompts_path=prompts, registry_path=REGISTRY,
    )
    manifest = verify_bundle(bundle, LANE_R)
    assert manifest["recertified_from"]["revision"] == revision
    assert (bundle / "manifest.json").read_bytes() != sealed_manifest
    deps = json.loads((bundle / "dependencies.json").read_text(encoding="utf-8"))
    assert fingerprint(deps, LANE_R) == current_fingerprint(LANE_R, load_manifests(prompts))
    assert no_provider == []

    # the next run under the same code finds a seal certified by current code: it skips
    again = present.preflight_cascade(
        REPOSITORY, clone, facts_path=tmp_path / "facts.json", candidates_root=candidates,
        prompts_path=prompts,
    )
    assert again.can_skip_provider_call, again.reason


def test_needs_repair_runs_the_generation_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[int] = []

    def cascade(*_args: Any, **_kwargs: Any) -> Any:
        ran.append(1)
        raise present.PresentFailure("generation ran")

    monkeypatch.setattr(present, "run_cascade", cascade)
    monkeypatch.setattr(present, "preflight_cascade", lambda *a, **k: PreflightDecision(
        False, "only mechanism versions changed", (), (), ("prompts.x",), recertify=True))
    monkeypatch.setattr(present, "recertify_instead", lambda **_k: False)
    with pytest.raises(present.PresentFailure, match="generation ran"):
        present._cascade_and_seal(
            repository=REPOSITORY, ecosystem="net", clone_path=tmp_path, facts_path=tmp_path,
            workdir=tmp_path, candidates_root=tmp_path, config=None, prompts_path=PROMPTS,
            registry_path=REGISTRY,
        )
    assert ran == [1]


def test_changed_facts_are_never_routed_to_recertification(tmp_path: Path) -> None:
    from repo_presenter.core import preflight

    assert "facts" in preflight.INPUT_CHANGES and "source" in preflight.INPUT_CHANGES


# --- D5: the count does not drop on a bump ----------------------------------------------------------


def _rec(repository: str, *, outcome: str = OUTCOME_RECERTIFIED, sealed: str = "v1" * 32,
         current: str = "v2" * 32, commit: str = "c" * 40, checks: tuple[str, ...] = (),
         regenerations: int = 0) -> Recertification:
    return Recertification(repository, LANE_R, "rev", outcome, checks, tuple(f"{c}: x" for c in checks),
                           sealed_version_set=sealed, current_version_set=current,
                           seal_commit=commit, regenerations=regenerations)


def test_the_count_does_not_drop_on_a_version_bump() -> None:
    calibration = Calibration("PASSED", reviewer_logic_version="10", prompt_version="21")
    review = {"verdict": "ACCEPT", "model_verdict": "ACCEPT", "calibration_status": "PASSED",
              "reviewer_logic_version": "10", "prompt_version": "21"}

    def lane(repo: str, current: str, rec: Recertification | None) -> list:
        sealed = pdc.SealedEvidence("durable-ref", {"state": "ACCEPTED"}, review, b"#\n",
                                    version_set="v1" * 32, commit="c" * 40)
        return pdc.outcomes_for_lane(repo, LANE_R, None, [sealed], [], current, calibration, {},
                                     _no_github, certification=rec)

    before = lane("o/a", "v1" * 32, _rec("o/a", current="v1" * 32)) + lane("o/b", "v1" * 32, _rec("o/b", current="v1" * 32))
    after = lane("o/a", "v2" * 32, _rec("o/a")) + lane("o/b", "v2" * 32, _rec("o/b"))
    assert pdc.summarize(before, calibration)["lane_r"][pdc.ACCEPTED] == 2
    assert pdc.summarize(after, calibration)["lane_r"][pdc.ACCEPTED] == 2  # never 0
    # the old "current fingerprint only" path would have zeroed it
    legacy = lane("o/a", "v2" * 32, None) + lane("o/b", "v2" * 32, None)
    assert pdc.summarize(legacy, calibration)["lane_r"][pdc.ACCEPTED] == 0

    # NEEDS_REPAIR is reported with its checks and does not count; the seal is not dropped silently
    broken = lane("o/a", "v2" * 32, _rec("o/a", outcome=OUTCOME_NEEDS_REPAIR, checks=("BC-05",)))
    summary = pdc.summarize(broken, calibration)["lane_r"]
    assert summary[pdc.ACCEPTED] == 0 and summary["needs_repair"] == {"o/a": ["BC-05"]}


def test_an_uncalibrated_reviewer_is_reported_as_needing_a_review_only_pass() -> None:
    calibration = Calibration("NOT_PASSED", reviewer_logic_version="10", prompt_version="21")
    sealed = pdc.SealedEvidence("durable-ref", {"state": "ACCEPTED"},
                                {"verdict": "ACCEPT", "model_verdict": "ACCEPT"}, b"#\n",
                                version_set="v1" * 32, commit="c" * 40)
    [head] = pdc.outcomes_for_lane("o/a", LANE_R, None, [sealed], [], "v2" * 32, calibration, {},
                                   _no_github, certification=_rec("o/a"))
    assert head.bucket == pdc.UNCALIBRATED and head.needs_review_only_pass
    assert "review-only pass" in head.reason and "no regeneration" in head.reason
    assert pdc.summarize([head], calibration)["lane_r"]["needs_review_only_pass"] == ["o/a"]


def test_the_portfolio_matrix_counts_recertified_latest_seals() -> None:
    from repo_presenter.core.portfolio_matrix import build_matrix, summarize

    entries = [SimpleNamespace(repository=r, ecosystem="net", mode="full") for r in ("o/a", "o/b")]
    certs = {("o/a", LANE_R): _rec("o/a"),
             ("o/b", LANE_R): _rec("o/b", outcome=OUTCOME_NEEDS_REPAIR, checks=("BC-07",))}
    rows = build_matrix(entries, lambda _r, _l: None, Path("/nonexistent"), (), {}, certs)
    summary = summarize(rows, {"R": "v2" * 32, "L": "x"})
    assert summary["lane_r_pipeline_good"] == 1
    assert summary["lane_r_needs_repair"] == ["o/b"]


# --- E: the no-regression merge gate --------------------------------------------------------------


def test_the_gate_fails_when_a_passing_seal_breaks_and_passes_with_a_justification() -> None:
    passing = [_rec("o/a"), _rec("o/b", commit="d" * 40)]
    baseline = recertify.baseline_document(passing)
    assert recertify.gate(passing, baseline) == []  # an unchanged tree passes

    broken = [_rec("o/a", outcome=OUTCOME_NEEDS_REPAIR, checks=("BC-99",)), passing[1]]
    problems = recertify.gate(broken, baseline)
    assert len(problems) == 1 and "o/a" in problems[0] and "BC-99" in problems[0]

    updated = recertify.baseline_document(broken)
    # updated without a justification: still a regression against the base baseline
    assert recertify.gate(broken, updated, base_baseline=baseline)
    for row in updated["seals"]:
        if row["repository"] == "o/a":
            row["justification"] = "BC-05 too weak; BC-99 catches the dropped supported-version table"
    assert recertify.gate(broken, updated, base_baseline=baseline) == []
    # a justification that does not name the newly failing check is not enough
    vague = copy.deepcopy(updated)
    vague["seals"][0]["justification"] = "new check"
    assert recertify.gate(broken, vague, base_baseline=baseline)


def test_the_gate_end_to_end_against_a_real_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    remote = _remote_with_seal(tmp_path, monkeypatch)
    results, _ = _recertify_remote(remote, tmp_path / "s1")
    assert [r.outcome for r in results] == [OUTCOME_RECERTIFIED]
    baseline = recertify.baseline_document(results)
    assert recertify.gate(results, baseline) == []

    _new_failing_check(monkeypatch)  # "the change"
    after, _ = _recertify_remote(remote, tmp_path / "s2")
    assert recertify.gate(after, baseline)
    justified = recertify.baseline_document(after)
    justified["seals"][0]["justification"] = "BC-99 catches a real defect the old checks missed"
    assert recertify.gate(after, justified, base_baseline=baseline) == []
    # writing a fresh baseline keeps an existing justification for the same seal and outcome
    assert recertify.baseline_document(after, justified)["seals"][0]["justification"]
    assert no_provider == []


def test_the_regeneration_count_is_derived_from_the_seal_history() -> None:
    def seal(revision: str, plan: str, review: str = "r", error: str = "") -> Any:
        return SimpleNamespace(revision=revision, error=error, files={
            "plan.json": {"sha256": plan}, "review_verdict.json": {"sha256": review},
            "README.md": {"sha256": plan + review},
        })

    history = [
        seal("old", "p0"),
        seal("new", "p1"),
        seal("new", "p1"),          # a re-certification or republish: LLM outputs unchanged
        seal("new", "p2"),          # regenerated
        seal("new", "p2", "r2"),    # review re-asked: regenerated again
        seal("new", "p9", error="corrupt"),
    ]
    assert recertify.regeneration_count(history, LANE_R) == 2
    assert recertify.regeneration_count(history[:3], LANE_R) == 0
    assert recertify.regeneration_count([], LANE_R) == 0
    assert recertify.regeneration_count([seal("x", "p", "r1"), seal("x", "q", "r1")], LANE_L) == 0


def test_a_platform_ecosystem_spec_is_registered_before_recertifying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry run 2026-11-06: every non-built-in ecosystem failed 'no ecosystem spec registered',
    because specs register on plugin import and only the generation path imported the plugin."""
    from types import SimpleNamespace

    import repo_presenter.recertify as rc
    from repo_presenter.extractors.platforms import registry

    asked: list[str] = []
    monkeypatch.setattr(registry, "plugin_for", lambda ecosystem: asked.append(ecosystem))
    entry = SimpleNamespace(repository="o/n", ecosystem="rust")
    rc.recertify_bundle(tmp_path / "missing", "R", entry=entry, source=None)
    assert asked == ["rust"]


# --- TC-019b: zero-call restore of a unit a parity check names as lost ------------------------------


def test_restore_re_dispositions_a_unit_a_check_names_and_writes_a_verifying_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]
) -> None:
    bundle = seal_lane_r(tmp_path, monkeypatch, renderer="35")
    unit = "inherited_unit:024.paragraph"  # SUPERSEDE_REDUNDANT -> development_testing in the seal
    kept = {"VERIFIED_PRESERVE", "VERIFIED_MOVE", "PRESERVE_ATTRIBUTED"}

    def lost_unless_kept(candidate: Any) -> list[Failure]:
        entry = next(e for e in candidate.dispositions["dispositions"] if e["unit_id"] == unit)
        if entry["disposition"] in kept:
            return []
        return [
            Failure(
                "RECONCILING",
                f"{unit} holds h2 'Examples', which the published README prints and this candidate "
                "loses (section_coverage): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE)",
                unit=unit,
            )
        ]

    judges = dict(blocking.JUDGES)
    judges["BC-17"] = lost_unless_kept
    monkeypatch.setattr(blocking, "JUDGES", judges)

    common = dict(entry=entry(), source=source(), current_version_set="current", seal_commit="c" * 40)
    dry = recertify.recertify_bundle(bundle, LANE_R, **common)
    assert dry.outcome == OUTCOME_NEEDS_REPAIR and "BC-17" in dry.failing_checks
    assert "restored_units.json" not in dry.artifacts  # the dry counter and the gate never restore

    rec = recertify.recertify_bundle(bundle, LANE_R, restore=True, **common)
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    restored = json.loads(rec.artifacts["restored_units.json"])["restored"]
    assert [r["unit_id"] for r in restored] == [unit]
    assert restored[0]["was"].startswith("SUPERSEDE_REDUNDANT")
    assert rec.provider_calls == 0 and no_provider == []

    written = recertify.write_recertified(
        bundle, rec, candidates_root=tmp_path / "repaired", prompts=load_manifests(PROMPTS),
        seal_commit="c" * 40,
    )
    assert verify_bundle(written, LANE_R) is not None
    after = {e["unit_id"]: e for e in json.loads((written / "dispositions.json").read_text())["dispositions"]}
    before = {e["unit_id"]: e for e in json.loads((bundle / "dispositions.json").read_text())["dispositions"]}
    assert after[unit]["disposition"] in kept and before[unit]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert {k: v for k, v in after.items() if k != unit} == {k: v for k, v in before.items() if k != unit}
