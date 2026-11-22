"""R17 sandbox write path (`repo_presenter.propose.sandbox`) and its scope (`repo_presenter.sandbox_scope`).
Fakes only: no GitHub call. The acceptance gate is the REAL classifier over the repository's committed
certificates (see test_acceptance_evidence.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter import sandbox_scope
from repo_presenter.authorization.refusals import Refusal
from repo_presenter.github.client import FileContents, PullRequestRef
from repo_presenter.github.errors import RepositoryMetadataError
from repo_presenter.propose import effect, sandbox
from repo_presenter.propose.acceptance_evidence import AttestedAcceptance, bytes_sha256
from repo_presenter.propose.pull_request import PullRequestEvidence
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

SANDBOX = "babar-raza/repo-presenter"
CANDIDATE = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
REVISION = "1a6004af47b1" + "0" * 28
README = "# Cells for Rust\n\nIntro.\n\n## Install\n\nRun it.\n"
DIGEST = bytes_sha256(README)
VERDICTS = {"M1": True, "M2": True, "M3": True, "M4": True, "M5": True, "M6": True, "M7": True, "M10": True}
ENV = {effect.AUTHORIZATION_VARIABLE: "1", sandbox_scope.SANDBOX_VARIABLE: SANDBOX}
ACCEPT = ReviewVerdict.folded((), model_verdict="ACCEPT", prompt_version="17", model_served="qwen3-next",
                              request_sha256="a" * 64, reply_sha256="b" * 64, calibration_status="NOT_PASSED")
RECORD = AttestedAcceptance(CANDIDATE, "R", REVISION, DIGEST, True, VERDICTS, {}, True, True)
OK = SimpleNamespace(ok=True, code=None, reason="ok")


class Fake:
    def __init__(self, *, prs: tuple[PullRequestRef, ...] = (), branch_exists: bool = False, file: FileContents | None = None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.prs, self.branch_exists, self.file = prs, branch_exists, file

    def _rec(self, name: str, *a: Any, **k: Any) -> None:
        self.calls.append((name, a, k))

    def get_ref(self, owner: str, name: str, branch: str, *, token: str) -> str | None:
        self._rec("get_ref", owner, name, branch)
        if branch == "main":
            return "base-sha"
        return "branch-sha" if self.branch_exists else None

    def create_ref(self, owner: str, name: str, branch: str, sha: str, *, token: str) -> None:
        self._rec("create_ref", owner, name, branch, sha)

    def get_contents(self, owner: str, name: str, path: str, *, ref: str, token: str) -> FileContents | None:
        self._rec("get_contents", owner, name, path, ref)
        return self.file

    def put_contents(self, owner: str, name: str, path: str, **k: Any) -> object:
        self._rec("put_contents", owner, name, path, **k)
        return object()

    def find_pull_requests(self, owner: str, name: str, *, head_branch: str, token: str) -> tuple[PullRequestRef, ...]:
        self._rec("find_pull_requests", owner, name, head_branch)
        return self.prs

    def create_pull_request(self, owner: str, name: str, **k: Any) -> PullRequestRef:
        self._rec("create_pull_request", owner, name, **k)
        return PullRequestRef(7, f"https://github.com/{owner}/{name}/pull/7", k["title"], k["body"], "open")

    @property
    def writes(self) -> list[str]:
        return [c[0] for c in self.calls if c[0] in {"create_ref", "put_contents", "create_pull_request"}]


def compose(live: str | None, path: str, digest: str):
    return sandbox.compose_sandbox_pull_request(
        candidate_repository=CANDIDATE, lane="R", candidate_readme=README, live_readme=live, source_revision=REVISION,
        readme_sha256=digest, sandbox_path=path, evidence=PullRequestEvidence(2, 2, True, 9, 9),
    )


def run(fake: Fake, **overrides: Any) -> effect.ProposalEffectResult:
    fields: dict[str, Any] = dict(
        candidate_repository=CANDIDATE, lane="R", readme_text=README, source_revision=REVISION,
        sandbox_base_branch="main", token="ghs_write", environment=dict(ENV), review=ACCEPT,
        acceptance_records=(RECORD,), compose=compose, live_readme_of_candidate=lambda: "# Cells for Rust\n\nOld.\n",
        recheck_source=lambda: REVISION, verify_token=lambda repo, token: OK,
        verify_pull_request_app=lambda *a, **k: OK, get_ref=fake.get_ref, create_ref=fake.create_ref,
        get_contents=fake.get_contents, put_contents=fake.put_contents,
        find_pull_requests=fake.find_pull_requests, create_pull_request=fake.create_pull_request,
    )
    fields.update(overrides)
    return sandbox.propose_sandbox(**fields)


def test_the_happy_path_opens_one_draft_pr_on_a_throwaway_branch_and_writes_only_under_sandbox() -> None:
    fake = Fake()
    result = run(fake)
    assert result.effected and result.pr_created and result.commit_written and result.repository == SANDBOX
    assert fake.writes == ["create_ref", "put_contents", "create_pull_request"]
    branch = result.branch
    assert branch == f"repository-presenter/sandbox/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust-r-{DIGEST[:12]}"
    put = next(c for c in fake.calls if c[0] == "put_contents")
    assert put[1][2] == "sandbox/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust/README.md"  # never the sandbox's own README
    assert put[2]["branch"] == branch and put[2]["text"] == README
    pr = next(c for c in fake.calls if c[0] == "create_pull_request")[2]
    assert pr["draft"] is True and pr["head"] == branch and pr["base"] == "main"
    assert next(c for c in fake.calls if c[0] == "create_pull_request")[1][:2] == ("babar-raza", "repo-presenter")


def test_the_body_is_factual_with_no_attribution_or_provenance_wording() -> None:
    pr = compose("# Cells for Rust\n\nOld.\n", "sandbox/x__y/README.md", DIGEST)
    lowered = (pr.title + "\n" + pr.body).lower()
    for word in sandbox.FORBIDDEN_BODY_WORDS:
        assert word not in lowered, word
    assert DIGEST in pr.body and REVISION[:12] in pr.body and "sandbox/x__y/README.md" in pr.body
    assert not re.search(r"candidate_hash|policy_version|proposed by", lowered)


@pytest.mark.parametrize("env", [{}, {sandbox_scope.SANDBOX_VARIABLE: ""}, {sandbox_scope.SANDBOX_VARIABLE: "*"},
                                 {sandbox_scope.SANDBOX_VARIABLE: CANDIDATE}, {sandbox_scope.SANDBOX_VARIABLE: "babar-raza/other"}])
def test_no_call_is_made_unless_the_variable_names_the_sandbox_exactly(env: dict[str, str]) -> None:
    fake = Fake()
    result = run(fake, environment={effect.AUTHORIZATION_VARIABLE: "1", **env})
    assert result.reason_code == Refusal.SANDBOX_NOT_SELECTED and not result.effected and fake.calls == []


def test_the_variable_is_matched_case_insensitively_but_never_as_a_wildcard() -> None:
    assert sandbox_scope.sandbox_repository({sandbox_scope.SANDBOX_VARIABLE: "Babar-Raza/Repo-Presenter"}) == SANDBOX
    assert sandbox_scope.sandbox_repository({sandbox_scope.SANDBOX_VARIABLE: "babar-raza/*"}) is None


def test_every_candidate_gate_runs_before_any_call() -> None:
    cases = [
        (dict(environment={sandbox_scope.SANDBOX_VARIABLE: SANDBOX}), Refusal.WRITE_NOT_ENABLED),
        (dict(review=ReviewVerdict.folded((), model_verdict="REJECT", prompt_version="17", model_served="m",
                                          request_sha256="a" * 64, reply_sha256="b" * 64, calibration_status="PASSED")), Refusal.REVIEW_REJECTED),
        (dict(acceptance_records=()), Refusal.ACCEPTANCE_NOT_CERTIFIED),
        (dict(acceptance_records=(AttestedAcceptance(CANDIDATE, "R", REVISION, None, True, VERDICTS, {}, True, True),)), Refusal.ACCEPTANCE_NOT_CERTIFIED),
        (dict(token=None), Refusal.NO_WRITE_TOKEN),
        (dict(verify_token=lambda r, t: SimpleNamespace(ok=False, code=Refusal.TOKEN_WRONG_SCOPE, reason="scope")), Refusal.TOKEN_WRONG_SCOPE),
        (dict(recheck_source=lambda: "f" * 40), Refusal.SOURCE_MOVED),
    ]
    for overrides, code in cases:
        fake = Fake()
        result = run(fake, **overrides)
        assert result.reason_code == code and not result.effected, (overrides, result.reason)
        assert fake.writes == []


def test_the_token_is_verified_against_the_sandbox_repository() -> None:
    seen: list[str] = []
    run(Fake(), verify_token=lambda repo, token: seen.append(repo) or OK)
    assert seen == [SANDBOX]


@pytest.mark.parametrize("state", ["open", "closed", "merged"])
def test_a_duplicate_is_refused_whatever_state_the_earlier_pull_request_is_in(state: str) -> None:
    prior = PullRequestRef(3, "https://github.com/babar-raza/repo-presenter/pull/3", "t", "b", state)
    fake = Fake(prs=(prior,))
    result = run(fake)
    assert result.reason_code == Refusal.PR_DUPLICATE and result.pr_number == 3 and not result.effected
    assert fake.writes == []


def test_a_branch_left_without_a_pr_is_completed_not_duplicated() -> None:
    fake = Fake(branch_exists=True, file=FileContents("sandbox/x/README.md", "blob", README))
    result = run(fake)
    assert result.effected and result.pr_created and not result.commit_written
    assert fake.writes == ["create_pull_request"]  # branch exists and the file is already right


def test_a_pr_attributed_to_another_identity_is_reported_not_effected() -> None:
    bad = SimpleNamespace(ok=False, code=Refusal.TOKEN_APP_MISMATCH, reason="not our app")
    result = run(Fake(), verify_pull_request_app=lambda *a, **k: bad)
    assert not result.effected and result.reason_code == Refusal.TOKEN_APP_MISMATCH and result.pr_created


def test_a_github_error_on_the_write_is_a_typed_refusal() -> None:
    fake = Fake()

    def boom(*a: Any, **k: Any) -> None:
        raise RepositoryMetadataError("HTTP 500")

    result = run(fake, put_contents=boom)
    assert result.reason_code == Refusal.GITHUB_ERROR and "create_pull_request" not in fake.writes


# --- the data file ------------------------------------------------------------------------------------------------


def test_the_committed_sandbox_entry_is_the_owners_choice_and_the_allowlist_is_untouched() -> None:
    entry = sandbox_scope.load_sandbox_entry()
    assert entry.repository == SANDBOX and entry.first_pr_as_draft
    assert entry.readme_path(CANDIDATE) == "sandbox/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust/README.md"
    raw = json.loads(Path(sandbox_scope.SANDBOX_TARGET_FILE).read_text(encoding="utf-8"))
    assert "owner" in raw["_comment"] and "2026-11-22" in raw["_comment"]
    allowlist = json.loads((sandbox_scope.REPO_ROOT / "data" / "upstream_write_allowlist.json").read_text(encoding="utf-8"))
    assert SANDBOX not in {r["repository"] for r in allowlist["repositories"]} and len(allowlist["repositories"]) == 9


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(sandbox_path_template="README.md"),
    lambda e: e.update(sandbox_path_template="sandbox/../{owner}{name}"),
    lambda e: e.update(sandbox_branch_prefix="main/"),
    lambda e: e.update(first_pr_as_draft=False),
    lambda e: e.update(repository="not-a-repo"),
])
def test_a_malformed_sandbox_file_selects_no_sandbox(tmp_path: Path, mutate: Any) -> None:
    doc = json.loads(Path(sandbox_scope.SANDBOX_TARGET_FILE).read_text(encoding="utf-8"))
    mutate(doc["sandbox"])
    path = tmp_path / "s.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert sandbox_scope.sandbox_repository(ENV, path) is None
    assert sandbox_scope.sandbox_repository(ENV, tmp_path / "missing.json") is None
