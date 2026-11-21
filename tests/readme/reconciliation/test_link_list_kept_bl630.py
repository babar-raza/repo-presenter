"""BL-630: a list of verified resource links is never deferred (Slides .NET ``083.list``, the three sibling-edition
repositories, hosted run 44924853748).

The model deferred the list; the repair answered 'enterprise_relationship' (offered as holdable) and S4's own fold for
that section returned the unit to DEFER_UNRESOLVED, so both asks were refused as 'still DEFER_UNRESOLVED, which is the
defect' and BC-17 named the h2 and the three links lost on every settle round. Nothing about such a list is
unresolved (every link is a verified target), so ``normalize`` keeps it in Documentation and Resources, which prints
every link as its own line. The list is the pinned README's own text; the negative controls are the shapes that must
still be deferred.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation import dispositions as d
from repo_presenter.readme.reconciliation.destinations import holdable_sections
from repo_presenter.readme.reconciliation.patch import PatchScope, patch_checks
from tests.readme.repair.test_accounting import _facts, _unit

LIST = (
    "- [Aspose.Slides FOSS for Java](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java)\n"
    "- [Aspose.Slides FOSS for C++](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp)\n"
    "- [Aspose.Slides FOSS for Python](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python)"
)
UNIT = "inherited_unit:083.list"
TARGETS = ["link_target:012", "link_target:013", "link_target:014"]


def _link(n: int, url: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(f"link_target:{n:03d}", "link_target", url, (Evidence(url, "HTTP 200"),), polarity=polarity)  # type: ignore[arg-type]


def _world(*, unit: str = LIST, third: str = "SUPPORTED") -> FactsDocument:
    base = _facts()
    return FactsDocument(
        base.repository, base.source_revision,
        (
            *base.facts,
            _link(12, "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java"),
            _link(13, "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp"),
            _link(14, "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python", third),
            _unit("083.list", unit),
        ),
    )


def _entry(disposition: str, destination: str | None, facts: list[str] | None = None) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": UNIT, "disposition": disposition, "destination_section": destination,
                "fact_ids": TARGETS if facts is None else facts, "rationale": "Lists related FOSS editions.",
            }
        ]
    }


def _folded(disposition: str, destination: str | None, facts: FactsDocument | None = None) -> dict[str, Any]:
    output = _entry(disposition, destination)
    d.normalize(output, facts or _world())
    return output["dispositions"][0]


@pytest.mark.parametrize(
    ("disposition", "destination"),
    [
        ("DEFER_UNRESOLVED", None),
        ("VERIFIED_PRESERVE", "enterprise_relationship"),  # the repair's answer in the hosted run
        ("PRESERVE_ATTRIBUTED", "enterprise_relationship"),
        ("VERIFIED_PRESERVE", "additional_examples"),  # a section this repository does not have
    ],
)
def test_the_exact_list_is_kept_in_documentation_resources(disposition: str, destination: str | None) -> None:
    folded = _folded(disposition, destination)
    assert (folded["disposition"], folded["destination_section"]) == ("VERIFIED_MOVE", "documentation_resources")
    assert set(TARGETS) <= set(folded["fact_ids"])
    assert "documentation_resources" in folded["rationale"]


def test_a_list_already_in_a_section_that_can_hold_it_is_not_touched_by_this_fold() -> None:
    folded = _folded("VERIFIED_PRESERVE", "documentation_resources")
    assert (folded["disposition"], folded["destination_section"]) == ("VERIFIED_PRESERVE", "documentation_resources")
    assert "list of resource links whose every link" not in folded["rationale"]


def test_what_is_not_a_verified_link_list_is_still_deferred() -> None:
    # an item with no link, a link no fact verifies, and a link whose fact is not SUPPORTED
    for world in (
        _world(unit=LIST + "\n- A plain note with no link"),
        _world(unit=LIST + "\n- [Elsewhere](https://example.com/not-a-fact)"),
        _world(third="UNRESOLVED"),
    ):
        folded = _folded("DEFER_UNRESOLVED", None, world)
        assert (folded["disposition"], folded["destination_section"]) == ("DEFER_UNRESOLVED", None)
    # a paragraph is never a link list, whatever it links
    paragraph = _world(unit="See [Java](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java).")
    entry = {"dispositions": [{**_entry("DEFER_UNRESOLVED", None)["dispositions"][0], "unit_id": UNIT}]}
    d.normalize(entry, paragraph)
    assert entry["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"


def test_a_repository_whose_documentation_resources_is_absent_keeps_the_old_fold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(d, "holdable_sections", lambda facts: tuple(s for s in holdable_sections(facts) if s != "documentation_resources"))
    folded = _folded("DEFER_UNRESOLVED", None)
    assert (folded["disposition"], folded["destination_section"]) == ("DEFER_UNRESOLVED", None)


def test_the_repair_reply_the_hosted_run_rejected_twice_now_passes_its_own_contract() -> None:
    """``patch_checks``: a deferred unit the defect names must stop being deferred; the reply's own
    'enterprise_relationship' used to be folded back to DEFER_UNRESOLVED by the checks that run first."""
    facts = _world()
    holdable = holdable_sections(facts)
    scope = PatchScope(
        batch_id="reconciliation#1", unit_ids=(UNIT,), shown={}, contract={},
        deferred=frozenset({UNIT}), holdable=holdable, parity_lost=frozenset({UNIT}),
        supported=frozenset(TARGETS),
    )
    reply = _entry("VERIFIED_PRESERVE", "enterprise_relationship")
    errors = patch_checks(scope, lambda revised: d.reconcile_checks(revised, facts))(copy.deepcopy(reply))
    assert errors == []
    # the unfixed contract: the same reply for a list that is not a verified link list is still refused
    plain = _world(unit=LIST + "\n- A plain note with no link")
    again = patch_checks(scope, lambda revised: d.reconcile_checks(revised, plain))(copy.deepcopy(reply))
    assert any("still DEFER_UNRESOLVED" in e for e in again), again
