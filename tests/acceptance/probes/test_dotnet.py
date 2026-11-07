"""TC-017a: the independent .NET export-surface probe, exercised against a real fixture tree.

Three required shapes (see the card): a genuinely public symbol reports ``exists=True,
exported=True``; a genuinely private symbol reports ``exists=True, exported=False``; a symbol
the probe cannot determine reports ``None``, never a guessed ``True``/``False``. Also proves the
probe reads the declared ``public`` keyword, not a capitalization heuristic: ``Hide`` is
capitalized like a public C# member would be, yet it is declared ``private`` and must read
``exported=False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import dotnet as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "dotnet"
_NO_SOURCE = Path(__file__).parent / "fixtures" / "dotnet_none"


def test_public_class_and_public_method_are_exported() -> None:
    assert probe.exists(_FIXTURES, "Widget") is True
    assert probe.exported(_FIXTURES, "Widget") is True
    assert probe.exists(_FIXTURES, "Widget.Render") is True
    assert probe.exported(_FIXTURES, "Widget.Render") is True


def test_private_method_exists_but_is_not_exported_despite_its_capitalized_name() -> None:
    assert probe.exists(_FIXTURES, "Widget.Hide") is True
    assert probe.exported(_FIXTURES, "Widget.Hide") is False


def test_internal_type_exists_but_is_not_exported() -> None:
    assert probe.exists(_FIXTURES, "Hidden") is True
    assert probe.exported(_FIXTURES, "Hidden") is False


def test_everything_is_unknown_when_no_cs_source_is_found() -> None:
    assert probe.exists(_NO_SOURCE, "Anything") is None
    assert probe.exported(_NO_SOURCE, "Anything") is None
    assert probe.count(_NO_SOURCE, "class") is None


def test_count_of_public_classes() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "function") is None
