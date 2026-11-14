"""Classify every blocking Lane R finding into concrete, reusable classes (BL-085).

Inputs (zero provider calls):
* ``hosted_lane_r.jsonl`` (``extract_hosted.py``): the final blocking findings of every hosted Lane R
  present run since 2026-11-12, with the run's repair lines;
* ``recertify_lane_r.json``: ``python -m repo_presenter.recertify --all --json --remote origin``
  filtered to Lane R (the latest seal of every Lane R cell, re-judged under current code).

Output: ``classified.json`` (one row per finding: source, cell, rule, class, origin, verdict,
repair outcome) and a printed Pareto. A finding's *final* set is what blocked the run: the
deterministic ``blocking`` lines when no LLM review was made, the review's ``finding`` lines when it
returned REJECT, the JobError otherwise.

Class names are the BL-085 vocabulary (docs/investigations/2026-11-13-lane-r-not-progressing.md);
``origin`` is one of renderer_from_fact, authored_unit, authored_type_row, inherited_unit,
planned_example, lane_l_correction, job_error; ``verdict`` one of true_defect_ours,
true_defect_maintainer, false_positive_check, mixed.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (class, regex on the finding text, origin, verdict). First match wins; order matters.
CLASSES: list[tuple[str, str, str, str]] = [
    ("JOB_OUTPUT_TRUNCATED", r"output truncated at the manifest's max_output_tokens", "job_error", "true_defect_ours"),
    ("INTERNAL_WORDING_TYPE_ROW", r"internal evidence or analysis wording: '\| `[^`]+` \| .*is a public symbol", "authored_type_row", "true_defect_ours"),
    ("INTERNAL_WORDING_PROSE", r"internal evidence or analysis wording", "authored_unit", "true_defect_ours"),
    ("VISIBLE_BUDGET_EXCEEDED", r"visible lines of \d+ exceed the visible budget", "authored_unit", "true_defect_ours"),
    ("KEPT_TEXT_FORMATTING", r"is not in title case|ends with a colon but nothing follows", "inherited_unit", "true_defect_maintainer"),
    ("SECTION_FIT_RESOURCE_IN_SCOPE", r"section fit: Scope and Limitations prints a resource link", "inherited_unit", "true_defect_ours"),
    ("SECTION_FIT_LICENSE_IN_SCOPE", r"section fit: Scope and Limitations states the project's license", "authored_unit", "mixed"),
    ("SUPERSEDED_SUBSTANCE_LOST", r"is SUPERSEDE_REDUNDANT, but the README does not state", "inherited_unit", "true_defect_ours"),
    ("LIVE_ITEM_LOST", r"which the published README prints and this candidate loses|live README content lost", "inherited_unit", "true_defect_ours"),
    ("SUPERSEDED_UNCITED", r"superseded into this section by reconciliation, so a unit must cite it", "inherited_unit", "true_defect_ours"),
    ("UNPROVEN_SOURCE_BUILD", r"the source build of a project whose build no run proved", "inherited_unit", "true_defect_maintainer"),
    ("NEVER_THROWN_CLAIMED_THROWN", r"is thrown, but implementation:never_thrown", "authored_unit", "true_defect_ours"),
    ("RETURNS_CLAIMED_NOT_IMPLEMENTED", r"throws a not-implemented exception, but its body was read and holds no throw", "authored_unit", "true_defect_ours"),
    ("STUB_CLAIMED_WORKING", r"reachable only through a stub|states the instance only throws|as working \(.*only throws", "authored_unit", "true_defect_ours"),
    ("KIND_WORD_MISREAD_LIST", r"calls `[^`]+\.[^`]+` a (method|constructor|field|property) \(", "authored_unit", "mixed"),
    ("KIND_WORD_TYPE_KIND", r"calls `[^`.]+` a (class|enum|interface|struct) \(", "authored_unit", "true_defect_ours"),
    ("MEMBER_NOT_OF_TYPE", r"as a property of `|names `[^`]+`, a member of|which no fact states \(no member", "authored_unit", "true_defect_ours"),
    ("WRONG_BASE_TYPE", r"derives from `", "authored_unit", "true_defect_ours"),
    ("SAMPLES_REFERENCE_MISSTATED", r"samples use the published package", "authored_unit", "true_defect_ours"),
    ("TYPE_COUNT_VS_LISTED", r"count of public types is listed", "inherited_unit", "true_defect_maintainer"),
    ("FORMAT_WITHOUT_FACT", r"lists the format\(s\) .* but no SUPPORTED format fact", "authored_unit", "true_defect_ours"),
    ("LLM_UNSUPPORTED_CLAIM", r"\[llm:factuality\]|\[unsupported_claim\]", "authored_unit", "true_defect_ours"),
    ("REGISTER_ROW_REPRINTED", r"open finding \(confirmed (false|misleading|unsupported) claim", "mixed", "true_defect_ours"),
]

REPAIR_REASONS = [
    ("NOOP_REVISION", r"matches the causal stage's own output unchanged"),
    ("FACTS_DEFECT_UNREACHABLE", r"facts defect: .* is printed by the renderer from fact"),
    ("SUPERSEDE_TARGET_REFUSED", r"still SUPERSEDE_REDUNDANT"),
    ("OUT_OF_UNIT_EDIT", r"is not the finding's own unit"),
    ("NOT_A_FACT_VALUE", r"identifiers that are not accepted fact values"),
    ("CHANGES_LEDGER_REFUSED", r"change R\d+ claims"),
    ("NO_STORED_DISPOSITION", r"no stored disposition of an inherited unit is named"),
    ("STILL_FAILS_AFTER_REVISION", r"still fails on this revision"),
    ("CITED_REGISTER_FACT", r"is a confirmed false claim \(findings register\), not SUPPORTED"),
    ("RATIONALE_REFUSED", r"dispositions\[\d+\]\.rationale"),
    ("ESCALATED_TO_PLAN", r"escalated once to a plan-level repair"),
]


def classify(text: str) -> tuple[str, str, str]:
    for name, pattern, origin, verdict in CLASSES:
        if re.search(pattern, text):
            return name, origin, verdict
    return "UNCLASSIFIED", "unknown", "unknown"


def rule_of(text: str) -> str:
    if m := re.match(r"(?:blocking |REVIEW:)?(BC-\d+)", text):
        return m.group(1)
    if m := re.match(r"finding (\S+) \[([^\]]+)\]", text):
        return m.group(2)
    if text.startswith("REVIEW:"):
        return text.split(":", 2)[1]
    if "JobError" in text:
        return "JobError"
    return "?"


def repair_outcomes(repairs: list[str]) -> dict[str, list[str]]:
    """rule -> the repair outcomes recorded for it in this run (repaired / reason class)."""
    found: dict[str, list[str]] = collections.defaultdict(list)
    for line in repairs:
        m = re.match(r"repair (repaired|unrepairable|escalated) ([^:]+):", line)
        if not m:
            continue
        outcome, keys = m.groups()
        reason = outcome
        if outcome != "repaired":
            reason = next((name for name, pat in REPAIR_REASONS if re.search(pat, line)), outcome)
        for key in keys.split("+"):
            found[re.sub(r":\d+$", "", key)].append(reason)
    return found


def hosted_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        run = json.loads(line)
        failure = " ".join(run["failure"])
        if not failure:
            continue  # sealed (Cells Go 43473811437, Email Python 43525320899)
        if "JobError" in failure:
            final = [f for f in run["failure"] if "JobError" in f][:1]
        elif "independent review returned REJECT" in failure:
            final = run["finding"]
        else:
            final = run["blocking"]
        repairs = repair_outcomes(run["repair"])
        for text in dict.fromkeys(final):
            cls, origin, verdict = classify(text)
            rule = rule_of(text)
            if cls == "REGISTER_ROW_REPRINTED":
                origin = "renderer_from_fact" if any(
                    "facts defect" in r and _quote(text)[:40] in r for r in run["repair"]
                ) else "authored_or_inherited"
            key = "claim_contradiction" if rule == "claim_contradiction" else rule
            outcome = repairs.get(key) or (repairs.get("BC-14") if key == "claim_contradiction" else None)
            rows.append({
                "source": "hosted", "run": run["run"], "main_sha": (run["main_sha"] or "")[:7],
                "repository": run["repository"], "rule": rule, "class": cls, "origin": origin,
                "verdict": verdict, "repair": sorted(set(outcome or ["not_attempted"])), "text": text[:300],
            })
    return rows


def _quote(text: str) -> str:
    m = re.search(r"claim: (.*?)\) still printed", text)
    return m.group(1) if m else text


def recert_rows(path: Path) -> list[dict]:
    rows = []
    for rec in json.loads(path.read_text(encoding="utf-8")):
        if rec["lane"] != "R" or rec["outcome"] == "RECERTIFIED":
            continue
        for text in rec["details"]:
            if text.startswith("REVIEW:"):
                continue  # the same rule's finding is already counted under its BC id
            cls, origin, verdict = classify(text)
            rows.append({
                "source": "recertify", "run": "", "main_sha": "", "repository": rec["repository"],
                "rule": rule_of(text), "class": cls, "origin": origin, "verdict": verdict,
                "repair": ["n/a (zero-call re-certification)"], "text": text[:300],
            })
    return rows


def pareto(rows: list[dict]) -> list[tuple[str, int, int, list[str]]]:
    by_class: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        by_class[row["class"]].append(row)
    table = [
        (name, len(found), len({r["repository"] for r in found}),
         sorted({r["repository"].split("/")[1] for r in found}))
        for name, found in by_class.items()
    ]
    return sorted(table, key=lambda t: (-t[2], -t[1]))


def new_class_rate(rows: list[dict]) -> tuple[int, int, list[str]]:
    """Over every re-run of a cell (its second and later hosted runs): the classes that blocked it,
    and how many of them that cell had never been blocked by before (whack-a-mole)."""
    runs: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row in rows:
        if row["source"] == "hosted":
            runs[(row["repository"], row["run"])].add(row["class"])
    by_cell: dict[str, list[tuple[str, set[str]]]] = collections.defaultdict(list)
    for (repository, run), classes in sorted(runs.items(), key=lambda item: item[0][1]):
        by_cell[repository].append((run, classes))
    total = new = 0
    lines = []
    for repository, sequence in sorted(by_cell.items()):
        seen: set[str] = set()
        for index, (run, classes) in enumerate(sequence):
            fresh = classes - seen
            if index:
                total += len(classes)
                new += len(fresh)
            lines.append(f"{repository.split('/')[1]} {run}: {', '.join(sorted(classes))}"
                         + (f"  [new: {', '.join(sorted(fresh)) or '-'}]" if index else ""))
            seen |= classes
    return total, new, lines


def main() -> int:
    hosted = hosted_rows(HERE / "hosted_lane_r.jsonl")
    recert = recert_rows(HERE / "recertify_lane_r.json")
    total, new, lines = new_class_rate(hosted)
    print("\n".join(lines))
    print(f"== re-run rounds: {total} blocking classes, {new} never seen before in that cell")
    (HERE / "classified.json").write_text(json.dumps(hosted + recert, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for label, rows in (("hosted final findings", hosted), ("re-certification of the latest seals", recert)):
        print(f"== {label}: {len(rows)} findings")
        for name, count, cells, names in pareto(rows):
            print(f"{count:4d} {cells:3d} {name:32s} {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
