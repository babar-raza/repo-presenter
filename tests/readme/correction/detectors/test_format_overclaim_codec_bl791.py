"""BL-791 (hosted Lane L TeX Python and Email Python, runs 44993635165 and 44993661753).

The real shapes, from the pinned sources (aspose-tex-foss/Aspose.TeX-FOSS-for-Python @ 07db320 and
aspose-email-foss/Aspose.Email-FOSS-for-Python @ 10a906b): the README names SVG as an output and CFB
as a container the library reads and writes. Neither has a file-extension ``format`` fact (the
executed examples name ``.dvi``/``.pdf`` and ``.msg``/``.eml``), so ``format_overclaim`` flagged both
as unrepaired defects and the whole Lane L candidate was refused. The public surface states them:
``aspose_tex.OutputFormat.SVG`` and ``aspose_tex.SvgDevice``; ``email_foss.cfb.CFBReader`` and
``CFBWriter``. A declaration of that kind backs the claim; anything the facts do not declare, and
anything a CONTRADICTED fact refutes, is still a defect.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.format_overclaim import format_overclaim

TEX = (
    "# aspose-tex\n\n```mermaid\nflowchart TD\n  subgraph Outputs[\"Outputs\"]\n"
    '    o1["PDF document (file path or in-memory bytes)"]\n'
    '    o3["SVG document (file path or in-memory bytes, multi-page)"]\n'
    "  end\n```\n"
)
EMAIL = (
    "# email\n\n```mermaid\nflowchart TD\n  subgraph StartingPoints[\"Starting Points\"]\n"
    '    i1["An existing CFB container (file or bytes)"]\n'
    '    i2["An existing .msg file (file or bytes)"]\n'
    "  end\n```\n"
)


def _enum(make_fact: Any, enum: str, name: str) -> Any:
    return make_fact(
        f"enum_member:{enum.lower()}.{name.lower()}",
        f"{enum}.{name}",
        attributes={"enum": enum, "literal": f"'{name.lower()}'", "member_kind": "enum"},
    )


def _symbol(make_fact: Any, value: str, kind: str = "class") -> Any:
    return make_fact(f"public_symbol:{value.lower()}", value, attributes={"symbol_kind": kind})


def test_a_format_enum_member_backs_the_claim(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    facts = make_facts(
        make_fact("format:output.pdf", ".pdf", evidence=(("README.md", None),)),
        _enum(make_fact, "aspose_tex.OutputFormat", "SVG"),
    )
    assert format_overclaim(make_context(TEX, facts)).findings == ()


def test_a_public_codec_class_backs_the_claim(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    facts = make_facts(
        make_fact("format:output.pdf", ".pdf", evidence=(("README.md", None),)),
        _symbol(make_fact, "aspose_tex.SvgDevice"),
    )
    assert format_overclaim(make_context(TEX, facts)).findings == ()
    facts = make_facts(
        make_fact("format:input.msg", ".msg", evidence=(("README.md", None),)),
        _symbol(make_fact, "email_foss.cfb.CFBReader"),
        _symbol(make_fact, "email_foss.cfb.CFBWriter"),
    )
    assert format_overclaim(make_context(EMAIL, facts)).findings == ()


def test_the_same_claims_with_no_declaration_stay_defects(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(make_fact("format:output.pdf", ".pdf", evidence=(("README.md", None),)))
    (finding,) = format_overclaim(make_context(TEX, facts)).findings
    assert "'SVG'" in finding.reason and finding.report_only_reason == ""
    facts = make_facts(make_fact("format:input.msg", ".msg", evidence=(("README.md", None),)))
    (finding,) = format_overclaim(make_context(EMAIL, facts)).findings
    assert "'CFB'" in finding.reason


def test_a_name_that_merely_starts_with_the_token_or_a_non_format_enum_does_not_back_it(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:output.pdf", ".pdf", evidence=(("README.md", None),)),
        _symbol(make_fact, "aspose_tex.SvgFontCache"),  # not a codec suffix
        _symbol(make_fact, "aspose_tex.SvgDeviceFactoryMethods"),
        _enum(make_fact, "aspose_tex.Colors", "SVG"),  # not a format enum
        _symbol(make_fact, "aspose_tex.SvgDevice", kind="function"),  # not a type
    )
    assert len(format_overclaim(make_context(TEX, facts)).findings) == 1


def test_a_declaration_never_overrides_a_contradicting_fact(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:output.pdf", ".pdf", evidence=(("README.md", None),)),
        make_fact(
            "format:output.svg", ".svg", polarity="CONTRADICTED",
            evidence=(("svg.py", "the SVG writer raises NotImplementedError"),),
        ),
        _symbol(make_fact, "aspose_tex.SvgDevice"),
    )
    (finding,) = format_overclaim(make_context(TEX, facts)).findings
    assert finding.fact_ids == ("format:output.svg",) and "CONTRADICTED" in finding.reason
