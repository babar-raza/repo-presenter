"""classify_license_text: the narrow slice of the old repo's license.py this repository ported
2026-10-23 (see that module's own docstring). Adapted from the one directly-applicable case in
the old repo's tests/components/readme/evidence/facts/test_license.py -- the rest of that file
tests license_facts/settle_declared_license, which this repository has not ported."""

from __future__ import annotations

from repo_presenter.readme.evidence.facts.license_text import classify_license_text


def test_classifies_known_license_texts() -> None:
    assert classify_license_text("MIT License\n\nCopyright...") == "MIT"
    assert classify_license_text("Apache License\nVersion 2.0, January 2004") == "Apache-2.0"
    assert classify_license_text("Some proprietary terms nobody wrote down properly.") is None
