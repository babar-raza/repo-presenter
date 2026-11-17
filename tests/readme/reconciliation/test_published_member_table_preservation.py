"""Published API member tables survive normalization (3D TypeScript run 43723761530).

The exact table body was downloaded from that run's present-typescript artifact. It has
Camera methods/properties that the generated type rows do not carry. No provider is used.
"""
from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.placement import api_listing_units
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.reconciliation import inherit
from repo_presenter.readme.reconciliation.dispositions import normalize
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
TABLE_ID = "inherited_unit:047.table"
TABLE = """| Class | Description |
|---|---|
| `Camera` | A viewpoint node entity with `moveForward` and `getBoundingBox` methods, and `nearPlane`, `farPlane`, `aspect`, `orthoHeight`, `fieldOfView`, `fieldOfViewX`/`Y`, `projectionType`, and `apertureMode` properties. |
| `Light` | A light-source node entity. Type is controlled by the `LightType` enumeration. |
| `LightType` | Enumeration of supported light kinds: `POINT`, `DIRECTIONAL`, `SPOT`, `AREA`, `VOLUME`. |
| `ProjectionType` | Enumeration of camera projection modes: `PERSPECTIVE` and `ORTHOGRAPHIC`. |"""
NAMES = ("Camera", "Light", "LightType", "ProjectionType")


def case():
    base = make_facts()
    facts = replace(base, repository=REPOSITORY, facts=(
        *base.facts,
        *(Fact("public_symbol:" + name.lower(), "public_symbol", name,
               (Evidence("src/" + name + ".ts"),),
               attributes={"symbol_kind": "class" if name in NAMES[:2] else "enum"})
          for name in NAMES),
        Fact(TABLE_ID, "inherited_unit", TABLE,
             (Evidence("README.md", "section 'X > API Reference > Scene graph'"),),
             attributes={"section": "X > API Reference > Scene graph"}),
    ))
    dispositions = copy.deepcopy(_dispositions())
    dispositions["dispositions"].append({
        "unit_id": TABLE_ID, "disposition": "SUPERSEDE_REDUNDANT",
        "destination_section": "api_reference",
        "fact_ids": ["public_symbol:" + name.lower() for name in NAMES],
        "rationale": "The generated table replaces these types.",
    })
    return facts, dispositions


def row(output):
    return next(e for e in output["dispositions"] if e["unit_id"] == TABLE_ID)


def test_the_real_published_table_keeps_members_through_normalize_and_render(monkeypatch):
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    facts, output = case()
    assert TABLE_ID in api_listing_units(facts)
    normalize(output, facts)
    assert row(output)["disposition"] == "VERIFIED_PRESERVE"
    assert row(output)["destination_section"] == "api_reference"
    # A stored result is normalized again by repair/re-certification: preserving is stable.
    first = copy.deepcopy(row(output))
    normalize(output, facts)
    assert row(output) == first
    plan = _plan()
    plan_checks(plan, facts, dispositions=output, ecosystem="python")
    readme = render_readme(make_entry(), facts, plan, _units(), output)
    for member in ("moveForward", "getBoundingBox", "nearPlane", "orthoHeight", "fieldOfViewX", "projectionType"):
        assert "`" + member + "`" in readme
    assert readme.index("`moveForward`") < readme.index("</details>", readme.index("## API Reference"))


@pytest.mark.parametrize("repository,policy", [
    (REPOSITORY, inherit.REGENERATE),
    ("aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET", inherit.INHERIT_AND_CORRECT),
])
def test_other_policies_keep_the_existing_table_decision(monkeypatch, repository, policy):
    monkeypatch.setenv(inherit.POLICY_ENV, policy)
    facts, output = case()
    normalize(output, replace(facts, repository=repository))
    assert row(output)["disposition"] == "SUPERSEDE_REDUNDANT"


@pytest.mark.parametrize("disposition", ["OMIT_UNSUPPORTED", "CORRECT_WITH_EVIDENCE", "DEFER_UNRESOLVED"])
def test_explicit_refutations_are_not_restored(monkeypatch, disposition):
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    facts, output = case()
    row(output).update(disposition=disposition, destination_section=None,
                       rationale="Evidence requires withholding this content.")
    normalize(output, facts)
    assert row(output)["disposition"] == disposition


def test_a_registered_false_row_is_still_withheld_after_restoration(monkeypatch):
    from types import SimpleNamespace

    from repo_presenter.readme.validation import must_correct

    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    false_quote = "A light-source node entity. Type is controlled by the `LightType` enumeration."
    citation = "finding:table-row-test"
    monkeypatch.setattr(must_correct, "open_finding_citations",
                        lambda *args, **kwargs: {citation: SimpleNamespace(quote=false_quote)})
    facts, output = case()
    normalize(output, facts)
    assert citation in row(output)["fact_ids"]
    plan = _plan()
    plan_checks(plan, facts, dispositions=output, ecosystem="python")
    readme = render_readme(make_entry(), facts, plan, _units(), output)
    assert false_quote not in readme
    assert "`moveForward`" in readme
