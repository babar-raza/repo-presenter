"""The hosted driver of the README-proposal effect (R50, WP-1): ``python -m repo_presenter.propose.run``.

``propose_candidate`` (``propose/effect.py``) had no caller. This module is the caller the old
project's ``repository-presenter propose`` command was, rebuilt on this repository's pieces:
the sealed candidate comes from its bundle ref on the state remote, the pull request text from
``propose/pull_request.py``, the gates from the registry, the upstream allowlist and the R15
portfolio predicate. It has three subcommands, and only the last can write anything:

``gates``    evaluate the five write gates for a target and print/record them. Read-only.
``payload``  the DRY RUN: build the exact branch/pull-request payload (title, body, files, draft flag,
             candidate hash, source revision) and report every gate and every refusal. It never
             calls a function that writes: the write seams are not even bound on this path
             (``tests/propose/test_run.py`` proves it with seams that raise).
``write``    the gated write. Refuses, before any GitHub call, unless every gate holds; then calls
             ``propose_candidate`` with the one repository-scoped App installation token in
             ``GH_PROPOSAL_WRITE_TOKEN`` (never ``GH_TOKEN``). The pull request is always a draft
             (the allowlist's ``first_pr_as_draft`` and the transport guard in ``github/client.py``).

The five write gates (every one must hold, none can be bypassed by a caller):

1. ``allowlist``      the target is on ``data/upstream_write_allowlist.json`` for ``pull_request``
                      with ``first_pr_as_draft`` true (R3/R22).
2. ``registry_full``  ``data/registry.json`` lists it, active, ``mode: full`` (the write permit).
3. ``kill_switch``    the owner variable ``REPO_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`` is truthy.
4. ``portfolio_r15``  every active repository has a terminal outcome in both lanes
                      (``propose/portfolio_gate.py``; owner ruling R15: nothing upstream before that).
                      NOT required when the target is exactly the sandbox repository the variable below
                      names (R17, owner decision 2026-11-22; never for ``*``); required, fail closed, for
                      every other target.
5. ``sandbox_target`` the owner variable ``REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY`` names exactly
                      this target. Unset or empty fails closed. The owner lifts the restriction only
                      by setting that variable to ``*`` (every allowlisted repository then passes
                      this gate, the other four unchanged).

``--sandbox`` (all three subcommands) is the R17 path: the candidate of ``--repository`` is written to the
sandbox repository the variable names (``propose/sandbox.py``: throwaway branch, ``sandbox/<owner>__<repo>/
README.md``, DRAFT pull request, duplicates refused), never to its own repository; gate 1 is then the
``data/sandbox_write_target.json`` entry and gate 2 only needs the candidate registered and active.

Exit codes: 0 ok, 2 usage or an unreadable/absent candidate, 3 refused by a gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from repo_presenter.acceptance.record import PUBLISHABLE_STATES, classify
from repo_presenter.authorization.proposal import (
    CURRENT_POLICY_VERSION,
    ProposalAuthorization,
    load_authorization_file,
    record_filename,
    validate_authorization,
)
from repo_presenter.authorization.record_provenance import verify_record_provenance
from repo_presenter.authorization.refusals import WriteRefusedError
from repo_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    LANE_L,
    LANE_R,
    lane_directory,
    verify_bundle,
)
from repo_presenter.core.hashing import sha256_text
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry.write_gate import require_write_permitted
from repo_presenter.github import client as github_client
from repo_presenter.github.read_client import fetch_default_branch_sha
from repo_presenter.propose.acceptance_evidence import (
    AttestedAcceptance,
    bytes_sha256,
    evaluate_acceptance,
    read_acceptance_evidence,
)
from repo_presenter.propose.effect import (
    AUTHORIZATION_VARIABLE,
    README_PATH,
    presenter_branch_name,
    propose_candidate,
    write_authorized,
)
from repo_presenter.propose.pull_request import (
    PullRequestContent,
    compose_pull_request,
    load_correction_residuals,
    load_pull_request_evidence,
)
from repo_presenter.readme.review.verdict_io import (
    ReviewVerdictError,
    load_review_verdict,
)
from repo_presenter.sandbox_scope import (
    SANDBOX_LIFTED,
    SANDBOX_VARIABLE,
    SandboxConfigError,
    load_sandbox_entry,
    names_sandbox,
    sandbox_repository,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY = REPO_ROOT / "data" / "registry.json"
# SANDBOX_VARIABLE (the repository variable that names the one repository the write job may touch, gate 5) and
# SANDBOX_LIFTED (the owner's lift of that restriction: every allowlisted repository passes gate 5; it is NEVER an
# R15 exemption) live in ``repo_presenter.sandbox_scope``, the one reader of the variable.
#: The write token's one variable name (never ``GH_TOKEN``, which the analysis jobs use read-only).
WRITE_TOKEN_VARIABLE = "GH_PROPOSAL_WRITE_TOKEN"
STATE_TOKEN_VARIABLE = "REPOSITORY_PRESENTER_STATE_TOKEN"

EXIT_OK, EXIT_USAGE, EXIT_REFUSED = 0, 2, 3
GATE_NAMES = ("allowlist", "registry_full", "kill_switch", "portfolio_r15", "sandbox_target")


@dataclass(frozen=True)
class Gate:
    name: str
    ok: bool
    detail: str


def _short(text: object, limit: int = 600) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def gate_allowlist(repository: str, path: Path | None = None) -> Gate:
    try:
        entries = github_client._load_upstream_allowlist(path or github_client.UPSTREAM_WRITE_ALLOWLIST)
    except github_client.UpstreamWriteForbiddenError as exc:
        return Gate("allowlist", False, _short(exc))
    entry = entries.get(repository.lower())
    if entry is None:
        return Gate("allowlist", False, f"{repository} is not on data/upstream_write_allowlist.json")
    if "pull_request" not in entry.effects:
        return Gate("allowlist", False, f"{repository} is allowlisted for {sorted(entry.effects)}, not pull_request")
    if not entry.first_pr_as_draft:
        return Gate("allowlist", False, f"{repository} is not allowlisted for draft pull requests only")
    return Gate("allowlist", True, f"{repository} is allowlisted for draft pull requests")


def gate_registry(repository: str, registry_path: Path = REGISTRY) -> Gate:
    try:
        require_write_permitted(load_registry(registry_path), repository, "readme_proposal")
    except WriteRefusedError as exc:
        return Gate("registry_full", False, _short(exc.message))
    except Exception as exc:  # noqa: BLE001 -- an unreadable registry is a closed gate
        return Gate("registry_full", False, f"registry unreadable ({type(exc).__name__}: {_short(exc, 200)})")
    return Gate("registry_full", True, f"{repository} is registry mode full and active")


def gate_kill_switch(environment: Mapping[str, str]) -> Gate:
    if write_authorized(environment):
        return Gate("kill_switch", True, f"{AUTHORIZATION_VARIABLE} is set")
    return Gate("kill_switch", False, f"{AUTHORIZATION_VARIABLE} is not set to a truthy value (owner-controlled)")


def gate_portfolio(
    readiness: Callable[[], Any] | None = None,
    *,
    target: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> Gate:
    """Gate 4, the R15 portfolio predicate. Owner decision 2026-11-22 (R17: sandbox first): it is NOT required
    when ``target`` is exactly the sandbox repository the variable names (``sandbox_scope.names_sandbox``: never
    the wildcard, never an unset variable). For every other target it is required and fails closed."""
    if target is not None and environment is not None and names_sandbox(target, environment):
        return Gate(
            "portfolio_r15",
            True,
            f"{target} is the R17 sandbox named by {SANDBOX_VARIABLE}: the R15 portfolio predicate is not required "
            "for the sandbox (it stays required for every other target)",
        )
    try:
        if readiness is None:
            from repo_presenter.propose.portfolio_gate import (
                portfolio_readiness as readiness,
            )
        result = readiness()
        ready, reason = result.ready is True, result.reason()
    except Exception as exc:  # noqa: BLE001 -- fail closed: an unreadable predicate is not ready
        ready, reason = False, f"portfolio readiness unreadable ({type(exc).__name__}: {exc})"
    return Gate("portfolio_r15", ready, _short(reason))


def gate_sandbox(repository: str, environment: Mapping[str, str]) -> Gate:
    value = environment.get(SANDBOX_VARIABLE, "").strip()
    if not value:
        return Gate("sandbox_target", False, f"{SANDBOX_VARIABLE} is not set: no target is cleared")
    if value == SANDBOX_LIFTED:
        return Gate("sandbox_target", True, f"{SANDBOX_VARIABLE} is {SANDBOX_LIFTED!r}: the owner lifted the sandbox restriction")
    if value.lower() == repository.lower():
        return Gate("sandbox_target", True, f"{repository} is the sandbox target")
    return Gate("sandbox_target", False, f"{repository} is not the sandbox target {value!r}")


def evaluate_gates(
    repository: str,
    environment: Mapping[str, str],
    *,
    allowlist_path: Path | None = None,
    registry_path: Path = REGISTRY,
    readiness: Callable[[], Any] | None = None,
) -> list[Gate]:
    """All five gates, always all of them (a report shows every blocker, not only the first)."""
    return [
        gate_allowlist(repository, allowlist_path),
        gate_registry(repository, registry_path),
        gate_kill_switch(environment),
        gate_portfolio(readiness, target=repository, environment=environment),
        gate_sandbox(repository, environment),
    ]


def gate_sandbox_allowlist(environment: Mapping[str, str], path: Path | None = None) -> Gate:
    """Gate 1 in sandbox mode: the ``sandbox`` entry of ``data/sandbox_write_target.json``, honoured only when
    the variable names it exactly (never ``*``). The R22 allowlist is not consulted and not widened."""
    chosen = sandbox_repository(environment, *((path,) if path else ()))
    if chosen is None:
        return Gate("allowlist", False, f"no sandbox is selected: {SANDBOX_VARIABLE} must name the sandbox exactly (never '*')")
    try:
        entry = load_sandbox_entry(*((path,) if path else ()))
    except SandboxConfigError as exc:
        return Gate("allowlist", False, _short(exc))
    if "pull_request" not in entry.effects or not entry.first_pr_as_draft:
        return Gate("allowlist", False, "the sandbox entry does not grant draft pull requests")
    return Gate("allowlist", True, f"{chosen} is the owner's R17 sandbox (data/sandbox_write_target.json): draft pull requests only")


def gate_registry_listed(repository: str, registry_path: Path = REGISTRY) -> Gate:
    """Gate 2 in sandbox mode: the CANDIDATE's repository is registered and active. Its mode need not be
    ``full``: nothing is written to it, the write target is the sandbox."""
    try:
        entry = next((e for e in load_registry(registry_path).entries if e.repository.lower() == repository.lower()), None)
    except Exception as exc:  # noqa: BLE001
        return Gate("registry_full", False, f"registry unreadable ({type(exc).__name__}: {_short(exc, 200)})")
    if entry is None or not entry.active:
        return Gate("registry_full", False, f"{repository} is not an active registry repository")
    return Gate("registry_full", True, f"{repository} is registered and active (sandbox mode: its mode {entry.mode!r} is not a write permit here)")


def evaluate_sandbox_gates(
    candidate_repository: str,
    environment: Mapping[str, str],
    *,
    sandbox_path: Path | None = None,
    registry_path: Path = REGISTRY,
    readiness: Callable[[], Any] | None = None,
) -> list[Gate]:
    """The five gates for a SANDBOX write of ``candidate_repository``'s README, same names and order. The write
    target is the sandbox repository the variable names (none selected: every target-bound gate fails closed and
    R15 is evaluated for real)."""
    target = sandbox_repository(environment, *((sandbox_path,) if sandbox_path else ()))
    return [
        gate_sandbox_allowlist(environment, sandbox_path),
        gate_registry_listed(candidate_repository, registry_path),
        gate_kill_switch(environment),
        gate_portfolio(readiness, target=target, environment=environment),
        Gate("sandbox_target", True, f"{target} is the sandbox target") if target else Gate(
            "sandbox_target", False, f"{SANDBOX_VARIABLE} does not name the sandbox: no target is cleared (the wildcard never selects it)"
        ),
    ]


def write_eligible(gates: Sequence[Gate]) -> bool:
    return [g.name for g in gates] == list(GATE_NAMES) and all(g.ok for g in gates)


# --- the candidate ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    repository: str
    lane: str
    revision: str
    readme_text: str
    bundle: Path
    manifest_state: str
    #: SHA-256 of the sealed README's own bytes (what an attested record's ``candidate_sha256`` binds to).
    readme_sha256: str = ""

    @property
    def candidate_hash(self) -> str:
        return sha256_text(self.readme_text)

    @property
    def bytes_sha256(self) -> str:
        return self.readme_sha256 or bytes_sha256(self.readme_text)


def bytes_sha256_of(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


class CandidateError(Exception):
    """The sealed candidate cannot be loaded; nothing is proposed."""


def load_candidate(repository: str, lane: str, root: Path) -> Candidate:
    """The latest sealed bundle of ``repository`` in ``lane`` under ``root/candidates/<slug>``,
    verified. Never a bundle that fails its own manifest."""
    slug_dir = root / CANDIDATES_DIRNAME / repository.replace("/", "__")
    lane_root = lane_directory(slug_dir, lane)
    pointer = lane_root / CURRENT_FILENAME
    if not pointer.is_file():
        raise CandidateError(f"{repository} lane {lane}: no sealed candidate ({CURRENT_FILENAME} missing)")
    revision = pointer.read_text(encoding="utf-8").strip()
    bundle = lane_root / revision
    try:
        manifest = verify_bundle(bundle, lane)
    except Exception as exc:
        raise CandidateError(f"{repository} lane {lane}: the sealed bundle does not verify: {exc}") from exc
    if manifest is None or not (bundle / BUNDLE_MANIFEST_NAME).is_file():
        raise CandidateError(f"{repository} lane {lane}: no verifiable bundle at {revision}")
    readme = bundle / README_PATH
    if not readme.is_file():
        raise CandidateError(f"{repository} lane {lane}: the bundle has no {README_PATH}")
    return Candidate(
        repository=repository,
        lane=lane,
        revision=revision,
        readme_text=readme.read_text(encoding="utf-8"),
        bundle=bundle,
        manifest_state=str(manifest.get("state")),
        readme_sha256=bytes_sha256_of(readme.read_bytes()),
    )


def export_candidate(repository: str, lane: str, scratch: Path, *, remote: str, token: str | None) -> Candidate:
    """Materialize the lane's stored bundle from its state ref (read-only) and load it."""
    from repo_presenter.core.errors import PresenterError
    from repo_presenter.core.state.bundle_store import export_bundle

    try:
        export_bundle(repository, lane, scratch / CANDIDATES_DIRNAME, remote=remote, token=token)
    except (PresenterError, OSError) as exc:
        raise CandidateError(f"{repository} lane {lane}: no stored bundle could be exported: {exc}") from exc
    return load_candidate(repository, lane, scratch)


def compose(candidate: Candidate, live_readme: str | None) -> PullRequestContent:
    """The pull request title and body for ``candidate`` against the README the target has now."""
    residuals = load_correction_residuals(candidate.bundle) if candidate.lane == LANE_L else ()
    return compose_pull_request(
        candidate_readme=candidate.readme_text,
        live_readme=live_readme,
        repository=candidate.repository,
        evidence=load_pull_request_evidence(candidate.bundle),
        candidate_hash=candidate.candidate_hash,
        source_revision=candidate.revision,
        policy_version=CURRENT_POLICY_VERSION,
        residuals=residuals,
    )


def authorization_loader(
    record_path: Path, *, control_root: Path, trigger_sha: str
) -> Callable[[], ProposalAuthorization]:
    """The committed authorization record, accepted only with merge-before-run provenance."""

    def load() -> ProposalAuthorization:
        authorization = load_authorization_file(record_path)
        provenance = verify_record_provenance(record_path, control_root=control_root, trigger_sha=trigger_sha)
        print(
            f"propose: authorization record {record_path.name} approved by {authorization.approver}; "
            f"commit {provenance.commit[:12]} by {provenance.author} at {provenance.committed_at}"
        )
        return authorization

    return load


def record_path_for(candidate: Candidate, root: Path) -> Path:
    from repo_presenter.authorization.proposal import AUTHORIZATION_DIRNAME

    return root / AUTHORIZATION_DIRNAME / record_filename(candidate.repository, candidate.candidate_hash)


# --- the dry run -----------------------------------------------------------------------------------


def build_payload(
    candidate: Candidate,
    gates: Sequence[Gate],
    *,
    read_token: str | None,
    root: Path = REPO_ROOT,
    trigger_sha: str = "",
    get_contents: Callable[..., Any] = github_client.get_contents,
    fetch_head: Callable[..., Any] = fetch_default_branch_sha,
    verify_token: Callable[..., Any] | None = None,
    now: Callable[[], str] | None = None,
    acceptance_records: Sequence[AttestedAcceptance] = (),
) -> dict[str, Any]:
    """Everything the write job would send, plus every refusal, with NO write. Only read seams are
    parameters of this function; nothing that creates a ref, puts contents or opens a pull request
    is bound here."""
    repository = candidate.repository
    owner, name = repository.split("/", 1)
    branch = presenter_branch_name()
    refusals: list[str] = [f"gate {g.name}: {g.detail}" for g in gates if not g.ok]

    head = fetch_head(repository, token=read_token)
    base_branch = getattr(head, "branch", None)
    live_revision = getattr(head, "sha", None)
    if getattr(head, "error", None) or not base_branch or not live_revision:
        refusals.append(f"target head unreadable: {getattr(head, 'error', None) or 'no branch'}")
    elif live_revision != candidate.revision:
        refusals.append(
            f"source moved: the candidate was sealed at {candidate.revision} but the target's head is "
            f"{live_revision}; re-present before proposing"
        )

    live_readme: str | None = None
    live_readme_read = False
    if base_branch:
        try:
            live = get_contents(owner, name, README_PATH, ref=base_branch, token=read_token or "")
            live_readme = None if live is None else live.text
            live_readme_read = True
        except Exception as exc:  # noqa: BLE001 -- a read failure is reported, never fatal to a dry run
            refusals.append(f"live {README_PATH} unreadable: {_short(exc, 200)}")
    if not live_readme_read:
        refusals.append("live README not read: the pull request text below is provisional (it assumes no README)")
    content = compose(candidate, live_readme)

    review_note: dict[str, Any]
    try:
        review = load_review_verdict(candidate.bundle / "review_verdict.json")
        review_note = {
            "verdict": review.verdict,
            "model_reviewed": review.model_reviewed,
            "pr_eligible": review.pr_eligible,
        }
        if review.verdict != "ACCEPT" or not review.model_reviewed:
            refusals.append("independent review: not an ACCEPT by a model review")
        # The effect's gate 3b, read-only (BL-731): the real classifier over the attested record(s) for this
        # revision, bound to the sealed README's bytes; the reviewer's frozen calibration is not an input (R33).
        verdict = evaluate_acceptance(
            acceptance_records,
            repository=repository,
            lane=candidate.lane,
            revision=candidate.revision,
            readme_bytes_sha256=candidate.bytes_sha256,
            classify_fn=classify,
        )
        review_note["acceptance_state"] = verdict.state
        review_note["acceptance_binding"] = verdict.binding
        review_note["acceptance_records_at_revision"] = verdict.records_considered
        if verdict.state not in PUBLISHABLE_STATES:
            refusals.append(
                f"acceptance contract: classified {verdict.state!r}, not one of {sorted(PUBLISHABLE_STATES)}"
                + (f" ({verdict.detail})" if verdict.detail else "")
            )
    except (ReviewVerdictError, OSError) as exc:
        review_note = {"error": _short(exc, 200)}
        refusals.append(f"independent review unreadable: {_short(exc, 200)}")

    record = record_path_for(candidate, root)
    authorization: dict[str, Any] = {"record": record.name}
    if not record.is_file():
        authorization["decision"] = "no committed authorization record exists for this exact candidate"
        refusals.append(authorization["decision"])
    else:
        try:
            loaded = authorization_loader(record, control_root=root, trigger_sha=trigger_sha or "HEAD")()
            decision = validate_authorization(
                loaded,
                now=(now or _utc_now)(),
                expected_repository=repository,
                expected_candidate_hash=candidate.candidate_hash,
                expected_source_revision=candidate.revision,
                expected_base_branch=base_branch or "",
                expected_branch=branch,
            )
            authorization["decision"] = "granted" if decision.granted else f"{decision.code}: {decision.reason}"
            if not decision.granted:
                refusals.append(f"authorization record: {authorization['decision']}")
        except WriteRefusedError as exc:
            authorization["decision"] = f"{exc.code}: {_short(exc.message, 300)}"
            refusals.append(f"authorization record: {authorization['decision']}")

    app_note = "not checked (no read token)"
    if read_token and verify_token is not None:
        token_verdict = verify_token(repository, read_token)
        app_note = (
            "installation token reaches exactly the target" if token_verdict.ok else _short(token_verdict.reason, 300)
        )

    return {
        "mode": "dry_run",
        "writes_performed": 0,
        "repository": repository,
        "lane": candidate.lane,
        "base_branch": base_branch,
        "branch": branch,
        "draft": True,
        "title": content.title,
        "body": content.body,
        "files": [
            {
                "path": README_PATH,
                "sha256": candidate.candidate_hash,
                "bytes": len(candidate.readme_text.encode("utf-8")),
            }
        ],
        "candidate_hash": candidate.candidate_hash,
        "source_revision": candidate.revision,
        "live_revision": live_revision,
        "live_readme_read": live_readme_read,
        "bundle_state": candidate.manifest_state,
        "review": review_note,
        "authorization": authorization,
        "app_token": app_note,
        "gates": [asdict(g) for g in gates],
        "write_eligible": write_eligible(gates) and not refusals,
        "refusals": refusals,
    }


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the gated write -------------------------------------------------------------------------------


def run_write(
    candidate: Candidate,
    gates: Sequence[Gate],
    *,
    environment: Mapping[str, str],
    root: Path = REPO_ROOT,
    trigger_sha: str,
    propose: Callable[..., Any] = propose_candidate,
    acceptance_records: Sequence[AttestedAcceptance] = (),
) -> int:
    """Refuse unless every gate holds, then call the effect with the App installation token."""
    repository = candidate.repository
    failed = [g for g in gates if not g.ok]
    if failed or not write_eligible(gates):
        for gate in failed:
            print(f"propose: refused by gate {gate.name}: {gate.detail}", file=sys.stderr)
        return EXIT_REFUSED
    token = environment.get(WRITE_TOKEN_VARIABLE) or None
    if token is None:
        print(f"propose: refused: no {WRITE_TOKEN_VARIABLE} (a repository-scoped App installation token)", file=sys.stderr)
        return EXIT_REFUSED
    registry = load_registry(REGISTRY)
    permit = require_write_permitted(registry, repository, "readme_proposal")
    review = load_review_verdict(candidate.bundle / "review_verdict.json")
    branch = presenter_branch_name()
    owner, name = repository.split("/", 1)

    def recheck_source() -> str:
        fresh = fetch_default_branch_sha(repository, token=token)
        return fresh.sha or f"<unreadable: {fresh.error}>"

    def reconcile_write() -> Any:
        return github_client.get_contents(owner, name, README_PATH, ref=branch, token=token)

    base = fetch_default_branch_sha(repository, token=token)
    if base.error or not base.branch:
        print(f"propose: refused: could not read {repository}'s default branch: {base.error}", file=sys.stderr)
        return EXIT_REFUSED

    result = propose(
        repository=repository,
        readme_text=candidate.readme_text,
        source_revision=candidate.revision,
        base_branch=base.branch,
        compose_pull_request=lambda live: compose(candidate, live),
        token=token,
        environment=environment,
        review=review,
        permit=permit,
        load_authorization=authorization_loader(
            record_path_for(candidate, root), control_root=root, trigger_sha=trigger_sha
        ),
        recheck_source=recheck_source,
        branch=branch,
        reconcile_write=reconcile_write,
        lane=candidate.lane,
        acceptance_records=acceptance_records,
        readme_bytes_sha256=candidate.bytes_sha256,
    )
    print(f"propose: {repository} authorized={result.authorized} effected={result.effected} - {result.reason}")
    if result.reason_code is not None:
        print(f"propose: refused ({result.reason_code})")
    if result.pr_url:
        print(
            f"  pr: {result.pr_url} (commit_written={result.commit_written} "
            f"pr_created={result.pr_created} pr_updated={result.pr_updated})"
        )
    return EXIT_OK if result.effected else EXIT_REFUSED


# --- the R17 sandbox: dry run and gated write ------------------------------------------------------------


def _sandbox_context(candidate: Candidate, environment: Mapping[str, str]) -> tuple[Any, str, str]:
    """``(entry, sandbox repository, sandbox README path)``; raises ``CandidateError`` when no sandbox is selected."""
    chosen = sandbox_repository(environment)
    if chosen is None:
        raise CandidateError(f"no sandbox is selected: {SANDBOX_VARIABLE} must name the sandbox exactly (never '*')")
    entry = load_sandbox_entry()
    return entry, chosen, entry.readme_path(candidate.repository)


def build_sandbox_payload(
    candidate: Candidate,
    gates: Sequence[Gate],
    *,
    environment: Mapping[str, str],
    read_token: str | None,
    acceptance_records: Sequence[AttestedAcceptance] = (),
    offline: bool = False,
    get_contents: Callable[..., Any] = github_client.get_contents,
    fetch_head: Callable[..., Any] = fetch_default_branch_sha,
) -> dict[str, Any]:
    """The exact sandbox branch/file/pull-request payload and every refusal, with NO write. ``offline`` makes no
    GitHub call at all (the candidate's head, its live README and the sandbox's default branch stay unread and
    are listed as such); the sealed candidate itself comes from the state ref."""
    from repo_presenter.propose.sandbox import compose_sandbox_pull_request, sandbox_branch

    repository = candidate.repository
    refusals: list[str] = [f"gate {g.name}: {g.detail}" for g in gates if not g.ok]
    try:
        entry, sandbox, sandbox_path = _sandbox_context(candidate, environment)
    except (CandidateError, SandboxConfigError) as exc:
        entry = sandbox = sandbox_path = None  # type: ignore[assignment]
        refusals.append(str(exc))
    branch = sandbox_branch(entry, repository, candidate.lane, candidate.bytes_sha256) if entry else None

    live_revision: str | None = None
    live_readme: str | None = None
    live_readme_read = False
    sandbox_base: str | None = None
    if offline:
        refusals.append("offline: the candidate's head, its live README and the sandbox's default branch were not read")
    else:
        head = fetch_head(repository, token=read_token)
        live_revision = getattr(head, "sha", None)
        if getattr(head, "error", None) or not live_revision:
            refusals.append(f"candidate head unreadable: {getattr(head, 'error', None) or 'no branch'}")
        elif live_revision != candidate.revision:
            refusals.append(f"source moved: sealed at {candidate.revision}, head is {live_revision}; re-present first")
        if getattr(head, "branch", None):
            try:
                owner, name = repository.split("/", 1)
                live = get_contents(owner, name, README_PATH, ref=head.branch, token=read_token or "")
                live_readme = None if live is None else live.text
                live_readme_read = True
            except Exception as exc:  # noqa: BLE001
                refusals.append(f"live {README_PATH} unreadable: {_short(exc, 200)}")
        if sandbox:
            base = fetch_head(sandbox, token=read_token)
            sandbox_base = getattr(base, "branch", None)
            if getattr(base, "error", None) or not sandbox_base:
                refusals.append(f"sandbox default branch unreadable: {getattr(base, 'error', None) or 'no branch'}")

    try:
        review = load_review_verdict(candidate.bundle / "review_verdict.json")
        review_note: dict[str, Any] = {"verdict": review.verdict, "model_reviewed": review.model_reviewed}
        if review.verdict != "ACCEPT" or not review.model_reviewed:
            refusals.append("independent review: not an ACCEPT by a model review")
    except (ReviewVerdictError, OSError) as exc:
        review_note = {"error": _short(exc, 200)}
        refusals.append(f"independent review unreadable: {_short(exc, 200)}")
    verdict = evaluate_acceptance(
        acceptance_records,
        repository=repository,
        lane=candidate.lane,
        revision=candidate.revision,
        readme_bytes_sha256=candidate.bytes_sha256,
        classify_fn=classify,
    )
    acceptance = {
        "state": verdict.state,
        "binding": verdict.binding,
        "records_at_revision": verdict.records_considered,
        "attestation_verified": any(r.attested for r in acceptance_records if r.revision == candidate.revision),
        "detail": verdict.detail,
    }
    if verdict.state not in PUBLISHABLE_STATES:
        refusals.append(
            f"acceptance contract: classified {verdict.state!r}, not one of {sorted(PUBLISHABLE_STATES)}"
            + (f" ({verdict.detail})" if verdict.detail else "")
        )

    content = (
        compose_sandbox_pull_request(
            candidate_repository=repository,
            lane=candidate.lane,
            candidate_readme=candidate.readme_text,
            live_readme=live_readme,
            source_revision=candidate.revision,
            readme_sha256=candidate.bytes_sha256,
            sandbox_path=sandbox_path,
            evidence=load_pull_request_evidence(candidate.bundle),
            live_read=live_readme_read,
        )
        if sandbox_path
        else None
    )
    return {
        "mode": "sandbox_dry_run",
        "writes_performed": 0,
        "github_calls": "none (offline)" if offline else "read-only",
        "candidate_repository": repository,
        "lane": candidate.lane,
        "sandbox_repository": sandbox,
        "sandbox_base_branch": sandbox_base,
        "branch": branch,
        "draft": True,
        "title": content.title if content else None,
        "body": content.body if content else None,
        "files": [{"path": sandbox_path, "sha256": candidate.bytes_sha256, "bytes": len(candidate.readme_text.encode("utf-8"))}]
        if sandbox_path
        else [],
        "source_revision": candidate.revision,
        "live_revision": live_revision,
        "live_readme_read": live_readme_read,
        "bundle_state": candidate.manifest_state,
        "review": review_note,
        "acceptance": acceptance,
        "authorization_record": "not required for the sandbox (the owner's variable selects it)",
        "gates": [asdict(g) for g in gates],
        "write_eligible": write_eligible(gates) and not refusals,
        "refusals": refusals,
    }


def run_sandbox_write(
    candidate: Candidate,
    gates: Sequence[Gate],
    *,
    environment: Mapping[str, str],
    acceptance_records: Sequence[AttestedAcceptance] = (),
    propose: Callable[..., Any] | None = None,
) -> int:
    """Refuse unless every gate holds, then open the sandbox draft pull request through the App token."""
    from repo_presenter.propose import sandbox as sandbox_module

    failed = [g for g in gates if not g.ok]
    if failed or not write_eligible(gates):
        for gate in failed:
            print(f"propose: refused by gate {gate.name}: {gate.detail}", file=sys.stderr)
        return EXIT_REFUSED
    token = environment.get(WRITE_TOKEN_VARIABLE) or None
    if token is None:
        print(f"propose: refused: no {WRITE_TOKEN_VARIABLE} (a repository-scoped App installation token)", file=sys.stderr)
        return EXIT_REFUSED
    repository = candidate.repository
    entry, sandbox, _ = _sandbox_context(candidate, environment)
    review = load_review_verdict(candidate.bundle / "review_verdict.json")
    read_token = environment.get("GH_TOKEN") or None
    base = fetch_default_branch_sha(sandbox, token=token)
    if base.error or not base.branch:
        print(f"propose: refused: could not read the sandbox's default branch: {base.error}", file=sys.stderr)
        return EXIT_REFUSED

    def live_readme() -> str | None:
        head = fetch_default_branch_sha(repository, token=read_token)
        if not head.branch:
            return None
        owner, name = repository.split("/", 1)
        live = github_client.get_contents(owner, name, README_PATH, ref=head.branch, token=read_token or "")
        return None if live is None else live.text

    def recheck_source() -> str:
        fresh = fetch_default_branch_sha(repository, token=read_token)
        return fresh.sha or f"<unreadable: {fresh.error}>"

    evidence = load_pull_request_evidence(candidate.bundle)
    result = (propose or sandbox_module.propose_sandbox)(
        candidate_repository=repository,
        lane=candidate.lane,
        readme_text=candidate.readme_text,
        source_revision=candidate.revision,
        sandbox_base_branch=base.branch,
        token=token,
        environment=environment,
        review=review,
        acceptance_records=acceptance_records,
        compose=lambda live, path, digest: sandbox_module.compose_sandbox_pull_request(
            candidate_repository=repository,
            lane=candidate.lane,
            candidate_readme=candidate.readme_text,
            live_readme=live,
            source_revision=candidate.revision,
            readme_sha256=digest,
            sandbox_path=path,
            evidence=evidence,
        ),
        live_readme_of_candidate=live_readme,
        recheck_source=recheck_source,
        readme_bytes_sha256=candidate.bytes_sha256,
        entry=entry,
    )
    print(f"propose: sandbox {result.repository} for {repository} effected={result.effected} - {result.reason}")
    if result.reason_code is not None:
        print(f"propose: refused ({result.reason_code})")
    if result.pr_url:
        print(f"  pr: {result.pr_url} (branch {result.branch}, commit_written={result.commit_written} pr_created={result.pr_created})")
    return EXIT_OK if result.effected else EXIT_REFUSED


# --- CLI -------------------------------------------------------------------------------------------


def _summary(payload: dict[str, Any] | None, gates: Sequence[Gate], title: str) -> str:
    lines = [f"## {title}", "", "| gate | ok | detail |", "|---|---|---|"]
    lines += [f"| {g.name} | {'yes' if g.ok else 'NO'} | {g.detail.replace('|', '/')} |" for g in gates]
    if payload is not None:
        lines += ["", f"write_eligible: **{payload['write_eligible']}** (writes performed: {payload['writes_performed']})", ""]
        lines += [f"- {r}" for r in payload["refusals"]]
        base = payload.get("base_branch", payload.get("sandbox_base_branch"))
        lines += ["", f"PR title: `{payload['title']}`", "", f"draft: {payload['draft']}, branch: `{payload['branch']}`, base: `{base}`"]
    return "\n".join(lines) + "\n"


def _emit_outputs(gates: Sequence[Gate]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    by_name = {g.name: g.ok for g in gates}
    with open(path, "a", encoding="utf-8") as handle:
        handle.writelines(f"{name}={'true' if by_name.get(name) else 'false'}\n" for name in GATE_NAMES)
        handle.write(f"write_eligible={'true' if write_eligible(gates) else 'false'}\n")


def _valid_repository(value: str) -> str:
    import re

    if not re.fullmatch(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}/[A-Za-z0-9._][A-Za-z0-9._-]{0,99}", value) or value.endswith("/.."):
        raise argparse.ArgumentTypeError(f"{value!r} is not OWNER/NAME")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("gates", "payload", "write"):
        p = sub.add_parser(command)
        p.add_argument("--repository", required=True, type=_valid_repository)
        p.add_argument("--summary", type=Path, help="append a Markdown report here ($GITHUB_STEP_SUMMARY)")
        p.add_argument(
            "--sandbox",
            action="store_true",
            help="R17: write the candidate to the sandbox the variable names (sandbox/<owner>__<repo>/README.md), not to its own repository",
        )
        if command == "gates":
            p.add_argument("--out", type=Path)
        else:
            p.add_argument("--lane", required=True, choices=(LANE_R, LANE_L))
            p.add_argument("--remote", default="origin")
            p.add_argument("--trigger-sha", default=os.environ.get("GITHUB_SHA", ""))
            p.add_argument("--records-remote", default="origin", help="remote holding the acceptance-record/* branches")
        if command == "payload":
            p.add_argument("--out", type=Path)
            p.add_argument("--gates-file", type=Path, help="gates already evaluated by the gate job")
            p.add_argument("--offline", action="store_true", help="make no GitHub API call (sandbox payload only)")
    args = parser.parse_args(argv)
    environment = dict(os.environ)

    def gates_for() -> list[Gate]:
        if args.sandbox:
            return evaluate_sandbox_gates(args.repository, environment)
        return evaluate_gates(args.repository, environment)

    if args.command == "gates":
        gates = gates_for()
        print(json.dumps([asdict(g) for g in gates], indent=2))
        if args.out:
            args.out.write_text(json.dumps([asdict(g) for g in gates], indent=2) + "\n", encoding="utf-8")
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as handle:
                handle.write(_summary(None, gates, f"Propose gates for {args.repository}"))
        _emit_outputs(gates)
        return EXIT_OK

    if args.command == "write":
        # Gates first, from the real environment, before any network call: a refusal costs nothing.
        gates = gates_for()
        if not write_eligible(gates):
            for gate in (g for g in gates if not g.ok):
                print(f"propose: refused by gate {gate.name}: {gate.detail}", file=sys.stderr)
            return EXIT_REFUSED
    elif args.gates_file:
        gates = [Gate(**row) for row in json.loads(args.gates_file.read_text(encoding="utf-8"))]
    else:
        gates = gates_for()

    state_token = environment.get(STATE_TOKEN_VARIABLE) or environment.get("GITHUB_TOKEN") or None
    with tempfile.TemporaryDirectory(prefix="propose-") as scratch:
        try:
            candidate = export_candidate(args.repository, args.lane, Path(scratch), remote=args.remote, token=state_token)
        except CandidateError as exc:
            print(f"propose: {exc}", file=sys.stderr)
            return EXIT_USAGE
        records = read_acceptance_evidence(
            candidate.repository, candidate.lane, remote=args.records_remote
        )
        if args.command == "write":
            if args.sandbox:
                return run_sandbox_write(candidate, gates, environment=environment, acceptance_records=records)
            return run_write(
                candidate, gates, environment=environment, trigger_sha=args.trigger_sha, acceptance_records=records
            )
        from repo_presenter.github.token_provenance import verify_installation_token

        read_token = environment.get("READ_TOKEN") or None
        if args.sandbox:
            payload = build_sandbox_payload(
                candidate, gates, environment=environment, read_token=read_token,
                acceptance_records=records, offline=args.offline,
            )
        else:
            payload = build_payload(
                candidate,
                gates,
                read_token=read_token,
                trigger_sha=args.trigger_sha,
                verify_token=verify_installation_token if (read_token or "").startswith("ghs_") else None,
                acceptance_records=records,
            )
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        print(text)
        if args.out:
            args.out.write_text(text + "\n", encoding="utf-8")
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as handle:
                handle.write(_summary(payload, gates, f"Propose dry run for {args.repository} lane {args.lane}"))
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
