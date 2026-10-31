"""A kept unit's link is carried only if the document holds it as a link (coverage.carries_hard_tokens).

Real hosted defect (aspose-3d-foss/Aspose.3D-FOSS-for-Java, review REJECT on `live_readme_loss`, link
`AGENTS.md`): inherited_unit:077.paragraph is VERIFIED_PRESERVE, but placement printed only its
"see [TODO.md]" half. `_carries_all` tested `token in document`, and the bare word "AGENTS.md" in
authored prose elsewhere counted as carrying the link `[AGENTS.md](AGENTS.md)`, so the sentence was
trimmed as already stated and the link was lost.
"""

from __future__ import annotations

from repo_presenter.readme.composition.coverage import (
    Destinations,
    carries_hard_tokens,
    uncovered,
)

UNIT = "Contributor rules are in [AGENTS.md](AGENTS.md); open tasks are in [TODO.md](TODO.md)."


def test_a_relative_link_target_written_as_a_bare_word_is_not_carried() -> None:
    document = "The AGENTS.md file lists the rules. Open tasks: [TODO.md](TODO.md)."
    assert not carries_hard_tokens(UNIT, document)


def test_a_relative_link_is_carried_as_a_markdown_link_or_an_html_href() -> None:
    assert carries_hard_tokens(UNIT, "See [AGENTS.md](AGENTS.md) and [TODO.md](TODO.md).")
    assert carries_hard_tokens(UNIT, '<a href="AGENTS.md">a</a> [t](<TODO.md>)')


def test_an_absolute_url_is_still_carried_when_printed_bare() -> None:
    unit = "Docs: [guide](https://example.org/guide)."
    assert carries_hard_tokens(unit, "Read https://example.org/guide for more.")
    assert not carries_hard_tokens(unit, "Read the guide for more.")


def test_a_command_is_carried_by_substring_and_no_tokens_means_carried() -> None:
    assert carries_hard_tokens("Run `pip install widget`.", "First `pip install widget`, then go.")
    assert not carries_hard_tokens("Run `pip install widget`.", "No command here.")
    assert carries_hard_tokens("Plain prose with no commands or links.", "")


def test_placement_no_longer_trims_a_sentence_whose_link_the_document_only_names() -> None:
    """The reproduced defect: the destination states the words, the document holds the TODO link as a
    link and AGENTS.md only as a word. The unit must not be reported fully covered."""
    destination_text = "Contributor rules are in AGENTS.md; open tasks are in TODO.md."
    shown = Destinations.of(
        {"contributing": destination_text, "other": "Open tasks: [TODO.md](TODO.md)."}
    )
    remainder = uncovered("inherited_unit:077.paragraph", UNIT, shown, "contributing")
    assert "[AGENTS.md](AGENTS.md)" in remainder


def test_placement_still_trims_a_sentence_whose_links_are_all_carried() -> None:
    destination_text = (
        "Contributor rules are in [AGENTS.md](AGENTS.md); open tasks are in [TODO.md](TODO.md)."
    )
    shown = Destinations.of({"contributing": destination_text})
    assert uncovered("inherited_unit:077.paragraph", UNIT, shown, "contributing") == ""
