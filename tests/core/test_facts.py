import json
from pathlib import Path

from repo_presenter.core.facts import (
    Evidence,
    Fact,
    FactsDocument,
    fact_id,
    read_facts,
    write_facts,
)


def test_fact_id_and_roundtrip(tmp_path: Path) -> None:
    f = Fact(
        id=fact_id("package", "aspose-3d-foss"),
        kind="package",
        value="aspose-3d-foss",
        evidence=(Evidence(path="setup.py"),),
    )
    doc = FactsDocument(repository="x/y", source_revision="abc123", facts=(f,))
    path = tmp_path / "facts.json"
    sha = write_facts(doc, path)
    assert sha
    loaded = read_facts(path)
    assert loaded.facts[0].id == f.id
    assert loaded.repository == "x/y"


def test_duplicate_ids_rejected() -> None:
    f = Fact(
        id=fact_id("package", "x"),
        kind="package",
        value="x",
        evidence=(Evidence(path="a"),),
    )
    try:
        FactsDocument(repository="r", source_revision="s", facts=(f, f))
        assert False, "should have raised"
    except ValueError:
        pass
