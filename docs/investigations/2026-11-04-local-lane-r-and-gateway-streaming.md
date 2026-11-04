# 2026-11-04 local Lane R run and gateway streaming finding

Moved out of docs/DECISION_LOG.md: that file is evidence for TC-009's marker check, so appending to it
stales TC-009's receipt, and the log is globally denied for scoped re-verification (gateverify). Until
that conflict is resolved, supervisor notes go in docs/investigations/ instead.

## 2026-11-04 (supervisor session, branch claude/blissful-gauss-8xels9): local Lane R feasibility and gateway finding

- **Observation (measured, not assumed):** from the cloud sandbox, `llm.professionalize.com/v1` returns HTTP 502
  at ~30.5 s for any non-streaming chat completion that takes longer than 30 s; the same request streamed
  succeeds. Every real cascade call exceeds 30 s, so the first two local runs failed with `HTTP 502` after 3
  retries. Added opt-in `GPT_OSS_STREAMING=1` (`core/llm/jobs.py`, `tests/core/llm/test_streaming.py`); default
  unchanged.
- **Local end-to-end run** (`present --stage combined --lane R`, `aspose-font-foss/Aspose.Font-FOSS-for-Python`,
  local bare state remote, no GitHub writes): 44 provider calls, all HTTP 200, 14 cache reuses, full cascade
  produced. Independent review returned REJECT (1 deterministic finding: live banner link
  `docs/images/banner.png` lost without disposition), run ended `FAILED_INTERNAL` (the durable-state label for
  a rejected, unsealed run). So: the pipeline works locally against the real gateway and the reviewer blocks a
  real content loss. It is NOT a delivered candidate and does not count toward P1.
- **TC-007 unchanged:** calibration remains `NOT_PASSED`; no status was edited. Iteration 4 needs fresh
  ACCEPTed clean twins per ecosystem, which requires further local cascade runs (about 10 minutes and ~45
  calls each) and a fix for the banner-link disposition gap seen above.
- **Not done this session:** mission matrix, migration-readiness package, TC-009a/009b/010a/011/012a. PR #3
  (write guard) was left to its own agent.

## Correction and second local run (after the owner allowed products.aspose.org / img.shields.io)

- The first run's banner REJECT was a sandbox artifact (products.aspose.org and img.shields.io were
  unreachable, so link facts were UNRESOLVED and the renderer correctly dropped the banner). It was not
  a pipeline or disposition defect.
- Second run (same repository, streaming on): 47 gateway calls, all HTTP 200. The deterministic review
  stage returned ACCEPT (`model_verdict: null`), but validation check BC-06 failed because
  `https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/LICENSE.txt` is `UNCHECKED`:
  direct requests to github.com and api.github.com return HTTP 403 from this session (governed GitHub
  access; raw.githubusercontent.com returns 200). The run was therefore correctly not sealed and no LLM
  review was made (a deterministic-only verdict is never sealed).
- Consequence: no sealed candidate and no calibration-corpus base can be produced in this sandbox for any
  README that links to github.com pages. That needs a hosted run (Actions, not dispatchable from this
  session: HTTP 403 on workflow_dispatch) or a runner with ordinary github.com access. The link check was
  deliberately not weakened.
