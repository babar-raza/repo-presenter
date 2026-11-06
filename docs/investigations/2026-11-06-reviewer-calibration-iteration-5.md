# Reviewer calibration iteration 5 (2026-11-06): NOT_PASSED

Frozen, held-out corpus (`docs/investigations/2026-11-06-reviewer-calibration-iteration-5-plan.md`; registration
sha256 `3352ced4974d64372cb7094bc9fa7ff2f27b8d654db2126891931489b8a6975c`): 288 cases (28 scored clean twins, 124
mutants, 113 real defects, 23 unscored twins), stability 20 × 3. Reviewer independent_review v21 / logic 10 on
qwen3-next. 786 provider calls of the 1,000 cap. Thresholds unchanged. Status written: `NOT_PASSED`.

| Gate | LLM reviewer alone | Whole pipeline | Need |
|---|---|---|---|
| recall: contradiction (n=38) | 0.34 | 0.68 | ≥ 0.90 |
| recall: content loss (n=18) | 0.00 | **1.00** | ≥ 0.90 |
| recall: unsupported claim (n=118) | 0.11 | 0.21 | ≥ 0.90 |
| recall: broken install (n=12) | 0.00 | **1.00** | ≥ 0.90 |
| false-reject rate (n=28) | 0.14 | 0.18 | ≤ 0.10 |
| first reply valid JSON (n=764) | **1.00** | **1.00** | ≥ 0.90 |
| stability (n=20) | **0.90** | **0.90** | ≥ 0.90 |

Per defect class, on target: drop_section, duplicate_paragraph, break_install_command, contradict_package_name,
contradict_version all 1.00 through the pipeline (deterministic checks); contradict_format 0.86, invent_api_name
0.87; add_promotional_filler 0.56 and inject_unsupported_claim 0.61 (reviewer alone); **real contradictions 0.15
pipeline / 0.00 reviewer, real unsupported claims 0.14 / 0.02.**

## What it shows

Iteration 4 → 5 fixed what code could fix: stability 0.70 → 0.90 and content-loss / section-drop detection 0.17 →
1.00 now come from deterministic checks and the reviewer seeing the right lines. What remains is the same failure
in five iterations: the LLM reviewer (qwen3-next) does not find real unsupported or contradicted claims, even shown
the line and the facts, and it falsely rejects clean candidates at 14 %. Prompt changes have not moved it. Per the
escalation ladder the approach changes rather than the prompt again:

1. **Model.** The generator and the reviewer are the same model (qwen3-next). A bounded experiment re-runs the clean
   twins and a sample of real defects with the reviewer on `gpt-oss` (also served by the gateway; independent of
   the generator), within the remaining 214 calls of the cap, writing no status.
2. **Deterministic claim entailment** where the reviewer is weakest: checkable tokens in a sentence (identifiers,
   versions, formats, platforms, numbers) must be entailed by the facts the sentence's unit cites -- the
   deterministic tier already reaches 1.00 on every class it covers.

## Experiment: the reviewer on `gpt-oss` (same corpus subset, no status written)

28 clean twins + 45 sampled real defects were sent with `--model gpt-oss`; the 1,000-call cap was reached after 214
more calls, so 6 clean twins and 29 unsupported-claim / 13 contradiction cases were judged. Reviewer alone: real
unsupported claims 0.25 (qwen3-next 0.02), real contradictions 0.00, injected unsupported claims 0.80,
promotional filler 0.75 -- but **false-reject rate 1.00 (6 of 6 clean twins rejected)**. A different model trades
missed defects for rejecting everything; it is not a fix. The owner-approved calibration budget (1,000 calls) is
now spent. The next measurement waits for the deterministic claim-entailment check, measured offline with zero
calls first, so any further calls are spent only on a reviewer that the offline numbers say can pass.

## Experiment: deterministic claim entailment (BC-15/BC-16), zero provider calls — not enforced

Built on branch `w/claim-entailment` (e1950e4), tuned on iteration-4 data and measured once on the iteration-5 held-out
set: real unsupported claims 0.14 (0.34 incl. advisory), real contradictions 0.23, contradict_format/package/version
1.00/1.00/0.83, invent_api_name 0.93, injected unsupported claims 0.00 -- and **13 of 28 clean twins rejected (0.46)**.
Not enforced and not merged (code nothing runs is itself a failure pattern). Its contradiction tokens
(package/format/version) duplicate what the deterministic tier already catches at 1.00.

Three detectors (qwen3-next, gpt-oss, deterministic) fail on the same class, which suggests the class measures more
than reviewer judgement. A zero-call audit classifies every real:unsupported_claim and real:contradiction case as
false / true-but-not-in-the-facts / unverifiable maintainer knowledge / pipeline-authored / label error, maps each to
the responsible component, and recomputes recall by responsibility, before any further calls are spent. Thresholds
and labels are not changed.
