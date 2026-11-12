"""The planner is shown, and may cite, every fact kind EXCEPT the evidence-only source-detail kinds
(Words .NET's planning request was ~0.8M tokens with them - gateway HTTP 400, 2026-11-10)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from repo_presenter.core.facts import EVIDENCE_ONLY_KINDS, FACT_KINDS, Evidence, Fact, FactsDocument
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.planning import citable_fact_ids, packet_fact_kinds

PROMPTS = Path(__file__).resolve().parents[3] / "prompts"


def _manifest():
    return load_manifests(PROMPTS)["presentation_planning"].manifest


def _fact(fact_id: str, kind: str) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value="v",  # type: ignore[arg-type]
        evidence=(Evidence("src/x", None),), polarity="SUPPORTED",
    )


def test_the_real_planning_manifest_names_no_kinds_so_the_fallback_applies() -> None:
    assert not _manifest().packet.fact_kinds
    kinds = packet_fact_kinds(_manifest())
    assert set(kinds) == set(FACT_KINDS) - EVIDENCE_ONLY_KINDS
    assert "public_symbol" in kinds and "inherited_unit" in kinds and "enum_member" in kinds


def test_an_explicit_manifest_list_is_used_exactly_as_written() -> None:
    manifest = SimpleNamespace(packet=SimpleNamespace(fact_kinds=("implementation", "example")))
    assert packet_fact_kinds(manifest) == ("implementation", "example")  # type: ignore[arg-type]


def test_evidence_only_facts_are_neither_in_the_packet_nor_citable() -> None:
    facts = FactsDocument(
        "o/r", "0" * 40,
        (
            _fact("implementation:a", "implementation"),
            _fact("project_file:b", "project_file"),
            _fact("internal_symbol:c", "internal_symbol"),
            _fact("enum_member:d", "enum_member"),
        ),
    )
    citable = citable_fact_ids(facts, {}, {"dispositions": []}, _manifest())
    assert "enum_member:d" in citable
    assert not {"implementation:a", "project_file:b", "internal_symbol:c"} & set(citable)
