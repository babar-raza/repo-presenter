"""What a review unit may show a reviewer: only text an author wrote.

The renderer prints the identity, badges, banner, navigation, At a Glance diagram, installation,
dependencies, third-party notices and license from facts, and in the mixed sections it prints the
headings, tables, fenced examples, ``<details>`` wrappers, "Not verified" notes and the member
reference. Iteration 2 found 130 of 159 unsupported-claim findings aimed at such text. The reviewer
is no longer shown it at all, so it cannot be cited: that is by construction, not by instruction.
"""

from __future__ import annotations

from repo_presenter.readme.review.scope import (
    reviewable_lines,
    section_of_line,
)

README = """# Aspose.Widget FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-widget-foss.svg)](https://pypi.org/project/aspose-widget-foss/) ![Python](https://img.shields.io/badge/python-3.10-blue.svg)

[![Aspose.Widget](https://products.aspose.org/media/widget/banner.png)](https://products.aspose.org/widget/)

Aspose.Widget FOSS renders widgets to PNG and SVG.
It is written in pure Python.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)

## At a Glance

```mermaid
flowchart LR
Start["A widget"] --> Product["Aspose.Widget"]
```

## Key Capabilities

- **Render to PNG.** It renders a `Widget` to `.png`.
- **Export SVG.** It exports vector output through `SvgExporter`.

## Installation

Install the published package from PyPI (`aspose-widget-foss`, version 26.9.0):

```bash
pip install aspose-widget-foss
```

## Quick Start

Render a widget to a file and read it back.

```python
from aspose.widget import Widget
Widget().render("out.png")
```

> **Not verified:** this example is carried over unchanged from the project's existing README. It could not be compiled or run here.

## Additional Examples

Further examples follow.

<details>
<summary>View Additional Examples</summary>

### Save to a stream

Render the widget into memory.

```python
Widget().render_to_stream(stream)
```

</details>

## API Reference

`Widget` is the main entry point and owns the render pipeline.

The verified public surface has 2 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Type | Summary |
|---|---|
| Widget | The main class. |

#### Detailed Member Reference

### Widget

The `Widget` class renders content.

- `Render`: Renders the widget.
- `Name`: Gets the name.

</details>

## Scope and Limitations

- Rendering to `.pdf` is not implemented in this build.

## License

This project is licensed under the MIT License.
"""
LINES = README.splitlines()


def shown() -> list[str]:
    return [LINES[n - 1] for n in reviewable_lines(README)]


def line_of(text: str) -> int:
    (found,) = [i for i, row in enumerate(LINES, 1) if text in row]
    return found


def test_authored_prose_is_reviewable() -> None:
    kept = shown()
    for text in (
        "Aspose.Widget FOSS renders widgets to PNG and SVG.",
        "It is written in pure Python.",
        "- **Render to PNG.** It renders a `Widget` to `.png`.",
        "Render a widget to a file and read it back.",
        "Further examples follow.",
        "Render the widget into memory.",
        "`Widget` is the main entry point and owns the render pipeline.",
        "The `Widget` class renders content.",
        "- Rendering to `.pdf` is not implemented in this build.",
    ):
        assert text in kept, text


def test_no_renderer_printed_line_is_ever_shown() -> None:
    kept = " | ".join(shown())
    for text in (
        "# Aspose.Widget FOSS for Python",
        "img.shields.io",
        "banner.png",
        "## Navigation",
        "[At a Glance](#at-a-glance)",
        "mermaid",
        "flowchart LR",
        "Install the published package from PyPI",
        "pip install aspose-widget-foss",
        "from aspose.widget import Widget",
        "Not verified",
        "<details>",
        "<summary>",
        "</details>",
        "### Core API",
        "| Type | Summary |",
        "| Widget | The main class. |",
        "#### Detailed Member Reference",
        "### Widget",
        "### Save to a stream",
        "- `Render`: Renders the widget.",
        "- `Name`: Gets the name.",
        "The verified public surface has 2 types.",
        "This project is licensed under the MIT License.",
        "## ",
    ):
        assert text not in kept, text


def test_the_numbers_are_the_candidates_own_line_numbers() -> None:
    for number in reviewable_lines(README):
        assert LINES[number - 1].strip()
    assert list(reviewable_lines(README)) == sorted(set(reviewable_lines(README)))
    n = line_of("It is written in pure Python.")
    assert n in reviewable_lines(README)


def test_each_reviewable_line_belongs_to_a_named_section() -> None:
    assert (
        section_of_line(README, line_of("renders widgets to PNG and SVG")) == "opening"
    )
    assert (
        section_of_line(README, line_of("It renders a `Widget` to `.png`"))
        == "key_capabilities"
    )
    assert section_of_line(README, line_of("read it back")) == "quick_start"
    assert (
        section_of_line(README, line_of("Render the widget into memory"))
        == "additional_examples"
    )
    assert (
        section_of_line(README, line_of("owns the render pipeline")) == "api_reference"
    )
    assert (
        section_of_line(README, line_of("is not implemented in this build"))
        == "scope_limitations"
    )


def test_a_heading_the_shell_does_not_name_is_a_structure_section_and_its_prose_is_reviewable() -> (
    None
):
    text = README + "\n## Roadmap\n\nWe plan to add PDF output.\n"
    n = text.splitlines().index("We plan to add PDF output.") + 1
    assert n in reviewable_lines(text)
    assert section_of_line(text, n) == "structure"


def test_a_candidate_with_only_renderer_text_has_nothing_to_review() -> None:
    only = (
        "# T\n\n## Installation\n\n```bash\npip install x\n```\n\n## License\n\nMIT.\n"
    )
    assert reviewable_lines(only) == ()


def test_tilde_fences_and_unclosed_fences_hide_their_contents() -> None:
    text = "# T\n\nIntro prose.\n\n## Key Capabilities\n\n~~~\nnot prose\n~~~\n\nAfter.\n\n```\nunclosed code\n"
    kept = [text.splitlines()[n - 1] for n in reviewable_lines(text)]
    assert kept == ["Intro prose.", "After."]


# --- sentences the renderer appends to a line an author wrote ---------------------------------------

API_SENTENCE = (
    "It covers all 293 verified public types; the [API Reference](#api-reference) section above "
    "covers the essentials."
)
ENTERPRISE = (
    "These limitations don't apply to [full-featured Aspose.3D for .NET - Enterprise Edition]"
    "(https://products.aspose.com/3d/net/)."
)


def test_a_sentence_the_renderer_appends_to_an_authored_line_is_not_shown() -> None:
    from repo_presenter.readme.review.scope import shown_text

    line = (
        "- **[Full API reference](https://reference.aspose.org/3d/net/)** - The full API reference "
        f"offers complete, generated documentation for every public type. {API_SENTENCE}"
    )
    assert shown_text(line) == (
        "- **[Full API reference](https://reference.aspose.org/3d/net/)** - The full API reference "
        "offers complete, generated documentation for every public type."
    )
    both = f"{ENTERPRISE} It adds the full commercial rendering pipeline."
    assert shown_text(both) == "It adds the full commercial rendering pipeline."


def test_a_line_that_is_only_renderer_sentences_is_not_reviewable() -> None:
    text = (
        "# T\n\nIntro prose.\n\n## Documentation & Resources\n\n"
        "- Found a bug or have a feature request? [Open an issue](https://github.com/o/r/issues).\n\n"
        "## Development and Testing\n\n"
        "The suite covers 16 test files under `src/test/`.\n"
        "The [ci workflow](.github/workflows/ci.yml) runs on Ubuntu and Windows, with .NET 6.0 and 8.0.\n"
        "Releases run through the [release workflow](.github/workflows/release.yml).\n"
        "Authored words about building the library from source.\n"
    )
    kept = [text.splitlines()[n - 1] for n in reviewable_lines(text)]
    assert kept == [
        "Intro prose.",
        "Authored words about building the library from source.",
    ]


def test_the_patterns_cover_every_sentence_the_renderer_writes_into_an_authored_section() -> (
    None
):
    from repo_presenter.readme.composition.planning import plan_checks
    from repo_presenter.readme.composition.renderer import renderer_sentences
    from repo_presenter.readme.review.scope import shown_text
    from tests.readme.composition.synthetic import make_entry, make_facts
    from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

    plan = _plan()
    dispositions = _dispositions()
    plan_checks(plan, make_facts(), dispositions=dispositions, ecosystem="python")
    sentences = renderer_sentences(
        make_entry(), make_facts(), plan, _units(), dispositions
    )
    assert sentences, "the fixture renders at least one renderer sentence"
    for sentence in sentences:
        assert shown_text(sentence) == "", sentence


# --- a candidate the renderer did not print (Lane L's corrected live README) ------------------------

LIVE = """# Widget

Widget renders widgets.

## Installation

Run pip install widget to get the library. It supports every Python 3 release.

```bash
pip install widget
```

## License

Widget is licensed under the MIT License, which permits commercial use.

## Notes

Found a bug or have a feature request? [Open an issue](https://github.com/o/r/issues).
"""


def test_a_corrected_live_readme_has_no_renderer_owned_section() -> None:
    live = LIVE.splitlines()
    shell = [live[n - 1] for n in reviewable_lines(LIVE)]
    assert (
        "Run pip install widget to get the library. It supports every Python 3 release."
        not in shell
    )
    maintainers = [live[n - 1] for n in reviewable_lines(LIVE, rendered=False)]
    assert (
        "Run pip install widget to get the library. It supports every Python 3 release."
        in maintainers
    )
    assert (
        "Widget is licensed under the MIT License, which permits commercial use."
        in maintainers
    )
    # the maintainers' own sentence is theirs even when it reads like one the renderer prints
    assert any("Found a bug" in row for row in maintainers)
    # markup is markup whoever wrote it
    assert not any(row.startswith(("#", "```", "pip install")) for row in maintainers)


def test_sections_are_still_named_for_a_live_readme() -> None:
    text = LIVE.splitlines()
    n = (
        text.index(
            "Widget is licensed under the MIT License, which permits commercial use."
        )
        + 1
    )
    assert section_of_line(LIVE, n, rendered=False) == "license"
