"""BL-540: an authored opening that only restates the inherited paragraph a zero-call restore printed
beside it is answered by the recorded degrade, not left to fail the whole candidate.

Hosted Lane R OCR .NET refresh (run 44775277577): the S9 loop refused the restore of the inherited
opening paragraph (``require_clean_review``: the restored pair held a blocking
``duplicate_opening_paragraph`` finding), 0 defects were repairable, the final restore applied it all
the same, and the degrade had no flag for a deterministic finding (``degrade: nothing kept (0 flag(s)
tried)``), so the candidate ended REJECT with the paragraph and its paraphrase printed together. The
degrade now carries that finding as a flag: the authored opening becomes the sentence the format facts
state (BL-220/BL-350), the inherited paragraph is untouched (R14). Negative controls: an opening with new
content, an opening that cites an inherited unit, and facts that state no format are never touched.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import repo_presenter.cascade as cascade_module
from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.validation.must_correct import (
    DEGRADE_RECORDS_KEY,
    duplicate_opening_flags,
)
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions
from tests.readme.validation.test_degrade_claims_bl240 import _facts_with, _World

PRESERVED = (
    "Aspose.3D FOSS for Python is a free, open-source library for Python 3.10 and later. It builds "
    "a scene graph from a model file and hands back every node it found. The parsers are embedded "
    "in the package and run locally."
)
PARAPHRASE = (
    "Aspose.3D FOSS for Python builds a scene graph from a model file and hands back every node it "
    "found, running locally."
)
NEW_CONTENT = "It also validates every mesh against the glTF schema before the file is written."
INHERITED = "inherited_unit:004.paragraph"


def _world(tmp_path: Path, opening: str, *, cite: str | None = None, drop_formats: bool = False) -> _World:
    facts = _facts_with(
        Fact(INHERITED, "inherited_unit", PRESERVED, (Evidence("README.md"),), polarity="SUPPORTED"),
        drop=("format:output.glb", "format:input.obj") if drop_formats else (),
    )
    units = copy.deepcopy(UNITS)
    unit = next(u for u in units["units"] if u["slot"] == "opening")
    unit["text"] = opening
    if cite:
        unit["fact_ids"] = [cite]
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        {"unit_id": INHERITED, "disposition": "VERIFIED_PRESERVE", "destination_section": "opening",
         "fact_ids": [], "rationale": "kept as written (BC-17 restore)"}
    )
    return _World(facts, units, dispositions, tmp=tmp_path)


def _degrade(world: _World, tmp_path: Path) -> Any:
    settled = world.settled()
    return cascade_module._degrade_settled(
        settled, settled.verdict, entry=ENTRY, document=world.facts, investigation={},
        tree_paths=[], original="", out_dir=tmp_path,
    )


def _rules(world: _World) -> set[str]:
    return {f.rule for f in world.judge()[1].blocking_findings}


def test_the_flag_is_read_from_the_deterministic_finding() -> None:
    world = _world(Path("."), PARAPHRASE)
    [flag] = duplicate_opening_flags(world.judge()[1].blocking_findings)
    assert flag.check == "duplicate_opening_paragraph" and flag.quote == PARAPHRASE


def test_a_restated_opening_prints_the_format_facts_sentence_and_the_paragraph_stays(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path, PARAPHRASE)
    assert "duplicate_opening_paragraph" in _rules(world) and PARAPHRASE in world.readme
    degraded = _degrade(world, tmp_path)
    assert degraded is not None
    assert not [f for f in degraded.verdict.blocking_findings if f.rule == "duplicate_opening_paragraph"]
    readme = degraded.composed.readme
    assert PARAPHRASE not in readme and PRESERVED in readme  # R14: the maintainers' paragraph is intact
    assert "Aspose.3D FOSS for Python reads OBJ files and writes GLB files." in readme
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "opening_fact_true" and record["findings"] == ["duplicate_opening_paragraph"]


def test_an_opening_that_adds_new_content_is_never_touched(tmp_path: Path) -> None:
    world = _world(tmp_path, NEW_CONTENT)
    assert "duplicate_opening_paragraph" not in _rules(world)
    assert _degrade(world, tmp_path) is None


def test_an_opening_that_cites_an_inherited_unit_is_not_replaced(tmp_path: Path) -> None:
    world = _world(tmp_path, PARAPHRASE, cite="inherited_unit:001.heading")
    assert _degrade(world, tmp_path) is None


def test_nothing_is_invented_when_the_facts_state_no_format(tmp_path: Path) -> None:
    """BL-580 supersedes "left for the checks": with no fact-true sentence the opening that adds nothing the
    maintainers' paragraph lacks is released for it on the record (hosted HTML Python 44916810423); no text is
    invented and the paragraph is intact."""
    world = _world(tmp_path, PARAPHRASE, drop_formats=True)
    degraded = _degrade(world, tmp_path)
    assert degraded is not None
    assert not [f for f in degraded.verdict.blocking_findings if f.rule == "duplicate_opening_paragraph"]
    readme = degraded.composed.readme
    assert PARAPHRASE not in readme and PRESERVED in readme
    assert not [u for u in degraded.composed.coherent_units["units"] if u["slot"] == "opening"]
    assert degraded.composed.coherent_units["omitted"][-1]["section"] == "opening"
    [record] = degraded.composed.coherent_units[DEGRADE_RECORDS_KEY]
    assert record["action"] == "opening_released" and record["rule"] == "BL-580"


def test_an_opening_with_new_content_is_never_released_without_a_format(tmp_path: Path) -> None:
    world = _world(tmp_path, NEW_CONTENT, drop_formats=True)
    assert _degrade(world, tmp_path) is None
