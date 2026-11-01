"""The two preservation holdouts ported from the old judge.py (J4 kept text and dispositions, J6
live-README loss) as deterministic rules of ``independent_reviewer``.

Each test is a negative control or a positive control for one rule: a candidate that loses or
mis-accounts for live content must REJECT, and a candidate that keeps it, or accounts for it with
evidence, must not. The fixtures are small and synthetic on purpose; the measurement on real
candidates is recorded in migration/reuse-manifest.yaml, not asserted here.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.bundle.recheck import original_readme as recover_original
from repo_presenter.readme.bundle.recheck import render_patch
from repo_presenter.readme.review.independent_reviewer import (
    disposition_coverage_rule,
    live_readme_loss_rule,
    review_candidate,
)

REVISION = "b" * 40
DOCS_LINE = "See the [docs](https://widget.example.com/docs/) for details.\n"
USAGE_SECTION = "## Usage\n\n" + DOCS_LINE

LIVE = (
    "# Widget FOSS\n\n"
    "Widget FOSS is a pure-Python library.\n\n"
    "## Installation\n\n"
    "```bash\npip install widget-foss\n```\n\n" + USAGE_SECTION
)


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument("org/widget", REVISION, facts)


def _unit(unit_id: str, text: str) -> Fact:
    return Fact(unit_id, "inherited_unit", text, (Evidence("README.md", "live"),))


UNITS = (
    _unit("inherited_unit:001.heading", "# Widget FOSS"),
    _unit("inherited_unit:002.paragraph", "Widget FOSS is a pure-Python library."),
    _unit("inherited_unit:003.heading", "## Installation"),
    _unit("inherited_unit:004.code_block", "```bash\npip install widget-foss\n```"),
    _unit("inherited_unit:005.heading", "## Usage"),
    _unit("inherited_unit:006.paragraph", DOCS_LINE.strip()),
)


def _command(value: str) -> Fact:
    return Fact(
        "install_command:pip",
        "install_command",
        value,
        (Evidence("README.md", "install"),),
    )


def _row(unit_id: str, disposition: str = "VERIFIED_PRESERVE", **extra: object) -> dict:
    row: dict = {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": "x",
        "fact_ids": [],
        "rationale": "fixture",
    }
    row.update(extra)
    return row


def _all_kept() -> dict:
    return {"dispositions": [_row(unit.id) for unit in UNITS]}


def _without(text: str, removed: str) -> str:
    assert removed in text
    return text.replace(removed, "")


def _messages(findings: list) -> list[str]:
    return [finding.message for finding in findings]


# ---------------------------------------------------------------------------
# disposition_coverage (judge.py J4)
# ---------------------------------------------------------------------------


def test_disposition_coverage_is_silent_when_every_unit_has_one_and_kept_text_is_printed() -> (
    None
):
    assert (
        disposition_coverage_rule(LIVE, facts=_facts(*UNITS), dispositions=_all_kept())
        == []
    )


def test_disposition_coverage_rejects_a_unit_with_no_disposition() -> None:
    dispositions = {
        "dispositions": [
            row
            for row in _all_kept()["dispositions"]
            if row["unit_id"] != "inherited_unit:002.paragraph"
        ]
    }
    findings = disposition_coverage_rule(
        LIVE, facts=_facts(*UNITS), dispositions=dispositions
    )
    assert _messages(findings) == [
        "inherited_unit:002.paragraph has 0 dispositions, not one"
    ]
    assert all(finding.source == "deterministic" and finding.blocking for finding in findings)


def test_disposition_coverage_rejects_a_unit_with_two_dispositions() -> None:
    dispositions = _all_kept()
    dispositions["dispositions"].append(
        _row("inherited_unit:002.paragraph", "OMIT_UNSUPPORTED")
    )
    findings = disposition_coverage_rule(
        LIVE, facts=_facts(*UNITS), dispositions=dispositions
    )
    assert _messages(findings) == [
        "inherited_unit:002.paragraph has 2 dispositions, not one"
    ]


def test_disposition_coverage_rejects_a_disposition_naming_an_unknown_unit() -> None:
    dispositions = _all_kept()
    dispositions["dispositions"].append(_row("inherited_unit:999.paragraph"))
    findings = disposition_coverage_rule(
        LIVE, facts=_facts(*UNITS), dispositions=dispositions
    )
    assert _messages(findings) == [
        "inherited_unit:999.paragraph is named by a disposition but is not an inherited unit"
    ]


def test_disposition_coverage_rejects_a_kept_unit_whose_text_is_not_printed() -> None:
    candidate = _without(LIVE, "Widget FOSS is a pure-Python library.\n\n")
    findings = disposition_coverage_rule(
        candidate, facts=_facts(*UNITS), dispositions=_all_kept()
    )
    assert len(findings) == 1
    assert "inherited_unit:002.paragraph is kept" in findings[0].message


def test_disposition_coverage_accepts_a_kept_heading_that_was_re_leveled_and_re_cased() -> (
    None
):
    candidate = LIVE.replace("## Installation", "# INSTALLATION")
    assert (
        disposition_coverage_rule(
            candidate, facts=_facts(*UNITS), dispositions=_all_kept()
        )
        == []
    )


def test_a_kept_heading_is_not_printed_because_another_heading_contains_its_words() -> (
    None
):
    """Hosted run 7: '### Convert a Lambert Material to PBR' was counted printed because the README
    says '### Convert a Lambert Material to PBR Material', while the loss rule (whole headings)
    reported it lost. A heading is printed only as the same heading."""
    live = "# Widget FOSS\n\n### Convert a Lambert Material to PBR\n"
    candidate = "# Widget FOSS\n\n### Convert a Lambert Material to PBR Material\n"
    units = (
        _unit("inherited_unit:001.heading", "# Widget FOSS"),
        _unit("inherited_unit:002.heading", "### Convert a Lambert Material to PBR"),
    )
    dispositions = {"dispositions": [_row(unit.id) for unit in units]}
    findings = disposition_coverage_rule(
        candidate, facts=_facts(*units), dispositions=dispositions
    )
    assert len(findings) == 1 and "002.heading" in findings[0].message
    assert (
        disposition_coverage_rule(live, facts=_facts(*units), dispositions=dispositions)
        == []
    )


RESOURCES = (
    "- **[Docs](https://widget.example.com/docs)** - installation and guides.\n"
    "- **[Notes](notes.md)** - implementation status."
)


def _list_case(readme: str) -> list:
    units = (_unit("inherited_unit:001.list", RESOURCES),)
    dispositions = {
        "dispositions": [
            _row(
                "inherited_unit:001.list",
                "VERIFIED_MOVE",
                destination_section="documentation_resources",
            )
        ]
    }
    return disposition_coverage_rule(
        readme, facts=_facts(*units), dispositions=dispositions
    )


def test_a_list_printed_in_part_with_every_other_item_stated_is_retained() -> None:
    """Hosted run 7's Documentation and Resources list: the renderer printed the one item the
    section did not already state, and stated the others with their links."""
    readme = (
        "## Documentation & Resources\n\n"
        "- **[Docs](https://widget.example.com/docs)** - The guides cover installation.\n"
        "- **[Notes](notes.md)** - implementation status.\n"
    )
    assert _list_case(readme) == []


def test_a_list_printed_in_part_is_rejected_when_another_item_is_nowhere() -> None:
    readme = (
        "## Documentation & Resources\n\n"
        "- **[Notes](notes.md)** - implementation status.\n"
    )
    findings = _list_case(readme)
    assert len(findings) == 1 and "001.list is kept" in findings[0].message


def test_a_list_with_no_item_printed_as_written_is_still_flagged_for_the_accounting() -> (
    None
):
    """A wholly restated list is the accounting's to supersede (the render is unchanged by it);
    the reviewer does not excuse it."""
    readme = (
        "## Documentation & Resources\n\n"
        "The guides cover installation, see https://widget.example.com/docs and notes.md.\n"
    )
    findings = _list_case(readme)
    assert len(findings) == 1 and "001.list is kept" in findings[0].message


# ---------------------------------------------------------------------------
# live_readme_loss (judge.py J6)
# ---------------------------------------------------------------------------


def test_live_loss_is_silent_when_the_candidate_keeps_everything() -> None:
    assert (
        live_readme_loss_rule(
            LIVE, LIVE, facts=_facts(*UNITS), dispositions=_all_kept()
        )
        == []
    )


def test_live_loss_rejects_a_dropped_section_with_no_disposition_and_names_it() -> None:
    candidate = _without(LIVE, USAGE_SECTION)
    messages = _messages(
        live_readme_loss_rule(
            LIVE, candidate, facts=_facts(*UNITS), dispositions=_all_kept()
        )
    )
    assert any("heading 'Usage'" in message for message in messages)
    assert any(
        "link https://widget.example.com/docs/" in message for message in messages
    )


def _dispositions_with(omitted: tuple[str, ...], **change: object) -> dict:
    """Every unit kept, except ``omitted``, which get an OMIT_UNSUPPORTED row with ``change``."""
    rows = [_row(unit.id) for unit in UNITS if unit.id not in omitted]
    for unit_id in omitted:
        fields: dict = {"fact_ids": ["link_target:docs"], "rationale": "dead link"}
        fields.update(change)
        rows.append(_row(unit_id, "OMIT_UNSUPPORTED", **fields))
    return {"dispositions": rows}


_DROPPED = ("inherited_unit:005.heading", "inherited_unit:006.paragraph")


def test_live_loss_is_accounted_for_by_an_accounting_disposition_with_evidence() -> (
    None
):
    candidate = _without(LIVE, USAGE_SECTION)
    findings = live_readme_loss_rule(
        LIVE, candidate, facts=_facts(*UNITS), dispositions=_dispositions_with(_DROPPED)
    )
    assert findings == []


def test_live_loss_is_not_accounted_for_without_evidence_or_by_a_kept_disposition() -> (
    None
):
    candidate = _without(LIVE, USAGE_SECTION)
    for change in (
        {"fact_ids": []},
        {"rationale": "  "},
        {"disposition": "VERIFIED_PRESERVE"},
    ):
        rows = [_row(unit.id) for unit in UNITS if unit.id not in _DROPPED]
        for unit_id in _DROPPED:
            fields: dict = {"fact_ids": ["f"], "rationale": "r"}
            fields.update(change)
            disposition = fields.pop("disposition", "OMIT_UNSUPPORTED")
            rows.append(_row(unit_id, disposition, **fields))
        messages = _messages(
            live_readme_loss_rule(
                LIVE,
                candidate,
                facts=_facts(*UNITS),
                dispositions={"dispositions": rows},
            )
        )
        assert any("heading 'Usage'" in message for message in messages), change


# Measured live, three times (aspose-cells-foss/Aspose.Cells-FOSS-for-.NET run 41112824093,
# aspose-words-foss/Aspose.Words-FOSS-for-.NET run 41125275923, aspose-pdf-foss/Aspose.PDF-FOSS-
# for-Cpp run 41149996795): a heading SUPERSEDE_REDUNDANT into a placeable section, uncited, was
# never caught by dispositions.py's own gap/fold machinery (headings are skipped outright) nor by
# this rule's own accounting bar (deliberately not exempt), so it reached this deterministic
# check with no path back to being accounted for. normalize() now assigns a real identity fact
# to this exact disposition+kind shape; this test proves the full chain -- the end-to-end
# behavior this session's own root-cause fixes are measured against -- not just that normalize()
# itself runs clean.
def test_normalize_fixes_an_uncited_redundant_heading_so_live_loss_accounts_for_it() -> None:
    from repo_presenter.readme.reconciliation.dispositions import normalize

    facts = _facts(*UNITS, Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)))
    candidate = _without(LIVE, USAGE_SECTION)
    rows = [_row(unit.id) for unit in UNITS if unit.id not in _DROPPED]
    rows.append(
        _row(
            "inherited_unit:005.heading",
            "SUPERSEDE_REDUNDANT",
            destination_section="development_testing",
            fact_ids=[],
            rationale="Superseded by the Development and Testing section heading.",
        )
    )
    rows.append(
        _row(
            "inherited_unit:006.paragraph",
            "OMIT_UNSUPPORTED",
            fact_ids=["link_target:docs"],
            rationale="dead link",
        )
    )
    output = {"dispositions": rows}
    normalize(output, facts)
    heading_entry = next(
        row for row in output["dispositions"] if row["unit_id"] == "inherited_unit:005.heading"
    )
    assert heading_entry["fact_ids"] == ["identity:ecosystem"]
    findings = live_readme_loss_rule(LIVE, candidate, facts=facts, dispositions=output)
    assert findings == []


# Measured live (aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp, run 41154207665, verifying the fix
# above): the model chose OMIT_UNSUPPORTED for this exact shape instead of SUPERSEDE_REDUNDANT --
# a heading the model considers covered elsewhere, not placed into any section at all. Headings
# are also absent from _UNCITED_OMIT_KINDS, so this slipped past placement_errors the same way.
def test_normalize_fixes_an_uncited_omitted_heading_so_live_loss_accounts_for_it() -> None:
    from repo_presenter.readme.reconciliation.dispositions import normalize

    facts = _facts(*UNITS, Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)))
    candidate = _without(LIVE, USAGE_SECTION)
    rows = [_row(unit.id) for unit in UNITS if unit.id not in _DROPPED]
    rows.append(
        _row(
            "inherited_unit:005.heading",
            "OMIT_UNSUPPORTED",
            destination_section=None,
            fact_ids=[],
            rationale="Omitted because the installation section renders this content from facts.",
        )
    )
    rows.append(
        _row(
            "inherited_unit:006.paragraph",
            "OMIT_UNSUPPORTED",
            fact_ids=["link_target:docs"],
            rationale="dead link",
        )
    )
    output = {"dispositions": rows}
    normalize(output, facts)
    heading_entry = next(
        row for row in output["dispositions"] if row["unit_id"] == "inherited_unit:005.heading"
    )
    assert heading_entry["fact_ids"] == ["identity:ecosystem"]
    findings = live_readme_loss_rule(LIVE, candidate, facts=facts, dispositions=output)
    assert findings == []


def test_live_loss_rejects_a_lost_code_block() -> None:
    candidate = LIVE.replace("pip install widget-foss", "uv add widget-foss")
    messages = _messages(
        live_readme_loss_rule(
            LIVE, candidate, facts=_facts(*UNITS), dispositions=_all_kept()
        )
    )
    assert any(
        "code block 'pip install widget-foss'" in message for message in messages
    )


def test_live_loss_rejects_a_lost_verified_install_command() -> None:
    facts = _facts(*UNITS, _command("pip install widget-foss"))
    candidate = LIVE.replace("pip install widget-foss", "uv add widget-foss")
    messages = _messages(
        live_readme_loss_rule(LIVE, candidate, facts=facts, dispositions=_all_kept())
    )
    assert any("command 'pip install widget-foss'" in message for message in messages)


def test_live_loss_rejects_a_lost_link_target() -> None:
    candidate = LIVE.replace("(https://widget.example.com/docs/)", "(#usage)")
    messages = _messages(
        live_readme_loss_rule(
            LIVE, candidate, facts=_facts(*UNITS), dispositions=_all_kept()
        )
    )
    assert any(
        "link https://widget.example.com/docs/" in message for message in messages
    )


# ---------------------------------------------------------------------------
# end to end: the rules inside review_candidate; the verdict fold is untouched
# ---------------------------------------------------------------------------


def test_review_candidate_accepts_an_unchanged_candidate_with_consistent_dispositions() -> (
    None
):
    verdict = review_candidate(
        readme_text=LIVE,
        units=[],
        facts=_facts(*UNITS),
        dispositions=_all_kept(),
        original_readme=LIVE,
    )
    assert verdict.verdict == "ACCEPT"
    assert verdict.findings == ()


def test_review_candidate_rejects_a_silently_dropped_live_section() -> None:
    """Negative control: a candidate that drops a live section without any disposition must be
    REJECTed by a deterministic refutation, never folded to ACCEPT."""
    candidate = _without(LIVE, USAGE_SECTION)
    verdict = review_candidate(
        readme_text=candidate,
        units=[],
        facts=_facts(*UNITS),
        dispositions=_all_kept(),
        original_readme=LIVE,
    )
    assert verdict.verdict == "REJECT"
    assert "live_readme_loss" in {finding.rule for finding in verdict.findings}
    # the dropped units are still marked kept, so disposition_coverage also refutes the candidate
    assert "disposition_coverage" in {finding.rule for finding in verdict.findings}


# ---------------------------------------------------------------------------
# the live README the review compares against, recovered from the sealed patch
# ---------------------------------------------------------------------------


def test_the_live_readme_is_recovered_from_the_patch_that_produced_the_candidate() -> (
    None
):
    candidate = _without(LIVE, USAGE_SECTION)
    assert recover_original(candidate, render_patch(LIVE, candidate)) == LIVE
