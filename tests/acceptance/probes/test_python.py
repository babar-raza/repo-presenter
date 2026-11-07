"""TC-017a: the independent Python export-surface probe, exercised against a real fixture tree.

Three required shapes (see the card): a genuinely public symbol reports ``exists=True,
exported=True``; a genuinely private symbol reports ``exists=True, exported=False``; a symbol
the probe cannot determine reports ``None``, never a guessed ``True``/``False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import python as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "python"


def test_public_class_exists_and_is_exported() -> None:
    assert probe.exists(_FIXTURES, "pkg.widget.Widget") is True
    assert probe.exported(_FIXTURES, "pkg.widget.Widget") is True


def test_private_method_exists_but_is_not_exported() -> None:
    # `_hidden` is declared (ast sees it regardless of its leading underscore) but
    # `inspect_public_surface` never admits it to the public surface -- exists, not exported.
    assert probe.exists(_FIXTURES, "pkg.widget.Widget._hidden") is True
    assert probe.exported(_FIXTURES, "pkg.widget.Widget._hidden") is False


def test_symbol_in_an_unparseable_module_reports_unknown_never_guessed() -> None:
    # pkg/broken.py has a real syntax error; the probe must say it cannot tell, not guess.
    assert probe.exists(_FIXTURES, "pkg.broken.Anything") is None
    assert probe.exported(_FIXTURES, "pkg.broken.Anything") is None


def test_count_of_public_classes() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_count_is_none_when_no_package_is_found(tmp_path: Path) -> None:
    (tmp_path / "README.txt").write_text("no python package here\n", encoding="utf-8")
    assert probe.count(tmp_path, "class") is None
    assert probe.exists(tmp_path, "anything.Anything") is None
    assert probe.exported(tmp_path, "anything.Anything") is None


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "not-a-real-kind") is None
