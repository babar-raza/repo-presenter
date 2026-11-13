"""BL-081: a plan never selects an example whose code prints a register-confirmed false line.

Hosted Lane R runs 43513031042 (Aspose.3D-FOSS-for-.NET) and 43516330798 (Aspose.Cells-FOSS-for-Python)
failed BC-18 on lines the renderer printed verbatim from the planned example facts
(``scene.Save("output.fbx", FileFormat.FBX7400Binary);``, ``style.font.color = "#FF0000"``); the S6
repairs could not reach them (no-op twice; an attempt to blank the example's heading unit). The
example code below is the real example facts' shape (3D .NET example:001 at 52b0f00e); the register
rows are the real committed ones.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.planning import (
    register_refuted_example_ids,
    section_conditions,
    selectable_example_ids,
)

THREED_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
REFUTED = (
    "using Aspose.ThreeD;\n\nvar scene = new Scene();\n"
    'scene.RootNode.CreateChildNode("Box", new Box(2, 2, 2));\n'
    'scene.Save("output.fbx", FileFormat.FBX7400Binary);\n'
)
GOOD = (
    "using Aspose.ThreeD;\n\nvar scene = new Scene();\n"
    'scene.Save("output.dae");\n'
)


@pytest.fixture
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )


def _facts(repository: str = THREED_NET) -> FactsDocument:
    return FactsDocument(
        repository,
        "5" * 40,
        (
            Fact("example:001", "example", REFUTED, (Evidence("tests/Quick.cs"),)),
            Fact("example:004", "example", GOOD, (Evidence("tests/Stream.cs"),)),
        ),
    )


def test_the_register_refuted_example_is_not_selectable(real_register: None) -> None:
    facts = _facts()
    assert register_refuted_example_ids(facts) == {"example:001"}
    assert selectable_example_ids(facts) == ["example:004"]
    conditions = section_conditions(facts)
    assert conditions["quick_start"] is True
    assert conditions["additional_examples"] is False


def test_negative_control_another_repository_selects_both(real_register: None) -> None:
    facts = _facts("org/other")
    assert register_refuted_example_ids(facts) == frozenset()
    assert selectable_example_ids(facts) == ["example:001", "example:004"]


def test_without_a_register_every_supported_example_is_selectable() -> None:
    assert selectable_example_ids(_facts()) == ["example:001", "example:004"]
