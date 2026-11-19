"""BL-310: a restore re-judges the candidate under the plan the register correction produced.

Measured on the Aspose.PDF-FOSS-for-Java Lane R seal (zero provider calls): with the registered
false capability sentence withheld (BL-210, ``corrected_authored``) the dry re-certification judged
the corrected plan, but the restore re-derived the plan from the SEALED one, so the capability slot
the corrected units no longer fill came back and BC-04 failed the restored candidate:

    BC-04: key_capabilities: units must fill exactly these slots once each: capability:1 ...
    capability:6; got capability:1, capability:2, capability:3, capability:4, capability:5

The restore must judge the corrected plan, with the link backstop re-applied to the restored
dispositions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repo_presenter import recertify
from repo_presenter.core.candidates import LANE_R
from repo_presenter.readme.validation import blocking
from repo_presenter.readme.validation.failures import Failure
from repo_presenter.recertify import OUTCOME_RECERTIFIED
from tests.test_recertify import entry, no_provider, seal_lane_r, source  # noqa: F401 -- fixtures

UNIT = "inherited_unit:014.paragraph"
KEPT = {"VERIFIED_PRESERVE", "VERIFIED_MOVE", "PRESERVE_ATTRIBUTED"}


def test_a_restore_judges_the_register_corrected_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_provider: list[str]  # noqa: F811
) -> None:
    bundle = seal_lane_r(tmp_path, monkeypatch, renderer="35")

    def lost_unless_kept(candidate: Any) -> list[Failure]:
        row = next(e for e in candidate.dispositions["dispositions"] if e["unit_id"] == UNIT)
        if row["disposition"] in KEPT:
            return []
        return [
            Failure(
                "RECONCILING",
                f"{UNIT} holds h2 'Examples', which the published README prints and this candidate "
                "loses (section_coverage): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE)",
                unit=UNIT,
            )
        ]

    judges = dict(blocking.JUDGES)
    judges["BC-17"] = lost_unless_kept
    monkeypatch.setattr(blocking, "JUDGES", judges)

    # The register correction, stood in for: it marks the plan it returns. Called on the units as
    # they were before the correction (the corrected units no longer hold the false quote).
    seen_units: list[Any] = []

    def correction(plan: Any, units: Any, *_args: Any, **_kwargs: Any) -> tuple[dict, dict]:
        seen_units.append(units)
        return {**dict(plan), "register_corrected": True}, dict(units)

    monkeypatch.setattr(recertify, "corrected_authored", correction)
    judged: list[dict[str, Any]] = []
    evaluate = recertify._evaluate_lane_r

    def spy(*args: Any, **kwargs: Any) -> Any:
        judged.append(dict(kwargs.get("plan_override") or {}))
        return evaluate(*args, **kwargs)

    monkeypatch.setattr(recertify, "_evaluate_lane_r", spy)

    common = dict(entry=entry(), source=source(), current_version_set="current", seal_commit="c" * 40)
    rec = recertify.recertify_bundle(bundle, LANE_R, restore=True, **common)
    assert rec.outcome == OUTCOME_RECERTIFIED, rec.details
    assert len(judged) >= 2, "the restore re-judged nothing"
    # before the fix the second judgement ran under a plan re-derived from the sealed one
    assert all(plan.get("register_corrected") for plan in judged), judged
    assert no_provider == []
