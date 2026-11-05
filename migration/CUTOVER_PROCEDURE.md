# Cutover procedure: repo-presenter -> single maintained `repository-presenter`

**Status: PREPARED, AWAITING OWNER AUTHORIZATION. Nothing in this document has been executed.**
Executing any step touching the legacy GitHub or GitLab repositories is prohibited until the owner
authorizes it in writing (recorded as `OWNER_RULING_CUTOVER: AUTHORIZED` in `docs/DECISION_LOG.md`).

## 0. Preconditions (all must be mechanically true; re-check on the day)
1. `python ops/checks/mission_matrix.py` passes and every G1-G8/P1-P5 row is `COMPLETE` or
   `IMPLEMENTED_AND_VERIFIED_EXTERNAL_EFFECT_PROHIBITED` with its prohibited effect owner-cleared.
2. `python ops/gatecli.py validate` reports TC-012a ACCEPTED (it depends on TC-002, TC-009b, TC-010a, TC-011).
3. `data/reviewer_calibration.json` status `PASSED` (TC-007).
4. Salvage table (`migration/reuse-manifest.yaml`) has no row marked `PENDING`; every predecessor
   capability maps to a successor file or an explicit, owner-accepted drop.

## 1. Freeze and snapshot the predecessor (read-only; do not push)
- Record predecessor GitHub and GitLab default-branch SHAs, tags, open PRs/issues, Actions secrets
  *names* (never values), branch protection, and webhooks into `migration/predecessor_snapshot.yaml`.
- Take a full mirror: `git clone --mirror <legacy GitHub>` and `<legacy GitLab>` into offline storage
  (bundle files). This is the recoverable predecessor state; keep until the owner releases it.

## 2. Dry-run the replacement outside the legacy repositories
- Push the successor to a fresh, empty repository the owner creates (e.g. `repository-presenter-next`).
- Run CI, one hosted `present` pilot per lane, and the Docker image there. Confirm state refs, secrets
  and the GitHub App installation work with no reference to legacy URLs (`grep -r` for legacy slugs).

## 3. Cutover (owner-authorized, owner-executed or explicitly delegated)
1. Announce freeze; disable legacy schedules/workflows.
2. Replace legacy default branch content with the successor history (force-push only with explicit
   authorization), or archive legacy and rename the successor into its slug; mirror to GitLab.
3. Re-install the GitHub App on the final slug; rotate and re-set Actions secrets.
4. Re-enable schedules last, only after `scheduled_execution_gate.py` predicates hold.

## 4. Verification after cutover
Dispatch one pilot per lane; confirm candidate bundle, durable-state record and CI green; confirm zero
writes to upstream Aspose repositories (audit via GitHub API reads).

## 5. Rollback
Restore from the step-1 mirrors (`git push --mirror` from the bundle) and re-enable legacy workflows.
Rollback needs only the step-1 artifacts, so keep them until sign-off.
