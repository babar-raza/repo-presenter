"""TC-017a: the independent Go export-surface probe, exercised against a real fixture tree.

Three required shapes (see the card): a genuinely public symbol reports ``exists=True,
exported=True``; a genuinely private symbol reports ``exists=True, exported=False``; a symbol
the probe cannot determine reports ``None``, never a guessed ``True``/``False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import go as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "go"
_NO_SOURCE = Path(__file__).parent / "fixtures" / "go_none"


def test_exported_type_and_method_follow_gos_own_capitalization_rule() -> None:
    assert probe.exists(_FIXTURES, "Widget") is True
    assert probe.exported(_FIXTURES, "Widget") is True
    assert probe.exists(_FIXTURES, "Widget.Render") is True
    assert probe.exported(_FIXTURES, "Widget.Render") is True


def test_unexported_method_exists_but_is_not_exported() -> None:
    assert probe.exists(_FIXTURES, "Widget.hide") is True
    assert probe.exported(_FIXTURES, "Widget.hide") is False


def test_unexported_type_exists_but_is_not_exported() -> None:
    assert probe.exists(_FIXTURES, "helper") is True
    assert probe.exported(_FIXTURES, "helper") is False


def test_everything_is_unknown_when_no_go_source_is_found() -> None:
    assert probe.exists(_NO_SOURCE, "Anything") is None
    assert probe.exported(_NO_SOURCE, "Anything") is None
    assert probe.count(_NO_SOURCE, "class") is None


def test_count_of_exported_types() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_count_of_exported_methods() -> None:
    assert probe.count(_FIXTURES, "method") == 1


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "enum") is None
