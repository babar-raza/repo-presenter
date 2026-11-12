"""``_compose``/``_settle_s9``'s ``dispositions_override`` (cascade.py): a recompose that follows
a zero-call restore must keep the restore's reshaped dispositions instead of silently rebuilding
them from a fresh ``_run_reconciliation`` call -- see ``_compose``'s own docstring for the live
failure this closes (Aspose.Slides-FOSS-for-Cpp: a restore-merged "opening" authoring task was
re-split by the very next recompose, orphaning a model-review repair keyed against the merged
shape, so the repaired text never reached the rendered README and the model review came back from
cache byte-identical to the verdict the repair was meant to fix).

Everything _compose calls beyond S4 (planning, authoring, coherence, rendering) is replaced with a
trivial stand-in: this test is only about whether ``_run_reconciliation`` is skipped when an
override is given, and used verbatim when it is not.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.llm.jobs import JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.jobs import CallStore
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.repair.targeted import RepairLedger
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict
from tests.readme.composition.synthetic import make_entry, make_facts

PROMPTS_PATH = Path(__file__).resolve().parent.parent / "prompts"

FRESH_DISPOSITIONS = {"dispositions": [], "_tag": "fresh"}
RESTORED_DISPOSITIONS = {"dispositions": [], "_tag": "restored"}


@pytest.fixture
def stub_pipeline(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replace every _compose stage after S4 with a trivial, deterministic stand-in, and count
    ``_run_reconciliation`` calls."""
    reconciliation_calls: list[int] = []
    monkeypatch.setattr(
        cascade_module,
        "_run_reconciliation",
        lambda **kw: (reconciliation_calls.append(1), FRESH_DISPOSITIONS)[1],
    )
    monkeypatch.setattr(cascade_module, "_run_planning", lambda **kw: {"sections": []})
    monkeypatch.setattr(cascade_module, "_run_authoring", lambda **kw: {"units": []})
    monkeypatch.setattr(cascade_module, "_run_coherence", lambda **kw: {"units": []})
    monkeypatch.setattr(cascade_module, "render_readme", lambda *a, **kw: "README\n")
    monkeypatch.setattr(cascade_module, "authoring_tasks", lambda *a, **kw: [])
    monkeypatch.setattr(cascade_module, "validate_candidate", lambda *a, **kw: {})
    monkeypatch.setattr(
        cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(())
    )
    return reconciliation_calls


def _settle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    dispositions_override: dict[str, Any] | None,
):
    prompts = load_manifests(PROMPTS_PATH)
    entry = make_entry()
    document = make_facts()
    out_dir = tmp_path / "cascade"
    ledger = Ledger(out_dir / "llm_cache" / "ledger.jsonl")
    store = CallStore(out_dir / "llm_cache" / "calls")
    context = JobContext(repository=entry.repository, source_revision=document.source_revision)
    repairs = RepairLedger(out_dir / "repairs.json", composition="test-composition")
    return cascade_module._settle_s9(
        entry=entry,
        document=document,
        investigation={},
        ecosystem=entry.ecosystem,
        tree_paths=[],
        original_bytes=b"# Original\n",
        original="# Original\n",
        out_dir=out_dir,
        prompts=prompts,
        config=None,
        ledger=ledger,
        store=store,
        context=context,
        repairs=repairs,
        max_rounds=1,
        dispositions_override=dispositions_override,
    )


def test_an_override_is_used_verbatim_and_skips_reconciliation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_pipeline: list[int]
) -> None:
    settled = _settle(monkeypatch, tmp_path, dispositions_override=RESTORED_DISPOSITIONS)
    assert stub_pipeline == []
    assert settled.composed.dispositions == RESTORED_DISPOSITIONS


def test_no_override_falls_back_to_a_fresh_reconciliation_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_pipeline: list[int]
) -> None:
    settled = _settle(monkeypatch, tmp_path, dispositions_override=None)
    assert stub_pipeline == [1]
    assert settled.composed.dispositions == FRESH_DISPOSITIONS


def test_a_second_internal_round_ignores_the_first_rounds_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_pipeline: list[int]
) -> None:
    """``_settle_s9``'s own docstring: the override applies to round 1 only -- an S4 defect
    repaired inside this call's own loop genuinely changes dispositions, so round 2 must go back
    to a fresh ``_run_reconciliation`` rather than reapplying a now-stale override forever."""
    prompts = load_manifests(PROMPTS_PATH)
    entry = make_entry()
    document = make_facts()
    out_dir = tmp_path / "cascade"
    ledger = Ledger(out_dir / "llm_cache" / "ledger.jsonl")
    store = CallStore(out_dir / "llm_cache" / "calls")
    context = JobContext(repository=entry.repository, source_revision=document.source_revision)
    repairs = RepairLedger(out_dir / "repairs.json", composition="test-composition")

    rounds_seen: list[int] = []

    def fake_settle_defects(**kwargs: Any):
        rounds_seen.append(1)
        return [] if len(rounds_seen) > 1 else ["defect"]

    def fake_repair_defects(**kwargs: Any) -> bool:
        return True

    monkeypatch.setattr(cascade_module, "_settle_defects", fake_settle_defects)
    monkeypatch.setattr(cascade_module, "_repair_defects", fake_repair_defects)

    settled = cascade_module._settle_s9(
        entry=entry,
        document=document,
        investigation={},
        ecosystem=entry.ecosystem,
        tree_paths=[],
        original_bytes=b"# Original\n",
        original="# Original\n",
        out_dir=out_dir,
        prompts=prompts,
        config=None,
        ledger=ledger,
        store=store,
        context=context,
        repairs=repairs,
        max_rounds=3,
        dispositions_override=RESTORED_DISPOSITIONS,
    )
    # Round 1 used the override (no reconciliation call); round 2, triggered by the fake repair,
    # must have gone back to a fresh call.
    assert stub_pipeline == [1]
    assert settled.composed.dispositions == FRESH_DISPOSITIONS
