# R38 — Mandatory Principle: Pipeline-First Execution, First Principles, and Pareto Optimization

Owner ruling, 2026-11-13, recorded verbatim. Binding on every agent and every task. "Make sure the agent working on
task must check it from time to time." — it is re-injected into the working agent's context on every owner prompt
(`.claude/settings.json` UserPromptSubmit hook printing `docs/R38_CHECKPOINT.md`), printed at every session start with
`docs/RULINGS.md`, included in every worker brief, and guarded by `tests/test_rulings_in_focus.py`.

---

**Mandatory Principle: Pipeline-First Execution, First Principles, and Pareto Optimization**

All execution tasks must be performed through existing or appropriately extended repeatable, deterministic,
verifiable, and governed pipelines. Manual, one-off execution must not substitute for a reusable process.

## 1. First-principles reasoning

* Examine the actual objective, underlying constraints, source of truth, and required outcomes before choosing an
  implementation.
* Challenge inherited assumptions, unnecessary complexity, and ineffective existing approaches.
* Prefer the simplest technically sound solution that satisfies the objective and established governance.

## 2. Pareto-driven prioritization

* Identify the highest-impact changes that deliver the greatest improvements in quality, reliability, and throughput.
* Prioritize removing systemic bottlenecks over repeatedly fixing individual symptoms.
* Never use Pareto prioritization to skip mandatory requirements, safety checks, verification, or acceptance criteria.

## 3. Pipeline-first execution

* Discover and reuse existing pipelines, skills, tools, and automation before introducing anything new.
* Where a necessary capability is missing, extend the smallest appropriate existing component rather than creating a
  parallel system.
* Ensure recurring operations are reproducible without relying on undocumented agent actions.
* Manual investigation, diagnosis, and human-required approvals are permitted; manual production execution is not a
  substitute for the governed pipeline.

## 4. Verification and evidence

* Verify pipeline behavior and outputs against independent sources of truth.
* Preserve execution logs, inputs, outputs, decisions, and verification evidence sufficient to reproduce and audit the
  result.
* Ensure fixes address the underlying process, not merely the immediate output.

## 5. No unnecessary architecture expansion

* Do not introduce new frameworks, services, pipelines, or abstractions unless an evidenced gap demonstrates their
  necessity.
* Prefer incremental changes that improve the existing system.
* Do not rebuild working components merely to make them more automated.

## 6. Execution responsibility

* The absence of an existing pipeline is a capability gap to investigate and resolve, not an automatic reason to
  abandon the task.
* Implement the minimum necessary reusable capability, validate it, then execute the requested task through it.
* Preserve existing governance, state machines, approval requirements, rollback mechanisms, and publication gates.

**Acceptance criterion:** A task is not considered complete merely because its immediate output exists. Its execution
must be reproducible through the governed pipeline, its results must be verified, and the required evidence must be
available.
