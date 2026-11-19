"""BL-310: a kept unit the README does not print is re-homed by the restore, not left to a repair.

The finding texts are the hosted Lane R run 44397309353 (Aspose-PDF-FOSS-for-Python), where ten
``disposition_coverage`` findings of one kind stayed and the model repair refused them twice
("uncited_prose_omit: OMIT_UNSUPPORTED on a code_block needs at least one fact ID ...")::

    inherited_unit:142.code_block is kept (VERIFIED_PRESERVE) but its text is not printed in the README

The keep was recorded and never took effect: the unit is filed in a section that does not print its
kind, or in one the plan omits. ``restore_units`` already re-homes a unit BC-05/BC-17 name; the
reviewer's finding names the same units, so they are fed to the same re-home (R14: the record is the
restore's ``{unit_id, was, now}``, the text is unchanged).
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter import cascade
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.destinations import prints_unit
from repo_presenter.readme.repair.restore_units import restore_lost_units
from repo_presenter.readme.review.independent_reviewer import disposition_coverage_rule

UNIT = "inherited_unit:142.code_block"
CODE = (
    '```python\nwith Document("manual.pdf") as document:\n'
    '    document.export_bookmarks_csv("bookmarks.csv", encoding="utf-8-sig")\n\n'
    'with Document("updated-manual.pdf") as document:\n'
    '    added = document.import_bookmarks_csv("bookmarks.csv", replace=True)\n'
    '    document.save("with-bookmarks.pdf")\n```'
)
HEADING = "inherited_unit:138.heading"
_EV = (Evidence("README.md", "lines 1-1"),)
README = "# Aspose.PDF FOSS for Python\n\nAspose.PDF reads and writes PDF documents.\n"


def _facts() -> FactsDocument:
    return FactsDocument(
        "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python",
        "0c756ef9" + "0" * 32,
        (
            Fact("identity:repository", "identity", "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python", _EV),
            Fact(UNIT, "inherited_unit", CODE, _EV, attributes={"section": "Bookmarks"}),
            Fact(HEADING, "inherited_unit", "### Exchange Bookmarks as JSON", _EV,
                 attributes={"section": "Bookmarks"}),
        ),
    )


def _dispositions(destination: str) -> dict:
    return {
        "dispositions": [
            {"unit_id": UNIT, "disposition": "VERIFIED_PRESERVE", "destination_section": destination,
             "fact_ids": [], "rationale": "Kept as written."},
            {"unit_id": HEADING, "disposition": "VERIFIED_MOVE", "destination_section": destination,
             "fact_ids": [], "rationale": "Kept."},
        ]
    }


def _findings(dispositions: dict, readme: str = README) -> list[str]:
    return [
        f.message
        for f in disposition_coverage_rule(readme, facts=_facts(), dispositions=dispositions)
    ]


def test_the_findings_are_the_hosted_texts_and_the_restore_rehomes_the_unit() -> None:
    dispositions = _dispositions("api_reference")  # a section that prints no code block
    assert not prints_unit("api_reference", "code_block")
    messages = _findings(dispositions)
    assert f"{UNIT} is kept (VERIFIED_PRESERVE) but its text is not printed in the README" in messages

    document = _facts()
    holdable = {"api_reference", "quick_start", "additional_examples"}
    restored, changes = restore_lost_units(dispositions, document, [UNIT], holdable, holdable)
    (change,) = changes
    row = next(r for r in restored["dispositions"] if r["unit_id"] == UNIT)
    assert change["unit_id"] == UNIT and prints_unit(row["destination_section"], "code_block")
    assert row["disposition"] == "VERIFIED_PRESERVE"  # kept as written, never dropped (R14)


def test_a_unit_kept_into_a_section_the_plan_omits_is_rehomed() -> None:
    dispositions = _dispositions("additional_examples")
    holdable = {"quick_start", "api_reference", "additional_examples"}
    included = {"quick_start", "api_reference"}  # the plan omits additional_examples: nothing prints
    restored, changes = restore_lost_units(dispositions, _facts(), [UNIT], holdable, included)
    row = next(r for r in restored["dispositions"] if r["unit_id"] == UNIT)
    assert [c["unit_id"] for c in changes] == [UNIT]
    assert row["destination_section"] in included


def test_negative_a_unit_printed_where_it_is_kept_is_untouched() -> None:
    dispositions = _dispositions("quick_start")
    holdable = {"quick_start", "api_reference"}
    restored, changes = restore_lost_units(dispositions, _facts(), [UNIT], holdable, holdable)
    assert changes == [] and restored == dispositions
    assert not any(UNIT in m for m in _findings(dispositions, README + "\n" + CODE + "\n"))


def test_the_cascade_feeds_only_non_shell_unprinted_units_to_the_restore() -> None:
    settled = SimpleNamespace(
        composed=SimpleNamespace(readme=README, dispositions=_dispositions("api_reference"))
    )
    assert cascade._unprinted_kept_unit_ids(settled, _facts()) == [UNIT]  # the heading is the shell's


# --- the gate: the reviewer's finding alone starts a restore, a passing candidate never does -----


def _attempted(monkeypatch, blocking: list[object]) -> bool:  # type: ignore[no-untyped-def]
    from pathlib import Path

    calls: list[bool] = []
    monkeypatch.setattr(cascade, "blocking_failures", lambda validation: [])
    monkeypatch.setattr(cascade, "_unprinted_kept_unit_ids", lambda settled, document: [UNIT])
    monkeypatch.setattr(cascade, "holdable_sections", lambda document: calls.append(True) or {})
    settled = SimpleNamespace(
        composed=SimpleNamespace(plan={"sections": []}, dispositions={}),
        validation={},
        verdict=SimpleNamespace(blocking_findings=blocking),
    )
    try:
        result = cascade._restore_lost_content(
            settled, entry=None, document=None, investigation={}, tree_paths=[], original="",
            out_dir=Path("."),
        )
    except Exception:  # noqa: BLE001 - past the gate the fake settled cannot be rendered
        return True
    assert result is settled
    return bool(calls)


def test_a_blocking_reviewer_finding_alone_starts_the_restore(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assert _attempted(monkeypatch, [object()])


def test_negative_a_candidate_the_reviewer_does_not_block_is_never_restored(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assert not _attempted(monkeypatch, [])
