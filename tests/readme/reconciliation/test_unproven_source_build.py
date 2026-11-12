"""A kept command block that prints a source build no build proved is omitted on evidence at S4.

Aspose.Cells FOSS for C++ (hosted, 2026-11-11): the measured build ran and FAILED, so
``install_command:cmake`` is UNRESOLVED ("no build exited 0: failed") and BC-02 refuses a README that
prints ``cmake --build build``. The maintainers' test-suite block (060) was kept ``VERIFIED_PRESERVE``
anyway, and the BC-02 repair "succeeded" with ``changes: []`` -- it re-answered and kept the block --
so the block, and BC-02, stayed. The disposition is deterministic given the facts, so S4 settles it.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    UNPROVEN_BUILD_RATIONALE,
    normalize,
    placement_errors,
    unproven_build_commands,
    unproven_source_build_blocks,
)

REVISION = "c" * 40
TEST_BLOCK = (
    "```bash\n"
    "git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp.git\n"
    "cd Aspose.Cells-FOSS-for-Cpp/Aspose.Cells.Foss.Cpp.Tests\n"
    "cmake -S . -B build\n"
    "cmake --build build\n"
    "ctest --test-dir build --output-on-failure\n"
    "```"
)
SAMPLES_BLOCK = "```bash\ncd samples\nmkdir build && cd build\ncmake ..\ncmake --build .\n```"
INSTALL_ID = "install_command:cmake"
UNIT_TESTS = "inherited_unit:060.code_block"
UNIT_SAMPLES = "inherited_unit:063.code_block"
NO_REGISTRY = "package registry: none could not be read"


def _install(polarity: str = "UNRESOLVED", registry: str = NO_REGISTRY) -> Fact:
    return Fact(
        INSTALL_ID,
        "install_command",
        "cmake -S Aspose.Cells.Foss.Cpp -B build\ncmake --build build",
        (
            Evidence("CMakeLists.txt", "source build for the CMake project the manifest declares"),
            Evidence("registry", registry),
        ),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        "org/Aspose.Cells-FOSS-for-Cpp",
        REVISION,
        (
            Fact("identity:repository", "identity", "org/Aspose.Cells-FOSS-for-Cpp", (Evidence("r"),)),
            Fact(UNIT_TESTS, "inherited_unit", TEST_BLOCK, (Evidence("README.md", "lines 1-9"),)),
            Fact(UNIT_SAMPLES, "inherited_unit", SAMPLES_BLOCK, (Evidence("README.md", "lines 10-14"),)),
            Fact("build_test_asset:tests", "build_test_asset", "tests", (Evidence("t"),)),
            *extra,
        ),
    )


def _row(unit_id: str, disposition: str = "VERIFIED_PRESERVE") -> dict:
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": "development_testing",
        "fact_ids": ["build_test_asset:tests"],
        "rationale": "kept as the maintainers wrote it",
    }


def test_the_unproven_commands_are_the_lines_of_the_unresolved_registry_less_install() -> None:
    assert unproven_build_commands(_facts(_install())) == {
        INSTALL_ID: {"cmake -s aspose.cells.foss.cpp -b build", "cmake --build build"}
    }


def test_a_block_with_one_such_line_is_unproven_and_a_block_without_one_is_not() -> None:
    blocks = unproven_source_build_blocks(_facts(_install()))
    assert blocks == {UNIT_TESTS: INSTALL_ID}  # the samples block's `cmake --build .` is another line


def test_a_proven_build_or_a_registry_kind_install_makes_nothing_unproven() -> None:
    assert unproven_source_build_blocks(_facts(_install(polarity="SUPPORTED"))) == {}
    assert unproven_source_build_blocks(_facts(_install(registry="package registry: found"))) == {}


def test_s4_omits_the_kept_block_citing_the_install_fact_and_validation_accepts_it() -> None:
    facts = _facts(_install())
    output = {"dispositions": [_row(UNIT_TESTS), _row(UNIT_SAMPLES)]}
    normalize(output, facts)
    tests, samples = output["dispositions"]
    assert tests["disposition"] == "OMIT_UNSUPPORTED" and tests["destination_section"] is None
    assert INSTALL_ID in tests["fact_ids"] and tests["rationale"] == UNPROVEN_BUILD_RATIONALE
    assert samples["disposition"] == "VERIFIED_PRESERVE"  # its commands are not the unproven ones
    assert not [e for e in placement_errors(output, facts) if UNIT_TESTS in e]


def test_the_omission_reads_as_evidence_to_the_loss_accounting() -> None:
    from repo_presenter.readme.parity_gate import disposition_is_non_loss

    facts = _facts(_install())
    output = {"dispositions": [_row(UNIT_TESTS)]}
    normalize(output, facts)
    assert disposition_is_non_loss(output["dispositions"][0], {})


def test_with_a_proven_build_the_block_stays_kept() -> None:
    facts = _facts(_install(polarity="SUPPORTED"))
    output = {"dispositions": [_row(UNIT_TESTS)]}
    normalize(output, facts)
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_restore_never_puts_the_forbidden_block_back() -> None:
    from repo_presenter.readme.repair.restore_units import restore_lost_units

    facts = _facts(_install())
    omitted = {
        "dispositions": [
            {
                "unit_id": UNIT_TESTS,
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [INSTALL_ID],
                "rationale": UNPROVEN_BUILD_RATIONALE,
            }
        ]
    }
    skipped: list[dict[str, str]] = []
    output, changes = restore_lost_units(
        omitted, facts, [UNIT_TESTS], ["development_testing"], ["development_testing"], skipped=skipped
    )
    assert changes == [] and output["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"
    assert skipped == [{"unit_id": UNIT_TESTS, "reason": "forbidden_command"}]
