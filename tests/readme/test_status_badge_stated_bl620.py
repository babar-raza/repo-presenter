"""BL-620: a maintainers' static status badge no fact verifies is never printed by the renderer (BC-07), and a
badge row is rendered by the shell, so no disposition could restore it: BC-17 named it lost on every settle
round of hosted Lane R run 44924893253 (Aspose.TeX-FOSS-for-Python, ``inherited_unit:002.badge_row`` holds
``https://img.shields.io/badge/status-pre--alpha-orange.svg``). It is accounted for when the candidate states
the same value in words (the maintainers' own kept Scope sentence 'This is a Pre-Alpha release'); a badge whose
value the candidate never states stays a loss. Real header text: README.md of the pinned source (07db3203)."""

from __future__ import annotations

from repo_presenter.readme.parity_gate import (
    badge_row_replaced,
    badge_slot_replaced,
    status_badge_stated,
)

STATUS = "https://img.shields.io/badge/status-pre--alpha-orange.svg"
HEADER = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python/blob/main/LICENSE) "
    "[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python/blob/main/pyproject.toml) "
    f"[![Status: Pre--Alpha]({STATUS})](https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python#scope-and-limitations)"
)
CANDIDATE = (
    "# Aspose.TeX FOSS for Python\n\n"
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) "
    "![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)\n\n"
    "## Scope and Limitations\n\n- This is a Pre-Alpha release: the core engine and public API are under active development.\n"
)
SILENT = CANDIDATE.replace("- This is a Pre-Alpha release: the core", "- The core")


def test_the_status_badge_is_accounted_when_the_candidate_says_the_status() -> None:
    assert status_badge_stated(STATUS, CANDIDATE)
    assert badge_slot_replaced(STATUS, HEADER, CANDIDATE)
    assert badge_row_replaced(HEADER, CANDIDATE)


def test_the_link_of_the_status_badge_follows_it() -> None:
    target = "https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python#scope-and-limitations"
    assert badge_slot_replaced(target, HEADER, CANDIDATE)
    assert badge_slot_replaced(target, HEADER, SILENT) is None


def test_a_status_the_candidate_never_states_stays_a_loss() -> None:
    assert status_badge_stated(STATUS, SILENT) is None
    assert badge_slot_replaced(STATUS, HEADER, SILENT) is None
    assert not badge_row_replaced(HEADER, SILENT)


def test_only_a_static_shields_badge_with_no_slot_is_covered() -> None:
    assert status_badge_stated("readme.resources/pre-alpha.png", CANDIDATE) is None  # a body image is content
    assert status_badge_stated("https://example.com/badge/status-pre--alpha-orange.svg", CANDIDATE) is None
    assert status_badge_stated("https://img.shields.io/badge/python-3.10%2B-blue.svg", "3.10+") is None  # a runtime slot: its own rule
    assert status_badge_stated("https://img.shields.io/github/issues/o/r.svg", CANDIDATE) is None  # dynamic: carried by the renderer
    assert status_badge_stated("https://img.shields.io/badge/coverage-12-red.svg", CANDIDATE) is None  # '12' stated nowhere
