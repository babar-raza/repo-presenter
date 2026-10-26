"""seal.py's full no-op-proof-adoption dance: the first seal, the real proof, and update
recording/adoption for a rerun whose artifacts genuinely differ.

Scope matches readme.bundle.seal's own module docstring (v1-v4): the first seal (ACCEPTED), the
real proof of a fresh byte-identical zero-call rerun (READY_FOR_PROPOSAL), recording a
difference against an already-proven or already-waiting bundle through invalidation.py's own
route() (VALID_UPDATE_AVAILABLE/INVALIDATED), and adopting a waiting update once a later rerun
reproduces it, fresh and zero-call. A byte-identical rerun that is not fresh or not zero-call
still raises NotImplementedError -- the proof is never faked.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from repo_presenter.core.llm.ledger import load_records
from repo_presenter.core.llm.prompts import (
    LoadedManifest,
    Output,
    Packet,
    PacketField,
    PromptManifest,
    PromptRegistry,
    Sampling,
)
from repo_presenter.core.noop_proof import Invocation, ProcessIdentity
from repo_presenter.core.secrets import ConfiguredSecret
from repo_presenter.readme.bundle.seal import (
    BUNDLE_MANIFEST_NAME,
    CURRENT_FILENAME,
    BundleLeakError,
    SealError,
    SealInputs,
    bundle_directory,
    seal_candidate,
)
from tests.readme.composition.synthetic import make_entry, make_facts


def _prompt_registry() -> PromptRegistry:
    manifest = PromptManifest(
        prompt_id="repository_investigation",
        version="1",
        stage="S3",
        purpose="test",
        model_route="qwen3-next",
        route_rationale="test",
        sampling=Sampling(temperature=0.0, max_output_tokens=100, response_format="json_schema"),
        schema_preface="Reply against this schema:",
        rejection_template="Fix: $errors",
        packet=Packet(fields=(PacketField(name="repository", type="string", description="x"),)),
        output=Output(
            contract="TestV1",
            binding="fact_ids",
            schema={"type": "object", "required": ["fact_ids"], "properties": {}},
        ),
        system="You are a test job.",
        user_template="Repository: $repository",
    )
    loaded = LoadedManifest(manifest, Path("test.yaml"), "deadbeef" * 8)
    return PromptRegistry({"repository_investigation": loaded})


_LEDGER_RECORD = {
    "attempt": 1,
    "call_id": "a-01-success-1",
    "completion_tokens": 5,
    "derived_via_reask": False,
    "disposition": "provider_call",
    "effective_model": "m",
    "error_class": None,
    "finished_at": "2026-10-26T00:00:01Z",
    "http_status": 200,
    "invocation_id": "inv1",
    "job": "repository_investigation",
    "latency_ms": 10,
    "logical_call_id": "a",
    "max_tokens": 100,
    "model_route": "m",
    "model_served": "m",
    "outcome": "success",
    "prompt_sha256": "a" * 64,
    "prompt_tokens": 5,
    "provider_request_id": "r",
    "rejection": [],
    "repository": "org/repo",
    "request_sha256": "a" * 64,
    "response_format": "json_schema",
    "response_sha256": "b" * 64,
    "retained_reason": None,
    "schema_version": 1,
    "source_revision": "a" * 40,
    "stage": "S3",
    "started_at": "2026-10-26T00:00:00Z",
    "temperature": 0.0,
    "total_tokens": 10,
}
LEDGER_LINE = json.dumps(_LEDGER_RECORD) + "\n"


def _out_dir(tmp_path: Path, invocation_id: str, *, coherent: bool = True) -> Path:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "dispositions.json").write_text('{"dispositions": []}\n', encoding="utf-8")
    (out_dir / "plan.json").write_text('{"core_capabilities": []}\n', encoding="utf-8")
    (out_dir / "review_verdict.json").write_text(
        '{"schema_version": 1, "reviewer_logic_version": "1", "verdict": "ACCEPT", "findings": []}\n',
        encoding="utf-8",
    )
    (out_dir / "README.patch.diff").write_text("", encoding="utf-8")
    readme_name = "README.coherent.md" if coherent else "README.rendered.md"
    (out_dir / readme_name).write_text("# Widget\n\nA widget.\n", encoding="utf-8")
    llm_cache = out_dir / "llm_cache"
    llm_cache.mkdir()
    record = {**_LEDGER_RECORD, "invocation_id": invocation_id}
    (llm_cache / "ledger.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    return out_dir


def _facts_path(tmp_path: Path) -> Path:
    from repo_presenter.core.facts import write_facts

    path = tmp_path / "evidence" / "facts.json"
    write_facts(make_facts(), path)
    return path


def _inputs(
    tmp_path: Path, *, secrets=(), coherent: bool = True, mutate_out_dir=None
) -> SealInputs:
    """Builds a real out_dir whose ledger carries the SAME invocation_id as the returned
    SealInputs -- required for reconcile_ledger's own cross-check to pass. ``mutate_out_dir``,
    when given, is called with the built out_dir before SealInputs is returned, so a test can
    corrupt/remove a file after the ledger is already consistent."""
    entry = make_entry()
    facts = make_facts()
    invocation = Invocation.begin()
    out_dir = _out_dir(tmp_path, invocation.invocation_id, coherent=coherent)
    if mutate_out_dir is not None:
        mutate_out_dir(out_dir)
    return SealInputs(
        entry=entry,
        source_revision=facts.source_revision,
        facts=facts,
        prompts=_prompt_registry(),
        out_dir=out_dir,
        facts_path=_facts_path(tmp_path),
        candidates_root=tmp_path,
        provider_calls=1,
        invocation=invocation,
        secrets=secrets,
    )


def test_seal_candidate_writes_a_real_manifest_with_every_required_artifact(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    result = seal_candidate(inputs)

    assert result.state == "ACCEPTED"
    manifest = json.loads((result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "ACCEPTED"
    assert manifest["no_op_proof"] is None
    assert manifest["repository"] == inputs.entry.repository
    assert manifest["revision"] == inputs.source_revision
    for name in (
        "README.md", "README.patch.diff", "facts.json", "dispositions.json", "plan.json",
        "review_verdict.json", "ledger.jsonl", "dependencies.json",
    ):
        assert name in manifest["files"], f"missing {name}"
        assert (result.bundle / name).is_file()


def test_seal_candidate_falls_back_to_rendered_readme_when_no_coherent_readme_exists(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path, coherent=False)
    result = seal_candidate(inputs)
    assert (result.bundle / "README.md").read_text(encoding="utf-8") == (
        inputs.out_dir / "README.rendered.md"
    ).read_text(encoding="utf-8")


def test_seal_candidate_fails_closed_when_a_required_artifact_is_missing(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, mutate_out_dir=lambda out_dir: (out_dir / "plan.json").unlink())
    with pytest.raises(SealError, match="plan.json"):
        seal_candidate(inputs)


def test_seal_candidate_writes_the_current_pointer(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    result = seal_candidate(inputs)
    current = result.bundle.parent / CURRENT_FILENAME
    assert current.read_bytes() == f"{inputs.source_revision}\n".encode()


def test_bundle_directory_matches_recheck_pys_own_candidates_convention(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    expected = (
        tmp_path / "candidates" / f"{inputs.entry.owner}__{inputs.entry.name}"
        / inputs.source_revision
    )
    assert bundle_directory(inputs.candidates_root, inputs.entry, inputs.source_revision) == expected


def test_seal_candidate_refuses_a_bundle_containing_a_configured_secret(tmp_path: Path) -> None:
    def _leak(out_dir: Path) -> None:
        (out_dir / "plan.json").write_text('{"leaked": "sk-super-secret-token"}\n', encoding="utf-8")

    secrets = (ConfiguredSecret("API_KEY", b"sk-super-secret-token"),)
    inputs = _inputs(tmp_path, secrets=secrets, mutate_out_dir=_leak)
    with pytest.raises(BundleLeakError, match="API_KEY"):
        seal_candidate(inputs)
    # No trace left on disk: neither the bundle nor a leftover staging directory.
    repo_dir = tmp_path / "candidates" / f"{inputs.entry.owner}__{inputs.entry.name}"
    assert not (repo_dir / inputs.source_revision).exists()
    assert not any(p.name.startswith(".") for p in repo_dir.iterdir()) if repo_dir.is_dir() else True


def _fresh_invocation(seed: int = 0) -> Invocation:
    """A different process from whatever sealed the first manifest in this test run -- real
    processes never share a nonce; this hand-built one deliberately does not either. Pass a
    distinct ``seed`` for each of several calls in one test that must be mutually fresh from
    one another too (not just from the original seal)."""
    identity = ProcessIdentity(
        pid=999999 + seed, started="2026-10-26T00:00:00Z", boot_id="other-boot",
        nonce=f"other-nonce-{seed}",
    )
    return Invocation(uuid.uuid4().hex, identity, "2026-10-26T00:00:01Z")


def _rerun_inputs(inputs: SealInputs, *, invocation: Invocation, provider_calls: int) -> SealInputs:
    return SealInputs(
        entry=inputs.entry,
        source_revision=inputs.source_revision,
        facts=inputs.facts,
        prompts=inputs.prompts,
        out_dir=inputs.out_dir,
        facts_path=inputs.facts_path,
        candidates_root=inputs.candidates_root,
        provider_calls=provider_calls,
        invocation=invocation,
    )


def _append_cache_reuse_record(out_dir: Path, invocation_id: str) -> None:
    """A real rerun that answers every job from the CallStore records a cache_reuse line for
    each -- measure_invocation refuses an invocation with zero ledger records at all (it cannot
    tell "genuinely reused everything" from "died before its first job")."""
    record = {
        **_LEDGER_RECORD,
        "call_id": f"a-00-cache_reuse-{invocation_id}",
        "invocation_id": invocation_id,
        "disposition": "cache_reuse",
        "attempt": 0,
    }
    ledger_path = out_dir / "llm_cache" / "ledger.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def test_seal_candidate_raises_not_implemented_when_a_rerun_is_not_zero_call(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    with pytest.raises(NotImplementedError, match="provider call"):
        seal_candidate(inputs)  # same inputs: byte-identical, but provider_calls == 1


def test_seal_candidate_raises_not_implemented_when_a_zero_call_rerun_is_not_fresh(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    rerun = _rerun_inputs(inputs, invocation=inputs.invocation, provider_calls=0)
    with pytest.raises(NotImplementedError, match="fresh process"):
        seal_candidate(rerun)  # the SAME process that sealed it, never fresh from itself


def test_seal_candidate_re_seals_plainly_when_an_unproven_bundle_s_artifacts_differ(
    tmp_path: Path,
) -> None:
    """Nothing was proven yet (still ACCEPTED), so a differing rerun simply re-seals over it --
    there is no proof to protect, matching the old repo's own seal_candidate: a changed,
    not-yet-``waiting_state`` bundle re-seals as ACCEPTED, proof withdrawn (there never was
    one)."""
    inputs = _inputs(tmp_path)
    first = seal_candidate(inputs)
    assert first.state == "ACCEPTED"

    (inputs.out_dir / "plan.json").write_text('{"core_capabilities": ["changed"]}\n', encoding="utf-8")
    rerun = _rerun_inputs(inputs, invocation=inputs.invocation, provider_calls=1)
    result = seal_candidate(rerun)

    assert result.state == "ACCEPTED"
    assert result.no_op_proof is None
    assert (result.bundle / "plan.json").read_text(encoding="utf-8") == (
        inputs.out_dir / "plan.json"
    ).read_text(encoding="utf-8")


def test_seal_candidate_records_an_invalidating_update_when_a_proven_bundle_s_facts_differ(
    tmp_path: Path,
) -> None:
    """facts.json's own scope ("facts") is the one scope that invalidates -- the proven content
    is still left untouched, but the manifest also carries an "invalidated" record."""
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(_rerun_inputs(inputs, invocation=fresh, provider_calls=0))
    assert proven.state == "READY_FOR_PROPOSAL"

    inputs.facts_path.write_text('{"not": "the same facts anymore"}\n', encoding="utf-8")
    later = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, later.invocation_id)
    result = seal_candidate(_rerun_inputs(inputs, invocation=later, provider_calls=0))

    assert result.state == "INVALIDATED"
    assert result.no_op_proof is not None  # still preserved for the record

    manifest = json.loads((result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "INVALIDATED"
    assert manifest["update"]["classification"] == "factual"
    assert manifest["update"]["triggering_scope"] == "facts"
    assert manifest["invalidated"]["scope"] == "facts"


def test_seal_candidate_raises_not_implemented_when_a_proven_bundle_s_artifacts_differ(
    tmp_path: Path,
) -> None:
    """Once a bundle IS proven (READY_FOR_PROPOSAL), a later difference must not silently
    overwrite the proof: it is routed through invalidation.py's route() and recorded as a
    waiting update instead, with the proven content and its proof left exactly as proven.
    Adopting the waiting update on a further matching rerun is not built yet."""
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(_rerun_inputs(inputs, invocation=fresh, provider_calls=0))
    assert proven.state == "READY_FOR_PROPOSAL"
    proven_plan_bytes = (proven.bundle / "plan.json").read_bytes()

    (inputs.out_dir / "plan.json").write_text('{"core_capabilities": ["changed"]}\n', encoding="utf-8")
    later = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, later.invocation_id)
    rerun = _rerun_inputs(inputs, invocation=later, provider_calls=0)
    result = seal_candidate(rerun)

    # plan.json's own scope ("planning") never invalidates -- only "facts" does.
    assert result.state == "VALID_UPDATE_AVAILABLE"
    assert result.no_op_proof is not None  # the original proof is preserved, not withdrawn
    assert (result.bundle / "plan.json").read_bytes() == proven_plan_bytes  # untouched

    manifest = json.loads((result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "VALID_UPDATE_AVAILABLE"
    assert manifest["update"]["available"] is True
    assert manifest["update"]["changed"] == ["plan.json"]
    assert manifest["update"]["triggering_scope"] == "planning"
    assert "invalidated" not in manifest


def test_seal_candidate_proves_the_no_op_on_a_fresh_byte_identical_zero_call_rerun(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    first = seal_candidate(inputs)
    assert first.state == "ACCEPTED"
    assert first.no_op_proof is None

    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    rerun = _rerun_inputs(inputs, invocation=fresh, provider_calls=0)
    result = seal_candidate(rerun)

    assert result.state == "READY_FOR_PROPOSAL"
    assert result.no_op_proof is not None
    assert result.no_op_proof["byte_identical"] is True
    assert result.no_op_proof["fresh_process"] is True
    assert result.no_op_proof["provider_calls"] == 0
    assert result.no_op_proof["rerun"]["invocation_id"] == fresh.invocation_id
    assert result.no_op_proof["first_run"]["invocation_id"] == inputs.invocation.invocation_id

    manifest = json.loads((result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    assert manifest["no_op_proof"]["byte_identical"] is True
    # The artifact content itself really is untouched -- not just reported as such.
    assert (result.bundle / "plan.json").read_text(encoding="utf-8") == (
        inputs.out_dir / "plan.json"
    ).read_text(encoding="utf-8")


def test_the_sealed_ledger_is_read_back_identically(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    result = seal_candidate(inputs)
    records = load_records(result.bundle / "ledger.jsonl")
    assert len(records) == 1
    assert records[0].job == "repository_investigation"


def test_dependencies_document_names_the_consumed_facts_and_components(tmp_path: Path) -> None:
    from repo_presenter.readme.bundle.seal import dependencies_document

    inputs = _inputs(tmp_path)
    document = dependencies_document(inputs)
    assert document["source"]["revision"] == inputs.source_revision
    assert set(document["facts"]) == {fact.id for fact in inputs.facts.facts}
    assert document["components"]["reviewer_logic"]
    assert "repository_investigation" in document["prompts"]


def test_seal_candidate_adopts_a_waiting_update_on_a_later_fresh_zero_call_reproduction(
    tmp_path: Path,
) -> None:
    """A rerun that reproduces exactly what a waiting update recorded -- fresh, zero calls --
    adopts it as the new proven content, keeping the previous proof on the manifest for the
    record under "adopted"."""
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    first_proof = seal_candidate(_rerun_inputs(inputs, invocation=fresh, provider_calls=0))
    assert first_proof.state == "READY_FOR_PROPOSAL"

    # A rerun changes plan.json and records the update (byte-identical check fails, so this
    # recording rerun itself need not be fresh or zero-call).
    (inputs.out_dir / "plan.json").write_text('{"core_capabilities": ["changed"]}\n', encoding="utf-8")
    recorder = _fresh_invocation(seed=1)
    _append_cache_reuse_record(inputs.out_dir, recorder.invocation_id)
    recorded = seal_candidate(_rerun_inputs(inputs, invocation=recorder, provider_calls=0))
    assert recorded.state == "VALID_UPDATE_AVAILABLE"

    # A LATER rerun reproduces exactly that same changed plan.json -- fresh (a genuinely
    # different process from the recorder, not just from the original seal), zero calls -- and
    # adopts it.
    adopter = _fresh_invocation(seed=2)
    _append_cache_reuse_record(inputs.out_dir, adopter.invocation_id)
    adopted_result = seal_candidate(_rerun_inputs(inputs, invocation=adopter, provider_calls=0))

    assert adopted_result.state == "READY_FOR_PROPOSAL"
    assert adopted_result.no_op_proof is not None
    assert adopted_result.no_op_proof["byte_identical"] is True
    assert (adopted_result.bundle / "plan.json").read_text(encoding="utf-8") == (
        inputs.out_dir / "plan.json"
    ).read_text(encoding="utf-8")

    manifest = json.loads((adopted_result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    assert manifest["adopted"]["changed"] == ["plan.json"]
    assert manifest["adopted"]["previous_proof"] == first_proof.no_op_proof
