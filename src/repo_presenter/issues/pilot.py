"""The issue-management pilot (owner ruling R39, 2026-11-13): which upstream repositories the
monitor may maintain issues on, and the recorded reproduction behind every monitored issue.

Two committed, owner-controlled data files, read verbatim and validated fail-closed:

* ``data/issue_pilot.json`` -- the pilot allowlist. Only a repository listed here may have its
  presenter issues commented on, closed or reopened, and only for the effects listed (``issue``:
  close/reopen, ``issue_comment``: the dated re-check / closing / recurrence comment). Creating a
  new issue is never part of the pilot (R39 (4): recording, monitoring and open/close
  maintenance); ``github/client.py``'s write guard refuses a create on a pilot-only grant. Widening
  the pilot is the owner's call (``tests/issues/test_pilot.py`` pins the committed list).
* ``data/issue_reproductions/<owner>__<name>.json`` -- per issue, the reproduction recorded from
  the issue itself (its script, the setup it needs, the source locations it names) and the two
  output predicates that decide it: ``reproduces_if_any`` (the defect's own "actual result") and
  ``resolved_if_all`` / ``resolved_if_output_empty`` (the "expected" result). Output that matches
  neither is NOT_VERIFIABLE: never a close.

Stdlib plus ``issues/model.py`` (itself stdlib only), so ``github/client.py`` can consult the
allowlist without an import cycle.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn

from repo_presenter.issues.model import DEFECT_CLASSES

REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_PATH = REPO_ROOT / "data" / "issue_pilot.json"
REPRODUCTIONS_DIR = REPO_ROOT / "data" / "issue_reproductions"

#: The client-level effects a pilot entry may grant (``github/client.py``'s own effect names).
PILOT_EFFECTS = frozenset({"issue", "issue_comment"})
Mode = Literal["dry_run", "live"]
MODES: tuple[Mode, ...] = ("dry_run", "live")
Environment = Literal["checkout", "consumer_omit_dev"]
ENVIRONMENTS: tuple[Environment, ...] = ("checkout", "consumer_omit_dev")

_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_CHECK_ID = re.compile(r"^example:[a-z0-9]+(?:[._-][a-z0-9]+)*$")
MAX_SCRIPT_CHARS = 20_000


class PilotError(ValueError):
    """A pilot data file is missing or does not have the shape the monitor depends on."""


@dataclass(frozen=True)
class PilotEntry:
    repository: str
    effects: frozenset[str]
    mode: Mode
    bot_login: str
    recheck_comment_interval_days: int
    unchanged_revision_comment_interval_days: int


@dataclass(frozen=True)
class Reproduction:
    issue_number: int
    defect_fingerprint: str
    check_id: str
    defect_class: str
    recorded_revision: str
    recorded_at: str
    environment: Environment
    script: str
    reproduces_if_any: tuple[str, ...]
    resolved_if_all: tuple[str, ...]
    resolved_if_output_empty: bool
    evidence: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class ReproductionSet:
    repository: str
    prepare: tuple[tuple[str, ...], ...]
    reproductions: tuple[Reproduction, ...]

    def by_fingerprint(self) -> dict[str, Reproduction]:
        return {r.defect_fingerprint: r for r in self.reproductions}


def _bad(path: Path, why: str) -> NoReturn:
    raise PilotError(f"{path}: {why}")


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _bad(path, "is missing")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _bad(path, f"is unreadable ({type(exc).__name__})")


def _positive_int(path: Path, value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _bad(path, f"{field} must be a positive integer")
    return value


def load_pilot(path: Path | None = None) -> dict[str, PilotEntry]:
    """The pilot allowlist as ``{lowercased owner/name: entry}``. One bad entry invalidates the
    whole file (fail closed, exactly like the upstream write allowlist)."""
    path = path or PILOT_PATH
    data = _read(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        _bad(path, "has no schema_version 1 object")
    bot_login = data.get("bot_login")
    if not isinstance(bot_login, str) or not bot_login.endswith("[bot]"):
        _bad(path, "bot_login must name a GitHub App bot identity (…[bot])")
    entries = data.get("repositories")
    if not isinstance(entries, list):
        _bad(path, "has no repositories list")
    result: dict[str, PilotEntry] = {}
    for item in entries:
        if not isinstance(item, dict):
            _bad(path, "has a non-object entry")
        slug = item.get("repository")
        if not isinstance(slug, str) or not _REPOSITORY.match(slug) or ".." in slug:
            _bad(path, f"has an invalid repository {slug!r}")
        effects = item.get("effects")
        if (
            not isinstance(effects, list)
            or not effects
            or not all(isinstance(e, str) and e in PILOT_EFFECTS for e in effects)
        ):
            _bad(path, f"has invalid effects for {slug}: {effects!r}")
        mode = item.get("mode")
        if mode not in MODES:
            _bad(path, f"has an invalid mode for {slug}: {mode!r}")
        key = slug.lower()
        if key in result:
            _bad(path, f"lists {slug} twice")
        result[key] = PilotEntry(
            repository=slug,
            effects=frozenset(effects),
            mode=mode,
            bot_login=bot_login,
            recheck_comment_interval_days=_positive_int(
                path, item.get("recheck_comment_interval_days"), "recheck_comment_interval_days"
            ),
            unchanged_revision_comment_interval_days=_positive_int(
                path,
                item.get("unchanged_revision_comment_interval_days"),
                "unchanged_revision_comment_interval_days",
            ),
        )
    return result


class NotInPilotError(PilotError):
    """The repository is not on the pilot allowlist: the monitor does nothing with it."""


def require_pilot(repository: str, path: Path | None = None) -> PilotEntry:
    """The pilot entry for ``repository``, or :class:`NotInPilotError` -- the enforcement point
    every monitor entry point passes before reading or writing anything for a repository."""
    entry = load_pilot(path).get(repository.lower())
    if entry is None:
        raise NotInPilotError(
            f"{repository} is not on the issue-management pilot allowlist "
            f"({path or PILOT_PATH}); widening the pilot is the owner's call (R39)"
        )
    return entry


def pilot_effects(repository: str, path: Path | None = None) -> frozenset[str]:
    """The pilot effects granted to ``repository`` (empty when unlisted or the file is bad)."""
    try:
        entry = load_pilot(path).get(repository.lower())
    except PilotError:
        return frozenset()
    return entry.effects if entry is not None else frozenset()


def reproductions_path(repository: str) -> Path:
    owner, name = repository.split("/", 1)
    return REPRODUCTIONS_DIR / f"{owner}__{name}.json"


def _patterns(path: Path, value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(p, str) and p for p in value):
        _bad(path, f"{field} must be a list of non-empty regular expressions")
    for pattern in value:
        try:
            re.compile(pattern)
        except re.error as exc:
            _bad(path, f"{field} has an invalid regular expression {pattern!r}: {exc}")
    return tuple(value)


def load_reproductions(repository: str, path: Path | None = None) -> ReproductionSet:
    """The recorded reproductions for ``repository``, validated fail-closed."""
    path = path or reproductions_path(repository)
    data = _read(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        _bad(path, "has no schema_version 1 object")
    if data.get("repository") != repository:
        _bad(path, f"names {data.get('repository')!r}, not {repository}")
    prepare = data.get("prepare")
    if not isinstance(prepare, list) or not all(
        isinstance(cmd, list) and cmd and all(isinstance(a, str) and a for a in cmd)
        for cmd in prepare
    ):
        _bad(path, "prepare must be a list of argv lists")
    raw = data.get("reproductions")
    if not isinstance(raw, list) or not raw:
        _bad(path, "reproductions must be a non-empty list")
    seen_fp: set[str] = set()
    seen_check: set[str] = set()
    items: list[Reproduction] = []
    for r in raw:
        if not isinstance(r, dict):
            _bad(path, "has a non-object reproduction")
        number = _positive_int(path, r.get("issue_number"), "issue_number")
        fp = r.get("defect_fingerprint")
        if not isinstance(fp, str) or not _FINGERPRINT.match(fp) or fp in seen_fp:
            _bad(path, f"issue {number}: defect_fingerprint missing, malformed or duplicated")
        check_id = r.get("check_id")
        if not isinstance(check_id, str) or not _CHECK_ID.match(check_id) or check_id in seen_check:
            _bad(path, f"issue {number}: check_id must be a unique example:<slug>")
        revision = r.get("recorded_revision")
        if not isinstance(revision, str) or not _REVISION.match(revision):
            _bad(path, f"issue {number}: recorded_revision must be a 40-hex commit")
        environment = r.get("environment")
        if environment not in ENVIRONMENTS:
            _bad(path, f"issue {number}: unknown environment {environment!r}")
        script = r.get("script")
        if not isinstance(script, str) or not script.strip() or len(script) > MAX_SCRIPT_CHARS:
            _bad(path, f"issue {number}: script must be a non-empty string")
        reproduces = _patterns(path, r.get("reproduces_if_any"), "reproduces_if_any")
        if not reproduces:
            _bad(path, f"issue {number}: reproduces_if_any must name at least one pattern")
        resolved = _patterns(path, r.get("resolved_if_all"), "resolved_if_all")
        output_empty = r.get("resolved_if_output_empty")
        if not isinstance(output_empty, bool):
            _bad(path, f"issue {number}: resolved_if_output_empty must be a boolean")
        if not resolved and not output_empty:
            _bad(path, f"issue {number}: no resolved predicate (a close needs a positive test)")
        evidence_raw = r.get("evidence")
        if not isinstance(evidence_raw, list) or not evidence_raw:
            _bad(path, f"issue {number}: evidence must be a non-empty list")
        evidence: list[tuple[str, str | None]] = []
        for e in evidence_raw:
            if not isinstance(e, dict) or not isinstance(e.get("path"), str) or not e["path"]:
                _bad(path, f"issue {number}: every evidence entry needs a path")
            detail = e.get("detail")
            if detail is not None and not isinstance(detail, str):
                _bad(path, f"issue {number}: evidence detail must be a string")
            evidence.append((e["path"], detail))
        for field in ("defect_class", "recorded_at"):
            if not isinstance(r.get(field), str) or not r[field]:
                _bad(path, f"issue {number}: {field} must be a non-empty string")
        if r["defect_class"] not in DEFECT_CLASSES:
            _bad(path, f"issue {number}: unknown defect_class {r['defect_class']!r}")
        seen_fp.add(fp)
        seen_check.add(check_id)
        items.append(
            Reproduction(
                issue_number=number,
                defect_fingerprint=fp,
                check_id=check_id,
                defect_class=r["defect_class"],
                recorded_revision=revision,
                recorded_at=r["recorded_at"],
                environment=environment,
                script=script,
                reproduces_if_any=reproduces,
                resolved_if_all=resolved,
                resolved_if_output_empty=output_empty,
                evidence=tuple(evidence),
            )
        )
    return ReproductionSet(
        repository=repository,
        prepare=tuple(tuple(cmd) for cmd in prepare),
        reproductions=tuple(items),
    )
