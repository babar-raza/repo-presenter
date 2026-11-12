"""BC-07's visible-line budget under the 2026-11-10 supervisor ruling (owner goals R2): the budget is
``max(policy budget, the published README's own visible lines)`` when a benchmark is present.

Measured motivation: Cells Go's published README prints 585 raw lines (a ~300+ visible-line body
once collapsible <details> blocks are excluded) and our candidate that keeps the R2 floor ran 308
visible lines against the fixed 300 - unfixable without dropping floor content."""

from __future__ import annotations

from repo_presenter.readme.composition.policy import DEFAULT_POLICY, PlanningPolicy
from repo_presenter.readme.composition.renderer import line_counts
from repo_presenter.readme.validation.rules import effective_visible_lines_budget


def _readme(visible: int, collapsed: int = 0) -> str:
    body = "\n".join(f"line {i}" for i in range(visible))
    if collapsed:
        body += "\n<details>\n" + "\n".join(f"hidden {i}" for i in range(collapsed)) + "\n</details>"
    return body


def test_no_benchmark_keeps_the_policy_budget() -> None:
    assert effective_visible_lines_budget(DEFAULT_POLICY, None) == 300
    assert effective_visible_lines_budget(DEFAULT_POLICY, "") == 300


def test_a_short_published_readme_never_lowers_the_budget() -> None:
    assert effective_visible_lines_budget(DEFAULT_POLICY, _readme(120)) == 300


def test_a_long_published_readme_raises_the_budget_to_its_own_visible_lines() -> None:
    published = _readme(560)
    visible, _ = line_counts(published)
    assert effective_visible_lines_budget(DEFAULT_POLICY, published) == visible == 560


def test_collapsed_details_lines_of_the_published_readme_do_not_count() -> None:
    published = _readme(310, collapsed=400)
    visible, total = line_counts(published)
    assert total > visible
    assert effective_visible_lines_budget(DEFAULT_POLICY, published) == visible


def test_a_non_default_policy_budget_is_the_floor_not_overridden() -> None:
    assert effective_visible_lines_budget(PlanningPolicy(visible_lines_budget=450), _readme(200)) == 450
