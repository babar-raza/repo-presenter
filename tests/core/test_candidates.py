"""The bundle-integrity/counting tier of core/candidates.py.

Adapted (REUSE of structure and test names, not verbatim -- the old repository-presenter
project's tests/core/test_candidates.py is 703 lines and most of it exercises the
proposal-gate/review-refusal tier, not ported here; see core/candidates.py's own module
docstring) from that file's "pure bundle-integrity" section.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CURRENT_FILENAME,
    BundleError,
    BundleLedgerError,
    SealedBundle,
    StaleCandidate,
    count_current_candidates,
    current_counted_repository_dirs,
    integrity_valid_candidates,
    iter_sealed_bundles,
    ready_revision,
    ready_revision_at,
    stale_candidates,
    verify_bundle,
)

REPOSITORY = "org/Aspose.Widget-FOSS-for-Python"
REPO_DIR = "org__Aspose.Widget-FOSS-for-Python"
REVISION = "a" * 40


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _seal(
    root: Path,
    *,
    repository: str = REPOSITORY,
    repo_dir: str = REPO_DIR,
    revision: str = REVISION,
    state: str = "READY_FOR_PROPOSAL",
    files: dict[str, bytes] | None = None,
    manifest_overrides: dict | None = None,
    set_current: bool = True,
) -> Path:
    """Write a real, self-consistent bundle directly (not via seal_candidate, so a test can
    produce a READY_FOR_PROPOSAL bundle -- a state seal.py v1 never writes itself yet)."""
    bundle = root / "candidates" / repo_dir / revision
    files = files or {"README.md": b"# Widget\n"}
    for name, data in files.items():
        _write_file(bundle / name, data)
    manifest = {
        "schema_version": 1,
        "repository": repository,
        "revision": revision,
        "state": state,
        "files": {
            name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in files.items()
        },
        **(manifest_overrides or {}),
    }
    _write_file(bundle / BUNDLE_MANIFEST_NAME, json.dumps(manifest).encode("utf-8"))
    if set_current:
        (bundle.parent / CURRENT_FILENAME).write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def test_missing_candidates_directory_counts_zero(tmp_path: Path) -> None:
    assert count_current_candidates(tmp_path) == 0
    assert integrity_valid_candidates(tmp_path) == 0
    assert list(iter_sealed_bundles(tmp_path)) == []
    assert stale_candidates(tmp_path, {}) == []


def test_iter_sealed_bundles_is_ordered_and_skips_unsealed(tmp_path: Path) -> None:
    _seal(tmp_path, revision="a" * 40, state="ACCEPTED", set_current=False)
    _seal(tmp_path, revision="b" * 40, state="READY_FOR_PROPOSAL", set_current=False)
    (tmp_path / "candidates" / REPO_DIR / ("c" * 40)).mkdir(parents=True)  # no manifest at all

    bundles = list(iter_sealed_bundles(tmp_path))
    assert bundles == [
        SealedBundle(REPO_DIR, "a" * 40, "ACCEPTED"),
        SealedBundle(REPO_DIR, "b" * 40, "READY_FOR_PROPOSAL"),
    ]


def test_count_is_per_repository_and_only_counted_states(tmp_path: Path) -> None:
    _seal(tmp_path, repo_dir="owner__ready", repository="owner/ready", state="READY_FOR_PROPOSAL")
    _seal(tmp_path, repo_dir="owner__accepted", repository="owner/accepted", state="ACCEPTED")
    assert count_current_candidates(tmp_path) == 1
    assert current_counted_repository_dirs(tmp_path) == {"owner__ready"}


@pytest.mark.parametrize(
    "raw,message",
    [
        ("not json", "unreadable"),
        ("[]", "is not an object"),
        ('{"schema_version": 1}', "has no state"),
    ],
)
def test_corrupt_manifest_is_an_error(tmp_path: Path, raw: str, message: str) -> None:
    bundle = tmp_path / "candidates" / REPO_DIR / REVISION
    _write_file(bundle / BUNDLE_MANIFEST_NAME, raw.encode("utf-8"))
    with pytest.raises(BundleError, match=message):
        verify_bundle(bundle)


def test_a_repository_with_no_current_file_is_silently_not_counted(tmp_path: Path) -> None:
    _seal(tmp_path, state="READY_FOR_PROPOSAL", set_current=False)
    assert count_current_candidates(tmp_path) == 0


def test_current_naming_a_revision_with_no_bundle_is_an_error(tmp_path: Path) -> None:
    repo_dir = tmp_path / "candidates" / REPO_DIR
    repo_dir.mkdir(parents=True)
    (repo_dir / CURRENT_FILENAME).write_text(f"{REVISION}\n", encoding="utf-8")
    with pytest.raises(BundleError, match="no sealed"):
        count_current_candidates(tmp_path)


def test_an_older_ready_sibling_that_is_not_current_is_not_counted(tmp_path: Path) -> None:
    _seal(tmp_path, revision="a" * 40, state="READY_FOR_PROPOSAL", set_current=False)
    _seal(tmp_path, revision="b" * 40, state="ACCEPTED", set_current=True)
    assert count_current_candidates(tmp_path) == 0


def test_verify_bundle_rejects_an_unsupported_schema_version(tmp_path: Path) -> None:
    bundle = _seal(tmp_path, manifest_overrides={"schema_version": 2})
    with pytest.raises(BundleError, match="unsupported schema_version"):
        verify_bundle(bundle)


def test_verify_bundle_rejects_an_empty_inventory(tmp_path: Path) -> None:
    bundle = tmp_path / "candidates" / REPO_DIR / REVISION
    _write_file(
        bundle / BUNDLE_MANIFEST_NAME,
        json.dumps({"schema_version": 1, "state": "ACCEPTED", "files": {}}).encode("utf-8"),
    )
    with pytest.raises(BundleError, match="no files"):
        verify_bundle(bundle)


def test_count_current_candidates_rejects_a_manifest_whose_revision_disagrees_with_current(
    tmp_path: Path,
) -> None:
    _seal(tmp_path, manifest_overrides={"revision": "f" * 40})
    with pytest.raises(BundleError, match="does not match CURRENT"):
        count_current_candidates(tmp_path)


def test_count_current_candidates_rejects_a_manifest_whose_repository_disagrees_with_its_directory(
    tmp_path: Path,
) -> None:
    _seal(tmp_path, manifest_overrides={"repository": "someone/else"})
    with pytest.raises(BundleError, match="does not match its directory"):
        count_current_candidates(tmp_path)


def test_stale_candidates_reports_every_component_behind_current(tmp_path: Path) -> None:
    bundle = _seal(tmp_path)
    _write_file(
        bundle / "dependencies.json",
        json.dumps({"components": {"renderer": "33", "shell": "6"}}).encode("utf-8"),
    )
    stale = stale_candidates(tmp_path, {"renderer": "34", "shell": "6"})
    assert stale == [StaleCandidate(REPO_DIR, REVISION, ("components.renderer 33 -> 34",))]


def test_stale_candidates_ignores_a_dependency_the_running_code_has_never_heard_of(
    tmp_path: Path,
) -> None:
    bundle = _seal(tmp_path)
    _write_file(
        bundle / "dependencies.json", json.dumps({"components": {"renderer": "33"}}).encode("utf-8")
    )
    assert stale_candidates(tmp_path, {}) == []


def test_stale_candidates_skips_a_candidate_with_no_dependencies_file_or_no_current_pointer(
    tmp_path: Path,
) -> None:
    _seal(tmp_path, repo_dir="owner__no_current", set_current=False)
    _seal(tmp_path, repo_dir="owner__no_deps", repository="owner/no_deps")
    assert stale_candidates(tmp_path, {"renderer": "99"}) == []


def test_verify_bundle_none_without_a_bundle_and_rejects_a_missing_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "candidates" / REPO_DIR / REVISION
    assert verify_bundle(bundle) is None
    sealed = _seal(tmp_path)
    (sealed / "README.md").unlink()
    with pytest.raises(BundleError, match="missing"):
        verify_bundle(sealed)


def test_verify_bundle_rejects_a_corrupt_artifact(tmp_path: Path) -> None:
    bundle = _seal(tmp_path)
    (bundle / "README.md").write_bytes(b"tampered")
    with pytest.raises(BundleError, match="corrupt"):
        verify_bundle(bundle)


def test_integrity_valid_candidates_with_no_candidates_directory_is_zero(tmp_path: Path) -> None:
    assert integrity_valid_candidates(tmp_path) == 0


def test_integrity_valid_candidates_counts_only_current_bundles_that_pass_verification(
    tmp_path: Path,
) -> None:
    _seal(tmp_path, repo_dir="owner__good")
    bad = _seal(tmp_path, repo_dir="owner__bad", repository="owner/bad")
    (bad / "README.md").unlink()
    assert integrity_valid_candidates(tmp_path) == 1


def test_integrity_valid_candidates_does_not_raise_on_a_current_naming_no_bundle(
    tmp_path: Path,
) -> None:
    repo_dir = tmp_path / "candidates" / REPO_DIR
    repo_dir.mkdir(parents=True)
    (repo_dir / CURRENT_FILENAME).write_text(f"{REVISION}\n", encoding="utf-8")
    assert integrity_valid_candidates(tmp_path) == 0


def test_ready_revision_names_the_current_revision_only_when_it_is_ready(tmp_path: Path) -> None:
    _seal(tmp_path, state="READY_FOR_PROPOSAL")
    assert ready_revision(tmp_path, REPOSITORY) == REVISION


@pytest.mark.parametrize("state", ["ACCEPTED", "VALID_UPDATE_AVAILABLE", "INVALIDATED"])
def test_ready_revision_refuses_a_non_ready_bundle(tmp_path: Path, state: str) -> None:
    _seal(tmp_path, state=state)
    assert ready_revision(tmp_path, REPOSITORY) is None


def test_ready_revision_is_none_for_an_absent_repository(tmp_path: Path) -> None:
    assert ready_revision(tmp_path, REPOSITORY) is None


def test_ready_revision_fails_closed_on_a_corrupt_current_bundle(tmp_path: Path) -> None:
    _seal(tmp_path, manifest_overrides={"repository": "someone/else"})
    with pytest.raises(BundleError):
        ready_revision(tmp_path, REPOSITORY)


def test_ready_revision_at_names_the_revision_for_a_matching_repository(tmp_path: Path) -> None:
    bundle = _seal(tmp_path, state="READY_FOR_PROPOSAL")
    assert ready_revision_at(bundle.parent, REPOSITORY) == REVISION


def test_ready_revision_at_is_none_for_a_missing_or_not_ready_bundle(tmp_path: Path) -> None:
    assert ready_revision_at(tmp_path / "nowhere", REPOSITORY) is None
    bundle = _seal(tmp_path, state="ACCEPTED")
    assert ready_revision_at(bundle.parent, REPOSITORY) is None


def test_ready_revision_at_rejects_a_bundle_claiming_a_different_repository(tmp_path: Path) -> None:
    bundle = _seal(tmp_path, state="READY_FOR_PROPOSAL")
    with pytest.raises(BundleError, match="does not match"):
        ready_revision_at(bundle.parent, "someone/else")


def test_ready_revision_at_fails_closed_on_a_corrupt_bundle(tmp_path: Path) -> None:
    bundle = _seal(tmp_path, state="READY_FOR_PROPOSAL")
    (bundle / "README.md").unlink()
    with pytest.raises(BundleError):
        ready_revision_at(bundle.parent, REPOSITORY)


def test_verify_bundle_reconciles_ledger_totals_when_present(tmp_path: Path) -> None:
    """The one real new check beyond the old repo's own verify_bundle: when a manifest records
    ledger_totals, they must equal the sums over its real ledger.jsonl (core/noop_proof.py,
    wired here exactly as readme/bundle/seal.py's own _write_bundle already does)."""
    record = {
        "attempt": 1, "call_id": "a-01-success-1", "completion_tokens": 5,
        "derived_via_reask": False, "disposition": "provider_call", "effective_model": "m",
        "error_class": None, "finished_at": "2026-10-26T00:00:01Z", "http_status": 200,
        "invocation_id": "inv1", "job": "x", "latency_ms": 10, "logical_call_id": "a",
        "max_tokens": 100, "model_route": "m", "model_served": "m", "outcome": "success",
        "prompt_sha256": "a" * 64, "prompt_tokens": 5, "provider_request_id": "r",
        "rejection": [], "repository": REPOSITORY, "request_sha256": "a" * 64,
        "response_format": "json_schema", "response_sha256": "b" * 64, "retained_reason": None,
        "schema_version": 1, "source_revision": REVISION, "stage": "S3",
        "started_at": "2026-10-26T00:00:00Z", "temperature": 0.0, "total_tokens": 10,
    }
    ledger_bytes = (json.dumps(record) + "\n").encode("utf-8")
    bundle = _seal(
        tmp_path,
        files={"README.md": b"# Widget\n", "ledger.jsonl": ledger_bytes},
        manifest_overrides={
            "provider_calls": 1,
            "sealed_by": {"invocation_id": "inv1"},
            "ledger_totals": {"provider_calls": 1, "cache_reuses": 0, "audit_only": 0,
                               "records": 1, "total_tokens": 10},
        },
    )
    assert verify_bundle(bundle) is not None  # does not raise

    tampered = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    tampered["ledger_totals"]["provider_calls"] = 99
    (bundle / BUNDLE_MANIFEST_NAME).write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(BundleLedgerError):
        verify_bundle(bundle)
