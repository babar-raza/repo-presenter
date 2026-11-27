"""BL-895: the owner's exclusion of GIS .NET is data (data/portfolio_exclusions.json), applied by every counter
and enumeration of the portfolio, never a hard-coded name; the registry entry and every seal stay (R10, R14)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from repo_presenter.core.errors import ConfigError
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry.portfolio_exclusions import (
    DEFAULT_PATH, excluded_repositories, load_portfolio_exclusions, split_portfolio,
)
from repo_presenter.readme.review.calibration_status import Calibration

REPO = Path(__file__).resolve().parents[2]
GIS = "aspose-gis-foss/Aspose.GIS.FOSS-for-.Net"
_SPEC = importlib.util.spec_from_file_location("portfolio_delivery_count", REPO / "ops" / "checks" / "portfolio_delivery_count.py")
pdc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pdc
_SPEC.loader.exec_module(pdc)


def write(tmp_path, rows):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"schema_version": 1, "exclusions": rows}), encoding="utf-8")
    return p


ROW = {"repository": "o/r", "reason": "why", "decision_log": "docs/DECISION_LOG.md, entry", "owner_decision_date": "2026-11-23"}


def test_the_recorded_exclusion_names_the_repository_reason_log_entry_and_date() -> None:
    (e,) = load_portfolio_exclusions()
    assert e.repository == GIS and e.owner_decision_date == "2026-11-23"
    assert "GIS .NET excluded from the 40-cell portfolio" in e.decision_log and e.reason
    assert (REPO / "docs" / "DECISION_LOG.md").read_text(encoding="utf-8").count("GIS .NET excluded from the 40-cell portfolio") >= 1


def test_the_registry_keeps_the_entry_so_both_denominators_are_39_of_40() -> None:
    entries = load_registry(REPO / "data" / "registry.json").entries
    counted, applied = split_portfolio(entries)
    assert any(e.repository == GIS for e in entries)  # never deleted
    assert len([e for e in entries if e.active]) == 40
    assert len([e for e in counted if e.active]) == 39 and GIS not in {e.repository for e in counted}
    assert [a.repository for a in applied] == [GIS]


def test_split_keeps_order_and_accepts_strings_and_keys(tmp_path) -> None:
    p = write(tmp_path, [ROW])
    assert split_portfolio(["a", "o/r", "b"], path=p)[0] == ["a", "b"]
    assert split_portfolio([("o/r", 1), ("z", 2)], key=lambda t: t[0], path=p)[0] == [("z", 2)]
    assert split_portfolio(["a"], path=p)[1] == []


@pytest.mark.parametrize("bad", [
    [dict(ROW, reason="")], [{k: v for k, v in ROW.items() if k != "decision_log"}], [ROW, ROW], "nope",
])
def test_malformed_exclusions_fail_closed(tmp_path, bad) -> None:
    with pytest.raises(ConfigError):
        load_portfolio_exclusions(write(tmp_path, bad))


def test_missing_file_fails_closed(tmp_path) -> None:
    with pytest.raises(ConfigError):
        excluded_repositories(tmp_path / "absent.json")
    assert DEFAULT_PATH.exists()


def test_summary_reports_records_and_the_exclusion_without_touching_counts() -> None:
    cal = Calibration("PASSED", reviewer_logic_version="8", prompt_version="17")
    _, applied = split_portfolio([GIS])
    summary = pdc.summarize([], cal, None, applied)
    assert [r["repository"] for r in summary["excluded_repositories"]] == [GIS]
    assert summary["excluded_repositories"][0]["owner_decision_date"] == "2026-11-23"
    assert pdc.summarize([], cal, None)["excluded_repositories"] == []
    assert pdc.evaluate(summary, 25, None)  # the >= 25 gate still reads the counted rows


def test_every_portfolio_enumeration_goes_through_the_exclusion_list() -> None:
    for rel in ("ops/checks/portfolio_delivery_count.py", "ops/checks/delivery_funnel.py", "scripts/select_scheduled_cohort.py",
                "scripts/review_page/build.py", "src/repo_presenter/monitor/run.py", "src/repo_presenter/propose/portfolio_gate.py"):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "portfolio_exclusions" in text, rel
        assert "Aspose.GIS" not in text and "aspose-gis-foss" not in text, rel  # data-driven, no special case
