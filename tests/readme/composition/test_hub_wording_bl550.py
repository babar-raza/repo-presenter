"""BL-550: a Detailed Member Reference hub paragraph never prints the pipeline's analysis wording (BC-07).

Real data: hosted Slides Java refresh run 44787829770 -- the hub unit "The getFontName method is a public symbol
exposed by certain text-related classes to retrieve the name of a font used in a presentation." printed
unfiltered; BC-07 failed on it with no section to repair, so nothing was reviewed or sealed. Core API rows already
went through ``_symbol_description`` (BL-087); the hub paragraph now takes the same rule.
"""

from __future__ import annotations

from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.validation.public_text import analysis_markers
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _facts, _plan

HUB_ID = "public_symbol:aspose.threed.scene"
BAD = (
    "The Scene method is a public symbol exposed by certain text-related classes to retrieve the "
    "name of a font used in a presentation."
)
GOOD = "The Scene class holds the nodes of one 3D scene and is the root of every export."


def _render(hub_text: str | None) -> str:
    units = {
        **UNITS,
        "units": [
            u for u in UNITS["units"] if u.get("slot") != f"hub:{HUB_ID}"
        ] + (
            [{"section": "api_reference", "slot": f"hub:{HUB_ID}", "text": hub_text, "fact_ids": [HUB_ID]}]
            if hub_text is not None
            else []
        ),
    }
    return render_readme(ENTRY, _facts(), _plan(), units, _dispositions())


def test_a_hub_sentence_with_analysis_wording_is_replaced_by_the_fact_true_description() -> None:
    readme = _render(BAD)
    assert BAD not in readme
    assert not [line for line in analysis_markers(readme) if "public symbol" in line]
    block = readme.split("### Scene\n", 1)[1].split("\n\n", 2)
    assert block[0].strip() == "Public symbol."


def test_negative_control_a_clean_hub_sentence_prints_as_written() -> None:
    assert "The `Scene` class holds the nodes of one 3D scene and is the root of every export." in _render(GOOD)


def test_negative_control_the_wording_check_still_sees_the_bad_sentence() -> None:
    assert analysis_markers(BAD)
