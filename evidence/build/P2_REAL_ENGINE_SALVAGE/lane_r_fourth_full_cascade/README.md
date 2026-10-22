# The fourth complete, real Lane R cascade — a fourth ecosystem, and a worse manifestation of the
# same known defect class

2026-10-22. `aspose-3d-foss/Aspose.3D-FOSS-for-Java`. Fourth cascade run, fourth ecosystem
(`java`, after python, go, net).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 3 (batched, 94 units) | All 3 batches accepted on the first attempt. 94/94 units disposed. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt, with the real `plan_checks`. |
| S6 `section_authoring` | 8 (one per real authored task) | 7 of 8 tasks accepted on their first attempt; `api_reference#types-1` needed a real reject→accept cycle (2 calls). 127 content units merged. |
| Render | 0 (deterministic code) | 30,767 characters, 416 lines. |
| S8 `coherence` | 3 (batched) | Both batches accepted (one needed a real reject→accept cycle too, 2 calls). 0 revisions made. |

Every real rejection in this run was followed by a real accepted correction on retry — the
schema+checks mechanism caught a real defect and the re-ask fixed it, exactly as designed.

## A worse manifestation of the same known defect class, not a new one

The first three cascade runs each measured exactly one extra, duplicate unit landing in the
single-slot `opening` section. This run is worse: **four** units were disposed into `opening`,
not one — the real lead paragraph (correctly `VERIFIED_REWRITE`), plus three unrelated preserved
units about Maven Central publication, "no required third-party dependencies," and a Java 21+
requirement list. None of the latter three belong in a product's opening paragraph; they belong
in `installation`/`dependencies`. The rendered result is not a clean duplicate paragraph this
time — it is a fragmented, nonsensical mix: "Add it to your project as a dependency — no extra
repositories or configuration required." and a bare bullet "No native/system libraries beyond
the JVM itself." both appear directly under the opening sentence, with no heading or context.

This is the same root cause scaling worse, not a different one: `coverage_findings()`'s own
gap-check still does not fire for a `PLACING` disposition into `opening` (an LLM-authored, not
deterministic, section) — confirmed again, and this time the model placed three extra units
there instead of one. It further strengthens, with a fourth independent measurement, why the
real fix needs the unported validation/review layer (an independent review of the *finished*
document, which could see that these three units read as garbled noise in the opening section)
rather than anything available in the composition-time stages already fired.

## Honest scope limits

- 4 of 36 repositories now have a full real cascade run (python, go, net, java). cpp, rust,
  typescript still untried for the full cascade.
