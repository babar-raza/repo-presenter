"""Format/capability OVER-claiming: a table row marks a format supported with nothing (or a
CONTRADICTED fact) confirming it -- the direction ``report_gaps`` does not cover (see
``migration/reuse-manifest.yaml``'s readme_correction/ entry, "known_gap"). Positive case, a
CONTRADICTED-fact case, and two negative controls (correctly-caveated and correctly-supported)."""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.format_overclaim import format_overclaim

TABLE_README = (
    "# P\n\n## Supported Formats\n\n"
    "| Format | Read |\n"
    "|---|---|\n"
    "| STL | ✅ |\n"
    "| OBJ | ✅ |\n"
    "| AMF | ❌ |\n"
)


def test_a_format_marked_supported_with_no_backing_fact_is_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(make_fact("format:stl", ".stl", evidence=(("io.py", None),)))
    result = format_overclaim(make_context(TABLE_README, facts))
    assert result.edits == ()  # this detector never edits
    (finding,) = result.findings
    assert finding.line == 8 and "'OBJ'" in finding.reason
    assert "no SUPPORTED format or capability fact confirms it" in finding.reason


def test_a_format_marked_supported_but_on_record_as_contradicted_cites_the_fact(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:stl", ".stl", evidence=(("io.py", None),)),
        make_fact(
            "format:obj",
            ".obj",
            polarity="CONTRADICTED",
            evidence=(("io.py", "IOService.cs rejects .obj: no writer registered"),),
        ),
    )
    result = format_overclaim(make_context(TABLE_README, facts))
    (finding,) = result.findings
    assert finding.line == 8 and finding.fact_ids == ("format:obj",)
    assert "CONTRADICTED" in finding.reason


def test_a_format_backed_by_a_supported_fact_is_not_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "# P\n\n| Format | Read |\n|---|---|\n| STL | ✅ |\n"
    facts = make_facts(make_fact("format:stl", ".stl", evidence=(("io.py", None),)))
    assert format_overclaim(make_context(readme, facts)).findings == ()


def test_a_correctly_caveated_row_marked_unsupported_is_not_flagged(
    make_context: Any, make_facts: Any
) -> None:
    """The ❌ cell in ``TABLE_README``'s AMF row is a correctly-undocumented claim: no claim of
    support is made at all, so nothing is flagged for it."""
    facts = make_facts()  # no format:amf fact of any polarity
    result = format_overclaim(make_context(TABLE_README, facts))
    assert all("AMF" not in finding.text for finding in result.findings)
