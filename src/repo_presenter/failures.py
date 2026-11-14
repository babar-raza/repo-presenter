"""Failure classification of every hosted present run (BL-084; owner, 2026-11-13: "Every failure
must be categorised and reviewed deeply to find appropriate solution and that solution must be
integrated to pipeline for repeatability").

Not a new subsystem: it extends the present job's failure path and the durable state (R27). Every
run of either lane ends with one record of what blocked it, built from data the run already has and
with zero provider calls:

* ``present.py`` writes ``<workdir>/failures/<lane>.json`` (:func:`write_local_record`) from the
  blocking findings the review returned, the blocking checks of ``validation.json``, the repair
  ledger (``repairs.json``) and the transaction's failure;
* the present job's ``Classify this run's failures`` step (:func:`main` ``publish``) completes it
  with the run's identity, code fingerprint and per-class code scope, synthesises a job-error
  record for a lane that left none (a facts failure, a crash), pushes it to the cell's state ref
  ``refs/repository-presenter-state/failures/<owner>__<name>[@lane-l]`` -- one ref per cell, one
  commit per run, the same compare-and-swap plumbing as the provider-spend ledger
  (``core.state.git_backend.GitJsonRef``) -- and writes a table to the job summary;
* ``pareto`` reads the latest record of every cell and prints the portfolio Pareto (supervisor
  tick, cohort planner summary);
* the cohort planner holds a cell whose last failure lies entirely in classes whose code scope is
  unchanged (:func:`unchanged_classes`), so a known failure is not paid for again;
* ``backfill`` rebuilds records from the logs of past runs (``gh run view <id> --log``), since run
  artifacts are not readable from a session.

A finding's class signature is ``<rule>|<origin kind>|<sub-rule>``: the check that raised it, what
printed the quoted text (the renderer from a fact, an authored unit, an inherited unit, a planned
example, a Lane L correction, or a job error), and the rule's own sub-shape (a claim
contradiction's member-kind or version reading, BC-17's coverage tag, a Lane L detector). The
origin is resolved on positive evidence only: a unit id the check names, the repair ledger's
"printed by the renderer from fact X", a unit, inherited unit or planned example whose text holds
the quote, or ``readme.repair.loop.renderer_printed_facts``; anything else is ``unresolved``, never
guessed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
FAILURE_REF_PREFIX = "refs/repository-presenter-state/failures"
LOCAL_DIRNAME = "failures"
#: The blocking findings of a rejected candidate, written beside the lane's outputs by present.py.
BLOCKING_FILENAME = "blocking_findings.json"
LANE_OUT_DIRS = {"R": "cascade", "L": "lane-l"}
HISTORY_LIMIT = 20
_QUOTE_LIMIT = 300
_TEXT_LIMIT = 500

ORIGIN_RENDERER = "renderer_fact"
ORIGIN_AUTHORED = "authored_unit"
ORIGIN_INHERITED = "inherited_unit"
ORIGIN_EXAMPLE = "planned_example"
ORIGIN_CORRECTION = "lane_l_correction"
ORIGIN_JOB = "job_error"
ORIGIN_UNRESOLVED = "unresolved"

RULE_JOB = "job_error"

#: A unit id a check names in its own text (BC-05/BC-07/BC-17 failures, repair reasons).
_UNIT_ID = re.compile(r"\binherited_unit:\d{3}(?:\.\d{3})?\.[a-z_]+")


# --------------------------------------------------------------------------------------- shapes


def _squash(text: str) -> str:
    return " ".join(str(text).split())


def printed_key(text: str) -> str:
    """The form a README quote is matched against a unit in: whitespace squashed, code-span
    backticks dropped (the renderer code-spans identifiers of authored text), as
    ``readme.repair.loop._printed`` matches them."""
    return _squash(str(text).replace("`", ""))


def _fragments(quote: str) -> list[str]:
    """``quote`` and its substantive pieces: each line, and each table cell or bullet body of
    12 characters or more (a table row is printed from one description, never from the pipes)."""
    pieces = [printed_key(quote)]
    for line in str(quote).splitlines():
        line = line.strip()
        if not line:
            continue
        pieces.append(printed_key(line))
        body = re.sub(r"^([-*+]|\d+\.)\s+", "", line)
        pieces.append(printed_key(body))
        for cell in body.split("|"):
            pieces.append(printed_key(cell))
    seen: list[str] = []
    for piece in pieces:
        if len(piece) >= 12 and piece not in seen:
            seen.append(piece)
    return seen


def shape(text: str, words: int = 4) -> str:
    """A text's stable shape: code spans, quotes, ids and numbers replaced, its first ``words``
    words joined. Two findings that differ only in the names they quote share a shape."""
    value = re.sub(r"`[^`]*`", " code ", str(text))
    value = re.sub(r"(?<![A-Za-z])'[^']*'(?![A-Za-z])|\"[^\"]*\"", " q ", value)
    value = re.sub(r"\b[a-z_]+:[\w.:/-]+", " id ", value)
    value = re.sub(r"\d+(?:\.\d+)*", " n ", value)
    tokens = re.findall(r"[a-z_]+", value.lower())
    return "_".join(tokens[:words]) or "-"


#: (rule pattern, text pattern, sub-rule; a ``\\1`` in it names the text pattern's first group).
_SUB_RULES: tuple[tuple[str, str, str], ...] = (
    (r"^claim_contradiction$", r"\bcalls `[^`]+` an? \w+", "member_kind"),
    (r"^claim_contradiction$", r"\bnames `[^`]+` as an? \w+ of\b|, a member of `", "member_owner"),
    (r"^claim_contradiction$", r"\bnames `[^`]+`, which no fact states\b", "unknown_member"),
    (r"^claim_contradiction$", r"\bis thrown, but implementation:never_thrown\b", "never_thrown"),
    (r"^claim_contradiction$", r"\bthrows a not-implemented exception, but its body\b", "not_implemented_but_returns"),
    (r"^claim_contradiction$", r"\breachable only through a stub\b", "stub_format"),
    (r"^claim_contradiction$", r"\bdescribes `[^`]+`.* as (?:working|usable)\b.*\bonly throws\b", "stub_described_working"),
    (r"^claim_contradiction$", r"\bderives from `", "base_class"),
    (r"^claim_contradiction$", r"\bsamples use the published package\b", "samples_reference"),
    (r"^claim_contradiction$", r"\bshown at version\b|\bversion\b", "version"),
    (r"^BC-07$", r"\binternal evidence or analysis wording\b", "internal_wording"),
    (r"^BC-05$", r"^section fit\b", "section_fit"),
    (r"^BC-05$", r"\bSUPERSEDE_REDUNDANT\b", "superseded_unstated"),
    (r"^BC-07$", r"\bnot in title case\b", "title_case"),
    (r"^BC-07$", r"\bends with a colon\b", "trailing_colon"),
    (r"^BC-02$", r"\bwhose build no run proved\b", "unproven_build"),
    (r"^BC-17$", r"\(([a-z_]+)\)", r"\1"),
    (r"^BC-18$", r"\bconfirmed ([a-z]+) claim\b", r"\1_claim"),
    (r"^live_readme_loss$", r"disposition: ([a-z]+(?: [a-z]+)?)\b", r"\1"),
    (r"^lane_l_unrepaired_defect$", r"^([a-z_]+) found a defect\b", r"\1"),
)


def sub_rule(rule: str, text: str, *, section_id: str = "") -> str:
    """The rule's own sub-shape of ``text`` (deterministic; :data:`_SUB_RULES`, then the text's
    :func:`shape`). A reviewer (LLM) finding's sub-rule is the section it was raised in."""
    if rule.startswith("llm:"):
        return section_id or "-"
    for rule_pattern, text_pattern, name in _SUB_RULES:
        if not re.search(rule_pattern, rule):
            continue
        match = re.search(text_pattern, text)
        if match:
            value = match.expand(name) if "\\" in name else name
            return value.replace(" ", "_").lower()
    return shape(re.sub(r"^line \d+ \([A-Z]+\):\s*", "", str(text)))


_README_TEXT = re.compile(r"The README text '(?P<quote>.+?)' is false", re.S)


def quote_in(text: str) -> str:
    """The README text a check's own detail quotes (BC-18's register rows), when it has one."""
    match = _README_TEXT.search(str(text))
    return match.group("quote") if match else ""


def printed_where(quote: str) -> str:
    """Where an unattributed quote sits, read from its own shape: an API table row or member
    bullet names its symbol; a fenced line is code. Location only, never an origin claim."""
    first = str(quote).strip().splitlines()[0] if str(quote).strip() else ""
    row = re.match(r"^\|\s*`([^`]+)`\s*\|", first)
    if row:
        return f"api_table_row:{row.group(1)}"
    bullet = re.match(r"^[-*]\s+`([^`]+)`\s*:", first)
    if bullet:
        return f"member_bullet:{bullet.group(1)}"
    if re.search(r"[;{}()]\s*$", first) and "(" in first:
        return "code_line"
    return ""


def job_error_kind(detail: str) -> tuple[str, str]:
    """``(exception type, sub-rule)`` of a transaction failure detail: ``JobError: section_authoring:
    output truncated ...`` -> ``("JobError", "section_authoring_output_truncated_at")``; a
    bracketed code (``NoOpProofError: [LEDGER_NO_RECORDS] ...``) is the sub-rule itself."""
    text = re.sub(r"^attempt under version set [0-9a-f]+:\s*", "", str(detail).strip())
    match = re.match(r"([A-Z][A-Za-z]+(?:Error|Failure|Unavailable|Exception))\s*:\s*(.*)", text, re.S)
    kind, rest = (match.group(1), match.group(2)) if match else ("unknown", text)
    code = re.match(r"\[([A-Z_]+)\]", rest)
    if code:
        return kind, code.group(1)
    head = re.match(r"([a-z][a-z0-9_]+):\s*(.*)", rest, re.S)
    if head:
        return kind, f"{head.group(1)}_{shape(head.group(2), 3)}"
    return kind, shape(rest)


def is_transient(detail: str) -> bool:
    """Whether a failure is one the same run can pass next time (present.py's own retryable
    wording): a re-run is never held for it."""
    lowered = str(detail).lower()
    return (
        "(retryable:" in lowered
        or "bundle not durably published" in lowered
        or "outputrejectederror" in lowered
        or "reviewunavailable" in lowered
    )


# --------------------------------------------------------------------------------------- origins


@dataclass
class OriginIndex:
    """What printed which text in one lane's outputs: authored units (``section.slot``), inherited
    units and planned examples (fact ids), the repair ledger's renderer-printed findings, Lane L's
    applied corrections, and the facts (for ``renderer_printed_facts``)."""

    authored: list[tuple[str, str]] = field(default_factory=list)
    inherited: list[tuple[str, str]] = field(default_factory=list)
    examples: list[tuple[str, str]] = field(default_factory=list)
    renderer: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    corrections: list[tuple[str, str]] = field(default_factory=list)
    facts: Any = None

    def add_renderer(self, quote: str, fact_ids: Iterable[str]) -> None:
        key = printed_key(quote)
        ids = tuple(str(i) for i in fact_ids)
        if key and ids and (key, ids) not in self.renderer:
            self.renderer.append((key, ids))

    def resolve(self, *, rule: str, quote: str, text: str, unit_id: str = "", lane: str = "R") -> dict[str, str]:
        """The origin of one finding, on positive evidence only."""
        if rule == "lane_l_unrepaired_defect":
            return {"kind": ORIGIN_CORRECTION, "id": sub_rule(rule, text)}
        # Only a unit the check is ABOUT (its own unit_id field, or a detail that opens with it):
        # a unit id cited later in a detail is the evidence for the claim, not what printed it.
        opening = _UNIT_ID.match(text.strip())
        named = unit_id or (opening.group(0) if opening else "")
        if named:
            return {"kind": ORIGIN_INHERITED, "id": named}
        pieces = _fragments(quote) if quote else []
        for piece in pieces:
            for key, ids in self.renderer:
                if piece == key or piece.startswith(key) or key.startswith(piece):
                    return {"kind": ORIGIN_RENDERER, "id": ", ".join(ids)}
        for kind, table in (
            (ORIGIN_CORRECTION, self.corrections),
            (ORIGIN_AUTHORED, self.authored),
            (ORIGIN_INHERITED, self.inherited),
            (ORIGIN_EXAMPLE, self.examples),
        ):
            for piece in pieces:
                for identity, body in table:
                    if piece in body:
                        return {"kind": kind, "id": identity}
        if quote and self.facts is not None:
            try:
                from repo_presenter.readme.repair.loop import renderer_printed_facts

                ids = renderer_printed_facts(self.facts, quote)
            except Exception:  # noqa: BLE001 -- origin is evidence, never a reason to fail
                ids = []
            if ids:
                return {"kind": ORIGIN_RENDERER, "id": ", ".join(ids)}
        where = printed_where(quote)
        if lane == "L" and quote:
            # Lane L prints only the live README and its applied corrections; a quote no
            # correction holds (checked above) is the live README's own text.
            return {"kind": ORIGIN_INHERITED, "id": f"live_readme:{where}" if where else "live_readme"}
        stage = re.search(r"\((EXTRACTING|RECONCILING|PLANNING|COMPOSING|AUTHORING)\)", text)
        return {"kind": ORIGIN_UNRESOLVED, "id": where or (stage.group(1) if stage else "-")}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def origin_index(workdir: Path, lane: str) -> OriginIndex:
    """The :class:`OriginIndex` of one lane's outputs under ``workdir`` (any missing file is simply
    not evidence)."""
    index = OriginIndex()
    out_dir = workdir / LANE_OUT_DIRS.get(lane, "cascade")
    units = _read_json(out_dir / "content_units.coherent.json") or _read_json(out_dir / "content_units.json")
    for unit in (units or {}).get("units", []) if isinstance(units, dict) else []:
        if isinstance(unit, dict) and unit.get("text"):
            index.authored.append(
                (f"{unit.get('section', '?')}.{unit.get('slot', '?')}", printed_key(unit["text"]))
            )
    plan = _read_json(out_dir / "plan.json") or {}
    planned = {
        str(value)
        for key in ("quick_start_example_id", "second_quick_start_example_id", "flagship_example_id")
        if (value := plan.get(key))
    } | {str(value) for value in plan.get("additional_example_ids") or []}
    facts_path = workdir / "facts.json"
    if facts_path.is_file():
        try:
            from repo_presenter.core.facts import read_facts

            index.facts = read_facts(facts_path)
        except Exception:  # noqa: BLE001
            index.facts = None
    for fact in getattr(index.facts, "facts", ()) or ():
        if fact.kind == "inherited_unit":
            index.inherited.append((fact.id, printed_key(fact.value)))
        elif fact.kind == "example" and fact.id in planned:
            code = (fact.attributes or {}).get("code") or fact.value
            index.examples.append((fact.id, printed_key(code)))
    repairs = _read_json(out_dir / "repairs.json") or {}
    attempts = repairs.get("attempts", {}) if isinstance(repairs, dict) else {}
    for attempt in attempts.values() if isinstance(attempts, dict) else []:
        for item in (attempt or {}).get("facts_defects") or []:
            index.add_renderer(str(item.get("quote", "")), item.get("fact_ids") or ())
    corrections = _read_json(out_dir / "corrections.json") or {}
    for edit in corrections.get("edits", []) if isinstance(corrections, dict) else []:
        if isinstance(edit, dict) and edit.get("replacement"):
            index.corrections.append((str(edit.get("detector", "?")), printed_key(edit["replacement"])))
    return index


# --------------------------------------------------------------------------------------- scopes

_SRC = "src/repo_presenter"
#: The code that raises a rule's findings (BL-084 class scope, part 1).
_RULE_SCOPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (r"^claim_contradiction$", (f"{_SRC}/readme/validation/claims.py", f"{_SRC}/readme/review/independent_reviewer.py")),
    (r"^(live_readme_loss|duplicate_\w+|disposition_coverage)$", (f"{_SRC}/readme/review/independent_reviewer.py", f"{_SRC}/lane_l_review.py")),
    (r"^BC-\d+$", (f"{_SRC}/readme/validation", f"{_SRC}/readme/parity_gate.py", "data/readme_findings.json")),
    (r"^llm:", (f"{_SRC}/readme/review", "prompts")),
    (r"^lane_l_", (f"{_SRC}/readme/correction", f"{_SRC}/lane_l_review.py")),
    (rf"^{RULE_JOB}$", (f"{_SRC}/core", f"{_SRC}/present.py", "prompts", "pyproject.toml")),
)
#: The code that printed the quoted text (part 2).
_ORIGIN_SCOPES: dict[str, tuple[str, ...]] = {
    ORIGIN_RENDERER: (f"{_SRC}/readme/composition/renderer.py", f"{_SRC}/extractors", f"{_SRC}/readme/evidence"),
    ORIGIN_AUTHORED: (f"{_SRC}/readme/composition", "prompts"),
    ORIGIN_INHERITED: (f"{_SRC}/readme/reconciliation", f"{_SRC}/readme/evidence/facts/inherited.py", "prompts"),
    ORIGIN_EXAMPLE: (f"{_SRC}/extractors", f"{_SRC}/readme/composition"),
    ORIGIN_CORRECTION: (f"{_SRC}/readme/correction",),
    ORIGIN_UNRESOLVED: (
        f"{_SRC}/readme/composition", f"{_SRC}/readme/reconciliation", f"{_SRC}/readme/evidence",
        f"{_SRC}/extractors", "prompts",
    ),
    ORIGIN_JOB: (),
}
#: The lane's own driver and repair, which can fix any class (part 3).
_LANE_SCOPES = {
    "R": (f"{_SRC}/cascade.py", f"{_SRC}/readme/repair"),
    "L": (f"{_SRC}/lane_l_run.py", f"{_SRC}/lane_l.py"),
}


def class_scope_paths(rule: str, origin_kind: str, lane: str) -> tuple[str, ...] | None:
    """The code whose change can change a class's outcome: the rule's code, the origin's code and
    the lane's driver and repair loop. ``None`` for a rule this table does not know (such a class is
    never held: only a whole-code fingerprint match, the planner's ``idempotent`` skip, holds it)."""
    rule_paths = next((paths for pattern, paths in _RULE_SCOPES if re.search(pattern, rule)), None)
    if rule_paths is None:
        return None
    return tuple(sorted({*rule_paths, *_ORIGIN_SCOPES.get(origin_kind, _ORIGIN_SCOPES[ORIGIN_UNRESOLVED]), *_LANE_SCOPES.get(lane, ())}))


def scope_fingerprint(paths: Sequence[str], root: Path, revision: str = "HEAD") -> str:
    """One hash of ``paths`` at ``revision`` (``git ls-tree``, as ``core.llm.budget.code_fingerprint``
    hashes the whole code); empty when git cannot read the tree."""
    listed = subprocess.run(
        ["git", "ls-tree", "-r", revision, "--", *paths],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if listed.returncode != 0 or not listed.stdout.strip():
        return ""
    return hashlib.sha256(listed.stdout.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------- records


def _finding(
    *,
    rule: str,
    source: str,
    message: str,
    quote: str = "",
    section_id: str = "",
    label: str = "",
    unit_id: str = "",
    lane: str,
    index: OriginIndex,
) -> dict[str, Any]:
    text = message or ""
    quote = quote or quote_in(text)
    origin = index.resolve(rule=rule, quote=quote, text=text, unit_id=unit_id, lane=lane)
    sub = sub_rule(rule, text, section_id=section_id)
    return {
        "rule": rule,
        "label": label or rule,
        "source": source,
        "section_id": section_id or "",
        "sub_rule": sub,
        "origin": origin,
        "quote": str(quote)[:_QUOTE_LIMIT],
        "message": str(text)[:_TEXT_LIMIT],
        "signature": f"{rule}|{origin['kind']}|{sub}",
    }


def _repair(attempt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "label": str(attempt.get("label", "")),
        "outcome": str(attempt.get("outcome", "")),
        "stage": attempt.get("stage"),
        "section_id": attempt.get("section_id"),
        "reason": str(attempt.get("reason") or "")[:_TEXT_LIMIT],
        "facts_defects": [
            {"quote": str(item.get("quote", ""))[:_QUOTE_LIMIT], "fact_ids": list(item.get("fact_ids") or [])}
            for item in attempt.get("facts_defects") or []
        ],
    }


def classes_of(findings: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """``{signature: {findings, rule, origin_kind, sub_rule, example, origins}}``."""
    classes: dict[str, dict[str, Any]] = {}
    for finding in findings:
        item = classes.setdefault(
            finding["signature"],
            {
                "findings": 0,
                "rule": finding["rule"],
                "origin_kind": finding["origin"]["kind"],
                "sub_rule": finding["sub_rule"],
                "example": finding.get("quote") or finding.get("message", ""),
                "origins": [],
            },
        )
        item["findings"] += 1
        origin = finding["origin"].get("id") or "-"
        if origin not in item["origins"] and len(item["origins"]) < 5:
            item["origins"].append(origin)
    return classes


def build_record(
    *,
    repository: str,
    lane: str,
    outcome: str,
    exit_code: int | None = None,
    durable_state: str = "",
    failure_detail: str = "",
    failure_classification: str = "",
    findings: Sequence[Mapping[str, Any]] = (),
    validation_failures: Sequence[Mapping[str, Any]] = (),
    repairs: Sequence[Mapping[str, Any]] = (),
    version_set: str = "",
    index: OriginIndex | None = None,
    origin: str = "hosted",
) -> dict[str, Any]:
    """One lane's record. ``findings`` are review findings (``Finding.to_record()`` shape, or the
    same keys parsed from a log); ``validation_failures`` are ``{"check", "detail", "unit_id",
    "quote", "section_id"}``. A failed lane with no finding is classified as a job error."""
    index = index or OriginIndex()
    for attempt in repairs:
        for item in attempt.get("facts_defects") or []:
            index.add_renderer(str(item.get("quote", "")), item.get("fact_ids") or ())
    rows: list[dict[str, Any]] = []
    for finding in findings:
        rows.append(
            _finding(
                rule=str(finding.get("rule", "")),
                source="review",
                message=str(finding.get("message") or finding.get("evidence") or ""),
                quote=str(finding.get("quote") or ""),
                section_id=str(finding.get("section_id") or ""),
                label=str(finding.get("finding_id") or finding.get("label") or ""),
                lane=lane,
                index=index,
            )
        )
    for failure in validation_failures:
        rows.append(
            _finding(
                rule=str(failure.get("check", "")),
                source="validation",
                message=str(failure.get("detail", "")),
                quote=str(failure.get("quote") or ""),
                section_id=str(failure.get("section_id") or ""),
                unit_id=str(failure.get("unit_id") or ""),
                lane=lane,
                index=index,
            )
        )
    error: dict[str, Any] | None = None
    if outcome != "success":
        kind, sub = job_error_kind(failure_detail) if failure_detail else ("unknown", "no_detail")
        error = {
            "classification": failure_classification,
            "detail": str(failure_detail)[:_TEXT_LIMIT * 2],
            "kind": kind,
            "transient": is_transient(failure_detail),
        }
        if not rows:
            rows.append(
                {
                    "rule": RULE_JOB,
                    "label": kind,
                    "source": "job",
                    "section_id": "",
                    "sub_rule": f"{kind}:{sub}",
                    "origin": {"kind": ORIGIN_JOB, "id": kind},
                    "quote": "",
                    "message": str(failure_detail)[:_TEXT_LIMIT],
                    "signature": f"{RULE_JOB}|{ORIGIN_JOB}|{kind}:{sub}",
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "lane": lane,
        "outcome": outcome,
        "exit_code": exit_code,
        "durable_state": durable_state,
        "version_set": version_set,
        "failure": error,
        "findings": rows,
        "repairs": [_repair(attempt) for attempt in repairs],
        "classes": classes_of(rows),
        "origin": origin,
    }


def finalize(
    record: dict[str, Any],
    *,
    run_id: str = "",
    run_url: str = "",
    main_sha: str = "",
    source_revision: str = "",
    at: str = "",
    code: str | None = None,
    root: Path | None = None,
    revision: str = "HEAD",
) -> dict[str, Any]:
    """Stamp the run's identity and each class's code scope (paths + hash at ``revision``)."""
    from repo_presenter.core.llm.budget import code_fingerprint

    root = root or Path.cwd()
    record = dict(record)
    record.update(
        run_id=str(run_id or record.get("run_id") or ""),
        run_url=run_url or record.get("run_url", ""),
        main_sha=main_sha or record.get("main_sha", ""),
        source_revision=source_revision or record.get("source_revision", ""),
        at=at or record.get("at") or datetime.now(UTC).isoformat(timespec="seconds"),
        code=code if code is not None else code_fingerprint(root, revision),
    )
    transient = bool((record.get("failure") or {}).get("transient"))
    classes = {}
    for signature, item in (record.get("classes") or {}).items():
        item = dict(item)
        paths = None if transient else class_scope_paths(item["rule"], item["origin_kind"], record["lane"])
        if item["rule"] == RULE_JOB and (record.get("failure") or {}).get("kind") in ("unknown", *JOB_KINDS.values()):
            paths = None
        item["scope_paths"] = list(paths) if paths else None
        item["scope"] = scope_fingerprint(paths, root, revision) if paths else ""
        classes[signature] = item
    record["classes"] = classes
    return record


def local_record_path(workdir: Path, lane: str) -> Path:
    return workdir / LOCAL_DIRNAME / f"{lane}.json"


def keep_blocking(out_dir: Path, verdict: Any) -> None:
    """present.py: the rejected candidate's blocking findings, beside the lane's outputs (the
    verdict file is only written for a model-reviewed candidate)."""
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = [finding.to_record() for finding in verdict.blocking_findings]
        (out_dir / BLOCKING_FILENAME).write_text(
            json.dumps({"findings": rows}, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 -- evidence, never a reason to change the outcome
        print(f"failure record: blocking findings not kept ({type(exc).__name__}: {exc})")


def write_local_record(
    *,
    workdir: Path,
    repository: str,
    lane: str,
    exit_code: int,
    durable_state: str,
    failure_detail: str = "",
    failure_classification: str = "",
    version_set: str = "",
) -> Path:
    """present.py, at the end of every lane run: the record of what this run's outputs show."""
    out_dir = workdir / LANE_OUT_DIRS.get(lane, "cascade")
    findings: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    if exit_code != 0:
        blocking = _read_json(out_dir / BLOCKING_FILENAME) or {}
        findings = [f for f in blocking.get("findings", []) if isinstance(f, dict)]
        document = _read_json(out_dir / "validation.json") or {}
        for check in document.get("checks", []) if isinstance(document, dict) else []:
            if check.get("verdict") != "FAIL":
                continue
            for failure in check.get("failures") or []:
                validation.append({"check": check.get("id", ""), **failure})
        ledger = _read_json(out_dir / "repairs.json") or {}
        attempts = ledger.get("attempts", {}) if isinstance(ledger, dict) else {}
        repairs = [a for a in (attempts.values() if isinstance(attempts, dict) else []) if isinstance(a, dict)]
    record = build_record(
        repository=repository,
        lane=lane,
        outcome="success" if exit_code == 0 else "failure",
        exit_code=exit_code,
        durable_state=durable_state,
        failure_detail=failure_detail,
        failure_classification=failure_classification,
        findings=findings,
        validation_failures=validation,
        repairs=repairs,
        version_set=version_set,
        index=origin_index(workdir, lane),
    )
    path = local_record_path(workdir, lane)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def job_record(*, repository: str, lane: str, kind: str, detail: str, outcome: str = "failure") -> dict[str, Any]:
    """A lane that left no record of its own: a facts-job failure, a crash, a cancelled step."""
    name = JOB_KINDS.get(kind, "LaneStepFailure")
    return build_record(
        repository=repository, lane=lane, outcome=outcome,
        failure_detail=f"{name}: {detail or '-'}",
        failure_classification="unknown",
    )


#: The job-error kinds of a lane that left no record; never held (their cause is not classified).
JOB_KINDS = {"facts": "FactsJobFailure", "unknown": "LaneStepFailure"}


# --------------------------------------------------------------------------------------- state refs


def failure_ref(repository: str, lane: str) -> str:
    from repo_presenter.core.state.git_backend import _ref_key

    return f"{FAILURE_REF_PREFIX}/{_ref_key(repository, lane)}"


def parse_failure_ref(ref: str) -> tuple[str, str] | None:
    if not ref.startswith(FAILURE_REF_PREFIX + "/"):
        return None
    key = ref[len(FAILURE_REF_PREFIX) + 1 :]
    lane = "R"
    if key.endswith("@lane-l"):
        key, lane = key[: -len("@lane-l")], "L"
    if key.count("__") < 1:
        return None
    return key.replace("__", "/", 1), lane


def _run_order(record: Mapping[str, Any]) -> tuple[int, str]:
    run_id = str(record.get("run_id") or "")
    return (int(run_id) if run_id.isdigit() else 0, str(record.get("at") or ""))


def compact(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record.get("run_id", ""),
        "at": record.get("at", ""),
        "code": record.get("code", ""),
        "version_set": record.get("version_set", ""),
        "source_revision": record.get("source_revision", ""),
        "outcome": record.get("outcome", ""),
        "classes": sorted(record.get("classes") or {}),
        "findings": len(record.get("findings") or []),
    }


def merge(document: Mapping[str, Any] | None, record: Mapping[str, Any]) -> dict[str, Any]:
    """The cell's document with ``record`` in it: the latest record by run order, a bounded
    history of compact records (one per run id; re-merging the same run changes nothing)."""
    document = dict(document or {})
    history = [h for h in document.get("history") or [] if str(h.get("run_id")) != str(record.get("run_id"))]
    history.append(compact(record))
    history.sort(key=_run_order)
    latest = document.get("latest")
    if latest is None or str(latest.get("run_id")) == str(record.get("run_id")) or _run_order(record) >= _run_order(latest):
        latest = dict(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": record["repository"],
        "lane": record["lane"],
        "latest": latest,
        "history": history[-HISTORY_LIMIT:],
    }


def publish_record(record: Mapping[str, Any], *, remote: str, token: str | None) -> dict[str, Any]:
    from repo_presenter.core.state.git_backend import GitJsonRef

    with GitJsonRef(failure_ref(record["repository"], record["lane"]), remote=remote, token=token) as store:
        return store.update(lambda current: merge(current if isinstance(current, dict) else None, record))


def read_cells(*, remote: str, token: str | None) -> list[dict[str, Any]]:
    """Every cell's failure document on ``remote``: one shallow fetch of the namespace into an
    isolated workspace; read-only."""
    from repo_presenter.core.git_safety.git import run_git
    from repo_presenter.core.state.git_backend import GitStateBackend

    local_prefix = "refs/repository-presenter-failures-read"
    documents: list[dict[str, Any]] = []
    with GitStateBackend(remote=remote, token=token) as backend, backend._lock:
        fetched = backend._run_remote_git(
            ["fetch", "--no-write-fetch-head", "--no-tags", "--depth=1", backend._remote,
             f"+{FAILURE_REF_PREFIX}/*:{local_prefix}/*"],
            timeout=600,
        )
        if fetched.returncode != 0:
            raise RuntimeError(f"fetch of {FAILURE_REF_PREFIX} failed: {fetched.stderr.strip()}")
        listed = run_git(["for-each-ref", "--format=%(refname)", local_prefix], cwd=backend._git_cwd)
        for local in sorted(filter(None, listed.stdout.splitlines())):
            blob = run_git(["cat-file", "-p", f"{local}:record.json"], cwd=backend._git_cwd)
            if blob.returncode != 0:
                continue
            try:
                document = json.loads(blob.stdout)
            except ValueError:
                continue
            if isinstance(document, dict) and isinstance(document.get("latest"), dict):
                documents.append(document)
    return documents


# --------------------------------------------------------------------------------------- pareto


def pareto(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The portfolio Pareto over each cell's latest record: class signature -> cells, findings,
    example quotes, origins, lanes, and whether the class is new since the previous code
    fingerprint (seen under the newest code and in no record of any older code)."""
    latest = [doc["latest"] for doc in documents if isinstance(doc.get("latest"), dict)]
    newest_code = max(latest, key=lambda r: str(r.get("at") or ""), default={}).get("code", "")
    older: set[str] = set()
    for doc in documents:
        for entry in doc.get("history") or []:
            if entry.get("code") and entry.get("code") != newest_code:
                older.update(entry.get("classes") or [])
    rows: dict[str, dict[str, Any]] = {}
    failing = 0
    for record in latest:
        classes = record.get("classes") or {}
        if record.get("outcome") == "success" or not classes:
            continue
        failing += 1
        cell = f"{record.get('repository')}@{record.get('lane')}"
        for signature, item in classes.items():
            row = rows.setdefault(
                signature,
                {"signature": signature, "cells": [], "findings": 0, "examples": [], "origins": [],
                 "lanes": set(), "new": False},
            )
            row["cells"].append(cell)
            row["findings"] += int(item.get("findings") or 0)
            row["lanes"].add(str(record.get("lane")))
            example = _squash(str(item.get("example") or ""))[:140]
            if example and example not in row["examples"] and len(row["examples"]) < 2:
                row["examples"].append(example)
            for origin in item.get("origins") or []:
                if origin not in row["origins"] and len(row["origins"]) < 3:
                    row["origins"].append(origin)
            if record.get("code") == newest_code and newest_code and signature not in older:
                row["new"] = True
    ordered = sorted(rows.values(), key=lambda r: (-len(r["cells"]), -r["findings"], r["signature"]))
    for row in ordered:
        row["lanes"] = sorted(row["lanes"])
    return {
        "cells": len(latest),
        "failing_cells": failing,
        "newest_code": newest_code[:12],
        "classes": ordered,
    }


_PIPE = "\\|"
_SIG_PIPE = " \\| "


def render_pareto(result: Mapping[str, Any], *, limit: int = 25, markdown: bool = True) -> str:
    rows = list(result.get("classes") or [])
    head = (
        f"{result.get('failing_cells', 0)} failing of {result.get('cells', 0)} recorded cells; "
        f"{len(rows)} classes; newest code {result.get('newest_code') or '?'}"
    )
    if not markdown:
        lines = [head]
        for row in rows[:limit]:
            lines.append(
                f"{len(row['cells']):>3} cells {row['findings']:>4} findings  {'NEW ' if row['new'] else ''}"
                f"{row['signature']}  [{', '.join(row['lanes'])}]  e.g. {(row['examples'] or ['-'])[0][:90]}"
            )
        return "\n".join(lines) + "\n"
    lines = [head, "", "| class (rule\\|origin\\|sub-rule) | cells | findings | lanes | new | example | origin |", "|---|---|---|---|---|---|---|"]
    for row in rows[:limit]:
        example = (row["examples"] or ["-"])[0].replace("|", _PIPE)
        signature = row["signature"].replace("|", _SIG_PIPE)
        lines.append(
            f"| {signature} | {len(row['cells'])} | {row['findings']} | "
            f"{', '.join(row['lanes'])} | {'yes' if row['new'] else ''} | {example[:100]} | "
            f"{', '.join(row['origins'])[:80].replace('|', '/')} |"
        )
    if len(rows) > limit:
        lines.append(f"\n... {len(rows) - limit} more classes")
    return "\n".join(lines) + "\n"


def render_run_summary(records: Sequence[Mapping[str, Any]]) -> str:
    """The present job's summary table: one row per class of each lane of this run."""
    lines = ["### Failure classes (this run)", "", "| lane | outcome | class | findings | origin | example |", "|---|---|---|---|---|---|"]
    for record in records:
        classes = record.get("classes") or {}
        if not classes:
            lines.append(f"| {record['lane']} | {record['outcome']} | - | 0 | - | - |")
        for signature, item in sorted(classes.items(), key=lambda kv: -int(kv[1].get("findings") or 0)):
            example = _squash(str(item.get("example") or ""))[:100].replace("|", _PIPE)
            shown = signature.replace("|", _SIG_PIPE)
            lines.append(
                f"| {record['lane']} | {record['outcome']} | {shown} | "
                f"{item.get('findings')} | {', '.join(item.get('origins') or [])[:60].replace('|', '/')} | {example} |"
            )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------- planner hold


def unchanged_classes(record: Mapping[str, Any], scope_of: Callable[[Sequence[str]], str]) -> list[str] | None:
    """The classes of a failed record when EVERY one is still unchanged under current code (its
    recorded scope hash equals ``scope_of(its paths)`` now), else ``None``: a class with no scope
    (transient, unknown rule, job error of unknown kind) or a changed scope releases the cell."""
    if record.get("outcome") == "success":
        return None
    classes = record.get("classes") or {}
    if not classes:
        return None
    for item in classes.values():
        paths = item.get("scope_paths")
        if not paths or not item.get("scope"):
            return None
        if scope_of(paths) != item["scope"]:
            return None
    return sorted(classes)


def known_failures(
    documents: Sequence[Mapping[str, Any]], scope_of: Callable[[Sequence[str]], str]
) -> dict[tuple[str, str], dict[str, Any]]:
    """``{(repository, lane): {run_id, source_revision, classes}}`` for every cell the planner may
    hold: its latest record failed in classes all unchanged under current code."""
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for doc in documents:
        record = doc.get("latest") or {}
        classes = unchanged_classes(record, scope_of)
        if classes:
            found[(str(record.get("repository")), str(record.get("lane")))] = {
                "run_id": str(record.get("run_id") or ""),
                "source_revision": str(record.get("source_revision") or ""),
                "classes": classes,
            }
    return found


# --------------------------------------------------------------------------------------- backfill (logs)

_LOG_LINE = re.compile(r"^(?P<job>[^\t]*)\t(?P<step>[^\t]*)\t﻿?(?:\d{4}-\d\d-\d\dT[\d:.]+Z )?(?P<text>.*)$")
_STEP_LANE = re.compile(r"^Present \(Lane (?P<lane>[RL])\)$")
_FINDING = re.compile(r"^finding (?P<label>\S+) \[(?P<rule>[^\]]+)\] section=(?P<section>\S+): (?P<message>.*)$")
_BLOCKING = re.compile(r"^blocking (?P<check>BC-\d+): (?P<detail>.*)$")
_REPAIR = re.compile(r"^repair (?P<outcome>\w+) (?P<label>[^:]+): (?P<rest>.*)$")
_PRESENT = re.compile(r"^present: (?P<repo>\S+) lane (?P<lane>[RL]) exit (?P<exit>\d+), durable state (?P<state>\S+)")
_FAILURE = re.compile(r"^failure \((?P<cls>[^)]+)\): (?P<detail>.*)$")
_VERSION = re.compile(r"^version set \(Lane [RL]\): (?P<vs>[0-9a-f]+)")
_FACTS_DEFECT = re.compile(
    r"facts defect: (?P<quote>'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\") is printed by the renderer from "
    r"fact (?P<ids>.+?), not by any authored"
)
_ARG = re.compile(r'--(?P<name>[a-z-]+) "(?P<value>[^"]*)"')


def _literal(text: str) -> str:
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text.strip("'\"")
    return value if isinstance(value, str) else str(value)


def parse_run_log(text: str) -> dict[str, Any]:
    """One hosted present run's log -> ``{repository, source_revision, main_sha, facts_failed,
    lanes: {lane: {findings, validation, repairs, exit_code, durable_state, failure, version_set}}}``.
    Only lines present.py prints are read (``report_findings``, ``report_repairs``, the
    deterministic-only ``blocking`` lines, the closing ``present:``/``failure`` lines)."""
    run: dict[str, Any] = {"repository": "", "source_revision": "", "main_sha": "", "facts_failed": False,
                           "outcomes": {}, "lanes": {}}
    last_finding: dict[str, Any] | None = None
    for raw in text.splitlines():
        match = _LOG_LINE.match(raw)
        if not match:
            continue
        step, body = match.group("step"), match.group("text").lstrip("﻿")
        if match.group("job") == "facts" and step == "Build the facts" and body.startswith("##[error]"):
            run["facts_failed"] = True
        if step.startswith("Record this run") or step.startswith("Run python -m repo_presenter.core.llm.budget settle"):
            for arg in _ARG.finditer(body):
                if arg.group("name") == "source-revision" and arg.group("value"):
                    run["source_revision"] = arg.group("value")
                elif arg.group("name") == "main-sha" and arg.group("value"):
                    run["main_sha"] = arg.group("value")
                elif arg.group("name") == "outcome":
                    lane, _, value = arg.group("value").partition("=")
                    run["outcomes"][lane] = value
        if body.startswith("  INPUT_REPOSITORY: ") and not run["repository"]:
            run["repository"] = body.split(":", 1)[1].strip()
        lane_match = _STEP_LANE.match(step)
        if not lane_match:
            continue
        lane = run["lanes"].setdefault(
            lane_match.group("lane"),
            {"findings": [], "validation": [], "repairs": [], "exit_code": None, "durable_state": "",
             "failure": "", "classification": "", "version_set": ""},
        )
        if body.startswith("  quote: ") and last_finding is not None:
            last_finding["quote"] = _literal(body[len("  quote: "):])
            continue
        if body.startswith("  evidence: ") and last_finding is not None:
            last_finding["evidence"] = body[len("  evidence: "):]
            continue
        last_finding = None
        if found := _FINDING.match(body):
            last_finding = {
                "rule": found.group("rule"), "finding_id": found.group("label"),
                "section_id": "" if found.group("section") == "-" else found.group("section"),
                "message": found.group("message"), "quote": "",
            }
            lane["findings"].append(last_finding)
        elif found := _BLOCKING.match(body):
            lane["validation"].append({"check": found.group("check"), "detail": found.group("detail")})
        elif found := _REPAIR.match(body):
            rest = found.group("rest")
            reason = rest.split(" | reason: ", 1)[1] if " | reason: " in rest else ""
            defects = [
                {"quote": _literal(item.group("quote")), "fact_ids": [i.strip() for i in item.group("ids").split(",")]}
                for item in _FACTS_DEFECT.finditer(rest)
            ]
            lane["repairs"].append(
                {"label": found.group("label"), "outcome": found.group("outcome"), "reason": reason,
                 "facts_defects": defects}
            )
        elif found := _PRESENT.match(body):
            lane["exit_code"] = int(found.group("exit"))
            lane["durable_state"] = found.group("state")
            run["repository"] = run["repository"] or found.group("repo")
        elif found := _FAILURE.match(body):
            lane["classification"] = found.group("cls")
            lane["failure"] = found.group("detail")
        elif found := _VERSION.match(body):
            lane["version_set"] = found.group("vs")
    return run


def records_from_log(text: str, *, run_id: str, run_url: str = "", at: str = "", head_sha: str = "",
                     lanes: Sequence[str] = ("R", "L")) -> list[dict[str, Any]]:
    """The records a past run would have written, rebuilt from its log (``origin: backfill:log``).
    Origins come from what the log prints: unit ids, the repair ledger's facts defects, a Lane L
    detector; nothing else is guessed."""
    run = parse_run_log(text)
    repository = run["repository"]
    if not repository:
        return []
    records: list[dict[str, Any]] = []
    for lane in lanes:
        parsed = run["lanes"].get(lane)
        outcome = run["outcomes"].get(lane, "")
        if parsed is None:
            if outcome in ("", "skipped") and not run["facts_failed"]:
                continue
            record = job_record(
                repository=repository, lane=lane,
                kind="facts" if run["facts_failed"] else "unknown",
                detail="the facts job failed; no lane ran" if run["facts_failed"] else f"lane step {outcome or 'absent'}",
            )
            record["origin"] = "backfill:log"
        else:
            exit_code = parsed["exit_code"]
            success = exit_code == 0 or (exit_code is None and outcome == "success")
            record = build_record(
                repository=repository, lane=lane,
                outcome="success" if success else "failure",
                exit_code=exit_code, durable_state=parsed["durable_state"],
                failure_detail=parsed["failure"] or ("" if success else f"lane step {outcome or 'failed'} with no failure line"),
                failure_classification=parsed["classification"],
                findings=parsed["findings"] if not success else (),
                validation_failures=parsed["validation"] if not success else (),
                repairs=parsed["repairs"], version_set=parsed["version_set"],
                origin="backfill:log",
            )
        records.append(record)
    for record in records:
        record.update(run_id=str(run_id), run_url=run_url, at=at,
                      main_sha=run["main_sha"] or head_sha, source_revision=run["source_revision"])
    return records


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return json.loads(result.stdout)


def backfill(
    *, repo: str, workflow: str, since: str, limit: int, logs_dir: Path | None, root: Path,
    conclusions: Sequence[str] = ("failure", "success"),
) -> list[dict[str, Any]]:
    """Records for every completed dispatched run of ``workflow`` created at or after ``since``,
    rebuilt from ``gh run view <id> --log`` (or ``<logs_dir>/<id>.log`` when present)."""
    runs = _gh_json(["run", "list", "-R", repo, "--workflow", workflow, "-L", str(limit), "--json",
                     "databaseId,conclusion,createdAt,event,headSha,status,url"])
    records: list[dict[str, Any]] = []
    for run in sorted(runs, key=lambda r: int(r["databaseId"])):
        if run.get("event") != "workflow_dispatch" or run.get("status") != "completed":
            continue
        if str(run.get("createdAt", "")) < since or run.get("conclusion") not in conclusions:
            continue
        run_id = str(run["databaseId"])
        cached = logs_dir / f"{run_id}.log" if logs_dir else None
        if cached is not None and cached.is_file() and cached.stat().st_size:
            text = cached.read_text(encoding="utf-8", errors="replace")
        else:
            result = subprocess.run(["gh", "run", "view", run_id, "-R", repo, "--log"],
                                    capture_output=True, text=True, check=False)
            if result.returncode != 0:
                print(f"backfill: run {run_id}: log not readable ({result.stderr.strip()[:200]})", file=sys.stderr)
                continue
            text = result.stdout
            if cached is not None:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(text, encoding="utf-8")
        for record in records_from_log(text, run_id=run_id, run_url=run.get("url", ""),
                                       at=str(run.get("createdAt", "")), head_sha=str(run.get("headSha", ""))):
            records.append(finalize(record, root=root, revision=record["main_sha"] or "HEAD"))
    return records


def documents_from_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Cell documents built locally (backfill dry run, tests): the same merge the ref applies."""
    cells: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (str(record["repository"]), str(record["lane"]))
        cells[key] = merge(cells.get(key), record)
    return list(cells.values())


# --------------------------------------------------------------------------------------- CLI


def _token() -> str | None:
    return os.environ.get("REPOSITORY_PRESENTER_STATE_TOKEN") or None


def _publish(args: argparse.Namespace) -> int:
    outcomes = dict(item.partition("=")[::2] for item in args.outcome or [])
    lanes = [lane for lane in (args.lanes or "").split(",") if lane in LANE_OUT_DIRS]
    records = []
    for lane in lanes:
        path = local_record_path(args.workdir, lane)
        record = _read_json(path) if path.is_file() else None
        outcome = outcomes.get(lane, "")
        if not isinstance(record, dict):
            if outcome in ("", "skipped") and args.facts_result in ("", "success", "skipped"):
                continue  # this lane did not run in this job (a single-lane run)
            facts_failed = args.facts_result not in ("", "success")
            record = job_record(
                repository=args.repository, lane=lane,
                kind="facts" if facts_failed else "unknown",
                detail=(f"the facts job ended {args.facts_result}; no lane ran" if facts_failed
                        else f"the lane step ended {outcome or 'without a record'} and left no failure record"),
            )
        records.append(finalize(record, run_id=args.run_id, run_url=args.run_url, main_sha=args.main_sha,
                                source_revision=args.source_revision))
    status = 0
    for record in records:
        try:
            if args.remote:
                publish_record(record, remote=args.remote, token=_token())
            print(f"failure record: {failure_ref(record['repository'], record['lane'])} run {record['run_id']} "
                  f"{record['outcome']}, {len(record['classes'])} class(es)")
        except Exception as exc:  # noqa: BLE001 -- loud: a record not written is evidence lost
            print(f"::error::failure record for {record['repository']} lane {record['lane']} not written: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            status = 1
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(render_run_summary(records))
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo_presenter.failures", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    pub = sub.add_parser("publish", help="the present job: finalize, push and summarise this run's records")
    pub.add_argument("--remote", default="")
    pub.add_argument("--repository", required=True)
    pub.add_argument("--lanes", default="R,L")
    pub.add_argument("--outcome", action="append")
    pub.add_argument("--facts-result", default="")
    pub.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    pub.add_argument("--run-url", default="")
    pub.add_argument("--main-sha", default="")
    pub.add_argument("--source-revision", default="")
    pub.add_argument("--workdir", type=Path, default=Path(".present-work"))
    pub.add_argument("--summary", default="")

    par = sub.add_parser("pareto", help="the portfolio Pareto over every cell's latest record")
    par.add_argument("--remote", default="origin")
    par.add_argument("--json", action="store_true")
    par.add_argument("--text", action="store_true", help="plain text instead of a markdown table")
    par.add_argument("--limit", type=int, default=25)

    back = sub.add_parser("backfill", help="rebuild records from the logs of past present runs")
    back.add_argument("--repo", required=True)
    back.add_argument("--workflow", default="present.yml")
    back.add_argument("--since", required=True, help="ISO date: runs created at or after it")
    back.add_argument("--limit", type=int, default=100)
    back.add_argument("--logs-dir", type=Path, default=None)
    back.add_argument("--remote", default="", help="push each record to its cell ref on this remote")
    back.add_argument("--out", type=Path, default=None, help="write the records as JSON here")
    back.add_argument("--conclusion", action="append", default=None)
    args = parser.parse_args(argv)

    if args.command == "publish":
        return _publish(args)
    if args.command == "pareto":
        result = pareto(read_cells(remote=args.remote, token=_token()))
        print(json.dumps(result, indent=1) if args.json else render_pareto(result, limit=args.limit, markdown=not args.text))
        return 0
    records = backfill(repo=args.repo, workflow=args.workflow, since=args.since, limit=args.limit,
                       logs_dir=args.logs_dir, root=Path.cwd(),
                       conclusions=tuple(args.conclusion or ("failure", "success")))
    if args.out:
        args.out.write_text(json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    status = 0
    if args.remote:
        for record in records:
            try:
                publish_record(record, remote=args.remote, token=_token())
            except Exception as exc:  # noqa: BLE001
                print(f"backfill: {record['repository']} lane {record['lane']} run {record['run_id']} not written: "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                status = 1
    print(render_pareto(pareto(documents_from_records(records))))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
