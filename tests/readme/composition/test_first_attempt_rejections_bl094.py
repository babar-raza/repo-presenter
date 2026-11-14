"""First-attempt section_authoring rejections on the PDF family (BL-094, BL-095, BL-096), each from
the real logged shape of version set 81a1cb4204c1, with a negative control.

- BL-094: Aspose.PDF-FOSS-for-.NET run 43572741039, "unit type:public_symbol:aspose.pdf.permissions:
  identifiers that are not accepted fact values: AssembleDocument, ExtractContentWithDisabilities,
  FillForm, ModifyTextAnnotations (nearest accepted: ModifyAnnotations), PrintingQuality" (and
  Aspose.PDF-FOSS-for-Cpp run 43572742592, LineIntent's LineArrow, LineDimension): enum values the
  type batch's own packet lists were refused by the identifier check.
- BL-095: Aspose.PDF-FOSS-for-TypeScript run 43572744168, "unit type:public_symbol:datamatrixoptions:
  identifiers that are not accepted fact values: DataMatrix (nearest accepted: DataMatrixOptions,
  DataMatrixOptions.shape)": the symbology the facts spell "Data Matrix", run together.
- BL-096: Aspose-PDF-FOSS-for-Go run 43572737387, "unit summary: text contains HTML ('<'): <name>":
  the maintainer's ``_examples/<name>/main.go`` placeholder restated in prose.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    _bare_angle_bracket,
    _type_batches,
    recorded_placeholders,
    restore_word_forms,
    type_members,
    unit_checks,
    word_form,
)
from tests.readme.composition.synthetic import make_entry, make_facts

NAME = "Aspose.Widget FOSS for Python"
PERMISSIONS = "public_symbol:aspose.pdf.permissions"
LINE_INTENT = "public_symbol:aspose.pdf.annotations.lineintent"
OPTIONS = "public_symbol:datamatrixoptions"
#: The real enum members of Aspose.Pdf.Permissions at 1d21c959 (src/Security/Permissions.cs).
PERMISSION_VALUES = (
    "AssembleDocument",
    "ExtractContent",
    "ExtractContentWithDisabilities",
    "FillForm",
    "ModifyContent",
    "ModifyTextAnnotations",
    "PrintDocument",
    "PrintingQuality",
)


def _enum(fact_id: str, value: str, path: str, members: tuple[str, ...]) -> list[Fact]:
    facts = [
        Fact(
            fact_id,
            "public_symbol",
            value,
            (Evidence(path, "line 6; enum; public by declaration"),),
            attributes={"symbol_kind": "enum", "type_kind": "enum"},
        )
    ]
    facts.extend(
        Fact(
            f"enum_member:{value.lower()}.{member.lower()}",
            "enum_member",
            f"{value}.{member}",
            (Evidence(path, f"line 7; member of enum {value}"),),
            attributes={"enum": value},
        )
        for member in members
    )
    return facts


def _facts(*extra: Fact) -> FactsDocument:
    base = make_facts()
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _type_unit(facts: FactsDocument, fact_id: str, text: str) -> tuple[dict, object]:
    tasks = [task for task in _type_batches(make_entry(), facts, []) if f"type:{fact_id}" in task.slots]
    (task,) = tasks
    units = [
        {
            "section": "api_reference",
            "slot": slot,
            "text": text if slot == f"type:{fact_id}" else "A public type.",
            "fact_ids": [slot.removeprefix("type:")],
        }
        for slot in task.slots
    ]
    return {"units": units, "omitted": []}, task


def _stray(errors: list[str], fact_id: str) -> list[str]:
    return [e for e in errors if e.startswith(f"unit type:{fact_id}:") and "not accepted" in e]


# BL-094 ------------------------------------------------------------------------------------


def _pdf_enums() -> FactsDocument:
    return _facts(
        *_enum(PERMISSIONS, "Aspose.Pdf.Permissions", "src/Security/Permissions.cs", PERMISSION_VALUES),
        *_enum(
            LINE_INTENT,
            "Aspose.Pdf.Annotations.LineIntent",
            "src/Annotations/LineIntent.cs",
            ("LineArrow", "LineDimension", "Undefined"),
        ),
    )


def test_the_packet_lists_the_enum_values_the_check_now_accepts() -> None:
    facts = _pdf_enums()
    by_id = {fact.id: fact for fact in facts.facts}
    assert set(PERMISSION_VALUES) <= set(type_members(by_id[PERMISSIONS], facts))
    text = (
        "Permissions has members AssembleDocument, ExtractContent, ExtractContentWithDisabilities, "
        "FillForm, ModifyContent, ModifyTextAnnotations, PrintDocument and PrintingQuality."
    )
    output, task = _type_unit(facts, PERMISSIONS, text)
    assert _stray(unit_checks(output, task, facts, NAME, register=False), PERMISSIONS) == []


def test_the_cpp_line_intent_values_are_accepted_in_their_own_unit() -> None:
    facts = _pdf_enums()
    output, task = _type_unit(facts, LINE_INTENT, "LineIntent has members LineArrow, LineDimension and Undefined.")
    assert _stray(unit_checks(output, task, facts, NAME, register=False), LINE_INTENT) == []


def test_negative_control_another_enums_values_and_invented_values_stay_refused() -> None:
    facts = _pdf_enums()
    output, task = _type_unit(
        facts, PERMISSIONS, "Permissions has members FillForm, LineArrow and EncryptEverything."
    )
    errors = _stray(unit_checks(output, task, facts, NAME, register=False), PERMISSIONS)
    assert len(errors) == 1
    assert "LineArrow" in errors[0] and "EncryptEverything" in errors[0]
    assert "FillForm" not in errors[0].split("values: ", 1)[1]


# BL-095 ------------------------------------------------------------------------------------


def _typescript_barcodes() -> FactsDocument:
    return _facts(
        Fact(
            OPTIONS,
            "public_symbol",
            "DataMatrixOptions",
            (Evidence("src/datamatrix.ts", "line 7; class; public by export"),),
            attributes={"symbol_kind": "class", "declaration": "export interface DataMatrixOptions"},
        ),
        Fact(
            "public_symbol:datamatrixoptions.shape",
            "public_symbol",
            "DataMatrixOptions.shape",
            (Evidence("src/datamatrix.ts", "line 10; method; public by export"),),
            attributes={
                "symbol_kind": "method",
                "docstring": "'square' (default), 'rectangle', or 'any' -- the smallest symbol of "
                "either shape that holds the data.",
            },
        ),
        Fact(
            "public_symbol:makedatamatrix",
            "public_symbol",
            "makeDataMatrix",
            (Evidence("src/datamatrix.ts", "line 225; function; public by export"),),
            attributes={
                "symbol_kind": "function",
                "docstring": "Generate a Data Matrix ECC 200 symbol for `data`.",
            },
        ),
    )


def test_a_run_together_symbology_name_is_written_as_the_facts_words() -> None:
    facts = _typescript_barcodes()
    output, task = _type_unit(
        facts, OPTIONS, "DataMatrixOptions selects the shape of a DataMatrix symbol: square, rectangle or any."
    )
    errors = _stray(unit_checks(output, task, facts, NAME, register=False), OPTIONS)
    assert errors == []
    unit = next(u for u in output["units"] if u["slot"] == f"type:{OPTIONS}")
    assert "a Data Matrix symbol" in unit["text"]
    assert "DataMatrixOptions selects" in unit["text"]


def test_negative_control_a_name_the_facts_never_spell_as_words_stays_refused_with_the_hint() -> None:
    facts = _typescript_barcodes()
    assert word_form("DataMatrix") == "Data Matrix"
    assert word_form("QRCode") == "QR Code"
    assert word_form("Data") is None and word_form("Foo.Bar") is None
    assert restore_word_forms("A DataMatrixWriter.", ["DataMatrixWriter"], facts) == "A DataMatrixWriter."
    output, task = _type_unit(facts, OPTIONS, "DataMatrixOptions configures DataMatrixOpt shapes.")
    (error,) = _stray(unit_checks(output, task, facts, NAME, register=False), OPTIONS)
    assert "DataMatrixOpt (nearest accepted: DataMatrixOptions" in error
    assert "write it in full exactly as listed" in error


# BL-096 ------------------------------------------------------------------------------------

#: inherited_unit:087.paragraph of Aspose-PDF-FOSS-for-Go at 2eed1113 (README.md), as extracted.
GO_PARAGRAPH = (
    "Standalone runnable example programs live in `_examples/<name>/main.go` (excluded from\n"
    "`go build ./...`/`go test ./...` by their leading underscore); run one directly with\n"
    "`go run ./_examples/<name>`. Short, focused API examples live as `ExampleXxx` functions in\n"
    "`examples_test.go`, validated by `go test`."
)


def _go_facts() -> FactsDocument:
    return _facts(
        Fact(
            "inherited_unit:087.paragraph",
            "inherited_unit",
            GO_PARAGRAPH,
            (Evidence("README.md", "lines 1095-1099; paragraph"),),
        )
    )


def test_a_recorded_placeholder_path_is_not_html() -> None:
    placeholders = recorded_placeholders(_go_facts())
    assert {"_examples/<name>/main.go", "./_examples/<name>"} <= placeholders
    text = (
        "Runnable example programs live in _examples/<name>/main.go; run one with "
        "go run ./_examples/<name>."
    )
    assert not _bare_angle_bracket(text, placeholders)
    assert _bare_angle_bracket(text)  # negative control: without the facts it is refused


def test_negative_control_real_html_and_unrecorded_placeholders_stay_refused() -> None:
    placeholders = recorded_placeholders(_go_facts())
    for text in (
        "Use <b>bold</b> output.",
        "Examples live in _examples/<name>/main.go<br>and more.",
        "Name the program <name> when you run it.",
        "Examples live in docs/<div>/main.go.",
        "Open <a href='x'>the page</a>.",
    ):
        assert _bare_angle_bracket(text, placeholders), text
    html_facts = _facts(
        Fact("inherited_unit:001.paragraph", "inherited_unit", "Wrap it in `<code>`.", (Evidence("README.md"),))
    )
    assert recorded_placeholders(html_facts) == frozenset()


def test_the_renderer_prints_a_placeholder_in_a_code_span() -> None:
    import repo_presenter.extractors.platforms.go  # noqa: F401  (registers the "go" ecosystem)
    from repo_presenter.core.registry.models import ProviderIdentity, RegistryEntry
    from repo_presenter.readme.composition.renderer import render_readme

    entry = RegistryEntry(
        repository="aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
        family="pdf",
        platform="go",
        ecosystem="go",
        mode="full",
        policy_profile="default",
        active=True,
        provider_identity=ProviderIdentity(repository_id=1, node_id="MDEwOlJlcG9zaXRvcnkx"),
    )
    facts = FactsDocument(
        entry.repository,
        "f" * 40,
        (
            Fact("identity:repository", "identity", entry.repository, (Evidence("data/registry.json"),)),
            Fact("identity:ecosystem", "identity", "go", (Evidence("data/registry.json"),)),
            Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
            Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
            *_go_facts().facts[-1:],
        ),
    )
    text = "Programs live in _examples/<name>/main.go; run one with go run ./_examples/<name>."
    units = {
        "units": [
            {"section": "development_testing", "slot": "summary", "text": text, "fact_ids": []}
        ],
        "omitted": [],
    }
    plan = {"sections": [{"section_id": "development_testing", "include": True}]}
    readme = render_readme(entry, facts, plan, units, {"dispositions": []})
    assert "`_examples/<name>/main.go`" in readme
    assert "`./_examples/<name>`" in readme
    bare = readme.replace("`_examples/<name>/main.go`", "").replace("`./_examples/<name>`", "")
    assert "<name>" not in bare
