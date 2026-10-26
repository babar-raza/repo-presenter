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
    assert all(finding.refuted_by is not None for finding in findings)


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
