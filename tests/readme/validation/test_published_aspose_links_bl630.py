"""BL-630: the Aspose-link ceiling bounds the links a README adds, not the links the published README itself prints.

Slides .NET (hosted run 44924853748): 'BC-06 4 aspose.com links exceed the aspose.com ceiling of 2 (auto budget from
1797 visible words and 7 verified examples)'. The four are the maintainers' own 'Documentation and support' list of
the pinned README (docs, reference, knowledge base, forum on aspose.com), which BC-17 names lost when they are
left out, so the floor R2 holds the candidate to could not satisfy the ceiling. As ``effective_visible_lines_budget``
does for BC-07's line budget, a link the published README prints is exempt; every other Aspose link still counts.
"""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.readme.validation.links import link_failures
from tests.readme.validation.test_registry_checks import _candidate, _link_fact, _with_links

DOCS_LIST = "\n".join(
    [
        "- [Aspose.Slides for .NET — product page](https://products.aspose.com/slides/net/)",
        "- [Documentation](https://docs.aspose.com/slides/net/)",
        "- [API reference](https://reference.aspose.com/slides/net/)",
        "- [Knowledge base](https://kb.aspose.com/slides/net/)",
        "- [Free support forum](https://forum.aspose.com/c/slides/11)",
    ]
)
PUBLISHED = f"# Aspose.Slides FOSS for .NET\n\n## Documentation and support\n\n{DOCS_LIST}\n"
FACTS = _with_links(
    _link_fact("015", "https://products.aspose.com/slides/net/"),
    _link_fact("016", "https://docs.aspose.com/slides/net/"),
    _link_fact("017", "https://reference.aspose.com/slides/net/"),
    _link_fact("018", "https://kb.aspose.com/slides/net/"),
    _link_fact("019", "https://forum.aspose.com/c/slides/11"),
    _link_fact("020", "https://docs.aspose.com/slides/net/extra/"),
    _link_fact("021", "https://blog.aspose.com/slides/net-news/"),
    _link_fact("022", "https://docs.aspose.com/slides/net/more/"),
)


#: As many visible words as the hosted candidate had (1797): the automatic budget is then 4 in all, 2 on aspose.com.
PROSE = " ".join(["word"] * 1800)


def _ceiling(readme: str, *, published: str | None) -> list[str]:
    candidate = replace(
        _candidate(readme=f"{_candidate().readme}\n{PROSE}\n\n{readme}\n", facts=FACTS),
        benchmark_readme=published,
    )
    return [f.detail for f in link_failures(candidate) if "exceed" in f.detail]


def test_the_exact_hosted_shape_the_published_lists_four_aspose_com_links() -> None:
    kept = f"## Documentation and support\n\n{DOCS_LIST}\n"
    before = _ceiling(kept, published=None)
    assert any("aspose.com links exceed the aspose.com ceiling of 2" in f for f in before), before
    assert _ceiling(kept, published=PUBLISHED) == []


def test_trailing_slashes_do_not_hide_a_published_link() -> None:
    kept = DOCS_LIST.replace("net/)", "net)")
    assert _ceiling(kept, published=PUBLISHED) == []


def test_a_link_the_published_readme_does_not_print_still_counts() -> None:
    added = (
        DOCS_LIST
        + "\n- [Extra](https://docs.aspose.com/slides/net/extra/)"
        + "\n- [News](https://blog.aspose.com/slides/net-news/)"
        + "\n- [More](https://docs.aspose.com/slides/net/more/)"
    )
    over = _ceiling(added, published=PUBLISHED)
    assert any("aspose.com links exceed the aspose.com ceiling of 2" in f for f in over), over
    # the same candidate against a published README that prints none of them
    assert _ceiling(DOCS_LIST, published="# Aspose.Slides FOSS for .NET\n") != []


def test_only_the_links_the_published_readme_prints_are_exempt() -> None:
    only_one = "# Aspose.Slides FOSS for .NET\n\n- [Docs](https://example.com/docs)\n- [Page](https://products.aspose.com/slides/net/)\n"
    assert any("exceed" in f for f in _ceiling(DOCS_LIST, published=only_one))


def test_a_candidate_with_no_published_readme_is_held_as_before() -> None:
    assert any("exceed" in f for f in _ceiling(DOCS_LIST, published=""))
    assert any("exceed" in f for f in _ceiling(DOCS_LIST, published=None))
