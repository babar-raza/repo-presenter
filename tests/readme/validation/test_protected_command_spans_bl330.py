"""BL-330: BC-08 reads a kept unit's commands as a reader of the README does (R46: universal, robust).

The finding texts are the hosted ones (run 44588774041 Page Python, 44588918976 PDF Python,
main 9476c1b): ``VERIFIED_PRESERVE keeps the command 'make\\nbuild'`` (an inline span wrapped across
two source lines, printed on one line) and ``VERIFIED_REWRITE keeps the command 'python\\n  with
Document(...'`` (a fenced block inside a list item read as one inline span).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation import units as units_module
from repo_presenter.readme.validation.text import inline_spans
from repo_presenter.readme.validation.units import protected_failures

_REPO = "aspose-page-foss/Aspose.Page-FOSS-for-Python"
WRAPPED = "Build the docs with `make\nbuild` before you push."
FENCED_LIST = (
    "- Extract the structure:\n\n"
    "  ```python\n"
    "  with Document(\"report.pdf\") as document:\n"
    "      for block in document.extract_blocks(pages=[1]):\n"
    "          print(block.page_index, block.kind, block.text, block.rows)\n"
    "      document.export_blocks_json(\"report-structure.json\")\n"
    "  ```\n"
    "- Use `pip install aspose-pdf` first.\n"
)


def _candidate(unit_id: str, text: str, disposition: str, readme: str) -> SimpleNamespace:
    facts = FactsDocument(
        _REPO,
        "0" * 40,
        (
            Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
            Fact(unit_id, "inherited_unit", text, (Evidence("README.md", None),)),
        ),
    )
    return SimpleNamespace(
        facts=facts,
        readme=readme,
        dispositions={
            "dispositions": [
                {"unit_id": unit_id, "disposition": disposition, "destination_section": "development_testing"}
            ]
        },
    )


@pytest.fixture(autouse=True)
def _no_placements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(units_module, "placements_of", lambda candidate: [])


def test_a_span_wrapped_across_lines_reads_with_a_space() -> None:
    assert inline_spans(WRAPPED) == ["make build"]


def test_a_fenced_block_in_a_list_is_not_an_inline_span() -> None:
    assert inline_spans(FENCED_LIST) == ["pip install aspose-pdf"]


@pytest.mark.parametrize("printed", ["Build the docs with `make build` before you push.", WRAPPED])
def test_wrapped_span_printed_on_one_line_or_two_passes(printed: str) -> None:
    candidate = _candidate("inherited_unit:092.paragraph", WRAPPED, "VERIFIED_PRESERVE", printed)
    assert protected_failures(candidate) == []


def test_wrapped_span_not_printed_still_fails_with_the_hosted_wording() -> None:
    candidate = _candidate("inherited_unit:092.paragraph", WRAPPED, "VERIFIED_PRESERVE", "Nothing here.")
    [failure] = protected_failures(candidate)
    assert failure.detail == (
        "inherited_unit:092.paragraph: VERIFIED_PRESERVE keeps the command 'make build' "
        "but the candidate does not render it"
    )


def test_fenced_python_in_a_rewritten_list_is_not_a_command_but_a_real_command_still_is() -> None:
    candidate = _candidate("inherited_unit:280.list", FENCED_LIST, "VERIFIED_REWRITE", "Use pip.")
    [failure] = protected_failures(candidate)
    assert "'pip install aspose-pdf'" in failure.detail and "with Document" not in failure.detail
    printed = _candidate(
        "inherited_unit:280.list", FENCED_LIST, "VERIFIED_REWRITE", "Run `pip install aspose-pdf`."
    )
    assert protected_failures(printed) == []
