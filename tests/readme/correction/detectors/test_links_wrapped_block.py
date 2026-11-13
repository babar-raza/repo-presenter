"""A broken link inside a soft-wrapped block, linked from more than one line (PSD Python).

Real shape, aspose-psd-foss/Aspose.PSD-FOSS-for-Python at 2271c228 (measured with the facts stage
locally): the badge row is one paragraph of four lines (README lines 3-6, each ending in two
spaces), the License badge on line 5 links ``License/LICENSE.txt``, and the License section links
the same target again. The tree has ``LICENSE.txt`` at its root. The link fact records the line its
block starts on (``line 3``) and, being one fact per distinct target, only once - so the detector
reported "not found on its line" and repaired neither link.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.links import broken_link

README = (
    "# Aspose.PSD FOSS for Python  \n"
    "\n"
    "[![PyPI version](https://img.shields.io/pypi/v/aspose-psd-foss.svg)](https://pypi.org/project/aspose-psd-foss/)  \n"
    "[![Python](https://img.shields.io/pypi/pyversions/aspose-psd-foss.svg)](https://pypi.org/project/aspose-psd-foss/)  \n"
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](License/LICENSE.txt)  \n"
    "[![Contributors](https://img.shields.io/github/contributors/aspose-psd-foss/Aspose.PSD-FOSS-for-Python.svg)](https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Python/graphs/contributors)  \n"
    "\n"
    "## License  \n"
    "\n"
    "This project is licensed under the [MIT License](License/LICENSE.txt). The MIT License "
    "permits use.\n"
    "\n"
    "```bash\n"
    "cat License/LICENSE.txt # [x](License/LICENSE.txt)\n"
    "```\n"
)
TREE = ("README.md", "LICENSE.txt", "src/aspose_psd_foss/__init__.py")


def _license_fact(make_fact: Any, line: int = 3) -> Any:
    return make_fact(
        "link_target:005",
        "License/LICENSE.txt",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", f"line {line}; relative; text 'License: MIT'"),
            ("README.md", "MISSING: tree does not contain License/LICENSE.txt"),
        ),
    )


def test_every_prose_link_to_the_broken_target_is_repaired(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(README, make_facts(_license_fact(make_fact)), tree=TREE)
    result = broken_link(ctx)
    assert result.findings == ()
    assert [(e.original, e.replacement) for e in result.edits] == [
        ("License/LICENSE.txt", "LICENSE.txt"),
        ("License/LICENSE.txt", "LICENSE.txt"),
    ]
    badge, section = result.edits
    assert README[badge.start - 2 : badge.end + 1] == "](License/LICENSE.txt)"
    assert README.rindex("[![License: MIT]") < badge.start < README.index("## License")
    assert README.index("[MIT License](") < section.start < README.index("```bash")


def test_a_recorded_line_outside_the_block_is_still_reported(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Line 7 is the blank line after the badge block: nothing of the block follows it."""
    ctx = make_context(README, make_facts(_license_fact(make_fact, line=7)), tree=TREE)
    result = broken_link(ctx)
    assert result.edits == ()
    assert "not found on its line" in result.findings[0].reason
