"""BL-087 (supervisor decision 2026-11-14, audit O3 P3): the findings register binds at authoring, not only at BC-18.

Real data: Aspose.HTML-FOSS-for-Python. Its sealed Lane R candidate's ``key_capabilities``
``capability:6`` says "an optional QuickJS-backed bridge exposing read-only DOM proxies to script
code", an OPEN register row since 2026-11-12; hosted run 43525324808 re-authored and printed it
again (BC-18), and the targeted repair returned it unchanged twice. The author now receives the row
as a do-not-claim record, and the section job rejects a unit that prints it, with the row's truth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.authoring import register_errors, register_records

HTML = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
QUOTE = "an optional QuickJS-backed bridge exposing read-only DOM proxies to script code"


@pytest.fixture(autouse=True)
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )


def _facts(repository: str) -> FactsDocument:
    return FactsDocument(repository, "bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11", ())


def test_the_packet_names_the_confirmed_false_claim_and_its_truth() -> None:
    records = register_records(_facts(HTML))
    row = next(r for r in records if r["value"] == QUOTE)
    assert row["kind"] == "confirmed_false_claim" and row["id"].startswith("finding:")
    assert "el.setAttribute" in row["truth"]


def test_a_unit_printing_the_claim_is_rejected_with_the_truth() -> None:
    unit = {"slot": "capability:6", "text": f"It runs scripts through {QUOTE}."}
    errors = register_errors([unit], _facts(HTML))
    assert len(errors) == 1 and "capability:6" in errors[0] and "writes through" in errors[0]


def test_ticks_do_not_hide_the_claim() -> None:
    unit = {"slot": "s", "text": "Use `css.parse` — parse selector and declaration text."}
    assert register_errors([unit], _facts(HTML))


def test_negative_controls() -> None:
    true_unit = {"slot": "capability:6", "text": "Scripts run through an optional QuickJS bridge."}
    assert register_errors([true_unit], _facts(HTML)) == []
    assert register_errors([{"slot": "c", "text": QUOTE}], _facts("other/repo")) == []
    assert register_records(_facts("other/repo")) == []
