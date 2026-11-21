"""BL-640: a restored kept list or paragraph whose only new failure is BC-07's reference sentence ("the examples
above" where no code precedes it in the section) is kept without that sentence, recorded on its disposition
(R14), instead of being rolled back whole.

Real data: ``inherited_unit:072.list`` of aspose-tex-foss/Aspose.TeX-FOSS-for-Python at the pinned revision
07db3203 (README 'Scope and Limitations'); the shape hosted run 44943500229 failed on: the whole list
(the Pre-Alpha status, the supported format, the unsupported commands) stayed lost, so the maintainers'
status badge ``status-pre--alpha-orange`` was named lost by BC-17 on every settle round."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.references import dangling_references
from repo_presenter.readme.repair.restore_units import reference_sentences, withhold_reference_sentences
from repo_presenter.readme.validation.must_correct import DEGRADE_WITHHELD_KEY, withheld_form

UNIT = "inherited_unit:072.list"
LIST = (
    "- This is a Pre-Alpha release: the core engine and public API are under active development, and\n"
    "  interfaces may change between releases.\n"
    "- Plain TeX is the supported format. The default `load_format=\"plain\"` option (`TeXOptions`) loads\n"
    "  Knuth's macros from the bundled `plain.tex`, with its output routine, footnotes, and inserts.\n"
    "  The examples above pass `load_format=False` to run a document from primitives alone; leave it\n"
    "  out to use the plain macros.\n"
    "- LaTeX and the e-TeX and pdfTeX extensions are not implemented yet. `\\documentclass`,\n"
    "  `\\numexpr`, `\\pdfoutput`, and similar commands raise `EngineError`."
)
README = "# X\n\n## Scope and Limitations\n\n" + LIST + "\n"


def _facts(text: str = LIST) -> FactsDocument:
    fact = Fact(
        id=UNIT, kind="inherited_unit", value=text, evidence=(Evidence("README.md", None),),  # type: ignore[arg-type]
        polarity="SUPPORTED", attributes={"section": "X > Scope and Limitations"},  # type: ignore[arg-type]
    )
    return FactsDocument("aspose-tex-foss/Aspose.TeX-FOSS-for-Python", "0" * 40, (fact,))


def _failing(readme: str = README) -> list[dict]:
    found = dangling_references(readme)
    assert found, "the fixture must really be a dangling reference"
    return [
        {
            "id": "BC-07",
            "failures": [
                {"unit_id": UNIT, "detail": f"{UNIT} is kept as written but {r.reason}: {r.sentence[:140]!r}"}
                for r in found
            ],
        }
    ]


def _dispositions() -> dict:
    return {
        "dispositions": [
            {
                "unit_id": UNIT, "disposition": "VERIFIED_PRESERVE", "destination_section": "scope_limitations",
                "fact_ids": [], "rationale": "restored",
            }
        ]
    }


def test_the_real_reference_sentence_is_read_from_the_failure_and_withheld_whole() -> None:
    wanted = reference_sentences(_failing(), {UNIT})
    assert list(wanted) == [UNIT] and "examples above" in wanted[UNIT][0]
    output = _dispositions()
    done = withhold_reference_sentences(output, _facts(), wanted)
    assert list(done) == [UNIT]
    printed = withheld_form(UNIT, LIST, output["dispositions"][0][DEGRADE_WITHHELD_KEY])
    assert "This is a Pre-Alpha release" in printed  # the status the badge states is kept
    assert "LaTeX and the e-TeX and pdfTeX extensions are not implemented yet" in printed
    assert "Plain TeX is the supported format." in printed and "Knuth's macros from the bundled" in printed
    assert "use the plain macros" not in printed  # only the pointing sentence of the item is withheld
    assert "examples above" not in printed
    assert not dangling_references("# X\n\n## Scope and Limitations\n\n" + printed + "\n")  # BC-07 now clean


def test_negative_control_a_failure_of_another_unit_or_check_is_not_trimmed() -> None:
    other = [{"id": "BC-14", "failures": [{"unit_id": UNIT, "detail": f"{UNIT} is kept as written but says 'x': 'y.'"}]}]
    assert reference_sentences(other, {UNIT}) == {}
    assert reference_sentences(_failing(), {"inherited_unit:999.list"}) == {}


def test_negative_control_a_unit_that_is_only_the_reference_sentence_is_not_trimmed_away() -> None:
    only = "The examples above pass `load_format=False` to run a document from primitives alone."
    output = _dispositions()
    done = withhold_reference_sentences(output, _facts(only), {UNIT: [only]})
    assert done == {} and DEGRADE_WITHHELD_KEY not in output["dispositions"][0]


def test_negative_control_a_sentence_already_withheld_that_still_fails_is_left_to_the_rollback() -> None:
    wanted = reference_sentences(_failing(), {UNIT})
    output = _dispositions()
    assert withhold_reference_sentences(output, _facts(), wanted)
    assert withhold_reference_sentences(output, _facts(), wanted) == {}  # second time: nothing new, so the rollback runs


def test_negative_control_an_unplaced_unit_is_never_trimmed() -> None:
    output = _dispositions()
    output["dispositions"][0]["disposition"] = "SUPERSEDE_REDUNDANT"
    assert withhold_reference_sentences(output, _facts(), reference_sentences(_failing(), {UNIT})) == {}


def test_negative_control_a_quote_that_is_not_a_reference_sentence_still_withholds_its_whole_item() -> None:
    # A register row / flagged claim withholds its item exactly as before: no sealed list moves (R10).
    text = "- First item.\n- Plain TeX is the supported format. It is fast. Use it everywhere.\n- Last item."
    printed = withheld_form("inherited_unit:001.list", text, ["It is fast."])
    assert printed == "- First item.\n- Last item."
