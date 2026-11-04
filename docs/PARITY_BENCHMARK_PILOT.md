# Pilot parity benchmark — repo-presenter vs. aspose.org — 2026-11-04

Resolves TC-006. Read-only analysis of committed and durable-state-backend candidates against
the local `aspose.org` sibling checkout (confirmed present on disk:
`C:/Users/babar/Documents/GitHub/aspose.org/reports/repo-presenter-regen-full/`). Does not
touch, resume, or ratify the 2026-10-31 sweep pause — see `project/taskcards/TC-006.yaml`.

**Method**: `python scripts/parity_benchmark.py <candidate> <reference>` — deterministic,
reproducible structural analysis (heading list, code-fence count, link count, line count,
presence of required sections, duplicate-H1 detection). Re-running it against the same two
files produces the same numbers; this is not a subjective judgment.

## 2026-11-04 correction (P0 follow-up directive section 4)

The prior version of this document covered 1 of 3 pilot repositories and called that coverage
"complete." It was not: a benchmark that measured one of three named pilots is a **partial
measurement**, and this document's own completion marker overstated it. This revision covers
all three named repositories — two now measured (Imaging-.NET's durable-state bundle was
exported via `bundle_store.export_bundle`, which this pass actually ran rather than flagging as
unattempted), one confirmed to have no sealed candidate to measure at all. The explicit verdict
below is **NOT_PASSED**: a completed benchmark and a passing parity verdict are different
things, and this repository has not reached the second one. Downstream acceptance (TC-007
calibration, TC-011 portfolio delivery) must not read this card's ACCEPTED status as "parity
achieved" — it means "the measurement was honestly done," nothing more.

## Coverage: 3 of 3 pilot repositories named in the 2026-10-31 decision log

| Repository | Lane R | Lane L | Source |
|---|---|---|---|
| Aspose.3D-FOSS-for-.NET | measured | not sealed (no `lane-l/CURRENT` committed) | `candidates/` (committed) |
| Aspose.Imaging-FOSS-for-.NET | measured | measured | durable-state bundle ref, exported this pass |
| Aspose.Words-FOSS-for-.NET | **no candidate exists** | **no candidate exists** | durable-state record: `FAILED_INTERNAL` both lanes |

Words-.NET cannot be benchmarked against anything because this repository's own pipeline has
never produced a sealed candidate for it on either lane — both lanes' most recent durable-state
record is `FAILED_INTERNAL`. That is itself a real, material finding for this card, not a gap in
the benchmark: there is no parity question to answer until Words-.NET has a candidate at all.

## Aspose.3D-FOSS-for-.NET (Lane R): candidate vs. reference

| Metric | Candidate (sealed 2026-10-26) | aspose.org reference | Delta |
|---|---|---|---|
| Line count | 837 | 631 | **+206 (longer)** |
| Heading count | 25 | 25 | 0 |
| Code fences | 2 | 11 | **-9** |
| Links | 9 | 26 | **-17** |
| H1 count (duplicate-opening check) | 1 | 1 | 0 |
| Has Quick Start / Minimal Example | **No** | Yes | missing |
| Has At a Glance | Yes | Yes | match |
| Has Installation | Yes | Yes | match |

**Verdict: FAIL.** Missing Quick Start, a fifth as many code fences, a third as many links.

## Aspose.Imaging-FOSS-for-.NET (Lane R): candidate vs. reference

| Metric | Candidate | aspose.org reference | Delta |
|---|---|---|---|
| Line count | 255 | 307 | -52 |
| Heading count | 19 | 20 | -1 |
| Code fences | 9 | 8 | +1 |
| Links | 27 | 24 | +3 |
| H1 count | 1 | 1 | 0 |
| Has Quick Start / Minimal Example | Yes | Yes | match |
| Has At a Glance | Yes | Yes | match |
| Has Installation | Yes | Yes | match |

**Verdict: PASS (structural).** Every required section present, comparable code-fence and link
density, no duplicate H1. One real heading is absent (reference has 20 H2 headings, candidate
19; the candidate's own `h2_headings` list is otherwise identical in order and name) — worth a
closer read, not a failure by this benchmark's own bar.

## Aspose.Imaging-FOSS-for-.NET (Lane L): candidate vs. reference

| Metric | Candidate | aspose.org reference | Delta |
|---|---|---|---|
| Line count | 306 | 307 | -1 |
| Heading count | 20 | 20 | 0 |
| Code fences | 8 | 8 | 0 |
| Links | 24 | 24 | 0 |
| H1 count | 1 | 1 | 0 |
| Has Quick Start / Minimal Example | Yes | Yes | match |
| Has At a Glance | Yes | Yes | match |
| Has Installation | Yes | Yes | match |

**Verdict: PASS (structural).** Near byte-for-byte structural match against the reference —
unsurprising given Lane L's own design (minimal, evidenced corrections to an already-live
README that was presumably already close to the aspose.org reference's own structure), but a
genuine, measured result, not assumed.

## Aspose.Words-FOSS-for-.NET: no candidate on either lane

**Verdict: N/A (no candidate to measure).** Not scored as PASS or FAIL; scored as a missing
prerequisite. Both lanes' most recent durable-state record is `FAILED_INTERNAL`.

## What this confirms, and what it corrects

**Confirmed, independently, by direct measurement**: 3D-.NET's Lane R candidate is missing a
Quick Start section and is far below the reference on code-fence and link density, consistent
with the 2026-10-31 decision log's own finding. Imaging-.NET's candidate, on both lanes,
structurally matches the reference closely — the pilot set is not uniformly behind; results
vary by repository and lane, which is itself evidence against treating "parity" as one
portfolio-wide number.

**Corrects an earlier, unconfirmed claim**: the 2026-11-03 independent audit's "double opening"
claim for the 3D-.NET candidate does **not** hold up under direct measurement — `h1_count` is
exactly 1 for both the candidate and the reference. The heading-structure observation (no
distinct Quick Start heading) was correct; the duplicate-H1 claim was not.

## What this does NOT establish

This is structural parity only — heading presence, counts, link density. It does not assess
factual accuracy, API coverage correctness, retained live-README content, or prose quality and
readability, which the 2026-11-04 directive separately asks for (factual correctness, API
coverage, documented features, installation, executable examples, retained live content,
structure, navigation, diagrams, readability, coherence, usability) and which remains open —
a structural PASS here is a necessary, not sufficient, condition for the directive's full bar.
No code-example execution or factual cross-check was performed in this pass.

## Explicit aggregate verdict

PARITY_VERDICT: NOT_PASSED
PILOTS_MEASURED: 2/3 (3D-.NET Lane R, Imaging-.NET Lane R+L; Words-.NET has no candidate)
PILOTS_STRUCTURALLY_PASSING: 2/3 lane-candidates PASS (Imaging-.NET R, Imaging-.NET L), 1/3 FAIL
  (3D-.NET R), 1/3 N/A (Words-.NET, no candidate on either lane)
REASON_NOT_PASSED: 3D-.NET Lane R fails on Quick Start/code-fence/link density; Words-.NET has
  no sealed candidate at all; factual-correctness and prose-quality comparison (directive R11)
  was not performed for any repository.

PARITY_BENCHMARK_COMPLETE: 2026-11-04 (3 of 3 pilot repositories addressed; see coverage table)
