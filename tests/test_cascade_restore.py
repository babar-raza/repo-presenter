"""TC-019c: the cascade applies the zero-call restore (``readme.repair.restore_units``) when the
settled candidate's only blocking failures are BC-05/BC-17, instead of dying at the seal gate with
~80 paid calls spent and no candidate (Email-FOSS-for-Python, first batch run, 2026-11-09).

Real cascade over the fixture ``tests/test_cascade.py`` defines, through a fake client with scripted
replies; the model review is replaced by a recorder, so these tests make no provider call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict
from repo_presenter.readme.validation.blocking import blocking_failures
from tests.test_cascade import README
from tests.test_cascade_s9 import _first_replies, _Run, _fixed_git_revision  # noqa: F401

GUIDE = "https://widget.example.org/guide"
README_WITH_LINK = README + f"\nRead the [full guide]({GUIDE}) for everything else.\n"
LINK_UNIT = "inherited_unit:007.paragraph"


class _ReachedReview(Exception):
    pass


#: The shared fixture (a synthetic widget with no LICENSE file, an unexecuted example and an
#: unevidenced pip install) fails BC-02/BC-03/BC-06 on its own, which has nothing to do with this
#: card; ``tests/test_cascade_s10.py`` replaces the same gate for the same reason. Every other
#: check, BC-17 included, is the real one.
_FIXTURE_ONLY = frozenset({"BC-02", "BC-03", "BC-06"})
_real_blocking_failures = blocking_failures


def _blocking_without_fixture_noise(validation: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in _real_blocking_failures(validation) if c["id"] not in _FIXTURE_ONLY]


def _reconciliation(link_disposition: str, destination: str | None) -> dict[str, Any]:
    reply = _first_replies()[1]
    reply = json.loads(json.dumps(reply))
    reply["dispositions"].append(
        {
            "unit_id": LINK_UNIT, "disposition": link_disposition,
            "destination_section": destination, "fact_ids": ["package:name"],
            "rationale": "the paragraph points at a guide",
        }
    )
    return reply


def _run_to_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_disposition: str, destination: str | None
) -> tuple[_Run, dict[str, Any]]:
    seen: dict[str, Any] = {}

    def record_review(**kwargs: Any) -> Any:
        seen["blocking"] = [
            check["id"] for check in _blocking_without_fixture_noise(kwargs["validation"])
        ]
        seen["readme"] = kwargs["candidate_readme"]
        raise _ReachedReview

    monkeypatch.setattr(cascade_module, "review_with_model", record_review)
    monkeypatch.setattr(cascade_module, "blocking_failures", _blocking_without_fixture_noise)
    # The fixture's own deterministic verdict is REJECT (heading losses in deterministic sections),
    # as tests/test_cascade_s10.py notes; BC-17, the check under test, is not part of that verdict.
    monkeypatch.setattr(cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(()))
    run = _Run(tmp_path, monkeypatch, README_WITH_LINK)
    run.script(_first_replies(reconciliation=_reconciliation(link_disposition, destination)))
    try:
        run.cascade(max_rounds=1)
    except _ReachedReview:
        seen["reached"] = True
    return run, seen


def test_a_candidate_that_loses_only_a_link_the_published_readme_prints_reaches_review_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, seen = _run_to_review(tmp_path, monkeypatch, "DEFER_UNRESOLVED", None)
    assert seen.get("reached") is True, "the cascade stopped before the model review"
    assert seen["blocking"] == []
    assert GUIDE in seen["readme"]
    restored = run.json("restored_units.json")["restored"]
    assert [change["unit_id"] for change in restored] == [LINK_UNIT]
    assert restored[0]["was"].startswith("DEFER_UNRESOLVED") and "VERIFIED_PRESERVE" in restored[0]["now"]
    assert next(e for e in run.json("dispositions.json")["dispositions"] if e["unit_id"] == LINK_UNIT)[
        "disposition"
    ] == "VERIFIED_PRESERVE"
    assert GUIDE in (run.out / "README.coherent.md").read_text(encoding="utf-8")


def test_negative_control_without_the_restore_the_same_run_is_stopped_at_the_blocking_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cascade_module, "restore_lost_units", lambda d, f, u, h, i=None, **k: (d, []))
    run, seen = _run_to_review(tmp_path, monkeypatch, "DEFER_UNRESOLVED", None)
    assert seen.get("reached") is None  # blocking checks still failed, so no model review was made
    assert "BC-17" in {c["id"] for c in _blocking_without_fixture_noise(run.json("validation.json"))}
    assert not (run.out / "restored_units.json").exists()
