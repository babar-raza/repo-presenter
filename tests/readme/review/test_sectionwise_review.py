"""The sectionwise review end to end (reviewer logic 6), with a scripted client in place of the
provider: one governed ``run_job`` per unit, the replies merged into one verdict, every fail-closed
branch, replay at zero calls and the no-re-roll record per unit."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.readme.review import llm_review
from repo_presenter.readme.review.independent_reviewer import (
    load_review_verdict,
    write_review_verdict,
)
from repo_presenter.readme.review.llm_review import (
    BLOCKED_FILENAME,
    RerollRefused,
    blocked_predicate,
)
from repo_presenter.readme.review.sectionwise import plan_units
from repo_presenter.readme.review.verdict import ReviewUnavailable
from tests.readme.review.test_llm_review import (
    ORIGINAL,
    Harness,
    completion,
    install,
    reply,
)

CAPABILITIES = "\n".join(
    f"- **Capability {n}.** It exports vector output through the SvgExporter class, number {n}."
    for n in range(1, 31)
)
CANDIDATE = f"""# Aspose.Widget FOSS for Python

Aspose.Widget FOSS renders widgets to PNG and SVG.

## Installation

```bash
pip install aspose-widget-foss
```

## Key Capabilities

{CAPABILITIES}

## Quick Start

Render a widget to a file and read it back.

```python
from aspose.widget import Widget
Widget().render("out.png")
```

## Scope and Limitations

- Rendering to `.pdf` is not implemented in this build.

## License

MIT.
"""
ROWS = CANDIDATE.splitlines()
UNIT_BUDGET = 700


def at(text: str) -> int:
    (found,) = [i for i, row in enumerate(ROWS, 1) if text in row]
    return found


def line_finding(
    kind: str, line: int, section: str, **overrides: Any
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "F01",
        "section_id": section,
        "causal_stage": "S6",
        "criterion": "specificity",
        "claim_kind": kind,
        "text": "a reviewer claim",
        "lines": [line],
        "fact_ids": [],
        "repair": "fix it",
    }
    base.update(overrides)
    return base


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Harness:
    monkeypatch.setattr(
        llm_review, "plan_units", partial(plan_units, max_chars=UNIT_BUDGET)
    )
    return Harness(tmp_path, CANDIDATE)


def test_the_candidate_splits_into_several_units() -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    assert len(units) >= 4
    assert units[0].sections[0] == "opening"
    assert units[-1].sections[-1] == "scope_limitations"


def test_one_governed_call_per_unit_and_one_merged_accept(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    client = install(monkeypatch, [completion(reply())] * len(units))
    verdict = harness.review()
    assert verdict.verdict == "ACCEPT" and verdict.model_reviewed
    assert harness.provider_calls() == len(units) == len(client.payloads)
    assert [r["unit"] for r in verdict.unit_reviews] == [u.label for u in units]
    assert all(
        r["status"] == "reviewed" and r["findings"] == 0 for r in verdict.unit_reviews
    )
    assert len({r["request_sha256"] for r in verdict.unit_reviews}) == len(units)
    assert verdict.prompt_version == "17"


def test_every_call_carries_only_its_own_units_text(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    client = install(monkeypatch, [completion(reply())] * len(units))
    harness.review()
    for unit, payload in zip(units, client.payloads, strict=True):
        user = payload["messages"][1]["content"]
        for number in unit.lines:
            assert f"{number:04d}| {ROWS[number - 1]}" in user
        for other in units:
            if other is not unit:
                assert f"{other.lines[0]:04d}|" not in user
        shown = user.split("BEGIN UNTRUSTED candidate_section")[1].split(
            "END UNTRUSTED candidate_section"
        )[0]
        for renderer_line in (
            "pip install aspose-widget-foss",
            "from aspose.widget",
            "MIT.",
        ):
            assert renderer_line not in shown, renderer_line


def test_findings_from_different_units_are_renumbered_and_all_block(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    first = at("Capability 1.")
    last_unit_line = at("is not implemented in this build")
    assert last_unit_line in units[-1].lines
    replies = [completion(reply())] * len(units)
    replies[1] = completion(
        reply(
            "REJECT_FACTUAL",
            line_finding("unsupported_claim", first, "key_capabilities"),
        )
    )
    replies[-1] = completion(
        reply(
            "REJECT_FACTUAL",
            line_finding("unsupported_claim", last_unit_line, "scope_limitations"),
        )
    )
    install(monkeypatch, replies)
    verdict = harness.review()
    assert verdict.verdict == "REJECT"
    assert [f.finding_id for f in verdict.blocking_findings] == ["F01", "F02"]
    assert [f.section_id for f in verdict.blocking_findings] == [
        "key_capabilities",
        "scope_limitations",
    ]
    assert verdict.model_verdict == "REJECT_FACTUAL"
    assert "blocks until" in blocked_predicate(verdict)


def test_a_finding_repeated_in_one_reply_is_one_blocking_finding(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    line = at("Capability 1.")
    repeats = [
        line_finding(
            "unsupported_claim",
            line,
            "key_capabilities",
            id=f"F{n:02d}",
            text=f"again {n}",
        )
        for n in range(1, 8)
    ]
    replies = [completion(reply())] * len(units)
    replies[1] = completion(reply("REJECT_FACTUAL", *repeats))
    install(monkeypatch, replies)
    verdict = harness.review()
    (only,) = verdict.blocking_findings
    assert "+6 identical findings merged" in only.message


def test_a_whole_section_quality_citation_is_valid_end_to_end(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    first, last = at("Capability 1."), at("Capability 30.")
    section = [u for u in units if "key_capabilities" in u.sections]
    replies = [completion(reply())] * len(units)
    index = units.index(section[0])
    span = (section[0].lines[0], section[0].lines[-1])
    assert span[1] - span[0] + 1 > 12 or first < last
    replies[index] = completion(
        reply(
            "REJECT_PRESENTATION",
            line_finding("quality", span[0], "key_capabilities", lines=list(span)),
        )
    )
    client = install(monkeypatch, replies)
    verdict = harness.review()
    assert verdict.verdict == "REJECT" and len(client.payloads) == len(units)
    assert harness.provider_calls() == len(
        units
    )  # no re-ask: the long citation was valid


def test_a_citation_of_a_line_the_unit_did_not_show_is_re_asked_then_unavailable(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    install_line = at("pip install aspose-widget-foss")
    bad = completion(
        reply(
            "REJECT_FACTUAL", line_finding("unsupported_claim", install_line, "opening")
        )
    )
    replies = [bad, bad] + [completion(reply())] * (len(units) - 1)
    install(monkeypatch, replies)
    with pytest.raises(ReviewUnavailable) as raised:
        harness.review()
    assert any("not shown to you" in e for e in raised.value.errors)


def test_an_unavailable_unit_makes_the_review_unavailable_unless_another_unit_blocks(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    garbage = completion("not json")
    replies = [completion(reply()), garbage, garbage] + [completion(reply())] * (
        len(units) - 2
    )
    install(monkeypatch, replies)
    with pytest.raises(ReviewUnavailable) as raised:
        harness.review()
    assert raised.value.retryable and f"unit {units[1].label}" in raised.value.reason


def test_a_blocking_unit_rejects_even_when_another_unit_is_unavailable(
    harness: Harness, monkeypatch, tmp_path: Path
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    garbage = completion("not json")
    blocking = completion(
        reply(
            "REJECT_FACTUAL",
            line_finding("unsupported_claim", units[0].lines[0], "opening"),
        )
    )
    replies = [blocking, garbage, garbage] + [completion(reply())] * (len(units) - 2)
    install(monkeypatch, replies)
    verdict = harness.review()
    assert verdict.verdict == "REJECT" and not verdict.retryable
    statuses = {r["unit"]: r["status"] for r in verdict.unit_reviews}
    assert statuses[units[0].label] == "reviewed"
    assert statuses[units[1].label] == "unavailable"
    path = tmp_path / "review_verdict.json"
    write_review_verdict(verdict, path)
    assert load_review_verdict(path) == verdict


def test_an_insufficient_unit_blocks_retryably_even_if_another_units_findings_are_cleared(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    cleared = reply(
        "REJECT_FACTUAL",
        {
            **line_finding("absence", at("Capability 1."), "key_capabilities"),
            "absent": ["quantum teleport mode"],
            "lines": [],
        },
    )
    replies = [completion(reply())] * len(units)
    replies[1] = completion(cleared)
    replies[2] = completion(reply("INSUFFICIENT_EVIDENCE"))
    install(monkeypatch, replies)
    verdict = harness.review()
    assert verdict.verdict == "REJECT" and verdict.retryable
    assert verdict.model_verdict == "INSUFFICIENT_EVIDENCE"
    assert any(f.status == "CLEARED" for f in verdict.findings)


def test_replay_makes_zero_calls_and_the_identical_verdict_bytes(
    harness: Harness, monkeypatch, tmp_path: Path
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    line = at("Capability 1.")
    replies = [completion(reply())] * len(units)
    replies[1] = completion(
        reply(
            "REJECT_FACTUAL",
            line_finding("unsupported_claim", line, "key_capabilities"),
        )
    )
    install(monkeypatch, replies)
    first = harness.review(invocation="inv-1")
    write_review_verdict(first, tmp_path / "a" / "v.json")
    client = install(monkeypatch, [])
    second = harness.review(invocation="inv-2")
    write_review_verdict(second, tmp_path / "b" / "v.json")
    assert client.payloads == [] and harness.provider_calls() == len(units)
    assert (tmp_path / "a" / "v.json").read_bytes() == (
        tmp_path / "b" / "v.json"
    ).read_bytes()


def test_only_the_blocking_unit_is_recorded_blocked_and_refused_a_fresh_ask(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    line = at("Capability 1.")
    replies = [completion(reply())] * len(units)
    replies[1] = completion(
        reply(
            "REJECT_FACTUAL",
            line_finding("unsupported_claim", line, "key_capabilities"),
        )
    )
    install(monkeypatch, replies)
    first = harness.review()
    record = json.loads(
        (harness.store.directory / BLOCKED_FILENAME).read_text(encoding="utf-8")
    )
    assert list(record["requests"]) == [first.unit_reviews[1]["request_sha256"]]
    for path in harness.store.directory.glob("*.json"):
        if path.name != BLOCKED_FILENAME:
            path.unlink()
    client = install(monkeypatch, [completion(reply())] * len(units))
    with pytest.raises(RerollRefused):
        harness.review(invocation="inv-2")
    assert (
        len(client.payloads) == 1
    )  # the unit before the blocked one was asked; then refused


def test_the_verdict_records_the_calibration_status_and_labels_an_accept_uncalibrated(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    install(monkeypatch, [completion(reply())] * len(units))
    verdict = harness.review()
    assert verdict.verdict == "ACCEPT"
    assert verdict.calibration_status == "NOT_PASSED"
    assert verdict.acceptance_label == "uncalibrated" and not verdict.pr_eligible


def test_a_candidate_with_nothing_an_author_wrote_is_unavailable_with_no_call(
    tmp_path: Path, monkeypatch
) -> None:
    only = (
        "# T\n\n## Installation\n\n```bash\npip install x\n```\n\n## License\n\nMIT.\n"
    )
    harness = Harness(tmp_path, only)
    client = install(monkeypatch, [])
    with pytest.raises(ReviewUnavailable, match="no author-written text"):
        harness.review()
    assert client.payloads == []


def test_more_findings_than_one_reply_may_hold_merge_into_one_verdict(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    replies = [completion(reply())] * len(units)
    for index in (1, 2, 3):
        unit = units[index]
        findings = [
            line_finding(
                "unsupported_claim",
                number,
                unit.sections[0],
                id=f"F{n:02d}",
            )
            for n, number in enumerate(unit.lines[:8], 1)
        ]
        replies[index] = completion(reply("REJECT_FACTUAL", *findings))
    install(monkeypatch, replies)
    verdict = harness.review()
    assert len(verdict.blocking_findings) > 16
    ids = [f.finding_id for f in verdict.blocking_findings]
    assert ids == [f"F{n:02d}" for n in range(1, len(ids) + 1)]


def test_the_original_readme_reaches_each_call_only_as_an_excerpt(
    harness: Harness, monkeypatch
) -> None:
    units = plan_units(CANDIDATE, max_chars=UNIT_BUDGET)
    client = install(monkeypatch, [completion(reply())] * len(units))
    harness.review()
    for payload in client.payloads:
        user = payload["messages"][1]["content"]
        assert "UNTRUSTED original_excerpt" in user
        assert "UNTRUSTED original_readme" not in user
    assert ORIGINAL  # the full original is an input of the review, never a packet field


# --- Lane L: a corrected live README is not printed by the renderer ----------------------------------

LIVE = """# Widget

Widget renders widgets.

## Installation

Run pip install widget to get the library. It supports every Python 3 release.

```bash
pip install widget
```

## License

Widget is licensed under the MIT License, which permits commercial use.
"""


def _review(harness: Harness, candidate: str, **extra: Any):
    from repo_presenter.core.llm.ledger import Ledger
    from tests.readme.review.test_llm_review import (
        CONFIG,
        CONTEXT,
        DISPOSITIONS,
        FACTS,
        PLAN,
        VALIDATION,
    )

    return llm_review.review_with_model(
        prompts=__import__(
            "tests.readme.review.test_llm_review", fromlist=["PROMPTS"]
        ).PROMPTS,
        config=CONFIG,
        ledger=Ledger(harness.ledger_path, invocation_id="inv-live"),
        store=harness.store,
        context=CONTEXT,
        candidate_readme=candidate,
        original_readme=ORIGINAL,
        facts=FACTS,
        plan=PLAN,
        dispositions=DISPOSITIONS,
        validation=VALIDATION,
        **extra,
    )


def _shown_in(client) -> str:
    return "\n".join(p["messages"][1]["content"] for p in client.payloads)


def test_lane_r_scope_is_the_default_and_withholds_the_renderers_sections(
    tmp_path: Path, monkeypatch
) -> None:
    harness = Harness(tmp_path, LIVE)
    client = install(monkeypatch, [completion(reply())] * 4)
    _review(harness, LIVE)
    text = _shown_in(client)
    assert "Widget renders widgets." in text
    assert "Run pip install widget" not in text and "licensed under the MIT" not in text


def test_lane_l_scope_shows_the_maintainers_installation_and_license_prose(
    tmp_path: Path, monkeypatch
) -> None:
    harness = Harness(tmp_path, LIVE)
    client = install(monkeypatch, [completion(reply())] * 4)
    verdict = _review(harness, LIVE, rendered=False)
    text = _shown_in(client)
    assert "Run pip install widget to get the library." in text
    assert "licensed under the MIT License" in text
    # markup is withheld whoever wrote it
    assert (
        "```bash"
        not in text.split("BEGIN UNTRUSTED candidate_section")[1].split(
            "END UNTRUSTED candidate_section"
        )[0]
    )
    assert verdict.verdict == "ACCEPT"


def test_a_lane_l_candidate_has_no_renderer_owned_exclusion_beyond_markup() -> None:
    from repo_presenter.readme.review.scope import reviewable_lines

    rows = LIVE.splitlines()
    prose = {
        n
        for n, row in enumerate(rows, 1)
        if row.strip() and not row.startswith(("#", "```", "pip install"))
    }
    assert set(reviewable_lines(LIVE, rendered=False)) == prose
    assert (
        set(reviewable_lines(LIVE)) < prose
    )  # Lane R withholds installation and license
