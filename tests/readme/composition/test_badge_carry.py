"""R2/BC-17: the badges row also carries the maintainers' own badges the slot badges do not.

Real text: the first-row ``badge_row`` units below are verbatim from the sealed Lane R bundles of
``aspose-cells-foss/Aspose.Cells-FOSS-for-.NET``, ``-for-Rust`` and ``-for-Python`` (fetched with
``bundle_store.seal_history`` on 2026-11-09), and the failures they fixed are recertify's own BC-17
output for those seals: the shields.io ``issues`` badge, the Rust edition badge linking
``Cargo.toml`` and the ``pyversions`` badge were printed by the published README and lost by the
candidate because the renderer never printed an inherited ``badge_row`` unit.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import (
    EXTRA_BADGE_SLOT,
    RenderContext,
    badge_slots,
)
from repo_presenter.readme.validation.rules import badge_problems

REGISTRY = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")

NET = "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"
RUST = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
PYTHON = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"

NET_ROW = (
    "[![NuGet version](https://img.shields.io/nuget/v/Aspose.Cells.FOSS.svg)](https://www.nuget.org/packages/Aspose.Cells.FOSS/) "
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/blob/master/License/LICENSE.txt) "
    "[![Contributors](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/graphs/contributors) "
    "[![Issues](https://img.shields.io/github/issues/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/issues)"
)
RUST_ROW = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt) "
    "[![Rust Edition](https://img.shields.io/badge/Rust-2021%20edition-orange.svg)](Cargo.toml)"
)
PYTHON_ROW = (
    "[![PyPI version](https://img.shields.io/pypi/v/aspose-cells-foss.svg)](https://pypi.org/project/aspose-cells-foss/)\n"
    "[![Python](https://img.shields.io/pypi/pyversions/aspose-cells-foss.svg)](https://pypi.org/project/aspose-cells-foss/)\n"
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](License/LICENSE.txt)\n"
    "[![Contributors](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-Python.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python/graphs/contributors)"
)


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attrs: str) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value=value,  # type: ignore[arg-type]
        evidence=(Evidence("README.md", None),), polarity=polarity,  # type: ignore[arg-type]
        attributes=attrs or None,
    )


LINKS = {
    NET: ("https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/issues",),
    RUST: (),
    PYTHON: ("https://pypi.org/project/aspose-cells-foss/",),
}
FLOORS = {RUST: (("package:rust_edition", "2021"),)}


def _context(repository: str, row: str, *extra: Fact) -> RenderContext:
    entry = next(e for e in REGISTRY.entries if e.repository == repository)
    plugin_for(entry.ecosystem)  # registers the ecosystem spec, as recertify does
    facts = [
        _fact("inherited_unit:002.badge_row", "inherited_unit", row, section="Product"),
        _fact("license:spdx", "license", "MIT"),
        _fact("license:file", "license", "LICENSE.txt"),
        _fact(
            "link_target:contributors", "link_target",
            f"https://github.com/{repository}/graphs/contributors",
        ),
        *(
            _fact(f"link_target:l{n}", "link_target", url)
            for n, url in enumerate(LINKS.get(repository, ()))
        ),
        *(_fact(fid, "package", value) for fid, value in FLOORS.get(repository, ())),
        *extra,
    ]
    return RenderContext(
        entry, FactsDocument(repository, "0" * 40, tuple(facts)),
        {"sections": []}, {"units": []}, {"dispositions": []},
    )


def _extras(context: RenderContext) -> list[str]:
    return [markdown for slot, markdown in badge_slots(context) if slot == EXTRA_BADGE_SLOT]


def test_the_cells_net_issues_badge_the_published_readme_prints_is_carried() -> None:
    extras = _extras(_context(NET, NET_ROW))
    assert any("img.shields.io/github/issues/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.svg" in m for m in extras)


def test_the_rust_edition_badge_and_its_cargo_toml_link_are_carried_as_written() -> None:
    extras = _extras(_context(RUST, RUST_ROW))
    # Image and link exactly as written; only the alt text's capital "Edition" is lower-cased,
    # because BC-06 forbids any capitalised "Xxx Edition" but Enterprise Edition in public text.
    assert "[![Rust edition](https://img.shields.io/badge/Rust-2021%20edition-orange.svg)](Cargo.toml)" in extras


def test_the_python_pyversions_badge_is_carried() -> None:
    extras = _extras(_context(PYTHON, PYTHON_ROW))
    assert any("img.shields.io/pypi/pyversions/aspose-cells-foss.svg" in m for m in extras)


def test_a_badge_whose_image_a_slot_badge_already_prints_is_not_repeated() -> None:
    context = _context(RUST, RUST_ROW)
    extras = _extras(context)
    assert not any("License-MIT-blue.svg" in m for m in extras)  # the license slot already prints it
    images = [m.split("](")[1] for m in extras]
    assert len(images) == len(set(images))


def test_extras_always_follow_the_slot_badges_and_pass_the_badge_contract() -> None:
    for repository, row in ((NET, NET_ROW), (RUST, RUST_ROW), (PYTHON, PYTHON_ROW)):
        context = _context(repository, row)
        slots = badge_slots(context)
        names = [slot for slot, _ in slots]
        first_extra = names.index(EXTRA_BADGE_SLOT)
        assert set(names[first_extra:]) == {EXTRA_BADGE_SLOT}
        assert badge_problems(" ".join(markdown for _slot, markdown in slots), slots) == []


def test_a_badge_whose_link_target_is_contradicted_is_not_carried() -> None:
    contradicted = _fact(
        "link_target:099", "link_target",
        "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/issues", polarity="CONTRADICTED",
    )
    assert _extras(_context(NET, NET_ROW, contradicted)) == [
        m for m in _extras(_context(NET, NET_ROW)) if "/issues" not in m
    ]


def test_the_contract_still_rejects_a_badge_nothing_derived() -> None:
    context = _context(RUST, RUST_ROW)
    slots = badge_slots(context)
    forged = " ".join(markdown for _slot, markdown in slots) + " [![X](https://example.com/x.svg)](https://example.com)"
    assert badge_problems(forged, slots) != []


def test_a_package_or_contributors_family_badge_needs_its_link_verified() -> None:
    # No SUPPORTED link_target for the PyPI project page: the pyversions badge stays out, the same
    # rule that already keeps an unverified upstream package badge out of its slot.
    context = _context(PYTHON, PYTHON_ROW)
    verified_off = RenderContext(
        context.entry,
        FactsDocument(
            "r", "0" * 40,
            tuple(f for f in context.facts.facts if f.value != "https://pypi.org/project/aspose-cells-foss/"),
        ),
        {"sections": []}, {"units": []}, {"dispositions": []},
    )
    assert not any("pyversions" in m for m in _extras(verified_off))


def test_a_static_runtime_badge_is_carried_only_when_its_numbers_are_the_verified_floor() -> None:
    wrong_floor = _context(
        RUST, RUST_ROW.replace("2021", "2018"),  # the badge says 2018; the verified floor is 2021
    )
    assert not any("Rust-2018" in m for m in _extras(wrong_floor))


def test_a_build_status_badge_is_never_carried_on_the_maintainers_word() -> None:
    row = (
        "[![CI](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust/actions/workflows/ci.yml/badge.svg)]"
        "(https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust/actions/workflows/ci.yml)"
    )
    assert _extras(_context(RUST, row)) == []
