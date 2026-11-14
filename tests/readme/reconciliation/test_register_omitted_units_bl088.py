"""BL-088 (supervisor decision 2026-11-14, audit O4): an inherited example block with no printable
form, because the findings register refutes a line of it, is omitted citing that register row, and
every reader accepts that one disposition.

Real data: Aspose.3D-FOSS-for-.NET at 52b0f00ebf28 (sealed Lane R bundle 03b940a46f7b; hosted run
43529876835 at main 0655d41). ``024.code_block`` saves to ``FileFormat.FBX7400Binary`` and
``028.code_block`` to ``FileFormat.WavefrontOBJ``; both lines are OPEN register rows
(``data/readme_findings.json``), so BL-081 makes ``example:001`` / ``example:002`` unselectable.
Kept, the blocks failed disposition_coverage ("kept but not printed"); dropped uncited, they failed
live_readme_loss.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.parity_gate import disposition_is_non_loss
from repo_presenter.readme.reconciliation.dispositions import (
    _fold_register_omitted_units,
    coverage_findings,
)
from repo_presenter.readme.review.independent_reviewer import (
    disposition_coverage_rule,
    live_readme_loss_rule,
)
from repo_presenter.readme.validation.must_correct import (
    REGISTER_OMITTED_RATIONALE,
    is_register_omission,
)

THREED_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
LEAD_1 = "Build a scene from a primitive, assign a material, and save it to FBX:"
BLOCK_1 = (
    "```csharp\nusing Aspose.ThreeD;\nusing Aspose.ThreeD.Entities;\nusing Aspose.ThreeD.Shading;\n\n"
    "// Create a new scene and add a box primitive to the root node\nvar scene = new Scene();\n"
    'var material = new LambertMaterial("Body")\n{\n    DiffuseColor = new Vector3(0.6, 0.6, 0.6),\n};\n'
    'scene.RootNode.CreateChildNode("Box", new Box(2, 2, 2), material);\n\n// Save to FBX\n'
    'scene.Save("output.fbx", FileFormat.FBX7400Binary);\n```'
)
LEAD_2 = "Load an existing glTF scene and re-save it as an OBJ:"
BLOCK_2 = (
    '```csharp\nusing Aspose.ThreeD;\n\nvar scene = Scene.FromFile("input.gltf");\n'
    'scene.Save("output.obj", FileFormat.WavefrontOBJ);\n```'
)


@pytest.fixture(autouse=True)
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )


def _unit(uid: str, text: str) -> Fact:
    return Fact(uid, "inherited_unit", text, (Evidence("README.md", "lines 1-9; unit"),),
                attributes={"section": "Aspose.3D FOSS for .NET > Quick Start"})


def _example(eid: str, block: str, unit: str) -> Fact:
    code = "\n".join(block.splitlines()[1:-1])
    return Fact(eid, "example", code, (Evidence("README.md", f"lines 1-9; csharp fence; unit {unit}"),))


def _facts(repository: str = THREED_NET) -> FactsDocument:
    return FactsDocument(
        repository,
        "52b0f00ebf28a0b4173921725ff170685ec2c502",
        (
            _unit("inherited_unit:023.paragraph", LEAD_1),
            _unit("inherited_unit:024.code_block", BLOCK_1),
            _unit("inherited_unit:027.paragraph", LEAD_2),
            _unit("inherited_unit:028.code_block", BLOCK_2),
            _example("example:001", BLOCK_1, "inherited_unit:024.code_block"),
            _example("example:002", BLOCK_2, "inherited_unit:028.code_block"),
        ),
    )


def _sealed() -> dict[str, Any]:
    """The sealed bundle's own four dispositions."""
    return {
        "dispositions": [
            {"unit_id": "inherited_unit:023.paragraph", "disposition": "SUPERSEDE_REDUNDANT",
             "destination_section": "quick_start", "fact_ids": ["example:001"],
             "rationale": "Lead-in of the block that follows: carried together with it, never alone."},
            {"unit_id": "inherited_unit:024.code_block", "disposition": "SUPERSEDE_REDUNDANT",
             "destination_section": "quick_start", "fact_ids": ["example:001"],
             "rationale": "Printed by the example section from the verified example fact it cites."},
            {"unit_id": "inherited_unit:027.paragraph", "disposition": "SUPERSEDE_REDUNDANT",
             "destination_section": "additional_examples", "fact_ids": ["example:002"],
             "rationale": "Lead-in of the block that follows: carried together with it, never alone."},
            {"unit_id": "inherited_unit:028.code_block", "disposition": "VERIFIED_PRESERVE",
             "destination_section": "additional_examples", "fact_ids": ["example:002"],
             "rationale": "The code block matches the verified example fact and is supported."},
        ]
    }


def test_the_unprintable_blocks_and_their_lead_ins_are_omitted_citing_the_register() -> None:
    output = _sealed()
    _fold_register_omitted_units(output, _facts())
    rows = {e["unit_id"]: e for e in output["dispositions"]}
    for unit in ("024.code_block", "028.code_block", "023.paragraph", "027.paragraph"):
        entry = rows[f"inherited_unit:{unit}"]
        assert entry["disposition"] == "OMIT_UNSUPPORTED", unit
        assert entry["destination_section"] is None
        assert entry["fact_ids"] and all(f.startswith("finding:") for f in entry["fact_ids"])
        assert entry["rationale"].startswith(REGISTER_OMITTED_RATIONALE)
        assert is_register_omission(entry)


def test_every_reader_accepts_the_omission() -> None:
    facts = _facts()
    output = _sealed()
    _fold_register_omitted_units(output, facts)
    live = "\n\n".join([LEAD_1, BLOCK_1, LEAD_2, BLOCK_2])
    # BC-17: the parity gate's non-loss rule
    assert all(disposition_is_non_loss(e, {}) for e in output["dispositions"])
    # live_readme_loss: both fences are accounted for although the candidate prints neither
    assert live_readme_loss_rule(live, "# Title\n", facts=facts, dispositions=output) == []
    # disposition_coverage: nothing is kept, so nothing is "kept but not printed"
    assert disposition_coverage_rule("# Title\n", facts=facts, dispositions=output) == []
    # S4's own coverage audit does not call it a verified example omitted
    assert coverage_findings(output, facts) == []


def test_negative_controls() -> None:
    # another repository: no register row applies, nothing changes
    output = _sealed()
    _fold_register_omitted_units(output, _facts("other/repo"))
    assert output == _sealed()
    # without the fold, the kept block is "kept but not printed" and the omission is a loss
    facts = _facts()
    assert disposition_coverage_rule("# Title\n", facts=facts, dispositions=_sealed())
    uncited = copy.deepcopy(_sealed())
    for entry in uncited["dispositions"]:
        entry.update(disposition="OMIT_UNSUPPORTED", destination_section=None,
                     rationale="Omitted.")
    assert not any(disposition_is_non_loss(e, {}) for e in uncited["dispositions"])
    # the marker alone is not enough: a register-omission rationale citing no register row
    forged = {"disposition": "OMIT_UNSUPPORTED", "fact_ids": ["example:001"],
              "rationale": REGISTER_OMITTED_RATIONALE + "x"}
    assert not is_register_omission(forged)
