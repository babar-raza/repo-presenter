# The second complete, real Lane R cascade — a different ecosystem, proving it's not a one-off

2026-10-22. `aspose-cells-foss/Aspose.Cells-FOSS-for-Go`. The first full S3→S4→S5→S6→render
cascade was proven for exactly one repository (`aspose-3d-foss/Aspose.3D-FOSS-for-Python`, see
`lane_r_first_full_cascade/`). This entry fires the identical cascade against a second
repository, deliberately a different ecosystem (Go, not Python) and a different family (Cells,
not 3D), to test whether the machinery generalizes or was tied to the first repository's own
shape.

## A real bug found and fixed before trusting this run

The second run crashed on its first attempt at S5 (`presentation_planning`):

```
repo_presenter.core.errors.ConfigError: no ecosystem spec registered for 'go' (known: net, python)
```

Traced precisely, not patched blindly: every ecosystem's `EcosystemSpec` self-registers into
`core.ecosystems.SPECS` only when its own `platforms/<ecosystem>.py` module is imported (by
design — `core/` may not import an extractor itself). The real production pipeline
(`scripts/run_lane_l.py`) already triggers this via `extractors/platforms/registry.py`'s
`plugin_for(ecosystem)` before any stage asks `spec_for()` for the same ecosystem. This
session's own `scripts/run_lane_r_{planning,authoring_real,render}.py` read only pre-built
`facts.json` and never touch the extractor layer otherwise, so nothing had imported
`platforms/go.py` in that process before `planning.plan_checks()` →
`placement.placements()` → `renders_verbatim()` → `spec_for("go")` needed it. This is a real
bug in this session's own new scripts, not a deeper architectural defect — confirmed because
`platforms/go.py` (and every other non-Python, non-.NET platform module) already correctly
self-registers via `SPECS.setdefault(...)` at its own import time; nothing was missing except
the import itself. Fixed by calling `plugin_for(ecosystem)` at the start of all three affected
scripts' `main()`.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 2 (batched, 75 units) | Both batches accepted on the first attempt. 75/75 units disposed: 32 `OMIT_UNSUPPORTED`, 24 `VERIFIED_PRESERVE`, 15 `SUPERSEDE_REDUNDANT`, 4 `VERIFIED_MOVE`. |
| S5 `presentation_planning` | 1 (after the fix above) | Accepted on the first attempt, with the real `plan_checks`. 8 core capabilities, 12 API hubs, 1+6 examples, 3 material limitations, 13/18 sections included. |
| S6 `section_authoring` | 6 (one per real authored task) | All 6 accepted on the first attempt, with the real `unit_checks`. 36 content units merged. |
| Render | 0 (deterministic code) | 22,203 characters, 477 lines. |

Every real provider call across S3–S6 (10 total) was accepted on its first attempt, the same
as the first cascade run. The Mermaid At a Glance diagram renders with correct bracket syntax
(`Product["Aspose.Cells FOSS for Go"]`), confirming the earlier `glance.py` fix generalizes to
a second repository's own capability set, not just the first's.

## The same honest, measured defect repeats — confirming it is systemic, not a fluke

The rendered README again carries two near-duplicate opening paragraphs (lines 5 and 7–11 of
`README.rendered.md`), the identical shape documented in `lane_r_first_full_cascade/`: a
`VERIFIED_PRESERVE` into the LLM-authored `opening` section, alongside the fresh authored
content for that same slot. Seeing the exact same defect shape on a second, unrelated
repository's own cascade confirms this is a systemic gap in the ported subset (traced
precisely in the first entry: `coverage_findings()`'s self-audit only checks a `PLACING`
disposition into a *deterministic* section, never an LLM-authored one), not something
specific to the first repository's facts or disposition shape.

## Honest scope limits

- Still only 2 of 36 repositories. The real bug found here (missing `plugin_for()` call) was
  specific to running these scripts for an ecosystem other than the first one tried
  (`python`), which happened to work without the fix only because `core.ecosystems.SPECS`
  already has `python`/`net` built in directly — a third ecosystem run would not have
  surfaced this fix were it not for `net`/`python` being special-cased in `ecosystems.py`
  itself (see that module's own comment on why).
