"""BL-640: a decimal that quantifies something ("a new 2.8 MB blob per commit") is a measurement, not a version.

Real data: README.md of aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript at the pinned revision 5fa17750,
``inherited_unit:589.paragraph``; hosted run 44943457723 ended on 'BC-17 holds versions 2.8, which the published
README prints and this candidate loses' after every restore."""

from __future__ import annotations

from repo_presenter.readme.parity_gate import _versions

REAL = (
    "The PDF is not checked in — it is regenerated on every run with fresh `/Info`\n"
    "dates, so tracking it would add a new 2.8 MB blob per commit for a document\n"
    "nobody edited. Run the command above to produce it, along with four siblings.\n"
    "All five are gitignored:"
)


def test_the_real_paragraph_names_no_version() -> None:
    assert _versions(REAL) == set()


def test_sizes_durations_and_percentages_are_measurements() -> None:
    assert _versions("a 2.8 MB blob, 10.5MiB, 1.5 GB, 3.2 seconds, 0.5 ms, 1.5s, 99.9% of 12.5 px") == set()


def test_negative_control_real_versions_are_still_versions() -> None:
    assert _versions("needs Node 2.8 or newer") == {"2.8"}
    assert _versions("Version 2.8.1 ships; requires v3.10 and Go 1.21") == {"2.8.1", "3.10", "1.21"}
    assert _versions(REAL + " Needs 2.8.") == {"2.8"}  # a version in the same paragraph is still held
