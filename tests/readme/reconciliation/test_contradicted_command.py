"""An inherited install command that a SUPPORTED fact contradicts may be omitted (mission section
7 step 3: contradicted content is removable with an evidence-backed explanation); every command
block short of that proof still cannot be omitted while install or build facts exist.

The positive case is the aspose-font-foss shape (``pip install "aspose-font[mcp]"`` against the
published distribution ``aspose-font-foss``); the negatives each remove exactly one element of the
proof.
"""

from __future__ import annotations

import copy
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    coverage_findings,
    normalize,
    placement_errors,
)

REPO = "org/Aspose.Widget-FOSS-for-Python"
COMMAND = "inherited_unit:010.code_block"
INSTALL = "install_command:pip"
IDENTITY = "package:name"


def _unit(text: str, uid: str = COMMAND) -> Fact:
    return Fact(uid, "inherited_unit", text, (Evidence("README.md", f"unit {uid}"),))


def _facts(
    block: str, *extra: Fact, install_polarity: str = "SUPPORTED"
) -> FactsDocument:
    base = (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        Fact(IDENTITY, "package", "aspose-widget-foss", (Evidence("x"),)),
        Fact(
            INSTALL,
            "install_command",
            "pip install aspose-widget-foss",
            (Evidence("x"),),
            polarity=install_polarity,
        ),
        Fact("package:version", "package", "1.0.0", (Evidence("x"),)),
        _unit(block),
    )
    return FactsDocument(REPO, "f" * 40, (*base, *extra))


def _omit(cited: list[str]) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": COMMAND,
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": cited,
                "rationale": "the command names a package the facts contradict",
            }
        ]
    }


WRONG = '```bash\npip install "aspose-widget[mcp]"\n```'
RIGHT = "```bash\npip install aspose-widget-foss\n```"
UNRELATED = "```bash\nmake test\n```"


def _after(block: str, cited: list[str], *extra: Fact, **kw: Any) -> dict[str, Any]:
    facts = _facts(block, *extra, **kw)
    output = _omit(list(cited))
    normalize(output, facts)
    return output["dispositions"][0]


def _refusals(block: str, cited: list[str], **kw: Any) -> list[str]:
    return placement_errors(_omit(list(cited)), _facts(block, **kw))


def test_a_command_contradicted_by_the_package_fact_stays_omitted_citing_the_fact() -> (
    None
):
    entry = _after(WRONG, [INSTALL])
    assert entry["disposition"] == "OMIT_UNSUPPORTED"
    assert entry["destination_section"] is None
    assert INSTALL in entry["fact_ids"]
    assert not any("never OMIT_UNSUPPORTED" in e for e in _refusals(WRONG, [INSTALL]))


def test_citing_the_package_identity_fact_is_equally_sufficient() -> None:
    assert _after(WRONG, [IDENTITY])["disposition"] == "OMIT_UNSUPPORTED"


def test_a_contradicted_omission_leaves_no_coverage_gap() -> None:
    assert coverage_findings(_omit([INSTALL]), _facts(WRONG)) == []


def test_negative_control_an_uncontradicted_install_command_is_still_not_omittable() -> (
    None
):
    entry = _after(RIGHT, [INSTALL])
    assert entry["disposition"] != "OMIT_UNSUPPORTED"
    assert any("never OMIT_UNSUPPORTED" in e for e in _refusals(RIGHT, [INSTALL]))


def test_negative_control_an_ordinary_command_block_is_still_not_omittable() -> None:
    entry = _after(UNRELATED, [INSTALL])
    assert entry["disposition"] != "OMIT_UNSUPPORTED"
    assert any("never OMIT_UNSUPPORTED" in e for e in _refusals(UNRELATED, [INSTALL]))


def test_negative_control_an_omission_citing_an_unrelated_fact_is_still_folded() -> (
    None
):
    entry = _after(WRONG, ["package:version"])
    assert entry["disposition"] != "OMIT_UNSUPPORTED"
    assert any(
        "never OMIT_UNSUPPORTED" in e for e in _refusals(WRONG, ["package:version"])
    )


def test_negative_control_an_omission_citing_nothing_is_still_folded() -> None:
    assert _after(WRONG, [])["disposition"] != "OMIT_UNSUPPORTED"


def test_negative_control_a_non_supported_install_fact_does_not_license_the_omission() -> (
    None
):
    build = Fact(
        "build_test_asset:make-test", "build_test_asset", "make test", (Evidence("x"),)
    )
    entry = _after(WRONG, [INSTALL], build, install_polarity="UNRESOLVED")
    assert entry["disposition"] != "OMIT_UNSUPPORTED"


def test_negative_control_without_a_supported_identity_there_is_no_proof() -> None:
    facts = _facts(WRONG)
    demoted = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            copy.replace(f, polarity="UNRESOLVED") if f.id == IDENTITY else f
            for f in facts.facts
        ),
    )
    output = _omit([IDENTITY])
    normalize(output, demoted)
    assert output["dispositions"][0]["disposition"] != "OMIT_UNSUPPORTED"


def test_the_contradicted_example_path_is_unchanged() -> None:
    """A code block whose EXAMPLE is CONTRADICTED is still omittable, and an UNRESOLVED example is
    still a deferral (``OMIT_UNRESOLVED_EXAMPLE``): the new proof touches command blocks only."""
    block = "```python\nimport widget\nwidget.run()\n```"

    def example(polarity: str) -> Fact:
        return Fact(
            "example:001",
            "example",
            "widget.run()",
            (Evidence("receipts.json", f"unit {COMMAND}"),),
            polarity=polarity,
        )

    contradicted = _facts(block, example("CONTRADICTED"))
    assert coverage_findings(_omit(["example:001"]), contradicted) == []
    unresolved = _facts(block, example("UNRESOLVED"))
    assert [
        g.reason for g in coverage_findings(_omit(["example:001"]), unresolved)
    ] == ["omit_unresolved_example"]
