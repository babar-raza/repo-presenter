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
- **Feedback cycle (R47, owner 2026-11-19):** a new or changed feedback entry starts investigation > execution >
  verification immediately (the standing watcher runs it in the same turn it finds it). When the feedback is honored
  and verified, the supervisor rebuilds this page with the command above and republishes it to the same URL, so the
  owner can review the result against their own feedback. The page is never left stale after a honored feedback; the
  refresh is part of the cycle's definition of done.

## Hosted on the runner (BL-760, BL-761; owner R47/R49/R50, work package WP-6)

- **Rebuild and host without a session:** `.github/workflows/review-page.yml` runs `scripts/review_page/build.py` on the
  state refs (zero provider calls) after every successful `recertify` run on main, daily, by hand, and by run request
  `{"job": "review-page"}`. It keeps the page as the `review-page` workflow artifact (90 days) and force-pushes one orphan
  commit to the `review-page` branch (`index.html`, `build.json`). Neither needs an owner action. A browser renders the
  page in place only through GitHub Pages: set the repository variable `REVIEW_PAGE_PAGES=true` and Pages source
  "GitHub Actions", and the workflow's `pages` job deploys the same site (an opt-in; without it the job is skipped).
- **Feedback on the hosted copy:** the artifact `db` is not reachable from Actions, so "Save feedback" there opens a
  prefilled GitHub issue (label `review-feedback`, a `<!-- review-feedback {...} -->` block with the same fields as the
  artifact documents). `.github/workflows/feedback-intake.yml` files it as a `type: feedback` backlog item at once (issues
  event; a 6-hourly sweep as a safety net; run request `{"job": "feedback-intake"}`): branch `feedback-intake/run-<id>`,
  a pull request where the repository allows Actions to open one, and a comment on the issue naming the item.
  `scripts/review_page/feedback_intake.py --snapshot-dir <dir>` imports artifact-db snapshots in the old format.
- **Still a session step:** republishing the Claude artifact above (the Artifact tool cannot run in Actions) and starting
  the investigation > execution > verification cycle on a filed item (R47); the intake only removes the wait for a session
  to notice the feedback.

