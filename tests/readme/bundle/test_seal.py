"""seal.py v1: the first seal of a cascade's real output into a durable bundle.

Scope matches readme.bundle.seal's own module docstring: only the first seal (state ACCEPTED,
no_op_proof None). Re-seal / update-adoption is not built yet and must raise NotImplementedError,
the same pattern readme.bundle.recheck's own recheck_bundle/recheck_portfolio already use.
"""

from __future__ import annotations

import json
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
from repo_presenter.core.noop_proof import Invocation
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


def test_seal_candidate_raises_not_implemented_against_an_already_sealed_bundle(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    seal_candidate(inputs)
    with pytest.raises(NotImplementedError, match="already sealed"):
        seal_candidate(inputs)


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
