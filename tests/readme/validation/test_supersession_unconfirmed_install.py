"""BC-05 / BC-17 and an UNRESOLVED-ownership registry install (Aspose.3D-FOSS-for-Python, 2026-11-10).

Real shapes from the failed run: the maintainers' README has a fenced block ``python3 -m pip install
aspose-3d-foss`` (``inherited_unit:013.code_block``) that the Installation section replaces, because
PyPI's ``aspose-3d-foss`` names another repository so BC-02 forbids printing the registry install.
BC-05 then demanded the command back ("the README does not state 1 piece(s) of it"), the repair kept
the unit (VERIFIED_PRESERVE into ``development_testing``), and BC-02 failed on the kept line: a
cycle no stage could leave. The command is not owed when the facts record the ownership as
unconfirmed; it is still owed for a package whose install is SUPPORTED, or a different package.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.core.package_registry import (
    is_unconfirmed_registry_install,
    unconfirmed_registry_packages,
)
from repo_presenter.readme.validation.supersession import superseded_failures
from tests.readme.validation.test_install_unconfirmed_ownership import (
    INSTALL,
    INSTALLATION_ONLY,
    UNCONFIRMED,
)

UNIT_ID = "inherited_unit:013.code_block"
UNIT_TEXT = "```bash\npython3 -m pip install aspose-3d-foss\n```"
SUPPORTED_INSTALL = Fact(
    "install_command:pip",
    "install_command",
    "pip install aspose-3d-foss",
    (
        Evidence("setup.py", "distribution name declared by the manifest"),
        Evidence("https://pypi.org/pypi/aspose-3d-foss/json", "package registry: found"),
    ),
    polarity="SUPPORTED",
)


def _candidate(install: Fact | None, readme: str = INSTALLATION_ONLY) -> SimpleNamespace:
    unit = SimpleNamespace(id=UNIT_ID, value=UNIT_TEXT)
    kinds = {"inherited_unit": [unit], "install_command": [install] if install else []}
    return SimpleNamespace(
        facts=SimpleNamespace(by_kind=lambda kind: kinds.get(kind, [])),
        dispositions={
            "dispositions": [
                {"unit_id": UNIT_ID, "disposition": "SUPERSEDE_REDUNDANT", "rationale": "installation"}
            ]
        },
        readme=readme,
    )


def test_the_registry_command_of_an_unconfirmed_package_is_not_owed_by_the_replacement() -> None:
    assert superseded_failures(_candidate(INSTALL)) == []


def test_the_same_loss_still_fails_when_the_install_is_supported() -> None:
    (failure,) = superseded_failures(_candidate(SUPPORTED_INSTALL))
    assert failure.unit == UNIT_ID and "python3 -m pip install aspose-3d-foss" in failure.detail


def test_the_same_loss_still_fails_with_no_install_fact() -> None:
    assert len(superseded_failures(_candidate(None))) == 1


def test_only_the_unconfirmed_package_is_exempt() -> None:
    packages = unconfirmed_registry_packages([INSTALL])
    assert packages == frozenset({"aspose-3d-foss"})
    for line in (
        "python3 -m pip install aspose-3d-foss",
        "$ pip install aspose-3d-foss==26.1.0",
        "pip install Aspose-3D-FOSS",
    ):
        assert is_unconfirmed_registry_install(line, packages)
    for line in (
        "pip install requests",
        "pip install aspose-3d-foss-extras",
        "git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git",
        "import aspose.threed",
    ):
        assert not is_unconfirmed_registry_install(line, packages)
    assert not is_unconfirmed_registry_install("pip install aspose-3d-foss", frozenset())


def test_a_sealed_facts_mapping_reads_the_same_way() -> None:
    mapping = {
        "kind": "install_command",
        "polarity": "UNRESOLVED",
        "value": "pip install aspose-3d-foss",
        "evidence": [{"path": "setup.py", "detail": "x"}, {"path": "u", "detail": UNCONFIRMED}],
    }
    assert unconfirmed_registry_packages([mapping]) == frozenset({"aspose-3d-foss"})
    assert unconfirmed_registry_packages([{**mapping, "polarity": "SUPPORTED"}]) == frozenset()
