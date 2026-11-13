"""Re-run each monitored issue's recorded reproduction against an upstream checkout (owner ruling
R39), and classify the captured output into the three re-detection outcomes ``issues/close.py``
already defines.

Two halves, split along the same trust boundary as ``present.yml``'s facts/present jobs:

* :func:`run_reproductions` (``python -m repo_presenter.issues.reproduce``) runs in the hosted
  ``reproduce`` job, which executes the upstream repository's own code (``npm install``, its
  build, the issue's script) and therefore holds NO secret and a read-only token. It records
  only raw observations: each command's exit code and output, bounded in size. It decides
  nothing.
* :func:`classify` runs in the trusted ``maintain`` job (no upstream code), on that artifact read
  as hostile input (:func:`load_checks` validates it). It applies the committed predicates from
  ``data/issue_reproductions/`` and returns a :class:`repo_presenter.core.facts.Fact` -- the
  same shape discovery and ``close.redetect`` already use: ``CONTRADICTED`` when the issue's own
  "actual result" is still observed, ``SUPPORTED`` when its "expected result" is positively
  observed, and NO fact (``redetect`` -> ``NOT_VERIFIABLE``) for anything else -- a failed
  build, a timeout, or output neither predicate recognises. Absence of the defect's symptom is
  never by itself a fix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.issues.pilot import (
    Reproduction,
    ReproductionSet,
    load_reproductions,
)

CHECKS_SCHEMA_VERSION = 1
MAX_OUTPUT_CHARS = 16_000
PREPARE_TIMEOUT_SECONDS = 900
SCRIPT_TIMEOUT_SECONDS = 120
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_CONSUMER_COPY = ("package.json", "dist")

Runner = Callable[[Sequence[str], Path, float], "tuple[int | None, str]"]


def _default_runner(argv: Sequence[str], cwd: Path, timeout: float) -> tuple[int | None, str]:
    """``(exit code, combined stdout+stderr)``; exit code ``None`` on a timeout or a missing
    executable (the output then says which)."""
    try:
        done = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout:.0f}s: {' '.join(argv)}"
    except OSError as exc:
        return None, f"could not start {argv[0]}: {exc}"
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def _bounded(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text, False
    return text[-MAX_OUTPUT_CHARS:], True


def _script_name(reproduction: Reproduction) -> str:
    return f"repo-presenter-repro-{reproduction.issue_number}.js"


def run_reproductions(
    repository: str,
    checkout: Path,
    *,
    reproductions: ReproductionSet | None = None,
    runner: Runner = _default_runner,
    revision: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Prepare ``checkout`` once and run every recorded reproduction in it. Raw observations only."""
    spec = reproductions or load_reproductions(repository)
    checkout = checkout.resolve()
    if revision is None:
        code, out = runner(["git", "rev-parse", "HEAD"], checkout, 60)
        revision = out.strip() if code == 0 else ""
    prepare: list[dict[str, Any]] = []
    prepared = True
    for argv in spec.prepare:
        code, out = runner(argv, checkout, PREPARE_TIMEOUT_SECONDS)
        tail, truncated = _bounded(out)
        prepare.append({"argv": list(argv), "exit_code": code, "output": tail, "truncated": truncated})
        if code != 0:
            prepared = False
            break
    versions = {}
    for tool in ("node", "npm"):
        code, out = runner([tool, "--version"], checkout, 60)
        versions[tool] = out.strip() if code == 0 else None
    results: list[dict[str, Any]] = []
    for reproduction in spec.reproductions:
        row: dict[str, Any] = {
            "issue_number": reproduction.issue_number,
            "defect_fingerprint": reproduction.defect_fingerprint,
            "check_id": reproduction.check_id,
            "ran": False,
            "exit_code": None,
            "output": "",
            "truncated": False,
            "setup": [],
        }
        if not prepared:
            row["note"] = "not run: the checkout could not be prepared"
            results.append(row)
            continue
        where = checkout
        if reproduction.environment == "consumer_omit_dev":
            # The issue's own consumer steps: only package.json and the built dist, production
            # dependencies only (``npm install --omit=dev``).
            where = checkout.parent / f"{checkout.name}-consumer-{reproduction.issue_number}"
            shutil.rmtree(where, ignore_errors=True)
            where.mkdir(parents=True)
            missing = [n for n in _CONSUMER_COPY if not (checkout / n).exists()]
            if missing:
                row["note"] = f"not run: the checkout has no {', '.join(missing)}"
                results.append(row)
                continue
            shutil.copy2(checkout / "package.json", where / "package.json")
            shutil.copytree(checkout / "dist", where / "dist")
            argv = ["npm", "install", "--omit=dev", "--no-audit", "--no-fund"]
            code, out = runner(argv, where, PREPARE_TIMEOUT_SECONDS)
            tail, truncated = _bounded(out)
            row["setup"].append({"argv": argv, "exit_code": code, "output": tail, "truncated": truncated})
            if code != 0:
                row["note"] = "not run: the consumer install failed"
                results.append(row)
                continue
        script = where / _script_name(reproduction)
        script.write_text(reproduction.script, encoding="utf-8")
        code, out = runner(["node", script.name], where, SCRIPT_TIMEOUT_SECONDS)
        output, truncated = _bounded(out)
        row.update({"ran": True, "exit_code": code, "output": output, "truncated": truncated})
        results.append(row)
    return {
        "schema_version": CHECKS_SCHEMA_VERSION,
        "repository": repository,
        "revision": revision,
        "ran_at": (now or (lambda: datetime.now(UTC)))().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toolchain": versions,
        "prepared": prepared,
        "prepare": prepare,
        "results": results,
    }


class ChecksError(ValueError):
    """The checks artifact handed over by the sandbox job is not trustworthy as a whole."""


@dataclass(frozen=True)
class CheckObservation:
    issue_number: int
    defect_fingerprint: str
    check_id: str
    ran: bool
    exit_code: int | None
    output: str
    truncated: bool
    note: str | None

    @property
    def output_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.output.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Checks:
    repository: str
    revision: str
    ran_at: str
    toolchain: dict[str, str | None]
    prepared: bool
    observations: dict[str, CheckObservation]


def load_checks(
    payload: Any, *, repository: str, reproductions: ReproductionSet, expected_revision: str | None
) -> Checks:
    """Validate the sandbox's artifact as hostile input: right repository, a 40-hex revision equal
    to the one the trusted job resolved itself, only fingerprints the committed reproductions
    name, bounded sizes, typed fields. Any doubt rejects the whole artifact."""

    def bad(why: str) -> ChecksError:
        return ChecksError(f"checks artifact refused: {why}")

    if not isinstance(payload, dict) or payload.get("schema_version") != CHECKS_SCHEMA_VERSION:
        raise bad("no schema_version 1 object")
    if payload.get("repository") != repository:
        raise bad(f"it names {payload.get('repository')!r}, not {repository}")
    revision = payload.get("revision")
    if not isinstance(revision, str) or not _REVISION.match(revision):
        raise bad("revision is not a 40-hex commit")
    if expected_revision is not None and revision != expected_revision:
        raise bad(f"revision {revision} is not the upstream head {expected_revision} resolved here")
    toolchain = payload.get("toolchain")
    if not isinstance(toolchain, dict) or not all(
        isinstance(k, str) and (v is None or (isinstance(v, str) and len(v) < 100))
        for k, v in toolchain.items()
    ):
        raise bad("toolchain is malformed")
    if not isinstance(payload.get("prepared"), bool):
        raise bad("prepared is not a boolean")
    ran_at = payload.get("ran_at")
    if not isinstance(ran_at, str) or len(ran_at) > 40:
        raise bad("ran_at is malformed")
    known = reproductions.by_fingerprint()
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise bad("results is not a list")
    observations: dict[str, CheckObservation] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise bad("a result is not an object")
        fp = row.get("defect_fingerprint")
        spec = known.get(fp) if isinstance(fp, str) else None
        if spec is None or fp in observations:
            raise bad(f"unknown or repeated fingerprint {fp!r}")
        if row.get("issue_number") != spec.issue_number or row.get("check_id") != spec.check_id:
            raise bad(f"{fp}: issue number or check id differs from the committed reproduction")
        output = row.get("output")
        exit_code = row.get("exit_code")
        note = row.get("note")
        if (
            not isinstance(row.get("ran"), bool)
            or not isinstance(output, str)
            or len(output) > MAX_OUTPUT_CHARS
            or not isinstance(row.get("truncated"), bool)
            or not (exit_code is None or (isinstance(exit_code, int) and not isinstance(exit_code, bool)))
            or not (note is None or (isinstance(note, str) and len(note) < 500))
        ):
            raise bad(f"{fp}: malformed result fields")
        observations[fp] = CheckObservation(
            issue_number=spec.issue_number,
            defect_fingerprint=fp,
            check_id=spec.check_id,
            ran=row["ran"],
            exit_code=exit_code,
            output=output,
            truncated=row["truncated"],
            note=note,
        )
    return Checks(
        repository=repository,
        revision=revision,
        ran_at=ran_at,
        toolchain=dict(toolchain),
        prepared=payload["prepared"],
        observations=observations,
    )


def classify(reproduction: Reproduction, observation: CheckObservation | None) -> Fact | None:
    """The re-detection fact for one reproduction, decided only from the committed predicates.

    ``CONTRADICTED`` (the defect still reproduces) when any ``reproduces_if_any`` pattern is in
    the output; ``SUPPORTED`` (verified resolved) only when the script ran to exit 0, every
    ``resolved_if_all`` pattern is present, the output is empty where the reproduction says a fix
    prints nothing, and no defect pattern appears; ``None`` (NOT_VERIFIABLE) otherwise."""
    if observation is None or not observation.ran or observation.exit_code is None:
        return None
    output = observation.output
    evidence = tuple(Evidence(path=p, detail=d) for p, d in reproduction.evidence)
    attrs = {"issue": str(reproduction.issue_number), "output_digest": observation.output_digest}
    if any(re.search(p, output) for p in reproduction.reproduces_if_any):
        return Fact(
            id=reproduction.check_id, kind="example", polarity="CONTRADICTED", evidence=evidence,
            value=f"issue #{reproduction.issue_number}: the recorded reproduction still shows the defect",
            attributes=attrs,
        )
    if observation.truncated or observation.exit_code != 0:
        return None
    if reproduction.resolved_if_output_empty and output.strip():
        return None
    if not all(re.search(p, output) for p in reproduction.resolved_if_all):
        return None
    return Fact(
        id=reproduction.check_id, kind="example", polarity="SUPPORTED", evidence=evidence,
        value=f"issue #{reproduction.issue_number}: the recorded reproduction shows the expected result",
        attributes=attrs,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", required=True)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    from repo_presenter.issues.pilot import require_pilot

    require_pilot(args.repository)
    document = run_reproductions(args.repository, args.checkout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    for row in document["results"]:
        print(f"#{row['issue_number']} {row['check_id']}: ran={row['ran']} exit={row['exit_code']}")
    print(f"revision {document['revision']} prepared={document['prepared']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
