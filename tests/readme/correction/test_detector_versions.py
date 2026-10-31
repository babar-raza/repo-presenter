"""Every Lane L detector carries a version, and its module's source is pinned beside it
(plans/PLAN_lane_l_hosted.md L8).

A Lane L bundle records ``detectors.<name>`` in its ``dependencies.json``; a change to one reopens
only the ``correction`` scope of the Lane L candidates. That is only as honest as the versions are:
a detector whose logic changes without a bump would leave every sealed candidate claiming currency
under logic it never ran. So the source of each detector module is pinned to the versions of the
detectors it registers. Changing a detector module fails this test until its pin is updated, and
the pin sits next to the version, so the diff that updates it shows whether the version moved too.
Formatting-only edits also need a pin update (the digest is over the LF-normalised bytes) and no
version bump: the reviewer of that diff sees exactly that.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from repo_presenter.readme.correction import detectors as detectors_package
from repo_presenter.readme.correction.detectors import DETECTOR_VERSIONS, load_detectors
from repo_presenter.readme.correction.engine import CORRECTION_ENGINE_VERSION

#: module file -> (the versions of the detectors it registers, in name order, sha256 of its
#: LF-normalised source).
PINS: dict[str, tuple[tuple[str, ...], str]] = {
    "enterprise_edition.py": (
        ("1",),
        "958c1d8b6b821be971d6fcf9d53330f84bfd5c596904a4bfdcbf9f4f7d343c88",
    ),
    "examples.py": (
        ("1",),
        "a7e4ac68af4dd93d9992462a7dd35f30ea6a01941869460bd599209a7953ca15",
    ),
    "format_overclaim.py": (
        ("2",),
        "cbc9ef5e78b4e753ec6eba68a4d1164acc2de900fd441525dcd4941348fafb90",
    ),
    "gaps.py": (
        ("1",),
        "84730a9041b74da6f35270ce2aa9e814490eac8417a8847eccb44676f2b4861e",
    ),
    "links.py": (
        ("1",),
        "831000cf4390bb73d51bcff348a6c914c23c80e1a3fc414e386d0fc84d85adb5",
    ),
    "structure.py": (
        ("1", "1", "1"),
        "7c836b19f79488ef3f857c9e9b40df9813d717539e4cfe26050227ea9871c573",
    ),
}


def _module_files() -> dict[str, Path]:
    directory = Path(detectors_package.__file__).parent
    return {
        path.name: path
        for path in sorted(directory.glob("*.py"))
        if not path.name.startswith("_")
    }


def test_every_registered_detector_has_exactly_one_version() -> None:
    assert sorted(DETECTOR_VERSIONS) == sorted(load_detectors())
    assert all(
        isinstance(version, str) and version for version in DETECTOR_VERSIONS.values()
    )
    assert CORRECTION_ENGINE_VERSION


def test_each_detector_module_is_pinned_to_the_versions_of_the_detectors_it_registers() -> (
    None
):
    detectors = load_detectors()
    by_module: dict[str, list[str]] = {}
    for name, function in detectors.items():
        by_module.setdefault(function.__module__.rsplit(".", 1)[-1] + ".py", []).append(
            name
        )
    files = _module_files()
    assert sorted(by_module) == sorted(files) == sorted(PINS)
    for module, names in by_module.items():
        digest = hashlib.sha256(
            files[module].read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        versions = tuple(DETECTOR_VERSIONS[name] for name in sorted(names))
        assert (versions, digest) == PINS[module], (
            f"{module} changed or its detectors' versions moved: if its behaviour changed, bump "
            f"DETECTOR_VERSIONS for {sorted(names)}, then set this pin to ({versions!r}, {digest!r})"
        )
