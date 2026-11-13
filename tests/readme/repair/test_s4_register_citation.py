"""BC-18: a repair answering a confirmed findings-register row may cite that row as its evidence.

Two hosted Lane R runs (2026-11-13) left a BC-18 defect unrepairable because the repair had no fact
it was allowed to cite for a claim only the register proves false:

* Aspose.PSD-FOSS-for-.NET, run 43419183454: the paragraph quoting "the matching `Program.cs`
  files must always remain identical" was answered CORRECT_WITH_EVIDENCE twice with empty
  ``fact_ids`` ("CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence").
* Aspose.Cells-FOSS-for-Java, run 43419171411: ``mvn javadoc:javadoc   # generates
  docs/apidocs/index.html`` sits in a code block of true build commands; both asks kept the block
  VERIFIED_PRESERVE ("still VERIFIED_PRESERVE, which prints the quoted text as written"), and the
  zero-call fold covers only paragraphs and lists.

The register row is the evidence BC-18 already trusts: it is cited as ``finding:<hex>``
(``FindingRecord.citation_id``), which binding admits only for an OPEN row of the repository
being judged. The same two shapes are reproduced offline on the Font Python S4 fixture
(``test_s4_repair``): its ``100.code_block`` holds a false install line beside a true command, and
its ``101.paragraph`` stands in for the false prose.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.binding import binding_errors
from repo_presenter.readme.composition.placement import placements
from repo_presenter.readme.parity_gate import withheld_by_finding
from repo_presenter.readme.repair.loop import repair_defect
from repo_presenter.readme.repair.targeted import Defect, validation_defects
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation import must_correct
from repo_presenter.readme_findings import (
    append_finding,
    read_findings,
    resolve_finding,
)
from tests.readme.repair.test_s4_repair import (
    AFTER,
    COMMAND,
    HOME,
    PLAN,
    WRONG_LINE,
    _by_unit,
    _Case,
    _entry,
    _reply,
)

PROSE_QUOTE = "machine-readable variable-font compatibility"
TRUE_LINE = "python -m aspose_font.mcp"


@pytest.fixture
def register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "readme_findings.json"
    monkeypatch.setattr(must_correct, "DEFAULT_FINDINGS_PATH", path)
    return path


def _row(path: Path, repository: str, quote: str, description: str) -> str:
    row = append_finding(
        path,
        repository=repository,
        description=description,
        evidence="pyproject.toml:1@0000000",
        route="lane_r",
        first_seen_at="2026-11-12",
        quote=quote,
        truth="the source says otherwise",
    )
    return row.citation_id()


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, register: Path) -> _Case:
    return _Case(tmp_path, monkeypatch)


def _bc18(unit: str, quote: str) -> Defect:
    validation = {
        "validator_version": "test",
        "checks": [
            {
                "id": "BC-18",
                "name": "must-correct",
                "verdict": "FAIL",
                "causal_stage": "RECONCILING",
                "details": [f"open finding still printed: {quote}"],
                "failures": [
                    {
                        "unit_id": unit,
                        "detail": f"open finding still printed: {quote}",
                        "quote": quote,
                        "instruction": f"The README text {quote!r} is false.",
                    }
                ],
            }
        ],
    }
    [defect] = validation_defects(validation, set())
    assert defect.stage == "S4"
    return defect


def _kept_block(fingerprint: str) -> dict[str, Any]:
    return _reply(
        fingerprint,
        _entry(COMMAND, "VERIFIED_PRESERVE", HOME, [], "the build commands, kept as written"),
    )


def _uncited_correction(fingerprint: str) -> dict[str, Any]:
    return _reply(
        fingerprint,
        _entry(AFTER, "CORRECT_WITH_EVIDENCE", HOME, [], "the claim is false; corrected"),
    )


# --- the Cells Java shape: one false line in a block of true commands -------------------------


def test_a_kept_code_block_cites_the_row_and_prints_without_only_the_false_line(
    case: _Case, register: Path
) -> None:
    citation = _row(register, case.facts.repository, WRONG_LINE, "confirmed false claim: install")
    defect = _bc18(COMMAND, WRONG_LINE)
    client = case.script([_kept_block(defect.fingerprint), _kept_block(defect.fingerprint)])

    assert repair_defect(case.rc, defect, case.repairs) is True

    assert client.chat.completions.replies == []  # both asks spent; the fold made no call
    assert case.repairs.attempts[defect.fingerprint]["outcome"] == "repaired"
    stored = case.stored_now()  # re-judged by schema, binding and checks, served with no call
    unit = _by_unit(stored)[COMMAND]
    assert unit["disposition"] == "VERIFIED_PRESERVE"
    assert unit["destination_section"] == HOME
    assert citation in unit["fact_ids"]
    assert unit["rationale"].startswith("The findings register confirms")

    [placed] = [p for p in placements(PLAN, stored, case.facts, "python") if p.unit_id == COMMAND]
    assert WRONG_LINE not in placed.text  # BC-18 no longer finds the quote
    assert TRUE_LINE in placed.text  # the true command is kept (R14: nothing else is dropped)
    assert placed.text.startswith("```bash") and placed.text.endswith("```")


def test_the_model_may_cite_the_row_itself(case: _Case, register: Path) -> None:
    citation = _row(register, case.facts.repository, WRONG_LINE, "confirmed false claim: install")
    defect = _bc18(COMMAND, WRONG_LINE)
    cited = _reply(
        defect.fingerprint,
        _entry(COMMAND, "VERIFIED_PRESERVE", HOME, [citation], "kept without the false line"),
    )
    client = case.script([cited])

    assert repair_defect(case.rc, defect, case.repairs) is True
    assert client.chat.completions.replies == []
    assert _by_unit(case.stored_now())[COMMAND]["fact_ids"] == [citation]


def test_bc08_bc17_and_the_reviewer_account_for_the_withheld_line_and_nothing_else(
    case: _Case, register: Path
) -> None:
    citation = _row(register, case.facts.repository, WRONG_LINE, "confirmed false claim: install")
    row = _entry(COMMAND, "VERIFIED_PRESERVE", HOME, [citation], "kept without the false line")
    # BC-17 (parity_gate): the false line is accounted, by the cited row; the true one is not.
    assert withheld_by_finding(row, WRONG_LINE)
    assert withheld_by_finding(row, f"```bash\n{WRONG_LINE}\n{TRUE_LINE}\n```")
    assert not withheld_by_finding(row, TRUE_LINE)
    assert not withheld_by_finding({**row, "fact_ids": []}, WRONG_LINE)
    # The reviewer judges the same printed form the renderer prints.
    readme = f"## Key Capabilities\n\n```bash\n{TRUE_LINE}\n```\n"
    dispositions = {"dispositions": [row]}
    assert unprinted_kept_units(readme, facts=case.facts, dispositions=dispositions) == []
    uncited = {"dispositions": [{**row, "fact_ids": []}]}
    assert unprinted_kept_units(readme, facts=case.facts, dispositions=uncited) == [
        (COMMAND, "VERIFIED_PRESERVE")
    ]


def test_a_block_of_nothing_but_false_lines_is_not_kept_by_citation() -> None:
    block = f"```bash\n{WRONG_LINE}\n```"
    assert must_correct.without_quoted_lines(block, [WRONG_LINE]) == block
    assert not must_correct.line_omission_holds(block, [WRONG_LINE])


# --- the PSD .NET shape: CORRECT_WITH_EVIDENCE with nothing to cite --------------------------


def test_an_uncited_correction_of_quoted_prose_cites_the_row(case: _Case, register: Path) -> None:
    citation = _row(register, case.facts.repository, PROSE_QUOTE, "confirmed false claim: prose")
    defect = _bc18(AFTER, PROSE_QUOTE)
    client = case.script(
        [_uncited_correction(defect.fingerprint), _uncited_correction(defect.fingerprint)]
    )

    assert repair_defect(case.rc, defect, case.repairs) is True

    assert client.chat.completions.replies == []
    unit = _by_unit(case.stored_now())[AFTER]
    assert unit["disposition"] == "CORRECT_WITH_EVIDENCE"
    assert unit["fact_ids"] == [citation]
    # BC-17: CORRECT_WITH_EVIDENCE is a non-loss disposition (parity_gate.NON_LOSS_ALWAYS), and
    # it is not a kept disposition, so the reviewer does not look for its text.
    from repo_presenter.readme.parity_gate import disposition_is_non_loss

    assert disposition_is_non_loss(unit, {})


def test_without_a_register_row_the_uncited_correction_is_still_refused(case: _Case) -> None:
    defect = _bc18(AFTER, PROSE_QUOTE)
    before = copy.deepcopy(case.stage)
    case.script([_uncited_correction(defect.fingerprint), _uncited_correction(defect.fingerprint)])

    assert repair_defect(case.rc, defect, case.repairs) is False

    reason = case.repairs.attempts[defect.fingerprint]["reason"]
    assert "CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence" in reason
    assert case.stored_now() == before


# --- binding: only an OPEN row of this repository is citable ---------------------------------


def _facts(repository: str) -> FactsDocument:
    return FactsDocument(repository, "0" * 40, ())


def _cites(citation: str) -> dict[str, Any]:
    return {"dispositions": [{"fact_ids": [citation]}]}


def test_binding_admits_only_an_open_row_of_the_repository_judged(register: Path) -> None:
    citation = _row(register, "org/one", WRONG_LINE, "confirmed false claim: install")
    assert binding_errors(_cites(citation), _facts("org/one"), "finding_ids") == []
    # another repository's row, an invented ID, and a row that is no longer OPEN are not evidence
    assert binding_errors(_cites(citation), _facts("org/two"), "finding_ids")
    assert binding_errors(_cites("finding:000000000000"), _facts("org/one"), "finding_ids")
    [row] = read_findings(register)
    resolve_finding(
        register, repository=row.repository, description=row.description, resolved_at="2026-11-13"
    )
    assert binding_errors(_cites(citation), _facts("org/one"), "finding_ids")


def test_a_register_row_never_supports_a_printed_claim(register: Path) -> None:
    citation = _row(register, "org/one", WRONG_LINE, "confirmed false claim: install")
    errors = binding_errors(_cites(citation), _facts("org/one"), "fact_ids")
    assert errors == [f"fact {citation} is a confirmed false claim (findings register), not SUPPORTED"]


def test_the_bc18_instruction_names_the_citation(register: Path) -> None:
    _row(register, "org/one", WRONG_LINE, "confirmed false claim: install")
    [row] = read_findings(register)
    assert row.citation_id() in must_correct._instruction(row)
    assert row.citation_id().startswith("finding:") and len(row.citation_id()) == 20


# --- the Cells Rust shape: a correction that would lose the paragraph's true commands --------
# Aspose.Cells-FOSS-for-Rust, hosted Lane R run 43419190710: 079.paragraph (its real text, cut
# down) was repaired CORRECT_WITH_EVIDENCE for its false CI sentence, then failed BC-08 because a
# Lane R correction is never authored (the authoring contract forbids literal commands), so
# `cargo bench` and `cargo doc --no-deps --open` were printed nowhere.

RUST_UNIT = "inherited_unit:079.paragraph"
RUST_TEXT = (
    "CI ([`ci.yml`](.github/workflows/ci.yml)) runs `fmt`, `check`, `clippy`, `test`, the three\n"
    "samples above as smoke tests, and `cargo bench` on Linux x64, Windows x64, macOS ARM, and\n"
    "macOS x64. The `samples/` directory demonstrates every feature area — `basic.rs`,\n"
    "`styles.rs` (see\n[`samples/README.md`](samples/README.md) for the full overview). "
    "Generate local API docs\nwith `cargo doc --no-deps --open`; published API docs are deployed "
    "by GitHub Pages."
)
RUST_QUOTE = (
    "CI ([`ci.yml`](.github/workflows/ci.yml)) runs `fmt`, `check`, `clippy`, `test`, the three"
)


def test_a_paragraph_prints_without_only_the_sentence_the_row_confirms_false() -> None:
    printed = must_correct.withheld_form(RUST_UNIT, RUST_TEXT, [RUST_QUOTE])
    assert printed.startswith("The `samples/` directory demonstrates")
    assert "`cargo doc --no-deps --open`" in printed
    assert "cargo bench" not in printed and "CI (" not in printed
    # BC-08 / BC-17 exempt exactly what sits in the withheld sentence.
    assert must_correct.withheld_text_holds(RUST_UNIT, RUST_TEXT, [RUST_QUOTE], "cargo bench")
    assert not must_correct.withheld_text_holds(
        RUST_UNIT, RUST_TEXT, [RUST_QUOTE], "cargo doc --no-deps --open"
    )
    # A paragraph that is nothing but the quote is withheld, not kept.
    assert not must_correct.omission_holds(RUST_UNIT, RUST_QUOTE + ".", [RUST_QUOTE])


def _rust_facts() -> FactsDocument:
    from repo_presenter.core.facts import Evidence, Fact

    return FactsDocument(
        "org/rust",
        "0" * 40,
        (
            Fact("identity:repository", "identity", "org/rust", (Evidence("x"),)),
            Fact("build_test_asset:ci", "build_test_asset", ".github/workflows/", (Evidence("x"),)),
            Fact(RUST_UNIT, "inherited_unit", RUST_TEXT, (Evidence("README.md", None),)),
        ),
    )


def _corrected_rust() -> dict[str, Any]:
    return {
        "dispositions": [
            _entry(
                RUST_UNIT,
                "CORRECT_WITH_EVIDENCE",
                "development_testing",
                ["build_test_asset:ci"],
                "the CI sentence is wrong",
            )
        ]
    }


def test_a_register_backed_correction_that_would_lose_commands_is_kept_citing_the_row(
    register: Path,
) -> None:
    """Zero-call, in the batch's own checks: the stored repaired batch is re-judged by them on the
    next run, so the corrected unit is kept as written (in the section it named) citing the row,
    and prints its true commands without the false CI sentence."""
    from repo_presenter.readme.reconciliation.dispositions import normalize

    citation = _row(register, "org/rust", RUST_QUOTE, "confirmed false claim: CI")
    output = _corrected_rust()
    normalize(output, _rust_facts())
    [entry] = output["dispositions"]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "development_testing"
    assert entry["fact_ids"] == ["build_test_asset:ci", citation]
    assert binding_errors(output, _rust_facts(), "unit_ids") == []


def test_without_a_register_row_a_correction_is_left_as_given(register: Path) -> None:
    from repo_presenter.readme.reconciliation.dispositions import normalize

    _row(register, "org/other", RUST_QUOTE, "confirmed false claim: CI")  # another repository's
    output = _corrected_rust()
    normalize(output, _rust_facts())
    assert output == _corrected_rust()



