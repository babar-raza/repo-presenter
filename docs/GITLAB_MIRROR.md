# GitHub to GitLab mirror

GitHub `babar-raza/repo-presenter` is the source of truth. The
`Mirror GitHub to GitLab` Actions workflow replaces the Git contents of
`https://gitlab.recruitize.ai/sialkot/cantt-smallize/repository-presenter`.
It mirrors every branch, tag and `refs/repository-presenter-state/**` ref,
including force updates and deletions. GitLab-only refs in those namespaces
are deleted. GitHub pull-request refs, GitLab merge-request refs and other
service-managed refs are excluded.

Every push and branch/tag deletion requests reconciliation. Manual dispatch
is available. The 15-minute schedule catches custom state-ref changes and
pushes made with GitHub's workflow token, which may not launch another Actions
workflow. GitHub schedules can be delayed; this is eventual synchronization.
One concurrency group serializes runs. Each run fetches current GitHub refs,
then pushes that snapshot atomically and checks exact destination ref SHA
equality. New source changes during a run are picked up by a later run.

## Credential and cutover

Create repository Actions secret `GITLAB_TOKEN` using a valid GitLab token
with `write_repository` access and sufficient project role to update the
destination. The local environment variable alone is not available to hosted
Actions. The token is passed through a temporary credential helper, never
committed or embedded in URLs. Rotate the secret before token expiry or when
revoked. GitLab API work during cutover additionally requires the appropriate
API scope; the recurring Git push itself does not require API scope.

Before the first replacement, the supervisor must:

1. Save an independent backup of the existing GitLab repository and its
   advertised refs, outside the destination repository, and verify it is readable.
2. Disable the legacy `babar-raza/repository-presenter` workflow
   `.github/workflows/mirror-gitlab.yml`, which targets this same GitLab project.
   Keep a record of its former state for rollback. Only one source should write
   the destination.
3. Inspect GitLab default-branch and branch/tag protection settings. Permit the
   mirror identity's required force updates/deletions during replacement and
   normal reconciliation, preserving equivalent protection against other writers.
   Record any temporary protection changes and restore them as appropriate.
4. Install the secret, enable this workflow on GitHub's default branch, and
   dispatch it. Confirm the hosted job succeeds and its destination SHA check
   passes. Exercise creation and deletion of a disposable source branch.

The push requires server support for atomic pushes. It deliberately fails as a
whole if any managed ref is protected or rejected. Do not rerun indefinitely
against an expired token or protection error: correct the credential or ref
permission, then dispatch again. Rollback uses the saved backup, after disabling
this workflow so scheduled reconciliation cannot overwrite the restoration.

## Scope

This is Git repository replacement and ongoing replication. It does not copy
issues, merge requests, project settings, CI variables, runner configuration,
GitHub artifacts or secrets. GitHub Actions continue running on GitHub; the
GitLab copy receives their Git outputs. It does not install a separate GitLab
test pipeline. Git LFS objects, if introduced later, need an additional explicit
transfer; ordinary Git refs alone do not replicate their external storage.

Only content committed and pushed to GitHub is mirrored. Local worktree branches,
ignored files and untracked candidate bundles are excluded. In particular, the
untracked Cells Go and PDF Java candidate directories observed during setup
remain local until deliberately committed and pushed. Local checkout HEAD can
lag GitHub main; the workflow always fetches GitHub rather than treating the
supervisor's checkout as the live source.
