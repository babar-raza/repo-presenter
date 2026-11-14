"""BL-065: a re-certified seal carries the facts narrowed to the packages the build ships.

Kept apart from ``tests/test_recertify.py`` (a checker file of TC-024's receipt) and reusing its sealed
Lane L fixture, so this change does not invalidate that card's verification.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from repo_presenter import recertify
from repo_presenter.core.candidates import LANE_L
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.recertify import OUTCOME_RECERTIFIED
from tests.test_recertify import PROMPTS, entry, no_provider, seal_lane_l, source  # noqa: F401 -- fixture


def test_a_narrowed_surface_rides_along_as_the_recertified_seals_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]  # noqa: F811
) -> None:
    """When ``shipped_facts`` drops tree-package facts the build never ships, the re-certified seal
    stores the narrowed ``facts.json`` and its dependencies record those facts; with nothing to drop
    the sealed ``facts.json`` is copied byte for byte (negative control)."""
    bundle = seal_lane_l(tmp_path, monkeypatch)
    prompts = load_manifests(PROMPTS)
    plain = recertify.recertify_bundle(bundle, LANE_L, entry=entry(), source=source())
    assert "facts.json" not in plain.artifacts
    written = recertify.write_recertified(bundle, plain, candidates_root=tmp_path / "plain", prompts=prompts)
    assert (written / "facts.json").read_bytes() == (bundle / "facts.json").read_bytes()

    sealed = recertify.read_facts(bundle / "facts.json")
    dropped = next(f for f in sealed.facts if f.kind == "public_symbol")

    def narrow(document, _ecosystem, _source):
        kept = tuple(f for f in document.facts if f.id != dropped.id)
        if len(kept) == len(document.facts):
            return document, None
        return replace(document, facts=kept), "tool.hatch.build.targets.wheel.packages"

    monkeypatch.setattr(recertify, "shipped_facts", narrow)
    rec = recertify.recertify_bundle(bundle, LANE_L, entry=entry(), source=source())
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    assert "facts.json" in rec.artifacts
    written = recertify.write_recertified(bundle, rec, candidates_root=tmp_path / "narrowed", prompts=prompts)
    stored = recertify.read_facts(written / "facts.json")
    assert dropped.id not in {f.id for f in stored.facts} and len(stored.facts) == len(sealed.facts) - 1
    deps = json.loads((written / "dependencies.json").read_text(encoding="utf-8"))
    assert set(deps["facts"]) == {f.id for f in stored.facts}
    assert recertify.verify_bundle(written, LANE_L) is not None
