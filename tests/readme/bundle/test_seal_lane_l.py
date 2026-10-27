"""Sealing a Lane L candidate, and what the lane dimension must not change for Lane R
(plans/PLAN_lane_l_hosted.md L3, L4, L6, L8)."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pytest

from repo_presenter.core.candidates import LANE_L, LANE_R, ready_revision, verify_bundle
from repo_presenter.core.llm.prompts import (
    LoadedManifest,
    Output,
    Packet,
    PacketField,
    PromptManifest,
    PromptRegistry,
    Sampling,
)
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.readme.bundle import seal as seal_module
from repo_presenter.readme.bundle.evaluation import evaluate
from repo_presenter.readme.bundle.invalidation import (
    STATE_INVALIDATED,
    STATE_UPDATE_AVAILABLE,
    route,
)
from repo_presenter.readme.bundle.seal import (
    BUNDLE_MANIFEST_NAME,
    CURRENT_FILENAME,
    SealError,
    SealInputs,
    bundle_directory,
    dependencies_document,
    seal_candidate,
)
from repo_presenter.readme.correction.detectors import DETECTOR_VERSIONS
from tests.readme.bundle.test_seal import (
    LEDGER_LINE,
    _append_cache_reuse_record,
    _facts_path,
    _fresh_invocation,
    _inputs,
    _rerun_inputs,
)
from tests.readme.composition.synthetic import make_entry, make_facts

README_ORIGINAL = "# Widget\n\nSee [guide](docs/Guide.md).\n"
README_CORRECTED = "# Widget\n\nSee [guide](docs/guide.md).\n"


def _registry(
    prompt_hash: str = "deadbeef" * 8, job: str = "independent_review"
) -> PromptRegistry:
    manifest = PromptManifest(
        prompt_id=job,
        version="16",
        stage="S10",
        purpose="test",
        model_route="qwen3-next",
        route_rationale="test",
        sampling=Sampling(
            temperature=0.0, max_output_tokens=100, response_format="json_schema"
        ),
        schema_preface="Reply against this schema:",
        rejection_template="Fix: $errors",
        packet=Packet(
            fields=(PacketField(name="repository", type="string", description="x"),)
        ),
        output=Output(
            contract="TestV1",
            binding="fact_ids",
            schema={"type": "object", "required": ["fact_ids"], "properties": {}},
        ),
        system="You are a test job.",
        user_template="Repository: $repository",
    )
    return PromptRegistry(
        {job: LoadedManifest(manifest, Path("test.yaml"), prompt_hash)}
    )


def _lane_l_out_dir(tmp_path: Path, invocation_id: str) -> Path:
    out_dir = tmp_path / "lane-l-out"
    (out_dir / "llm_cache").mkdir(parents=True)
    (out_dir / "README.corrected.md").write_bytes(README_CORRECTED.encode())
    (out_dir / "README.original.md").write_bytes(README_ORIGINAL.encode())
    (out_dir / "README.patch.diff").write_bytes(b"--- a/README.md\n+++ b/README.md\n")
    report = {
        "outcome": "CORRECTED",
        "edits": [{"index": 0}],
        "unapplied": [{"defect": False}, {"defect": False}],
    }
    (out_dir / "corrections.json").write_text(
        json.dumps(report) + "\n", encoding="utf-8"
    )
    (out_dir / "holdouts.json").write_text('{"checks": []}\n', encoding="utf-8")
    (out_dir / "review_verdict.json").write_text(
        '{"verdict": "ACCEPT"}\n', encoding="utf-8"
    )
    record = json.loads(LEDGER_LINE)
    record["invocation_id"] = invocation_id
    (out_dir / "llm_cache" / "ledger.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )
    return out_dir


def _l_inputs(tmp_path: Path, *, prompts: PromptRegistry | None = None) -> SealInputs:
    facts = make_facts()
    invocation = Invocation.begin()
    return SealInputs(
        entry=make_entry(),
        source_revision=facts.source_revision,
        facts=facts,
        prompts=prompts or _registry(),
        out_dir=_lane_l_out_dir(tmp_path, invocation.invocation_id),
        facts_path=_facts_path(tmp_path),
        candidates_root=tmp_path,
        provider_calls=1,
        invocation=invocation,
        lane=LANE_L,
    )


def _l_rerun(
    inputs: SealInputs, invocation: Invocation, *, calls: int = 0
) -> SealInputs:
    return SealInputs(
        entry=inputs.entry,
        source_revision=inputs.source_revision,
        facts=inputs.facts,
        prompts=inputs.prompts,
        out_dir=inputs.out_dir,
        facts_path=inputs.facts_path,
        candidates_root=inputs.candidates_root,
        provider_calls=calls,
        invocation=invocation,
        lane=LANE_L,
    )


# --- the Lane L bundle -------------------------------------------------------------------------------


def test_a_lane_l_seal_writes_its_own_tree_manifest_and_pointer(tmp_path: Path) -> None:
    inputs = _l_inputs(tmp_path)
    result = seal_candidate(inputs)

    repo_dir = tmp_path / "candidates" / f"{inputs.entry.owner}__{inputs.entry.name}"
    assert result.bundle == repo_dir / "lane-l" / inputs.source_revision
    assert (
        bundle_directory(tmp_path, inputs.entry, inputs.source_revision, LANE_L)
        == result.bundle
    )
    assert (repo_dir / "lane-l" / CURRENT_FILENAME).read_bytes() == (
        f"{inputs.source_revision}\n".encode()
    )
    assert not (
        repo_dir / CURRENT_FILENAME
    ).exists()  # Lane R's pointer was never written

    manifest = verify_bundle(result.bundle, LANE_L)
    assert manifest is not None
    assert manifest["schema_version"] == 2 and manifest["lane"] == "L"
    assert manifest["state"] == "ACCEPTED"
    assert manifest["correction"] == {
        "outcome": "CORRECTED",
        "edits": 1,
        "defects": 0,
        "opportunities": 2,
    }
    assert set(manifest["files"]) == {
        "README.md",
        "README.original.md",
        "README.patch.diff",
        "corrections.json",
        "holdouts.json",
        "facts.json",
        "review_verdict.json",
        "ledger.jsonl",
        "dependencies.json",
    }
    assert (result.bundle / "README.md").read_bytes() == README_CORRECTED.encode()
    assert (
        result.bundle / "README.original.md"
    ).read_bytes() == README_ORIGINAL.encode()


def test_a_lane_l_seal_is_refused_when_an_artifact_is_missing(tmp_path: Path) -> None:
    inputs = _l_inputs(tmp_path)
    (inputs.out_dir / "holdouts.json").unlink()
    with pytest.raises(SealError, match="holdouts.json"):
        seal_candidate(inputs)
    repo_dir = tmp_path / "candidates"
    assert not repo_dir.exists() or not list(repo_dir.rglob("manifest.json"))


def test_a_lane_l_candidate_has_no_lane_r_artifacts_and_needs_none(
    tmp_path: Path,
) -> None:
    inputs = _l_inputs(tmp_path)
    result = seal_candidate(inputs)
    for absent in (
        "plan.json",
        "dispositions.json",
        "content_units.json",
        "investigation.json",
    ):
        assert not (result.bundle / absent).exists()


def test_the_lane_l_no_op_proof_is_the_same_proof_as_lane_rs(tmp_path: Path) -> None:
    inputs = _l_inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation()
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(_l_rerun(inputs, fresh))
    assert proven.state == "READY_FOR_PROPOSAL"
    assert (
        proven.no_op_proof is not None and proven.no_op_proof["byte_identical"] is True
    )
    manifest = json.loads(
        (proven.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["lane"] == "L" and manifest["correction"]["outcome"] == "CORRECTED"
    assert (
        ready_revision(tmp_path, inputs.entry.repository, LANE_L)
        == inputs.source_revision
    )
    assert ready_revision(tmp_path, inputs.entry.repository, LANE_R) is None


# --- the dependencies a Lane L candidate consumed ---------------------------------------------------------


def _staged(inputs: SealInputs) -> dict[str, bytes]:
    return seal_module._staged_artifacts(inputs)


def test_the_lane_l_dependencies_name_exactly_what_the_candidate_consumed(
    tmp_path: Path,
) -> None:
    inputs = _l_inputs(tmp_path)
    document = json.loads(_staged(inputs)["dependencies.json"])
    assert set(document) == {
        "schema_version",
        "lane",
        "source",
        "environment",
        "facts",
        "prompts",
        "components",
        "detectors",
    }
    assert document["lane"] == "L"
    assert document["source"] == {
        "revision": inputs.source_revision,
        "readme_sha256": hashlib.sha256(README_ORIGINAL.encode()).hexdigest(),
    }
    assert document["detectors"] == DETECTOR_VERSIONS
    assert set(document["components"]) == {
        "correction_engine",
        "correction_review",
        "reviewer_logic",
    }
    assert set(document["prompts"]) == {
        "independent_review"
    }  # no authoring/planning prompt
    assert set(document["facts"]) == {fact.id for fact in inputs.facts.facts}


def test_the_lane_l_dependencies_name_no_machine_so_a_rerun_elsewhere_writes_the_same_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _l_inputs(tmp_path)
    here = _staged(inputs)["dependencies.json"]
    (tmp_path / "r").mkdir()
    r_inputs = _inputs(tmp_path / "r")
    r_here = dependencies_document(r_inputs)

    monkeypatch.setattr(platform, "system", lambda: "Plan9")
    monkeypatch.setattr(platform, "python_version", lambda: "2.7.18")
    monkeypatch.setattr(seal_module, "toolchain_fingerprint", lambda: {"javac": "99.0"})
    assert _staged(inputs)["dependencies.json"] == here

    # The same change DOES move Lane R's record: that is its existing, extraction-environment
    # semantics, left exactly as it was.
    assert dependencies_document(r_inputs) != r_here
    assert dependencies_document(r_inputs)["environment"]["python_version"] == "2.7.18"


def test_lane_rs_dependencies_document_keeps_exactly_its_keys(tmp_path: Path) -> None:
    """Falsifier for 'the lane dimension edited a Lane R bundle': a Lane R rerun compares its
    dependencies.json byte for byte with the sealed one, so a new key (a lane marker) would make
    every layout-v1 bundle look changed. Lane R's document keeps exactly its old keys."""
    document = dependencies_document(_inputs(tmp_path))
    assert set(document) == {
        "schema_version",
        "source",
        "environment",
        "facts",
        "prompts",
        "components",
    }
    assert set(document["source"]) == {"revision"}
    assert set(document["components"]) == {
        "shell",
        "renderer",
        "normalisation",
        "reviewer_logic",
    }


# --- consumed-scope invalidation for Lane L ------------------------------------------------------------------


def _deps(tmp_path: Path, **overrides: object) -> dict:
    inputs = _l_inputs(tmp_path)
    document = json.loads(_staged(inputs)["dependencies.json"])
    document.update(overrides)
    return document


def test_a_changed_detector_reopens_only_the_correction_scope_and_never_invalidates(
    tmp_path: Path,
) -> None:
    sealed = _deps(tmp_path)
    current = json.loads(json.dumps(sealed))
    current["detectors"]["broken_link"] = "2"
    changes = evaluate(sealed, current).changes
    assert [(c.dependency, c.scope, c.reopens) for c in changes] == [
        ("detectors.broken_link", "correction", "COMPOSING")
    ]
    routing = route([c.dependency for c in changes])
    assert routing.state == STATE_UPDATE_AVAILABLE and not routing.invalidates


def test_a_changed_correction_engine_version_is_the_same_scope(tmp_path: Path) -> None:
    sealed = _deps(tmp_path)
    current = json.loads(json.dumps(sealed))
    current["components"]["correction_engine"] = "2"
    (change,) = evaluate(sealed, current).changes
    assert (change.dependency, change.scope) == (
        "components.correction_engine",
        "correction",
    )


def test_a_changed_live_readme_invalidates_because_it_is_a_changed_source(
    tmp_path: Path,
) -> None:
    sealed = _deps(tmp_path)
    current = json.loads(json.dumps(sealed))
    current["source"]["readme_sha256"] = "0" * 64
    (change,) = evaluate(sealed, current).changes
    assert (change.dependency, change.scope, change.reopens) == (
        "source",
        "facts",
        "EXTRACTING",
    )
    assert route([change.dependency]).state == STATE_INVALIDATED


def test_a_changed_fact_record_invalidates_through_the_facts_scope(
    tmp_path: Path,
) -> None:
    sealed = _deps(tmp_path)
    current = json.loads(json.dumps(sealed))
    some = min(current["facts"])
    current["facts"][some] = "0" * 64
    (change,) = evaluate(sealed, current).changes
    assert change.scope == "facts" and route([change.dependency]).invalidates


def test_a_prompt_or_renderer_lane_l_never_consumed_cannot_reopen_it(
    tmp_path: Path,
) -> None:
    """The record has no ``section_authoring`` prompt and no renderer: a registry that changes
    either leaves the sealed Lane L record equal to the one it would write now."""
    first = _l_inputs(tmp_path / "a", prompts=_registry())
    second = _l_inputs(tmp_path / "b", prompts=_registry())
    other = PromptRegistry(
        {
            **second.prompts.manifests,
            "section_authoring": _registry("0" * 64, "section_authoring").manifests[
                "section_authoring"
            ],
        }
    )
    third = _l_inputs(tmp_path / "c", prompts=other)
    doc = json.loads(_staged(first)["dependencies.json"])
    assert evaluate(doc, json.loads(_staged(third)["dependencies.json"])).changes == ()
    # ... while the review prompt it DID consume reopens the reviewer scope, and only that.
    changed = _l_inputs(tmp_path / "d", prompts=_registry("0" * 64))
    (change,) = evaluate(doc, json.loads(_staged(changed)["dependencies.json"])).changes
    assert (change.dependency, change.scope) == (
        "prompts.independent_review",
        "reviewer",
    )


def test_a_lane_l_artifact_that_differs_with_no_changed_input_routes_to_the_correction_scope() -> (
    None
):
    assert route((), ["README.md"], "L").triggering_scope == "correction"
    assert route((), ["README.patch.diff"], "L").triggering_scope == "correction"
    assert route((), ["corrections.json"], "L").triggering_scope == "correction"
    assert route((), ["README.original.md"], "L").state == STATE_INVALIDATED
    assert route((), ["review_verdict.json"], "L").triggering_scope == "reviewer"
    # Lane R's mapping of the same names is what it was.
    assert route((), ["README.md"]).triggering_scope == "authoring"


def test_a_difference_in_a_proven_lane_l_bundle_is_recorded_as_a_correction_update(
    tmp_path: Path,
) -> None:
    inputs = _l_inputs(tmp_path)
    seal_candidate(inputs)
    fresh = _fresh_invocation(1)
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(_l_rerun(inputs, fresh))
    proven_readme = (proven.bundle / "README.md").read_bytes()

    (inputs.out_dir / "README.corrected.md").write_bytes(
        b"# Widget\n\nAnother correction.\n"
    )
    later = _fresh_invocation(2)
    _append_cache_reuse_record(inputs.out_dir, later.invocation_id)
    result = seal_candidate(_l_rerun(inputs, later))

    assert result.state == STATE_UPDATE_AVAILABLE
    manifest = json.loads(
        (result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["update"]["triggering_scope"] == "correction"
    assert "invalidated" not in manifest
    assert (
        result.bundle / "README.md"
    ).read_bytes() == proven_readme  # the proven content stands


# --- layout v1 stays layout v1 ----------------------------------------------------------------------------------


def test_a_sealed_layout_v1_bundle_is_rewritten_as_layout_v1_never_upgraded(
    tmp_path: Path,
) -> None:
    """Non-negotiable #3: the lane dimension never reseals a bundle for the sake of its layout. A
    bundle sealed before the dimension existed (schema 1, no lane) that is proven by a later rerun
    keeps writing schema 1 with no lane key."""
    inputs = _inputs(tmp_path)
    first = seal_candidate(inputs)
    manifest_path = first.bundle / BUNDLE_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2 and manifest["lane"] == "R"  # a new seal
    legacy = {k: v for k, v in manifest.items() if k != "lane"}
    legacy["schema_version"] = 1
    manifest_path.write_text(
        json.dumps(legacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    assert verify_bundle(first.bundle, LANE_R) is not None

    fresh = _fresh_invocation(3)
    _append_cache_reuse_record(inputs.out_dir, fresh.invocation_id)
    proven = seal_candidate(_rerun_inputs(inputs, invocation=fresh, provider_calls=0))

    assert proven.state == "READY_FOR_PROPOSAL"
    after = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert after["schema_version"] == 1 and "lane" not in after


def test_a_first_lane_r_seal_now_names_its_lane(tmp_path: Path) -> None:
    result = seal_candidate(_inputs(tmp_path))
    manifest = json.loads(
        (result.bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == 2 and manifest["lane"] == "R"
    assert result.bundle.parent.name != "lane-l"
