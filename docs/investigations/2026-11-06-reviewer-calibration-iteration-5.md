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
