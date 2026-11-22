"""BL-892: a kept unit's BC-07 reference sentence is withheld whether or not the restore placed the unit.

Real data: ``inherited_unit:589.paragraph`` of aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript at the sealed
revision 5fa17750 (numbered 592 at 851c1a6a), 'The PDF is not checked in ... Run the command above to produce
it, along with four siblings.'. Hosted run 45052413270 (R46 robust/reliable: a failure degrades the affected
sentence, never the candidate): S4 kept the paragraph in a section with no code before it, so BC-07 failed
BEFORE the restore as well as after it; BL-640 trimmed only a restored unit whose failure was new, so the
trim never ran, BC-07 stayed through the time-box, no LLM review was made, and nothing could be sealed
('a deterministic-only verdict is never sealed'). Zero provider calls here."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.references import dangling_references
from repo_presenter.readme.validation.must_correct import DEGRADE_WITHHELD_KEY, withheld_form

POINTER = "inherited_unit:589.paragraph"
OTHER = "inherited_unit:01.paragraph"
TEXT = (
    "The PDF is not checked in — it is regenerated on every run with fresh `/Info`\n"
    "dates, so tracking it would add a new 2.8 MB blob per commit for a document\n"
    "nobody edited. Run the command above to produce it, along with four siblings.\n"
    "All five are gitignored: `docs/feature-showcase.pdf` and its four siblings."
)
SENTENCE = "Run the command above to produce it, along with four siblings."
SECTION = "# X\n\n## Key Capabilities\n\n"


@dataclasses.dataclass(frozen=True)
class _Composed:
    plan: Any
    coherent_units: Any
    dispositions: Any
    readme: str
    tasks: Any
    accounted: Any
    planned_dispositions: Any = None


def _document() -> FactsDocument:
    def fact(unit: str, text: str) -> Fact:
        return Fact(
            id=unit, kind="inherited_unit", value=text, evidence=(Evidence("README.md", None),),  # type: ignore[arg-type]
            polarity="SUPPORTED", attributes={"section": "X"},  # type: ignore[arg-type]
        )

    return FactsDocument("o/r", "0" * 40, (fact(OTHER, "Maintainers' note."), fact(POINTER, TEXT)))


def _row(unit: str, disposition: str) -> dict[str, Any]:
    return {"unit_id": unit, "disposition": disposition, "destination_section": "key_capabilities", "fact_ids": []}


def _printed(dispositions: dict[str, Any]) -> str:
    row = next(r for r in dispositions["dispositions"] if r["unit_id"] == POINTER)
    return withheld_form(POINTER, TEXT, row.get(DEGRADE_WITHHELD_KEY) or [])


def _validate(candidate: Any, *a: Any, **k: Any) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    rows = {r["unit_id"]: r for r in candidate.dispositions["dispositions"]}
    if rows[OTHER]["disposition"] != "VERIFIED_PRESERVE":
        detail = f"{OTHER} is SUPERSEDE_REDUNDANT, but the README does not state it"
        checks.append({"id": "BC-05", "details": [detail], "failures": [{"detail": detail, "unit_id": OTHER}]})
    if rows[POINTER]["disposition"] == "VERIFIED_PRESERVE":
        failures = [
            {"unit_id": POINTER, "detail": f"{POINTER} is kept as written but {r.reason}: {r.sentence[:140]!r}"}
            for r in dangling_references(SECTION + _printed(candidate.dispositions) + "\n")
        ]
        if failures:
            checks.append({"id": "BC-07", "details": [f["detail"] for f in failures], "failures": failures})
    return {"checks": checks}


def _drive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rows: list[dict[str, Any]]
) -> tuple[Any, Any]:
    monkeypatch.setattr(cascade_module, "blocking_failures", lambda validation: validation["checks"])
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: {"key_capabilities"})
    monkeypatch.setattr(
        cascade_module, "choose_units",
        lambda details, doc, already, mandatory_checks=(), exclude=(): [
            unit for unit in (OTHER,) if unit not in already and unit not in exclude
            and any("BC-05" in d for d in details)
        ],
    )

    def restore(d, f, unit_ids, h, i=None, **k):  # noqa: ANN001, ANN202 - restore_lost_units' shape
        out = json.loads(json.dumps(d))
        changes = []
        for row in out["dispositions"]:
            if row["unit_id"] in unit_ids and row["disposition"] != "VERIFIED_PRESERVE":
                row["disposition"] = "VERIFIED_PRESERVE"
                changes.append({"unit_id": row["unit_id"], "was": "S -> x", "now": "V -> x"})
        return out, changes

    monkeypatch.setattr(cascade_module, "restore_lost_units", restore)
    monkeypatch.setattr(cascade_module, "colocate_pointed_blocks", lambda d, *a, **k: (d, []))
    monkeypatch.setattr(cascade_module, "render_readme", lambda *a, **k: "RESTORED README\n")
    monkeypatch.setattr(cascade_module, "authoring_tasks", lambda *a, **k: [])
    monkeypatch.setattr(
        cascade_module, "_candidate",
        lambda entry, doc, plan, units, dispositions, *a, **k: SimpleNamespace(dispositions=dispositions),
    )
    monkeypatch.setattr(cascade_module, "account_unprinted_units", lambda c: ({}, []))
    monkeypatch.setattr(cascade_module, "validate_candidate", _validate)
    monkeypatch.setattr(
        cascade_module, "review_candidate", lambda **k: SimpleNamespace(blocking_findings=())
    )
    monkeypatch.setattr(
        cascade_module, "write_dispositions", lambda d, p: Path(p).write_text("{}", encoding="utf-8")
    )
    monkeypatch.setattr(cascade_module, "write_review_verdict", lambda v, p: None)
    original = {"dispositions": rows}
    composed = _Composed(
        {"sections": [{"section_id": "key_capabilities", "include": True}]},
        {"units": []}, original, "OLD README\n", [], [],
    )
    before = _validate(SimpleNamespace(dispositions=original))
    settled = cascade_module._Settled(composed, before, SimpleNamespace(blocking_findings=()), 1)
    result = cascade_module._restore_lost_content(
        settled, entry=None, document=_document(), investigation={}, tree_paths=[], original="OLD\n",
        out_dir=tmp_path,
    )
    return settled, result


def test_real_paragraph_fails_bc07_as_kept_and_is_clean_once_the_sentence_is_withheld() -> None:
    assert any("command above" in r.reason for r in dangling_references(SECTION + TEXT + "\n"))
    printed = withheld_form(POINTER, TEXT, [SENTENCE])
    assert not dangling_references(SECTION + printed + "\n")
    assert "regenerated on every run" in printed and "All five are gitignored" in printed  # the rest stays


def test_a_kept_unit_already_failing_before_the_restore_is_trimmed_beside_a_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [_row(OTHER, "SUPERSEDE_REDUNDANT"), _row(POINTER, "VERIFIED_PRESERVE")]
    settled, result = _drive(monkeypatch, tmp_path, rows)
    assert [c["id"] for c in settled.validation["checks"]] == ["BC-05", "BC-07"]
    assert result.composed is not settled.composed
    assert result.validation["checks"] == []  # BC-05 restored, BC-07 trimmed: nothing blocking is left
    row = next(r for r in result.composed.dispositions["dispositions"] if r["unit_id"] == POINTER)
    assert row[DEGRADE_WITHHELD_KEY] == [SENTENCE]  # R14: recorded on the disposition
    record = json.loads((tmp_path / "restored_units.json").read_text(encoding="utf-8"))
    assert {c["unit_id"]: c.get("withheld") for c in record["restored"]}[POINTER] == SENTENCE


def test_bc07_alone_with_nothing_else_to_restore_is_still_answered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [_row(OTHER, "VERIFIED_PRESERVE"), _row(POINTER, "VERIFIED_PRESERVE")]
    settled, result = _drive(monkeypatch, tmp_path, rows)
    assert [c["id"] for c in settled.validation["checks"]] == ["BC-07"]
    assert result.composed is not settled.composed
    assert result.validation["checks"] == []
    row = next(r for r in result.composed.dispositions["dispositions"] if r["unit_id"] == POINTER)
    assert row[DEGRADE_WITHHELD_KEY] == [SENTENCE]


def test_negative_control_a_unit_that_is_not_kept_is_never_touched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [_row(OTHER, "VERIFIED_PRESERVE"), _row(POINTER, "OMIT_UNSUPPORTED")]
    settled, result = _drive(monkeypatch, tmp_path, rows)
    assert settled.validation["checks"] == [] and result.composed is settled.composed


def test_negative_control_a_failure_that_names_another_unit_is_not_withheld() -> None:
    dispositions = {"dispositions": [_row(OTHER, "VERIFIED_PRESERVE"), _row(POINTER, "VERIFIED_PRESERVE")]}
    failing = [{"id": "BC-07", "failures": [
        {"unit_id": OTHER, "detail": f"{OTHER} is kept as written but says 'command above' but no code precedes it "
                                     f"in this section: {SENTENCE!r}"}]}]
    restored: list[dict[str, str]] = []
    assert not cascade_module._withhold_pointing_sentences(dispositions, failing, _document(), restored)
    assert restored == [] and DEGRADE_WITHHELD_KEY not in dispositions["dispositions"][1]


def test_the_withholding_is_idempotent() -> None:
    dispositions = {"dispositions": [_row(OTHER, "VERIFIED_PRESERVE"), _row(POINTER, "VERIFIED_PRESERVE")]}
    failing = [{"id": "BC-07", "failures": [
        {"unit_id": POINTER, "detail": f"{POINTER} is kept as written but says 'command above' but no code precedes "
                                       f"it in this section: {SENTENCE!r}"}]}]
    restored: list[dict[str, str]] = []
    assert cascade_module._withhold_pointing_sentences(dispositions, failing, _document(), restored)
    assert not cascade_module._withhold_pointing_sentences(dispositions, failing, _document(), restored)
    assert len(restored) == 1
