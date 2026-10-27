# PLAN — Lane L hosted parity: the live README, corrected, sealed and independently reviewed

Status: BUILT 2026-10-27 (ported, tests pass; not run hosted, not owner-reviewed). It has no authority of
its own: the mission document (`plans/repository_presenter_fresh_start_supervisor_prompt.md`) wins any
conflict and `project/state.yaml` (`LANE_L_HOSTED_PARITY`) holds the live cursor. Decisions are labelled
**L#** and recorded in `docs/DECISION_LOG.md`.

## 0. The requirement and the fact it answers

Mission section 1 and non-negotiables #1/#2: Lane L (live README first, minimal evidenced correction) and
Lane R (reconstruction) are two equal first-class lanes, neither a fallback, neither measured by the
other's delivery. Section 6: Lane L "must prove a zero-drift rerun is byte-identical and generates no new
model calls; independent retention and factual-review gates must judge the final README, not only the
edit delta. A successful deterministic patch is not automatically a high-quality README."

Fact before this work: hosted `present` ran only the Lane R cascade. The Lane L engine
(`readme/correction/`) ran only from `scripts/run_lane_l.py`, with no hosted run, no seal, no durable
transaction and no independent review.

## 1. What a Lane L candidate is

**L1 — a candidate.** The live README, corrected with the engine's minimal evidenced edits, and judged as
a whole. It is a pure function of (the live README's bytes at the pinned revision, the verified facts, the
tracked tree, the engine and detector versions). The engine makes no provider call; the one model call of
a Lane L run is the independent review of the final README.

Artifacts (sealed in the bundle; the producer is `lane_l_run.py`):

| bundle name | what it is |
|---|---|
| `README.md` | the corrected README (equal to the live one when nothing needed correcting) |
| `README.original.md` | the live README's exact bytes: a consumed input, sealed so the edits are re-checkable by anyone holding only the bundle |
| `README.patch.diff` | unified diff live -> corrected (empty for `NO_CHANGE_WARRANTED`) |
| `corrections.json` | the edit list and report: every edit with its evidence facts, every finding left unapplied (typed `defect` or opportunity), the confinement proof, determinism and idempotence |
| `holdouts.json` | the deterministic review checks L-01..L-06 |
| `facts.json`, `review_verdict.json`, `ledger.jsonl`, `dependencies.json` | as Lane R |

No plan, no dispositions, no content units: Lane L has none, and none are invented.

**L2 — three outcomes, two of them candidates.**
`CORRECTED` (at least one evidenced edit, no defect left unrepaired); `NO_CHANGE_WARRANTED` (no edit, no
defect: the live README is the candidate, byte for byte, still model-reviewed; a legitimate result, not a
fabricated improvement); `REFUSED_LANE_R_RECOMMENDED` (a detector found a defect no deterministic edit may
repair: a failing example, an over-claimed format, a link with no unique target). A refusal is never
sealed, never silently dropped and never masked; the recorded failure names the defects and Lane R. Which
findings are defects is a closed table (`report.INFORMATIONAL_DETECTORS`); an unknown detector is a defect.
A README that is absent or not UTF-8 is also a typed refusal (bytes outside the edits could not be kept).

## 2. Sealing and the zero-drift rerun

**L3 — sealing.** The existing sealer (`readme/bundle/seal.py`), lane-aware: same first seal, same
fresh-process byte-identical zero-call proof to `READY_FOR_PROPOSAL`, same update recording and adoption.
Only the artifact set (above) and the dependencies record differ by lane.

**L4 — what the zero-drift rerun proves, and what it does not.** Proves: the correction and the report are
byte-identical across a rerun from another working directory, host and newline setting, and the bundle
moves to `READY_FOR_PROPOSAL` with a measured proof (fresh process, byte-identical, zero provider calls
counted from the ledger). Does not prove: that the model is repeatable. The review's zero calls are a
replay from the call store (the workflow restores it); lose the store and the rerun asks again, spends a
call, and the seal withholds the proof (tested). Cross-machine determinism is enforced three ways:
(a) Lane L's `dependencies.json` names no host, Python version or toolchain (those belong to the facts
job; the facts' own digests carry what they produced); (b) every artifact is written as bytes or with
`newline="\n"` (AST test) and clones pin `core.autocrlf=false` so README bytes are git's; (c) a Lane R
facts defect this work found and fixed: the Python verifier quoted pip's error with the checkout's
absolute path and a CRLF, so two machines sealed different `facts.json` (`python_examples._redact`).

## 3. The independent review of the FINAL README

**L5 — review.** `lane_l_review.py` (a top-level module: the correction package names no model client, by test). Deterministic holdouts first, model-free, each blocking:
confinement re-proved from the edit list (not trusted from the engine), engine determinism, the
reviewer's own `claim_contradiction_rule` over the FINAL text, the reviewer's own `live_readme_loss_rule`
(retention versus the live README, with the edits as the accounting dispositions), and any unrepaired
defect. Only a candidate clearing them reaches `review_with_model` (the same job, prompt, route, fold and
no-re-roll guard as Lane R), given the final README, the live README, the facts, an empty plan, the
edits as dispositions and the holdouts as validation context. This module decides and clears nothing; a
`ReviewUnavailable` is a retryable failure; a deterministic-only verdict never seals. Lane R's
`disposition_coverage` and `duplicate_opening_paragraph` rules do not apply (no dispositions, no authored
opening). Limits stated: the reviewer's prompt is written for Lane R's shape and is uncalibrated for Lane L;
no Lane L candidate is PR-eligible until the reviewer calibration gate and a Lane L corpus pass. And a
blind spot in the reviewer's own scope that Lane L cannot fix from outside: `readme/review/scope.py` treats
the installation, license, badges and navigation sections, every fenced block and every table row as
renderer-printed and never shows them to the model. That is true of a Lane R candidate and false of a Lane L
one, whose every byte outside the edits is the maintainers' own (a format-support table is exactly where an
over-claim lives). Until the reviewer can be told the candidate is not renderer-owned (an API change in a file
this work does not touch), the deterministic holdouts are the only check on that text.

## 4. The lane dimension

**L6 — versioned layout, nothing moved.** Layout v1 (every existing bundle) IS Lane R:
`candidates/<slug>/<rev>/` with `candidates/<slug>/CURRENT`. Lane L: `candidates/<slug>/lane-l/<rev>/`
with `candidates/<slug>/lane-l/CURRENT` (a name that cannot be a revision). Manifest `schema_version` 1
has no `lane` and reads as Lane R; version 2 names its `lane`, and a reader refuses a manifest found in
the other lane's tree. New first seals write version 2 (either lane); a bundle already sealed in version
1 keeps being rewritten as version 1 by its own proof, so no bundle is resealed for its layout; Lane R's
`dependencies.json` gains no key (a new key would make every sealed Lane R bundle look changed on rerun).
`CURRENT` is per lane because one pointer cannot name two revisions.

**L7 — one status model.** `core/candidates.portfolio_status` reports one row per repository per lane
(`READY_FOR_PROPOSAL`, `ACCEPTED`, ..., `NO_BUNDLE`, `CORRUPT_BUNDLE`; a corrupt lane is shown, never
hidden, never counted, and never hides the other lane); `counted_by_lane` is the progress unit, separately
per lane. Every counting reader takes `lane` (default R). The drift monitor and `overlay_bundle` (the
candidates-publish effect) take `lane`; the overlay replaces only one lane's part of a slug, so publishing
one lane never deletes the other's committed candidate.

**L8 — consumed-scope invalidation.** Lane L consumes: the revision and the live README's bytes
(`source`: factual, invalidates), the fact records (invalidates), `components.correction_engine` and
`detectors.<name>` (the new `correction` scope: stage COMPOSING, update available, never invalidating),
`correction_review` and `reviewer_logic` and the `independent_review` prompt (reviewer scope). A prompt,
renderer or shell Lane L never ran is not in its record and cannot reopen it. Detector versions live in
`DETECTOR_VERSIONS`; a test pins each detector module's source to its versions so a logic change cannot
pass without a deliberate pin update.

**L9 — durable state.** One transaction record per repository per lane: the lane-scoped state backend
keeps Lane L's record in `refs/.../records/<owner>__<name>@lane-l` (`@` is illegal in a GitHub name, so no
repository can own that key); Lane R's refs are unchanged. The record names its lane; a record of the
other lane found in a lane's ref is refused. Same spine, same recovery, same lease; the receipt cites the
lane's own pointer.

## 5. The hosted flow

**L10.** `present.py --lane R|L` (default R). The facts job is shared and unchanged (secret-free, runs
the repository's examples). The credentialed job runs the chosen lane on the validated facts only: Lane L
executes no repository code, builds no facts, re-clones the SAME pinned revision to read the README, runs
the engine, has the final README reviewed, seals, and commits the transaction outcome. `present.yml` has a
`lane` input (`both` default, `R`, `L`): `both` runs R then L as separate processes, each its own
transaction and seal; Lane L runs even if Lane R failed (status function), only with the facts fetched; the
job is red if either is. Both call stores are cached beside the slug's bundles.

## 6. Blast-radius query (non-negotiable #3), run before the layout change

| scope | count |
|---|---|
| `candidates/` slug directories | 2 |
| tracked files under `candidates/` | 14 |
| sealed bundles (a `manifest.json`) | 1 (`aspose-3d-foss/Aspose.3D-FOSS-for-.NET`, schema 1, READY_FOR_PROPOSAL, `CURRENT` present) |
| revision directories without a manifest | 1 (`...-for-Python`, `probes.json` only) |
| `lane-l/` directories | 0 |
| `scripts/_lane_r_output/` repository directories | 36 (untracked, none sealed) |
| live durable-state refs (read-only `ls-remote`) | 2, both Lane R, both load unchanged under the new schema |
| source modules reading the layout | 6 (`core/candidates.py`, `readme/bundle/seal.py`, `core/state/present_transaction.py`, `monitor/drift.py`, `candidates_publish/git_ops.py`, `readme/bundle/recheck.py`) |
| source modules changed | 5 of the 6 (`recheck.py` unchanged: its rechecks are unported and a receipt path nobody writes is not made lane-aware) |

Held by tests: the committed bundle's manifest and `CURRENT` are pinned by digest and read as Lane R through
the versioned reader (`tests/core/test_candidates_lanes.py`); a v1 bundle's proof is written as v1.

## 7. What this does not decide

PR eligibility of a Lane L candidate (needs the reviewer calibration gate, a Lane L corpus, and
`propose/effect.py` taking a lane); a Lane L recheck runner (`recheck_bundle` is unported for both lanes); a
Lane L review prompt; the cohort pilot. Two shared-state facts the card should reflect: "zero provider
calls" is a call-store replay, not model repeatability (mission section 7 step 8 distinguishes them), and a
single `CURRENT` with a lane dimension cannot exist: `CURRENT` is per lane.
