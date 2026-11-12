"""S9 accounting of a kept inherited badge row (readme/repair/accounting.py ``_badge_row``).

Real text: the two badge rows are inherited_unit:001.badge_row and :003.badge_row of
aspose-font-foss/Aspose.Font-FOSS-for-Python, whose first generation run (2026-11-09, batch 1) was
REJECTed by the independent review with ``disposition_coverage`` because S4 kept both
(VERIFIED_PRESERVE) although the renderer never prints an inherited badge row as written.

Two cases: (1) every link of the row IS printed in the README (by the renderer's own badges), so
the kept row is redundant and is accounted SUPERSEDE_REDUNDANT into badges, citing the facts that
section renders; (2) a link of the row is NOT printed anywhere (the Font run's actual state): that
is R2 content loss, not redundancy, and the row is left for the reviewer to refuse.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.validation.failures import Candidate

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-font-foss/Aspose.Font-FOSS-for-Python",
        "family": "font",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
REVISION = "c" * 40
PYPI = "https://pypi.org/project/aspose-font-foss/"
ROW_PYPI = f"[![PyPI version](https://img.shields.io/pypi/v/aspose-font-foss.svg)]({PYPI})"
ROW_BANNER = (
    "[![Aspose.Font FOSS for Python](https://raw.githubusercontent.com/aspose-font-foss/"
    "Aspose.Font-FOSS-for-Python/main/docs/images/banner.png)]"
    "(https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python)"
)


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md"),), polarity="SUPPORTED")


def _facts() -> FactsDocument:
    return FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            _fact("identity:repository", "identity", ENTRY.repository),
            _fact("identity:revision", "identity", REVISION),
            _fact("package:name", "package", "aspose-font-foss"),
            _fact("license:spdx", "license", "MIT"),
            _fact("link_target:001", "link_target", PYPI),
            _fact("inherited_unit:003.badge_row", "inherited_unit", ROW_PYPI),
            _fact("inherited_unit:001.badge_row", "inherited_unit", ROW_BANNER),
        ),
    )


def _plan() -> dict[str, Any]:
    names = ["identity", "badges", "banner", "opening", "license"]
    return {
        "sections": [{"section_id": n, "include": True, "reason": "r"} for n in names],
        "core_capabilities": [],
        "at_a_glance": {},
        "quick_start_example_id": None,
        "additional_example_ids": [],
        "api_hubs": [],
        "material_limitations": [],
        "links": [],
        "deviations": [],
    }


def _dispositions() -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": unit,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "opening",
                "fact_ids": ["link_target:001"],
                "rationale": "kept",
            }
            for unit in ("inherited_unit:001.badge_row", "inherited_unit:003.badge_row")
        ]
    }


def _candidate(readme: str) -> Candidate:
    return Candidate(
        ENTRY, _facts(), _plan(), {"units": [], "omitted": []}, _dispositions(), readme, None,
        REVISION, None, (), [],
    )


def _by_unit(dispositions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["unit_id"].split(":")[1]: e for e in dispositions["dispositions"]}


def test_a_kept_badge_row_whose_links_are_all_printed_is_accounted_into_badges() -> None:
    readme = (
        "# Aspose.Font FOSS for Python\n\n"
        f"[![PyPI](https://img.shields.io/pypi/v/aspose-font-foss.svg)]({PYPI})\n"
        "[![Aspose.Font FOSS for Python](https://raw.githubusercontent.com/aspose-font-foss/"
        "Aspose.Font-FOSS-for-Python/main/docs/images/banner.png)]"
        "(https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python)\n"
    )
    settled, accounted = account_unprinted_units(_candidate(readme))
    rows = _by_unit(settled)
    # 003's row is not printed as written (the renderer's PyPI badge has other alt text) but every
    # link it carries is printed: redundant, accounted into badges from the facts that section
    # renders. 001's row IS printed verbatim, so it needs no accounting and is left exactly as is.
    assert [a.unit_id for a in accounted] == ["inherited_unit:003.badge_row"]
    assert rows["003.badge_row"]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert rows["003.badge_row"]["destination_section"] == "badges"
    assert rows["003.badge_row"]["fact_ids"]  # a supersession is only counted when a fact backs it
    assert rows["001.badge_row"]["disposition"] == "VERIFIED_PRESERVE"


def test_a_kept_badge_row_with_a_link_the_readme_lost_is_left_for_the_reviewer() -> None:
    # The Font run's actual state: the maintainers' banner image and PyPI links are not printed.
    readme = (
        "# Aspose.Font FOSS for Python\n\n"
        "[![PyPI](https://img.shields.io/pypi/v/aspose-font-foss.svg)](https://example.org/other)\n"
    )
    settled, accounted = account_unprinted_units(_candidate(readme))
    rows = _by_unit(settled)
    assert not any(a.unit_id.endswith("badge_row") for a in accounted)
    assert rows["001.badge_row"]["disposition"] == "VERIFIED_PRESERVE"
    assert rows["003.badge_row"]["disposition"] == "VERIFIED_PRESERVE"


def test_the_input_dispositions_are_never_mutated() -> None:
    readme = f"[![PyPI](https://img.shields.io/pypi/v/aspose-font-foss.svg)]({PYPI})\n"
    candidate = _candidate(readme)
    before = repr(candidate.dispositions)
    account_unprinted_units(candidate)
    assert repr(candidate.dispositions) == before
