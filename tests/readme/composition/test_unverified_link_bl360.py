"""BL-360: a link nothing could verify (UNCHECKED) is never printed as a link.

Real finding text (hosted frozen-code pass 3, 2026-11-19, run 44619992187, Aspose.PDF-FOSS-for-Cpp
Lane R): ``BC-06 https://en.cppreference.com/w/cpp/20 is UNRESOLVED: UNCHECKED`` -- the maintainers'
C++20 badge links cppreference, which the runner could not answer. The badge keeps its image, a kept
unit keeps its label, BC-17 accounts for the omitted link on the UNRESOLVED fact, and a verified
(SUPPORTED) or gone (CONTRADICTED) link behaves exactly as before.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.evidence.facts.links import (
    is_unverified_external,
    unverified_external_hrefs,
)
from repo_presenter.readme.validation.surface_claims import without_contradicted_links

from .test_badge_carry import CPP, CPP_ROW, _context, _extras, _fact

CPPREF = "https://en.cppreference.com/w/cpp/20"
BADGE = "[![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus)](" + CPPREF + ")"
IMAGE = "![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus)"


FLOOR = _fact("package:cxx_standard", "package", "20")


def _extras_for(polarity: str) -> list[str]:
    link = _fact("link_target:099", "link_target", CPPREF, polarity)
    return [m for m in _extras(_context(CPP, CPP_ROW, FLOOR, link)) if "C%2B%2B-20" in m]


def test_the_pdf_cpp_badge_with_an_unchecked_link_is_printed_as_its_image_alone() -> None:
    assert _extras_for("UNRESOLVED") == [IMAGE]


def test_negative_controls_a_verified_link_stays_and_a_dead_one_was_never_printed() -> None:
    assert _extras_for("SUPPORTED") == [BADGE]
    assert _extras_for("CONTRADICTED") == []


def test_extra_badge_unlinked_when_unchecked_and_linked_when_verified() -> None:
    row = (
        "[![Issues](https://img.shields.io/github/issues/x/y.svg)](https://example.org/issues) "
        "[![CMake](https://img.shields.io/badge/CMake-3.20+-064F8C?logo=cmake)](https://cmake.org/)"
    )
    cmake = "https://cmake.org/"
    unchecked = _extras(_context(CPP, row, _fact("link_target:098", "link_target", cmake, "UNRESOLVED")))
    verified = _extras(_context(CPP, row, _fact("link_target:098", "link_target", cmake, "SUPPORTED")))
    assert unchecked == ["![CMake](https://img.shields.io/badge/CMake-3.20+-064F8C?logo=cmake)"]
    assert verified == ["[![CMake](https://img.shields.io/badge/CMake-3.20+-064F8C?logo=cmake)](https://cmake.org/)"]


def _doc(*facts: Fact) -> FactsDocument:
    return FactsDocument("aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp", "0" * 40, tuple(facts))


def test_a_kept_unit_prints_an_unchecked_link_as_its_label() -> None:
    text = f"See the [C++20 reference]({CPPREF}) and [CMake](https://cmake.org/)."
    unchecked = _doc(_fact("link_target:1", "link_target", CPPREF, "UNRESOLVED"))
    assert without_contradicted_links(text, unchecked) == (
        "See the C++20 reference and [CMake](https://cmake.org/)."
    )
    for polarity in ("SUPPORTED",):  # negative control: a verified link is untouched
        ok = _doc(_fact("link_target:1", "link_target", CPPREF, polarity))
        assert without_contradicted_links(text, ok) == text


def test_only_web_targets_count_mailto_and_other_links_stay() -> None:
    assert is_unverified_external(CPPREF, "UNRESOLVED")
    assert not is_unverified_external("mailto:a@b.c", "UNRESOLVED")
    assert not is_unverified_external(CPPREF, "SUPPORTED")
    assert not is_unverified_external(CPPREF, "CONTRADICTED")
    doc = _doc(
        _fact("link_target:1", "link_target", "mailto:a@b.c", "UNRESOLVED"),
        _fact("link_target:2", "link_target", CPPREF, "UNRESOLVED"),
    )
    assert unverified_external_hrefs(doc) == {CPPREF}
    assert Evidence  # imported for fact construction parity with the badge-carry tests


# --- BC-17: the omitted link is accounted for on the UNRESOLVED fact (Lane R only) ---------------

BENCH = f"# Aspose.PDF FOSS for C++\n\nBuilt with [C++20]({CPPREF}).\n"
CAND = f"# Aspose.PDF FOSS for C++\n\n{IMAGE}\n\nBuilt with C++20.\n"


def _link_losses(lane: str, polarity: str) -> list:
    from repo_presenter.readme.parity_gate import SealedCandidate, content_losses

    doc = _doc(_fact("link_target:1", "link_target", CPPREF, polarity))
    rows = tuple(
        {"id": f.id, "kind": f.kind, "value": f.value, "polarity": f.polarity,
         "attributes": f.attributes, "evidence": []}
        for f in doc.facts
    )
    candidate = SealedCandidate(lane, CAND, rows, (), document=doc)
    return [loss for loss in content_losses(candidate, BENCH) if CPPREF in loss.item]


def test_bc17_does_not_call_an_unchecked_link_printed_as_an_image_a_loss() -> None:
    assert _link_losses("R", "UNRESOLVED") == []


def test_bc17_negative_controls_a_verified_link_and_lane_l_still_lose_it() -> None:
    assert _link_losses("R", "SUPPORTED") != []
    assert _link_losses("L", "UNRESOLVED") != []
