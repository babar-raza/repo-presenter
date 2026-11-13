# R40 — Persistent, autonomously managed backlog

Owner ruling, 2026-11-13, recorded verbatim. Binding. The backlog itself is `project/backlog.yaml`, checked by
`ops/checks/backlog_check.py` (CI); requirements traceability stays in `project/mission_matrix.yaml`.

---

Maintain a persistent, structured, and continuously updated backlog covering all project goals, requirements, tasks,
defects, gaps, technical debt, blocked work, and deferred improvements.
Manage the backlog autonomously, including discovery, deduplication, prioritization, dependency tracking, status updates,
execution scheduling, verification, and closure.
Additional requirements:

1. Requirements completeness: Reconstruct and reconcile all requirements from the original instructions, project goals,
plans, decisions, and subsequent feedback. Identify and incorporate anything previously missed, misunderstood, partially
implemented, or silently dropped. Do not invent requirements.
2. Pipeline-only execution: All repeatable work must run through the project's established, reproducible pipelines,
applying both first-principles and preto principles as previously defined. Do not substitute manual execution for
missing or broken automation; fix or extend the pipeline where justified.
3. Autonomous management: Continuously select and execute the highest-priority eligible work, respecting dependencies,
governance, existing authority boundaries, and verification gates. Do not require human intervention for decisions
already delegated to automation.
4. Backlog integrity: Every requirement must have a traceable status, implementation path, acceptance criteria, and
evidence. Preserve unfinished work across sessions. Never silently discard, downgrade, or mark items complete without
proof.
5. Continuous reconciliation: Compare actual implementation and observed outcomes against the original requirements.
Reopen incomplete or incorrectly closed tasks and create backlog items for newly discovered gaps.
6. Honest reporting: Clearly distinguish verified facts, assumptions, interpretations, uncertainties, failures, and
unverified claims. Never fabricate progress, inflate completion percentages, hide blockers, or present intended behavior
as implemented functionality.
7. Evidence-based completion: Close work only after reproducible verification demonstrates that its acceptance criteria
are satisfied. Record relevant commands, logs, test results, artifacts, and commits.
8. Efficient execution: Reuse existing architecture, skills, tools, and pipelines. Avoid unnecessary redesign,
duplicated work, speculative improvements, and repeated analysis without actionable outcomes.
9. Failure recovery: Investigate failures, identify root causes, record corrective actions, and resume safely through
the pipeline. Escalate only genuine authority, access, policy, or irrecoverable blockers.
10. Transparent progress: Maintain an accurate view of completed, active, pending, blocked, and deferred work, including
what remains, why it remains, and what should execute next.

Critical instruction: Independently verify these requirements against the project's actual state and governing
instructions. Challenge my assumptions and your own conclusions rather than blindly accepting them. If something is
infeasible, contradictory, unauthorized, or unsupported, explain precisely why and propose the smallest viable correction.
Success means delivering the original project goals through a reliable, repeatable, autonomously managed system—not
merely completing taskcards, producing reports, or claiming progress.
Be completely truthful. Unsupported claims, concealed failures, and unnecessary analysis waste tokens, time, and
resources. Prioritize verified outcomes over apparent activity.

---

## Supervisor's independent verification (2026-11-13)

- **Existing mechanism, reused (R38):** `project/mission_matrix.yaml` already tracks goals G1–G… with evidence-gated
  COMPLETE (checked by `ops/checks/mission_matrix.py`); taskcards + `project/state.yaml` gate verified work. It was stale
  (last 2026-11-04/07) and held goals only. The backlog extends it (`project/backlog.yaml`, items link to matrix rows),
  not a parallel system.
- **Feasibility limit, stated plainly (requirement 3):** GitHub Actions autonomously executes the *repeatable pipeline*
  work (candidate generation, re-certification, M9 audits, issue maintenance — R37). Backlog items that need *code
  changes* cannot be executed by Actions: no agent runs there, and none is authorized to. Smallest correction: those
  items are selected and worked by scheduled agent sessions (the hourly watcher in the supervisor session), always
  landing through PR + CI + the gates; Actions reports the next eligible item every tick.
- **Contradiction check:** "close only with reproducible evidence" (requirement 7) matches the matrix rule; "do not invent
  requirements" (1) means every backlog item cites its source (owner message, ruling, decision-log entry, feedback id).

## How dropped work is prevented (owner: "how to best track it", 2026-11-13)

Root causes of the silently dropped items found by the 2026-11-13 reconciliation: follow-ups that existed only in prose
(decision log, plans, worker reports); items with no freshness signal; nothing comparing claims with reality (four
"done" branches existed only locally). Mechanical answers, all in the existing checker `ops/checks/backlog_check.py`
(CI via `tests/test_backlog_check.py`; printed by the hourly hosted `supervisor-tick` under "Backlog"):
1. Every task card not ACCEPTED/SUPERSEDED on the release-gate dashboard must be named by a backlog item (CI fails).
2. Every decision-log entry dated 2026-11-14 or later must carry a `Backlog:` line naming BL ids or `none` (CI fails).
3. A `done` item citing a commit that is not in the history is refused (not landed).
4. Staleness by status age (`updated` field; active 3 days, blocked 7 days per R24, open 14 days) is reported every
   tick and fails with `--strict`.
5. Pre-work checklist item 11 in `docs/RULINGS.md`; every worker brief asks for follow-ups as backlog items.
