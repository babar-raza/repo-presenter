"""BL-651 (hosted Lane R Words Python, run 44947429600: BC-04 and BC-17 after 7 calls).

The real shapes, from the pinned source (aspose-words-foss/Aspose.Words-FOSS-for-Python @ 2d2efee):

* BC-14 rule (g): the published README says "``Document`` ... loads a ``.doc``, ``.docx``, ``.rtf``,
  ``.txt``, or ``.md`` file". The product declares ``LoadFormat`` (AUTO, DOC, DOCX, RTF, TEXT,
  MARKDOWN), but ``format`` facts come from verified examples only (``.md`` and ``.txt``), so the
  kept unit ``084.list`` failed BC-14; restoring it for BC-17 (``AUTO`` lost) was rolled back for
  that BC-14, and the model's only other answer (omit) loses it again.
* BC-04: the renderer's Documentation and Resources link line for the kept sentence "The
  ``ApiExamples/`` scripts ... commercial [`aspose-words`](...) package ... replacing
  ``aspose.words_foss`` with ``aspose.words``" prints the maintainers' spans on a line BC-04 judged
  as authored (``aspose-words``, ``aspose.words`` are not fact values).
"""

from __future__ import annotations

import dataclasses

from test_registry_checks import DISPOSITIONS, ENTRY, FACTS, PLAN, UNITS, _candidate

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.units import unit_failures


def _fact(fact_id: str, kind: str, value: str, detail: str = "x", **attributes: object) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", detail),), attributes=attributes or None)


def _with(facts: FactsDocument, *extra: Fact) -> FactsDocument:
    return FactsDocument(facts.repository, facts.source_revision, (*facts.facts, *extra))


LOAD_ENUM = tuple(
    _fact(
        f"enum_member:aspose.words_foss.loadformat.{name.lower()}", "enum_member",
        f"aspose.words_foss.LoadFormat.{name}", enum="aspose.words_foss.LoadFormat", member_kind="enum",
    )
    for name in ("AUTO", "DOC", "DOCX", "RTF", "TEXT", "MARKDOWN")
)
SAVE_ENUM = tuple(
    _fact(
        f"enum_member:aspose.words_foss.saveformat.{name.lower()}", "enum_member",
        f"aspose.words_foss.SaveFormat.{name}", enum="aspose.words_foss.SaveFormat", member_kind="enum",
    )
    for name in ("DOC", "DOCX", "TEXT", "PDF")
)
FORMATS = (
    _fact("format:input.md", "format", ".md"),
    _fact("format:input.txt", "format", ".txt"),
    _fact("format:output.pdf", "format", ".pdf"),
)
LOADS = (
    "- `Document(filepath=None, *, stream=None, data=None)` — loads a `.doc`, `.docx`, `.rtf`, `.txt`, or\n"
    "  `.md` file (or DOCX bytes/stream) and populates the model immediately at construction time."
)
OPENS = (
    "- Open any supported input with a single `Document(filepath)` constructor — the concrete reader is\n"
    "  chosen automatically from the `.docx`/`.doc`/`.rtf`/`.md`/`.txt` file extension."
)


def _formats(readme: str, *facts: Fact) -> list[str]:
    document = _with(FACTS, *FORMATS, *facts)
    return [f.detail for f in claim_findings(readme, document) if "lists the format" in f.detail]


def test_the_published_load_sentences_are_stated_by_the_load_format_enum() -> None:
    assert _formats(LOADS, *LOAD_ENUM, *SAVE_ENUM) == []
    assert _formats(OPENS, *LOAD_ENUM, *SAVE_ENUM) == []


def test_negative_control_without_the_declaration_the_claim_is_still_refused() -> None:
    # The same README on facts that declare no load formats (the state the hosted run judged).
    assert _formats(LOADS) == ["the README lists the format(s) .doc, .docx, .rtf, but no SUPPORTED format fact states them"]
    assert _formats(OPENS)
    # A save enum is not a load declaration, nor is a non-SUPPORTED member.
    assert _formats(LOADS, *SAVE_ENUM)
    stale = tuple(dataclasses.replace(fact, polarity="CONTRADICTED") for fact in LOAD_ENUM)
    assert _formats(LOADS, *stale)


def test_negative_control_an_extension_the_enum_does_not_declare_or_a_save_sentence_is_refused() -> None:
    invented = "- `Document(filepath)` — loads a `.docx`, `.xls` or `.txt` file."
    assert _formats(invented, *LOAD_ENUM) == [
        "the README lists the format(s) .xls, but no SUPPORTED format fact states it"
    ]
    saving = "- `Document.save()` — saves a `.doc`, `.docx` or `.txt` file."
    assert _formats(saving, *LOAD_ENUM) != []  # a load enum says nothing about writing


# --- BC-04 ---------------------------------------------------------------------------------------

SENTENCE = (
    "The `ApiExamples/` scripts are written against the API this library shares with the commercial "
    "[`aspose-words`](https://github.com/aspose-words/Aspose.Words-for-Python-via-.NET) package — the same "
    "sources run there too, by replacing `aspose.words_foss` with `aspose.words` in the imports."
)
RESOURCES = (
    "- **[Getting started guide](https://docs.aspose.org/words/python/)** — installation, walkthroughs, "
    "and feature guides for this library.\n"
    f"- {SENTENCE}"
)


def _docs_candidate(*, kept: bool):
    links = (
        _fact("link_target:901", "link_target", "https://docs.aspose.org/words/python/",
              "line 605; external; text 'Getting started guide'"),
        _fact("link_target:902", "link_target", "https://github.com/aspose-words/Aspose.Words-for-Python-via-.NET",
              "line 608; external; text 'aspose-words'"),
        _fact("import_path:aspose.words_foss", "import_path", "aspose.words_foss"),
        _fact("inherited_unit:099.list", "inherited_unit", RESOURCES, "section 'Documentation & Resources'",
              section="Aspose.Words FOSS for Python > Documentation & Resources"),
    )
    facts = _with(FACTS, *links)
    dispositions = {
        "dispositions": [
            *DISPOSITIONS["dispositions"],
            {
                "unit_id": "inherited_unit:099.list",
                "disposition": "VERIFIED_PRESERVE" if kept else "SUPERSEDE_REDUNDANT",
                "destination_section": "documentation_resources" if kept else None,
                "fact_ids": [] if kept else ["identity:repository"],
                "rationale": "kept" if kept else "r",
            },
        ]
    }
    plan = {
        **PLAN,
        "links": [
            {"link_fact_id": "link_target:901", "section_id": "documentation_resources"},
            {"link_fact_id": "link_target:902", "section_id": "documentation_resources"},
        ],
    }
    readme = render_readme(ENTRY, facts, plan, UNITS, dispositions)
    return _candidate(readme=readme, facts=facts, dispositions=dispositions, plan=plan)


def _spans(candidate) -> list[str]:
    return [f.detail for f in unit_failures(candidate) if "is not a fact value" in f.detail]


def test_a_kept_resource_sentence_printed_on_its_link_line_is_not_judged_as_authored() -> None:
    candidate = _docs_candidate(kept=True)
    line = next(l for l in candidate.readme.splitlines() if l.startswith("- **[aspose-words]"))
    assert "`aspose-words`" in line and "`aspose.words`" in line  # the failing shape is rendered
    assert _spans(candidate) == []


def test_negative_control_the_same_line_not_held_by_a_kept_list_is_still_judged() -> None:
    candidate = _docs_candidate(kept=True)
    # An authored line with the same spans (no kept list holds that description) stays refused.
    forged = candidate.readme.replace(
        SENTENCE, "Run the scripts against the commercial `aspose-words` package, replacing the import with `aspose.words`."
    )
    assert forged != candidate.readme
    assert set(_spans(dataclasses.replace(candidate, readme=forged))) == {
        "code span 'aspose-words' is not a fact value",
        "code span 'aspose.words' is not a fact value",
    }
