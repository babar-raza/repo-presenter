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

## Restricted operations recorded (environment capability, not project blockers)

| Operation | Observed | Exact capability needed |
|---|---|---|
| `workflow_dispatch` of `present.yml` from this session | `POST .../actions/workflows/present.yml/dispatches` -> 403 "Resource not accessible by integration" (reads of Actions succeed) | The GitHub App/integration token must carry `actions: write` on `babar-raza/repo-presenter`; a grant made mid-session did not reach this session's token (still 403 afterwards) |
| Debian package install in `docker build` | `deb.debian.org` unreachable | allowlist `deb.debian.org`, `security.debian.org`; or verify via the hosted `docker` CI job (PR #4) |
| .NET SDK for example compilation | `builds.dotnet.microsoft.com` unreachable (api.nuget.org reachable) | allowlist `builds.dotnet.microsoft.com`; or run on a hosted runner (present.yml installs 10.0.204) |
| github.com / api.github.com direct reads | 403 (raw.githubusercontent.com 200) | governed access; handled by the alternate-source rule for blob/raw links only |

## Local Lane L run on aspose-font-foss/Aspose.Font-FOSS-for-Python (streaming on, local state remote)

Result: `FAILED_INTERNAL` (validation_failed), nothing sealed - the intended outcome, not a fault. The
independent review returned REJECT with 5 deterministic blocking findings: the live README lists
formats (.otf, .woff, .woff2, .cff, .cff2, .pfa, .pfb, .eot) that no SUPPORTED format fact states
(`claim_contradiction`), and four of its own examples FAIL when executed
(`UnsupportedFontFormatException` x2, `ImportError`, `TypeError`; `lane_l_unrepaired_defect`). Lane L
may not repair content it cannot verify, so it left 4 defects and recommended Lane R. These are real
upstream README defects (issue-discovery candidates for G3); upstream issue filing remains disabled,
so nothing was filed. Counts toward neither G1 nor P1 (no sealed candidate).

## 3D-FOSS-for-Python (mandatory G4 target) local Lane R: blocked source fact, not a pipeline fault

Four local attempts. Two pipeline defects were found and fixed on the way (merged / pushed): the
`python3 -m pip` launcher not matching the UNRESOLVED install fact (reconciliation rejected 3x), and
- on Font - a deferred CONTRADICTED example reported as lost. The final 3D-Python attempt completed
the whole cascade and the independent review returned REJECT with exactly one finding:
`live_readme_loss`: code block `python3 -m pip install aspose-3d-foss`.

Cause: `install_command:pip` is UNRESOLVED because PyPI's `aspose-3d-foss` 26.1.0 lists its project
URL as `https://github.com/aspose-3d/Aspose.3D-for-Python`, a different repository from
`aspose-3d-foss/Aspose.3D-FOSS-for-Python`; ownership cannot be confirmed. The candidate therefore
renders an Installation section saying the package "could not be confirmed on PyPI" and does not
reproduce the live install command. `DEFER_UNRESOLVED` is deliberately not an accounting disposition
(independent_reviewer.ACCOUNTING_DISPOSITIONS), per the 2026-11-01 Page-Python ruling in
docs/DECISION_LOG.md ("not something a reconciliation/review code change should paper over"). That
ruling is kept; the reviewer was not changed.

Consequence: the 3D-Python candidate cannot seal until the registry metadata is reconciled (a PyPI
project-URL change by the package maintainers, an upstream data question outside this pipeline) or
the owner explicitly rules otherwise. Recorded as a genuinely blocked source fact; the
upstream-issue candidate cannot be filed (external writes prohibited). Mandatory-target status for
G4/3D-Python: BLOCKED_ON_SOURCE_FACT.
