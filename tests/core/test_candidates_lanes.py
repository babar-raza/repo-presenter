"""The lane dimension of the sealed-bundle layout (plans/PLAN_lane_l_hosted.md L6, L7).

Two equal lanes share one ``candidates/<slug>/`` tree: layout v1 (every bundle sealed before the
dimension existed) is Lane R and is never moved or edited; Lane L lives in ``lane-l/`` beside it.
The tests pin both halves of that: the real committed Lane R bundle is byte-for-byte what it was
and still reads as Lane R, and nothing one lane writes is visible to, counted by, or able to
overwrite the other.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repo_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CORRUPT_BUNDLE,
    CURRENT_FILENAME,
    LANE_L,
    LANE_R,
    NO_BUNDLE,
    BundleError,
    SealedBundle,
    count_current_candidates,
    counted_by_lane,
    current_counted_repository_dirs,
    integrity_valid_candidates,
    iter_sealed_bundles,
    lane_directory,
    manifest_lane,
    portfolio_status,
    ready_revision,
    stale_candidates,
    verify_bundle,
)

REPOSITORY = "org/Aspose.Widget-FOSS-for-Python"
SLUG = "org__Aspose.Widget-FOSS-for-Python"
REVISION = "a" * 40
OTHER_REVISION = "b" * 40
REPO_ROOT = Path(__file__).resolve().parents[2]

# The one sealed Lane R bundle committed to this repository, pinned by the digest of its manifest
# and of its CURRENT pointer. A reseal, an edit or a move changes these and fails this test: the
# lane dimension must read the bundle as it is, never rewrite it (mission non-negotiable #3).
COMMITTED_SLUG = "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
COMMITTED_REVISION = "52b0f00ebf28a0b4173921725ff170685ec2c502"
COMMITTED_MANIFEST_SHA256 = (
    "ce4d6fb24090cdc084048c3e1d03b3d10a6739f4265870de080e73183df1cbc2"
)
COMMITTED_CURRENT_SHA256 = (
    "d49d3ed2456a23a11c8223205982838aaa7e0bc7388b2115ccfc6c3de4369799"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seal(
    root: Path,
    lane: str,
    *,
    revision: str = REVISION,
    state: str = "READY_FOR_PROPOSAL",
    schema_version: int | None = None,
    declared_lane: str | None = None,
    slug: str = SLUG,
    repository: str = REPOSITORY,
) -> Path:
    """A self-consistent bundle written straight into ``lane``'s tree. ``schema_version`` defaults
    to what the sealer writes for that lane (Lane R: the legacy 1 when asked, else 2)."""
    version = schema_version if schema_version is not None else 2
    lane_root = lane_directory(root / "candidates" / slug, lane)
    bundle = lane_root / revision
    bundle.mkdir(parents=True, exist_ok=True)
    data = f"# {lane} candidate\n".encode()
    (bundle / "README.md").write_bytes(data)
    manifest: dict[str, object] = {
        "schema_version": version,
        "repository": repository,
        "revision": revision,
        "state": state,
        "files": {"README.md": {"sha256": _sha256(data), "bytes": len(data)}},
    }
    if version == 2:
        manifest["lane"] = declared_lane or lane
    (bundle / BUNDLE_MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    (lane_root / CURRENT_FILENAME).write_text(f"{revision}\n", encoding="utf-8")
    return bundle


# --- the committed layout-v1 bundle is Lane R and is untouched ------------------------------------


def test_the_committed_bundle_is_byte_for_byte_what_was_sealed() -> None:
    bundle = REPO_ROOT / "candidates" / COMMITTED_SLUG
    manifest = bundle / COMMITTED_REVISION / BUNDLE_MANIFEST_NAME
    assert _sha256(manifest.read_bytes()) == COMMITTED_MANIFEST_SHA256
    assert _sha256((bundle / CURRENT_FILENAME).read_bytes()) == COMMITTED_CURRENT_SHA256


def test_the_committed_layout_v1_bundle_reads_as_lane_r_through_the_versioned_reader() -> (
    None
):
    bundle = REPO_ROOT / "candidates" / COMMITTED_SLUG / COMMITTED_REVISION
    manifest = verify_bundle(bundle, LANE_R)
    assert manifest is not None
    assert manifest["schema_version"] == 1 and "lane" not in manifest
    assert manifest_lane(manifest) == LANE_R
    with pytest.raises(BundleError, match="Lane L tree declares Lane R"):
        verify_bundle(bundle, LANE_L)


def test_the_real_candidates_tree_reports_both_lanes_and_counts_each_on_its_own() -> (
    None
):
    rows = {(row.repository_dir, row.lane): row for row in portfolio_status(REPO_ROOT)}
    committed = rows[(COMMITTED_SLUG, LANE_R)]
    assert committed.status == "READY_FOR_PROPOSAL" and committed.counted
    assert committed.revision == COMMITTED_REVISION
    assert rows[(COMMITTED_SLUG, LANE_L)].status == NO_BUNDLE
    python_slug = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    assert rows[(python_slug, LANE_R)].status == NO_BUNDLE  # it holds probes.json only
    assert counted_by_lane(list(rows.values())) == {LANE_R: 1, LANE_L: 0}
    assert count_current_candidates(REPO_ROOT) == 1
    assert count_current_candidates(REPO_ROOT, LANE_L) == 0


# --- the versioned reader ---------------------------------------------------------------------------


def test_a_schema_1_manifest_is_lane_r_and_a_schema_2_manifest_names_its_lane(
    tmp_path: Path,
) -> None:
    legacy = seal(
        tmp_path, LANE_R, schema_version=1, slug="a__legacy", repository="a/legacy"
    )
    modern_r = seal(tmp_path, LANE_R, slug="a__modern", repository="a/modern")
    modern_l = seal(tmp_path, LANE_L, slug="a__modern", repository="a/modern")
    assert manifest_lane(verify_bundle(legacy, LANE_R)) == LANE_R  # type: ignore[arg-type]
    assert manifest_lane(verify_bundle(modern_r, LANE_R)) == LANE_R  # type: ignore[arg-type]
    assert manifest_lane(verify_bundle(modern_l, LANE_L)) == LANE_L  # type: ignore[arg-type]


def test_a_manifest_in_the_wrong_lane_tree_is_corrupt_evidence_not_a_candidate(
    tmp_path: Path,
) -> None:
    lane_l_in_r = seal(tmp_path, LANE_R, declared_lane=LANE_L)
    with pytest.raises(BundleError, match="Lane R tree declares Lane L"):
        verify_bundle(lane_l_in_r, LANE_R)
    with pytest.raises(BundleError, match="Lane R tree declares Lane L"):
        count_current_candidates(tmp_path)

    lane_r_in_l = seal(tmp_path / "other", LANE_L, declared_lane=LANE_R)
    with pytest.raises(BundleError, match="Lane L tree declares Lane R"):
        verify_bundle(lane_r_in_l, LANE_L)


def test_a_legacy_manifest_can_never_stand_in_the_lane_l_tree(tmp_path: Path) -> None:
    bundle = seal(tmp_path, LANE_L, schema_version=1)
    with pytest.raises(BundleError, match="Lane L tree declares Lane R"):
        verify_bundle(bundle, LANE_L)


def test_a_schema_2_manifest_with_an_unknown_lane_fails_closed(tmp_path: Path) -> None:
    bundle = seal(tmp_path, LANE_R, declared_lane="X")
    with pytest.raises(BundleError, match="unknown lane"):
        verify_bundle(bundle, LANE_R)


def test_an_unknown_lane_is_a_caller_defect() -> None:
    with pytest.raises(ValueError, match="unknown lane"):
        lane_directory(Path("candidates") / SLUG, "X")


# --- isolation: one lane never sees, counts or overwrites the other -----------------------------------


def test_each_lane_has_its_own_current_pointer_and_its_own_count(
    tmp_path: Path,
) -> None:
    seal(tmp_path, LANE_R, revision=REVISION)
    seal(tmp_path, LANE_L, revision=OTHER_REVISION, state="ACCEPTED")
    root = tmp_path / "candidates" / SLUG
    assert (root / CURRENT_FILENAME).read_text(encoding="utf-8").strip() == REVISION
    assert (root / "lane-l" / CURRENT_FILENAME).read_text(encoding="utf-8").strip() == (
        OTHER_REVISION
    )
    assert ready_revision(tmp_path, REPOSITORY, LANE_R) == REVISION
    assert (
        ready_revision(tmp_path, REPOSITORY, LANE_L) is None
    )  # ACCEPTED is not counted
    assert current_counted_repository_dirs(tmp_path, LANE_R) == {SLUG}
    assert current_counted_repository_dirs(tmp_path, LANE_L) == set()
    assert integrity_valid_candidates(tmp_path, LANE_R) == 1
    assert integrity_valid_candidates(tmp_path, LANE_L) == 1


def test_a_lane_l_seal_leaves_the_lane_r_bundle_and_pointer_byte_identical(
    tmp_path: Path,
) -> None:
    r_bundle = seal(tmp_path, LANE_R)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "candidates").rglob("*")
        if path.is_file()
    }
    seal(tmp_path, LANE_L, revision=OTHER_REVISION)
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "candidates").rglob("*")
        if path.is_file() and "lane-l" not in path.parts
    }
    assert after == before
    assert r_bundle.is_dir()


def test_the_lane_directory_is_never_read_as_a_revision(tmp_path: Path) -> None:
    seal(tmp_path, LANE_R)
    seal(tmp_path, LANE_L, revision=OTHER_REVISION)
    bundles = list(iter_sealed_bundles(tmp_path))
    assert bundles == [
        SealedBundle(SLUG, REVISION, "READY_FOR_PROPOSAL", LANE_R),
        SealedBundle(SLUG, OTHER_REVISION, "READY_FOR_PROPOSAL", LANE_L),
    ]


def test_the_one_status_model_lists_both_lanes_even_when_only_one_has_sealed(
    tmp_path: Path,
) -> None:
    seal(tmp_path, LANE_L, slug="o__only-l", repository="o/only-l")
    seal(tmp_path, LANE_R, slug="o__only-r", repository="o/only-r")
    rows = [
        (row.repository_dir, row.lane, row.status) for row in portfolio_status(tmp_path)
    ]
    assert rows == [
        ("o__only-l", LANE_R, NO_BUNDLE),
        ("o__only-l", LANE_L, "READY_FOR_PROPOSAL"),
        ("o__only-r", LANE_R, "READY_FOR_PROPOSAL"),
        ("o__only-r", LANE_L, NO_BUNDLE),
    ]
    assert counted_by_lane(portfolio_status(tmp_path)) == {LANE_R: 1, LANE_L: 1}


def test_a_corrupt_bundle_in_one_lane_is_shown_and_never_hides_the_other_lane(
    tmp_path: Path,
) -> None:
    seal(tmp_path, LANE_R)
    broken = seal(tmp_path, LANE_L, revision=OTHER_REVISION)
    (broken / "README.md").write_bytes(b"tampered after sealing\n")
    rows = {row.lane: row for row in portfolio_status(tmp_path)}
    assert rows[LANE_R].status == "READY_FOR_PROPOSAL" and rows[LANE_R].counted
    assert rows[LANE_L].status == CORRUPT_BUNDLE and not rows[LANE_L].counted
    assert "corrupt" in (rows[LANE_L].detail or "")
    with pytest.raises(BundleError):
        count_current_candidates(tmp_path, LANE_L)  # the counting contract still raises
    assert count_current_candidates(tmp_path, LANE_R) == 1


def test_staleness_is_judged_per_lane(tmp_path: Path) -> None:
    for lane, version in ((LANE_R, "1"), (LANE_L, "7")):
        bundle = seal(tmp_path, lane)
        (bundle / "dependencies.json").write_text(
            json.dumps({"components": {"renderer": version}}), encoding="utf-8"
        )
    assert [
        c.reasons for c in stale_candidates(tmp_path, {"renderer": "2"}, LANE_R)
    ] == [("components.renderer 1 -> 2",)]
    assert [
        c.reasons for c in stale_candidates(tmp_path, {"renderer": "7"}, LANE_L)
    ] == []
