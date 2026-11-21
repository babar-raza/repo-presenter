"""Dangling-pointer fixes: a Title-Case heading name is not a pointer (PDF-Cpp), and a de-linked
anchor takes its positional word with it (PDF-Go)."""

from __future__ import annotations

from repo_presenter.readme.composition.placement import resolve_intra_document_anchors
from repo_presenter.readme.composition.references import dangling_references

_CPP = (
    "Additional Examples below extends this into a from-scratch showcase "
    "([`examples/12_create_features.cpp`](examples/12_create_features.cpp)) that creates a "
    "document with text, images and tables."
)
_GO = (
    "Page-level encryption (RC4 / AES-128 / AES-256) is covered in "
    "[Encryption and Signing](#encryption-and-signing) below. Regenerate it locally with "
    "`go run ./_examples/feature_showcase`."
)


def _reasons(body: str) -> list[str]:
    return [r.reason for r in dangling_references(f"# P\n\n## Usage\n\n{body}\n")]


def test_title_case_heading_name_is_not_a_pointer() -> None:
    assert _reasons(_CPP) == []


def test_real_pointers_stay_flagged() -> None:
    assert len(_reasons("The examples below show more.")) == 1
    assert len(_reasons("Examples below show more.")) == 1
    assert len(_reasons("See Examples below for more.")) == 1
    assert len(_reasons("The Examples below show more.")) == 1
    assert len(_reasons("The table below lists them.")) == 1
    assert len(_reasons("Additional examples below extend this.")) == 1


def test_title_case_name_with_a_following_example_is_still_fine() -> None:
    assert _reasons(_CPP + "\n\n```cpp\nrun();\n```") == []


def test_rendered_anchor_keeps_its_position_word() -> None:
    text = resolve_intra_document_anchors(_GO, frozenset({"encryption-and-signing"}))
    assert text == _GO


def test_real_dangling_stays_flagged_after_delink() -> None:
    text = resolve_intra_document_anchors("The table below lists [X](#x).", frozenset())
    assert len(_reasons(text)) == 1


# BL-652 (hosted Lane R PDF Python, run 44943413732): the API Reference prints the members' own
# docstrings, and "Find image placements whose effective DPI is below ``min_dpi``." is a comparison,
# not a pointer to content below. A bullet list that ends its section tripped BC-07 on it in both
# settle rounds (and the repair blanked a plan hub to evade it).
def _below(sentence: str) -> list[str]:
    from repo_presenter.readme.composition.references import dangling_references

    readme = f"# T\n\n## API Reference\n\n- `a`: First member.\n- `b`: {sentence}\n"
    return [found.reason for found in dangling_references(readme)]


def test_a_comparison_below_a_value_is_not_a_pointer() -> None:
    for sentence in (
        "Find image placements whose effective DPI is below ``min_dpi``.",
        "Report each placed image below a finite, positive threshold.",
        "Find image placements on this page below multiple DPI thresholds.",
        "One image paint below the requested effective DPI on either image axis.",
    ):
        assert _below(sentence) == [], sentence


def test_negative_control_a_real_pointer_below_still_dangles() -> None:
    for sentence in (
        "The options are described below.",
        "See below.",
        "Errors are listed below",
        "Run the commands as shown below:",
    ):
        assert _below(sentence), sentence
