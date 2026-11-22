"""BL-800/801/802: three more classes of audit false flag on clean Lane R controls (round 7, seed run 44988613948).

* BarCode Python line 186, ``| `Barcode` | Public barcode object returned by the high-level API (some members not
  implemented). |``: the renderer's own marker (``renderer._stub_marked``) for a type with a stubbed member, kept by
  the K02 "behaviour claim" class although a SUPPORTED limitation statement names the member as one that only throws.
* PDF Go line 1130: the maintainers' "Full API reference" bullet plus the count sentence the renderer appended ("It
  covers all 297 public types; the [API Reference](#api-reference) section above covers the essentials."); the flag
  quoted only that sentence, which is the facts' computation (K05), on a line the structural reading calls prose.
* PDF TypeScript line 3848, ``| `OpenOptions` | `password`, `recipient` and `limits` (a `LoadLimits`). |``: a kept
  maintainers' table row that does nothing but list the members of its type, each a SUPPORTED member fact.

Negative controls (each keeps its flag): a type no limitation statement names, a stubbed member whose body returns
a value, a CONTRADICTED statement, a description with its own behaviour cue, a count the facts do not compute, a
claim that also states the maintainers' text, an authored row, a member list with an extra word, an unknown member,
a member of another type, a type the member's own fact does not name.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.derivation import (
    Derivation,
    flag_within_sentences,
    keep_reason,
    member_list_provenance,
    statement_clearances,
    stub_member_provenance,
)
from tests.readme.validation.test_degrade_claims_bl240 import _facts_with, _member, _type

REPO = Path(__file__).resolve().parents[3]


def _auditor():
    spec = importlib.util.spec_from_file_location("run_m9_auditor_bl800", REPO / "scripts" / "run_m9_auditor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- BL-800: the marker for a type with a stubbed member ---------------------------------------------------


def _limitation(text: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact("inherited_unit:052.list", "inherited_unit", text, (Evidence("README.md", "line 9"),), polarity)


def _stub_facts(limitation: str = "`Barcode.to_pdf()` is not implemented.", polarity: str = "SUPPORTED",
                body_throws: str | None = None) -> FactsDocument:
    member = _member("pkg.Barcode", "to_pdf", "method")
    if body_throws:
        member = Fact(member.id, member.kind, member.value, member.evidence, member.polarity,
                      attributes={**(member.attributes or {}), "body_throws": body_throws})
    return _facts_with(_type("pkg.Barcode"), _type("pkg.Other"), member, _limitation(limitation, polarity),
                       drop=("public_symbol:aspose.threed.scene",))


ROW = "| `Barcode` | Public barcode object returned by the high-level API (some members not implemented). |"


def test_a_type_with_a_stubbed_member_is_verified_by_the_limitation_statement() -> None:
    facts = _stub_facts()
    proof = stub_member_provenance([ROW], 1, facts)
    assert proof is not None and "inherited_unit:052.list" in proof and "`Barcode.to_pdf`" in proof
    verified: dict[int, str] = {}
    assert keep_reason("R", ROW, {"source": "renderer"}, facts, [ROW], 1, verified) is None
    assert "K02 verified" in verified[1]


def test_negative_control_a_type_no_statement_names_keeps_its_flag() -> None:
    row = ROW.replace("`Barcode`", "`Other`")
    facts = _stub_facts()
    assert stub_member_provenance([row], 1, facts) is None
    assert keep_reason("R", row, {"source": "renderer"}, facts, [row], 1, {}) == "K02 behaviour claim"


def test_negative_control_a_member_whose_body_returns_a_value_keeps_its_flag() -> None:
    facts = _stub_facts(body_throws="no")
    assert stub_member_provenance([ROW], 1, facts) is None
    assert keep_reason("R", ROW, {"source": "renderer"}, facts, [ROW], 1, {}) == "K02 behaviour claim"


def test_negative_control_an_unsupported_statement_or_another_row_keeps_its_flag() -> None:
    assert stub_member_provenance([ROW], 1, _stub_facts(polarity="CONTRADICTED")) is None
    facts = _stub_facts()
    for row in (
        "| `Barcode` | Always throws when it renders (some members not implemented). |",
        "| `Barcode` | Public barcode object (several members not implemented). |",
        "| `Barcode` | Public barcode object (some members not implemented) and it is thread safe. |",
        "Public barcode object (some members not implemented).",
    ):
        assert stub_member_provenance([row], 1, facts) is None, row


# --- BL-801: the count sentence the renderer appended to a kept maintainers' line --------------------------------

TYPES = _facts_with(*[_type(f"pkg.T{i}") for i in range(5)], drop=("public_symbol:aspose.threed.scene",))
POINTER = "(the [API reference](#api-reference) section above covers the essentials)"
SENTENCE = "It covers all {n} public types; the [API Reference](#api-reference) section above covers the essentials."


def _bullet(n: int) -> str:
    return ("- **[Full API reference](https://reference.aspose.org/pdf/go/)** — the complete, browsable reference for "
            f"the public API surface {POINTER}. {SENTENCE.format(n=n)}")


def _clear(row: str, origin: str = "renderer", refuted: dict[int, str] | None = None):
    return statement_clearances([row], {1: {"source": origin}}, frozenset(), TYPES, None, refuted or {})


def test_the_renderers_count_sentence_on_a_kept_line_is_verified_by_the_facts_computation() -> None:
    whole, sentences = _clear(_bullet(5))
    assert whole == {}
    texts, proof = sentences[1]
    assert texts == (SENTENCE.format(n=5),) and proof.startswith("K05 verified: 5 public types")
    claim = f"[unsupported_claim] {SENTENCE.format(n=5)}"
    assert flag_within_sentences(claim, texts)
    assert flag_within_sentences(f"Line 1: {SENTENCE.format(n=5)}", texts)


def test_negative_control_a_flag_that_also_states_the_maintainers_text_is_not_within_the_sentence() -> None:
    texts = _clear(_bullet(5))[1][1][0]
    claim = "[unsupported_claim] the complete, browsable reference for the public API surface. " + SENTENCE.format(n=5)
    assert not flag_within_sentences(claim, texts)
    assert not flag_within_sentences("[unsupported_claim] It covers all 6 public types.", texts)
    assert not flag_within_sentences("[unsupported_claim] anything", ())


def test_negative_control_a_count_the_facts_do_not_compute_or_an_unowned_line_is_not_verified() -> None:
    assert _clear(_bullet(7)) == ({}, {})
    assert _clear(_bullet(5), origin="authored") == ({}, {})
    assert _clear(_bullet(5), refuted={1: "findings register"}) == ({}, {})
    assert statement_clearances([_bullet(5)], {1: {"source": "renderer"}}, frozenset({1}), TYPES, None, {}) == ({}, {})
    assert statement_clearances([_bullet(5)], {1: {"source": "renderer"}}, frozenset(), TYPES, {2}, {}) == ({}, {})


# --- BL-802: a kept maintainers' table row that only lists members of its type ------------------------------------


def _options_facts(**limits: str) -> FactsDocument:
    def member(name: str, **attributes: str) -> Fact:
        return Fact(f"public_symbol:openoptions.{name}", "public_symbol", f"OpenOptions.{name}",
                    (Evidence("src/o.ts", "line 3; method"),), attributes={"symbol_kind": "method", **attributes})

    return _facts_with(
        _type("OpenOptions"), _type("LoadLimits"), _type("Other"), member("password", docstring="Password."),
        member("recipient", signature=": PubSecRecipient"),
        member("limits", docstring_full="Bounds on what this document may cost to open. A `LoadLimits` and never a patch.",
               **limits),
        drop=("public_symbol:aspose.threed.scene",),
    )


MEMBERS = "| `OpenOptions` | `password`, `recipient` and `limits` (a `LoadLimits`). |"


def test_a_row_listing_only_members_of_its_type_is_verified_by_the_member_facts() -> None:
    proof = member_list_provenance(MEMBERS, _options_facts())
    assert proof is not None
    for fact_id in ("public_symbol:openoptions.password", "public_symbol:openoptions.limits", "public_symbol:loadlimits"):
        assert fact_id in proof
    whole, _ = statement_clearances([MEMBERS], {1: {"source": "renderer"}}, frozenset(), _options_facts(), None, {})
    assert 1 in whole


def test_negative_control_a_cell_that_says_more_than_the_member_names_keeps_its_flag() -> None:
    facts = _options_facts()
    for row in (
        "| `OpenOptions` | `password`, `recipient` and `limits` (a `LoadLimits`) that are always encrypted. |",
        "| `OpenOptions` | Holds `password`, `recipient` and `limits`. |",
        "| `OpenOptions` | `password`, `token` and `limits`. |",
        "| `Other` | `password`, `recipient`. |",
        "| `Unknown` | `password`. |",
        "| `OpenOptions` | `password` (a `Other`). |",
        "| `OpenOptions` | `password` (a `LoadLimits`). |",
        "| `OpenOptions` | `password`, 3 more. |",
        "| `OpenOptions` | See the guide. |",
    ):
        assert member_list_provenance(row, facts) is None, row


def test_negative_control_a_member_that_is_not_supported_is_not_verified() -> None:
    facts = _options_facts()
    unsupported = FactsDocument(
        facts.repository, facts.source_revision,
        tuple(Fact(f.id, f.kind, f.value, f.evidence, "CONTRADICTED", attributes=f.attributes)
              if f.id == "public_symbol:openoptions.recipient" else f for f in facts.facts),
    )
    assert member_list_provenance(MEMBERS, unsupported) is None


# --- the audit applies them -------------------------------------------------------------------------------


def _flag(line: int, claim: str) -> dict:
    return {"candidate_id": "c", "claim": claim, "verdict": "unverifiable", "path": "c.md", "line": line,
            "evidence": "audit: no registered clearance", "located": True, "source": "llm"}


def test_the_audit_clears_a_verified_member_list_row_and_a_flag_that_is_only_the_count_sentence() -> None:
    auditor = _auditor()
    text = f"{MEMBERS}\n{_bullet(5)}\n"
    derived = Derivation(
        derivable=frozenset(), underived=frozenset(),
        statements={1: "member list verified: example"},
        sentences={2: ((SENTENCE.format(n=5),), "K05 verified: example")},
    )
    rows = [
        _flag(1, "[unsupported_claim] Line 1: `OpenOptions` | `password`, `recipient` and `limits`"),
        _flag(2, f"[unsupported_claim] {SENTENCE.format(n=5)}"),
        _flag(2, "[unsupported_claim] the complete, browsable reference for the public API surface"),
    ]
    out = auditor.apply_derivation("c", text, rows, derived)
    assert [r["verdict"] for r in out] == ["supported", "supported", "unverifiable"]
    assert out[0]["cleared_by"] == "derivation" and out[0]["provenance"].startswith("member list verified")
    assert out[1]["provenance"].startswith("K05 verified")
    assert "cleared_by" not in out[2]
