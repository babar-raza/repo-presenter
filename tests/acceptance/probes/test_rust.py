"""TC-017a: the independent Rust export-surface probe, exercised against a real fixture crate.

Three required shapes (see the card), plus the Rust-specific shape it names explicitly: a name
reachable only via `pub use` plus a bare `pub` declaration (the exact
``aho_corasick::AhoCorasick`` shape from ``extractor.py``'s own docstring) is NOT confirmed
unreachable even when the vendored engine's own ``reachable`` mark says ``False``.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.acceptance.probes import rust as probe

_FIXTURES = Path(__file__).parent / "fixtures" / "rust"
_NO_SOURCE = Path(__file__).parent / "fixtures" / "rust_none"


def test_pub_use_reexported_struct_exists_and_is_exported() -> None:
    assert probe.exists(_FIXTURES, "AhoCorasick") is True
    assert probe.exported(_FIXTURES, "ahocorasick::AhoCorasick") is True


def test_non_reexported_struct_exists_but_is_not_exported() -> None:
    # Secret is declared (bare, no pub at all) in internal.rs, but lib.rs never `pub use`s it.
    assert probe.exists(_FIXTURES, "Secret") is True
    assert probe.exported(_FIXTURES, "Secret") is False


def test_everything_is_unknown_when_no_rust_source_is_found() -> None:
    assert probe.exists(_NO_SOURCE, "Anything") is None
    assert probe.exported(_NO_SOURCE, "Anything") is None
    assert probe.count(_NO_SOURCE, "class") is None


def test_count_of_exported_structs() -> None:
    assert probe.count(_FIXTURES, "class") == 1


def test_confirms_unreachable_does_not_trust_the_engines_mark_alone() -> None:
    """The exact `aho_corasick::AhoCorasick` shape the extractor.py docstring describes.

    The vendored engine's own best-effort scan mismarked `aho_corasick::AhoCorasick`
    (re-exported through nested braces) as unreachable. ``confirms_unreachable_for`` must
    refuse to confirm it: it IS `pub use`-re-exported at the crate root, so signal 1 alone
    already disagrees.
    """
    confirms_unreachable = probe.confirms_unreachable_for(_FIXTURES)
    entry = {"class_import": "ahocorasick::AhoCorasick", "reachable": False}
    assert confirms_unreachable(entry) is False


def test_confirms_unreachable_agrees_when_both_negative_signals_hold() -> None:
    """Secret is neither `pub use`-re-exported nor declared with a bare `pub` in lib.rs itself --
    both independent negative signals agree, so confirming it unreachable is correct here."""
    confirms_unreachable = probe.confirms_unreachable_for(_FIXTURES)
    entry = {"class_import": "internal::Secret", "reachable": False}
    assert confirms_unreachable(entry) is True


def test_unsupported_kind_returns_none_not_zero() -> None:
    assert probe.count(_FIXTURES, "method") is None
