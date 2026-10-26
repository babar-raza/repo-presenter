"""The pure badge and example rules BC-03 and BC-07 call (plans/idea.md).

Ported (ADAPT, import paths only) from the old repository-presenter project's
``tests/components/readme/validation/links/test_rules.py``. One test dropped: the Enterprise
anchor rule it exercised (``enterprise_anchor_problems``) is retired (owner correction R2/R3).
"""

from __future__ import annotations

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import BADGE_ORDER
from repo_presenter.readme.validation import rules
from repo_presenter.readme.validation.provenance import (
    EXECUTION_MARKERS as PROVENANCE_MARKERS,
)
from repo_presenter.readme.validation.rules import (
    badge_problems,
    badge_slot,
    verified_example_hashes,
)

PYPI = "[![PyPI](https://img.shields.io/pypi/v/p.svg)](https://pypi.org/project/p/)"
RUNTIME = "![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)"
BUILD = (
    "[![Build Status](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)]"
    "(https://github.com/o/r/actions/workflows/ci.yml)"
)
LICENSE = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)"
)
CONTRIB = (
    "[![Contributors](https://img.shields.io/github/contributors/o/r)]"
    "(https://github.com/o/r/graphs/contributors)"
)
EVERYTHING = [
    ("package", PYPI),
    ("runtime", RUNTIME),
    ("build", BUILD),
    ("license", LICENSE),
    ("contributors", CONTRIB),
]


def test_the_stable_order_is_the_one_idea_md_states() -> None:
    assert BADGE_ORDER == ("package", "runtime", "build", "license", "contributors")


def test_the_execution_markers_match_the_ones_bc_03_uses() -> None:
    assert rules.EXECUTION_MARKERS == PROVENANCE_MARKERS


@pytest.mark.parametrize(
    ("token", "slot"),
    [
        (PYPI, "package"),
        (RUNTIME, "runtime"),
        (BUILD, "build"),
        (LICENSE, "license"),
        (CONTRIB, "contributors"),
        ("![x](relative/img.png)", None),
        ("no badge here", None),
    ],
)
def test_a_badge_is_classified_by_its_image(token: str, slot: str | None) -> None:
    assert badge_slot(token) == slot


def test_the_full_row_in_order_has_no_problems() -> None:
    assert badge_problems(" ".join(m for _, m in EVERYTHING), EVERYTHING) == []


def test_any_subset_in_order_is_allowed_because_a_badge_may_be_omitted() -> None:
    for drop in range(len(EVERYTHING)):
        subset = [pair for index, pair in enumerate(EVERYTHING) if index != drop]
        assert badge_problems(" ".join(m for _, m in subset), EVERYTHING) == []
    assert badge_problems("", EVERYTHING) == []


def test_every_adjacent_swap_breaks_the_order() -> None:
    for i in range(len(EVERYTHING) - 1):
        swapped = list(EVERYTHING)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        problems = badge_problems(" ".join(m for _, m in swapped), EVERYTHING)
        assert any("breaks the stable order" in p for p in problems), (i, problems)


def test_a_repeat_a_forgery_and_an_unrecognized_badge_are_each_named() -> None:
    assert "duplicate license badge" in badge_problems(
        f"{LICENSE} {LICENSE}", EVERYTHING
    )
    forged = badge_problems(BUILD, [("license", LICENSE)])
    assert any(
        p.startswith("build badge is not supported by any verified fact")
        for p in forged
    )
    altered = BUILD.replace("ci.yml", "evil.yml")
    assert any(
        "build badge differs from the verified one" in p
        for p in badge_problems(altered, EVERYTHING)
    )
    assert any(
        "fills no recognized slot" in p for p in badge_problems("![x](local.png)", [])
    )


def test_only_examples_that_actually_ran_count_as_verified() -> None:
    def example(
        name: str, value: str, detail: str, polarity: str = "SUPPORTED"
    ) -> Fact:
        return Fact(
            f"example:{name}",
            "example",
            value,
            (Evidence("examples.json", detail),),
            polarity=polarity,  # type: ignore[arg-type]
        )

    facts = FactsDocument(
        "o/r",
        "a" * 40,
        (
            example("001", "print(1)\n", "example 1: EXECUTED; ok"),
            example("002", "print(2)\n", "example 2: COMPILED; ok"),
            example("003", "print(3)\n", "example 3: SKIPPED"),
            example(
                "004", "print(4)\n", "example 4: EXECUTED", polarity="CONTRADICTED"
            ),
        ),
    )
    assert len(verified_example_hashes(facts)) == 2
