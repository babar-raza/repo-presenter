"""P2/P4 (2026-11-14): zero-call re-certification judges a sealed Lane R candidate under the
reconciliation folds current code applies at S4 (``recertify.current_dispositions`` /
``current_plan``), and a findings-register quote in a nested list sub-item withholds that
sub-item only.

The fixtures are the real units of the sealed Aspose.Email-FOSS-for-Cpp Lane R candidate (seal
revision c844a467) and its two OPEN register rows in ``data/readme_findings.json``
(finding:5d6facf1dfb3, finding:6d38822c85aa): aspose.org's published signature bullets
``get(property_id, property_type) -> mapi_property`` and ``get_property_value(property_id,
property_type) -> std::any``, each one sub-item of a list whose single top-level item names the
type. Withheld whole, each list would print nothing, so the register fold could not cite the
rows and BC-18 failed on maintainer text the register had already settled.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.must_correct import (
    omission_holds,
    open_finding_citations,
    without_quoted_items,
)
from repo_presenter.recertify import current_dispositions, current_plan

REPOSITORY = "aspose-email-foss/Aspose.Email-FOSS-for-Cpp"

UNIT_053 = """- `mapi_message`
  - `create(subject, body, unicode_strings) -> mapi_message`
  - `from_file(path, strict) -> mapi_message` / `from_stream(stream, strict) -> mapi_message`
  - `set_property(property_id, property_type, value, flags) -> mapi_property` /
    `get_property_value(property_id, property_type) -> std::any`
  - `validation_issues() -> std::vector<std::string>`"""

UNIT_059_003 = """- `mapi_property_collection`
  - `set(property) -> mapi_property`, `add(property_id, property_type, value, flags) -> mapi_property`
  - `get(property_id, property_type) -> mapi_property`,
    `remove(property_id, property_type) -> void`, `items() -> std::map<std::pair<std::uint16_t, std::uint16_t>, mapi_property>`"""

QUOTE_GET = "get(property_id, property_type) -> mapi_property"
QUOTE_VALUE = "get_property_value(property_id, property_type) -> std::any"

#: The two OPEN rows of ``data/readme_findings.json`` for this repository, verbatim (2026-11-14).
REGISTER_ROWS = [
    {
        "description": f"confirmed false claim: {QUOTE_GET}",
        "evidence": "include/aspose/email/foss/msg/mapi_property_collection.hpp:~16@c844a467cf7f2503819b655f4d6ceaef91056c40",
        "first_seen_at": "2026-11-12",
        "quote": QUOTE_GET,
        "repository": REPOSITORY,
        "resolved_at": None,
        "route": "lane_r",
        "status": "OPEN",
        "truth": "mapi_property_collection::get returns a (const) mapi_property pointer (nullptr "
        "when missing), with property_type an optional parameter.",
    },
    {
        "description": f"confirmed false claim: {QUOTE_VALUE}",
        "evidence": "include/aspose/email/foss/msg/mapi_message.hpp:~63@c844a467cf7f2503819b655f4d6ceaef91056c40",
        "first_seen_at": "2026-11-12",
        "quote": QUOTE_VALUE,
        "repository": REPOSITORY,
        "resolved_at": None,
        "route": "lane_r",
        "status": "OPEN",
        "truth": "It returns `const std::any*` (nullptr when absent) and property_type is an "
        "optional<uint16_t> defaulting to nullopt.",
    },
]


@pytest.fixture(autouse=True)
def email_cpp_register(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from repo_presenter.readme.validation import must_correct

    path = tmp_path / "readme_findings.json"
    path.write_text(json.dumps({"schema_version": 1, "findings": REGISTER_ROWS}), encoding="utf-8")
    monkeypatch.setattr(must_correct, "DEFAULT_FINDINGS_PATH", path)


def test_a_quote_in_a_nested_sub_item_withholds_that_sub_item_only() -> None:
    printed = without_quoted_items(UNIT_053, [QUOTE_VALUE])
    assert QUOTE_VALUE not in printed
    assert "set_property(property_id" not in printed  # the same sub-item, one line up
    assert printed.splitlines() == [
        "- `mapi_message`",
        "  - `create(subject, body, unicode_strings) -> mapi_message`",
        "  - `from_file(path, strict) -> mapi_message` / `from_stream(stream, strict) -> mapi_message`",
        "  - `validation_issues() -> std::vector<std::string>`",
    ]
    assert omission_holds("inherited_unit:053.list", UNIT_053, [QUOTE_VALUE])
    assert omission_holds("inherited_unit:059.003.list", UNIT_059_003, [QUOTE_GET])


def test_a_quote_in_a_top_level_item_still_withholds_the_whole_item() -> None:
    text = "- Reads `.msg` files.\n  - nested detail\n- Writes `.eml` files."
    assert without_quoted_items(text, ["Reads `.msg` files."]) == "- Writes `.eml` files."


def test_every_item_quoted_leaves_the_list_unchanged() -> None:
    text = "- one claim\n- two claim"
    assert without_quoted_items(text, ["one claim", "two claim"]) == text


def _facts(*units: tuple[str, str], extra: tuple[Fact, ...] = ()) -> FactsDocument:
    facts = tuple(
        Fact(unit_id, "inherited_unit", text, (Evidence("README.md", "section 'API'"),),
             attributes={"section": "Aspose.Email FOSS for C++ > API Reference"})
        for unit_id, text in units
    )
    return FactsDocument(REPOSITORY, "c844a467cf7f2503819b655f4d6ceaef91056c40", facts + extra)


def _kept(unit_id: str, section: str = "api_reference") -> dict:
    return {
        "unit_id": unit_id,
        "disposition": "VERIFIED_PRESERVE",
        "destination_section": section,
        "fact_ids": [],
        "rationale": "Kept in the collapsed API Reference: it lists public API members.",
    }


def test_the_register_folds_cite_the_rows_on_the_sealed_email_cpp_units() -> None:
    rows = open_finding_citations(REPOSITORY)
    ids = {cid for cid, row in rows.items() if row.quote in (QUOTE_GET, QUOTE_VALUE)}
    assert ids == {"finding:5d6facf1dfb3", "finding:6d38822c85aa"}
    facts = _facts(("inherited_unit:053.list", UNIT_053), ("inherited_unit:059.003.list", UNIT_059_003))
    sealed = {"dispositions": [_kept("inherited_unit:053.list"), _kept("inherited_unit:059.003.list")]}
    before = copy.deepcopy(sealed)
    folded = current_dispositions(sealed, facts, {"links": [], "material_limitations": []})
    assert sealed == before  # pure
    cited = {entry["unit_id"]: entry["fact_ids"] for entry in folded["dispositions"]}
    assert cited == {
        "inherited_unit:053.list": ["finding:6d38822c85aa"],
        "inherited_unit:059.003.list": ["finding:5d6facf1dfb3"],
    }


SCOPE_LIST = (
    "- Rendering is not implemented in this build.\n"
    "- get(property_id, property_type) -> mapi_property is the lookup signature."
)


def test_a_scope_unit_is_withheld_only_when_no_planned_limitation_covers_it() -> None:
    facts = _facts(("inherited_unit:064.list", SCOPE_LIST))
    sealed = {"dispositions": [_kept("inherited_unit:064.list", "scope_limitations")]}
    uncovered = current_dispositions(sealed, facts, {"links": [], "material_limitations": []})
    assert uncovered["dispositions"][0]["fact_ids"] == ["finding:5d6facf1dfb3"]
    covered_plan = {
        "links": [],
        "material_limitations": [{"fact_ids": [], "unit_ids": ["inherited_unit:064.list"]}],
    }
    covered = current_dispositions(sealed, facts, covered_plan)
    assert covered["dispositions"][0]["fact_ids"] == []


RESOURCES = (
    "- **[Getting started guide](https://docs.aspose.org/3d/net/)** — installation, walkthroughs, "
    "and feature guides for this library.\n"
    "- **[How-to articles and FAQ](https://kb.aspose.org/3d/net/)** — task-focused how-tos and "
    "answers to common questions."
)


def test_a_resource_links_list_kept_in_scope_moves_to_documentation_with_its_links() -> None:
    """3D .NET ``059.list`` (seal 52b0f00e): kept in Scope and Limitations, BC-05 section fit."""
    links = (
        Fact("link_target:020", "link_target", "https://docs.aspose.org/3d/net/", (Evidence("README.md"),)),
        Fact("link_target:021", "link_target", "https://kb.aspose.org/3d/net/", (Evidence("README.md"),)),
    )
    facts = FactsDocument(
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        "52b0f00ebf28a0b4173921725ff170685ec2c502",
        (
            Fact("identity:repository", "identity", "aspose-3d-foss/Aspose.3D-FOSS-for-.NET", (Evidence("x"),)),
            Fact("inherited_unit:059.list", "inherited_unit", RESOURCES,
                 (Evidence("README.md", "section 'Documentation & Resources'"),),
                 attributes={"section": "Aspose.3D FOSS for .NET > Documentation & Resources"}),
            *links,
        ),
    )
    entry = _kept("inherited_unit:059.list", "scope_limitations")
    entry["fact_ids"] = ["link_target:020", "link_target:021"]
    plan = {"links": [], "material_limitations": [], "sections": []}
    folded = current_dispositions({"dispositions": [entry]}, facts, plan)
    assert folded["dispositions"][0]["destination_section"] == "documentation_resources"
    updated = current_plan(plan, facts, folded)
    assert updated["links"] == [
        {"link_fact_id": "link_target:020", "section_id": "documentation_resources"},
        {"link_fact_id": "link_target:021", "section_id": "documentation_resources"},
    ]
    assert plan["links"] == []  # pure

    from repo_presenter.readme.composition.list_coverage import kept_link_descriptions

    assert kept_link_descriptions(folded, facts) == {
        "link_target:020": "installation, walkthroughs, and feature guides for this library.",
        "link_target:021": "task-focused how-tos and answers to common questions.",
    }
