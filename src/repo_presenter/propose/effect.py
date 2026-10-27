"""The gated README-proposal PR effect (G6-W02) - and, in this project's current environment,
never armed.

This is the write half `docs/EXECUTION_STATE_MACHINE.md` G6 Work item 1 names: `propose.yml` as a
separately authorized write-capable workflow, distinct from `present.yml`/`monitor.yml`'s read-only
scope. Building the mechanism is in scope here; firing it live against a real product repository is
not - `AGENTS.md` is explicit: "Do not perform a target write unless the current execution gate and
exact authorization permit it", and `docs/STATE_MACHINE.md` section 12.1 requires the *first* live
exercise against a real external target to be owner-selected, never agent-selected. This module is
built and tested against injected fakes only - never fired live by its work items.

Every gate below runs, in this order, before the first write, and each refusal is a typed
`core/authorization/refusals.py::Refusal` with no write call made:

1. `WritePermit` - a required argument, only obtainable from `core/registry/write_gate.py`'s
   `require_write_permitted`: the registry entry is listed, active and `full`. A `dry_run` entry can
   never reach this function.
2. `write_authorized(environment)` - the owner-controlled kill switch
   `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`. Never inferred from a credential.
3. `review` (required, `readme/review/independent_reviewer.py::ReviewVerdict`) - the independent
   reviewer's veto (mission section 11: "independent non-authoring criticism that can veto, with
   no quiet demotion"). A verdict other than `"ACCEPT"`, or one no model reviewed
   (`ReviewVerdict.model_reviewed`), refuses with `Refusal.REVIEW_REJECTED`
   before any token or network call; there is no override parameter, because a veto that can be
   bypassed by the caller is not a veto.
3b. The reviewer's calibration status (`readme/review/calibration_status.py`): the verdict must have
   been made while the committed status was PASSED or PASSED_WITH_DECLARED_LIMITS, and the committed
   status must permit it now; otherwise `Refusal.REVIEW_UNCALIBRATED`. No parameter overrides it.
4. A write-scoped token is supplied (`GH_PROPOSAL_WRITE_TOKEN` - never `GH_TOKEN`).
5. The authorization record (`core/authorization/proposal.py`): a persisted, reviewed file committed
   to the control repository before this run was triggered, which `load_authorization` loads and
   checks for provenance. Every bound field - repository, candidate hash, source revision, base
   branch, presenter branch, window - is then checked against the candidate and live target this
   call holds. The record is independent of the proposal: it is not computed from it.
6. Token provenance (`core/github/token_provenance.py`): an installation token whose reach is
   exactly the target repository.
7. Source freshness: `recheck_source` (required) must equal the authorized source revision - the
   `AGENTS.md` "Recheck upstream revision immediately before an effect" rule.
8. Pull-request history: every state is read before anything is written. A merged or closed
   pull request for the same candidate is never recreated unless the record names it in
   `supersedes_prs`.

The effect itself is idempotent by construction: it reads the presenter branch's current README
content and the presenter pull request before writing, and only writes what has actually changed.
A lost response from the one write call that can go missing in flight (`put_contents`) is never
retried blindly: `reconcile_write` re-observes the branch, and the write is re-attempted only when
that observation confirms the prior attempt did not land - `AGENTS.md` "reconcile uncertain remote
effects before retrying". The pull request the effect creates or updates is attributed to the
expected GitHub App (`verify_pull_request_app`) - the one thing a bare installation token cannot
prove about itself ahead of time.

Ported (ADAPT) from the old repository-presenter project's
``components/propose/effect.py``, 2026-10-23, as the write half of mission P3's "submit one
authorized PR" blocker -- a research fork confirmed it is a bounded port once
``authorization/proposal.py``+``record_provenance.py``, ``propose/pull_request.py``'s
composition half, and the ~9 github/client.py REST primitives it uses are each pulled (all done
the same day). Still never armed here either: ``REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED``
has no production wiring, token_provenance.py's ``EXPECTED_APP_ID``/``EXPECTED_APP_SLUG`` are
inherited placeholders pending confirmation of this repository's own App identity, and nothing
calls ``propose_candidate`` from any live Lane R/L path yet. The one change beyond import
paths: a required ``review`` argument whose non-ACCEPT verdict refuses with ``REVIEW_REJECTED``
(mission section 7, step 7: a reviewer REJECT is blocking); the old module had no reviewer gate.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from repo_presenter.authorization.proposal import (
    ProposalAuthorization,
    validate_authorization,
)
from repo_presenter.authorization.refusals import Refusal, WriteRefusedError
from repo_presenter.core.hashing import sha256_text
from repo_presenter.core.registry.write_gate import WritePermit
from repo_presenter.github.client import (
    FileContents,
    PullRequestRef,
)
from repo_presenter.github.client import (
    create_pull_request as default_create_pull_request,
)
from repo_presenter.github.client import (
    create_ref as default_create_ref,
)
from repo_presenter.github.client import (
    find_pull_requests as default_find_pull_requests,
)
from repo_presenter.github.client import (
    get_contents as default_get_contents,
)
from repo_presenter.github.client import (
    get_ref as default_get_ref,
)
from repo_presenter.github.client import (
    put_contents as default_put_contents,
)
from repo_presenter.github.client import (
    update_pull_request as default_update_pull_request,
)
from repo_presenter.github.errors import RepositoryMetadataError
from repo_presenter.github.token_provenance import (
    TokenDecision,
)
from repo_presenter.github.token_provenance import (
    verify_installation_token as default_verify_installation_token,
)
from repo_presenter.github.token_provenance import (
    verify_pull_request_app as default_verify_pull_request_app,
)
from repo_presenter.propose.pull_request import PullRequestContent
from repo_presenter.readme.review.calibration_status import load_calibration
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

#: The one stable presenter branch this project proposes README updates from, on every target
#: (`docs/STATE_MACHINE.md` section 11.1: "One stable presenter branch and one open PR exist per
#: target repository."). Deliberately a single constant, not derived per-repository - each target
#: repository already has its own separate git namespace, so one fixed name here is already "one
#: stable branch per target", and a fixed name is what lets every invocation find the same branch
#: rather than inventing a new one on each run.
PRESENTER_BRANCH = "repository-presenter/readme-update"


def presenter_branch_name() -> str:
    """The canonical presenter branch name, independent of whatever branch a given authorization
    *claims* - `propose_candidate` validates every authorization's own `branch` field against this
    before trusting it for anything, so an authorization minted for the wrong branch is refused
    rather than silently followed."""
    return PRESENTER_BRANCH


_NOT_AUTHORIZED_REASON = (
    f"not authorized: set {AUTHORIZATION_VARIABLE}=1 (owner-controlled) - a token's presence or "
    "scope is never by itself sufficient"
)
_NO_TOKEN_REASON = (
    "no write-scoped token available (GH_PROPOSAL_WRITE_TOKEN, never GH_TOKEN)"
)
README_PATH = "README.md"

GetRefFn = Callable[..., "str | None"]
CreateRefFn = Callable[..., None]
GetContentsFn = Callable[..., "FileContents | None"]
PutContentsFn = Callable[..., object]
FindPullRequestsFn = Callable[..., "tuple[PullRequestRef, ...]"]
CreatePullRequestFn = Callable[..., PullRequestRef]
UpdatePullRequestFn = Callable[..., PullRequestRef]
RecheckSourceFn = Callable[[], str]
ReconcileWriteFn = Callable[[], "FileContents | None"]
LoadAuthorizationFn = Callable[[], ProposalAuthorization]
VerifyTokenFn = Callable[..., TokenDecision]
VerifyPullRequestAppFn = Callable[..., TokenDecision]
ClockFn = Callable[[], str]
#: ``(the README the base branch has now, or None if it has none) -> (title, body)``; called only
#: past every gate, so composing it (which needs a read of the target) never precedes the token.
ComposePullRequestFn = Callable[["str | None"], "PullRequestContent"]

_CANDIDATE_HASH_LINE = re.compile(r"candidate_hash:\s*([0-9a-f]{64})")


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_authorized(environment: Mapping[str, str]) -> bool:
    """`True` only when the owner has explicitly set `AUTHORIZATION_VARIABLE` to a truthy value.
    Absence, an empty string, or any other value is unauthorized - fail closed."""
    return (
        environment.get(AUTHORIZATION_VARIABLE, "").strip().lower()
        in _AUTHORIZED_VALUES
    )


@dataclass(frozen=True)
class ProposalEffectResult:
    """The outcome of one `propose_candidate` call. `effected` is `True` only when every gate
    passed and the branch/PR state was confirmed to match the candidate by the end of the call -
    whether or not that needed a new commit or PR edit; every refusal leaves `effected` `False`
    with a typed `reason_code` and no network call beyond whatever read was needed to decide it."""

    repository: str
    authorized: bool
    effected: bool
    branch: str
    pr_number: int | None
    pr_url: str | None
    commit_written: bool
    pr_created: bool
    pr_updated: bool
    reason: str
    reason_code: Refusal | None = None


def _commit_message(authorization: ProposalAuthorization) -> str:
    return (
        "Update README via repository-presenter\n\n"
        f"candidate_hash: {authorization.candidate_hash}\n"
        f"source_revision: {authorization.source_revision}\n"
        f"approver: {authorization.approver}\n"
    )


def _is_same_candidate(pr: PullRequestRef, candidate_hash: str) -> bool:
    """A pull request body that does not carry a candidate hash is treated as the same candidate:
    unknown is never "new"."""
    found = _CANDIDATE_HASH_LINE.search(pr.body)
    return found is None or found.group(1) == candidate_hash


def _settled_pull_request_refusal(
    prs: tuple[PullRequestRef, ...], authorization: ProposalAuthorization
) -> tuple[Refusal, str] | None:
    """The refusal for creating a new pull request while a merged or closed one already exists for
    the same candidate (`docs/STATE_MACHINE.md` section 11.1: a settled proposal is not recreated
    until new drift - a different candidate - or explicit policy permits another)."""
    blocking = [
        pr
        for pr in prs
        if pr.state != "open"
        and pr.number not in authorization.supersedes_prs
        and _is_same_candidate(pr, authorization.candidate_hash)
    ]
    if not blocking:
        return None
    merged = [pr for pr in blocking if pr.state == "merged"]
    pr = (merged or blocking)[0]
    code = Refusal.PR_ALREADY_MERGED if merged else Refusal.PR_ALREADY_CLOSED
    return code, (
        f"pull request #{pr.number} ({pr.url}) for this candidate was already {pr.state}; it is "
        "not recreated unless the authorization record names it in supersedes_prs"
    )


def propose_candidate(
    *,
    repository: str,
    readme_text: str,
    source_revision: str,
    base_branch: str,
    token: str | None,
    environment: Mapping[str, str],
    review: ReviewVerdict,
    permit: WritePermit,
    load_authorization: LoadAuthorizationFn,
    recheck_source: RecheckSourceFn,
    branch: str | None = None,
    clock: ClockFn = _utc_now,
    verify_token: VerifyTokenFn = default_verify_installation_token,
    verify_pull_request_app: VerifyPullRequestAppFn = default_verify_pull_request_app,
    get_ref: GetRefFn = default_get_ref,
    create_ref: CreateRefFn = default_create_ref,
    get_contents: GetContentsFn = default_get_contents,
    put_contents: PutContentsFn = default_put_contents,
    find_pull_requests: FindPullRequestsFn = default_find_pull_requests,
    create_pull_request: CreatePullRequestFn = default_create_pull_request,
    update_pull_request: UpdatePullRequestFn = default_update_pull_request,
    reconcile_write: ReconcileWriteFn | None = None,
    pr_title: str | None = None,
    pr_body: str | None = None,
    compose_pull_request: ComposePullRequestFn | None = None,
) -> ProposalEffectResult:
    """Create or update the one stable presenter branch and PR on `repository` - but only past
    every gate in this module's own docstring. Every early return before the first write makes no
    write call, and the gates before the token check make no network call at all.

    The pull request's text is either given (``pr_title`` and ``pr_body``) or composed after the
    gates from the README the base branch has now (``compose_pull_request``, see
    ``components/propose/pull_request.py``); exactly one of the two.
    """
    if compose_pull_request is None and (pr_title is None or pr_body is None):
        raise ValueError("give pr_title and pr_body, or compose_pull_request")
    if compose_pull_request is not None and (
        pr_title is not None or pr_body is not None
    ):
        raise ValueError(
            "give either pr_title and pr_body, or compose_pull_request - not both"
        )
    if permit.effect != "readme_proposal" or permit.entry.repository != repository:
        raise ValueError(
            "the write permit does not clear this effect for this repository"
        )
    owner, name = repository.split("/", 1)
    branch = branch if branch is not None else presenter_branch_name()

    def _refuse(authorized: bool, code: Refusal, reason: str) -> ProposalEffectResult:
        return ProposalEffectResult(
            repository=repository,
            authorized=authorized,
            effected=False,
            branch=branch,
            pr_number=None,
            pr_url=None,
            commit_written=False,
            pr_created=False,
            pr_updated=False,
            reason=reason,
            reason_code=code,
        )

    def _github_error(reason: str) -> ProposalEffectResult:
        return _refuse(True, Refusal.GITHUB_ERROR, reason)

    if not write_authorized(environment):
        return _refuse(False, Refusal.WRITE_NOT_ENABLED, _NOT_AUTHORIZED_REASON)

    if review.verdict != "ACCEPT":
        blocking = review.blocking_findings
        rules = ", ".join(sorted({finding.rule for finding in blocking})) or review.fold.reason
        return _refuse(
            True,
            Refusal.REVIEW_REJECTED,
            "the independent reviewer rejected this candidate "
            f"({len(blocking)} blocking finding(s), {review.deterministic_reject_count} of them "
            f"deterministic: {rules}); it is never proposed while a REJECT stands, and no caller "
            "can override this verdict",
        )
    if not review.model_reviewed:
        return _refuse(
            True,
            Refusal.REVIEW_REJECTED,
            "no LLM review of this candidate was made: a deterministic-only verdict is not "
            "the independent review the mission requires, so it is never proposed",
        )

    current = load_calibration()
    if not review.pr_eligible or not current.permits:
        return _refuse(
            True,
            Refusal.REVIEW_UNCALIBRATED,
            "the independent reviewer has not passed its calibration gate, so no candidate is "
            f"eligible for a pull request (committed status {current.status}"
            f"{': ' + current.problem if current.problem else ''}; this verdict was made under "
            f"{review.calibration_status or 'no recorded status'}); PASSED, or "
            "PASSED_WITH_DECLARED_LIMITS with an owner acceptance in data/reviewer_calibration.json, "
            "is required and no caller can override it",
        )

    if not token:
        return _refuse(True, Refusal.NO_WRITE_TOKEN, _NO_TOKEN_REASON)

    try:
        authorization = load_authorization()
    except WriteRefusedError as exc:
        return _refuse(True, exc.code, exc.message)
    decision = validate_authorization(
        authorization,
        now=clock(),
        expected_repository=repository,
        expected_candidate_hash=sha256_text(readme_text),
        expected_source_revision=source_revision,
        expected_base_branch=base_branch,
        expected_branch=branch,
    )
    if not decision.granted:
        return _refuse(
            True, decision.code or Refusal.AUTHORIZATION_MISMATCH, decision.reason
        )

    token_decision = verify_token(repository, token)
    if not token_decision.ok:
        return _refuse(
            True,
            token_decision.code or Refusal.TOKEN_UNVERIFIABLE,
            token_decision.reason,
        )

    # past every gate that needs nothing of the target but the token itself ------------------

    live_revision = recheck_source()
    if live_revision != authorization.source_revision:
        return _refuse(
            True,
            Refusal.SOURCE_MOVED,
            "stale source: the target's live current revision "
            f"({live_revision}) no longer matches the authorized source revision "
            f"({authorization.source_revision}) - refusing to propose against a moved "
            "target; recapture and reauthorize",
        )

    try:
        prs = find_pull_requests(owner, name, head_branch=branch, token=token)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not list pull requests for {branch!r}: {exc}")
    existing_pr = next((pr for pr in prs if pr.state == "open"), None)
    if existing_pr is None:
        settled = _settled_pull_request_refusal(prs, authorization)
        if settled is not None:
            return _refuse(True, settled[0], settled[1])
    else:
        attribution = verify_pull_request_app(
            owner, name, existing_pr.number, token=token
        )
        if not attribution.ok:
            return _refuse(
                True, attribution.code or Refusal.TOKEN_UNVERIFIABLE, attribution.reason
            )

    # past every gate: the first remote write is below ----------------------------------------

    try:
        base_sha = get_ref(owner, name, base_branch, token=token)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not read base branch {base_branch!r}: {exc}")
    if base_sha is None:
        return _github_error(f"base branch {base_branch!r} does not exist")

    if compose_pull_request is not None:
        try:
            live_readme = get_contents(
                owner, name, README_PATH, ref=base_branch, token=token
            )
        except RepositoryMetadataError as exc:
            return _github_error(
                f"could not read {README_PATH} on {base_branch!r}: {exc}"
            )
        content = compose_pull_request(
            None if live_readme is None else live_readme.text
        )
        pr_title, pr_body = content.title, content.body
    assert pr_title is not None and pr_body is not None

    try:
        branch_sha = get_ref(owner, name, branch, token=token)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not read presenter branch {branch!r}: {exc}")
    if branch_sha is None:
        try:
            create_ref(owner, name, branch, base_sha, token=token)
        except RepositoryMetadataError as exc:
            return _github_error(f"could not create presenter branch {branch!r}: {exc}")

    try:
        existing_file = get_contents(owner, name, README_PATH, ref=branch, token=token)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not read {README_PATH} on {branch!r}: {exc}")

    commit_written = False
    if existing_file is None or existing_file.text != readme_text:
        file_sha = existing_file.sha if existing_file is not None else None
        try:
            put_contents(
                owner,
                name,
                README_PATH,
                branch=branch,
                message=_commit_message(authorization),
                text=readme_text,
                sha=file_sha,
                token=token,
            )
            commit_written = True
        except RepositoryMetadataError as exc:
            if "unreachable" not in str(exc) or reconcile_write is None:
                return _github_error(
                    f"could not write {README_PATH} on {branch!r}: {exc}"
                )
            # Lost-response reconciliation (AGENTS.md "reconcile uncertain remote effects before
            # retrying"): re-observe the branch's real current content before ever retrying.
            reconciled = reconcile_write()
            if reconciled is not None and reconciled.text == readme_text:
                commit_written = True  # the write landed; only the response was lost
            else:
                try:
                    put_contents(
                        owner,
                        name,
                        README_PATH,
                        branch=branch,
                        message=_commit_message(authorization),
                        text=readme_text,
                        sha=reconciled.sha if reconciled is not None else None,
                        token=token,
                    )
                    commit_written = True
                except RepositoryMetadataError as retry_exc:
                    return _github_error(
                        f"write to {README_PATH} on {branch!r} failed after reconciliation: "
                        f"{retry_exc}"
                    )

    pr_created = False
    pr_updated = False
    if existing_pr is None:
        try:
            pr_ref = create_pull_request(
                owner,
                name,
                title=pr_title,
                body=pr_body,
                head=branch,
                base=base_branch,
                token=token,
            )
        except RepositoryMetadataError as exc:
            return _github_error(f"could not open the presenter pull request: {exc}")
        pr_created = True
        attribution = verify_pull_request_app(owner, name, pr_ref.number, token=token)
        if not attribution.ok:
            return ProposalEffectResult(
                repository=repository,
                authorized=True,
                effected=False,
                branch=branch,
                pr_number=pr_ref.number,
                pr_url=pr_ref.url,
                commit_written=commit_written,
                pr_created=True,
                pr_updated=False,
                reason=f"{attribution.reason} - review and close {pr_ref.url} if it is not ours",
                reason_code=attribution.code or Refusal.TOKEN_UNVERIFIABLE,
            )
    else:
        pr_ref = existing_pr
        if existing_pr.title != pr_title or existing_pr.body != pr_body:
            try:
                pr_ref = update_pull_request(
                    owner,
                    name,
                    existing_pr.number,
                    title=pr_title,
                    body=pr_body,
                    token=token,
                )
                pr_updated = True
            except RepositoryMetadataError as exc:
                return _github_error(
                    f"could not update the presenter pull request: {exc}"
                )

    return ProposalEffectResult(
        repository=repository,
        authorized=True,
        effected=True,
        branch=branch,
        pr_number=pr_ref.number,
        pr_url=pr_ref.url,
        commit_written=commit_written,
        pr_created=pr_created,
        pr_updated=pr_updated,
        reason="proposed"
        if (commit_written or pr_created or pr_updated)
        else "no change needed",
    )
