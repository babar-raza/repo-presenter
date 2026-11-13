R38 CHECKPOINT (owner ruling, full text docs/R38_PIPELINE_FIRST.md) — check before and during this task:
1. First principles: what is the real objective, the source of truth, the required outcome? Simplest sound solution?
2. Pareto: am I removing a systemic bottleneck (a class), or patching one symptom? Never skip mandatory checks.
3. Pipeline-first: is this being executed through the governed, reproducible pipeline (GitHub Actions, R37)? Reuse or minimally extend; no manual one-off production execution.
4. Evidence: verified against an independent source of truth; logs/inputs/outputs/decisions preserved.
5. No unnecessary architecture; 6. a missing pipeline is a gap to fix, not a reason to stop.
Done = reproducible through the pipeline + verified + evidence available, not merely "the output exists".
