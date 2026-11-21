"""BL-560: a Core API row that is the renderer's own fact-true description is not an author's claim.

Real data: hosted Lane R refresh runs 44898179900 (HTML Python) and 44898282006 (PSD Java). The BL-240 degrade
replaced each authored row the review faulted with the renderer's fact-true row ("| `CSSSupportsRule` | Declares
the fields condition_text and css_rules. |", "| `PsdImageWriter` | Class that declares the method save. |"), and
the production review then faulted those rows (``unsupported_claim``): its packet lists a type's method names, so
the fields and properties the row names were never shown, and no lever can change a row no unit owns. Five of six
and five of seven blocking findings were such rows, and the candidates were rejected.

The rows are printed by ``renderer._described`` from the one ``TypeDescriber`` both lanes share, so they are
filtered out of the production review's scope exactly like ``Public class.``; a row an author wrote, or a
describer row with one member changed, is still reviewed. The audit (``authored_type_rows`` default) keeps the
row and its type facts.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import RenderContext, _described
from repo_presenter.readme.review.scope import (
    authored_table_lines,
    authored_type_rows,
    fact_true_row_forms,
)
from tests.readme.composition.synthetic import make_entry


def _cls(name: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:aspose_html.cssom.{name.lower()}", "public_symbol", f"aspose_html.cssom.{name}",
        (Evidence("src/aspose_html/cssom/_rules.py", "line 1; class; public"),), "SUPPORTED",
        attributes={"symbol_kind": "class", **attributes},
    )


def _method(owner: str, name: str) -> Fact:
    return Fact(
        f"public_symbol:aspose_html.cssom.{owner.lower()}.{name}", "public_symbol",
        f"aspose_html.cssom.{owner}.{name}",
        (Evidence("src/aspose_html/cssom/_rules.py", "line 2; method; public"),), "SUPPORTED",
        attributes={"symbol_kind": "method"},
    )


def _enum() -> list[Fact]:
    kind = Fact(
        "public_symbol:aspose_html.cssom.ruletype", "public_symbol", "aspose_html.cssom.RuleType",
        (Evidence("src/aspose_html/cssom/_rules.py", "line 3; enum; public"),), "SUPPORTED",
        attributes={"symbol_kind": "enum"},
    )
    members = [
        Fact(
            f"enum_member:aspose_html.cssom.ruletype.{value.lower()}", "enum_member",
            f"aspose_html.cssom.RuleType.{value}", (Evidence("src/aspose_html/cssom/_rules.py"),),
            "SUPPORTED", attributes={"enum": "aspose_html.cssom.RuleType"},
        )
        for value in ("MEDIA", "SUPPORTS")
    ]
    return [kind, *members]


def _facts() -> FactsDocument:
    return FactsDocument(
        "o/r", "a" * 40,
        (
            _cls("CSSSupportsRule", fields="condition_text, css_rules"),
            _cls("CSSMediaRule", fields="media_text, css_rules"),
            _cls("CSSWriter"),
            _method("CSSWriter", "save"),
            *_enum(),
        ),
    )


def _types(facts: FactsDocument) -> dict[str, Fact]:
    return {f.value.rsplit(".", 1)[-1]: f for f in facts.facts if f.kind == "public_symbol" and "." not in f.value[len("aspose_html.cssom."):]}


def _readme(rows: dict[str, str]) -> str:
    body = "\n".join(f"| `{name}` | {text} |" for name, text in rows.items())
    return f"# Aspose.HTML FOSS for Python\n\n## API Reference\n\n### Core API\n\n| Class | Description |\n| --- | --- |\n{body}\n"


def _printed(facts: FactsDocument, name: str) -> str:
    """The row description the real renderer prints for ``name`` with no authored sentence."""
    context = RenderContext(make_entry(), facts, {"sections": []}, {"units": []}, {"dispositions": []})
    return _described(context, _types(facts)[name], "")


def _reviewed(readme: str, facts: FactsDocument) -> list[str]:
    rows = readme.splitlines()
    return [rows[n - 1].split("|")[1].strip(" `") for n in sorted(authored_table_lines(readme, facts))]


def test_the_renderers_printed_rows_are_the_fact_true_forms() -> None:
    facts = _facts()
    assert _printed(facts, "CSSSupportsRule") == "Declares the fields condition_text and css_rules."
    assert _printed(facts, "CSSWriter") == "Declares the member save."
    assert _printed(facts, "RuleType") == "Enumerates MEDIA and SUPPORTS."
    types = _types(facts)
    for name in ("CSSSupportsRule", "CSSWriter", "RuleType"):
        forms = fact_true_row_forms(types[name], facts)
        assert " ".join(_printed(facts, name).casefold().split()) in forms


def test_a_fact_true_row_is_not_in_the_production_review_scope() -> None:
    facts = _facts()
    readme = _readme({name: _printed(facts, name) for name in ("CSSSupportsRule", "CSSMediaRule", "CSSWriter", "RuleType")})
    assert _reviewed(readme, facts) == []


def test_the_audit_still_sees_each_row_with_its_type_fact() -> None:
    facts = _facts()
    readme = _readme({"CSSSupportsRule": _printed(facts, "CSSSupportsRule")})
    assert [f.id for f in authored_type_rows(readme, facts).values()] == ["public_symbol:aspose_html.cssom.csssupportsrule"]


def test_the_stub_marked_fact_true_row_is_also_the_renderers() -> None:
    facts = _facts()
    text = _printed(facts, "CSSMediaRule").removesuffix(".") + " (some members not implemented)."
    assert _reviewed(_readme({"CSSMediaRule": text}), facts) == []


def test_negative_control_an_authored_sentence_is_still_reviewed() -> None:
    facts = _facts()
    readme = _readme({"CSSSupportsRule": "Applies a @supports condition and always persists to disk."})
    assert _reviewed(readme, facts) == ["CSSSupportsRule"]


def test_negative_control_a_fact_true_row_with_a_member_the_facts_do_not_state_is_still_reviewed() -> None:
    facts = _facts()
    readme = _readme({"CSSSupportsRule": "Declares the fields condition_text and media_text."})
    assert _reviewed(readme, facts) == ["CSSSupportsRule"]
    readme = _readme({"CSSWriter": "Declares the members save and delete."})
    assert _reviewed(readme, facts) == ["CSSWriter"]
    readme = _readme({"RuleType": "Enumerates MEDIA, SUPPORTS and IMPORT."})
    assert _reviewed(readme, facts) == ["RuleType"]
