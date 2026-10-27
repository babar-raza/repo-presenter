"""Hosted Lane L, end to end and offline (plans/PLAN_lane_l_hosted.md).

A disposable upstream git repository stands in for the target (cloned through ``file://``); the
hosted flow is driven through the real CLI entry (``--stage facts`` then ``--stage cascade --lane
L``) against the real git-ref durable-state backend on a disposable local remote. The only fake is
the provider: ``transport.build_client`` is replaced by a scripted client, so no model is ever
called and every provider call a run makes is counted.

What is proven here, each with a falsifier in the test that follows it:

* a README with a known defect becomes a corrected, reviewed, sealed Lane L candidate whose every
  byte outside the one evidenced edit is the maintainers' own;
* an unchanged rerun, from another working directory with another newline setting, writes the same
  bytes, makes zero provider calls, and moves the bundle to READY_FOR_PROPOSAL;
* a README with nothing to correct is sealed honestly as NO_CHANGE_WARRANTED (no edit, no invented
  improvement);
* the lanes are isolated: a Lane L seal never touches Lane R's bundle, pointer or transaction, and
  the reverse;
* a candidate seals only on a model-reviewed ACCEPT; a reviewer outage is a retryable failure; a
  defect the engine may not repair is refused with a Lane R recommendation and the model is never
  asked.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from support import (
    commit_all,
    head_revision,
    init_git_repository,
    monitor_registry_entry,
    write_registry_file,
)

from repo_presenter import lane_l_run, present
from repo_presenter.core.candidates import (
    LANE_L,
    LANE_R,
    count_current_candidates,
    lane_directory,
    portfolio_status,
    ready_revision,
    verify_bundle,
)
from repo_presenter.core.examples import ExampleReceipt
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.ledger import load_records
from repo_presenter.core.noop_proof import Invocation, ProcessIdentity
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.extractors.platforms import python as python_platform
from repo_presenter.facts_handoff import MANIFEST_FILENAME
from repo_presenter.present import main
from repo_presenter.readme.evidence.facts import links
from repo_presenter.readme.review.independent_reviewer import Finding
from repo_presenter.readme.review.verdict import ReviewUnavailable, ReviewVerdict
from repo_presenter.readme.review.verdict_io import load_review_verdict

REPOSITORY = "aspose-widget-foss/Aspose.Widget-FOSS-for-Python"
SLUG = REPOSITORY.replace("/", "__")
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"

#: The maintainers' README. One link is broken by letter case (``docs/Usage.md``; the tree holds
#: ``docs/usage.md``), the one defect the engine can repair deterministically, with an evidenced,
#: one-fragment edit. Every other byte is the maintainers' own.
DEFECTIVE_README = (
    "# Widget\n"
    "\n"
    "A plain description of the widget library, in the maintainers' own words.\n"
    "\n"
    "## Documentation\n"
    "\n"
    "See the [usage guide](docs/Usage.md) for the details.\n"
    "\n"
    "## Quick start\n"
    "\n"
    "```python\n"
    "import widget\n"
    "widget.render()\n"
    "```\n"
)
CORRECTED_README = DEFECTIVE_README.replace("docs/Usage.md", "docs/usage.md")
CLEAN_README = DEFECTIVE_README.replace("docs/Usage.md", "docs/usage.md")


def _completion(content: dict[str, Any], model: str = "qwen3-next") -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model=model, id="req", usage=usage)


def accept_reply() -> Any:
    return _completion({"verdict": "ACCEPT", "findings": [], "preserve": []})


class Provider:
    """The scripted gateway: replies in call order, then ``default`` for every further call when
    one is given; a call beyond the script is an error, so a run that was meant to make no provider
    call fails loudly if it makes one. ``Provider(monkeypatch, default=accept_reply())`` answers ACCEPT
    to however many reviewer requests the reviewer makes, so these tests prove Lane L's wiring
    without depending on how many requests a review is split into."""

    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, *replies: Any, default: Any = None
    ) -> None:
        self.replies = list(replies)
        self.payloads: list[dict[str, Any]] = []

        def create(**payload: Any) -> Any:
            self.payloads.append(payload)
            if not self.replies:
                if default is None:
                    raise AssertionError(
                        "the provider was called but no reply was scripted"
                    )
                return default
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        monkeypatch.setattr(
            jobs_module.transport, "build_client", lambda config: client
        )

    @property
    def calls(self) -> int:
        return len(self.payloads)


def fresh_invocation(seed: int) -> Invocation:
    """A different process from whatever sealed the first manifest: a real second run is a new
    process, which this single pytest process cannot be, so the identity is hand-built (the same
    device ``tests/readme/bundle/test_seal.py`` uses)."""
    import uuid

    identity = ProcessIdentity(
        pid=900000 + seed,
        started="2026-10-27T00:00:00Z",
        boot_id="other-boot",
        nonce=f"other-nonce-{seed}",
    )
    return Invocation(uuid.uuid4().hex, identity, "2026-10-27T00:00:01Z")


def make_upstream(
    root: Path, readme: str, *, files: dict[str, str] | None = None
) -> Path:
    upstream = init_git_repository(root)
    (upstream / "README.md").write_bytes(readme.encode("utf-8"))
    (upstream / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted.\n", encoding="utf-8"
    )
    (upstream / "widget.py").write_text(
        "def render():\n    return 1\n", encoding="utf-8"
    )
    (upstream / "docs").mkdir()
    (upstream / "docs" / "usage.md").write_text(
        "# Usage\n\nCall render().\n", encoding="utf-8"
    )
    for name, text in (files or {}).items():
        target = upstream / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    commit_all(upstream, "seed")
    return upstream


def stub_verifier(
    root: Path, tree_paths: Any, candidates: Any, workspace: Path
) -> list[Any]:
    """Stands in for the real example verifier (a venv and a pip install per run): an example that
    calls ``does_not_exist`` fails, every other one runs. The real verifier is exercised by the
    zero-drift test, which is the one that needs its machine-independence."""
    return [
        ExampleReceipt(
            candidate.ordinal,
            "FAILED" if "does_not_exist" in candidate.code else "EXECUTED",
            1 if "does_not_exist" in candidate.code else 0,
            "",
            "AttributeError: module 'widget' has no attribute 'does_not_exist'"
            if "does_not_exist" in candidate.code
            else "",
            "ran",
        )
        for candidate in candidates
    ]


class Hosted:
    """One disposable hosted environment: an upstream, a registry, a state remote and a directory
    each stage writes under. ``facts`` and ``lane_l`` call the real CLI entry."""

    def __init__(
        self,
        root: Path,
        monkeypatch: pytest.MonkeyPatch,
        readme: str = DEFECTIVE_README,
        *,
        files: dict[str, str] | None = None,
        real_verifier: bool = False,
    ) -> None:
        self.root = root
        self.monkeypatch = monkeypatch
        if not real_verifier:
            monkeypatch.setattr(
                python_platform, "verify_python_examples", stub_verifier
            )
        monkeypatch.setattr(
            links, "fetch_status", lambda url, transport=None: (200, url)
        )
        self.upstream = make_upstream(root / "upstream", readme, files=files)
        monkeypatch.setattr(
            present, "_clone_url", lambda repository: self.upstream.as_uri()
        )
        self.registry = write_registry_file(
            root / "reg",
            [monitor_registry_entry(REPOSITORY, mode="full", repository_id=7)],
        )
        self.remote = init_git_repository(root / "state-remote")
        self.candidates = root / "candidates-root"
        monkeypatch.setenv("GPT_OSS_ENDPOINT", "http://127.0.0.1:9/v1")
        monkeypatch.setenv("GPT_OSS_API_KEY", "not-a-real-key")
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    def args(
        self, stage: str, tag: str, *extra: str, lane: str | None = None
    ) -> list[str]:
        argv = [
            "--stage",
            stage,
            "--repository",
            REPOSITORY,
            "--ecosystem",
            "python",
            "--registry",
            str(self.registry),
            "--prompts",
            str(PROMPTS),
            "--workdir",
            str(self.root / f"work-{tag}"),
            "--facts-dir",
            str(self.root / f"handoff-{tag}"),
            "--candidates-root",
            str(self.candidates),
            *extra,
        ]
        if lane is not None:
            argv += ["--lane", lane]
        return argv

    def facts(self, tag: str) -> str:
        assert main(self.args("facts", tag)) == 0
        manifest = json.loads(
            (self.root / f"handoff-{tag}" / MANIFEST_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        return str(manifest["facts_sha256"])

    def stage(self, tag: str, lane: str | None, digest: str | None = None) -> int:
        extra = ["--state-remote", str(self.remote)]
        if digest is not None:
            extra += ["--expected-facts-sha256", digest]
        return main(self.args("cascade", tag, *extra, lane=lane))

    def lane_l(self, tag: str, digest: str | None = None) -> int:
        return self.stage(tag, "L", digest)

    def record(self, lane: str) -> Any:
        with GitStateBackend(remote=str(self.remote), lane=lane) as backend:
            return backend.load(REPOSITORY)

    def bundle(self, lane: str = LANE_L) -> Path:
        root = lane_directory(self.candidates / "candidates" / SLUG, lane)
        revision = (root / "CURRENT").read_text(encoding="utf-8").strip()
        return root / revision

    def manifest(self, lane: str = LANE_L) -> dict[str, Any]:
        return json.loads(
            (self.bundle(lane) / "manifest.json").read_text(encoding="utf-8")
        )


@pytest.fixture
def hosted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Hosted:
    return Hosted(tmp_path, monkeypatch)


def digest_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# --- 1. a known defect becomes a corrected, reviewed, sealed candidate -----------------------------


def test_a_readme_with_a_broken_link_becomes_a_corrected_reviewed_sealed_candidate(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = Provider(monkeypatch, default=accept_reply())
    digest = hosted.facts("a")

    assert hosted.lane_l("a", digest) == 0

    bundle = hosted.bundle()
    manifest = verify_bundle(bundle, LANE_L)
    assert manifest is not None
    assert manifest["lane"] == "L" and manifest["schema_version"] == 2
    assert (
        manifest["state"] == "ACCEPTED"
    )  # sealed; the no-op proof needs a second, fresh run
    assert manifest["revision"] == head_revision(hosted.upstream)
    assert manifest["correction"] == {
        "outcome": "CORRECTED",
        "edits": 1,
        "defects": 0,
        "opportunities": 1,
    }

    # The candidate is the live README with exactly one evidenced fragment changed.
    assert (bundle / "README.md").read_bytes() == CORRECTED_README.encode("utf-8")
    assert (bundle / "README.original.md").read_bytes() == DEFECTIVE_README.encode(
        "utf-8"
    )
    report = json.loads((bundle / "corrections.json").read_text(encoding="utf-8"))
    (edit,) = report["edits"]
    assert (edit["kind"], edit["original"], edit["replacement"]) == (
        "BROKEN_LINK",
        "docs/Usage.md",
        "docs/usage.md",
    )
    assert edit["evidence"][0]["status"] == "CONTRADICTED"
    assert report["confinement"]["verified"] is True
    assert report["stability"] == {
        "deterministic": True,
        "idempotent": True,
        "provider_calls": 0,
    }
    patch = (bundle / "README.patch.diff").read_text(encoding="utf-8")
    assert (
        "-See the [usage guide](docs/Usage.md)" in patch
        and "+See the [usage guide](docs/usage.md)" in patch
    )

    # The FINAL README was reviewed by the model, and the one provider call is on the one ledger.
    verdict = load_review_verdict(bundle / "review_verdict.json")
    assert verdict.verdict == "ACCEPT" and verdict.model_reviewed
    records = load_records(bundle / "ledger.jsonl")
    assert provider.calls >= 1
    assert {record.job for record in records} == {"independent_review"}
    assert (
        sum(record.disposition == "provider_call" for record in records)
        == provider.calls
    )
    requests = json.dumps(provider.payloads)
    assert (
        "docs/usage.md" in requests and "docs/Usage.md" in requests
    )  # candidate and original

    # Its own transaction, in its own lane: Lane L accepted, Lane R untouched.
    record = hosted.record("L")
    assert record is not None and record.lane == "L" and record.state == "ACCEPTED"
    assert record.lease is None
    assert record.last_transition is not None
    assert record.last_transition.output_manifest == f"candidates/{SLUG}/lane-l/CURRENT"
    assert hosted.record("R") is None
    assert not (hosted.candidates / "candidates" / SLUG / "CURRENT").exists()
    rows = {row.lane: row for row in portfolio_status(hosted.candidates)}
    assert rows[LANE_L].status == "ACCEPTED" and rows[LANE_R].status == "NO_BUNDLE"


def test_the_corrected_candidate_is_the_live_readme_outside_its_one_edit(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falsifier for the confinement claim: the corrected text with the edit's span removed is the
    original with the same span removed, and a README whose edit is widened by one byte fails the
    holdout (tests/readme/correction/test_lane_l_review.py proves the holdout itself)."""
    Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("b", hosted.facts("b")) == 0
    bundle = hosted.bundle()
    original = (bundle / "README.original.md").read_text(encoding="utf-8")
    corrected = (bundle / "README.md").read_text(encoding="utf-8")
    report = json.loads((bundle / "corrections.json").read_text(encoding="utf-8"))
    (edit,) = report["edits"]
    assert original[: edit["start"]] + original[edit["end"] :] == (
        corrected[: edit["start"]]
        + corrected[edit["start"] + len(edit["replacement"]) :]
    )
    assert len(original) - len(corrected) == len(edit["original"]) - len(
        edit["replacement"]
    )


# --- 2. the zero-drift rerun ---------------------------------------------------------------------


def restore_state(hosted: Hosted, first_tag: str, second_tag: str) -> None:
    """What the workflow's cache restore does: the previous run's sealed bundle and call store
    reach the next runner. Nothing else carries over."""
    import shutil

    shutil.copytree(
        hosted.root / f"work-{first_tag}" / "lane-l" / "llm_cache",
        hosted.root / f"work-{second_tag}" / "lane-l" / "llm_cache",
    )


def test_an_unchanged_rerun_from_another_directory_and_newline_setting_is_byte_identical_with_zero_provider_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """This is the one test that runs the real example verifier: the facts it seals must not
    depend on where it ran (hosted Lane L found pip's error quoting the checkout's path)."""
    hosted = Hosted(tmp_path, monkeypatch, real_verifier=True)
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("run1", hosted.facts("run1")) == 0
    sealed_first = digest_tree(hosted.bundle())
    assert provider.calls >= 1

    # Run 2 is a different "machine": another working directory, git told to convert line endings
    # (a Windows checkout), a new process identity, and a provider that fails if it is called.
    elsewhere = tmp_path / "somewhere" / "else"
    elsewhere.mkdir(parents=True)
    crlf = tmp_path / "gitconfig-crlf"
    crlf.write_text("[core]\n\tautocrlf = true\n\teol = crlf\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(crlf))
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(Invocation, "begin", staticmethod(lambda: fresh_invocation(2)))
    restore_state(hosted, "run1", "run2")
    rerun_provider = Provider(monkeypatch)  # no replies: any call raises

    assert hosted.lane_l("run2", hosted.facts("run2")) == 0

    assert rerun_provider.calls == 0
    sealed_second = digest_tree(hosted.bundle())
    for name in (
        "README.md",
        "README.original.md",
        "README.patch.diff",
        "corrections.json",
        "holdouts.json",
        "facts.json",
        "review_verdict.json",
        "dependencies.json",
    ):
        assert sealed_second[name] == sealed_first[name], name
    manifest = hosted.manifest()
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    proof = manifest["no_op_proof"]
    assert proof["byte_identical"] is True and proof["fresh_process"] is True
    assert proof["provider_calls"] == 0
    assert proof["first_run"]["invocation_id"] != proof["rerun"]["invocation_id"]
    record = hosted.record("L")
    assert record is not None and record.state == "READY_FOR_PROPOSAL"
    assert count_current_candidates(hosted.candidates, LANE_L) == 1
    assert count_current_candidates(hosted.candidates, LANE_R) == 0
    assert ready_revision(hosted.candidates, REPOSITORY, LANE_L) == head_revision(
        hosted.upstream
    )

    # Control: the same newline setting DOES change a plain clone's bytes, so the equality above is
    # the pinned clone's doing and not an accident of the environment.
    plain = tmp_path / "plain-clone"
    subprocess.run(
        ["git", "clone", "-q", hosted.upstream.as_uri(), str(plain)],
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": str(crlf)},
    )
    assert b"\r\n" in (plain / "README.md").read_bytes()
    assert b"\r" not in (hosted.bundle() / "README.original.md").read_bytes()


def test_without_the_restored_call_store_the_rerun_asks_the_model_again_and_proves_nothing(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Falsifier for the zero-call claim: the byte-identical rerun is a replay from the call
    store, not a repeatable model. Lose the store and the rerun spends a call and cannot be a
    no-op proof (the seal withholds it rather than faking it)."""
    Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("run1", hosted.facts("run1")) == 0
    monkeypatch.setattr(Invocation, "begin", staticmethod(lambda: fresh_invocation(3)))
    provider = Provider(
        monkeypatch, default=accept_reply()
    )  # calls allowed: the store is gone
    with pytest.raises(NotImplementedError, match="provider call"):
        hosted.lane_l("run2", hosted.facts("run2"))
    assert provider.calls >= 1
    assert (
        hosted.manifest()["state"] == "ACCEPTED"
    )  # never promoted to READY_FOR_PROPOSAL


# --- 3. nothing to correct is a legitimate, honest outcome ------------------------------------------


def test_a_readme_with_nothing_to_correct_is_sealed_as_no_change_warranted_not_an_invented_improvement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = Hosted(tmp_path, monkeypatch, CLEAN_README)
    provider = Provider(monkeypatch, default=accept_reply())

    assert hosted.lane_l("clean", hosted.facts("clean")) == 0

    bundle = hosted.bundle()
    manifest = verify_bundle(bundle, LANE_L)
    assert manifest is not None
    assert manifest["correction"] == {
        "outcome": "NO_CHANGE_WARRANTED",
        "edits": 0,
        "defects": 0,
        "opportunities": 1,
    }
    assert (bundle / "README.md").read_bytes() == CLEAN_README.encode("utf-8")
    assert (bundle / "README.md").read_bytes() == (
        bundle / "README.original.md"
    ).read_bytes()
    assert (bundle / "README.patch.diff").read_bytes() == b""  # nothing to propose
    report = json.loads((bundle / "corrections.json").read_text(encoding="utf-8"))
    assert report["outcome"] == "NO_CHANGE_WARRANTED" and report["edits"] == []
    # It is still judged: the model reads the final README (the live one) before it is sealed.
    assert provider.calls >= 1
    assert load_review_verdict(bundle / "review_verdict.json").model_reviewed
    record = hosted.record("L")
    assert record is not None and record.state == "ACCEPTED"


# --- 4. lane isolation ---------------------------------------------------------------------------------


def seal_lane_r_fixture(candidates_root: Path, revision: str) -> Path:
    """A Lane R bundle for the same repository, in the layout v1 every earlier seal used."""
    from tests.core.test_candidates_lanes import seal

    return seal(
        candidates_root,
        LANE_R,
        revision=revision,
        schema_version=1,
        slug=SLUG,
        repository=REPOSITORY,
    )


def test_a_lane_l_seal_never_touches_the_lane_r_bundle_pointer_or_transaction(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    r_bundle = seal_lane_r_fixture(hosted.candidates, "a" * 40)
    lane_r_before = {
        path: digest
        for path, digest in digest_tree(hosted.candidates / "candidates" / SLUG).items()
        if not path.startswith("lane-l/")
    }
    Provider(monkeypatch, default=accept_reply())

    assert hosted.lane_l("iso", hosted.facts("iso")) == 0

    lane_r_after = {
        path: digest
        for path, digest in digest_tree(hosted.candidates / "candidates" / SLUG).items()
        if not path.startswith("lane-l/")
    }
    assert lane_r_after == lane_r_before
    assert r_bundle.is_dir()
    assert ready_revision(hosted.candidates, REPOSITORY, LANE_R) == "a" * 40
    assert (
        ready_revision(hosted.candidates, REPOSITORY, LANE_L) is None
    )  # ACCEPTED, not proven
    assert hosted.record("R") is None  # Lane R's transaction record was never written
    assert hosted.record("L") is not None


def test_a_lane_r_seal_never_touches_the_lane_l_bundle(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tests.readme.bundle.test_seal import _inputs

    Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("iso2", hosted.facts("iso2")) == 0
    lane_l_before = digest_tree(hosted.bundle().parent)

    from repo_presenter.readme.bundle.seal import seal_candidate

    # Same candidates root, same repository, other lane: seal Lane R beside the Lane L bundle.
    (tmp_path / "r-seal").mkdir()
    r_inputs = _inputs(tmp_path / "r-seal")
    entry = hosted_entry(hosted)
    shared = type(r_inputs)(
        entry=entry,
        source_revision=r_inputs.source_revision,
        facts=r_inputs.facts,
        prompts=r_inputs.prompts,
        out_dir=r_inputs.out_dir,
        facts_path=r_inputs.facts_path,
        candidates_root=hosted.candidates,
        provider_calls=1,
        invocation=r_inputs.invocation,
    )
    seal_candidate(shared)

    assert digest_tree(hosted.bundle().parent) == lane_l_before
    assert ready_revision(hosted.candidates, REPOSITORY, LANE_L) is None
    rows = {row.lane: row for row in portfolio_status(hosted.candidates)}
    assert rows[LANE_R].status == "ACCEPTED" and rows[LANE_L].status == "ACCEPTED"


def hosted_entry(hosted: Hosted) -> Any:
    from repo_presenter.core.registry.loader import load_registry, require_listed

    return require_listed(load_registry(hosted.registry), REPOSITORY)


def test_a_failing_lane_l_run_leaves_lane_r_s_record_exactly_as_it_was(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repo_presenter.core.state.schema import RepositoryRecord

    with GitStateBackend(remote=str(hosted.remote), lane="R") as backend:
        saved = backend.save(
            REPOSITORY,
            RepositoryRecord(
                repository=REPOSITORY,
                provider_repository_id=7,
                state="READY_FOR_PROPOSAL",
            ),
            None,
        )
        assert saved.outcome == "saved"
    before = hosted.record("R")
    Provider(monkeypatch, default=accept_reply())
    monkeypatch.setattr(
        lane_l_run,
        "review_correction",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    digest = hosted.facts("fail")
    with pytest.raises(RuntimeError, match="boom"):
        hosted.lane_l("fail", digest)
    assert hosted.record("R") == before
    after = hosted.record("L")
    assert after is not None and after.lease is None


# --- 5. the reviewer gates the seal -----------------------------------------------------------------------


def model_verdict(verdict: str, *findings: Finding) -> ReviewVerdict:
    """A verdict as the reviewer returns one after a model review (the fold decides ACCEPT/REJECT)."""
    return ReviewVerdict.folded(
        findings,
        model_verdict=verdict,
        prompt_version="16",
        model_served="qwen3-next",
        request_sha256="a" * 64,
        reply_sha256="b" * 64,
    )


def llm_finding() -> Finding:
    return Finding(
        rule="llm:factuality",
        source="llm",
        message="the opening states a capability no fact supports",
        claim_kind="unsupported_claim",
        finding_id="F01",
        section_id="opening",
        causal_stage="S6",
        criterion="factuality",
        quote="A plain description of the widget library, in the maintainers' own words.",
    )


def test_a_model_reject_blocks_the_seal_and_names_what_would_unblock_it(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reviewer's veto is final for Lane L as for Lane R: a REJECT seals nothing, in either
    lane, and the recorded failure names the finding and what would clear it. The review is stubbed
    at its boundary (the verdict is the reviewer's own; its contract is tested in readme/review)."""
    monkeypatch.setattr(
        lane_l_run,
        "review_correction",
        lambda **kwargs: model_verdict("REJECT_FACTUAL", llm_finding()),
    )
    assert hosted.lane_l("rej", hosted.facts("rej")) == 1

    assert not (
        hosted.candidates / "candidates" / SLUG
    ).exists()  # nothing sealed in either lane
    record = hosted.record("L")
    assert (
        record is not None
        and record.state == "FAILED_INTERNAL"
        and record.failure is not None
    )
    assert "Lane L: independent review returned REJECT" in record.failure.detail
    assert "F01 [unsupported_claim] in opening blocks until" in record.failure.detail
    assert "nothing sealed" in record.failure.detail
    assert hosted.record("R") is None


def test_a_deterministic_only_verdict_never_seals_a_lane_l_candidate(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        lane_l_run, "review_correction", lambda **kwargs: ReviewVerdict.folded(())
    )
    assert hosted.lane_l("det", hosted.facts("det")) == 1
    record = hosted.record("L")
    assert record is not None and record.failure is not None
    assert "no LLM review of this candidate was made" in record.failure.detail
    assert not (hosted.candidates / "candidates" / SLUG).exists()


def test_a_reviewer_outage_is_a_retryable_failure_and_seals_nothing(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    def outage(**kwargs: Any) -> ReviewVerdict:
        raise ReviewUnavailable(
            "the reviewer could not be reached (connection reset)", ["connection reset"]
        )

    real_review = lane_l_run.review_correction
    monkeypatch.setattr(lane_l_run, "review_correction", outage)
    assert hosted.lane_l("out", hosted.facts("out")) == 1

    record = hosted.record("L")
    assert record is not None and record.failure is not None
    assert record.failure.classification == "transient"
    assert (
        "retryable" in record.failure.detail
        and "nothing was sealed" in record.failure.detail
    )
    assert "connection reset" in record.failure.detail
    assert not (hosted.candidates / "candidates" / SLUG).exists()
    assert hosted.record("R") is None

    # The retry is a new transaction that succeeds: nothing was left half-done.
    monkeypatch.setattr(lane_l_run, "review_correction", real_review)
    Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("out2", hosted.facts("out2")) == 0
    assert hosted.manifest()["state"] == "ACCEPTED"


def test_a_provider_that_never_returns_a_usable_review_is_the_same_retryable_failure(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real review path, not a stub: a gateway whose every reply is unusable (not even JSON)
    is no review; it is ReviewUnavailable, recorded as transient, and nothing is sealed."""
    garbage = _completion({})
    garbage.choices[0].message.content = "this is not a review"
    provider = Provider(monkeypatch, default=garbage)
    assert hosted.lane_l("garbage", hosted.facts("garbage")) == 1

    assert provider.calls >= 1
    record = hosted.record("L")
    assert record is not None and record.failure is not None
    assert (
        record.failure.classification == "transient"
        and "retryable" in record.failure.detail
    )
    assert not (hosted.candidates / "candidates" / SLUG).exists()


FAILING_EXAMPLE_README = DEFECTIVE_README.replace(
    "docs/Usage.md", "docs/usage.md"
).replace(
    "import widget\nwidget.render()\n", "import widget\nwidget.does_not_exist()\n"
)


def test_a_defect_the_engine_may_not_repair_is_refused_before_the_model_is_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = Hosted(tmp_path, monkeypatch, FAILING_EXAMPLE_README)
    provider = Provider(monkeypatch)  # a call would raise
    assert hosted.lane_l("bad", hosted.facts("bad")) == 1

    assert provider.calls == 0
    record = hosted.record("L")
    assert record is not None and record.failure is not None
    detail = record.failure.detail
    assert "lane_l_unrepaired_defect" in detail
    assert "Lane R is the recommended lane" in detail
    assert "failing_example" in detail
    assert not (hosted.candidates / "candidates" / SLUG).exists()


# --- 6. the CLI -----------------------------------------------------------------------------------------------


def test_lane_r_is_the_default_lane_and_an_unknown_lane_is_refused(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def spy(lane: str, **kwargs: Any) -> None:
        seen.append(lane)
        raise present.PresentFailure("stop here")

    monkeypatch.setattr(present, "_lane_and_seal", spy)
    digest = hosted.facts("cli")
    assert hosted.stage("cli", None, digest) == 1
    assert hosted.stage("cli", "L", digest) == 1
    assert seen == ["R", "L"]
    with pytest.raises(SystemExit):
        main(hosted.args("cascade", "cli", lane="X"))


def test_the_lane_l_cascade_stage_runs_no_repository_code_and_builds_no_facts(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lane L runs in the credentialed job on the validated facts only: it never builds facts, and
    it reads the clone, never executes it."""
    digest = hosted.facts("iso3")

    def never(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "the credentialed stage must not build facts or run examples"
        )

    monkeypatch.setattr(present, "build_lane_l_facts", never)
    from repo_presenter.extractors.platforms import python as python_platform

    monkeypatch.setattr(python_platform, "verify_python_examples", never)
    Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("iso3", digest) == 0


def test_a_tampered_facts_file_is_refused_before_lane_l_does_anything(
    hosted: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted.facts("tamper")
    facts = hosted.root / "handoff-tamper" / "facts.json"
    payload = json.loads(facts.read_text(encoding="utf-8"))
    payload["facts"][0]["value"] += " (edited)"
    facts.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    provider = Provider(monkeypatch)
    assert hosted.lane_l("tamper") == 1
    assert provider.calls == 0
    record = hosted.record("L")
    assert record is not None and record.failure is not None
    assert "FactsHandoffError" in record.failure.detail
    assert not (hosted.candidates / "candidates" / SLUG).exists()
