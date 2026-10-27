"""The closed set of correction detectors, registered by name.

A detector is a pure function ``Context -> DetectorResult`` registered with ``@detector(name)``;
``load_detectors`` imports every public module in this package so adding a detector is adding a
file and its test, never a branch in the engine (registries, not a central if/elif).

Ported (REUSE, verbatim) from the old repository's ``components/readme_correction/detectors/
__init__.py`` per ``migration/reuse-manifest.yaml``.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

from repo_presenter.readme.correction.model import Detector

DETECTORS: dict[str, Detector] = {}

#: One version per registered detector, recorded in every Lane L bundle's ``dependencies.json`` as
#: ``detectors.<name>``. Bump a detector's entry when its matching or its edits change meaning: that
#: reopens the ``correction`` scope of the Lane L candidates (and no other candidate). A detector
#: with no entry here, or an entry with no detector, fails ``tests/readme/correction/
#: test_detector_versions.py``, which also pins each module's source so an unversioned logic
#: change cannot pass quietly.
DETECTOR_VERSIONS: dict[str, str] = {
    "broken_link": "1",
    "enterprise_edition_naming": "1",
    "failing_example": "1",
    "format_overclaim": "1",
    "report_gaps": "1",
    "second_h1": "1",
    "stray_fence": "1",
    "unclosed_details": "1",
}


def detector(name: str) -> Callable[[Detector], Detector]:
    def register(function: Detector) -> Detector:
        if name in DETECTORS:
            raise ValueError(f"detector {name!r} is registered twice")
        DETECTORS[name] = function
        return function

    return register


def load_detectors() -> dict[str, Detector]:
    """Every registered detector, in name order, after importing the package's modules."""
    for module in pkgutil.iter_modules(__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{__name__}.{module.name}")
    return dict(sorted(DETECTORS.items()))
