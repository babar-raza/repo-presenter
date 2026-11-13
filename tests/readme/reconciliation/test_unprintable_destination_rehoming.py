"""A kept unit the model filed in a section that is generated-only for its kind is moved to the
nearest section that actually prints it (``documentation_resources``'s renderer -- ``composition/
renderer.py``'s ``_documentation_resources`` -- only walks the plan's own generated link entries,
never a placed unit's text: ``readme/repair/restore_units.py``'s ``_GENERATED_ONLY_DESTINATIONS``
names the same fact for its own, restore-time re-homing).

Real case (Aspose.Cells-FOSS-for-Go, fresh Lane R generation): the model kept the maintainers'
"Documentation & Resources" links list verbatim and filed it in ``documentation_resources`` --
topically exactly right, mechanically impossible -- and BC-05/``disposition_coverage`` both
REJECTed: "inherited_unit:055.list was placed in documentation_resources but the candidate does
not render it there"."""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import normalize

_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
_SECTION = "Aspose.Cells FOSS for Go"

# The real kept unit's text (inherited_unit:055.list), trimmed to its first two items.
_LINKS_LIST = (
    "- **[Getting started guide](https://docs.aspose.org/cells/go/)** — Go documentation for\n"
    "  Aspose.Cells FOSS: loading, editing, styling, and saving spreadsheets.\n"
    "- **[How-to guides & FAQ](https://kb.aspose.org/cells/go/)** — Go knowledge base for Aspose.Cells\n"
    "  FOSS: how-to articles, FAQ, and troubleshooting guides.\n"
)


def _unit(uid: str, text: str, section: str) -> Fact:
    return Fact(
        uid, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": section}
    )


def _facts(unit_text: str, heading: str = "Documentation & Resources") -> FactsDocument:
    units = (_unit("inherited_unit:055.list", unit_text, f"{_SECTION} > {heading}"),)
    base = (
        Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
        Fact(
            "link_target:038", "link_target", "https://docs.aspose.org/cells/go/", (Evidence("x"),)
        ),
        Fact("link_target:039", "link_target", "https://kb.aspose.org/cells/go/", (Evidence("x"),)),
    )
    return FactsDocument(_REPO, "f" * 40, (*base, *units))


def _table(disposition: str, destination: str) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:055.list",
                "disposition": disposition,
                "destination_section": destination,
                "fact_ids": ["link_target:038", "link_target:039"],
                "rationale": "The list of documentation links is kept as written.",
            }
        ]
    }


def _entry(output: dict[str, Any]) -> dict[str, Any]:
    return output["dispositions"][0]


def test_a_kept_links_list_filed_in_documentation_resources_stays_there() -> None:
    """BL-004 (owner P0): a list whose every item is a link the plan can assign IS Documentation
    and Resources' material; planning owes each of its links to that section's own link lines
    (``planning._kept_list_links``), so it is no longer re-homed into Scope and Limitations."""
    for disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE"):
        output = _table(disposition, "documentation_resources")
        normalize(output, _facts(_LINKS_LIST))
        entry = _entry(output)
        assert entry["destination_section"] == "documentation_resources"
        assert entry["disposition"] == disposition
        assert "link_target:038" in entry["fact_ids"]


def test_a_kept_list_with_an_unlinked_item_filed_in_documentation_resources_is_rehomed() -> None:
    """A list the section cannot carry as link lines (an item with no link) is still re-homed."""
    text = _LINKS_LIST + "- Community support is available on the forum.\n"
    for disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE"):
        output = _table(disposition, "documentation_resources")
        normalize(output, _facts(text))
        entry = _entry(output)
        assert entry["destination_section"] != "documentation_resources"
        assert entry["disposition"] == disposition
        assert "prints nothing from a placed unit" in entry["rationale"].lower()
        assert len(entry["rationale"]) <= 160


_LIMITS_LIST = (
    "- Formula recalculation is not implemented; cached values are kept as written.\n"
    "- Charts are read but not rendered.\n"
)


def test_a_unit_already_in_a_section_that_prints_it_is_left_alone() -> None:
    output = _table("VERIFIED_PRESERVE", "scope_limitations")
    normalize(output, _facts(_LIMITS_LIST, heading="Scope and Limitations"))
    entry = _entry(output)
    assert entry["destination_section"] == "scope_limitations"
    assert entry["rationale"] == "The list of documentation links is kept as written."


def test_a_links_list_filed_in_scope_and_limitations_moves_to_documentation_resources() -> None:
    """BL-004 section fit: resource links are never a limitation."""
    output = _table("VERIFIED_PRESERVE", "scope_limitations")
    normalize(output, _facts(_LINKS_LIST, heading="Scope and Limitations"))
    entry = _entry(output)
    assert entry["destination_section"] == "documentation_resources"
    assert entry["rationale"].startswith("Kept in documentation_resources: a list of resource links")


def test_a_paragraph_filed_in_documentation_resources_is_also_rehomed() -> None:
    """Not just a list: any kind that section prints nothing of is caught the same way."""
    output = _table("VERIFIED_PRESERVE", "documentation_resources")
    output["dispositions"][0]["unit_id"] = "inherited_unit:055.paragraph"
    units = (
        _unit(
            "inherited_unit:055.paragraph", _LINKS_LIST, f"{_SECTION} > Documentation & Resources"
        ),
    )
    base = (
        Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
        Fact(
            "link_target:038", "link_target", "https://docs.aspose.org/cells/go/", (Evidence("x"),)
        ),
        Fact("link_target:039", "link_target", "https://kb.aspose.org/cells/go/", (Evidence("x"),)),
    )
    normalize(output, FactsDocument(_REPO, "f" * 40, (*base, *units)))
    entry = _entry(output)
    assert entry["destination_section"] != "documentation_resources"
