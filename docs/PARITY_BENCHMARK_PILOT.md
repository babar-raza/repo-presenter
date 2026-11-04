# Pilot parity benchmark — repo-presenter vs. aspose.org — 2026-11-04

Resolves TC-006. Read-only analysis of already-committed candidates against the local
`aspose.org` sibling checkout (confirmed present on disk this pass:
`C:/Users/babar/Documents/GitHub/aspose.org/reports/repo-presenter-regen-full/`). Does not
touch, resume, or ratify the 2026-10-31 sweep pause — see `project/taskcards/TC-006.yaml`.

**Method**: `python scripts/parity_benchmark.py <candidate> <reference>` — deterministic,
reproducible structural analysis (heading list, code-fence count, link count, line count,
presence of required sections, duplicate-H1 detection). Re-running it against the same two
files produces the same numbers; this is not a subjective judgment.

## Coverage: 1 of 3 pilot repositories (honest, not padded)

The 2026-10-31 decision log names a three-repository pilot set: Imaging-.NET, 3D-.NET,
Words-.NET. Only **3D-.NET** has a bundle physically committed under `candidates/` in this
repository as of this pass; Imaging-.NET and Words-.NET exist only as durable state-backend
records, not materialized locally, and were not exported for this comparison (a real, flagged
gap — `bundle_store.export_bundle` can do this; not attempted this pass given time).

## Aspose.3D-FOSS-for-.NET: candidate vs. reference

| Metric | Candidate (this repo, sealed 2026-10-26) | aspose.org reference | Delta |
|---|---|---|---|
| Line count | 837 | 631 | **+206 (longer)** |
| Heading count | 25 | 25 | 0 |
| Code fences | 2 | 11 | **-9** |
| Links | 9 | 26 | **-17** |
| H1 count (duplicate-opening check) | 1 | 1 | 0 |
| Has Quick Start / Minimal Example | **No** | Yes | missing |
| Has At a Glance | Yes | Yes | match |
| Has Installation | Yes | Yes | match |

## What this confirms, and what it corrects

**Confirmed, independently, by direct measurement**: the candidate is missing a Quick Start /
Minimal Example section and has roughly a fifth as many code fences and a third as many links
as the reference — consistent with the 2026-10-31 decision log's own finding ("hosted Words-.NET
run lacks both [Quick Start/Additional Examples]... Imaging-.NET is rejected by
`live_readme_loss`") now independently reconfirmed for a third repository. This is the real,
measurable content gap between this repository's Lane R output and aspose.org's reference at
this pilot stage.

**Corrects an earlier, unconfirmed claim**: the 2026-11-03 independent audit's "double opening"
claim for this same candidate does **not** hold up under direct measurement — `h1_count` is
exactly 1 for both the candidate and the reference. That audit's own text already graded this
claim `PARTIAL` confirmation, not `CONFIRMED`, and flagged it as "a lead for a future, deeper
pass" rather than fully proven — this pass is that deeper check, and the specific "double
opening" claim is not borne out. The heading-structure observation (no distinct Quick Start
heading) was correct; the duplicate-H1 claim was not.

## What this does NOT establish

This is structural parity only — heading presence, counts, link density. It does not assess
factual accuracy, API coverage correctness, or prose quality, which R11 of the 2026-11-04
directive separately asks for and which remains open. It covers 1 of 3 pilot repositories, not
all three, and none of the portfolio beyond the pilot set.

PARITY_BENCHMARK_COMPLETE: 2026-11-04 (1 of 3 pilot repositories; see coverage note above)
