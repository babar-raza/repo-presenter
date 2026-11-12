"""The maintainers' table of contents is navigation, not a list kept in the opening
(Aspose.Cells-FOSS-for-Go, hosted Lane R: ``006.list`` was VERIFIED_PRESERVE into the opening;
placement de-linked its anchors, the printed text differed from the unit, and disposition_coverage
refused it). Synthetic dispositions table."""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    coverage_findings,
    is_table_of_contents,
    normalize,
)

_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
_SECTION = "Aspose.Cells FOSS for Go"

_TOC = (
    "- [Overview](#overview)\n"
    "- [Installation](#installation)\n"
    "  - [Requirements](#requirements)\n"
    "  - [Quick start](#quick-start)\n"
    "- [API](#api)\n"
    "- [License](#license)\n"
    "Requires Go 1.24.5+"
)
_EXTERNAL = (
    "- [Docs](https://docs.example.com/docs)\n"
    "- [Blog](https://blog.example.com/post)\n"
    "- [Issues](https://github.com/o/r/issues)\n"
    "- [Overview](#overview)"
)


def _unit(uid: str, text: str) -> Fact:
    return Fact(
        uid, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": _SECTION}
    )


def _facts(list_text: str) -> FactsDocument:
    units = (
        _unit("inherited_unit:005.paragraph", "A Go library for spreadsheets."),
        _unit("inherited_unit:006.list", list_text),
    )
    base = (Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),)
    return FactsDocument(_REPO, "f" * 40, (*base, *units))


def _table(disposition: str = "VERIFIED_PRESERVE") -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:005.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "opening",
                "fact_ids": ["identity:repository"],
                "rationale": "Lead paragraph.",
            },
            {
                "unit_id": "inherited_unit:006.list",
                "disposition": disposition,
                "destination_section": "opening",
                "fact_ids": [],
                "rationale": "Kept as written.",
            },
        ]
    }


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


def test_a_mostly_anchor_list_is_recognised_as_a_table_of_contents() -> None:
    assert is_table_of_contents(_TOC)
    assert not is_table_of_contents(_EXTERNAL)
    assert not is_table_of_contents("- [Overview](#overview)\n- [API](#api)")


def test_a_kept_table_of_contents_becomes_navigation() -> None:
    for disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE"):
        facts = _facts(_TOC)
        output = _table(disposition)
        normalize(output, facts)
        toc = _by_unit(output)["inherited_unit:006.list"]
        assert toc["disposition"] == "SUPERSEDE_REDUNDANT"
        assert toc["destination_section"] == "navigation"
        assert "identity:repository" in toc["fact_ids"]
        assert "table of contents" in toc["rationale"].lower()
        assert len(toc["rationale"]) <= 160
        assert not [
            gap for gap in coverage_findings(output, facts) if gap.unit_id == "inherited_unit:006.list"
        ]


def test_a_list_of_external_links_stays_preserved() -> None:
    output = _table()
    normalize(output, _facts(_EXTERNAL))
    entry = _by_unit(output)["inherited_unit:006.list"]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "opening"


def test_a_table_of_contents_already_superseded_is_left_alone() -> None:
    output = _table("SUPERSEDE_REDUNDANT")
    output["dispositions"][1]["destination_section"] = "navigation"
    output["dispositions"][1]["fact_ids"] = ["identity:repository"]
    normalize(output, _facts(_TOC))
    entry = _by_unit(output)["inherited_unit:006.list"]
    assert entry["rationale"] == "Kept as written."
