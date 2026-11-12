"""An HTML element named in an inline code span is inert (HTML Python's DOM-interface table).

Measured on Aspose.HTML-FOSS-for-Python: its maintainers' reference table has rows such as
``| `HTMLBaseElement` | HTML <base> element. |`` and ``| `HTMLDetailsElement` | HTML `<details>`
disclosure widget element. |``. The raw ``<base>``/``<meta>``/``<script>`` words made zero-call restore
refuse the table (BC-06), and the backticked ``<details>`` was counted as an opened collapsed block
(BC-07), so the lost table stayed lost (BC-05/BC-17)."""

from __future__ import annotations

from repo_presenter.readme.validation.links import defang_unsafe_html, unsafe_html_failures
from repo_presenter.readme.validation.structure import _collapsed_section_failures

TABLE = (
    "| Class | Description |\n"
    "|---|---|\n"
    "| `HTMLBaseElement` | HTML <base> element. |\n"
    "| `HTMLScriptElement` | HTML <script> element. |\n"
    "| `HTMLMetaElement` | HTML `<meta>` element. |\n"
)


def test_a_raw_unsafe_tag_in_prose_is_wrapped_in_a_code_span_and_nothing_else_changes() -> None:
    kept = defang_unsafe_html(TABLE)
    assert "HTML `<base>` element." in kept
    assert "HTML `<script>` element." in kept
    assert "HTML `<meta>` element." in kept  # already a code span: untouched, not double-wrapped
    assert kept.replace("`", "") == TABLE.replace("`", "")
    assert defang_unsafe_html(kept) == kept


def test_the_kept_form_passes_bc06_but_the_raw_form_does_not() -> None:
    assert unsafe_html_failures(TABLE)
    assert unsafe_html_failures(defang_unsafe_html(TABLE)) == []


def test_a_real_tag_outside_a_code_span_still_fails_bc06() -> None:
    assert unsafe_html_failures("text `<meta>` and <script>alert(1)</script>\n")


def test_a_fenced_example_is_left_exactly_as_written() -> None:
    fenced = "```html\n<script>alert(1)</script>\n```\n"
    assert defang_unsafe_html(fenced) == fenced


def test_a_details_tag_in_a_code_span_does_not_open_a_collapsed_block() -> None:
    readme = (
        "<details>\n<summary>API</summary>\n\n"
        "| `HTMLDetailsElement` | HTML `<details>` disclosure widget element. |\n\n"
        "</details>\n\n## Documentation & Resources\n\ntext\n"
    )
    assert _collapsed_section_failures(readme) == []


def test_an_unclosed_real_details_block_still_swallows_a_visible_section() -> None:
    readme = "<details>\n<summary>API</summary>\n\n## Documentation & Resources\n\ntext\n"
    assert _collapsed_section_failures(readme)
