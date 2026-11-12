"""A heading parked or dropped without evidence while the content under it is kept follows that
content (Aspose.Email-FOSS-for-Cpp, hosted Lane R: ``017.heading`` "Install (Optional)" was
DEFER_UNRESOLVED while 018/019 were VERIFIED_PRESERVE into development_testing, so the heading
was printed nowhere and live_readme_loss refused it). Synthetic dispositions table."""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import normalize

_REPO = "aspose-email-foss/Aspose.Email-FOSS-for-Cpp"
_SECTION = "Aspose.Email FOSS for C++ > Install (Optional)"


def _unit(uid: str, text: str) -> Fact:
    return Fact(
        uid, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": _SECTION}
    )


def _facts(*extra: Fact) -> FactsDocument:
    units = (
        _unit("inherited_unit:016.paragraph", "Some earlier paragraph."),
        _unit("inherited_unit:017.heading", "## Install (Optional)"),
        _unit("inherited_unit:018.paragraph", "Build the library from source with CMake."),
        _unit("inherited_unit:019.code_block", "```bash\ncmake --build build\n```"),
        _unit("inherited_unit:020.heading", "## Next Section"),
        _unit("inherited_unit:021.paragraph", "Text of the next section."),
    )
    base = (
        Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
        Fact("build_test_asset:tests", "build_test_asset", "tests/", (Evidence("x"),)),
        Fact("install_command:cmake", "install_command", "cmake --build build", (Evidence("x"),)),
    )
    return FactsDocument(_REPO, "f" * 40, (*base, *units, *extra))


def _entry(unit: str, disposition: str, destination: str | None, fact_ids: list[str], why: str):
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": fact_ids,
        "rationale": why,
    }


def _table(heading: dict[str, Any]) -> dict[str, Any]:
    return {
        "dispositions": [
            _entry("inherited_unit:016.paragraph", "NON_CONTENT", None, [], "Not content."),
            heading,
            _entry(
                "inherited_unit:018.paragraph", "VERIFIED_PRESERVE", "development_testing",
                ["identity:repository"], "Kept as written.",
            ),
            _entry(
                "inherited_unit:019.code_block", "VERIFIED_PRESERVE", "development_testing",
                [], "Kept as written.",
            ),
            _entry("inherited_unit:020.heading", "SUPERSEDE_REDUNDANT", "installation", [], "x"),
            _entry("inherited_unit:021.paragraph", "DEFER_UNRESOLVED", None, [], "Undecided."),
        ]
    }


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


_DEFERRED = _entry(
    "inherited_unit:017.heading", "DEFER_UNRESOLVED", None, [],
    "Superseded by the installation section.",
)


def test_a_deferred_heading_follows_its_first_kept_body_unit() -> None:
    output = _table(dict(_DEFERRED))
    normalize(output, _facts())
    heading = _by_unit(output)["inherited_unit:017.heading"]
    assert heading["disposition"] == "VERIFIED_PRESERVE"
    assert heading["destination_section"] == "development_testing"
    assert heading["fact_ids"] == ["identity:repository"]
    assert "inherited_unit:018.paragraph" in heading["rationale"]
    assert "DEFER_UNRESOLVED" in heading["rationale"]  # the accounting stays traceable
    assert len(heading["rationale"]) <= 160


def test_a_moved_body_gives_a_move() -> None:
    output = _table(dict(_DEFERRED))
    output["dispositions"][2]["disposition"] = "VERIFIED_MOVE"
    normalize(output, _facts())
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "VERIFIED_MOVE"


def test_the_body_and_the_next_sections_units_are_untouched() -> None:
    output = _table(dict(_DEFERRED))
    normalize(output, _facts())
    after = _by_unit(output)
    assert after["inherited_unit:018.paragraph"]["disposition"] == "VERIFIED_PRESERVE"
    assert after["inherited_unit:018.paragraph"]["fact_ids"] == ["identity:repository"]
    assert after["inherited_unit:021.paragraph"]["disposition"] == "DEFER_UNRESOLVED"


def test_an_uncited_omitted_heading_with_no_identity_fact_also_follows() -> None:
    facts = _facts()
    no_identity = FactsDocument(
        facts.repository, facts.source_revision, tuple(f for f in facts.facts if f.kind != "identity")
    )
    heading = _entry("inherited_unit:017.heading", "OMIT_UNSUPPORTED", None, [], "Not needed.")
    output = _table(heading)
    normalize(output, no_identity)
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "VERIFIED_PRESERVE"


def test_a_heading_whose_body_is_all_dropped_stays_deferred() -> None:
    output = _table(dict(_DEFERRED))
    for entry in output["dispositions"][2:4]:
        entry["disposition"] = "NON_CONTENT"
        entry["destination_section"] = None
    normalize(output, _facts())
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "DEFER_UNRESOLVED"


def test_a_kept_unit_after_the_next_heading_does_not_count() -> None:
    output = _table(dict(_DEFERRED))
    for entry in output["dispositions"][2:4]:
        entry["disposition"] = "NON_CONTENT"
        entry["destination_section"] = None
    output["dispositions"][5] = _entry(
        "inherited_unit:021.paragraph", "VERIFIED_PRESERVE", "development_testing", [], "Kept."
    )
    normalize(output, _facts())
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "DEFER_UNRESOLVED"


def test_a_heading_citing_a_contradicted_fact_is_left_alone() -> None:
    bad = Fact("package:old", "package", "old-name", (Evidence("x"),), polarity="CONTRADICTED")
    heading = dict(_DEFERRED, fact_ids=["package:old"])
    output = _table(heading)
    normalize(output, _facts(bad))
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "DEFER_UNRESOLVED"


def test_a_heading_already_accounted_with_evidence_is_left_alone() -> None:
    heading = _entry(
        "inherited_unit:017.heading", "SUPERSEDE_REDUNDANT", "installation",
        ["identity:repository"], "Installation prints it.",
    )
    output = _table(heading)
    normalize(output, _facts())
    assert _by_unit(output)["inherited_unit:017.heading"]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_non_heading_deferred_unit_is_never_folded_by_this_rule() -> None:
    output = _table(dict(_DEFERRED))
    normalize(output, _facts())
    assert _by_unit(output)["inherited_unit:021.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
