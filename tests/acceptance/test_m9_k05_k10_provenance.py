"""BL-013 round 2, after BL-065 and BL-070: a K05 count or K10 Enterprise Edition line leaves the
known-false list only when its provenance verifies it (``run_m9_auditor.class_provenance``).

Every line below is verbatim from a control of M9 round 43559491132 (its seal at the audited revision);
the Words Python facts are the real sealed surface (``tests/fixtures/shipped_packages/words_python.json.gz``)
narrowed by the build's package list, the other counts are the sealed facts' numbers. Negative controls:
the very same lines as sealed before the fixes (198, "Aspose.Words — Enterprise Edition", the Cells C++
duplicated name), a count of a kind no fact counts, a wrong number, and a registered K05 row.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("run_m9_auditor", REPO / "scripts" / "run_m9_auditor.py")
auditor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditor)

ENTERPRISE = "link_target:product.enterprise"


def _types(classes: int, enums: int, extra: tuple[Fact, ...] = ()) -> FactsDocument:
    facts = [
        Fact(f"public_symbol:pkg.t{i}", "public_symbol", f"pkg.T{i}",
             (Evidence(f"src/pkg/t{i}.x", f"line 1; {'class' if i < classes else 'enum'}; T{i}"),),
             attributes={"symbol_kind": "class" if i < classes else "enum"})
        for i in range(classes + enums)
    ]
    return FactsDocument("o/r", "a" * 40, (*facts, *extra))


def _enterprise(url: str, level: str = "platform") -> Fact:
    return Fact(ENTERPRISE, "link_target", url, (Evidence(url, "RESOLVED; enterprise target"),),
                attributes={"level": level, "role": "enterprise"})


def _words_python() -> FactsDocument:
    """The sealed Words Python surface at 2d2efee2, narrowed as re-certification now narrows it."""
    from repo_presenter.recertify import SourceSnapshot, shipped_facts

    case = json.loads(gzip.decompress((REPO / "tests" / "fixtures" / "shipped_packages" / "words_python.json.gz").read_bytes()))
    facts = tuple(
        Fact(r["id"], r["kind"], r["value"], tuple(Evidence(p, r["detail"]) for p in r["paths"]),
             polarity=r["polarity"], attributes={"symbol_kind": r["symbol_kind"]} if r["kind"] == "public_symbol" else None)
        for r in case["surface"]
    )
    document = FactsDocument(case["repository"], case["revision"],
                             (*facts, _enterprise("https://products.aspose.com/words/python-net/")))
    source = SourceSnapshot(tree_paths=tuple(case["tree_py"]), readme=b"", manifests=case["manifests"])
    return shipped_facts(document, "python", source)[0]


WORDS_H1 = "# Aspose.Words FOSS for Python"
#: ab8a03 lines 337-338, 614 and 632 as sealed (before) and as re-certified under the fixes (after)
WORDS_BEFORE = [
    WORDS_H1,
    "the target format is otherwise inferred from the output file's extension. The library ships 198",
    "public types across the DOC/DOCX/RTF/Markdown/Text readers, the DOCX/Markdown/PDF writers, and the shared",
    "- **[Full API reference](https://reference.aspose.org/words/python/)** — the complete, browsable reference "
    "for all 198 public types (the [API reference](#api-reference) section above covers the essentials).",
    "  `memory_optimization` — exist for API forward-compatibility with Aspose.Words — Enterprise Edition",
]
WORDS_AFTER = [row.replace("198", "189").replace("with Aspose.Words — ", "with Aspose.Words for Python — ")
               for row in WORDS_BEFORE]


def test_words_python_counts_and_name_verify_only_after_the_fixes() -> None:
    facts = _words_python()
    for number in (2, 4):
        assert auditor.class_provenance("K05 type count", WORDS_BEFORE, number, facts) is None
        proof = auditor.class_provenance("K05 type count", WORDS_AFTER, number, facts)
        assert proof is not None and "189 " in proof and "aspose/words_foss 189" in proof
    assert auditor.class_provenance("K10 Enterprise Edition naming", WORDS_BEFORE, 5, facts) is None
    proof = auditor.class_provenance("K10 Enterprise Edition naming", WORDS_AFTER, 5, facts)
    assert proof is not None and "Aspose.Words for Python — Enterprise Edition" in proof


def test_a_kept_reason_cites_the_class_until_the_provenance_verifies_it() -> None:
    facts = _words_python()
    edit = {"source": "edit", "detector": "stale_type_count", "fact_ids": ("public_symbol:aspose",)}
    assert auditor.keep_reason("L", WORDS_BEFORE[1], edit, facts, WORDS_BEFORE, 2) == "K05 type count"
    verified: dict[int, str] = {}
    assert auditor.keep_reason("L", WORDS_AFTER[1], edit, facts, WORDS_AFTER, 2, verified) is None
    assert verified[2].startswith("K05 verified: 189 public types")
    # without the case text there is no provenance: the class keeps the flag (the old behaviour)
    assert auditor.keep_reason("L", WORDS_AFTER[1], edit, facts) == "K05 type count"


def test_the_3d_java_enterprise_name_verifies_and_the_cells_cpp_duplicate_does_not() -> None:
    java = ["# Aspose.3D FOSS for Java", "**Acknowledgments.** This project is a clean-room implementation built for API compatibility",
            "with Aspose.3D for Java — Enterprise Edition library."]  # e43a75 lines 632-633
    assert auditor.class_provenance("K10", java, 3, FactsDocument("o/r", "a" * 40, (_enterprise("https://products.aspose.com/3d/java/"),)))
    cpp = ["# Aspose.Cells FOSS for C++",
           "[Aspose.Cells for C++ — Enterprise Edition](https://products.aspose.com/cells/cpp/), the",
           "Aspose.Cells for C++ — Enterprise Edition line this FOSS edition's API is modeled on, with the wider format matrix and"]
    facts = FactsDocument("o/r", "a" * 40, (_enterprise("https://products.aspose.com/cells/cpp/"),))
    assert auditor.class_provenance("K10", cpp, 2, facts)  # the link line names it once, at its own URL
    assert auditor.class_provenance("K10", cpp, 3, facts) is None  # 802069 line 561: the duplicate
    # a link carrying the name to another URL, or a family-level target named with a platform, fails
    assert auditor.class_provenance("K10", [cpp[0], cpp[1].replace("/cells/cpp/", "/cells/net/")], 2, facts) is None
    family = FactsDocument("o/r", "a" * 40, (_enterprise("https://products.aspose.com/cells/", "family"),))
    assert auditor.class_provenance("K10", cpp[:2], 2, family) is None


def test_counts_verify_against_the_computation_and_the_rows_listed() -> None:
    # 8aecb5 line 1970 (PDF Python, 385 public types in the sealed facts): the Lane L edit made the live
    # "277 public types are organized by module below" read 385 over the 284 type rows that follow it --
    # a total said to be organized below is held to those rows, so the sealed line does not verify
    pdf = ["`PdfFileEditor` provides a boolean-returning facade for file-based concatenate, extract, insert,",
           "and delete workflows. 385 public types are organized by module below.", ""]
    table = ["| Type | Description |", "|---|---|"]
    sealed = pdf + table + [f"| `T{i}` | A type. |" for i in range(284)]
    assert auditor.class_provenance("K05", sealed, 2, _types(354, 31)) is None
    complete = pdf + table + [f"| `T{i}` | A type. |" for i in range(385)]
    assert auditor.class_provenance("K05", complete, 2, _types(354, 31))
    assert auditor.class_provenance("K05", complete, 2, _types(354, 30)) is None  # a different computation
    # BL-093: the sentence listed_type_count v2 writes over the same 284 rows verifies
    fixed = [pdf[0], "and delete workflows. 385 public types — 284 of them organized by module below.", ""]
    assert auditor.class_provenance("K05", fixed + table + [f"| `T{i}` | A type. |" for i in range(284)], 2, _types(354, 31))
    # e48a84 line 271 (Cells Rust Lane R, 115 type facts): a renderer line with no fact value of its own
    rust = ["The public API has 115 types."]
    renderer = {"source": "renderer"}
    assert auditor.keep_reason("R", rust[0], renderer, _types(100, 15), rust, 1) is None
    assert auditor.keep_reason("R", rust[0], renderer, _types(100, 15)) == "no fact value in the line"
    # 802069 line 266 (Cells C++: 195 types, 189 table rows follow)
    cpp = ["The full public surface — 195 public types — has 189 of them listed below", "",
           "| Type | Description |", "|---|---|", *[f"| `T{i}` | A type. |" for i in range(189)], "## Next"]
    assert auditor.class_provenance("K05", cpp, 1, _types(168, 27))
    short = cpp[:-10] + ["## Next"]  # 180 rows follow: "189 of them listed" is false
    assert auditor.class_provenance("K05", short, 1, _types(168, 27)) is None
    # a kind no fact counts stays kept
    assert auditor.class_provenance("K05", ["It defines 12 public interfaces."], 1, _types(10, 2)) is None


def test_a_registered_k05_row_is_refuted_before_any_provenance() -> None:
    """Words .NET "618 public types": the sealed facts still count 618, the source has 615 (#if CPLUSPLUS,
    BL-065); the register row keeps it whatever the computation says."""
    text = "# Aspose.Words FOSS for .NET\n\nThe full surface totals 618 public types.\n"
    facts = _types(600, 18)
    register = [{"repository": "o/r", "status": "OPEN", "quote": "The full surface totals 618 public types"}]
    edit = {"source": "edit", "detector": "stale_type_count", "fact_ids": ("public_symbol:pkg.t0",)}
    rederived = auditor.Rederived(text, ({"source": "maintainer"}, {"source": "maintainer"}, edit))
    derived = auditor.derivation("L", text, facts, rederived, repository="o/r", register=register)
    assert derived.kept[3] == "findings register" and 3 not in derived.clearable
    derived = auditor.derivation("L", text, facts, rederived, repository="o/r")  # negative control: no row
    assert 3 in derived.clearable and derived.provenance[3].startswith("K05 verified: 618 public types")


def test_the_audit_packet_carries_each_counts_provenance() -> None:
    """The model sees the computation it is asked to check: kinds and source roots of the counted facts
    (Words Python: 189, all in aspose/words_foss, none in ApiExamples/)."""
    from repo_presenter.readme.review.sectionwise import computed_counts

    counts = computed_counts(_words_python())
    assert (counts["public_types"], counts["public_classes"], counts["public_enums"]) == (189, 166, 23)
    assert counts["counted_by_source_root"] == {"aspose/words_foss": 189}
