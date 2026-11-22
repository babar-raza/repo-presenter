"""BL-700: three classes of audit false flag on clean Lane R controls (round 6, seed run 44972760783).

* 3D TypeScript line 252, ``| `Watermark` | Not implemented. |``: the renderer's fact-true stub row, kept by the K02
  "behaviour claim" class although a SUPPORTED limitation statement names the whole type as a stub.
* Slides .NET line 726, "The suite covers 121 test files ... Project documentation lives under `docs/`.": the last
  sentence is the renderer's own build/test asset locator, which the scope patterns did not list, so the line stayed
  "authored" and was neither shown as renderer text nor derivable.
* PDF TypeScript lines 3827 and 3833, ``| `MdLink` | Inline and reference links are indistinguishable here ... gl6o.3
  wants. |``: the row prints the type's own doc comment (the SUPPORTED fact's ``docstring_full``) word for word.

Negative controls: a fabricated 'Not implemented.' row, a stubbed member alone, a locator-looking sentence that is not
one, and a doc-comment row one word off all keep their flag or stay reviewed.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.derivation import keep_reason, stub_provenance
from repo_presenter.readme.review.scope import authored_type_rows, shown_text


def _public(name: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{name.lower()}", "public_symbol", name, (Evidence("src/x.ts", "line 1; class"),), "SUPPORTED",
        attributes={"symbol_kind": "class", **attributes},
    )


def _limitation(text: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact("inherited_unit:010.list", "inherited_unit", text, (Evidence("README.md", "line 9"),), polarity)


def _facts(limitation: str = "`Watermark` is not implemented.", polarity: str = "SUPPORTED") -> FactsDocument:
    return FactsDocument(
        "o/r", "a" * 40,
        (_public("Watermark"), _public("Scene"), _public("Mesh"), _limitation(limitation, polarity)),
    )


ROW = "| `Watermark` | Not implemented. |"


# --- 3D TypeScript: the stub row ---------------------------------------------------------------------------


def test_the_whole_stub_type_row_is_verified_by_the_limitation_statement() -> None:
    facts = _facts()
    proof = stub_provenance([ROW], 1, facts)
    assert proof is not None and "inherited_unit:010.list" in proof and proof.startswith("K02 verified")
    verified: dict[int, str] = {}
    assert keep_reason("R", ROW, {"source": "renderer"}, facts, [ROW], 1, verified) is None
    assert "K02 verified" in verified[1]


def test_negative_control_a_type_no_statement_names_keeps_its_flag() -> None:
    facts = _facts()
    row = "| `Scene` | Not implemented. |"
    assert stub_provenance([row], 1, facts) is None
    assert keep_reason("R", row, {"source": "renderer"}, facts, [row], 1, {}) == "K02 behaviour claim"


def test_negative_control_a_stubbed_member_is_not_a_stubbed_type() -> None:
    facts = _facts("`Watermark.decode()` is not implemented.")
    assert stub_provenance([ROW], 1, facts) is None
    assert keep_reason("R", ROW, {"source": "renderer"}, facts, [ROW], 1, {}) == "K02 behaviour claim"


def test_negative_control_an_unsupported_statement_or_another_description_keeps_its_flag() -> None:
    assert stub_provenance([ROW], 1, _facts(polarity="CONTRADICTED")) is None
    facts = _facts()
    for row in (
        "| `Watermark` | Not implemented in this release. |",
        "| `Watermark` | Always throws when decoding. |",
        "| `Watermark` | Not implemented. It encodes blind watermarks. |",
        "Watermark is not implemented.",
    ):
        assert stub_provenance([row], 1, facts) is None, row


# --- Slides .NET: the renderer's asset locator sentences -----------------------------------------------------


def test_the_renderers_asset_locator_sentences_are_not_shown_as_an_authors_claim() -> None:
    line = (
        "The suite covers 121 test files under `tests/`. The [ci workflow](.github/workflows/ci.yml) runs on "
        "Ubuntu, Windows and macOS. Releases run through the [nuget-release workflow]"
        "(.github/workflows/nuget-release.yml). Project documentation lives under `docs/`."
    )
    assert shown_text(line) == ""
    for sentence in (
        "Tests live under `tests/`.",
        "Example programs live under `examples/`.",
        "Project documentation lives under `docs/`.",
    ):
        assert shown_text(sentence) == "", sentence


def test_negative_control_an_authored_sentence_next_to_a_locator_is_still_shown() -> None:
    line = "Project documentation lives under `docs/`. The build also uploads every artifact to a public bucket."
    assert shown_text(line) == "The build also uploads every artifact to a public bucket."
    assert shown_text("Project documentation lives under the docs folder.") != ""


def test_the_locator_sentences_are_in_the_renderers_own_list() -> None:
    from repo_presenter.readme.composition.planning import plan_checks
    from repo_presenter.readme.composition.renderer import renderer_sentences
    from tests.readme.composition.synthetic import make_entry, make_facts
    from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

    facts = make_facts()
    plan, dispositions = _plan(), _dispositions()
    plan_checks(plan, facts, dispositions=dispositions, ecosystem="python")
    for sentence in renderer_sentences(make_entry(), facts, plan, _units(), dispositions):
        assert shown_text(sentence) == "", sentence


# --- PDF TypeScript: a row that prints the type's own doc comment ----------------------------------------------

DOC = "Inline and reference links are indistinguishable here: both carry a resolved destination and title."


def _readme(description: str) -> str:
    return f"# T\n\n## API Reference\n\n### Core API\n\n| Class | Description |\n| --- | --- |\n| `MdLink` | {description} |\n"


def _doc_facts() -> FactsDocument:
    return FactsDocument("o/r", "a" * 40, (_public("MdLink", docstring_full=DOC),))


def test_a_row_that_prints_the_doc_comment_word_for_word_is_not_an_authored_row() -> None:
    facts = _doc_facts()
    assert authored_type_rows(_readme(DOC), facts) == {}
    assert authored_type_rows(_readme(DOC), facts, reviewable=True) == {}
    escaped = FactsDocument("o/r", "a" * 40, (_public("MdLink", docstring_full="One of: 'a' | 'b'."),))
    assert authored_type_rows(_readme("One of: 'a' \\| 'b'."), escaped) == {}


def test_negative_control_a_doc_comment_row_changed_by_one_word_stays_authored() -> None:
    facts = _doc_facts()
    changed = DOC.replace("indistinguishable", "distinguishable")
    assert list(authored_type_rows(_readme(changed), facts).values())[0].id == "public_symbol:mdlink"


def test_negative_control_a_type_without_a_doc_comment_stays_authored() -> None:
    facts = FactsDocument("o/r", "a" * 40, (_public("MdLink"),))
    assert authored_type_rows(_readme(DOC), facts)
