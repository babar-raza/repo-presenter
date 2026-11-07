"""BC-14 rules (h)-(m): the mechanically checkable false claims (class A) and the generator-authored
counts and verification narratives (class D) of the 2026-11-06 claim-class audit.

Every fixture is synthetic (the shape of an audited case, never its text): a wrong public-type
count, an API-table row naming a type the public surface does not hold, a stub described as
working, a CONTRADICTED example printed in full, a truncated package name, an uncomputed structure
count, and an invented verification narrative. Each has its negative twin, the clean form the rule
must leave alone.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.independent_reviewer import claim_contradiction_rule
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.provenance import claim_failures

REVISION = "a" * 40


def _fact(
    fact_id: str,
    kind: str,
    value: str,
    detail: str | None = None,
    *,
    polarity: str = "SUPPORTED",
    attributes: dict[str, str] | None = None,
) -> Fact:
    return Fact(
        fact_id,
        kind,  # type: ignore[arg-type]
        value,
        (Evidence("src/lib.py", detail),),
        polarity=polarity,  # type: ignore[arg-type]
        attributes=attributes,
    )


def _type(name: str, kind: str = "class", docstring: str | None = None) -> Fact:
    attributes = {"symbol_kind": kind, "defined_at": f"acme.widgets.{name}"}
    if docstring:
        attributes["docstring"] = docstring
    return _fact(
        f"public_symbol:acme.widgets.{name.lower()}",
        "public_symbol",
        f"acme.widgets.{name}",
        f"line 1; {kind}; public by name",
        attributes=attributes,
    )


def _module(name: str) -> Fact:
    return _fact(
        f"public_symbol:{name}",
        "public_symbol",
        name,
        attributes={"symbol_kind": "module"},
    )


def _unit(number: str, text: str, kind: str = "list") -> Fact:
    return _fact(
        f"inherited_unit:{number}.{kind}",
        "inherited_unit",
        text,
        f"lines 1-9; {kind}; under Acme > Scope and Limitations",
    )


TYPES = tuple(
    _type(name)
    for name in (
        "Workbook",
        "Worksheet",
        "Cell",
        "Style",
        "Chart",
        "Scene",
        "Watermark",
        "XmlMapper",
    )
)
ENUMS = (_type("SaveFormat", "enum"), _type("LoadFormat", "enum"))


def _facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        "acme/widgets",
        REVISION,
        (_fact("package:name", "package", "acme-widgets-foss"), *TYPES, *ENUMS, *extra),
    )


def _details(readme: str, facts: FactsDocument) -> list[str]:
    return [finding.detail for finding in claim_findings(readme, facts)]


# --- (h) type counts -------------------------------------------------------------------------


def test_a_public_type_count_the_facts_do_not_give_fails() -> None:
    readme = "## API Reference\n\nThe public API surface spans 12 public types across the tables below.\n"
    details = _details(readme, _facts())
    assert (
        len(details) == 1
        and "'12 public types'" in details[0]
        and "10 public types" in details[0]
    )


def test_the_computed_count_and_unrelated_numbers_pass() -> None:
    readme = (
        "The verified public surface has 10 types.\n\n"
        "It covers all 10 verified public types.\n\n"
        "| `Workbook` | Class with 12 methods and 3 properties. |\n\n"
        "The reference site lists 40 types published there.\n"
    )
    assert _details(readme, _facts()) == []


def test_a_count_wrapped_over_two_lines_is_read_as_one_sentence() -> None:
    readme = "The\nfull public surface — 11 public types — is listed below.\n"
    findings = claim_findings(readme, _facts())
    assert [(finding.line, finding.last) for finding in findings] == [(0, 1)]


def test_a_maintainer_count_above_the_facts_is_a_coverage_question_not_a_contradiction() -> (
    None
):
    # The maintainers may count kinds the extractor does not record (a .NET delegate).
    sentence = "The library exposes 14 public types in total, listed below by module."
    facts = _facts(_unit("010", sentence, "paragraph"))
    assert _details(f"{sentence}\n", facts) == []
    below = "The library exposes 7 public types in total, listed below by module."
    assert len(_details(f"{below}\n", _facts(_unit("010", below, "paragraph")))) == 1
    # The pipeline's own sentence above the facts is an uncomputed count.
    assert len(_details(f"{sentence}\n", _facts())) == 1


# --- (i) API-table names ---------------------------------------------------------------------

TABLE = """| Class | Description |
|---|---|
| `Workbook` | Represents a workbook. |
| `Worksheet` | Represents a worksheet. |
| `Cell` | Represents a cell. |
| `Style` | Represents a style. |
"""


def test_an_api_table_row_naming_a_type_the_surface_does_not_hold_fails() -> None:
    readme = TABLE + "| `Workbook_Impl` | Struct with 1 method and 7 properties. |\n"
    details = _details(readme, _facts())
    assert len(details) == 1 and "`Workbook_Impl`" in details[0]


def test_a_name_a_public_signature_uses_and_a_delegate_row_pass() -> None:
    returned = _fact(
        "public_symbol:acme.widgets.workbook.charts",
        "public_symbol",
        "acme.widgets.Workbook.charts",
        attributes={
            "symbol_kind": "method",
            "signature": "def charts(self) -> ChartCollection",
        },
    )
    readme = (
        TABLE
        + "| `ChartCollection` | The workbook's charts. |\n"
        + "| `BeforeSave` | Callback fired before each page is written. |\n"
    )
    assert _details(readme, _facts(returned)) == []


def test_a_table_that_is_not_an_api_type_table_is_not_judged() -> None:
    readme = "| Option | Meaning |\n|---|---|\n| `--fast` | a |\n| `--slow` | b |\n| `--deep` | c |\n"
    assert _details(readme, _facts()) == []


# --- (j) stubs described as working ----------------------------------------------------------

LIMITATIONS = _unit(
    "056",
    "- `Scene.render()` raises `NotImplementedError` — this library does not render scenes.\n"
    "- The mapper class (`XmlMapper`) exists in source but its read/write methods "
    "unconditionally throw `UnsupportedFeatureException`.\n"
    "- Text watermarking is not currently functional in this build.\n"
    "- `Workbook.Save()` raises `UnsupportedFormatException` for any other format.\n"
    "- `Style`'s theme accessors are not implemented, even though `Chart` exists as a holder.",
)


def test_a_stubbed_member_or_type_described_as_working_fails() -> None:
    readme = (
        TABLE.replace("| `Style` | Represents a style. |\n", "")
        + "| `Scene` | Loads, saves and renders 3D scenes; rendering is its main entry point. |\n"
        + "| `XmlMapper` | Maps workbook XML content for XLSX files. |\n"
        + "| `Watermark` | Embeds and extracts text watermarks. |\n"
    )
    details = _details(readme, _facts(LIMITATIONS))
    assert len(details) == 3
    assert "`Scene.render` only throws" in details[0]
    assert "`XmlMapper` only throws" in details[1]
    assert "`Watermark` only throws" in details[2]


def test_an_honest_description_a_conditional_throw_and_a_possessive_subject_pass() -> (
    None
):
    readme = (
        TABLE
        + "| `Scene` | Loads and saves scenes; rendering is not implemented. |\n"
        + "| `XmlMapper` | Mapper class for the legacy XML dialect. |\n"
        + "| `Chart` | Provides chart configuration. |\n"
        + "| `Watermark` | Watermark settings holder. |\n"
        + "`Workbook` saves workbooks to XLSX.\n"
    )
    # `Style`'s accessors, not Style, are stubbed; `Workbook.Save` throws only for other formats;
    # `Chart` is named after the marker; a noun-first description says what a stub is.
    assert _details(readme, _facts(LIMITATIONS)) == []


# --- (k) CONTRADICTED examples printed --------------------------------------------------------

CODE = "doc = acme.Document('a.one')\nfor page in doc:\n    print(page.title.text)\n"


def _example(detail: str) -> Fact:
    return _fact(
        "example:001",
        "example",
        CODE,
        detail,
        polarity="CONTRADICTED",
    )


def test_a_failing_example_printed_in_full_fails_and_quotes_its_fence() -> None:
    readme = f"## Quick Start\n\n```python\n{CODE}```\n"
    facts = _facts(_example("example 1: FAILED; AttributeError"))
    findings = claim_findings(readme, facts)
    assert len(findings) == 1 and "example:001" in findings[0].detail
    (rule,) = claim_contradiction_rule(readme, facts)
    assert "print(page.title.text)" in rule.quote


def test_a_repaired_example_or_an_environment_failure_passes() -> None:
    repaired = f"```python\n{CODE.replace('    print(page.title.text)', '    print(page.number)')}```\n"
    assert (
        _details(repaired, _facts(_example("example 1: FAILED; AttributeError"))) == []
    )
    printed = f"```python\n{CODE}```\n"
    for detail in (
        "example 1: FAILED; ImportError",
        (
            "example 1: FAILED; AttributeError; ran against the repository source tree; the "
            "package would not build"
        ),
    ):
        assert _details(printed, _facts(_example(detail))) == []


# --- (l) the stated package name --------------------------------------------------------------


def test_a_truncated_package_name_stated_as_the_distribution_name_fails() -> None:
    readme = "The distribution name is `acme-widgets` (declared in `pyproject.toml`).\n"
    details = _details(readme, _facts())
    assert len(details) == 1 and "'acme-widgets'" in details[0]


def test_the_identity_an_import_path_and_an_unframed_span_pass() -> None:
    facts = _facts(_fact("import_path:acme_widgets", "import_path", "acme_widgets"))
    readme = (
        "The distribution name is `acme-widgets-foss`.\n\n"
        "The package name for imports is `acme_widgets`.\n\n"
        "See `acme-widgets` on the forum.\n"
    )
    assert _details(readme, facts) == []


# --- (m) generator guard: structure count, verification narrative ------------------------------


def test_an_uncomputed_single_module_claim_and_a_verification_narrative_fail() -> None:
    facts = _facts(_module("acme.widgets"), _module("acme.widgets.core"))
    readme = (
        "The surface holds 10 public types organized into one module.\n\n"
        "Everything below was exercised through the public API and then confirmed by reading the "
        "output.\n\n"
        "These real outputs mirror the fixture-backed examples of the demo site.\n"
    )
    details = _details(readme, facts)
    assert len(details) == 3
    assert "organized into one module" in details[0]
    assert all("narrates a verification" in detail for detail in details[1:])


def test_maintainer_text_and_a_negated_or_factual_mention_pass() -> None:
    quoted = (
        "Everything below was tested by the maintainers against the conformance suite."
    )
    facts = _facts(
        _module("acme.widgets"),
        _module("acme.widgets.core"),
        _unit("012", quoted, "paragraph"),
    )
    readme = (
        f"{quoted}\n\n"
        "Verify the install:\n\n"
        "The test suite is run to verify functionality.\n\n"
        "A module groups 10 public types across 2 modules.\n"
    )
    assert _details(readme, facts) == []
    # A single-module claim is never judged without module facts to hold it to.
    assert (
        _details("All 10 public types are organized into one module.\n", _facts()) == []
    )


# --- TC-017b work item 4: the verification-narrative ban, now conditional ----------------------


def _executed_example(ordinal: str, code: str = CODE) -> Fact:
    """A genuinely, fully passed example: SUPPORTED at confidence 1.0, the only thing
    ``readme/evidence/facts/examples.py`` ever writes for an ``EXECUTED`` receipt."""
    return Fact(
        f"example:{ordinal}",
        "example",
        code,
        (Evidence("docs/quickstart.md", f"example {ordinal}: EXECUTED"),),
        polarity="SUPPORTED",
        confidence=1.0,
    )


def _unresolved_example(ordinal: str, code: str = CODE) -> Fact:
    """A TIMED_OUT (or NEEDS_INPUT/NOT_VERIFIED) receipt: UNRESOLVED at confidence 0.5, post-
    TC-016's own fix -- a timeout proves nothing either way, so it must never, by itself, license
    a verification narrative."""
    return Fact(
        f"example:{ordinal}",
        "example",
        code,
        (Evidence("docs/quickstart.md", f"example {ordinal}: TIMED_OUT"),),
        polarity="UNRESOLVED",
        confidence=0.5,
    )


NARRATIVE = (
    "Everything below was exercised through the public API and then confirmed by reading the "
    "output.\n"
)


def test_a_verification_narrative_backed_by_a_fully_verified_example_passes() -> None:
    facts = _facts(_executed_example("001"))
    assert _details(NARRATIVE, facts) == []


def test_a_verification_narrative_with_no_example_facts_at_all_still_fails() -> None:
    details = _details(NARRATIVE, _facts())
    assert len(details) == 1 and "narrates a verification" in details[0]
    assert "no real, fully-passed verification record" in details[0]


def test_a_timed_out_example_never_backs_a_verification_narrative() -> None:
    # The card's own wording: "NOT merely not UNRESOLVED -- only a genuinely passed execution
    # counts." One real EXECUTED example beside one TIMED_OUT (UNRESOLVED, confidence 0.5) one
    # is not "every example fully passed," so the narrative is still rejected.
    facts = _facts(_executed_example("001"), _unresolved_example("002"))
    details = _details(NARRATIVE, facts)
    assert len(details) == 1 and "narrates a verification" in details[0]


def test_a_contradicted_example_among_passes_also_blocks_the_narrative() -> None:
    failed = Fact(
        "example:002",
        "example",
        CODE,
        (Evidence("docs/quickstart.md", "example 2: FAILED; AttributeError"),),
        polarity="CONTRADICTED",
        confidence=1.0,
    )
    facts = _facts(_executed_example("001"), failed)
    details = _details(NARRATIVE, facts)
    assert len(details) == 1 and "narrates a verification" in details[0]


def test_maintainer_text_narrating_verification_is_never_judged_by_this_ban() -> None:
    # Rule (m)'s own open-world carve-out, unaffected by the new condition: quoted maintainer
    # text is the reconciliation stage's concern, not this generator-only ban's, whether or not
    # any example fact exists at all.
    facts = _facts(_unit("090", NARRATIVE.strip(), "paragraph"))
    assert _details(f"{NARRATIVE.strip()}\n", facts) == []


# --- routing ---------------------------------------------------------------------------------


def test_kept_maintainer_text_routes_to_reconciling_with_its_unit_and_the_rest_to_composing() -> (
    None
):
    kept = "The library exposes 7 public types in total, listed below by module."
    facts = _facts(_unit("046", kept, "paragraph"))
    readme = f"## API Reference\n\n{kept}\n\nThe surface spans 12 public types.\n"
    candidate = SimpleNamespace(readme=readme, facts=facts)
    failures = claim_failures(candidate)  # type: ignore[arg-type]
    assert [(failure.stage, failure.unit) for failure in failures] == [
        ("RECONCILING", "inherited_unit:046.paragraph"),
        ("COMPOSING", None),
    ]
    assert all(failure.section == "api_reference" for failure in failures)
