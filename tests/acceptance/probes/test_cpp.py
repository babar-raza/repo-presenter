"""TC-017a: the independent C++ export-surface probe, exercised against a real fixture tree.

Three required shapes (see the card), plus the C++-specific shape it names explicitly: a
declaration under an ``internal/`` path segment is reported ``exported=False`` by this
independent reader, matching -- but never calling into -- ``api_surface.py``'s own
``_CPP_ONLY_VENDOR_SEGMENTS`` filter.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import cpp as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "cpp"
_NO_HEADERS = Path(__file__).parent / "fixtures" / "cpp_none"


def test_public_header_class_exists_and_is_exported() -> None:
    assert probe.exists(_FIXTURES, "aspose::pdf::Document") is True
    assert probe.exported(_FIXTURES, "Document") is True


def test_internal_path_segment_class_exists_but_is_not_exported() -> None:
    # Helper is declared under include/aspose/pdf/internal/ -- exists, but not public, by this
    # probe's own independent re-derivation of the path-segment rule (never reads the engine's
    # own visibility="internal" tag).
    assert probe.exists(_FIXTURES, "Helper") is True
    assert probe.exported(_FIXTURES, "Helper") is False


def test_everything_is_unknown_when_no_header_is_found() -> None:
    assert probe.exists(_NO_HEADERS, "Anything") is None
    assert probe.exported(_NO_HEADERS, "Anything") is None
    assert probe.count(_NO_HEADERS, "class") is None


def test_count_of_public_classes() -> None:
    # Document is public; Helper sits under internal/ and does not count.
    assert probe.count(_FIXTURES, "class") == 1


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "function") is None
