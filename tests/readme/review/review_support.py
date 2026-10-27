"""Shared fixtures for the LLM-reviewer core tests: one small candidate, its facts, and builders
for findings and replies. Everything is offline and deterministic."""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.clearances import ClearanceContext
from repo_presenter.readme.review.findings import Finding, OmissionClaim

CANDIDATE = """# Aspose.Widget FOSS for Python

Aspose.Widget FOSS renders widgets to PNG and SVG.

## Installation

```bash
pip install aspose-widget-foss
```

## Key Capabilities

- Renders a Widget to PNG with Widget.render.
- Exports SVG through the SvgExporter class.

## Quick Start

```python
from aspose.widget import Widget
Widget().render("out.png")
```

## API Reference

| Type | Summary |
|---|---|
| Widget | The main class. |
| SvgExporter | Writes SVG. |

## License

MIT.
"""

ORIGINAL = """# Aspose.Widget

Widgets, rendered. Supports a plugin loader named PluginHost and a legacy CLI called widgetctl.

## Install

pip install aspose-widget-foss
"""

REVISION = "a" * 40


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md"),), polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/widget",
    REVISION,
    (
        _fact("package:name", "package", "aspose-widget-foss"),
        _fact("package:version", "package", "26.9.0"),
        _fact("public_symbol:widget", "public_symbol", "Widget"),
        _fact("public_symbol:svgexporter", "public_symbol", "SvgExporter"),
        _fact(
            "public_symbol:legacyexport",
            "public_symbol",
            "LegacyExport",
            "CONTRADICTED",
        ),
        _fact(
            "example:001",
            "example",
            'from aspose.widget import Widget\nWidget().render("out.png")',
        ),
        _fact("example:002", "example", "Widget().render_pdf()", "CONTRADICTED"),
        _fact("format:png", "format", "PNG"),
        _fact("capability:svg", "capability", "SVG export"),
        _fact("inherited_unit:001.paragraph", "inherited_unit", "Widgets, rendered."),
    ),
)

SECTIONS = {
    "opening",
    "key_capabilities",
    "quick_start",
    "api_reference",
    "installation",
    "license",
}


def context(candidate: str = CANDIDATE, original: str = ORIGINAL) -> ClearanceContext:
    return ClearanceContext(candidate, original, FACTS)


def llm(claim_kind: str = "quality", **overrides: Any) -> Finding:
    """A BLOCKING LLM finding with sensible defaults; override any field."""
    fields: dict[str, Any] = {
        "rule": "llm:completeness",
        "source": "llm",
        "message": "a reviewer claim",
        "claim_kind": claim_kind,
        "finding_id": "F01",
        "section_id": "key_capabilities",
        "causal_stage": "S6",
        "criterion": "completeness",
        "repair": "fix it",
    }
    fields.update(overrides)
    if isinstance(fields.get("omission"), tuple):
        fields["omission"] = OmissionClaim(*fields["omission"])
    return Finding(**fields)


def rule_finding(rule: str = "claim_contradiction") -> Finding:
    return Finding(rule=rule, source="deterministic", message="m", evidence="proof")


def raw_finding(claim_kind: str = "quality", **overrides: Any) -> dict[str, Any]:
    """One finding as the reviewer's JSON reply carries it, valid against CANDIDATE and FACTS."""
    base: dict[str, Any] = {
        "id": "F01",
        "section_id": "key_capabilities",
        "causal_stage": "S6",
        "criterion": "completeness",
        "claim_kind": claim_kind,
        "text": "a reviewer claim",
        "quote": "Exports SVG through the SvgExporter class.",
        "fact_ids": ["capability:svg"],
        "absent": [],
        "unsupported_names": [],
        "omission": None,
        "repair": "fix it",
    }
    base.update(overrides)
    return base


def raw_reply(
    verdict: str = "ACCEPT", findings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {"verdict": verdict, "findings": findings or [], "preserve": []}
