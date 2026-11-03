# First-Principles Project Audit, Accountability Review, and Goal-Oriented Recovery Plan

**Date:** 2026-11-01 (produced); **owner-adopted as binding authority 2026-11-03**
**Requested by:** project owner, via a pasted directive (verbatim goals G1–G8 below)
**Status:** **ADOPTED.** Wired into the authority chain this project's agents actually read —
see `AGENTS.md`'s own top section, `docs/MISSION_AUTHORITY.md`'s "Corrective plan" section, and
`project/state.yaml`'s nine `AUDIT_2026_11_01_ITEM_*` cards (full wiring record:
`docs/DECISION_LOG.md`'s 2026-11-03 entry). This document stays open, not closed, until every one
of those nine cards is independently verified `DONE` — reading it once does not satisfy that.
**Method:** five parallel research threads (mission-authority history; G3–G6 code-level
implementation; real portfolio acceptance tally via durable state records; predecessor-project
retrospective, including direct access to both legacy repos' own primary sources; aspose.org
refresh-candidate skill investigation) plus direct inspection by the supervisor session that
wrote this report. Every claim below is sourced to a file, commit, `gh api` call, or durable
state record — see citations inline. Claims that could not be verified are marked `UNVERIFIED`
rather than guessed.

---

## A. Executive Verdict

**The project is building a technically sound core (the Lane R/Lane L README cascade and its
evidence/state machinery) inside a governance and scope environment that has already repeated at
least two of its own named predecessor failure modes in its first 12 days, and has never
operated four of its eight stated capabilities (issues, publishing, GitHub App auth, autonomous
scheduling) outside of library code that nothing calls.**

Three things are simultaneously true, and the rest of this report tries not to collapse them
into one number:

1. **The verified, hands-on core works, and today proved it.** In one working session, 11
   repository/lane pairs reached a genuine, independently-reviewed `ACCEPTED` state for the first
   time (not self-graded — `ACCEPTED` is only reachable after an independent, non-authoring LLM
   review returns ACCEPT), four real defects were found, fixed, cold-verified by an independent
   agent, and live-verified against the real failing case, and every fix that turned out to be
   unsafe on first attempt was caught before merge, not after. This is real evidence that the
   evidence-gated discipline this project claims to follow can and does work when it is actually
   applied.
2. **The 25+-candidate targets in G1/G2 are not yet met, but are reachable.** Lane R: 9/25+
   (36% of target, 25% of the 36-repository registry ceiling). Lane L: 12/25+ (48% of target,
   33% of the ceiling). Neither lane is close to exhausted — most of the registry has simply
   never been run to completion, or failed for reasons already triaged (see §E, §I).
3. **G3 (issues), G4 (publishing), G5 (GitHub App auth), and G6 (autonomous Docker/CI) are not
   production capabilities today — they are unexercised library code.** Each has real,
   reasonably-written Python behind it. None has a caller that anything actually runs
   autonomously or on a schedule. Zero bot PRs have ever been opened by this codebase against
   either of G4's two mandatory test repositories. The issues module's own filing path has fired
   exactly once, by hand, owner-authorized in-session — real, but a single manual exercise, not
   an operating capability (discovery and close were never built at all). There is no Dockerfile
   in the repository.
   There is exactly one GitHub Actions workflow, and its only trigger is a human typing a command.

**The honest one-line answer to the user's five final questions (§14 of the directive):**
Yes, the right thing is mostly being built (the verified-evidence core), but the project has
drifted into building it without the production shell (App auth, publishing, issues, autonomous
execution) that would make it count as *delivered*, while its own governance mechanism for
preventing exactly that drift was used once and then silently abandoned. The shortest path to the
eight goals is not a rewrite — it is wiring four already-written, already-tested libraries to
something that calls them, fixing the real defect backlog the core cascade keeps finding, and
reinstating (or formally retiring, on the record) the supervisor/worker discipline this project's
own founding documents require and currently do not practice.

---

## B. Eight-Goal Scorecard

Legend: `PASS` met / `PARTIAL` real progress, short of the bar / `FAIL` not implemented as a
working capability / `BLOCKED` depends on something else first / `UNVERIFIED` no evidence either
way.

| Goal | Verdict | Evidence |
|---|---|---|
| **G1 — Lane L production, 25+ accepted** | `PARTIAL` | 12 repositories currently `ACCEPTED` via the hosted cascade + independent review (not self-graded). Registry ceiling is 36, so 25 is reachable. 24 repositories currently `FAILED_INTERNAL` for Lane L; most have a real, already-triaged cause (see §E). |
| **G2 — Lane R production, 25+ accepted** | `PARTIAL` | 9 repositories currently `ACCEPTED`/`READY_FOR_PROPOSAL`. Same ceiling/reachability as G1. 27 repositories currently failing; causes triaged in §E, several fixed today. |
| **G3 — Issues module operational** | `FAIL` (as a running capability); library code `PARTIAL` | Real filing code exists (`src/repo_presenter/issues/{model,dedup,approval,file}.py`, 962 lines) with real gating (kill-switch env var, per-handoff approval file). **No discovery mechanism exists** (nothing constructs a `Handoff` except tests). **No close mechanism exists** (explicitly not ported — `file.py` comment, "NOT ported this pass, deliberately"). **No autonomous caller exists** anywhere outside `tests/`. The required `ops/issue_approvals/` directory does not exist on disk. The project's entire lifetime (old repo + this repo) has produced exactly **one** real filed issue (`aspose-3d-foss/Aspose.3D-FOSS-for-Python#4`) — `project/state.yaml`'s own record confirms it genuinely went through `src/repo_presenter/issues/file.py`, in local `GITHUB_TOKEN` mode (a human-authenticated token, not the App), owner-authorized in-session on 2026-10-21. The filing *path* is real, proven once, by hand; discovery and close remain entirely unbuilt. |
| **G4 — Candidate publishing, mandatory tests cells/net + 3d/python** | `FAIL` | Real effect-layer code exists (`src/repo_presenter/propose/{effect,pull_request}.py`, `authorization/*`, 1,832 lines combined) with **zero callers anywhere in `src/` or `scripts/`**. The code's own comment states plainly: *"this repository's own `propose/effect.py` has never fired live."* Live-checked via `gh api search/issues?type:pr` against both mandatory repositories (`aspose-cells-foss/Aspose.Cells-FOSS-for-.NET`, `aspose-3d-foss/Aspose.3D-FOSS-for-Python`): **every PR against either repository is human-authored; zero bot-authored PRs exist against either, ever.** A genuine bot-authored PR does exist (`aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp#7`, author `repository-presenter[bot]`) — from the **old, legacy** repository's own workflows, on a **different** repository (Cpp, not .NET), proving the *capability* worked once, historically, elsewhere — not proof of anything in this codebase or against either mandated target. |
| **G5 — GitHub App integration** | `FAIL` | The App identity is real and externally confirmed (`repository-presenter[bot]`, App ID 5092474, installed on target upstream repos) — but **this codebase has no code path that can mint its own installation token**: no JWT signing, no private-key handling, no call to `/app/installations/{id}/access_tokens` anywhere in `src/`. `token_provenance.py` only *verifies* a token handed to it externally. The one workflow (`present.yml`) never references an App token at all; its only secrets are a plain state-write PAT and the LLM-provider key. |
| **G6 — Autonomous Docker + GitHub Actions production** | `FAIL` | Zero `Dockerfile`/`docker-compose*` files exist anywhere in the repository. Exactly one GitHub Actions workflow exists (`present.yml`); its only trigger is `workflow_dispatch` (manual); its own comment states: *"a scheduled trigger is an owner decision (cadence and provider spend) not yet made."* Infrastructure-level resilience is limited to a 60/90-minute timeout cap — no retry, no crash recovery, no runner-failure handling at the workflow level (the *application's* own durable-state retry/resume logic is real and separately evaluated in §C dimension 9, but that is not the same as infrastructure-level autonomy). Every run in this project's history, including all of today's ~45 dispatches, was started by a human or an agent acting as one, typing a command. |
| **G7 — Parity with/non-duplication of aspose.org's refresh-candidate skill** | `PARTIAL` | The skill is real and was located and read directly: `skills/readme-refresh.md` + a 6,219-line state machine (`readme_refresh_run.py`) + a 12,050-line deterministic-checks file (`readme_refresh_checks.py`) in the sibling `aspose.org` checkout, last exercised 2026-10-31 against `3d/python` and `cells/java`. **Decisive finding: the skill contains zero programmatic LLM calls** — authoring happens inside an interactive Claude Code session via a slash command; the Python is a state machine + deterministic checks wrapped around a human/agent-in-the-loop editing step. This **directly refutes** the premise that Lane L/R could become "a lightweight orchestration mode" around this skill without reintroducing an interactive step, which would contradict G6. Separately and genuinely true: real, substantive **duplication at the pattern/check level** exists — disposition-coverage checks, retention/fidelity scoring, and diagram validation were independently rebuilt inside `repo-presenter` after `migration/reuse-manifest.yaml` had flagged the skill's own checks as "optional... not yet inspected" from day one — and apparently never were inspected before being reimplemented. |
| **G8 — Deliver without endless development; do not repeat the predecessors** | `PARTIAL`, trending toward repeat | See §F for the full retrospective. Two concrete, dated instances of a predecessor failure mode recurring *inside this project's own 12-day life* were found: (1) a 2026-10-21 informal acceptance sweep reported 36/34 lane-accepted candidates; the owner personally caught this as a "false-green" on 2026-10-28 and reset the real count to 2/36 and 0/36 — the exact "automated ACCEPT was not trustworthy even after a known bug was fixed" lesson this project's own `MISSION_AUTHORITY.md` names from the *old* repo. (2) The project's own mandated supervisor/worker taskcard mechanism (`ops/gatecli.py`, `ops/SUPERVISOR.md`) was used exactly once (one smoke-test card) and then silently never used again, including for today's own work — "an elaborate plan authored then abandoned after step one" is this project's own name for a predecessor mistake, now recurring, unflagged until this audit. Counter-evidence that disciplined delivery is achievable: today's own session (§A, §E). |

---

## C. Twenty-Dimension Audit

| # | Dimension | Verdict | Key evidence |
|---|---|---|---|
| 1 | Purpose & Objectives | `PARTIAL` | At least **four different numeric "how many candidates is enough" targets** have existed across this project's life and its immediate predecessor: 20/36 (`plans/idea.md`, retired), 28+ (`docs/PORTFOLIO_SCALE_PLAYBOOK.md`, a superseded manual-sweep methodology), "all 36, both lanes, hosted-sealed" (`OWNER_FULL_PORTFOLIO_BAR_2026_10_28`), and now 25+ (this directive). None of these four is "wrong," but the repeated redefinition is itself the pattern G8 warns against. |
| 2 | Requirements & Scope | `PARTIAL` | The mission document (`plans/repository_presenter_fresh_start_supervisor_prompt.md`) covers G1/G2/G3/G5/G6/G7/G8 in substance, but **the specific numeric floor (25), the two mandatory G4 test repositories (cells/net, 3d/python), and any Docker requirement are not present anywhere in this repository's existing authority chain** — confirmed by direct, targeted search. This directive is introducing new, more specific requirements, not surfacing hidden existing ones; flagged plainly rather than assumed either way. |
| 3 | Architecture & Design | `PASS`/`PARTIAL` | The fact-polarity evidence model (SUPPORTED/CONTRADICTED/UNRESOLVED, every fact citing real evidence), the structurally-non-self-gradable independent reviewer (S10), and the durable git-ref state machine are a genuinely sound design — today's own work repeatedly exercised and validated this design under real adversarial pressure (cold verifiers finding real gaps, live hosted runs confirming fixes). Risk: `dispositions.py` (the S4 reconciliation stage) is 2,711 lines in one file — a real complexity concentration that made today's own fix work slower and more error-prone than it should have been (two of four fixes needed a correction round after an independent verifier found a gap). |
| 4 | Code Quality | `PASS` | 68,663 source lines against 63,069 test lines (near 1:1), 2,664 test functions across 189 test files. Today's own session repeatedly used real falsifiers (revert-only-the-fix, confirm the new test fails) as a matter of course — this is a real, practiced discipline, not aspirational. |
| 5 | Functional Correctness | `PARTIAL` | The core cascade demonstrably produces independently-accepted candidates (11 fresh ones today). It also still has an active, real defect backlog: today's single session found and fixed four previously-unknown defects (heading-accounting, a classifier string-match gap, a .NET version-format false positive, a lead-in/payload coordination gap) and found-but-deliberately-did-not-fix four more (a cache-staleness repair bug, a sibling-product-name false positive, a printed-but-uncited content-loss gap, a repair-loop oscillation on a stale claim) — all from running real repositories through the real pipeline for one day. |
| 6 | Implementation Completeness | `FAIL` for G3–G6; `PARTIAL` for G1/G2 core | See §B. The core cascade is substantially complete; the production shell around it (issues, publishing, App auth, scheduling) is not. |
| 7 | Testing & Verification | `PASS` core / `BLOCKED` shell | The core cascade has deep, real unit/negative-control test coverage and a practiced independent-cold-verification discipline (demonstrated 4 times today). G3–G6 cannot be integration-tested because they have never been exercised end to end — there is nothing to test against. |
| 8 | Security | `PARTIAL`/`UNVERIFIED` | Positive: issue-filing is gated behind an explicit kill-switch env var and a committed per-handoff approval file (defense in depth, even though the mechanism around it is incomplete). Positive: the GitHub App cannot be silently bypassed with a personal token in production (`token_provenance.py` fails closed if the App token doesn't verify) — though this path has never actually run. Not independently audited this pass: secret handling in the one existing workflow, supply-chain pinning beyond the already-noted tree-sitter grammar pins, or any dependency-vulnerability scanning (none found, not deeply searched for). |
| 9 | Reliability & Resilience | `PARTIAL` | Application-level: the durable state machine's retry/resume/dedup logic is real and was exercised extensively and successfully today (including a real discovered-and-documented limitation: a repeat success/failure landing on the same terminal state can leave `last_transition` stale while `failure`/the record's own `state` field stays accurate — a genuine, now-documented gap in how "freshness" must be read, not a correctness bug). Infrastructure-level: minimal (see G6). |
| 10 | Performance & Scalability | `UNVERIFIED` | Not directly measured by any research thread. Each hosted run takes roughly 10–20 minutes; today's ~45 runs were dispatched and awaited serially, by hand. No evidence of tested concurrent/parallel execution at any meaningful scale. |
| 11 | Dependencies & Toolchains | `PASS` | Modern, reasonable toolchain (`hatchling`, `pydantic` v2, `tenacity`, `httpx`). `tree-sitter` grammar versions are deliberately pinned exactly rather than by floor, with a clear, specific reason recorded in `pyproject.toml` itself (an unpinned grammar bump would silently move extracted facts under an already-sealed candidate). |
| 12 | Infrastructure & Deployment | `FAIL` | No Docker, no local-runner tooling (despite being explicitly called for in two planning documents since this project's founding), exactly one manual-only workflow. |
| 13 | Data & State Management | `PASS` design / `PARTIAL` operation | The git-ref-based durable record design is sound and real. Operationally, `project/state.yaml`'s own top-of-file dashboard is **explicitly self-admitted stale** (it says so in its own header) and has not been regenerated since 2026-10-31 — meaning it predates every one of today's 11 fresh accepts and does not reflect current reality. The only way to get the real current count, right now, is to read 68 git refs by hand (which is what the research thread for this report had to do, because nothing in the repository automates or surfaces it). |
| 14 | Agentic Capabilities | `PASS`, with an important caveat | Today's own session is itself the evidence: an independent cold-verifier subagent found a real, concrete gap in 2 of the 4 fixes attempted before they were merged — proving the verification step is load-bearing, not ceremonial, and that first-pass agentic work (including this session's own) is not reliably correct without it. |
| 15 | Observability & Diagnostics | `PARTIAL` | The per-run durable record, ledger, and evidence artifact trail is genuinely rich and was relied on heavily and successfully throughout today's work. The project-level rollup (`state.yaml`'s own dashboard) is stale and not self-correcting. |
| 16 | Documentation & Knowledge | `FAIL` | The repository's own top-level `README.md` is **completely empty** (0 lines) — a README-generation project ships no README of its own. `docs/MISSION_AUTHORITY.md` itself carries a now-provably-stale caveat (claiming `foss-readme-optimizer`'s failure modes are "not yet independently inspected" — a 15-minute investigation during this audit found real, specific, primary-source evidence directly from that project's own `POC-FREEZE.md`, proving the caveat is now simply out of date). |
| 17 | User Experience & Usability | `FAIL` | Zero autonomous operation; every action requires a human (or an agent acting on the human's behalf) to type a command. No status dashboard. No single command surfaces the real, current, trustworthy portfolio count (confirmed by needing a dedicated research pass to compute it from raw git refs for this very report). |
| 18 | Integration & Compatibility | `PARTIAL` | Read-side GitHub API integration is real and heavily exercised (today's own session). Write-side (App auth, publishing, issues) is unused. aspose.org integration is real at the fixture/pattern level but genuinely under-exploited (G7). |
| 19 | Governance & Maintainability | `FAIL` | `AGENTS.md`'s own binding "Taskcard discipline" section, and the dedicated `ops/SUPERVISOR.md`/`ops/gatecli.py` mechanism built to enforce it, has been exercised exactly once in this project's history (one smoke-test card, `TC-000`) and then never used again — including for every one of today's own merges, which went through direct git branches and ad-hoc Agent-tool verification instead. This is not a hypothetical risk: it is a live, current, previously-unflagged instance of the exact "an elaborate plan was authored, then abandoned after step one" failure mode this project's own `MISSION_AUTHORITY.md` names as a predecessor mistake. |
| 20 | Production Readiness | `FAIL` | By the mission document's own stated "7/8 maturity threshold" standard: zero autonomous execution, zero live publishing, zero live App-authenticated action, zero live issue automation. The parts that ARE production-grade (the cascade's own correctness discipline) are real but are not, by themselves, "production" in the sense G1–G8 define it. |

---

## D. Component and Architecture Inventory (goal-mapped)

| Component | Goal(s) served | Works? | Recommendation |
|---|---|---|---|
| `src/repo_presenter/cascade.py` + S1–S10 stage modules (`readme/evidence`, `readme/reconciliation`, `readme/composition`, `readme/validation`, `readme/review`, `readme/repair`) | G1, G2, G7 | **Yes**, demonstrably (11 fresh independent accepts today) | `KEEP`. This is the project's real asset. Continue the evidence-gated fix-queue discipline that produced today's results; do not rewrite. |
| `src/repo_presenter/core/state/*` (durable git-ref state machine, transitions, recovery) | G1, G2, G6 (application layer) | **Yes**, exercised extensively and successfully today, with one newly-documented freshness-reading nuance | `KEEP`. Add the "repeat-terminal-state last_transition can be stale" lesson (found today) as a permanent, documented reading rule, not a code change. |
| `src/repo_presenter/issues/{model,dedup,approval,file}.py` | G3 | **Partially** — filing path is real and gated, but nothing calls it, and discovery/close were deliberately never ported | `REUSE`/`REPAIR`. Do not rewrite. Wire a real discovery step and a close step, and give it one real caller (even a manual CLI entrypoint would satisfy "operational" before a scheduled one does). |
| `src/repo_presenter/propose/{effect,pull_request}.py`, `authorization/*` | G4, G5 | **No** — has never fired live, zero callers | `REUSE`. Code quality looks reasonable per the research thread; the gap is integration, not implementation. Wire one real, owner-selected, explicitly-authorized first live test against each of the two mandatory G4 repositories, per the mission document's own existing "first live exercise is owner-selected, not agent-selected" rule (already in `plans/idea.md`'s owner-corrections table — this rule already exists, it has just never been exercised). |
| `src/repo_presenter/github/{client,token_provenance,errors}.py` | G5 | **Partially** — can verify an externally-supplied App token; cannot mint one | `REPAIR`. Add JWT-signing + installation-token-minting. This is the single piece of code whose absence blocks G5 outright. |
| `.github/workflows/present.yml` | G6 | **Yes**, for manual dispatch; **no**, for autonomy | `SIMPLIFY` then `EXTEND`. Add a `schedule:` trigger (the workflow's own comment says this is "an owner decision... not yet made" — it is now squarely the owner's decision to make, informed by this report). Do not add Docker speculatively (see §H) until a concrete reason is demonstrated. |
| `ops/SUPERVISOR.md`, `ops/gatecli.py`, `project/taskcards/` | G8 (governance) | **No** — used once, abandoned | `REPAIR` or formally `REMOVE`. Either start actually using it (today's work is proof real discipline exists even informally — formalizing it is a process change, not a technical one) or explicitly retire it in `docs/DECISION_LOG.md` so `AGENTS.md`'s own binding claim stops being false. Leaving it silently unused, as now, is the worst of the three options. |
| `project/state.yaml`'s own top-of-file counters dashboard | G1, G2, G8 (observability) | **No** — self-admittedly stale since 2026-10-31 | `REPAIR`. A single script that reads the real git refs (exactly what one research thread for this report had to improvise) and regenerates this block should run automatically, not be left to go stale again. |
| aspose.org `readme-refresh` skill (sibling checkout, not this repo) | G7 | **Yes**, for its own interactive purpose; **not directly reusable** as Lane L/R's engine | `DEFER` the orchestration-reuse question (refuted by evidence, §B). `REUSE` candidate: pull its deterministic disposition-coverage/retention/diagram checks under the already-sanctioned reuse-manifest discipline — this was apparently never attempted despite being explicitly allowed since day one. |
| Top-level `README.md` | Dimension 16 | **No** — empty | `REPAIR`. Trivial, but a real, currently-true embarrassment for a README-generation project. |

---

## E. Independent Capability Verification

Distinguishing implemented / test-covered / executed / independently verified / accepted /
production-ready / actually delivered, per the directive's own framework:

- **Lane R cascade**: implemented, test-covered, executed (today, dozens of times), independently
  verified (S10's own non-authoring reviewer, plus today's own cold-verifier-subagent discipline
  on 4 separate code fixes), **accepted** for 9 repositories (pipeline-level, not owner-reviewed —
  see the project's own standing distinction between "ready for review" and "owner-accepted"),
  not yet production-ready in the full G1–G8 sense (no autonomous trigger, no publishing).
- **Lane L cascade**: same profile, 12 repositories currently accepted.
- **Issues module**: implemented (filing path), test-covered (unit tests only), **executed once,
  by hand, owner-authorized** (the one real filed issue genuinely went through `file.py`'s own
  code, in local human-token mode — `project/state.yaml`'s own record confirms this), but with no
  discovery or close mechanism and no autonomous or scheduled caller — not independently verified
  as an operating capability, not accepted, not production-ready.
- **Publishing/propose effect layer**: implemented, test-covered (unit tests only), **never
  executed**, not verified, not accepted, not production-ready. Explicitly self-admitted in the
  code's own comments.
- **GitHub App auth**: partially implemented (verify-only), not executed as a minting path (no
  such path exists), not production-ready.
- **Autonomous Docker/CI**: not implemented at all. `UNVERIFIED` is too generous a word — there is
  nothing to verify.
- **aspose.org skill reuse (G7)**: the skill itself is implemented, test-covered, and executed
  (real runs as recent as 2026-10-31) **in its own project**, for its own interactive purpose. It
  has never been integrated into this repository in the way G7 asks about; that specific
  integration is `NOT ATTEMPTED`, not `NOT VERIFIED`.

---

## F. Historical Failure and Accountability Report

### Predecessor 1 — `foss-readme-optimizer`

Primary source: that project's own `POC-FREEZE.md`, read directly during this audit (previously
marked in this repository's own `docs/MISSION_AUTHORITY.md` as "not yet independently inspected"
— that caveat is now out of date; see §G). Between 2026-07-17 and 2026-08-09 the project produced
complete README candidates for four repositories, then **repeatedly re-declared them "not
current" through its own fact/acceptance contract revisions**. Raw historical reach hit 20/31
`FACTS_READY` and 9/31 `NO_OP_PROVEN`; contract-valid reach collapsed to 1/0/0/0. The project's
own freeze document states the root cause plainly: *"the machinery invalidates its own output
faster than it produces it."* A second, compounding failure: the freeze itself (the correct
countermeasure) was never formally marked retired after being superseded in practice around
2026-08-10, which let a later agent read it literally and bypass the (by-then-current) mission
graph again on 2026-08-28, **reintroducing a known defect class** — a stale-authority-document
failure, one level further back than the lesson this repository already explicitly carries
forward from predecessor 2.

### Predecessor 2 — the old `repository-presenter`

Primary source: this repository's own `docs/history-reconstruction.md` (independently
re-verified against the old repo's real git history, not trusted from its own claims) plus a
direct, fresh `git log` count against the old repo on disk (1,378 commits, 2026-09-02 →
2026-10-20, 48 days). The project ended when the owner personally reviewed 34 Lane L bundles and
found, independently of the automated pipeline's own `ACCEPTED` claims: 71/366 example facts
CONTRADICTED, 88 contradicted-or-unresolved links, 30 missing-API findings across 19
repositories, and undetected false format claims — with the pipeline's own `authorizable_candidates`
count sitting at 0 of 36 despite 28 candidates marked sealed. Root cause, independently confirmed
against the actual code: a review-verdict demotion rule
(`components/readme/review/independent/review.py:219,269`) silently folded 27 of 30 real `REJECT`
findings back to `ACCEPT` whenever a finding's quoted span happened to match a literal supported
fact value — a category error (confusing "this phrase is literally true" with "this finding has
no merit"), not a typo. The fix landed 2026-10-10; **the 28 already-sealed candidates were never
re-checked against the fixed reviewer** before the owner's own manual review found the gap ten
days later. A separately-authored 8-card "Lane R dependability rebuild" plan saw only its first
card ever executed. Lane L was quietly demoted to non-primary internally on 2026-10-14 — six days
*before* the owner's own evidence confirmed it was in fact broken, i.e. the scope narrowing
preceded, rather than followed, the evidence that justified it.

### Decision → Rationale → Outcome → Root Cause → Alternative → Prevention

| # | Decision | Rationale | Outcome | Root cause | Better alternative | Prevention |
|---|---|---|---|---|---|---|
| 1 | Old repo's reviewer folds a finding matching a literal supported fact value | "If the words are factually true, the finding is noise" | 27/30 sealed reviews silently folded REJECT→ACCEPT over ~1 month; hid a real dropped security warning | Category error: "phrase is true" ≠ "finding has no merit" | Split rules into ones that may refute (with cited evidence) vs. ones that may only annotate, never fold | A negative-control test pinning exactly this shape now exists in this repository |
| 2 | Ship the reviewer fix without re-checking the 28 already-sealed candidates | Fixing forward seemed sufficient | 28 stale "accepted" candidates stayed trusted for 10 more days | No standing rule that a fix to acceptance logic must reseal everything it previously touched | Any acceptance-logic fix triggers mandatory re-verification of its own prior output | This session's own practice today (fresh live hosted check + cold independent verifier on every merge) is the correct countermeasure, already in active use |
| 3 | Author an 8-card rebuild plan | Structured, sequenced remediation | Only card 1 of 8 ever ran | Plan depth was tracked as progress; nothing gated claiming "in progress" on the dependency actually finishing | Report only verified external outcomes, never plan cardinality | Stage gates requiring evidence, not a card number, before advancing |
| 4 | Demote Lane L to non-primary (2026-10-14) | Appeared to be the weaker lane | The owner's own evidence, 6 days later, confirmed it was in fact broken — but the demotion came first | Scope narrowed ahead of, not in response to, confirming evidence | Narrow scope only after a dated, evidence-backed decision-log entry | This repository's own standing rule: no quiet lane narrowing without a dated `DECISION_LOG.md` entry |
| 5 | `foss-readme-optimizer` repeatedly revises its own acceptance contract while producing output | Each revision seemed like a genuine improvement | Contract-valid reach collapsed to 1/0/0/0 from a raw 20/31 — "invalidates its own output faster than it produces it" | No freeze on the acceptance contract while work was in flight | Time-boxed contract freeze; log defects to a backlog instead of changing the bar mid-flight | The freeze itself was correct but was never marked retired after being superseded — prevention is applying supersession markers the moment they're true, not leaving them for a later reader to infer |
| 6 | **This repository's own 2026-10-21 informal sweep reports 36/34 lane-accepted** | A fast, informal check to get a baseline | The owner personally caught this as a false green on 2026-10-28 and reset the real count to 2/36 and 0/36 | The sweep's own acceptance note admitted "no automated rerun/no-op proof exists... every ACCEPT was a one-time manual/agent-assisted verification," but the headline number was reported and persisted anyway | Never report a headline acceptance count without the independently-built non-authoring reviewer this project did not yet have at the time | Already corrected once (2026-10-28); needs to stay corrected — `state.yaml`'s own dashboard going stale again since 2026-10-31 is the same risk recurring in a milder form (§C dim. 13) |
| 7 | **This repository's own taskcard/supervisor-worker mechanism used once, then abandoned** | Built day one as the project's own governance answer to predecessor failures | Never used again, including for all of today's real merges | No decision-log entry ever recorded choosing the informal path instead — it simply stopped being used, unflagged | Either use it, or retire it on the record | Neither has happened yet; this audit is the first place it is named |

---

## G. Strengths and Weaknesses Assessment

**Strongest assets (real, independently validated, retain without rewriting):**
- The evidence/fact-polarity model and the independent non-authoring reviewer design — directly
  descended from, and a genuine correction of, predecessor-2's own worst defect, and proven
  resilient under real adversarial testing today.
- The durable git-ref state machine — sophisticated, real, and the actual mechanism this very
  audit's acceptance tally depended on.
- The practiced (if informal) fix-queue discipline exercised today: real downloaded hosted
  evidence → real reproduction → real falsifier → real cold independent verification → real live
  re-check → honest decision-log entry. This is, in miniature, exactly what both predecessors
  lacked.

**Weakest areas (directly block delivery, by severity):**
1. Zero autonomous execution (G6) — the single largest gap between "it works when I run it" and
   "it is production."
2. Four capabilities (G3–G5, part of G6) exist only as unexercised library code with no caller.
3. The project's own governance mechanism for preventing exactly this kind of drift has itself
   silently drifted.
4. Observability has already gone stale once in 12 days, and nothing prevents it happening again.

None of these four requires a rewrite. All four are integration/process gaps around a core that
already works.

---

## H. Alternative Architecture Comparison

1. **Current approach (keep the cascade, wire the shell):** lowest risk, most reuse, fastest
   plausible path — see §I. Recommended.
2. **Minimal-rework "thin wrapper around aspose.org's skill" (as G7 originally floats):**
   **refuted by direct evidence** — the skill requires an interactive human/agent session to
   author content; it has no programmatic generation call to wrap. Adopting it as the engine
   would mean reintroducing a human-in-the-loop step, directly contradicting G6. Not recommended
   as the primary engine; recommended only narrowly, for its deterministic checks (see §D).
3. **Full rewrite:** no evidence anywhere in this audit justifies this. The core cascade is the
   project's best asset and the one thing that demonstrably works; a rewrite would restart the
   clock on the one capability already proven, to chase capabilities (G3–G6) that are gaps in
   wiring, not gaps in design.

**Recommendation: alternative 1, with the narrow G7 reuse pull from alternative 2 folded in as a
bounded, separate task.**

---

## I. Prioritized Corrective Plan

Ordered by dependency, each item tied to a specific goal, each with a measurable gate. No item
below is speculative infrastructure or scope expansion — everything is either a goal named in
G1–G8 or a documented production-safety dependency.

1. **Decide, on the record, what to do with the abandoned taskcard mechanism.** (Governance,
   underpins G8.) Gate: one `DECISION_LOG.md` entry, either "reinstating supervisor/worker
   taskcards starting now" or "formally retiring `ops/gatecli.py`/`ops/SUPERVISOR.md`, informal
   discipline continues instead." Either answer is fine; silence is not.
2. **Automate the portfolio-count dashboard** (`state.yaml`'s own stale counters; underpins G1/G2
   observability). Gate: a script that reads the real git refs (the exact method this audit's own
   research thread had to improvise) runs and the file stops needing a manual research pass to
   trust.
3. **Give the issues module one real caller** (G3). Gate: discovery + file + dedupe fires, once,
   against one real, owner-named repository, with the result independently checked (not
   self-reported) the same way this session verified today's code fixes.
4. **Add App-token minting to `github/client.py`** (G5, blocks G4). Gate: a real installation
   token is minted and verified by the existing `verify_installation_token` path, end to end, once.
5. **Fire one real, owner-authorized candidate publication against each of the two mandatory G4
   repositories.** Per the mission document's own existing rule (already written, never
   exercised): the owner personally names the first live target, the agent executes exactly that.
   Gate: one real, bot-authored PR against `cells/net`, one against `3d/python`, each
   independently confirmed via `gh api` the same way this audit confirmed their absence today.
6. **Decide the G6 scheduling question.** The workflow's own comment already frames this as a
   pending owner decision (cadence, provider spend). Gate: either a `schedule:` trigger exists and
   has fired once unattended, or a dated decision-log entry explains why not yet.
7. **Continue the already-proven fix-queue sweep toward the 25+ targets** (G1/G2) — this is
   already working; today is the evidence. No process change needed here, only continuation.
8. **Pull aspose.org's deterministic checks under the existing reuse-manifest discipline** (G7,
   lowest priority of the eight — real but not blocking). Gate: at least one of
   disposition-coverage/retention/diagram checking is demonstrably informed by (not copied
   wholesale from) the sibling skill's own incident-tested logic.
9. **Write a real top-level `README.md`.** Trivial, but currently a true, citable embarrassment.

Items 1–6 are the ones that actually move G3–G6 from `FAIL` to real. Item 7 is already in motion
and should not be paused for the others. Item 8 is explicitly lower priority, matching G7's own
"optional acceleration, not another authority" framing.

---

## J. Production Readiness Verdict

- **Production-ready today:** the Lane R/Lane L cascade itself, as a verified local-evidence
  generator — not as an unattended production system.
- **Can already run autonomously:** nothing. Every execution path requires a human-initiated
  trigger.
- **Can already produce accepted candidates:** yes — 9 Lane R, 12 Lane L, independently reviewed,
  not self-graded.
- **Publishing and issue-management capabilities that actually work today:** none, in the sense of
  "has ever fired against a real target from this codebase." Both have real code and zero
  real-world exercises.
- **Minimum remaining work:** items 3–6 of §I — give the three unused capabilities (issues,
  publishing, App auth) one real caller each, in dependency order, each gated on independent
  confirmation.
- **What prevents unattended production operation:** the complete absence of a scheduled trigger
  and of Docker/local-runner validation (G6), compounded by the fact that three of the four
  capabilities a schedule would need to call have never been exercised even by hand.
- **Shortest defensible path to completion:** wire, don't rebuild. The core is real; the shell
  around it is a short, concrete, dependency-ordered list (§I), not a redesign.

---

## Confidence Notes

Everything in §B, §C rows 1–2/6/12/16/17/19/20, §D, §F, and §J rests on primary-source citations
gathered directly during this audit (file reads, `git log`/`gh api` calls, durable-state-record
reads) and is high-confidence. §C rows 8 and 10 (security depth, performance/scale) were not
independently audited this pass and are marked `UNVERIFIED`/`PARTIAL` honestly rather than padded.
§F's predecessor-1 causal chain beyond the quoted `POC-FREEZE.md` text (its own referenced
`Decision #114`, later logs) was not followed further in the time available and should be treated
as a lead for a future, deeper pass if it matters to a specific decision.
