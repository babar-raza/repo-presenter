"""The harness re-renders a candidate offline, so it must register the entry's ecosystem spec the
way every cascade stage does (``plugin_for``); without it a java, go, cpp, rust or typescript
candidate fails with ``ConfigError: no ecosystem spec registered`` and can never be a corpus base."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.readme.review.calibration import sources
from tests.readme.composition.synthetic import make_entry
from tests.readme.review.calibration.synthetic import FACTS, ORIGINAL


class Registered(Exception):
    def __init__(self, ecosystem: str) -> None:
        super().__init__(ecosystem)
        self.ecosystem = ecosystem


def test_build_source_registers_the_entrys_ecosystem_before_it_renders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def record(ecosystem: str) -> None:
        raise Registered(ecosystem)

    monkeypatch.setattr(sources, "plugin_for", record)
    entry = make_entry()
    with pytest.raises(Registered) as raised:
        sources.build_source(
            name="x",
            entry=entry,
            facts=FACTS,
            plan={},
            units={},
            dispositions={},
            investigation={},
            original=ORIGINAL,
            tree_paths=[],
            scratch=tmp_path,
        )
    assert raised.value.ecosystem == entry.ecosystem


def test_a_recorded_readme_is_used_as_written_and_needs_no_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sources, "plugin_for", lambda ecosystem: pytest.fail("no render, no spec")
    )
    source = sources.build_source(
        name="x",
        entry=make_entry(),
        facts=FACTS,
        plan={},
        units={},
        dispositions={},
        investigation={},
        original=ORIGINAL,
        tree_paths=[],
        scratch=tmp_path,
        recorded_readme="# x\n",
    )
    assert source.readme == "# x\n"
