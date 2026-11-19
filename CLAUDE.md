# CLAUDE.md — Repository Presenter

**STOP — before anything else, read `docs/RULINGS.md` in full.** It holds every binding owner ruling (R1–R49) and the
pre-work checklist; a SessionStart hook prints it into every new session, and `tests/test_rulings_in_focus.py` fails
CI if this pointer or any ruling disappears. Then read `AGENTS.md`.

Non-negotiable summary (details in `docs/RULINGS.md`):
- Judge every action by **candidates produced**: Lane L 100% handled, Lane R ≥ 85% independently accepted (R44, supersedes ≥ 25 per lane), never by machinery built (R27, R31).
- **Architecture freeze**: fixes to existing components only; the PHP extractor is the one sanctioned exception (R27, R29).
- **Never lose a seal** on a version bump; re-certify (R10). **Never drop live README content** without a recorded decision (R14).
- **No attribution or provenance wording** in any public README (R9).
- **No upstream push** before every candidate of both lanes passes; draft PRs only, allowlist (R15, R3, R22).
- **Decide, don't ask** the owner; report results first; when stuck, change approach (R11, R12).
- **Feedback is global** (R41): a fix applies to both lanes and every candidate; done only after every candidate is re-verified under the fixed code, with evidence.
- **Upstream-caused blockers** (R42): aspose.org's published readme-refresh candidates are the quick reference — adopt their approach for quick fixes, beat it where we can, decide case by case where it is wrong; always implemented in the pipeline globally.
- **Lane R throughput** (R43): rolling-12-run stop rule; deterministic Dev & Testing / Docs & Resources / Scope; inherit-and-correct for aspose.org-published repos (near-term; keep lanes separately evaluable long-run); API rows fall back on failure.
- **Budgets measure, never block** (R45): provider caps, batches, the envelope and the rolling window report usage and cost per seal and never halt work; the owner sets any value; `data/provider_budget.json` `enforcement: measure`. An unproductive window is diagnosed (R36), not waited on.
- **Feedback cycle** (R47): new feedback starts investigation > execution > verification at once; when honored, rebuild and republish the README Candidate Review page (`scripts/review_page/build.py`).
- **Supervisor conduct** (R48): never idle while processes run (investigate Lane R, R46); questions to the owner only through the interactive form; every agent briefed with the goal and `docs/RULINGS.md`, no deviation.
- **Deploy by end of week** (R49): every component running on GitHub Actions by 2026-11-22; the quality bar is not lowered for the date; report conflicts first.
- **Lane R trust** (R46): universal, robust, reliable, repeatable and proven on the hosted runner across the whole portfolio. Idle time is Lane R investigation time; every Lane R change names the property it improves; class fixes only. Bar: ≥ 85% of 40 cells seal in one frozen-code hosted pass, repeat agrees on ≥ 90%.
- **Backlog** (R40, `project/backlog.yaml`): every requirement, defect and feedback is an item with source, acceptance and evidence; never closed without proof.
- **Pipeline-first** (R38, `docs/R38_PIPELINE_FIRST.md`): execute only through the governed, reproducible pipeline; first principles + Pareto; done = reproducible + verified + evidenced. Re-check `docs/R38_CHECKPOINT.md` from time to time.
- **The system runs itself on GitHub Actions** (R37): never do by hand what the hosted loop should do; the session oversees and fixes.
- **Never park a blocker** (R36): verify it, list honest alternatives, decide one; classify failures portfolio-wide and fix each class once at the root, proven locally before hosted runs; question the checks and their data too.
