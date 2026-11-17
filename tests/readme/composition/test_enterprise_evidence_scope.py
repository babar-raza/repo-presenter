"""A reachable product page is not evidence that every FOSS limitation is absent."""

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.renderer import _enterprise_paragraph
from repo_presenter.readme.evidence.facts.product_pages import ENTERPRISE_FACT_ID
from repo_presenter.readme.review.scope import shown_text
from repo_presenter.readme.composition import renderer


def context(polarity="SUPPORTED", level="platform", added=""):
    fact = Fact(ENTERPRISE_FACT_ID, "link_target", "https://products.aspose.com/cells/cpp/",
                (Evidence("https://products.aspose.com/cells/cpp/", "RESOLVED"),),
                polarity=polarity, attributes={"level": level})
    return SimpleNamespace(included=[SimpleNamespace(id="enterprise_relationship")],
                           facts=SimpleNamespace(facts=[fact]), name="Aspose.Cells FOSS for Cpp",
                           unit=lambda section, slot: added)


def test_reachable_enterprise_page_does_not_prove_absence_of_all_limitations():
    text = _enterprise_paragraph(context())
    assert text == "See [Aspose.Cells for Cpp — Enterprise Edition](https://products.aspose.com/cells/cpp/)."
    assert "limitations don't apply" not in text


def test_enterprise_link_falls_closed_and_reviewer_still_sees_authored_claims():
    assert _enterprise_paragraph(context(polarity="UNRESOLVED")) == ""
    text = _enterprise_paragraph(context(added="It adds more formats."))
    assert shown_text(text) == "It adds more formats."
    assert shown_text("These limitations don't apply to [old](https://example.org). Legacy authored claim.") == "Legacy authored claim."


def test_unplaced_scope_keeps_ordinary_see_text_and_removes_only_exact_closing(monkeypatch):
    closing = "See [Product — Enterprise Edition](https://example.com)."
    ordinary = ["See the detailed restrictions.", "No support for encrypted files."]
    ctx = renderer.RenderContext.__new__(renderer.RenderContext)
    ctx.included = [SimpleNamespace(id="scope_limitations")]
    ctx.rendered_ids = None
    ctx._unplaced = False
    monkeypatch.setattr(renderer, "_enterprise_paragraph", lambda ctx: closing)
    monkeypatch.setattr(renderer, "_section_body", lambda ctx, section: ordinary + ["", closing])
    assert ctx.unplaced_destinations().text("scope_limitations").strip() == "\n".join(ordinary)
    monkeypatch.setattr(renderer, "_enterprise_paragraph", lambda ctx: "")
    monkeypatch.setattr(renderer, "_section_body", lambda ctx, section: ordinary)
    assert ctx.unplaced_destinations().text("scope_limitations") == "\n".join(ordinary)
