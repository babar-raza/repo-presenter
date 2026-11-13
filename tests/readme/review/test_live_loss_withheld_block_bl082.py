"""BL-082: a kept code block printed without its register-confirmed false line is not "lost".

Hosted Lane R run 43516326802 (Aspose.Cells-FOSS-for-Java at c65329e7) was REJECTed with one
blocking finding, ``live_readme_loss`` "code block 'mvn compile'". The BC-18 repair had kept the
build block (``inherited_unit:054.code_block``, verbatim below) VERIFIED_PRESERVE citing the OPEN
register row ``mvn javadoc:javadoc   # generates docs/apidocs/index.html``, so the renderer printed
it without that line; the loss rule compared the live block whole and called it lost.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule
from repo_presenter.readme.validation.must_correct import open_finding_citations


@pytest.fixture(autouse=True)
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests are about the real committed register row, so they read it (the suite's
    default isolates every test from it, ``tests/conftest.py``)."""
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )

JAVA = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
BLOCK = (
    "```bash\nmvn compile\nmvn clean package\n"
    "mvn javadoc:javadoc   # generates docs/apidocs/index.html\n```"
)
WITHHELD = "```bash\nmvn compile\nmvn clean package\n```"
LIVE = f"# Aspose.Cells FOSS for Java\n\n## Building\n\n{BLOCK}\n"
CANDIDATE = f"# Aspose.Cells FOSS for Java\n\n## Building\n\n{WITHHELD}\n"


def _citation() -> str:
    rows = open_finding_citations(JAVA)
    return next(cid for cid, row in rows.items() if "mvn javadoc:javadoc" in row.quote)


def _facts() -> FactsDocument:
    return FactsDocument(
        JAVA,
        "c" * 40,
        (
            Fact("inherited_unit:054.code_block", "inherited_unit", BLOCK,
                 (Evidence("README.md", "lines 120-124; code_block; under Building"),)),
            Fact("build_test_asset:build-command", "build_test_asset", "mvn clean package",
                 (Evidence("pom.xml"),)),
        ),
    )


def _dispositions(fact_ids: list[str]) -> dict:
    return {"dispositions": [{
        "unit_id": "inherited_unit:054.code_block",
        "disposition": "VERIFIED_PRESERVE",
        "destination_section": "development_testing",
        "fact_ids": fact_ids,
        "rationale": "The findings register confirms the quoted text false.",
    }]}


def _lost(fact_ids: list[str], candidate: str = CANDIDATE) -> list[str]:
    findings = live_readme_loss_rule(LIVE, candidate, facts=_facts(), dispositions=_dispositions(fact_ids))
    return [f.message for f in findings]


def test_the_withheld_block_is_kept_not_lost() -> None:
    assert _lost(["build_test_asset:build-command", _citation()]) == []


def test_negative_control_without_the_citation_the_block_is_lost() -> None:
    assert any("code block 'mvn compile'" in m for m in _lost(["build_test_asset:build-command"]))


def test_negative_control_a_block_not_printed_at_all_is_lost() -> None:
    gone = "# Aspose.Cells FOSS for Java\n\n## Building\n\nSee the docs.\n"
    assert any("code block" in m for m in _lost(["build_test_asset:build-command", _citation()], gone))
