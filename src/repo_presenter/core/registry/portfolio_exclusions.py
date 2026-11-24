"""The recorded, data-driven list of repositories outside the counted portfolio.

``data/portfolio_exclusions.json`` names each excluded repository with its reason, the decision-log
entry that records the owner's decision, and the owner's decision date. An excluded repository stays
in ``data/registry.json`` and keeps every seal and record it has (R10, R14); it is only not a cell of
either lane's denominator. Every place that enumerates the portfolio for counting or reporting calls
:func:`split_portfolio` instead of hard-coding a repository name.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from repo_presenter.core.errors import ConfigError

EXCLUSIONS_RELATIVE_PATH = Path("data") / "portfolio_exclusions.json"
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PATH = _REPO_ROOT / EXCLUSIONS_RELATIVE_PATH
_REQUIRED = ("repository", "reason", "decision_log", "owner_decision_date")

T = TypeVar("T")


@dataclass(frozen=True)
class PortfolioExclusion:
    repository: str
    reason: str
    decision_log: str
    owner_decision_date: str

    def line(self) -> str:
        return (
            f"{self.repository} (owner decision {self.owner_decision_date}; "
            f"{self.decision_log}): {self.reason}"
        )


def load_portfolio_exclusions(path: Path | None = None) -> list[PortfolioExclusion]:
    """Read and validate the list; fail closed on anything malformed. A missing file is an error
    only when ``path`` was given explicitly; the default file is required to exist in the repository."""
    target = path or DEFAULT_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"portfolio exclusions not found: {target}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"portfolio exclusions are not valid JSON: {target}: {exc}") from exc
    rows = raw.get("exclusions") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        raise ConfigError(f"portfolio exclusions need an 'exclusions' list: {target}")
    out: list[PortfolioExclusion] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in _REQUIRED):
            raise ConfigError(f"each portfolio exclusion needs non-empty {', '.join(_REQUIRED)}: {target}")
        if row["repository"] in seen:
            raise ConfigError(f"duplicate portfolio exclusion {row['repository']}: {target}")
        seen.add(row["repository"])
        out.append(PortfolioExclusion(**{k: row[k] for k in _REQUIRED}))
    return out


def excluded_repositories(path: Path | None = None) -> frozenset[str]:
    return frozenset(e.repository for e in load_portfolio_exclusions(path))


def split_portfolio(
    items: Iterable[T], key: Any = None, path: Path | None = None
) -> tuple[list[T], list[PortfolioExclusion]]:
    """``(counted, applied)``: ``items`` without the excluded repositories (order kept), and the
    exclusions that actually removed something. ``key`` maps an item to its repository (default: the
    item itself, or its ``.repository``)."""
    exclusions = {e.repository: e for e in load_portfolio_exclusions(path)}

    def repo_of(item: Any) -> str:
        if key is not None:
            return key(item)
        return item if isinstance(item, str) else item.repository

    counted: list[T] = []
    applied: dict[str, PortfolioExclusion] = {}
    for item in items:
        name = repo_of(item)
        if name in exclusions:
            applied[name] = exclusions[name]
        else:
            counted.append(item)
    return counted, list(applied.values())
