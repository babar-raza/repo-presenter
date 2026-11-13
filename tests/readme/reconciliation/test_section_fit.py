"""BL-004 section fit, from the real Aspose.3D FOSS for .NET Lane R units (seal 03b940a46f7b,
revision 52b0f00ebf28).

Owner (P0): "Documentation & Resources is not complete because its content is shown in Scope and
Limitations section. AND This project is licensed under the MIT License, as stated in the LICENSE
file. Above line does not fit Scope and Limitations."

Root cause, measured on the sealed artifacts: (1) reconciliation's ``_rehome_unprintable_kind_units``
moved the maintainers' links list (059.list, filed by the model in documentation_resources) to the
"nearest" printable section, scope_limitations, so planning's kept-list backstop never owed its
docs/kb/reference links to Documentation and Resources and the list printed verbatim under Scope
and Limitations; (2) the model kept the License paragraph (070.paragraph) in scope_limitations,
and the plan made a limitation slot of ``license:file``/``license:spdx``, authored as "This project
is licensed under the MIT License" -- a limitation it is not.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.planning import (
    _drop_license_limitations,
    _kept_list_links,
    link_list_targets,
)
from repo_presenter.readme.reconciliation.dispositions import normalize
from repo_presenter.readme.validation import units as units_module
from repo_presenter.readme.validation.units import section_fit_failures

_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
_ROOT = "Aspose.3D FOSS for .NET"

# inherited_unit:059.list and inherited_unit:070.paragraph, verbatim from the sealed facts.json.
LINKS_059 = (
    "- **[Getting started guide](https://docs.aspose.org/3d/net/)** — installation, walkthroughs, "
    "and feature guides for this library.\n"
    "- **[How-to articles and FAQ](https://kb.aspose.org/3d/net/)** — task-focused how-tos and "
    "answers to common questions.\n"
    "- **[Full API reference](https://reference.aspose.org/3d/net/)** — complete, generated "
    "reference documentation for every public type.\n"
    "- **[Implementation progress notes](docs/foss-net-progress.md)** — current FOSS-edition "
    "implementation status, in the repository.\n"
    "- **[Release 26.2.0 notes](docs/release-26.2.0.md)** — change log for this release, in the "
    "repository.\n"
    "- **[AGENTS.md](AGENTS.md)** — implementation status and development guidelines for "
    "contributors.\n"
    "- **[Issues and feature requests](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET/"
    "issues)** — report a bug or request a feature on GitHub."
)
LICENSE_070 = (
    "This project is licensed under the [MIT License](LICENSE). The MIT License permits use, "
    "copying, modification, distribution, sublicensing, and commercial use, provided its copyright "
    "and permission notice are retained. The software is provided without warranty."
)
_LINKS = {
    "link_target:004": "LICENSE",
    "link_target:020": "https://docs.aspose.org/3d/net/",
    "link_target:021": "https://kb.aspose.org/3d/net/",
    "link_target:022": "https://reference.aspose.org/3d/net/",
    "link_target:023": "docs/foss-net-progress.md",
    "link_target:024": "docs/release-26.2.0.md",
    "link_target:025": "AGENTS.md",
    "link_target:026": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET/issues",
}
_DOC_LINKS = [f"link_target:0{n}" for n in range(20, 27)]


def _facts() -> FactsDocument:
    def unit(uid: str, text: str, heading: str) -> Fact:
        return Fact(
            uid,
            "inherited_unit",
            text,
            (Evidence("README.md", None),),
            attributes={"section": f"{_ROOT} > {heading}"},
        )

    return FactsDocument(
        _REPO,
        "52b0f00ebf28a0b4173921725ff170685ec2c502",
        (
            Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
            Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
            Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
            *(Fact(i, "link_target", v, (Evidence("x"),)) for i, v in _LINKS.items()),
            unit("inherited_unit:059.list", LINKS_059, "Documentation & Resources"),
            unit("inherited_unit:070.paragraph", LICENSE_070, "License"),
        ),
    )


def _dispositions(links_destination: str) -> dict[str, Any]:
    """The model's own S4 picks as sealed (before the old re-homing rewrote 059's destination)."""
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:059.list",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": links_destination,
                "fact_ids": list(_DOC_LINKS),
                "rationale": "The list items are all verified links to documentation.",
            },
            {
                "unit_id": "inherited_unit:070.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "scope_limitations",
                "fact_ids": ["license:file", "license:spdx"],
                "rationale": "The paragraph describes the MIT license, which is verified; it is "
                "kept as written for completeness.",
            },
        ]
    }


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


@pytest.mark.parametrize("filed", ["documentation_resources", "scope_limitations"])
def test_the_links_list_lands_in_documentation_resources(filed: str) -> None:
    output = _dispositions(filed)
    normalize(output, _facts())
    entry = _by_unit(output)["inherited_unit:059.list"]
    assert entry["destination_section"] == "documentation_resources"
    assert entry["disposition"] == "VERIFIED_PRESERVE"


def test_every_link_of_the_kept_list_is_owed_to_documentation_resources() -> None:
    """The sealed plan assigned only 023-026 there; docs/kb/reference (020-022) were missing."""
    facts = _facts()
    output = _dispositions("documentation_resources")
    normalize(output, facts)
    plan = {
        "links": [
            {"link_fact_id": f"link_target:0{n}", "section_id": "documentation_resources"}
            for n in (23, 24, 25, 26)
        ]
    }
    owed = _kept_list_links(plan, facts, output)
    assert {fid for fid, section in owed.items() if section == "documentation_resources"} >= set(
        _DOC_LINKS
    )


def test_a_links_list_is_owed_even_when_the_plan_assigned_none_of_its_links_there() -> None:
    facts = _facts()
    output = _dispositions("documentation_resources")
    normalize(output, facts)
    owed = _kept_list_links({"links": []}, facts, output)
    assert set(_DOC_LINKS) <= set(owed)


def test_link_list_targets_reads_every_item() -> None:
    assert link_list_targets(LINKS_059, _facts()) == _DOC_LINKS
    assert link_list_targets(LINKS_059 + "\n- Ask on the forum.", _facts()) is None
    assert link_list_targets(LICENSE_070, _facts()) is None


def test_the_license_paragraph_is_superseded_by_the_license_section() -> None:
    output = _dispositions("documentation_resources")
    normalize(output, _facts())
    entry = _by_unit(output)["inherited_unit:070.paragraph"]
    assert entry["disposition"] == "SUPERSEDE_REDUNDANT"
    assert entry["destination_section"] == "license"
    assert {"license:file", "license:spdx"} <= set(entry["fact_ids"])
    assert len(entry["rationale"]) <= 160


def test_a_limitation_about_the_license_api_is_not_moved() -> None:
    """``License``/``Metered`` are API classes a real limitation names (061.list's last item)."""
    facts = _facts()
    text = (
        "License and trial-management APIs (`License`, `Metered`) are present for API-surface "
        "compatibility but are not applicable to this open-source edition."
    )
    unit = Fact(
        "inherited_unit:061.paragraph",
        "inherited_unit",
        text,
        (Evidence("README.md", None),),
        attributes={"section": f"{_ROOT} > Scope and Limitations"},
    )
    facts = FactsDocument(facts.repository, facts.source_revision, (*facts.facts, unit))
    output = _dispositions("documentation_resources")
    output["dispositions"].append(
        {
            "unit_id": "inherited_unit:061.paragraph",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "scope_limitations",
            "fact_ids": ["license:file"],
            "rationale": "A verified limitation.",
        }
    )
    normalize(output, facts)
    entry = _by_unit(output)["inherited_unit:061.paragraph"]
    assert entry["destination_section"] == "scope_limitations"
    assert entry["disposition"] == "VERIFIED_PRESERVE"


def test_the_license_only_limitation_slot_is_dropped() -> None:
    """The sealed plan's six slots: the sixth cites only license facts and hands 061.list, which
    the other five already hand."""
    slots = [
        {"fact_ids": ["install_command:dotnet"], "unit_ids": ["inherited_unit:061.list"]},
        {"fact_ids": ["format:input.ply", "format:output.ply"], "unit_ids": ["inherited_unit:061.list"]},
        {"fact_ids": ["public_symbol:aspose.threed"], "unit_ids": ["inherited_unit:061.list"]},
        {"fact_ids": ["public_symbol:aspose"], "unit_ids": ["inherited_unit:061.list"]},
        {"fact_ids": ["format:input.3mf", "format:output.3mf"], "unit_ids": ["inherited_unit:061.list"]},
        {"fact_ids": ["license:file", "license:spdx"], "unit_ids": ["inherited_unit:061.list"]},
    ]
    plan = {"material_limitations": [dict(s) for s in slots]}
    _drop_license_limitations(plan, _facts())
    assert plan["material_limitations"] == slots[:5]


def test_a_license_fact_is_stripped_from_a_real_limitation_slot() -> None:
    """Cells C++'s shape: a real limitation slot that also cited ``license:file``."""
    plan = {
        "material_limitations": [
            {"fact_ids": ["license:file"], "unit_ids": ["inherited_unit:055.paragraph"]}
        ]
    }
    _drop_license_limitations(plan, _facts())
    assert plan["material_limitations"] == [
        {"fact_ids": [], "unit_ids": ["inherited_unit:055.paragraph"]}
    ]


# The sealed README's Scope and Limitations, trimmed (the two misplaced shapes, verbatim).
_SEALED_SCOPE = (
    "## Scope and Limitations\n\n"
    "- Rendering is not implemented in this FOSS build — `Scene.Render` throws "
    "`NotImplementedException`.\n"
    "- `Text` watermarking is not currently functional, and `License` and `Metered` APIs are present "
    "for API-surface compatibility but are not applicable to this open-source edition.\n"
    "- This project is licensed under the MIT `License`, as stated in the LICENSE file.\n\n"
    + LINKS_059
    + "\n\n## Development and Testing\n\nRun the tests.\n"
)
_FIXED_SCOPE = (
    "## Scope and Limitations\n\n"
    "- Rendering is not implemented in this FOSS build — `Scene.Render` throws "
    "`NotImplementedException`.\n"
    "- `Text` watermarking is not currently functional, and `License` and `Metered` APIs are present "
    "for API-surface compatibility but are not applicable to this open-source edition.\n\n"
    "## Development and Testing\n\nRun the tests.\n"
)


def _candidate(readme: str, plan: dict[str, Any] | None = None) -> Any:
    return SimpleNamespace(readme=readme, facts=_facts(), plan=plan or {})


def test_the_sealed_scope_section_fails_section_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(units_module, "placements_of", lambda candidate: [])
    plan = {"material_limitations": [{"fact_ids": ["license:file", "license:spdx"]}]}
    failures = section_fit_failures(_candidate(_SEALED_SCOPE, plan))
    links = [f for f in failures if "resource link" in f.detail]
    licence = [f for f in failures if "license" in f.detail and "resource link" not in f.detail]
    assert len(links) == 7
    assert len(licence) == 1
    assert licence[0].stage == "PLANNING"
    assert all(f.section == "scope_limitations" for f in failures)


def test_the_fixed_scope_section_passes_section_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(units_module, "placements_of", lambda candidate: [])
    assert section_fit_failures(_candidate(_FIXED_SCOPE)) == []
