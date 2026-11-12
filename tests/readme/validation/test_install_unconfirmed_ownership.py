"""BC-02 and an UNRESOLVED-ownership registry install (Aspose.3D-FOSS-for-Python, 2026-11-10).

Real data: the ``install_command:pip`` fact and the README lines are copied from the batch-1 run of
``aspose-3d-foss/Aspose.3D-FOSS-for-Python``. PyPI holds ``aspose-3d-foss`` 26.1.0 but its project URL
points at another repository, so the fact is UNRESOLVED ("ownership not confirmed"). Before: BC-02
failed at EXTRACTING whether or not the README printed the command, so no repair stage could ever
reach the authored sentence ("Install the published package from PyPI ...") that actually made the
claim. After: a README that prints no registry command claims nothing (the renderer states the
package as unconfirmed and gives the source install), and a README that prints one fails at the line
that prints it (COMPOSING / RECONCILING), which the repair stages can change.
"""

from __future__ import annotations

import hashlib

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.install import install_failures

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
UNCONFIRMED = (
    "package registry: a distribution of this name exists, but ownership not confirmed: the "
    "registry's project URLs point at another repository"
)

INSTALL = Fact(
    "install_command:pip",
    "install_command",
    "pip install aspose-3d-foss",
    (
        Evidence("setup.py", "distribution name declared by the manifest"),
        Evidence("https://pypi.org/pypi/aspose-3d-foss/json", UNCONFIRMED),
    ),
    polarity="UNRESOLVED",
    confidence=0.5,
    attributes={"source_checkout_command": "git clone https://github.com/x/y.git\ncd y\npip install ."},
)
PACKAGE = Fact(
    "package:name", "package", "aspose-3d-foss", (Evidence("setup.py", "distribution name declared by the manifest"),)
)

INSTALLATION_ONLY = """## Installation

The package `aspose-3d-foss` could not be confirmed on PyPI (package registry: a distribution of this name exists, but ownership not confirmed: the registry's project URLs point at another repository).

To work from a source checkout instead, install the clone with pip:

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git
cd Aspose.3D-FOSS-for-Python
pip install .
```
"""

WITH_AUTHORED_REGISTRY_LINE = INSTALLATION_ONLY + """
## Development and Testing

Install the published package from PyPI (`aspose-3d-foss`, version 26.1.0):

```bash
python3 -m pip install aspose-3d-foss
```
"""


def _candidate(readme: str) -> Candidate:
    entry = RegistryEntry.model_validate(
        {
            "repository": REPOSITORY,
            "family": "3d",
            "platform": "python",
            "ecosystem": "python",
            "mode": "dry_run",
            "policy_profile": "aspose-3d-foss-python",
            "active": True,
            "provider_identity": {"provider": "github", "repository_id": 1138357893, "node_id": "R_x"},
        }
    )
    facts = FactsDocument(REPOSITORY, "0" * 40, (INSTALL, PACKAGE))
    return Candidate(
        entry, facts, {}, {"units": []}, {"dispositions": []}, readme, b"# x\n", "0" * 40,
        hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )


def test_a_readme_that_prints_no_registry_command_claims_nothing() -> None:
    assert [f for f in install_failures(_candidate(INSTALLATION_ONLY)) if "install_command:pip" in f.detail] == []


def test_an_authored_registry_install_line_fails_at_the_section_that_prints_it() -> None:
    failures = [f for f in install_failures(_candidate(WITH_AUTHORED_REGISTRY_LINE)) if "install_command:pip" in f.detail]
    assert len(failures) == 1
    (failure,) = failures
    assert failure.stage == "COMPOSING"  # repairable by the section's author, not EXTRACTING
    assert "python3 -m pip install aspose-3d-foss" in failure.detail
    assert "ownership" in failure.detail
    assert failure.section == "Development and Testing" or "development" in str(failure.section).lower()


def test_a_supported_install_is_unaffected_by_the_new_branch() -> None:
    supported = Fact(
        "install_command:pip", "install_command", "pip install aspose-3d-foss",
        (
            Evidence("setup.py", "distribution name declared by the manifest"),
            Evidence("https://pypi.org/pypi/aspose-3d-foss/json", "package registry: published, corroborated"),
        ),
    )
    candidate = _candidate("## Installation\n\n```bash\npip install aspose-3d-foss\n```\n")
    candidate = Candidate(
        candidate.entry, FactsDocument(REPOSITORY, "0" * 40, (supported, PACKAGE)), {}, {"units": []},
        {"dispositions": []}, candidate.readme, b"# x\n", "0" * 40, hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )
    assert install_failures(candidate) == []


def test_other_unresolved_readings_still_fail_at_extracting() -> None:
    unreadable = Fact(
        "install_command:pip", "install_command", "pip install aspose-3d-foss",
        (
            Evidence("setup.py", "distribution name declared by the manifest"),
            Evidence("https://pypi.org/pypi/aspose-3d-foss/json", "package registry could not be read: timeout"),
        ),
        polarity="UNRESOLVED", confidence=0.5,
    )
    candidate = _candidate(INSTALLATION_ONLY)
    candidate = Candidate(
        candidate.entry, FactsDocument(REPOSITORY, "0" * 40, (unreadable, PACKAGE)), {}, {"units": []},
        {"dispositions": []}, candidate.readme, b"# x\n", "0" * 40, hashlib.sha256(b"# x\n").hexdigest(), (), [],
    )
    failures = install_failures(candidate)
    assert failures and failures[0].stage == "EXTRACTING"
