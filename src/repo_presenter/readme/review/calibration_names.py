"""The reviewer's calibration status names, in a leaf module so the verdict can use them and the
reader of the committed file (``calibration_status``) can import the verdict's logic version."""

from __future__ import annotations

NOT_PASSED = "NOT_PASSED"
PASSED = "PASSED"
PASSED_WITH_DECLARED_LIMITS = "PASSED_WITH_DECLARED_LIMITS"
STATUSES: tuple[str, ...] = (NOT_PASSED, PASSED, PASSED_WITH_DECLARED_LIMITS)
#: The statuses under which an ACCEPT is calibrated and a candidate may be eligible for a pull request.
PERMITTING: frozenset[str] = frozenset({PASSED, PASSED_WITH_DECLARED_LIMITS})
CALIBRATED = "calibrated"
UNCALIBRATED = "uncalibrated"


def label_for(status: str | None) -> str:
    """``calibrated`` only for a permitting status; anything else, including no status, is not."""
    return CALIBRATED if status in PERMITTING else UNCALIBRATED
