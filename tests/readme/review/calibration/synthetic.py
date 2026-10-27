"""One small synthetic candidate, rich enough for every mutation operator, built without a render."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.calibration.corpus import Base, Repair
from repo_presenter.readme.review.calibration.sources import SourceCandidate
from tests.readme.composition.synthetic import make_entry

README = """# Aspose.Widget FOSS for Python

Aspose.Widget FOSS for Python renders widgets to PNG and SVG through the `Widget` class and the `SvgExporter` class.

## Key Capabilities

- **Render to PNG.** It renders a `Widget` to `.png` with `Widget.render`.
- **Export SVG.** It exports vector output to `.svg` through `SvgExporter`.

## Installation

Install the published package from PyPI (`aspose-widget-foss`, version 26.9.0):

```bash
pip install aspose-widget-foss
```

## Quick Start

```python
from aspose.widget import Widget
Widget().render("out.png")
```

## Additional Examples

Render the same widget to a stream and read the bytes back, which shows the whole path from construction to output in two lines.

## Scope and Limitations

- Rendering to `.pdf` is not implemented in this build.

## License

MIT.
"""

ORIGINAL = """# Aspose.Widget FOSS for Python

Renders widgets to PNG and SVG.

## Installation

pip install aspose-widget-foss
"""

REVISION = "b" * 40


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md"),))


FACTS = FactsDocument(
    "org/Aspose.Widget-FOSS-for-Python",
    REVISION,
    (
        _fact("package:name", "package", "aspose-widget-foss"),
        _fact("package:version", "package", "26.9.0"),
        _fact(
            "install_command:pip", "install_command", "pip install aspose-widget-foss"
        ),
        _fact("format:png", "format", ".png"),
        _fact("format:svg", "format", ".svg"),
        _fact("public_symbol:widget", "public_symbol", "Widget"),
        _fact("public_symbol:svgexporter", "public_symbol", "SvgExporter"),
        _fact("public_symbol:widget.render", "public_symbol", "Widget.render"),
        _fact("capability:png", "capability", "Renders widgets to PNG"),
    ),
)

PLAN = {
    "sections": [
        {"section_id": name, "include": True}
        for name in (
            "opening",
            "key_capabilities",
            "installation",
            "quick_start",
            "additional_examples",
            "scope_limitations",
            "license",
        )
    ]
}


def make_source(
    tmp_path: Path,
    *,
    readme: str = README,
    facts: FactsDocument = FACTS,
    name: str = "widget",
) -> SourceCandidate:
    return SourceCandidate(
        name=name,
        entry=make_entry(),
        repository="org/Aspose.Widget-FOSS-for-Python",
        ecosystem="python",
        readme=readme,
        original=ORIGINAL,
        facts=facts,
        plan=PLAN,
        units={"units": []},
        dispositions={"dispositions": []},
        validation={"summary": {}, "checks": []},
        tree_paths=(),
        tasks=(),
        scratch=tmp_path,
    )


def make_base(tmp_path: Path, repairs: tuple[Repair, ...] = ()) -> Base:
    return Base(make_source(tmp_path), repairs)
