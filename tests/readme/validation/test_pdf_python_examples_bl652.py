"""BL-652 (hosted Lane R PDF Python, run 44943413732: REJECT with 36 blocking findings of 36, 52
calls). Every finding is a kept example unit of the published README that the candidate printed as
a different spelling, so no disposition could clear it (the model's only answer, omit, is refused
for citing no fact, R14):

* 15 headings ('### Exchange Bookmarks as JSON', ``138.heading``, directly above the example it
  titles, ``139.code_block``): kept into Additional Examples, but a verified example printed under
  the AUTHORED task title only, and a heading is never a verbatim placed unit, so the maintainers'
  heading was printed nowhere (``disposition_coverage`` 'kept but not printed', and 16
  ``live_readme_loss`` headings).
* 5 code blocks (``142``, ``196``, ``199``, ``220``, ``244``): fragments that lean on the import
  printed elsewhere in the README. The verified example prints as the program its receipt ran, the
  verifier's prelude (``from aspose_pdf import Document``) first, so the fragment is printed inside
  that program and never as the fenced text it was written as.

The units below are the real ones (pinned source aspose-pdf-foss/Aspose-PDF-FOSS-for-Python @
5e122e0)."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.readme.composition.renderer import RenderContext, _example_entry
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units

REPO = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python"
HEADING = "### Exchange Bookmarks as JSON"
CODE_139 = (
    '```python\nfrom aspose_pdf import Document\n\nwith Document("manual.pdf") as document:\n'
    '    document.export_bookmarks_json("bookmarks.json")\n```'
)
HEADING_141 = "### Edit Simple Bookmarks as CSV"
CODE_142 = (
    '```python\nwith Document("manual.pdf") as document:\n'
    '    document.export_bookmarks_csv("bookmarks.csv", encoding="utf-8-sig")\n\n'
    'with Document("updated-manual.pdf") as document:\n'
    '    added = document.import_bookmarks_csv("bookmarks.csv", encoding="utf-8-sig")\n```'
)


def _body(fence: str) -> str:
    return "\n".join(fence.splitlines()[1:-1])


def _facts() -> FactsDocument:
    def unit(unit_id: str, text: str) -> Fact:
        return Fact(f"inherited_unit:{unit_id}", "inherited_unit", text, (Evidence("README.md"),))

    def example(number: int, unit_id: str, code: str, prelude: str = "") -> Fact:
        return Fact(
            f"example:{number:03d}", "example", code,
            (Evidence("README.md", f"lines 1-2; python fence; unit inherited_unit:{unit_id}"),
             Evidence("receipts.json", f"example {number}: EXECUTED; exit 0")),
            attributes={"prelude": prelude} if prelude else None,
        )

    return FactsDocument(
        REPO, "5e122e051e914e83b1ddbf3649055bc0d8ec1ea8",
        (
            Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
            unit("138.heading", HEADING),
            unit("139.code_block", CODE_139),
            unit("141.heading", HEADING_141),
            unit("142.code_block", CODE_142),
            example(13, "139.code_block", _body(CODE_139)),
            example(14, "142.code_block", _body(CODE_142), "from aspose_pdf import Document"),
        ),
    )


def _dispositions(heading_destination: str = "additional_examples") -> dict:
    kept = lambda unit, destination: {  # noqa: E731
        "unit_id": unit, "disposition": "VERIFIED_PRESERVE", "destination_section": destination,
        "fact_ids": [], "rationale": "kept",
    }
    return {"dispositions": [
        kept("inherited_unit:138.heading", heading_destination),
        kept("inherited_unit:139.code_block", "additional_examples"),
        kept("inherited_unit:141.heading", heading_destination),
        kept("inherited_unit:142.code_block", "additional_examples"),
    ]}


def _entry():
    return next(e for e in load_registry(Path("data/registry.json")).entries if e.repository == REPO)


def _context(dispositions: dict) -> RenderContext:
    plan = {"sections": [{"section_id": "additional_examples", "include": True}],
            "additional_example_ids": ["example:013", "example:014"], "links": []}
    units = {"units": [
        {"section": "additional_examples", "slot": "workflow:example:013",
         "text": "Round-trip the outline through a JSON file.", "fact_ids": ["example:013"]},
        {"section": "additional_examples", "slot": "workflow:example:014",
         "text": "Edit the outline as a spreadsheet.", "fact_ids": ["example:014"]},
    ]}
    return RenderContext(_entry(), _facts(), plan, units, dispositions)


def test_a_kept_heading_directly_above_a_verified_example_titles_its_entry() -> None:
    context = _context(_dispositions())
    first = _example_entry(context, "additional_examples", "example:013")
    second = _example_entry(context, "additional_examples", "example:014")
    assert first[1] == HEADING and second[1] == HEADING_141
    readme = "\n".join(first + second)
    # The verified program prints with the verifier's import above the maintainers' fragment.
    assert "from aspose_pdf import Document\n\nwith Document(\"manual.pdf\")" in readme
    assert unprinted_kept_units(readme, facts=context.facts, dispositions=_dispositions()) == []


def test_negative_control_without_the_fix_shapes_the_unit_stays_refused() -> None:
    # A heading kept elsewhere is not the example's title: the authored task title stands and the
    # kept heading is still unprinted, exactly as before.
    moved = _dispositions("scope_limitations")
    context = _context(moved)
    entry = _example_entry(context, "additional_examples", "example:013")
    assert entry[1] == "### Round-trip the Outline Through a JSON File"
    readme = "\n".join(entry + _example_entry(context, "additional_examples", "example:014"))
    unprinted = {unit for unit, _ in unprinted_kept_units(readme, facts=context.facts, dispositions=moved)}
    assert unprinted == {"inherited_unit:138.heading", "inherited_unit:141.heading"}


def test_negative_control_a_heading_not_kept_is_never_printed_in_place_of_the_authored_title() -> None:
    superseded = _dispositions()
    superseded["dispositions"][0]["disposition"] = "SUPERSEDE_REDUNDANT"
    context = _context(superseded)
    assert _example_entry(context, "additional_examples", "example:013")[1].startswith("### Round-trip")


def test_a_fragment_printed_inside_the_verified_program_is_printed_but_an_altered_one_is_not() -> None:
    context = _context(_dispositions())
    readme = "\n".join(_example_entry(context, "additional_examples", "example:014"))
    assert "inherited_unit:142.code_block" not in {
        unit for unit, _ in unprinted_kept_units(readme, facts=context.facts, dispositions=_dispositions())
    }
    # The same README with one line of the maintainers' code changed no longer prints the block.
    altered = readme.replace("encoding=\"utf-8-sig\")\n\nwith", "encoding=\"latin-1\")\n\nwith")
    assert altered != readme
    assert "inherited_unit:142.code_block" in {
        unit for unit, _ in unprinted_kept_units(altered, facts=context.facts, dispositions=_dispositions())
    }
    # And a README that prints nothing of it, as before.
    assert "inherited_unit:142.code_block" in {
        unit for unit, _ in unprinted_kept_units("# Title\n", facts=context.facts, dispositions=_dispositions())
    }
