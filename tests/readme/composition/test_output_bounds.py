"""Targeted tests for output_bounds.py's citation caps on an authoring_schema call.

Real hosted defect (aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET, run 41121245347):
section_authoring failed with TruncatedOutput ("output truncated at the manifest's
max_output_tokens"). The truncated reply's own single-fact "hub:public_symbol:
aspose.imaging.foss" unit had a fact_ids array that repeated its one allowed fact id hundreds
of times with no sign of stopping -- the same "unbounded field under constrained decoding has
no terminating condition" disease the manifest's own text.maxLength: 2200 was already added
for (G4-W17 arrival item 75), here hitting an array instead of a string.

bound_authoring_citations() already exists and is already proven live (wired into
authoring_retry.py's narrowed re-ask), but was never applied to the INITIAL/universal ask --
exactly the attempt that failed on Imaging-.NET. Confirmed from readme/investigation/dossier.py's
own comment ("the gateway answers HTTP 400 to uniqueItems, probed live 2026-10-05") that
uniqueItems is NOT a safe keyword for this gateway: an earlier version of this fix added
maxItems AND uniqueItems directly inside authoring_schema() itself, dispatched a live
verification run, and that run failed immediately with "gateway answered HTTP 400" -- caught
before being declared done, reverted, and replaced with this module's own already-proven
maxItems-only bound, wired into cascade.py's initial ask instead of inventing new, riskier
schema logic.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.authoring import SectionTask, authoring_schema
from repo_presenter.readme.composition.output_bounds import (
    bound_authoring_citations,
    largest_slot_citation_count,
    omittable_count,
)
from support import REPO_ROOT

SECTION_AUTHORING = load_manifests(REPO_ROOT / "prompts")["section_authoring"]


def _hub_task() -> SectionTask:
    """The real shape of aspose-imaging-foss/.NET's own failing task: "intro" plus one
    single-fact hub slot."""
    return SectionTask(
        section_id="api_reference",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose.imaging.foss", "package:name"}),
        slots=("intro", "hub:public_symbol:aspose.imaging.foss"),
        slot_facts={
            "hub:public_symbol:aspose.imaging.foss": frozenset(
                {"public_symbol:aspose.imaging.foss"}
            )
        },
    )


def test_bound_authoring_citations_caps_a_single_fact_slots_fact_ids_array() -> None:
    task = _hub_task()
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    hub_item = schema["properties"]["units"]["prefixItems"][1]
    fact_ids = hub_item["properties"]["fact_ids"]
    # citable() also admits the section's neutral identity:/package: facts, so 2 here
    # (package:name, public_symbol:aspose.imaging.foss), never an unbounded array.
    assert fact_ids["maxItems"] == 2
    assert fact_ids["items"]["enum"] == [
        "package:name",
        "public_symbol:aspose.imaging.foss",
    ]


def test_bound_authoring_citations_never_adds_unique_items() -> None:
    """Pins the gateway constraint directly, not just by omission: readme/investigation/
    dossier.py's own comment records that this gateway answers HTTP 400 to uniqueItems
    (probed live 2026-10-05), confirmed the hard way a second time this round when an earlier
    version of this exact fix added it and a live verification run failed immediately with
    that exact error. uniqueItems must never appear in a bounded fact_ids schema."""
    task = _hub_task()
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    for item in schema["properties"]["units"]["prefixItems"]:
        assert "uniqueItems" not in item["properties"]["fact_ids"]
    assert "uniqueItems" not in schema["properties"].get("omitted", {})


def test_bound_authoring_citations_caps_to_the_slots_own_allowed_count() -> None:
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset(
            {"public_symbol:a", "public_symbol:b", "public_symbol:c", "package:name"}
        ),
        slots=("capability:1",),
        slot_facts={"capability:1": frozenset({"public_symbol:a", "public_symbol:b"})},
    )
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    fact_ids = schema["properties"]["units"]["prefixItems"][0]["properties"]["fact_ids"]
    # citable() also admits every neutral (identity:/package:) accepted id, so 3 here
    # (public_symbol:a, public_symbol:b, package:name), never an unbounded array.
    assert fact_ids["maxItems"] == 3


def test_bound_authoring_citations_caps_to_one_when_nothing_is_citable() -> None:
    task = SectionTask(
        section_id="scope_limitations", packet={}, accepted_ids=frozenset(), slots=("scope",)
    )
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    fact_ids = schema["properties"]["units"]["prefixItems"][0]["properties"]["fact_ids"]
    assert fact_ids["maxItems"] == 1


def test_bound_authoring_citations_caps_the_omitted_list_too() -> None:
    task = SectionTask(
        section_id="scope_limitations",
        packet={},
        accepted_ids=frozenset({"public_symbol:a", "public_symbol:b"}),
        slots=("scope",),
        must_carry=frozenset({"inherited_unit:005.paragraph"}),
    )
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    assert schema["properties"]["omitted"]["maxItems"] == omittable_count([task])
    assert omittable_count([task]) == 3


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("src/x"),))


def test_largest_slot_citation_count_is_the_biggest_slots_own_set() -> None:
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset({"public_symbol:a", "public_symbol:b", "package:name"}),
        slots=("capability:1", "capability:2"),
        slot_facts={
            "capability:1": frozenset({"public_symbol:a"}),
            "capability:2": frozenset({"public_symbol:a", "public_symbol:b"}),
        },
    )
    # capability:1 cites 2 (its own fact + the neutral package:name); capability:2 cites 3.
    assert largest_slot_citation_count([task]) == 3


def test_largest_slot_citation_count_defaults_to_one_without_any_task() -> None:
    assert largest_slot_citation_count([]) == 1
