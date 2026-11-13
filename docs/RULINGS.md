# OWNER RULINGS — read this first, every session, every agent

**This file is binding and is read before any work.** It is printed into every new Claude Code session by the
SessionStart hook in `.claude/settings.json`, referenced on the first lines of `AGENTS.md` and `CLAUDE.md`, and
guarded by `tests/test_rulings_in_focus.py` (CI fails if any reference or ruling goes missing). The full text and
provenance of R1–R27 is in `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part B and Part E; where this summary and that
text differ, that text governs. A new owner ruling is added here and there in the same commit.

## The goal (one paragraph)

Deliver high-quality README files across the authorized Aspose FOSS portfolio, through two independent lanes —
**Lane R** (regenerate) and **Lane L** (maintain the live README with only evidence-justified edits) — with **at
least 25 certified candidates in each lane** out of the portfolio, at or above the published aspose.org
readme-refresh benchmark, preserving valuable maintainer content, every claim verified, and real upstream delivery
(draft PRs) only once every candidate of both lanes passes. **Judge all work by certified candidates produced, not
by machinery built.**

## Before you do anything, check

1. Does this work move a certified-candidate count, or remove a named blocker of one? If not, do not do it (R27, R31).
2. Is it a fix to an existing component, not new architecture? (R27; the only sanctioned exception is R29.)
3. Will it lose or demote a seal? It must not (R10); a newly failing seal needs a justified genuine defect.
4. Does it drop anything from a live README? Only with a recorded decision and rule (R14).
5. Does any public README text carry attribution/provenance wording? It must not (R9).
6. Is it an upstream write? Not before every candidate of both lanes passes (R15), PRs only, drafts, allowlist (R3/R22).
7. Am I about to ask the owner something I can decide? Decide (R11). Stuck after repeated tries? Change approach (R12).

## New rulings, 2026-11-13 (owner)

| # | Ruling |
|---|---|
| **R28** | **Words Java is a machine port of Words .NET**, not standard native Java. Its README work needs dedicated handling (port-aware facts and examples; API naming follows the port, not idiomatic Java assumptions). Treat as a recorded work item; do not present it as a native Java library. |
| **R29** | **A PHP extractor is needed** (Cells PHP). This is the one sanctioned exception to the R27 freeze: add a PHP platform plugin in the existing plugin pattern (`extractors/platforms/`), nothing broader. Until it exists, Cells PHP is registered but inactive. |
| **R30** | **PDF Go MCP is out of scope at this stage** (maybe in future). Excluded in `data/registry_exclusions.json`. |
| **R31** | **Provider budget reset.** The LLM budget is reset (new envelope in `data/provider_budget.json`) and may be spent on anything that **improves the certified numbers** — never on building machinery. Spend that does not move a count, or remove a blocker of one, is a defect. |
| **R32** | **Sweep pause lifted** (`OWNER_RULING_SWEEP_PAUSE: LIFTED` in `docs/DECISION_LOG.md`), on the condition that it is used to produce results: portfolio runs proceed, judged by certified counts after every wave. |
| **R33** | **"Accepted" is defined by the acceptance contract**: a candidate is independently accepted when it re-certifies under current code and holds an attested M9 acceptance record under a PASSED `data/acceptance_calibration.json`. The frozen `data/reviewer_calibration.json` (NOT_PASSED, iteration 5) no longer gates counting or upstream writes; this replaces R3's "reviewer calibration PASSED". Condition: it is used to produce results. |
| **R34** | **Portfolio grows to 41 products**: the 36 plus OCR .NET, OMR Python, PSD Java, Words Java (R28) and Cells PHP (R29, inactive until its extractor exists). |
| **R35** | **Lane L finish line**: 25 Lane L candidates that each remove at least one real, verified defect (R21 net improvement). A product with no warranted change is `NO_ACTION_JUSTIFIED` — a terminal outcome reported separately, never counted toward the 25 (R16). |

## All rulings in force (one line each)

| # | Topic | Ruling |
|---|---|---|
| R1 | Record order | Consolidated goals are the top authority; conflicting lower records are amended. |
| R2 | Benchmark | A candidate must equal or exceed the published aspose.org README for that product. |
| R3 | Upstream writes | Allowlisted repositories only, every gate passing, first PR a draft; calibration gate per R33. |
| R4 | Target | About 25 accepted per lane, counted independently. |
| R5 | Lane L trigger | A verified upstream change and a verified defect; minimal, byte-preserving edits. |
| R6 | New sections | Specific content-describing headings allowed; generic catch-alls forbidden. |
| R7 | Issues | Upstream: product/source defects only; here: own blockers. |
| R8 | Resumption | `dispatch-next` / `worker-tick` and a scheduled supervisor tick. |
| R9 | Attribution | Internal only; never in a public README in any form. |
| R10 | Seals | One standard for all candidates; a version bump never loses a seal; re-certify, never regenerate for a version. |
| R11 | Conduct | Decide, don't ask; report results first; parallel workers. |
| R12 | Stuck | After repeated failure, change approach from first principles; solve once. |
| R13 | Coverage | Complete portfolio or at least 25 per lane; never a handful of pilots. |
| R14 | Drops | Every live-README drop examined, decided, recorded and calibrated. |
| R15 | Push timing | No upstream push before every candidate of both lanes is sealed, validated and passed. |
| R16 | No-edit Lane L | `NO_ACTION_JUSTIFIED` is terminal but never counted toward 25. |
| R17 | Sandbox | Upstream-write mechanics proven on an owner sandbox before R15 holds. |
| R18 | Model | qwen3-next for every product route. |
| R19 | (superseded by the Final Directive) | |
| R20 | Lane L done | Strict R5; done when every repository has a terminal outcome. |
| R21 | Lane L bar | Net improvement: every edit verified, no new defect, at least one real defect removed. |
| R22 | Write authority | One authority, draft PRs only, nine allowlisted repositories. |
| R23 | (superseded by R25, now R31) | |
| R24 | External blockers | A verified upstream defect makes a repository terminal for R15. |
| R25 | Budget envelope | Superseded in amount by R31's reset; batches of six, measured cost. |
| R26 | Prose judge | Measure M8 first; fallback ladder only on a recorded failure. |
| R27 | **Architecture freeze** | Only fixes that make the existing system work; judge work by certified candidates. |
| R28–R35 | 2026-11-13 | See the table above. |
| Final Directive | Continuous execution | PLAN → DISPATCH → EXECUTE → VERIFY → INTEGRATE → UPDATE STATE → NEXT; never stop at a report. |
