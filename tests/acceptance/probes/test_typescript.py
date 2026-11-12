"""TC-017a: the independent TypeScript export-surface probe, exercised against a real fixture.

Three required shapes (see the card): a genuinely public symbol reports ``exists=True,
exported=True``; a genuinely private symbol reports ``exists=True, exported=False``; a symbol
the probe cannot determine reports ``None``, never a guessed ``True``/``False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import typescript as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "typescript"
_NO_PACKAGE = Path(__file__).parent / "fixtures" / "typescript_none"


def test_public_class_exists_and_is_exported() -> None:
    assert probe.exists(_FIXTURES, "Widget") is True
    assert probe.exported(_FIXTURES, "Widget") is True


def test_undeclared_class_exists_but_is_not_re_exported_by_the_barrel() -> None:
    # Helper is declared in widget.ts but index.ts's barrel never re-exports it.
    assert probe.exists(_FIXTURES, "Helper") is True
    assert probe.exported(_FIXTURES, "Helper") is False


def test_reachability_is_unknown_without_a_package_manifest() -> None:
    # orphan.ts has a real class declaration, but there is no package.json anywhere above it,
    # so the probe has no entry point to check reachability against -- it must say so, not guess.
    assert probe.exported(_NO_PACKAGE, "Orphan") is None
    assert probe.count(_NO_PACKAGE, "class") is None


def test_count_of_exported_classes() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "method") is None
