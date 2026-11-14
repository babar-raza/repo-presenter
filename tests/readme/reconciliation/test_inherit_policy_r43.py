"""R43(3) (owner, 2026-11-14; BL-103): inherit-and-correct is a switchable Lane R policy, applied
only to repositories whose live README is aspose.org's published readme-refresh candidate, and
recorded in every Lane R seal's dependencies so the two engines stay separately evaluable."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.version_set import mechanism_scope
from repo_presenter.readme.bundle.evaluation import evaluate
from repo_presenter.readme.reconciliation import inherit
from repo_presenter.readme.reconciliation.dispositions import (
    fold_deterministic_sections,
    fold_inherited_published,
)

PUBLISHED = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"
UNPUBLISHED = "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET"


def _facts(repository: str) -> FactsDocument:
    return FactsDocument(repository, "a" * 40, (
        Fact("identity:repository", "identity", repository, (Evidence("data/registry.json"),)),
        Fact("inherited_unit:040.list", "inherited_unit",
             "- Formula expressions are preserved, but this is not a calculation engine.\n"
             "- Only `.xlsx` is supported.",
             (Evidence("README.md", "section 'X > Scope and Limitations'"),)),
        Fact("inherited_unit:041.paragraph", "inherited_unit", "Install the dev extras and run pytest.",
             (Evidence("README.md", "section 'X > Development and Testing'"),)),
        Fact("inherited_unit:012.list", "inherited_unit", "- Fast\n- Small",
             (Evidence("README.md", "section 'X > Features'"),)),
    ))


def _dispositions() -> dict:
    return {"dispositions": [
        {"unit_id": "inherited_unit:040.list", "disposition": "SUPERSEDE_REDUNDANT",
         "destination_section": "scope_limitations", "fact_ids": [], "rationale": "Restated."},
        {"unit_id": "inherited_unit:041.paragraph", "disposition": "SUPERSEDE_REDUNDANT",
         "destination_section": "development_testing", "fact_ids": [], "rationale": "Restated."},
        {"unit_id": "inherited_unit:012.list", "disposition": "SUPERSEDE_REDUNDANT",
         "destination_section": "key_capabilities", "fact_ids": [], "rationale": "Restated."},
    ]}


def test_the_mapping_is_aspose_org_s_published_list_mapped_onto_the_registry() -> None:
    document = json.loads(Path("data/aspose_published_readmes.json").read_text(encoding="utf-8"))
    registry = {
        (e["family"], e["platform"]): e["repository"]
        for e in json.loads(Path("data/registry.json").read_text(encoding="utf-8"))["entries"]
    }
    rows = document["repositories"]
    assert document["policy"] in inherit.POLICIES
    assert len(rows) == 31
    for row in rows:
        assert registry[(row["family"], row["platform"])] == row["repository"]
    source = Path("../aspose.org/data/readme_published_state.json")
    if source.is_file():  # the live aspose.org record, where the checkout is beside this one
        products = json.loads(source.read_text(encoding="utf-8"))["products"]
        assert {(p["family"], p["platform"]) for p in products} == {
            (r["family"], r["platform"]) for r in rows
        }


def test_only_a_listed_repository_inherits_and_the_switch_turns_it_off(monkeypatch) -> None:
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    assert inherit.lane_r_policy(PUBLISHED) == inherit.INHERIT_AND_CORRECT
    assert inherit.lane_r_policy(UNPUBLISHED) == inherit.REGENERATE
    monkeypatch.setenv(inherit.POLICY_ENV, inherit.REGENERATE)
    assert inherit.lane_r_policy(PUBLISHED) == inherit.REGENERATE
    monkeypatch.setenv(inherit.POLICY_ENV, "nonsense")  # an unknown value never switches anything
    assert inherit.lane_r_policy(PUBLISHED) == inherit.INHERIT_AND_CORRECT


def test_inherit_keeps_the_published_prose_of_the_deterministic_sections_only(monkeypatch) -> None:
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    output = _dispositions()
    fold_inherited_published(output, _facts(PUBLISHED))
    by = {e["unit_id"]: e for e in output["dispositions"]}
    assert by["inherited_unit:040.list"]["disposition"] == "VERIFIED_PRESERVE"
    assert by["inherited_unit:041.paragraph"]["disposition"] == "VERIFIED_PRESERVE"
    assert by["inherited_unit:040.list"]["rationale"].startswith("Kept as written (inherit-and-correct")
    # key capabilities stay model-authored (R43(2)); the published list there is not re-kept
    assert by["inherited_unit:012.list"]["disposition"] == "SUPERSEDE_REDUNDANT"


@pytest.mark.parametrize("repository,env", [(UNPUBLISHED, None), (PUBLISHED, inherit.REGENERATE)])
def test_inherit_is_a_no_op_off_the_list_or_under_regenerate(monkeypatch, repository, env) -> None:
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    if env:
        monkeypatch.setenv(inherit.POLICY_ENV, env)
    output = _dispositions()
    fold_inherited_published(output, _facts(repository))
    assert output == _dispositions()


def test_a_fit_supersession_is_never_undone(monkeypatch) -> None:
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    output = _dispositions()
    output["dispositions"][0]["rationale"] = "Superseded by the License section, which states it."
    fold_inherited_published(output, _facts(PUBLISHED))
    assert output["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_r43_2_keeps_a_carried_unit_for_every_repository(monkeypatch) -> None:
    monkeypatch.setenv(inherit.POLICY_ENV, inherit.REGENERATE)
    output = _dispositions()
    fold_deterministic_sections(output, _facts(UNPUBLISHED))
    by = {e["unit_id"]: e for e in output["dispositions"]}
    # nothing authors these sections now, so what their units had to carry is kept as written
    assert by["inherited_unit:040.list"]["disposition"] == "VERIFIED_PRESERVE"
    assert by["inherited_unit:041.paragraph"]["disposition"] == "VERIFIED_PRESERVE"
    assert by["inherited_unit:012.list"]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_the_seal_records_the_policy_outside_the_version_set(monkeypatch) -> None:
    from repo_presenter.core.llm.prompts import load_manifests
    from repo_presenter.readme.bundle.seal import current_dependencies_document

    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    prompts = load_manifests(Path("prompts"))
    published = current_dependencies_document(
        lane="R", source_revision="a" * 40, facts=_facts(PUBLISHED), prompts=prompts
    )
    other = current_dependencies_document(
        lane="R", source_revision="a" * 40, facts=_facts(UNPUBLISHED), prompts=prompts
    )
    assert published["lane_r_policy"] == {"name": "inherit_and_correct", "version": "1"}
    assert other["lane_r_policy"]["name"] == "regenerate"
    assert published["components"]["lane_r_policy"] == "1"
    # one version set for both policies (R10): the per-repository policy is an input, not a mechanism
    assert mechanism_scope(published, "R") == mechanism_scope(other, "R")
    # switching a seal's policy reopens it at reconciliation
    sealed = copy.deepcopy(published)
    sealed["lane_r_policy"]["name"] = "regenerate"
    changes = evaluate(sealed, published).changes
    assert [(c.dependency, c.reopens) for c in changes] == [("lane_r_policy", "RECONCILING")]


def test_recertification_counts_lane_r_per_policy() -> None:
    from repo_presenter.recertify import Recertification, policy_counts

    rows = [
        Recertification(PUBLISHED, "R", "a", "RECERTIFIED", lane_r_policy="inherit_and_correct"),
        Recertification(PUBLISHED, "L", "a", "RECERTIFIED"),
        Recertification(UNPUBLISHED, "R", "b", "NEEDS_REPAIR", lane_r_policy="regenerate"),
    ]
    assert policy_counts(rows) == {"inherit_and_correct": (1, 1), "regenerate": (0, 1)}


def test_a_lead_in_of_a_block_not_printed_beside_it_stays_superseded(monkeypatch) -> None:
    """Email .NET 015.paragraph ("Or add it directly to a project file.") introduced a superseded
    PackageReference block: kept alone it would print a lead-in to nothing."""
    monkeypatch.delenv(inherit.POLICY_ENV, raising=False)
    base = _facts(PUBLISHED)
    facts = FactsDocument(base.repository, base.source_revision, (
        *base.facts,
        Fact("inherited_unit:042.code_block", "inherited_unit", "```xml\n<PackageReference />\n```",
             (Evidence("README.md", "section 'X > Development and Testing'"),)),
    ))
    output = _dispositions()
    output["dispositions"].append(
        {"unit_id": "inherited_unit:042.code_block", "disposition": "SUPERSEDE_REDUNDANT",
         "destination_section": "installation", "fact_ids": [], "rationale": "Restated."}
    )
    fold_inherited_published(output, facts)
    by = {e["unit_id"]: e for e in output["dispositions"]}
    assert by["inherited_unit:041.paragraph"]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert by["inherited_unit:040.list"]["disposition"] == "VERIFIED_PRESERVE"
