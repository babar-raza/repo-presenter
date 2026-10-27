"""BUILD_INDEPENDENT_REVIEWER's still-open item: where a REJECT hands off. The most important
test here is ``test_a_finding_over_inherited_content_routes_to_s4_not_s6`` -- it is the real
aspose-font-foss/Aspose.Font-FOSS-for-Python case (project/state.yaml's
root_cause_traced_2026_10_24), reconstructed as a fixture: a finding whose quote matches content
the candidate inherited and placed verbatim must never be routed to S6, because authoring never
wrote that text and cannot revise it.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import Finding, Refutation, ReviewVerdict

REVISION = "a" * 40
REPOSITORY = "org/repo"


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument(REPOSITORY, REVISION, facts)


def _plan(*section_ids: str) -> dict[str, object]:
    return {"sections": [{"include": True, "section_id": s} for s in section_ids]}


def _disposition(unit_id: str, destination: str, disposition: str = "VERIFIED_PRESERVE") -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "destination_section": destination,
        "disposition": disposition,
        "fact_ids": [],
        "rationale": "test fixture",
    }


def test_a_finding_over_inherited_content_routes_to_s4_not_s6() -> None:
    """The real case: the broken install line is inherited verbatim, not authored."""
    quote = 'pip install "aspose-font[mcp]"'
    facts = _facts(
        Fact(
            "inherited_unit:050.code_block",
            "inherited_unit",
            f"```bash\n{quote}\npython -m aspose_font.mcp\n```",
            (Evidence("README.md"),),
        )
    )
    plan = _plan("additional_examples")
    dispositions = {"dispositions": [_disposition("inherited_unit:050.code_block", "additional_examples")]}
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="claim_contradiction",
                kind="deterministic",
                message="wrong package name",
                refuted_by=Refutation(rule="claim_contradiction", evidence="wrong package name"),
                quote=quote,
            ),
        ),
    )
    [defect] = build_defects(
        verdict, units=[], plan=plan, dispositions=dispositions, facts=facts, ecosystem="python"
    )
    assert defect.stage == "S4"
    assert defect.repairable is True
    assert defect.record.get("misrouted") is True
    assert defect.record.get("message") == "wrong package name"


def test_a_finding_over_an_authored_unit_in_an_llm_owned_section_routes_to_s6() -> None:
    quote = "authored text that duplicates the preserved opening"
    units = [{"section": "opening", "slot": "opening", "text": quote}]
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="duplicate_opening_paragraph",
                kind="deterministic",
                message="restates the preserved paragraph",
                refuted_by=Refutation(rule="duplicate_opening_paragraph", evidence="dup"),
                quote=quote,
            ),
        ),
    )
    [defect] = build_defects(
        verdict,
        units=units,
        plan=_plan("opening"),
        dispositions={"dispositions": []},
        facts=_facts(),
        ecosystem="python",
    )
    assert defect.stage == "S6"
    assert defect.repairable is True
    assert defect.section_id == "opening"


def test_a_finding_in_a_deterministic_section_is_advisory_not_repairable() -> None:
    """A section no unit was ever authored for (badges, identity, ...) is not llm-owned -- S6
    cannot be the answer even if nothing was inherited either."""
    quote = "some deterministic text"
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="claim_contradiction",
                kind="deterministic",
                message="m",
                refuted_by=Refutation(rule="claim_contradiction", evidence="e"),
                quote=quote,
            ),
        ),
    )
    [defect] = build_defects(
        verdict,
        units=[{"section": "opening", "slot": "opening", "text": "unrelated authored text"}],
        plan=_plan("opening"),
        dispositions={"dispositions": []},
        facts=_facts(),
        ecosystem="python",
    )
    assert defect.repairable is False
    assert defect.reason is not None


def test_judgment_only_findings_never_become_defects() -> None:
    """Annotate-only: a judgment finding (no refuted_by -- enforced structurally, see
    Finding.__post_init__) never reaches review_defects at all."""
    verdict = ReviewVerdict(
        verdict="ACCEPT",
        findings=(Finding(rule="style_note", kind="judgment", message="a bit verbose"),),
    )
    assert (
        build_defects(
            verdict,
            units=[],
            plan=_plan(),
            dispositions={"dispositions": []},
            facts=_facts(),
            ecosystem="python",
        )
        == []
    )


def test_an_accepted_verdict_with_no_findings_produces_no_defects() -> None:
    verdict = ReviewVerdict(verdict="ACCEPT", findings=())
    assert (
        build_defects(
            verdict,
            units=[],
            plan=_plan(),
            dispositions={"dispositions": []},
            facts=_facts(),
            ecosystem="python",
        )
        == []
    )


def test_every_defect_fingerprint_embeds_the_ruleset_version_for_future_invalidation() -> None:
    """A future change to how a rule matches content must produce a different fingerprint, so a
    stale repair attempt recorded under the old meaning never short-circuits a fresh one."""
    quote = "x"
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="claim_contradiction",
                kind="deterministic",
                message="m",
                refuted_by=Refutation(rule="claim_contradiction", evidence="e"),
                quote=quote,
            ),
        ),
    )
    units = [{"section": "opening", "slot": "opening", "text": quote}]
    [a] = build_defects(
        verdict, units=units, plan=_plan("opening"), dispositions={"dispositions": []},
        facts=_facts(), ecosystem="python", repairer="r1",
    )
    [b] = build_defects(
        verdict, units=units, plan=_plan("opening"), dispositions={"dispositions": []},
        facts=_facts(), ecosystem="python", repairer="r2",
    )
    assert a.fingerprint != b.fingerprint


def test_a_kept_but_unprinted_unit_is_an_s4_defect_even_when_the_render_placed_nothing() -> None:
    """``disposition_coverage`` measures a disposition's claim, so its cause is S4 whatever section
    the quote sits in; before this route it was filed under S6 and then refused as deterministic."""
    unit = "inherited_unit:059.list"
    text = "- **[Getting started guide](https://docs.example.com/)** - installation."
    facts = _facts(Fact(unit, "inherited_unit", text, (Evidence("README.md"),)))
    plan = _plan("opening")  # the destination is not rendered, so the text is not a placed text
    dispositions = {"dispositions": [_disposition(unit, "documentation_resources")]}
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="disposition_coverage",
                kind="deterministic",
                message=f"{unit} is kept (VERIFIED_PRESERVE) but its text is not printed",
                refuted_by=Refutation(rule="disposition_coverage", evidence="not printed"),
                quote=text,
            ),
        ),
    )
    [defect] = build_defects(
        verdict, units=[], plan=plan, dispositions=dispositions, facts=facts, ecosystem="python"
    )
    assert (defect.stage, defect.repairable) == ("S4", True)


def test_the_same_quote_under_another_rule_stays_where_it_was_routed() -> None:
    """Negative control: only the disposition rule moves to S4. The identical quote and section
    filed by a claim rule is still an authored-text matter, unrepairable in a deterministic one."""
    unit = "inherited_unit:059.list"
    text = "- **[Getting started guide](https://docs.example.com/)** - installation."
    facts = _facts(Fact(unit, "inherited_unit", text, (Evidence("README.md"),)))
    verdict = ReviewVerdict(
        verdict="REJECT",
        findings=(
            Finding(
                rule="claim_contradiction",
                kind="deterministic",
                message="m",
                refuted_by=Refutation(rule="claim_contradiction", evidence="e"),
                quote=text,
            ),
        ),
    )
    [defect] = build_defects(
        verdict,
        units=[],
        plan=_plan("opening"),
        dispositions={"dispositions": [_disposition(unit, "documentation_resources")]},
        facts=facts,
        ecosystem="python",
    )
    assert defect.stage is None and defect.repairable is False
