# README Candidate Review page (owner: "lets maintain it", 2026-11-13; backlog BL-009)

- **URL:** https://claude.ai/artifact/8HFgxgu6vDRubMuNhr3pEc (private to the owner; `db` capability).
- **What it shows:** every seal that RECERTIFIES under current code — Lane R and Lane L — rendered (links resolved at
  the pinned revision, images embedded, mermaid diagrams drawn), the diff from the live README for both lanes, the raw
  Markdown, R16 no-op and audit-accepted markers, and a per-candidate verdict + note.
- **Rebuild (reproducible, R38):** `python scripts/review_page/build.py --out <file.html>` (needs the state remote; pass
  `--mermaid <mermaid.min.js 10.9.1>` when the npm registry is unreachable). Then republish that file to the URL above
  with the Artifact tool (a session step: Actions cannot publish artifacts). Rebuild after every wave that changes seals.
- **Owner feedback:** the artifact's `feedback` collection (doc id = candidate id; fields verdict, note, repository,
  lane, revision, seal, updatedAt). An hourly scheduled check in the supervisor session reads it; every entry becomes a
  `project/backlog.yaml` item (treated as a global requirement unless it says otherwise).
