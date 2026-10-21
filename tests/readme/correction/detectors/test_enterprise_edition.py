"""Auto-fix for the Enterprise Edition naming violation: generalized from three real portfolio
fixes (see ``evidence/build/P1_PORTFOLIO_SCALE/*/lane_l_candidate.diff`` for
aspose-slides-foss__Aspose.Slides-FOSS-for-Java, aspose-words-foss__Aspose.Words-FOSS-for-.NET and
aspose-words-foss__Aspose.Words-FOSS-for-Python -- the exact phrases below are drawn from those
diffs, not invented for the test).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.enterprise_edition import (
    ENTERPRISE_FACT_ID,
    enterprise_edition_naming,
)
from repo_presenter.readme.correction.model import FALSE_CLAIM_FIX


def _enterprise(make_fact: Any) -> Any:
    return make_fact(
        ENTERPRISE_FACT_ID,
        "https://products.aspose.com/words/net/",
        evidence=(("https://products.aspose.com/words/", "enterprise target"),),
    )


def test_a_commercial_link_is_rewritten_with_enterprise_edition_in_its_text(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = (
        "If your project grows into needing any of the above, the commercial "
        "[Aspose.Words for .NET](https://products.aspose.com/words/net/) has all of it.\n"
    )
    ctx = make_context(readme, make_facts(_enterprise(make_fact)))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.kind == FALSE_CLAIM_FIX
    assert edit.fact_ids == (ENTERPRISE_FACT_ID,)
    assert edit.original == "the commercial [Aspose.Words for .NET](https://products.aspose.com/words/net/)"
    assert edit.replacement == (
        "[Aspose.Words for .NET — Enterprise Edition](https://products.aspose.com/words/net/)"
    )
    assert readme[edit.start : edit.end] == edit.original


def test_a_bare_commercial_product_name_drops_the_product_wrapper(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = (
        "This library mirrors the naming of the commercial Aspose.Words for .NET product, so "
        "that product's own documentation is often the fastest way to understand it.\n"
    )
    ctx = make_context(readme, make_facts(_enterprise(make_fact)))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.original == "the commercial Aspose.Words for .NET product"
    assert edit.replacement == "Aspose.Words for .NET — Enterprise Edition"


def test_no_enterprise_fact_on_record_means_the_fix_is_reported_not_applied(
    make_context: Any, make_facts: Any
) -> None:
    readme = "See the commercial Aspose.Words for .NET for the full feature set.\n"
    ctx = make_context(readme, make_facts())  # no link_target:product.enterprise fact
    result = enterprise_edition_naming(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert "no link_target:product.enterprise fact is on record" in finding.reason


def test_a_bare_commercial_product_with_no_name_on_its_line_is_reported_not_guessed(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "The namespaces are the same as the commercial product, so existing code compiles.\n"
    ctx = make_context(readme, make_facts(_enterprise(make_fact)))
    result = enterprise_edition_naming(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert "commercial product" in finding.reason and "not guessed" in finding.reason


def test_commercial_describing_something_other_than_the_product_name_is_left_alone(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Measured in the real .NET diff: "the commercial codebase reduced as far as it would go"
    was correctly left unchanged by this session's own manual fix -- it is not a naming violation
    (the codebase is commercial-origin, not a substitute spelling of the product's own name)."""
    readme = "What's included today is the minimum, the commercial codebase reduced as far as it would go.\n"
    ctx = make_context(readme, make_facts(_enterprise(make_fact)))
    result = enterprise_edition_naming(ctx)
    assert result.edits == () and result.findings == ()
