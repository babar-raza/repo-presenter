"""R39 re-verification: the sandbox records raw observations only; the trusted side validates them
as hostile input and classifies them with the committed predicates into close.redetect's three
outcomes -- and only a positive "expected result" is ever VERIFIED_RESOLVED."""

from __future__ import annotations

import copy
import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from repo_presenter.issues.close import redetect
from repo_presenter.issues.monitor import Issue, handoff_for_issue
from repo_presenter.issues.pilot import load_reproductions
from repo_presenter.issues.reproduce import (
    MAX_OUTPUT_CHARS,
    CheckObservation,
    ChecksError,
    classify,
    load_checks,
    run_reproductions,
)

PILOT = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
REV = "66cb26df3b031f0bf6976d4e88dc89721983afa4"
SPEC = load_reproductions(PILOT)
BY_ISSUE = {r.issue_number: r for r in SPEC.reproductions}

#: The "Actual result" blocks of issues #4-#8, verbatim, and what each would print once fixed
#: (the issue's own "Expected" section).
ACTUAL = {
    4: "STL_Node control points: 0 polygons: 0\n",
    5: "TypeError: rotation[0].eulerAngles is not a function\nTypeError: rotation[0].eulerAngles is not a function\n",
    6: "[ '', 'o Node_0', 'v 10.000000 20.000000 30.000000' ]\nUnsupported format: FbxFormat\nMesh control points: 0\n",
    7: "Error: Cannot find module 'adm-zip'\n",
    8: "solid Scene\n  facet normal 0 0 0\n    outer loop\n      vertex 0 1 2\n    endloop\n  endfacet\nendsolid Scene\n\nbinary STL size: 50 bytes\n",
}
EXPECTED = {
    4: "Tri control points: 3 polygons: 1\n",
    5: "",
    6: "[ '', 'FBXHeaderExtension:  {', '...' ]\nMesh control points: 3\n",
    7: "",
    8: "solid Scene\n  facet normal 0 0 1\n    outer loop\n      vertex 10 20 30\n      vertex 11 20 30\n      vertex 10 21 30\n    endloop\n  endfacet\nendsolid Scene\n\nbinary STL size: 134 bytes\n",
}


def _obs(n: int, output: str, exit_code: int | None = 0, *, ran: bool = True, truncated: bool = False) -> CheckObservation:
    r = BY_ISSUE[n]
    return CheckObservation(n, r.defect_fingerprint, r.check_id, ran, exit_code, output, truncated, None)


def _outcome(n: int, observation: CheckObservation | None) -> str:
    issue = Issue(n, f"https://github.com/{PILOT}/issues/{n}", "t", "b", "repository-presenter[bot]", "open", None, "")
    handoff = handoff_for_issue(PILOT, BY_ISSUE[n].defect_fingerprint, issue, BY_ISSUE[n])
    fact = classify(BY_ISSUE[n], observation)
    return redetect(handoff, {fact.id: fact} if fact else {})


@pytest.mark.parametrize("n", [4, 5, 6, 7, 8])
def test_each_issues_own_actual_result_still_reproduces(n: int) -> None:
    assert _outcome(n, _obs(n, ACTUAL[n])) == "STILL_REPRODUCES"


@pytest.mark.parametrize("n", [4, 5, 6, 7, 8])
def test_each_issues_own_expected_result_is_verified_resolved(n: int) -> None:
    assert _outcome(n, _obs(n, EXPECTED[n])) == "VERIFIED_RESOLVED"


@pytest.mark.parametrize("n", [4, 5, 6, 7, 8])
def test_anything_else_is_not_verifiable_never_resolved(n: int) -> None:
    assert _outcome(n, None) == "NOT_VERIFIABLE"  # no observation at all
    assert _outcome(n, _obs(n, "", None, ran=False)) == "NOT_VERIFIABLE"  # not run
    assert _outcome(n, _obs(n, "Error: Cannot find module './dist/aspose/threed'\n", 1)) == "NOT_VERIFIABLE"
    assert _outcome(n, _obs(n, EXPECTED[n], 1)) == "NOT_VERIFIABLE"  # expected text but a crash
    assert _outcome(n, _obs(n, EXPECTED[n], truncated=True)) == "NOT_VERIFIABLE"
    assert _outcome(n, _obs(n, "something unrelated\n")) == "NOT_VERIFIABLE"


def test_a_partial_fix_still_reproduces() -> None:
    # #6 has three symptoms; fixing the open path alone is not a fix of the issue.
    partial = "[ '', 'o Node_0', 'v 10' ]\nUnsupported format: FbxFormat\nMesh control points: 3\n"
    assert _outcome(6, _obs(6, partial)) == "STILL_REPRODUCES"


class FakeRunner:
    def __init__(self, outputs: dict[str, tuple[int | None, str]]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, argv: Sequence[str], cwd: Path, timeout: float) -> tuple[int | None, str]:
        self.calls.append((tuple(argv), cwd))
        key = " ".join(argv)
        for pattern, value in self.outputs.items():
            if re.fullmatch(pattern, key):
                return value
        return 0, ""


def _checkout(tmp_path: Path) -> Path:
    root = tmp_path / "up"
    (root / "dist").mkdir(parents=True)
    (root / "package.json").write_text("{}", "utf-8")
    return root


def test_the_sandbox_runs_every_script_and_records_raw_output_only(tmp_path: Path) -> None:
    runner = FakeRunner({
        r"node repo-presenter-repro-(\d+)\.js": (0, "out\n"),
        r"node --version": (0, "v22.23.4\n"),
    })
    doc = run_reproductions(PILOT, _checkout(tmp_path), runner=runner, revision=REV)
    assert doc["prepared"] is True and doc["revision"] == REV
    assert [r["issue_number"] for r in doc["results"]] == [4, 5, 6, 7, 8]
    assert all(r["ran"] and r["output"] == "out\n" for r in doc["results"])
    assert "outcome" not in str(doc) and "VERIFIED" not in str(doc)  # it decides nothing
    consumer = [c for c in runner.calls if c[0][:2] == ("npm", "install") and "--omit=dev" in c[0]]
    assert len(consumer) == 1 and consumer[0][1].name.endswith("consumer-7")
    assert (consumer[0][1] / "dist").is_dir() and (consumer[0][1] / "repo-presenter-repro-7.js").exists()


def test_a_failed_build_runs_nothing(tmp_path: Path) -> None:
    runner = FakeRunner({r"npm run build": (2, "tsc: error\n")})
    doc = run_reproductions(PILOT, _checkout(tmp_path), runner=runner, revision=REV)
    assert doc["prepared"] is False
    assert not any(r["ran"] for r in doc["results"])
    assert not any(c[0][0] == "node" and c[0][1] != "--version" for c in runner.calls)


def test_output_is_bounded(tmp_path: Path) -> None:
    runner = FakeRunner({r"node repo-presenter-repro-4\.js": (0, "x" * (MAX_OUTPUT_CHARS + 50))})
    doc = run_reproductions(PILOT, _checkout(tmp_path), runner=runner, revision=REV)
    row = doc["results"][0]
    assert row["truncated"] is True and len(row["output"]) == MAX_OUTPUT_CHARS


def _payload(tmp_path: Path) -> dict:
    return run_reproductions(PILOT, _checkout(tmp_path), runner=FakeRunner({}), revision=REV)


def test_valid_checks_load(tmp_path: Path) -> None:
    checks = load_checks(_payload(tmp_path), repository=PILOT, reproductions=SPEC, expected_revision=REV)
    assert set(checks.observations) == {r.defect_fingerprint for r in SPEC.reproductions}


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda d: d.update(repository="x/y"), "names"),
        (lambda d: d.update(revision="f" * 40), "not the upstream head"),
        (lambda d: d.update(revision="HEAD"), "40-hex"),
        (lambda d: d["results"][0].update(defect_fingerprint="sha256:" + "0" * 64), "unknown"),
        (lambda d: d["results"].append(copy.deepcopy(d["results"][0])), "repeated"),
        (lambda d: d["results"][0].update(issue_number=99), "differs"),
        (lambda d: d["results"][0].update(output="x" * (MAX_OUTPUT_CHARS + 1)), "malformed"),
        (lambda d: d["results"][0].update(exit_code="0"), "malformed"),
        (lambda d: d.update(schema_version=2), "schema_version"),
    ],
)
def test_hostile_checks_are_refused_whole(tmp_path: Path, mutate, fragment: str) -> None:
    payload = _payload(tmp_path)
    mutate(payload)
    with pytest.raises(ChecksError, match=fragment):
        load_checks(payload, repository=PILOT, reproductions=SPEC, expected_revision=REV)
