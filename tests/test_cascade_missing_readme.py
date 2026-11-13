"""R36: a repository with no README.md at its pinned revision is a valid Lane R input.

Real failing shape: aspose-gis-foss/Aspose.GIS.FOSS-for-.Net has no README.md at its pinned
revision; the cascade raised PresenterError "no README.md at the pinned revision ... nothing to
reconcile". Lane R writes a README, so an absent one is an empty inherited document: zero inherited
units, original text "", authored from facts alone -- and no step downstream (BC-17 parity, the
live-README loss rule, re-certification's source snapshot) may fail on it or invent a loss.

No network or provider call is made: the transport is the same scripted fake tests/test_cascade.py
uses, with its real replies minus the reconciliation call (zero units means zero batches).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from repo_presenter.cascade import (
    _document_with_inherited_units,
    _original_readme_bytes,
    run_cascade,
)
from repo_presenter.core.facts import read_facts, write_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.extractors.platforms.registry import plugin_for
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.test_cascade import (
    _AUTHORING_REPLIES,
    _INVESTIGATION_REPLY,
    _PLANNING_REPLY,
    CONFIG,
    _completion,
    _FakeClient,
    _write_registry,
)


@pytest.fixture(autouse=True)
def _fixed_git_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    import repo_presenter.cascade as cascade_module

    monkeypatch.setattr(
        cascade_module, "run_git", lambda *a, **k: SimpleNamespace(stdout="f" * 40 + "\n")
    )


@pytest.fixture
def bare_clone(tmp_path: Path) -> Path:
    clone = tmp_path / "clone"
    (clone / "src").mkdir(parents=True)
    (clone / "src" / "widget.py").write_text("class Widget: ...\n", encoding="utf-8")
    return clone


def test_missing_readme_is_an_empty_inherited_document(bare_clone: Path) -> None:
    assert _original_readme_bytes(bare_clone) == b""
    document = _document_with_inherited_units("o/n", make_facts(), "f" * 40, bare_clone)
    assert not document.by_kind("inherited_unit")
    # Every other fact is kept: the candidate is authored from facts alone.
    assert {f.id for f in document.facts} == {
        f.id for f in make_facts().facts if f.kind != "inherited_unit"
    }


def test_present_readme_is_still_read(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "README.md").write_bytes(b"# Title\n\nBody text.\n")
    assert _original_readme_bytes(clone) == b"# Title\n\nBody text.\n"


def test_empty_original_invents_no_parity_or_live_readme_loss() -> None:
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.readme import parity_gate as pg
    from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule

    candidate = "# Widget\n\n## Installation\n\n```bash\npip install widget\n```\n"
    assert pg.content_losses(pg.SealedCandidate("R", candidate, (), ()), "") == []
    facts = FactsDocument("o/n", "f" * 40, tuple(make_facts().facts))
    assert live_readme_loss_rule("", candidate, facts=facts, dispositions={"dispositions": []}) == []


def test_run_cascade_authors_a_readme_from_facts_when_the_repository_has_none(
    tmp_path: Path, bare_clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repo_presenter.readme.composition.authoring import merge_units

    plugin_for("python")
    entry = make_entry()
    facts_path = tmp_path / "facts.json"
    write_facts(make_facts(), facts_path)
    registry_path = tmp_path / "registry.json"
    _write_registry(registry_path, entry)
    out_dir = tmp_path / "out"

    # No inherited unit exists, so the investigation's limitation is authored from facts only
    # (the fixture's original reply cites the README's limitation paragraph instead).
    text = _AUTHORING_REPLIES[4]["units"][0]["text"]
    authoring = [
        *_AUTHORING_REPLIES[:4],
        {
            "units": [
                {"section": "scope_limitations", "slot": slot, "text": text,
                 "fact_ids": ["package:name"]}
                for slot in ("scope", "limitation:1")
            ],
            "omitted": [],
        },
    ]
    labels = ["opening", "key_capabilities", "quick_start", "api_reference", "scope_limitations"]
    merged = merge_units(dict(zip(labels, authoring)))
    replies = [
        _completion(_INVESTIGATION_REPLY),
        _completion(_PLANNING_REPLY),
        *[_completion(r) for r in authoring],
        _completion({"units": merged["units"], "omitted": []}),
    ]
    client = _FakeClient(replies)
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)

    result = run_cascade(
        entry.repository, "python", bare_clone, facts_path=facts_path, out_dir=out_dir,
        config=CONFIG, registry_path=registry_path, max_rounds=1,
    )

    # Zero reconciliation calls: investigation, planning, five authoring tasks, one coherence.
    assert result.provider_calls == 8
    assert not client.chat.completions.replies
    assert not read_facts(facts_path).by_kind("inherited_unit")
    readme = (out_dir / "README.coherent.md").read_text(encoding="utf-8")
    assert readme.strip()
    # Nothing was lost because nothing was inherited: no BC-17 / live-README failure.
    checks = {check["id"]: check for check in result.validation["checks"]}
    assert checks["BC-17"]["verdict"] == "PASS", checks["BC-17"]["details"]
    assert not [
        f for f in result.review_verdict.findings if getattr(f, "rule", "") == "live_readme_loss"
    ]
