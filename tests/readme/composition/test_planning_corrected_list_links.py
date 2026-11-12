"""A docs list the model CORRECTED keeps every link it prints.

Aspose.Cells-FOSS-for-Go (fresh Lane R, 2026-11-11): the maintainers' "Documentation & Resources"
list (``inherited_unit:055.list``, five items) was dispositioned ``CORRECT_WITH_EVIDENCE`` into
``scope_limitations`` (a name correction), citing link_target:038..042. The plan carried three of the
five links in ``documentation_resources`` (docs, kb, issues) and dropped ``reference.aspose.org`` and
``AGENTS.md``; only ``documentation_resources`` prints a link bullet, and a ``CORRECT_WITH_EVIDENCE``
unit is never placed verbatim, so BC-17 reported the ``AGENTS.md`` link lost.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.planning import (
    _kept_list_links,
    _missing_kept_list_links,
)

LIST = (
    "- **[Getting started guide](https://docs.aspose.org/cells/go/)** — Go documentation for\n"
    "  Aspose.Cells FOSS: loading, editing, styling, and saving spreadsheets.\n"
    "- **[How-to guides & FAQ](https://kb.aspose.org/cells/go/)** — Go knowledge base for Aspose.Cells\n"
    "  FOSS: how-to articles, FAQ, and troubleshooting guides.\n"
    "- **[Full API reference](https://reference.aspose.org/cells/go/)** — the complete, browsable\n"
    "  reference for all 14 public types (the [API reference](#api-reference) section above covers the\n"
    "  essentials).\n"
    "- **[AGENTS.md](AGENTS.md)** — the repository's own contribution guide for AI-assisted\n"
    "  development, covering source-of-truth conventions and areas to avoid changing without review.\n"
    "- Found a bug or have a feature request?\n"
    "  [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/issues) on GitHub."
)
URLS = {
    "link_target:036": "#constraints",
    "link_target:038": "https://docs.aspose.org/cells/go/",
    "link_target:039": "https://kb.aspose.org/cells/go/",
    "link_target:040": "https://reference.aspose.org/cells/go/",
    "link_target:041": "AGENTS.md",
    "link_target:042": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/issues",
    "link_target:043": "https://products.aspose.com/cells/go-cpp/",
}
CITED = ["link_target:038", "link_target:039", "link_target:040", "link_target:041", "link_target:042"]


def _facts() -> FactsDocument:
    facts = [
        Fact(fact_id, "link_target", value, (Evidence("README.md"),))  # type: ignore[arg-type]
        for fact_id, value in URLS.items()
    ]
    facts.append(
        Fact("inherited_unit:055.list", "inherited_unit", LIST, (Evidence("README.md"),))  # type: ignore[arg-type]
    )
    return FactsDocument("org/Aspose.Cells-FOSS-for-Go", "f" * 40, tuple(facts))


def _dispositions(disposition: str, cited: list[str] = CITED) -> dict:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:055.list",
                "disposition": disposition,
                "destination_section": "scope_limitations",
                "fact_ids": cited,
                "rationale": "Corrected product name to canonical 'Aspose.Cells FOSS for Go'.",
            }
        ]
    }


def _plan(*planned: str) -> dict:
    return {"links": [{"link_fact_id": f, "section_id": "documentation_resources"} for f in planned]}


def test_a_corrected_docs_list_requires_every_link_its_text_prints() -> None:
    plan = _plan("link_target:038", "link_target:039", "link_target:042")
    required = _kept_list_links(plan, _facts(), _dispositions("CORRECT_WITH_EVIDENCE"))
    assert required == dict.fromkeys(CITED, "documentation_resources")
    missing = _missing_kept_list_links(plan, _facts(), _dispositions("CORRECT_WITH_EVIDENCE"))
    assert sorted(m["link_fact_id"] for m in missing) == ["link_target:040", "link_target:041"]
    assert {m["section_id"] for m in missing} == {"documentation_resources"}


def test_a_link_cited_only_as_evidence_is_not_a_link_to_print() -> None:
    cited = [*CITED, "link_target:043"]  # products.aspose.com is nowhere in the unit's text
    required = _kept_list_links(
        _plan("link_target:038"), _facts(), _dispositions("CORRECT_WITH_EVIDENCE", cited)
    )
    assert "link_target:043" not in required
    assert "link_target:036" not in required  # an in-page anchor is never assigned
    assert set(required) == set(CITED)


def test_a_corrected_list_the_plan_carries_no_link_of_is_left_alone() -> None:
    assert _kept_list_links(_plan(), _facts(), _dispositions("CORRECT_WITH_EVIDENCE")) == {}


def test_only_corrected_lists_gain_this_not_other_dispositions_in_other_sections() -> None:
    plan = _plan("link_target:038")
    for disposition in ("SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED", "DEFER_UNRESOLVED"):
        assert _kept_list_links(plan, _facts(), _dispositions(disposition)) == {}
