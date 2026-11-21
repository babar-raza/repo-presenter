"""BL-581 / BL-582: the two shapes behind hosted PSD Java refresh run 44920305486 (and HTML Python
44916810423, 3D TypeScript: ``llm:factuality|authored_unit|api_reference``).

BL-581: the API Reference's authored ``intro`` has no renderer fallback, so a whole-text model finding
(``unsupported_claim``) was "refused" by the degrade and the candidate ended REJECT. The degrade now releases
the slot on the record; the renderer prints the verified type count and the Core API table alone.
Negative controls: an intro the review does not fault, and an intro that cites an inherited unit, are not
released by this lever.

BL-582: a Documentation & Resources item whose description is the renderer's own fact-true one for the
link's target ("On github.com.") is not an author's claim: it is not shown to the reviewer.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from typing import Any

import repo_presenter.cascade as cascade_module
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.scope import reviewable_lines, shown_text
from repo_presenter.readme.validation.blocking import blocking_failures
from repo_presenter.readme.validation.must_correct import DEGRADE_RECORDS_KEY
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions
from tests.readme.validation.test_degrade_claims_bl240 import _facts_with, _World

INTRO = (
    "The `Scene` class serves as the main entry point for reading and writing scene files, and it exposes "
    "nodes through the `Node` class. `Mesh` and `SceneError` support geometry and load error handling."
)


def _world(tmp_path: Path, intro: str = INTRO, *, cite: str | None = None) -> _World:
    units = copy.deepcopy(UNITS)
    unit = next(u for u in units["units"] if u["section"] == "api_reference" and u["slot"] == "intro")
    unit["text"] = intro
    if cite:
        unit["fact_ids"] = [cite]
    return _World(_facts_with(), units, _dispositions(), tmp=tmp_path)


def _degrade(world: _World, tmp_path: Path, quotes: list[str]) -> Any:
    settled = world.settled()
    findings = tuple(
        Finding(rule="unsupported_claim", source="llm", message="no fact", claim_kind="unsupported_claim",
                quote=q, section_id="api_reference")
        for q in quotes
    )
    verdict = replace(settled.verdict, findings=findings, verdict="REJECT" if findings else "ACCEPT")
    return cascade_module._degrade_settled(
        settled, verdict, entry=ENTRY, document=world.facts, investigation={},
        tree_paths=[], original="", out_dir=tmp_path,
    )


def test_a_faulted_api_reference_intro_is_released_and_the_count_line_stays(tmp_path: Path) -> None:
    world = _world(tmp_path)
    assert INTRO in world.readme
    degraded = _degrade(world, tmp_path, [INTRO])
    assert degraded is not None
    readme = degraded.composed.readme
    assert INTRO not in readme and "The public API has" in readme and "### Core API" in readme
    units = degraded.composed.coherent_units
    assert not [u for u in units["units"] if (u["section"], u["slot"]) == ("api_reference", "intro")]
    assert [o for o in units["omitted"] if o.get("slot") == "intro" and "BL-581" in o["reason"]]
    assert [r["action"] for r in units[DEGRADE_RECORDS_KEY]] == ["intro_withheld"]
    # no new blocking check: BC-04 owes the released slot no unit
    assert {c["id"] for c in blocking_failures(degraded.validation)} <= {
        c["id"] for c in blocking_failures(world.settled().validation)
    }


def test_an_intro_the_review_does_not_fault_is_untouched(tmp_path: Path) -> None:
    world = _world(tmp_path)
    assert _degrade(world, tmp_path, []) is None


def test_an_intro_citing_an_inherited_unit_is_not_released_by_this_lever(tmp_path: Path) -> None:
    world = _world(tmp_path, cite="inherited_unit:001.heading")
    degraded = _degrade(world, tmp_path, [INTRO])
    assert degraded is None or not any(
        "BL-581" in str(o.get("reason")) for o in degraded.composed.coherent_units.get("omitted", [])
    )


def test_a_renderer_fallback_link_description_is_not_shown_to_the_reviewer() -> None:
    for line in (
        "- **[GitHub Repository](https://github.com/org/Repo)** — On github.com.",
        "- **[Docs](https://docs.aspose.org/x/)** — Installation, walkthroughs, and feature guides for this library.",
        "- **[Releases](https://github.com/org/Repo/releases)** — Release history.",
        "- **[Examples](examples/)** — The `examples/` directory in this repository.",
    ):
        assert shown_text(line) == "", line
    readme = "# T\n\n## Documentation & Resources\n\n- **[GitHub Repository](https://github.com/org/Repo)** — On github.com.\n"
    assert not [n for n in reviewable_lines(readme) if "On github.com." in readme.splitlines()[n - 1]]


def test_a_maintainers_or_authored_link_description_is_still_shown() -> None:
    for line in (
        "- **[GitHub Repository](https://github.com/org/Repo)** — Source code, issue tracker and contribution guide.",
        "- **[GitHub Repository](https://github.com/org/Repo)** — On github.com. It ships a CLI.",
    ):
        assert shown_text(line) == line
