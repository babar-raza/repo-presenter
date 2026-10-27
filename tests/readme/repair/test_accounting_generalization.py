"""The generalization behind the first hosted qwen3-next cohort (Java, Go, TypeScript): the old
fix for the measured .NET/Python shapes (b0c72f9, 4604b62) did not generalize, because it
hard-coded the literal disposition string ``SUPERSEDE_REDUNDANT`` and a full-text-or-nothing
notion of "printed", instead of the two underlying shapes placement/S4 can actually produce on
any ecosystem's own content:

1. A kept paragraph or list the renderer prints only in part (``composition/coverage.py``'s own
   ``uncovered``, shared by every ecosystem): the part a destination section already states is
   dropped, the rest is printed verbatim. The old "printed" test
   (``independent_reviewer._kept_text_printed``) only recognized a full exact match (or, for a
   list, every item stated in its own destination section) -- never a trimmed remainder -- so it
   called a unit "not printed" whenever any sentence of it, not just the whole block, was covered
   elsewhere. Fixed by recognizing the same sentence-overlap test placement rests its own drop
   on (``coverage.states_all``), guarded by requiring every link or command the unit carries to
   still be in the document (``coverage.hard_tokens``) so a dropped link is never masked by a
   paraphrase.
2. An ``OMIT_UNSUPPORTED`` unit (most often a heading) whose own rationale already says it is
   redundant with a real section, but cites no fact for it: S4 used the word "omit" for the very
   same "this is covered elsewhere" shape ``_uncited_heading`` already repairs for the word
   "supersede". Fixed by ``_uncited_redundant_omission``, which proves the covering section from
   the rendered document (``_section_covering``), never from the rationale's own prose, and backs
   a heading with what it introduced.

Each scenario below is built fresh per ecosystem (java, go, typescript, net, python) from each
platform's own registered spec, not copied from one working fixture -- the point of a
generalization fix is that it must not care which ecosystem it runs on.
"""

from __future__ import annotations

from typing import Any

import pytest

import repo_presenter.extractors.platforms.go
import repo_presenter.extractors.platforms.java
import repo_presenter.extractors.platforms.typescript  # noqa: F401  registers the "typescript" spec
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.review.independent_reviewer import (
    review_candidate,
    unprinted_kept_units,
)
from repo_presenter.readme.validation.failures import Candidate

ECOSYSTEMS = ["java", "go", "typescript", "net", "python"]
REVISION = "c" * 40


_PLATFORM_NAMES = {
    "java": "Java",
    "go": "Go",
    "typescript": "TypeScript",
    "net": "NET",
    "python": "Python",
}


def _entry(ecosystem: str) -> RegistryEntry:
    platform = _PLATFORM_NAMES[ecosystem]
    return RegistryEntry.model_validate(
        {
            "repository": f"demo-foss/Aspose.Demo-FOSS-for-{platform}",
            "family": "demo",
            "platform": ecosystem,
            "ecosystem": ecosystem,
            "mode": "dry_run",
            "policy_profile": "p",
            "active": True,
            "provider_identity": {
                "provider": "github",
                "repository_id": 1,
                "node_id": "R_1",
            },
        }
    )


def _fact(fact_id: str, kind: str, value: str, *details: str) -> Fact:
    evidence = tuple(Evidence("README.md", detail) for detail in details) or (
        Evidence("README.md"),
    )
    return Fact(fact_id, kind, value, evidence, polarity="SUPPORTED")


def _unit(unit_id: str, value: str) -> Fact:
    return _fact(f"inherited_unit:{unit_id}", "inherited_unit", value)


def _authored(section: str, slot: str, text: str) -> dict[str, Any]:
    return {
        "section": section,
        "slot": slot,
        "text": text,
        "fact_ids": ["identity:repository"],
    }


def _disposition_entry(
    unit: str,
    disposition: str,
    destination: str | None,
    fact_ids: list[str],
    rationale: str = "r",
) -> dict[str, Any]:
    return {
        "unit_id": f"inherited_unit:{unit}",
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": fact_ids,
        "rationale": rationale,
    }


# --- scenario: a kept paragraph the renderer only partly drops (disposition_coverage shape) ----


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_a_trimmed_remainder_paragraph_is_recognized_as_printed(ecosystem: str) -> None:
    """The Java hosted shape (inherited_unit:012/024/080): a kept paragraph whose first sentence
    is restated, in different words, by the section's own authored content, and whose second
    sentence is unique. The renderer prints only the uncovered remainder; the old full-text check
    would call the whole unit "not printed" even though nothing was silently dropped."""
    entry = _entry(ecosystem)
    facts = FactsDocument(
        entry.repository,
        REVISION,
        (
            _fact("identity:repository", "identity", entry.repository),
            _fact("format:archive_formats", "format", "legacy archive formats"),
            _unit(
                "030.paragraph",
                "The package provides read-only access to legacy archive formats. It also "
                "needs a native zlib library the operating system must already supply.",
            ),
        ),
    )
    plan = {
        "sections": [
            {"section_id": section, "include": True, "reason": "r"}
            for section in [
                "identity",
                "badges",
                "opening",
                "navigation",
                "scope_limitations",
                "license",
            ]
        ],
        "core_capabilities": [],
        "material_limitations": [
            {"fact_ids": ["format:archive_formats"], "unit_ids": []}
        ],
        "api_hubs": [],
        "links": [],
        "deviations": [],
    }
    units = {
        "units": [
            _authored(
                "opening", "opening", f"Demo for {ecosystem} reads legacy archives."
            ),
            _authored(
                "scope_limitations",
                "scope",
                "Read-only access to legacy archive formats is all this package provides.",
            ),
        ],
        "omitted": [],
    }
    dispositions = {
        "dispositions": [
            _disposition_entry(
                "030.paragraph",
                "VERIFIED_PRESERVE",
                "scope_limitations",
                ["format:archive_formats"],
            )
        ]
    }
    readme = render_readme(entry, facts, plan, units, dispositions)
    unit_value = next(f.value for f in facts.by_kind("inherited_unit"))

    # The old, narrow check: proves the fix is doing real work, not a no-op.
    assert " ".join(unit_value.split()) not in " ".join(readme.split())
    # The new check: nothing was silently dropped.
    assert unprinted_kept_units(readme, facts=facts, dispositions=dispositions) == []
    # And the uncovered remainder really is there, verbatim.
    assert "native zlib library" in readme

    candidate = Candidate(
        entry, facts, plan, units, dispositions, readme, None, REVISION, None, (), []
    )
    settled, accounted = account_unprinted_units(candidate)
    assert accounted == []  # nothing to account for: it already prints
    assert settled == dispositions


def test_a_dropped_link_is_still_flagged_even_when_the_rest_paraphrases() -> None:
    """Negative control: the sentence-overlap fallback must never stand in for the literal link
    or command a unit carries. A paraphrase that drops the link must stay flagged as not printed,
    exactly as it would if the whole unit vanished."""
    facts = FactsDocument(
        "demo/demo",
        REVISION,
        (
            _unit(
                "009.paragraph",
                "For the complete usage guide, see [docs/usage.md](docs/usage.md).",
            ),
        ),
    )
    dispositions = {
        "dispositions": [
            _disposition_entry(
                "009.paragraph", "VERIFIED_PRESERVE", "documentation_resources", []
            )
        ]
    }
    # The README restates the same words at length, but never the link target itself.
    readme = (
        "## Documentation & Resources\n\nFor the complete API reference and usage guide, read "
        "the project's own long-form guide carefully before filing an issue.\n"
    )
    found = unprinted_kept_units(readme, facts=facts, dispositions=dispositions)
    assert [unit for unit, _ in found] == ["inherited_unit:009.paragraph"]


# --- scenario: an OMIT_UNSUPPORTED heading S4 should have called SUPERSEDE_REDUNDANT -----------


def _redundant_omission_candidate(
    ecosystem: str,
) -> tuple[Candidate, str]:
    """A heading and its one list child, both ``OMIT_UNSUPPORTED`` with an empty ``fact_ids`` and
    a "redundant with X" rationale (the Go hosted shape: inherited_unit:072/073) -- the list's
    content is, in fact, restated by ``scope_limitations``' own authored content. A sibling
    heading/paragraph pair (``020``/``021``) is genuinely unsupported: nothing restates it, so it
    must be left alone. Returns the candidate and the original (live) README the units came from."""
    entry = _entry(ecosystem)
    facts = FactsDocument(
        entry.repository,
        REVISION,
        (
            _fact("identity:repository", "identity", entry.repository),
            _fact("format:row_limit", "format", "a 1,048,576 row ceiling"),
            _unit("010.heading", "## Constraints"),
            _unit(
                "011.list",
                "- Rows beyond 1,048,576 are rejected.\n- Only UTF-8 input is accepted.",
            ),
            _unit("020.heading", "## Telemetry"),
            _unit(
                "021.paragraph",
                "The CLI phones home anonymised usage statistics daily.",
            ),
        ),
    )
    plan = {
        "sections": [
            {"section_id": section, "include": True, "reason": "r"}
            for section in [
                "identity",
                "badges",
                "opening",
                "navigation",
                "scope_limitations",
                "license",
            ]
        ],
        "core_capabilities": [],
        "material_limitations": [{"fact_ids": ["format:row_limit"], "unit_ids": []}],
        "api_hubs": [],
        "links": [],
        "deviations": [],
    }
    units = {
        "units": [
            _authored(
                "opening", "opening", f"Demo for {ecosystem} edits spreadsheets."
            ),
            _authored(
                "scope_limitations",
                "scope",
                "Rows beyond 1,048,576 are rejected, and only UTF-8 input is accepted.",
            ),
        ],
        "omitted": [],
    }
    dispositions = {
        "dispositions": [
            _disposition_entry(
                "010.heading",
                "OMIT_UNSUPPORTED",
                None,
                [],
                "The Constraints heading is not supported by any fact and is redundant with "
                "the scope_limitations section.",
            ),
            _disposition_entry(
                "011.list",
                "OMIT_UNSUPPORTED",
                None,
                [],
                "The constraints list is not supported by any fact and is redundant with the "
                "scope_limitations section.",
            ),
            _disposition_entry(
                "020.heading",
                "OMIT_UNSUPPORTED",
                None,
                [],
                "The Telemetry heading is not supported by any fact and is redundant with "
                "another section.",
            ),
            _disposition_entry(
                "021.paragraph",
                "OMIT_UNSUPPORTED",
                None,
                [],
                "The telemetry paragraph is not supported by any fact and is redundant with "
                "another section.",
            ),
        ]
    }
    readme = render_readme(entry, facts, plan, units, dispositions)
    original = (
        "# Old\n\n## Constraints\n\n- Rows beyond 1,048,576 are rejected.\n"
        "- Only UTF-8 input is accepted.\n\n## Telemetry\n\nThe CLI phones home anonymised "
        "usage statistics daily.\n"
    )
    candidate = Candidate(
        entry, facts, plan, units, dispositions, readme, None, REVISION, None, (), []
    )
    return candidate, original


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_an_omit_unsupported_heading_redundant_with_a_real_section_is_backfilled(
    ecosystem: str,
) -> None:
    candidate, original = _redundant_omission_candidate(ecosystem)
    known = {fact.id for fact in candidate.facts.facts}
    before = review_candidate(
        readme_text=candidate.readme,
        units=candidate.units.get("units", []),
        facts=candidate.facts,
        dispositions=candidate.dispositions,
        original_readme=original,
    )
    assert any(
        "Constraints" in f.message and f.rule == "live_readme_loss"
        for f in before.findings
    )

    settled, accounted = account_unprinted_units(candidate)
    by_unit = {a.unit_id: a for a in accounted}
    heading = by_unit["inherited_unit:010.heading"]
    content = by_unit["inherited_unit:011.list"]
    assert heading.destination == content.destination == "scope_limitations"
    assert heading.fact_ids and set(heading.fact_ids) <= known
    assert content.fact_ids and set(content.fact_ids) <= known

    # Rendering must not change: accounting only rewrites the bookkeeping.
    assert (
        render_readme(
            candidate.entry, candidate.facts, candidate.plan, candidate.units, settled
        )
        == candidate.readme
    )

    after = review_candidate(
        readme_text=candidate.readme,
        units=candidate.units.get("units", []),
        facts=candidate.facts,
        dispositions=settled,
        original_readme=original,
    )
    assert not any("Constraints" in f.message for f in after.findings), [
        f.message for f in after.findings
    ]
    # The sibling that nothing really restates must still be caught, before and after.
    assert any("Telemetry" in f.message for f in after.findings)


@pytest.mark.parametrize("ecosystem", ECOSYSTEMS)
def test_an_omit_unsupported_heading_truly_unsupported_is_left_uncited(
    ecosystem: str,
) -> None:
    """Negative control: a unit whose rationale claims redundancy but whose content the finished
    README never actually restates must not be backfilled -- the real loss stays blocking."""
    candidate, _original = _redundant_omission_candidate(ecosystem)
    _settled, accounted = account_unprinted_units(candidate)
    touched = {a.unit_id for a in accounted}
    assert "inherited_unit:020.heading" not in touched
    assert "inherited_unit:021.paragraph" not in touched
