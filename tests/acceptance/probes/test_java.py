"""TC-017a: the independent Java export-surface probe, exercised against a real fixture tree.

Three required shapes (see the card): a genuinely public symbol reports ``exists=True,
exported=True``; a genuinely private symbol reports ``exists=True, exported=False``; a symbol
the probe cannot determine reports ``None``, never a guessed ``True``/``False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import java as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "java"
_NO_SOURCE = Path(__file__).parent / "fixtures" / "java_none"


def test_public_class_and_public_method_are_exported() -> None:
    assert probe.exists(_FIXTURES, "Widget") is True
    assert probe.exported(_FIXTURES, "Widget") is True
    assert probe.exists(_FIXTURES, "Widget.render") is True
    assert probe.exported(_FIXTURES, "Widget.render") is True


def test_private_method_exists_but_is_not_exported() -> None:
    # hide() is declared (the raw scan sees it regardless of its modifier) but carries no
    # `public` keyword -- exists, but its own type being public does not make it reachable.
    assert probe.exists(_FIXTURES, "Widget.hide") is True
    assert probe.exported(_FIXTURES, "Widget.hide") is False


def test_everything_is_unknown_when_no_java_source_is_found() -> None:
    assert probe.exists(_NO_SOURCE, "Anything") is None
    assert probe.exported(_NO_SOURCE, "Anything") is None
    assert probe.count(_NO_SOURCE, "class") is None


def test_count_of_public_classes() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "method") is None
