# The first complete, real Lane R cascade: S3 → S4 → S5 → S6 → a fully rendered README

2026-10-22. `aspose-3d-foss/Aspose.3D-FOSS-for-Python`. The first time this repository has
produced a complete, real Lane R README — not a hand-built stand-in packet, not one stage in
isolation, but the full `repository_investigation` → `source_reconciliation` →
`presentation_planning` → `section_authoring` → `render_readme` cascade, every stage firing its
real LLM call (where it has one) against the real prompt manifests, real facts, and the previous
real stage's real accepted output.

## What was built to make this possible

Two real blockers had to close first, both discovered only by trying to fire the cascade, not
assumed from reading the module docstrings alone:

1. **`readme/reconciliation/dispositions.py` had no S4 job-wiring at all** — `coverage_findings()`
   and `normalize()` (the self-audit) were already ported, but `reconciliation_packet`/
   `reconciliation_schema`/`reconciliation_batches`/`merge_dispositions`/`write_dispositions` (the
   half that actually builds and fires the LLM call) were not. Ported now, verbatim except import
   paths, with 12 new tests (`tests/readme/reconciliation/test_output_budget.py`, including both
   real retained rejected-call fixtures: the PDF-TypeScript citation runaway and the Imaging-.NET
   truncated-reply-that-can't-close defect, copied byte for byte).
2. **A real bug in `readme/composition/components/glance.py`**, found only once a real diagram was
   actually rendered and read: `_label()` returned a bare quoted string (`"text"`), never wrapped
   in the `[...]` a Mermaid node declaration needs, so every node in the At a Glance diagram came
   out as unparseable `NodeID"text"`. This module had no test file at all before this session —
   nothing had ever rendered a real diagram and inspected its Mermaid syntax. Fixed
   (`["text"]`), with 7 new tests.

`readme/composition/planning.py` (S5: `planning_packet`/`planning_schema`/`plan_checks`) and
`readme/composition/authoring.py` (S6: `authoring_tasks`/`authoring_schema`/`unit_checks`/
`merge_units`) and `readme/composition/renderer.py` (`render_readme`) were already **fully**
ported from earlier in this session — this entry is the first time any of them has been exercised
against a real cascade rather than a hand-built packet or unit test fixture.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the **first attempt** — the schema-pinning mechanism (`investigation_schema`) prevented any hallucinated citation proactively; no reject/re-ask needed. |
| S4 `source_reconciliation` | 3 (batched, 77 units) | All 3 batches accepted on the first attempt. 77/77 units disposed, no duplicates, no gaps: 25 `SUPERSEDE_REDUNDANT`, 26 `OMIT_UNSUPPORTED`, 25 `VERIFIED_PRESERVE`, 1 `VERIFIED_REWRITE`. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt, **with the real `plan_checks`** (not a stand-in) as the checks callback. 7 core capabilities, 4 API hubs, 1+5 examples, 6 material limitations, 13/18 sections included. |
| S6 `section_authoring` | 10 (one per real authored task, including 4 batched `api_reference#types-N` tasks) | All 10 accepted on the first attempt, **with the real `unit_checks`** (not the earlier session's deliberately-simplified stand-in). 171 content units merged. |
| Render | 0 (deterministic code) | 73,072 characters, 1,037 lines. |

Every one of 15 real provider calls across S3–S6 was accepted on its first attempt. No rejection,
no re-ask, anywhere in this cascade for this repository.

## Honest scope limits — one real, measured defect left in the output, not hidden

The rendered README's opening section carries **two near-duplicate lead paragraphs** (lines 5 and
7–10 of `README.rendered.md`): the real, freshly-authored "opening" unit, and the *original*
inherited paragraph, printed verbatim because `source_reconciliation` disposed it
`VERIFIED_PRESERVE` → `opening` instead of `SUPERSEDE_REDUNDANT` → `opening`.

This is traced to a real, already-documented gap, not a new mystery: `dispositions.py`'s own
`coverage_findings()` self-audit only checks whether a `SUPERSEDE_REDUNDANT` (or a `PLACING`
disposition into a *deterministic* section) is provable — "opening" is LLM-authored, not
deterministic, so a `VERIFIED_PRESERVE` targeting it sails through unchecked. The mechanism that
*would* catch this — `placement_errors()`, part of the refusal/repair half `dispositions.py`'s own
module docstring states as "still deferred" — is not ported (it needs `composition/references.py`'s
`dangling_references`, also not ported). This is the first real, measured confirmation of exactly
the gap that docstring predicted, not a new finding requiring a new investigation.

## Honest scope limits, the rest

- Verified against one repository. The batching, schema-pinning, and checks machinery is proven
  to fire correctly here; not yet run against a second repository to see whether a different
  fact/disposition shape breaks any of it.
- `reconciliation_narrowing` (the narrowed re-ask repair path for a partially-rejected S4 batch)
  is still not ported — never needed here because every batch was accepted whole.
- This is one full run, not a scaled portfolio proof. "Lane R produces a real document" is now
  demonstrated once, for one candidate; it is not yet demonstrated as a repeatable, portfolio-wide
  capability.
