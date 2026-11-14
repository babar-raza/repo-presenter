"""BL-013: the root causes of hosted M9 round 43445578226 (recall 0.238, false-flag 0.625), each pinned by
a test built from the round's real failing shape. Zero calls: the reviewer is never invoked.

* 11 of 16 misses were D/D14 seeds the operators append to the first paragraph -- the ``# Title`` line --
  which the reviewer never showed (headings are markup).
* 2 of 16 were class A counts caught on the right sentence but written one line early (the count sat on
  the second line of a wrapped sentence; the finding was written at the quote's first line).
* the flags on clean controls were on unchanged maintainer text (Lane L), on lines the renderer derived
  from the pinned facts (Lane R), or on seals that no longer re-certify; none was adjudicated.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from repo_presenter.acceptance.audit.score import Finding as ScoreFinding, seeded_recall
from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, seed_defect
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.sectionwise import plan_units

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auditor = _load("run_m9_auditor")
writer = _load("run_acceptance_writer")

LIVE = (
    "# Aspose.Widget FOSS for Python\n"
    "\n"
    "Aspose.Widget FOSS reads and writes widget files. The classes below cover the full supported\n"
    "public API surface — 190 public types organized into one module.\n"
    "\n"
    "## Classes\n"
    "\n"
    "| Class | Description |\n"
    "|---|---|\n"
    "| `Widget` | The main widget object. |\n"
    "| `WidgetOptions` | Options for saving a widget. |\n"
)


def _llm(quote: str, kind: str = "unsupported_claim") -> Finding:
    return Finding(rule="llm_review", source="llm", message=f"{kind} here", claim_kind=kind, quote=quote)


# --- recall: the title line is reviewable in the audit ----------------------------------------------------


def test_a_seed_written_onto_the_title_line_is_shown_to_the_auditor_and_only_to_the_auditor():
    for operator in ("add_promotional_filler", "inject_unsupported_claim"):
        seeded = seed_defect("c", LIVE, operator)
        assert seeded.record.line == 1 and seeded.seeded_readme.splitlines()[0].startswith("# ")
        before = {n for u in plan_units(seeded.seeded_readme, rendered=False) for n in u.lines}
        audit = {n for u in plan_units(seeded.seeded_readme, rendered=False, headings=True) for n in u.lines}
        assert 1 not in before  # the round-43445578226 blind spot, kept for every production review
        assert 1 in audit and audit - before == {1, 6}  # the title and the "## Classes" heading


# --- the join: a finding is written at every line of a wrapped sentence -----------------------------------


def test_a_count_on_the_second_line_of_a_wrapped_sentence_is_caught_at_the_seeded_line():
    seeded = seed_defect("c", LIVE, "count_mismatch")
    assert seeded.record.line == 4  # the count, on the sentence's second line
    rows = seeded.seeded_readme.splitlines()
    quote = "\n".join(rows[2:4])  # what claim_contradiction_rule / the reviewer quote: the whole sentence
    findings = auditor.findings_for("c", seeded.seeded_readme, [_llm(quote, "contradiction")])
    assert [r["line"] for r in findings] == [3, 4] and all(r["source"] == "llm" for r in findings)
    manifest = [{"candidate_id": "c", **seeded.record.as_dict()}]
    caught = seeded_recall([ScoreFinding(f["candidate_id"], f["claim"], f["verdict"], f["path"], f["line"])
                            for f in findings], manifest)
    assert caught.matched == 1  # was 0: the old writer put the finding at line 3 only


def test_a_wide_quote_is_written_at_its_first_line_only_so_it_cannot_cover_a_seed_by_accident():
    text = "\n".join(f"line {n}" for n in range(1, 11)) + "\n"
    rows = auditor.findings_for("c", text, [_llm("\n".join(f"line {n}" for n in range(2, 8)))])
    assert [r["line"] for r in rows] == [2]


def test_a_quote_whose_first_line_is_common_is_located_by_the_whole_quote():
    text = "```python\nprint(1)\n```\n\ntext\n\n```python\nprint(2)\n```\n"
    assert auditor.quote_lines("```python\nprint(2)\n```", text.splitlines()) == (7, 8, 9)


# --- Lane L: the audit judges what the candidate changed, blind to which change is genuine ----------------


def test_a_lane_l_case_is_scoped_to_the_lines_that_differ_from_the_live_readme_with_nothing_from_its_seal():
    seeded = seed_defect("c", LIVE, "add_promotional_filler").seeded_readme
    source = SimpleNamespace(original=LIVE, validation={"residuals": ["seal-only"], "applied_edits": ["x"]})
    validation, changed = auditor.audit_scope("L", source, seeded)
    assert validation == {"lane": "L"} and changed == frozenset({1})
    assert auditor.audit_scope("R", source, seeded) == (source.validation, None)


def test_the_deterministic_rule_keeps_only_lane_l_findings_on_a_changed_line():
    rows = LIVE.splitlines()
    on_changed = SimpleNamespace(quote=rows[2] + "\n" + rows[3])
    on_unchanged = SimpleNamespace(quote=rows[9])
    kept = auditor.scoped_deterministic([on_changed, on_unchanged], LIVE, frozenset({4}))
    assert kept == (on_changed,)
    assert auditor.scoped_deterministic([on_changed, on_unchanged], LIVE, None) == (on_changed, on_unchanged)


# --- the writer's deterministic adjudication --------------------------------------------------------------


def _flag(line: int, case: str = "c0") -> dict:
    return {"candidate_id": case, "claim": "[unsupported_claim] x", "verdict": "unverifiable", "path": f"{case}.md",
            "line": line, "source": "llm"}


def _case(sealed: str = LIVE, derived=frozenset({10, 11}), certified: bool = True, lane: str = "R"):
    return writer.CaseEvidence(lane=lane, facts=None, sealed=sealed, derived=frozenset(derived), certified=certified)


def test_a_flag_the_claim_detector_proves_is_confirmed_and_one_on_a_derived_line_of_the_unmodified_seal_is_refuted():
    adjudications = writer.deterministic_adjudications(
        [_flag(4), _flag(10), _flag(3)], {"c0": LIVE}, {"c0": _case()},
        contradicted_by=lambda text, facts: frozenset({4}),
    )
    assert [(a["line"], a["adjudication"], a["rule"]) for a in adjudications] == [
        (4, "confirmed", "claim_detector"), (10, "refuted", "derived_from_pinned_facts"),
    ]  # line 3 is author-written prose: no deterministic check decides it, so it stays unadjudicated


def test_no_refutation_for_a_modified_copy_a_seal_that_does_not_recertify_or_a_contradicted_line():
    none = frozenset()
    seeded = LIVE.replace("main widget", "secondary widget")
    assert writer.deterministic_adjudications([_flag(10)], {"c0": seeded}, {"c0": _case()},
                                              contradicted_by=lambda t, f: none) == []
    assert writer.deterministic_adjudications([_flag(10)], {"c0": LIVE}, {"c0": _case(certified=False)},
                                              contradicted_by=lambda t, f: none) == []
    confirmed = writer.deterministic_adjudications([_flag(10)], {"c0": LIVE}, {"c0": _case()},
                                                   contradicted_by=lambda t, f: frozenset({10}))
    assert [a["adjudication"] for a in confirmed] == ["confirmed"]


def test_a_confirmed_verdict_is_never_overturned_by_a_later_refutation():
    index = writer._adjudication_index([
        {"candidate_id": "c0", "line": 4, "adjudication": "confirmed"},
        {"candidate_id": "c0", "line": 4, "adjudication": "refuted"},
    ])
    assert index == {("c0", 4): "confirmed"}


def test_lane_r_derived_lines_are_the_renderer_printed_ones_and_lane_l_needs_an_evidenced_zero_call_run(tmp_path):
    from repo_presenter.core.facts import FactsDocument

    facts = FactsDocument(repository="o/r", source_revision="a" * 40, facts=())
    rendered = writer.derived_lines("R", LIVE, facts)
    assert 3 not in rendered and 4 not in rendered  # author-written prose
    assert {1, 6, 8, 9, 10, 11} <= rendered  # headings and the table the renderer printed

    corrected = LIVE.replace("190 public types", "191 public types")
    record = {"stability": {"deterministic": True, "provider_calls": 0},
              "edits": [{"evidence": [{"fact_id": "count:public_types", "status": "SUPPORTED"}]}]}
    (tmp_path / "corrections.json").write_text(json.dumps(record), encoding="utf-8")
    assert writer.derived_lines("L", corrected, facts, tmp_path, LIVE) == frozenset({4})
    record["edits"][0]["evidence"][0]["status"] = "UNVERIFIED"
    (tmp_path / "corrections.json").write_text(json.dumps(record), encoding="utf-8")
    assert writer.derived_lines("L", corrected, facts, tmp_path, LIVE) == frozenset()
    record["edits"][0]["evidence"][0]["status"] = "SUPPORTED"
    record["stability"]["provider_calls"] = 2
    (tmp_path / "corrections.json").write_text(json.dumps(record), encoding="utf-8")
    assert writer.derived_lines("L", corrected, facts, tmp_path, LIVE) == frozenset()


def test_the_audit_packet_carries_the_facts_computed_type_counts_and_production_packets_do_not():
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.readme.review.sectionwise import unit_packet

    facts = FactsDocument(repository="o/r", source_revision="a" * 40, facts=())
    units = plan_units(LIVE, rendered=False)
    common = dict(units=units, repository="o/r", candidate_readme=LIVE, original_readme=LIVE, facts=facts,
                  plan={"sections": []})
    assert "computed_counts" not in unit_packet(units[0], **common)["review_scope"]
    counts = unit_packet(units[0], **common, audit=True)["review_scope"]["computed_counts"]
    assert (counts["public_types"], counts["public_classes"]) == (0, 0)


def test_a_control_that_does_not_recertify_is_reported_and_left_out_of_the_false_flag_rate():
    seeded = [{"candidate_id": f"s{i}", "shape": "A", "line": 5} for i in range(10)]
    clean = [{"candidate_id": f"c{i}", "shape": CLEAN_SHAPE} for i in range(10)]
    manifest = seeded + clean
    case_index = [{"case_id": m["candidate_id"], "repository": f"o/{m['candidate_id']}", "lane": "R",
                   "revision": "r"} for m in manifest]
    recert = {(c["repository"], "R"): ("r", c["case_id"] != "c0") for c in case_index}
    findings = [{"candidate_id": m["candidate_id"], "claim": "x", "verdict": "false", "path": "p", "line": 5}
                for m in seeded] + [_flag(3, "c0")]
    doc = writer.build_records_document("1", case_index, manifest, findings, recert)
    assert doc["gates"]["controls_not_recertified"] == ["c0"]
    assert doc["gates"]["false_flag_rate"] == {"matched": 0, "total": 9, "rate": 0.0}
    assert doc["batch_passed"] is True
    assert not next(r for r in doc["records"] if r["case_id"] == "c0")["audit_passed"]  # flagged and not validated
    recert[("o/c0", "R")] = ("r", True)  # the same flag on a re-certifying control counts against the auditor
    doc = writer.build_records_document("1", case_index, manifest, findings, recert)
    assert doc["gates"]["false_flag_rate"]["matched"] == 1 and doc["gates"]["controls_not_recertified"] == []


# --- BL-013 round 2 (hosted round 43559491132): derivation, the audit-scope note, evidenced statuses --------


def test_a_deterministic_owned_line_the_rederivation_reproduces_clears_a_model_flag_and_one_it_does_not_is_flagged():
    seeded = seed_defect("c", LIVE, "inject_unsupported_claim").seeded_readme  # onto the "# Title" line
    derived = auditor.derivation("L", seeded, None, LIVE)  # Lane L: every line is the engine's or the live one
    assert derived.underived == frozenset({1}) and 4 in derived.derivable
    rows = [dict(_flag(4, "c"), located=True), dict(_flag(1, "c"), located=True)]
    out = auditor.apply_derivation("c", seeded, rows, derived)
    assert [(r["line"], r["verdict"], r["source"]) for r in out] == [
        (4, "supported", "llm"), (1, "unverifiable", "llm"), (1, "unverifiable", "deterministic")]
    assert out[0]["cleared_by"] == "derivation"
    assert auditor.apply_derivation("c", seeded, rows, None) == rows  # no re-derivation: nothing changes


def test_lane_r_compares_only_the_lines_the_renderer_prints_never_an_authored_line():
    from repo_presenter.core.facts import FactsDocument

    facts = FactsDocument(repository="o/r", source_revision="a" * 40, facts=())
    authored_edit = LIVE.replace("reads and writes widget files", "reads, writes and repairs widget files")
    derived = auditor.derivation("R", authored_edit, facts, LIVE)
    assert derived.underived == frozenset() and 3 not in derived.derivable  # prose stays the model's
    title = seed_defect("c", LIVE, "add_promotional_filler").seeded_readme
    assert auditor.derivation("R", title, facts, LIVE).underived == frozenset({1})  # the renderer's title line


def test_a_failed_rederivation_is_no_derivation(tmp_path):
    seal = SimpleNamespace(bundle=str(tmp_path), lane="L", repository="o/r", revision="r")
    assert auditor.case_derivation(seal, LIVE, tmp_path, fetch=lambda *a: SimpleNamespace(tree_paths=())) is None


def test_the_audit_packet_tells_the_model_headings_are_shown_and_production_packets_do_not():
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.readme.review.sectionwise import AUDIT_SCOPE_NOTE, unit_packet

    facts = FactsDocument(repository="o/r", source_revision="a" * 40, facts=())
    units = plan_units(LIVE, rendered=False, headings=True)
    common = dict(units=units, repository="o/r", candidate_readme=LIVE, original_readme=LIVE, facts=facts,
                  plan={"sections": []})
    assert "audit_scope" not in unit_packet(units[0], **common)["review_scope"]
    assert unit_packet(units[0], **common, audit=True)["review_scope"]["audit_scope"] == AUDIT_SCOPE_NOTE


def test_a_structure_fix_citing_the_readme_text_still_derives_the_lane_l_lines(tmp_path):
    from repo_presenter.core.facts import FactsDocument

    facts = FactsDocument(repository="o/r", source_revision="a" * 40, facts=())
    corrected = LIVE.replace("190 public types", "191 public types")
    record = {"stability": {"deterministic": True, "provider_calls": 0}, "edits": [
        {"evidence": [{"fact_id": None, "status": "README_TEXT", "kind": "readme_structure"}]},
        {"evidence": [{"fact_id": "count:public_types", "status": "SUPPORTED"}]}]}
    (tmp_path / "corrections.json").write_text(json.dumps(record), encoding="utf-8")
    assert writer.derived_lines("L", corrected, facts, tmp_path, LIVE) == frozenset({4})
    record["edits"][0]["evidence"][0]["status"] = "ABSENT"
    (tmp_path / "corrections.json").write_text(json.dumps(record), encoding="utf-8")
    assert writer.derived_lines("L", corrected, facts, tmp_path, LIVE) == frozenset()
