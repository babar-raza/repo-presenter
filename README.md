# repo-presenter

Evidence-gated README generation and repair for authorized product repositories, run as a
durable, reviewable pipeline (two independent lanes — a full regeneration and a minimal-edit
correction — over a fact-polarity evidence model with a non-authoring independent reviewer).

This is the control repository: it holds the pipeline's source, its durable per-repository
state, and the sealed candidate bundles it has produced. It does not hold the product
repositories' own READMEs directly; see `data/registry.json` for the portfolio it operates over.

## Where to start

- **What this project must do, for whom, with what quality bar:** `docs/MISSION_AUTHORITY.md`.
- **What must get fixed before that counts as delivered:**
  `docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` — owner-adopted binding authority, not a
  one-time report. Read it, including its `§K` amendment, before treating any other planning
  document as current.
- **What is currently true, in progress, or blocked right now:** `project/state.yaml` (the only
  execution cursor — never hand-edited).
- **Binding authority table and roles for anyone working in this repository:** `AGENTS.md`.
- **Why a given decision was made, and what it deliberately did not decide:**
  `docs/DECISION_LOG.md`.

## Running it

```
pip install -e .
PYTHONPATH=src python scripts/run_cascade.py <owner>/<repo> <ecosystem> <clone_path>
PYTHONPATH=src python scripts/portfolio_status.py
```

`requirements-lock.txt` is advisory only — see its own header before assuming it is enforced in
CI. `.github/workflows/present.yml` is the one hosted workflow; it currently triggers only on
`workflow_dispatch` (manual).
