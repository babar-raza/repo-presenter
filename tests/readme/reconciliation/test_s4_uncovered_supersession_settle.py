"""BL-420: the last S4 ask settles a unit the check itself refuses as ``uncovered_supersession``.

Real data: aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp, hosted run 44665731411 (2026-11-20).
Unit 033.code_block, a PowerShell ``Install-Package`` snippet from the maintainers' "Install From
NuGet on Windows", was answered SUPERSEDE_REDUNDANT into ``installation`` (which prints the
verified CMake command) three times; the check named the lever each time and the whole candidate
died on the job error. The rejection text below is the run log's own.
"""

from __future__ import annotations

import json

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    _reconciliation_merge,
    _settle_unresolved,
    reconcile_checks,
)

REPO = "aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp"
SECTION = "Aspose.Slides FOSS for C++ > Installation > Install From NuGet on Windows"
U33 = "inherited_unit:033.code_block"
U34 = "inherited_unit:034.paragraph"
NUGET = "```powershell\nInstall-Package Aspose.Slides.Cpp.FOSS\n```"
LOGGED = (
    "inherited_unit:033.code_block: uncovered_supersession: SUPERSEDE_REDUNDANT treats "
    "installation as carrying this code block, but installation prints the verified install "
    "command, not 'install-package aspose.slides.cpp.foss'."
)


def _entry(unit, disposition, destination=None, fact_ids=(), why="because") -> dict:
    return {
        "unit_id": unit, "disposition": disposition, "destination_section": destination,
        "fact_ids": list(fact_ids), "rationale": why,
    }


def _unit(unit: str, text: str, section: str = SECTION) -> Fact:
    return Fact(unit, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": section})


def _facts(*extra: Fact, text: str = NUGET) -> FactsDocument:
    return FactsDocument(REPO, "f" * 40, (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "cpp", (Evidence("x"),)),
        Fact("package:name", "package", "Aspose.Slides.Cpp.FOSS", (Evidence("x"),)),
        Fact("install_command:cmake", "install_command", "cmake -B build", (Evidence("CMakeLists.txt"),)),
        Fact("build_test_asset:ctest", "build_test_asset", "ctest", (Evidence("CMakeLists.txt"),)),
        _unit(U33, text),
        *extra,
    ))


def _logged_reply(unit=U33, cited=("install_command:cmake",)) -> str:
    return json.dumps({"dispositions": [_entry(unit, "SUPERSEDE_REDUNDANT", "installation", cited,
                                                "Superseded by the installation section.")]})


def test_the_logged_rejection_is_reproduced_from_the_logged_reply() -> None:
    errors = reconcile_checks(json.loads(_logged_reply()), _facts())
    assert any(e.startswith(LOGGED) for e in errors), errors


def test_the_unit_is_kept_in_the_section_the_check_names_after_the_last_ask() -> None:
    facts = _facts()
    settled = json.loads(_settle_unresolved(_logged_reply(), [U33], facts))
    entry = settled["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "development_testing"
    assert entry["fact_ids"] == ["install_command:cmake"]
    assert entry["rationale"].startswith("Kept as the maintainers wrote it")
    assert "superseded by a section that does not carry it" in entry["rationale"]
    assert reconcile_checks(json.loads(json.dumps(settled)), facts) == []  # the real checks accept it


def test_the_narrowed_merge_path_settles_the_same_way() -> None:
    facts = _facts()
    base = json.dumps({"dispositions": [_entry(U33, "SUPERSEDE_REDUNDANT", "installation", ["install_command:cmake"])]})
    merged = _reconciliation_merge(base, _logged_reply(), [U33])
    assert json.loads(_settle_unresolved(merged, [U33], facts))["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_unit_that_cannot_be_placed_fails_closed() -> None:
    facts = _facts(text=NUGET)
    # no holdable section exists for a unit under a heading no section can hold: nothing to name.
    import repo_presenter.readme.reconciliation.dispositions as d
    original = d.nearest_holdable
    d.nearest_holdable = lambda *a, **k: None
    try:
        assert _settle_unresolved(_logged_reply(), [U33], facts) == _logged_reply()
    finally:
        d.nearest_holdable = original


def test_a_unit_citing_a_contradicted_fact_is_left_alone() -> None:
    bad = Fact("install_command:nuget", "install_command", "Install-Package x", (Evidence("x"),), polarity="CONTRADICTED")
    facts = _facts(bad)
    reply = _logged_reply(cited=("install_command:nuget",))
    assert json.loads(_settle_unresolved(reply, [U33], facts))["dispositions"][0]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_unit_not_asked_about_is_never_touched() -> None:
    assert _settle_unresolved(_logged_reply(), [U34], _facts()) == _logged_reply()


def test_a_passing_reply_is_returned_untouched() -> None:
    ok = json.dumps({"dispositions": [_entry(U33, "VERIFIED_PRESERVE", "development_testing", ["install_command:cmake"])]})
    assert _settle_unresolved(ok, [U33], _facts()) == ok


def test_a_first_pass_supersession_is_still_refused_loudly_not_settled_by_the_checks() -> None:
    """The checks themselves still refuse (the sibling regression guard): only the final-ask settle
    applies the lever."""
    errors = reconcile_checks(json.loads(_logged_reply()), _facts())
    assert any("uncovered_supersession" in e for e in errors)
