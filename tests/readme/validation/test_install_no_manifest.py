"""A Python repository with no package manifest (R36(a), owner decision 2026-11-13).

Real shape: aspose-psd-foss/Aspose.PSD-FOSS-for-Python at 2271c228 ships no pyproject.toml,
setup.cfg or setup.py (only a requirements.txt saying ``python>=3.7``). Before this, extraction
made no install fact at all, so BC-02 could only refuse the candidate ("no install command fact"),
and nothing stopped the maintainers' ``pip install -e ".[dev]"`` block - which cannot work without
a manifest - from being kept. Measured locally (facts stage, zero provider calls): example 2 of the
README executed against the tree's own source directories (``ran against the repository source
tree; the package would not build``), which is the receipt the source-checkout path rests on.

Decision (b): the install fact is the source-checkout path, and only on such a receipt - otherwise
there is still no install fact and BC-02's "the source install is not verified at this revision"
stands; a README never prints a pip install of the checkout, and S4 omits the block citing the
missing-manifest fact (``project_file:python_package_manifest``, which extraction already records).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from repo_presenter.core.examples import ExampleReceipt
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import RenderContext, _installation
from repo_presenter.readme.evidence.facts.extract import manifestless_install_fact
from repo_presenter.readme.parity_gate import disposition_is_non_loss
from repo_presenter.readme.reconciliation.dispositions import (
    NO_MANIFEST_RATIONALE,
    normalize,
    placement_errors,
    unproven_source_build_blocks,
)
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.install import install_failures
from repo_presenter.readme.validation.text import installs_the_checkout

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "aspose-psd-foss/Aspose.PSD-FOSS-for-Python"
ENTRY = next(
    e for e in load_registry(ROOT / "data" / "registry.json").entries if e.repository == REPOSITORY
)
REVISION = "2271c228d991bcd79048bb61773bcbcb415399c6"
CHECKOUT = (
    "git clone https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Python.git\n"
    "cd Aspose.PSD-FOSS-for-Python\n"
    'export PYTHONPATH="src:.:$PYTHONPATH"'
)
# The maintainers' "Development and Testing" block, README.md lines 240-246 at the pin.
DEV_BLOCK = (
    "```bash\n"
    "# Install development dependencies and the package in editable mode\n"
    'pip install -e ".[dev]"\n'
    "\n"
    "# Run the full test suite\n"
    'pytest -o python_files="*tests.py"\n'
    "```"
)
DEV_UNIT = "inherited_unit:090.code_block"


def _executed_from_source() -> ExampleReceipt:
    return ExampleReceipt(
        2,
        "EXECUTED",
        0,
        "",
        "",
        "exit 0; ran against the repository source tree; the package would not build",
        build_verified=False,
        source_roots=("src", "."),
    )  # type: ignore[arg-type]


def _failed_from_source() -> ExampleReceipt:
    return ExampleReceipt(
        5,
        "FAILED",
        1,
        "",
        "NameError",
        "NameError; ran against the repository source tree; the package would not build",
        build_verified=False,
        source_roots=("src", "."),
    )  # type: ignore[arg-type]


def test_with_an_executed_source_tree_receipt_the_fact_is_the_source_checkout() -> None:
    fact = manifestless_install_fact(ENTRY, [_executed_from_source(), _failed_from_source()])
    assert fact is not None
    assert fact.id == "install_command:pip"
    assert fact.polarity == "SUPPORTED"
    assert fact.value == CHECKOUT
    assert fact.attributes == {"install_kind": "source_checkout"}
    assert "no package manifest (pyproject.toml, setup.cfg, setup.py)" in (
        fact.evidence[0].detail or ""
    )
    assert "pip install" not in fact.value


def test_without_one_there_is_still_no_install_fact() -> None:
    assert manifestless_install_fact(ENTRY, [_failed_from_source()]) is None
    assert manifestless_install_fact(ENTRY, []) is None


def test_an_ecosystem_with_no_source_reference_gets_no_such_fact() -> None:
    net = ENTRY.model_copy(update={"ecosystem": "net"})
    assert manifestless_install_fact(net, [_executed_from_source()]) is None


# What project_detail records for PSD Python at the pin (local facts stage).
NO_MANIFEST = Fact(
    "project_file:python_package_manifest",
    "project_file",
    "no pyproject.toml, setup.py or setup.cfg at the repository root",
    (Evidence("requirements.txt", "the tracked root files hold no Python package manifest"),),
    attributes={"present": "none"},
)


def _facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        REPOSITORY,
        REVISION,
        (
            Fact("identity:repository", "identity", REPOSITORY, (Evidence("registry"),)),
            Fact(DEV_UNIT, "inherited_unit", DEV_BLOCK, (Evidence("README.md", "lines 240-246"),)),
            Fact(
                "build_test_asset:tests",
                "build_test_asset",
                "src/aspose_psd_foss_test",
                (Evidence("src/aspose_psd_foss_test"),),
            ),
            NO_MANIFEST,
            *extra,
        ),
    )


def _rendered(*facts: Fact) -> str:
    plugin_for(ENTRY.ecosystem)
    context = RenderContext(
        ENTRY, _facts(*facts), {"sections": []}, {"units": []}, {"dispositions": []}
    )
    return "\n".join(_installation(context))


def test_the_installation_section_gives_only_the_verified_checkout() -> None:
    fact = manifestless_install_fact(ENTRY, [_executed_from_source()])
    assert fact is not None
    text = _rendered(fact)
    assert text.startswith(
        "The repository ships no package manifest (`pyproject.toml`, `setup.cfg`, or "
        "`setup.py`), so nothing can be built or installed from a checkout"
    )
    assert f"```bash\n{CHECKOUT}\n```" in text
    assert "pip install" not in text


def test_an_unverified_install_is_stated_as_unverified() -> None:
    text = _rendered()
    assert "the source install is not verified at this revision" in text
    assert "```" not in text and "pip install" not in text


def _candidate(readme: str, *facts: Fact) -> Candidate:
    return Candidate(
        ENTRY, _facts(*facts), {}, {"units": []}, {"dispositions": []}, readme, b"# x\n",
        REVISION, hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )


def test_bc02_passes_the_rendered_checkout_and_refuses_the_editable_install() -> None:
    fact = manifestless_install_fact(ENTRY, [_executed_from_source()])
    assert fact is not None
    readme = "## Installation\n\n" + _rendered(fact) + "\n"
    assert install_failures(_candidate(readme, fact)) == []

    kept = readme + "\n## Development and Testing\n\n" + DEV_BLOCK + "\n"
    failures = install_failures(_candidate(kept, fact))
    assert len(failures) == 1
    assert failures[0].stage == "COMPOSING"
    assert "'pip install -e \".[dev]\"'" in failures[0].detail
    assert "ships no package manifest" in failures[0].detail
    assert failures[0].detail.startswith("project_file:python_package_manifest:")


def test_bc02_still_refuses_an_unverified_install() -> None:
    """The evidence rule is unchanged: with no install fact there is no verified install."""
    readme = "## Installation\n\n" + _rendered() + "\n"
    failures = install_failures(_candidate(readme))
    assert [(f.stage, f.detail) for f in failures] == [
        (
            "EXTRACTING",
            "no install command fact; the source install is not verified at this revision",
        )
    ]


def test_s4_omits_the_editable_install_block_citing_the_missing_manifest() -> None:
    fact = manifestless_install_fact(ENTRY, [_executed_from_source()])
    assert fact is not None
    facts = _facts(fact)
    assert unproven_source_build_blocks(facts) == {
        DEV_UNIT: "project_file:python_package_manifest"
    }
    output = {
        "dispositions": [
            {
                "unit_id": DEV_UNIT,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "development_testing",
                "fact_ids": ["build_test_asset:tests"],
                "rationale": "kept as the maintainers wrote it",
            }
        ]
    }
    normalize(output, facts)
    row = output["dispositions"][0]
    assert row["disposition"] == "OMIT_UNSUPPORTED" and row["destination_section"] is None
    assert row["rationale"] == NO_MANIFEST_RATIONALE
    assert "project_file:python_package_manifest" in row["fact_ids"]
    assert not [e for e in placement_errors(output, facts) if DEV_UNIT in e]
    assert disposition_is_non_loss(row, {})


def test_with_a_manifest_nothing_is_omitted_for_this_reason() -> None:
    with_manifest = FactsDocument(
        REPOSITORY,
        REVISION,
        tuple(f for f in _facts().facts if f.id != NO_MANIFEST.id),
    )
    assert unproven_source_build_blocks(with_manifest) == {}


def test_what_counts_as_installing_the_checkout() -> None:
    for line in ('pip install -e ".[dev]"', "pip install .", "python -m pip install -e .[dev]",
                 "pip3 install --quiet ./", "$ pip install -e ."):
        assert installs_the_checkout(line), line
    for line in ("pip install aspose-psd-foss", "pip install -r requirements.txt",
                 "pytest -o python_files=\"*tests.py\"", "pip install pytest"):
        assert not installs_the_checkout(line), line
