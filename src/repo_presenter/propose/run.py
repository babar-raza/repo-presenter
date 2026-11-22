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
5. ``sandbox_target`` the owner variable ``REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY`` names exactly
                      this target. Unset or empty fails closed. The owner lifts the restriction only
                      by setting that variable to ``*`` (every allowlisted repository then passes
                      this gate, the other four unchanged).

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

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY = REPO_ROOT / "data" / "registry.json"
#: The repository variable that names the one repository the write job may touch (gate 5).
SANDBOX_VARIABLE = "REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY"
#: The owner's lift of the sandbox restriction: every allowlisted repository passes gate 5.
SANDBOX_LIFTED = "*"
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


def _short(text: str, limit: int = 600) -> str:
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


def gate_portfolio(readiness: Callable[[], Any] | None = None) -> Gate:
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
        gate_portfolio(readiness),
        gate_sandbox(repository, environment),
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

    @property
    def candidate_hash(self) -> str:
        return sha256_text(self.readme_text)


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
        # The effect's gate 3b, read-only: the acceptance contract must classify the candidate as publishable.
        state = classify(
            repository, "unspecified", sealed=True, mechanism_verdicts={"independent_review": review.pr_eligible}
        )
        review_note["acceptance_state"] = state
        if state not in PUBLISHABLE_STATES:
            refusals.append(f"acceptance contract: classified {state!r}, not one of {sorted(PUBLISHABLE_STATES)}")
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
        verdict = verify_token(repository, read_token)
        app_note = "installation token reaches exactly the target" if verdict.ok else _short(verdict.reason, 300)

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


# --- CLI -------------------------------------------------------------------------------------------


def _summary(payload: dict[str, Any] | None, gates: Sequence[Gate], title: str) -> str:
    lines = [f"## {title}", "", "| gate | ok | detail |", "|---|---|---|"]
    lines += [f"| {g.name} | {'yes' if g.ok else 'NO'} | {g.detail.replace('|', '/')} |" for g in gates]
    if payload is not None:
        lines += ["", f"write_eligible: **{payload['write_eligible']}** (writes performed: {payload['writes_performed']})", ""]
        lines += [f"- {r}" for r in payload["refusals"]]
        lines += ["", f"PR title: `{payload['title']}`", "", f"draft: {payload['draft']}, branch: `{payload['branch']}`, base: `{payload['base_branch']}`"]
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
        if command == "gates":
            p.add_argument("--out", type=Path)
        else:
            p.add_argument("--lane", required=True, choices=(LANE_R, LANE_L))
            p.add_argument("--remote", default="origin")
            p.add_argument("--trigger-sha", default=os.environ.get("GITHUB_SHA", ""))
        if command == "payload":
            p.add_argument("--out", type=Path)
            p.add_argument("--gates-file", type=Path, help="gates already evaluated by the gate job")
    args = parser.parse_args(argv)
    environment = dict(os.environ)

    if args.command == "gates":
        gates = evaluate_gates(args.repository, environment)
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
        gates = evaluate_gates(args.repository, environment)
        if not write_eligible(gates):
            for gate in (g for g in gates if not g.ok):
                print(f"propose: refused by gate {gate.name}: {gate.detail}", file=sys.stderr)
            return EXIT_REFUSED
    elif args.gates_file:
        gates = [Gate(**row) for row in json.loads(args.gates_file.read_text(encoding="utf-8"))]
    else:
        gates = evaluate_gates(args.repository, environment)

    state_token = environment.get(STATE_TOKEN_VARIABLE) or environment.get("GITHUB_TOKEN") or None
    with tempfile.TemporaryDirectory(prefix="propose-") as scratch:
        try:
            candidate = export_candidate(args.repository, args.lane, Path(scratch), remote=args.remote, token=state_token)
        except CandidateError as exc:
            print(f"propose: {exc}", file=sys.stderr)
            return EXIT_USAGE
        if args.command == "write":
            return run_write(candidate, gates, environment=environment, trigger_sha=args.trigger_sha)
        from repo_presenter.github.token_provenance import verify_installation_token

        read_token = environment.get("READ_TOKEN") or None
        payload = build_payload(
            candidate,
            gates,
            read_token=read_token,
            trigger_sha=args.trigger_sha,
            verify_token=verify_installation_token if (read_token or "").startswith("ghs_") else None,
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
