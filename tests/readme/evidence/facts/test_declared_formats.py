"""Formats a directional format enum declares become UNRESOLVED format facts, never SUPPORTED
(owner decision 2026-11-05: declared is not working -- Aspose.3D for Java declares about 30 formats
and handles 4)."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.evidence.facts.formats import declared_format_facts


def member(enum: str, name: str) -> Fact:
    value = f"{enum}.{name}"
    return Fact(
        f"enum_member:{value.lower()}",
        "enum_member",
        value,
        (Evidence("src/SaveFormat.cs", "line 3; member of enum " + enum),),
        attributes={"enum": enum},
    )


def test_save_and_load_enum_members_declare_output_and_input_formats():
    facts = [
        member("W.SaveFormat", "Pdf"),
        member("W.SaveFormat", "Docx"),
        member("W.LoadFormat", "Doc"),
    ]
    declared = {f.id: f for f in declared_format_facts(facts)}
    assert set(declared) == {"format:output.pdf", "format:output.docx", "format:input.doc"}
    pdf = declared["format:output.pdf"]
    assert pdf.value == ".pdf" and pdf.polarity == "UNRESOLVED"
    assert pdf.attributes == {"source": "enum_declaration"}
    assert "declared is not verified" in pdf.evidence[0].detail


def test_a_declaration_never_touches_an_existing_format_fact():
    executed = Fact(
        "format:output.pdf", "format", ".pdf", (Evidence("README.md", "example 1"),)
    )
    out = declared_format_facts([executed, member("W.SaveFormat", "Pdf")])
    assert out == []


def test_neutral_enums_and_behaviour_members_declare_nothing():
    facts = [
        member("W.FileFormat", "Pdf"),  # no direction
        member("W.SaveFormat", "Auto"),
        member("W.LoadFormat", "Unknown"),
        member("W.SaveFormat", "NotAnExtensionAtAll"),
    ]
    assert declared_format_facts(facts) == []


def test_the_falsifier_a_declaration_made_supported_is_caught():
    # If the rule were "declared = SUPPORTED", this would fail.
    out = declared_format_facts([member("W.ExportFormat", "Svg")])
    assert [f.polarity for f in out] == ["UNRESOLVED"]
