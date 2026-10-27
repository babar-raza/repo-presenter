"""The reviewer's calibration status: a committed file, read by code, failing closed.

``data/reviewer_calibration.json`` records whether the independent reviewer passed the calibration
gate (``readme.review.calibration.harness``) and the numbers it was measured at. Three statuses:

* ``NOT_PASSED``: the gate failed, was never run for this reviewer, or the file cannot be trusted.
  Every candidate the reviewer accepts is labelled ``uncalibrated`` and none is eligible for a pull
  request (``propose.effect``).
* ``PASSED``: every gate passed at ``reviewer_logic_version``/``prompt_version`` in the file.
* ``PASSED_WITH_DECLARED_LIMITS``: the deterministic stage carries the classes code can decide and
  the LLM-only classes missed the recall target; the measured recalls are declared in the file and
  the OWNER has accepted them. It is valid only while ``owner_acceptance`` is a non-empty string in
  a committed file. Nothing in this repository writes that field: this module has a reader and no
  writer, and ``tests/readme/review/test_calibration_status.py`` asserts so.

Failing closed means every doubt reads as ``NOT_PASSED``: a missing, unreadable or malformed file,
an unknown status, ``PASSED_WITH_DECLARED_LIMITS`` without an owner acceptance, ``PASSED`` while the
file itself lists failed gates, and a file measured for another ``REVIEWER_LOGIC_VERSION`` (a changed
reviewer is a different reviewer; it must be measured again).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_presenter.readme.review.calibration_names import (
    CALIBRATED,
    NOT_PASSED,
    PASSED,
    PASSED_WITH_DECLARED_LIMITS,
    PERMITTING,
    STATUSES,
    UNCALIBRATED,
    label_for,
)
from repo_presenter.readme.review.verdict import REVIEWER_LOGIC_VERSION

__all__ = [
    "CALIBRATED",
    "NOT_PASSED",
    "PASSED",
    "PASSED_WITH_DECLARED_LIMITS",
    "PERMITTING",
    "STATUSES",
    "UNCALIBRATED",
    "Calibration",
    "label_for",
    "load_calibration",
    "parse_calibration",
]

DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "reviewer_calibration.json"
)


@dataclass(frozen=True)
class Calibration:
    """The status the code acts on, with why a doubtful file was read as ``NOT_PASSED``."""

    status: str
    reviewer_logic_version: str = ""
    prompt_version: str = ""
    measured: dict[str, Any] = field(default_factory=dict)
    failed_gates: tuple[str, ...] = ()
    owner_acceptance: str = ""
    problem: str = ""

    @property
    def permits(self) -> bool:
        return self.status in PERMITTING

    @property
    def label(self) -> str:
        return label_for(self.status)


def _not_passed(problem: str, **known: Any) -> Calibration:
    return Calibration(NOT_PASSED, problem=problem, **known)


def parse_calibration(document: Any) -> Calibration:
    """The status a decoded file stands for. Pure; never raises."""
    if not isinstance(document, dict):
        return _not_passed("the calibration file is not a JSON object")
    status = document.get("status")
    if status not in STATUSES:
        return _not_passed(f"unknown calibration status {status!r}")
    measured = document.get("measured")
    failed = document.get("failed_gates", [])
    acceptance = document.get("owner_acceptance", "")
    if not isinstance(failed, list) or not all(
        isinstance(item, str) for item in failed
    ):
        return _not_passed("failed_gates must be a list of strings")
    if not isinstance(measured, dict):
        return _not_passed("measured must be an object holding the measured numbers")
    if not isinstance(acceptance, str):
        return _not_passed("owner_acceptance must be a string")
    known = {
        "reviewer_logic_version": str(document.get("reviewer_logic_version", "")),
        "prompt_version": str(document.get("prompt_version", "")),
        "measured": measured,
        "failed_gates": tuple(failed),
        "owner_acceptance": acceptance,
    }
    if status == NOT_PASSED:
        return Calibration(NOT_PASSED, **known)
    if known["reviewer_logic_version"] != REVIEWER_LOGIC_VERSION:
        return _not_passed(
            f"measured for reviewer logic {known['reviewer_logic_version']!r}, but this is "
            f"{REVIEWER_LOGIC_VERSION!r}: a changed reviewer is measured again",
            **known,
        )
    if status == PASSED and failed:
        return _not_passed(
            f"status PASSED while the file lists failed gates ({', '.join(failed)})",
            **known,
        )
    if status == PASSED_WITH_DECLARED_LIMITS and not acceptance.strip():
        return _not_passed(
            "PASSED_WITH_DECLARED_LIMITS needs a non-empty owner_acceptance in the committed "
            "file; code never writes it",
            **known,
        )
    return Calibration(status, **known)


def load_calibration(path: Path | None = None) -> Calibration:
    """Read the committed calibration file. A missing or unreadable file is ``NOT_PASSED``."""
    target = DEFAULT_CALIBRATION_PATH if path is None else path
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return _not_passed(f"cannot read {target.name}: {error}")
    return parse_calibration(document)
