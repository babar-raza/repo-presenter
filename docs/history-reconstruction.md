# History Reconstruction — independently re-verified, not trusted from old-repo claims

Produced 2026-10-21 per mission document §2 ("falsify all claims, including old
green verdicts"). Source: `E:\Users\prora\OneDrive\Documents\GitHub\repository-presenter`,
read-only (`git show`/`git log --all`, no checkout of the live worktree). Every SHA
below was independently resolved and its cited evidence file read directly, not
taken from the mission document's or the old repo's own framing of itself.

## Checkpoint ledger

| Date | SHA | What | Defect | Reusable method | Required new verification |
|---|---|---|---|---|---|
| 2026-09-03 | `cc6da3681226` | G1 first sealed Lane R canary, `aspose-3d-foss/Aspose.3D-FOSS-for-Python` | Reviewer fold-to-ACCEPT bug (below) | Bundle/manifest schema shape | Candidate's actual quality — accepted under a broken reviewer, never re-checked |
| 2026-09-05 | `fa04bc96ef6f` | G2 stability canary | Same fold bug | — | Same |
| 2026-09-06 | `6a42d72b537d` | 2nd-gen candidate (Slides-Python), 2/34 sealed | Same fold-era logic | — | Same |
| 2026-10-10 | `e482390bde59e77` | **Fix**: `REJECT` stands unless every finding carries a deterministic refutation (`DETERMINISTIC_RULES` vs `JUDGMENT_RULES` split) | — | The deterministic/judgment rule split is a genuinely reusable *pattern* — the idea, not the code, since it was never proven against fresh data | Confirm no regression since; itself unverified against anything sealed after it landed |
| 2026-10-11 | `a919d0394d` | Two-lane governance introduced (Lane L), live-README-based structural rulings | — | Governance framing concept | Superseded 3 days later |
| 2026-10-14 | `53ae90c9` | State machine repointed to Lane R as primary; 16 unpinned queue items retired | Lane L internally demoted *before* the Oct 20 owner ruling | — | — |
| 2026-10-16 | (plan in `state.yaml` `G3-W12`/"D8") | Lane R "dependability rebuild" plan authored: 8 cards (C1–C8), metrics M1–M9, floors | — | The metric/floor *design* is sound reading material | Everything past card C1 — C2 through C8 never executed |
| 2026-10-19 | `bf2a71eecd` | Salvage batch merge; registry scope 44→36 (JMAP excluded) | — | — | — |
| 2026-10-20 | `a8a8be0d` (PR #352) | Owner ruling, in person, on Lane L: not a deliverable. 71/366 example facts CONTRADICTED, 8 contradicted + 80 unresolved links, 30 missing-API findings across 19 repos, undetected false 3D-.NET format claims | Confirms both lanes currently ship zero trustworthy output | The investigation's defect taxonomy (examples / links / API / format claims) is a reusable **checklist** for this repo's own independent verifier | This ruling is one day old and explicitly partial — owner expects to find more on manual review |

## The acceptance-integrity bug, in detail

At `cc6da3681226` and `fa04bc96ef6f`, `src/repository_presenter/components/readme/review/independent/review.py:219` and `:269`
read:

```python
verdict = returned if findings or returned == ACCEPT else ACCEPT
```

Confirmed directly against the sealed evidence, not inferred:

- `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/d9f3bfe50d47e8156266955dda52ec5abf2d9dec/review.json`:
  `findings: []`, `verdict: "ACCEPT"`, `verdict_as_returned: "REJECT_FACTUAL"` — 7
  findings demoted to `advisory`.
- Same path, revision `65b1f577c0f16d0d9112bb6c1153d3024543ac02/review.json`:
  `findings: []`, `verdict: "ACCEPT"`, `verdict_as_returned: "REJECT_PRESENTATION"`.

The demotion was not a blind overwrite — each advisory entry cites a stated rule
(e.g. "quoted span is the literal value of a SUPPORTED fact"). The rule is
overbroad: it conflates "this exact phrase is factually correct" with "this
finding has no merit," so a genuine omission finding (a missing PyPI-availability
caveat) was folded purely because its quoted span matched a literal fact value.

**Scale, per the fix commit's own message (`e482390bde59e77`, 2026-10-10):** not a
two-canary anomaly — **27 of the 30 sealed reviews** were REJECT-folded-to-ACCEPT
this way, including one case that hid a dropped security warning and a false API
claim. Fixed by splitting demotion rules into `DETERMINISTIC_RULES` (may refute,
carrying `refuted_by{rule, evidence}`) and `JUDGMENT_RULES` (annotate only, never
fold) — a `REJECT` now stands unless *every* finding has a deterministic
refutation.

**Status: fixed on `main` as of 2026-10-10. Nothing has re-verified the 28
currently-sealed candidates against the fixed reviewer** — this is the most
likely direct cause of the old repo's own `authorizable_candidates: 0/36`
despite `current_candidates: 28`, independent of the separate Oct 20 Lane L
findings.

## Correction to the mission document's own citation

The mission document (§2) attributes to PR #347 a claim that "old BC-04/BC-14
detected 0/20 sampled real defects and newer validation rejected all 30 stored
bundles." Independent check: PR #347 (merge `1c95db12`, 2026-10-20) is titled
"G3-W12 (C1): Lane R labeled corpus, ratchet, bump-entry test; recovery M1
inventory" — it **is** the C1 measurement card, not a separate sampling study,
and no commit under that PR matches the "0/20 sampled" wording. **Treat that
specific figure as unverified; do not cite it further without finding its
actual source.** The real self-audit is `docs/investigations/14-lane-r-dependability.md`
/ `evidence/lane-r-dependability/ledger_baseline.json`, confirmed below.

## `ledger_baseline.json` — numbers confirmed real; an earlier methodology flaw was already self-identified and fixed

Confirmed live against the file itself: `measured_on: "candidates/*/CURRENT at
control revision 4a7baf11 (sealed bundles on disk, 30)"`, with real per-repository
disposition counts (e.g. `aspose-3d-foss__Aspose.3D-FOSS-for-.NET`: 70 units, 15
`OMIT_UNSUPPORTED`, 12 of those `omit_unsupported_without_fact`,
`judge_failing: [J4_DISPOSITIONS, J6_NOT_WORSE_THAN_LIVE]`).

`docs/investigations/14-lane-r-dependability.md` (line ~100) already documents a
circularity the project found in its *own earlier* audit attempt: "M1 counted
only the units the model chose to keep (so moving a unit to `DEFER` gave 100
percent) and M4 to M5 were identities of the gates being built." The 2026-10-16
redesign fixes this: M1 is now measured over *all* live units with `DEFER`
counting as unaccounted, M1–M5 are implemented outside the gates under test,
and a differential catch-rate (mutant vs. clean twin) was added. This confirms
the self-grading risk the mission document warns about was real here once —
and was already caught and fixed once, which is itself evidence the old team's
process can self-correct, not just accumulate false greens.

## Net assessment for this repository's salvage decisions

1. **Do not** give `REUSE` to `readme/review/independent/review.py` or
   `readme/acceptance/judge.py` as they exist on old-repo `main` — even the
   post-fix version has never been exercised against a real candidate end to
   end, and the Oct 20 findings show the Lane L validation chain (a different
   but related component) has an independent, separately-confirmed blind spot
   around examples/links/API/format claims.
2. **Do** treat the deterministic/judgment-rule-split *pattern* (never fold a
   `REJECT` unless every finding has a deterministic refutation) as a design
   worth re-implementing fresh in this repo's own reviewer — `ADAPT`, not
   `REUSE`, since the code itself is unproven.
3. **Do** treat the Oct 20 defect taxonomy (example verification, link
   verification, API-completeness checking, format-claim cross-checking) as
   the starting checklist for this repo's own independent verifier design.
4. No candidate sealed in the old repo (all 30 in `ledger_baseline.json`, all
   28 currently marked `current_candidates`) may be treated as a trusted
   positive example. They are usable only as **negative/positive holdout
   material** per mission §3, after this repo's own fresh review of each one.
