"""BL-500: the full-reference link's pointer to the API Reference section is true by construction.

Hosted Lane R PDF .NET (run 44709138381, main 6f5a176) ended on the model reviewer's finding
"The API Reference section above covers the essentials." against the line below, which the renderer prints from
the link fact and the maintainers' kept sentence (the count 968 already corrected to the facts' computation).
``review.scope`` stripped only the renderer's own spelling of that pointer, so the maintainers' spelling was shown
to the reviewer as an authored claim it cannot ground, and the degrade cannot drop the line (BC-05/BC-17: the
documentation link is a retained unit). The pointer is the renderer's guarantee, not a claim: it is printed only
when the section is rendered above (``renderer._reference_pointer``) and ``review.scope`` no longer shows it.
Sealed READMEs are byte-identical (recertify before/after). Every input line below is a hosted or published line,
verbatim.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import _reference_pointer, render_readme
from repo_presenter.readme.review.derivation import count_provenance
from repo_presenter.readme.review.scope import shown_text
from tests.readme.repair import test_accounting as base

#: PDF .NET, hosted failure record 44709138381 (maintainers' sentence, count already corrected to 968).
PDF_NET = (
    "- **[Full API reference](https://reference.aspose.org/pdf/net/)** — the complete, browsable reference "
    "for all 968 public types (the API Reference section above covers the essentials)."
)
#: Words Python seal ab8a03, 3D Python audit line 713: the linked spelling.
LINKED = (
    "- **[Full API reference](https://reference.aspose.org/3d/python/)** — the complete, browsable reference "
    "for all 344 public types (the [API reference](#api-reference) section above covers the essentials)."
)

POINTER_FRAGMENT = "section above covers the essentials"


@pytest.mark.parametrize("line", [PDF_NET, LINKED])
def test_the_reviewer_is_not_shown_the_pointer_or_the_count_clause_of_the_line(line: str) -> None:
    shown = shown_text(line)
    assert shown.endswith("— the complete, browsable reference.")
    assert POINTER_FRAGMENT not in shown and "public types" not in shown


@pytest.mark.parametrize("prose", [
    # negative controls: the same words anywhere but the link line's parenthetical are an author's claim
    "The API Reference section above covers the essentials.",
    "The library has 968 public types (see the API Reference section above).",
    "- **[Guides](https://docs.aspose.org/x/)** — all 12 guides (the guide section above covers the basics).",
])
def test_the_same_words_outside_the_pointer_are_still_shown(prose: str) -> None:
    assert shown_text(prose) == prose


def test_with_the_section_rendered_the_maintainers_words_are_kept_byte_for_byte() -> None:
    sentence = "the complete, browsable reference for all 968 public types (the API Reference section above covers the essentials)."
    assert _reference_pointer(sentence, True, 968) == sentence


def test_a_description_without_a_count_is_told_the_renderers_own_sentence_as_before() -> None:
    # Cells Rust and PDF Java seals (the maintainers' pointer, no count): the renderer's own sentence follows
    # it, byte for byte what the seals print, so recertification changes nothing
    sentence = "the complete, browsable reference for the public API surface (the [API reference](#api-reference) section above covers the essentials)."
    assert _reference_pointer(sentence, True, 115) == (
        sentence + " It covers all 115 public types; the [API Reference](#api-reference) section above covers the essentials."
    )
    assert shown_text(_reference_pointer(sentence, True, 115)) == "the complete, browsable reference for the public API surface."


def test_without_the_section_the_pointer_goes_and_the_rest_stays() -> None:
    printed = _reference_pointer(
        "the complete, browsable reference for all 968 public types (the API Reference section above covers the essentials).",
        False, 968)
    assert printed == "the complete, browsable reference for all 968 public types."
    linked = _reference_pointer(
        "the complete, browsable reference (the [API reference](#api-reference) section above covers the entry points).",
        False, 5)
    assert linked == "the complete, browsable reference."


@pytest.mark.parametrize("plain", [
    "complete, generated reference documentation for every public type.",  # no pointer, no count
    "the complete, browsable reference for all 617 public types.",  # a count, no pointer: left to the count check
])
def test_a_description_with_no_pointer_is_left_as_written(plain: str) -> None:
    assert _reference_pointer(plain, False, 617) == plain
    if "public types" in plain:
        assert _reference_pointer(plain, True, 617) == plain


def _world(maintainers_line: str, *, with_api: bool = True) -> tuple[FactsDocument, dict[str, Any], dict[str, Any]]:
    facts = [f for f in base._facts().facts if f.id not in {"inherited_unit:004.list"}]
    facts = [
        Fact(f.id, f.kind, f.value, f.evidence, polarity=f.polarity, attributes={"symbol_kind": "class"})
        if f.kind == "public_symbol" else f
        for f in facts
    ]
    facts += [
        Fact(f"public_symbol:t{i}", "public_symbol", f"aspose.threed.T{i}",
             (Evidence("x.py", "line 1; class; public by name"),), polarity="SUPPORTED",
             attributes={"symbol_kind": "class"})
        for i in range(6)
    ]
    reference = base._fact("link_target:003", "link_target", "https://reference.aspose.org/pdf/net/",
                           "line 9; external; text 'Full API reference'", "RESOLVED")
    lst = (
        "- **[Getting started guide](https://docs.example.com/3d)** - installation and walkthroughs.\n"
        "- **[How-to articles](https://kb.example.com/3d)** - task-focused answers.\n" + maintainers_line
    )
    facts += [reference, base._unit("004.list", lst)]
    document = FactsDocument(base.ENTRY.repository, base.REVISION, tuple(facts))
    plan = base._plan()
    plan["links"].append({"link_fact_id": "link_target:003", "section_id": "documentation_resources"})
    if not with_api:
        for section in plan["sections"]:
            if section["section_id"] == "api_reference":
                section["include"] = False
        plan["api_hubs"] = []
    dispositions = base._dispositions()
    for entry in dispositions["dispositions"]:
        if entry["unit_id"] == "inherited_unit:004.list":
            entry["fact_ids"] = ["link_target:001", "link_target:002", "link_target:003"]
    return document, plan, dispositions


def _line(readme: str) -> str:
    return next(row for row in readme.splitlines() if "reference.aspose.org" in row)


def test_the_rendered_line_keeps_its_link_the_maintainers_words_and_a_count_the_k05_check_verifies() -> None:
    document, plan, dispositions = _world(PDF_NET.replace("968", "3"))
    readme = render_readme(base.ENTRY, document, plan, copy.deepcopy(base.UNITS), dispositions)
    line = _line(readme)
    assert line == PDF_NET.replace("968", "7")  # byte for byte, the count corrected to the 7 type facts
    assert "## API Reference" in readme  # the pointer's target is rendered above the line
    assert readme.index("## API Reference") < readme.index(line)
    assert count_provenance(readme.splitlines(), readme.splitlines().index(line) + 1, document)
    assert POINTER_FRAGMENT not in shown_text(line)


def test_with_the_section_not_rendered_no_pointer_is_printed() -> None:
    document, plan, dispositions = _world(PDF_NET.replace("968", "3"), with_api=False)
    readme = render_readme(base.ENTRY, document, plan, copy.deepcopy(base.UNITS), dispositions)
    assert "## API Reference" not in readme
    assert "section above" not in _line(readme)
    assert _line(readme).endswith("for all 7 public types.")
