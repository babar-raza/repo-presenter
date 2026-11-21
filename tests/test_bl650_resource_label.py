"""BL-650 (hosted Lane R Slides .NET, run 44947970617): a kept list of sibling editions
("- [Aspose.Slides FOSS for Java](https://github.com/.../Aspose.Slides-FOSS-for-Java)") is printed by
Documentation and Resources through its link facts. An item that is only its link had its own label as
its "description", so the line read ``- **[Aspose.Slides FOSS for Java](url)** — Aspose.Slides FOSS for
Java`` and BC-12 read the prose copy as a short spelling of the product ('Aspose.Slides FOSS'): a
COMPOSING failure in a renderer-owned section, which no repair can route (no LLM section named)."""

from __future__ import annotations

import types
from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.readme.composition.renderer import RenderContext, _documentation_resources
from repo_presenter.readme.validation.structure import canonical_name_failures

REPO = "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET"
LIST = (
    "- [Aspose.Slides FOSS for Java](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java)\n"
    "- [Aspose.Slides FOSS for C++](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp)\n"
    "- [Aspose.Slides FOSS for Python](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python)"
)
URLS = [
    "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
    "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp",
    "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python",
]
TEXTS = ["Aspose.Slides FOSS for Java", "Aspose.Slides FOSS for C++", "Aspose.Slides FOSS for Python"]


def _entry():
    return next(e for e in load_registry(Path("data/registry.json")).entries if e.repository == REPO)


def _render(list_text: str, urls: list[str], texts: list[str], *, polarity: str = "SUPPORTED") -> str:
    links = tuple(
        Fact(f"link_target:{12 + i}", "link_target", url,
             (Evidence("README.md", f"line {493 + i}; external; text '{text}'"),), polarity=polarity)
        for i, (url, text) in enumerate(zip(urls, texts))
    )
    facts = FactsDocument(
        REPO, "86c441b5" * 5,
        (
            Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
            Fact("inherited_unit:083.list", "inherited_unit", list_text, (Evidence("README.md"),),
                 attributes={"section": "Aspose.Slides FOSS for .NET > Choosing an edition"}),
            *links,
        ),
    )
    dispositions = {"dispositions": [{
        "unit_id": "inherited_unit:083.list", "disposition": "VERIFIED_PRESERVE",
        "destination_section": "documentation_resources", "fact_ids": [],
    }]}
    plan = {
        "sections": [{"section_id": "documentation_resources", "include": True}],
        "links": [{"link_fact_id": link.id, "section_id": "documentation_resources"} for link in links],
    }
    context = RenderContext(_entry(), facts, plan, {"units": []}, dispositions)
    return "\n".join(_documentation_resources(context))


def _failures(text: str):
    return canonical_name_failures(types.SimpleNamespace(entry=_entry(), readme=text))


def test_a_list_of_sibling_editions_prints_no_label_as_its_own_description() -> None:
    rendered = _render(LIST, URLS, TEXTS)
    assert "— On github.com." in rendered
    assert "— Aspose.Slides FOSS for" not in rendered
    assert rendered.count("**[Aspose.Slides FOSS for ") == 3  # every link and its label stay
    assert _failures(rendered) == []


def test_negative_control_the_label_as_description_is_the_failing_shape() -> None:
    old = "\n".join(f"- **[{t}]({u})** — {t}" for t, u in zip(TEXTS, URLS))
    assert [f.stage for f in _failures(old)] == ["COMPOSING", "COMPOSING", "COMPOSING"][: len(_failures(old))]
    assert _failures(old), "the shape the hosted run printed must still fail BC-12"


def test_a_real_description_is_kept_as_written() -> None:
    described = "\n".join(
        f"- [{t}]({u}) — the {t.rsplit(' ', 1)[-1]} edition of the library." for t, u in zip(TEXTS, URLS)
    )
    rendered = _render(described, URLS, TEXTS)
    assert "— the Java edition of the library." in rendered
    assert "— On github.com." not in rendered
