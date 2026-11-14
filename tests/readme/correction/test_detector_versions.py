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
    "absent_type_row.py": (
        ("1",),
        "606536ac28df7e7d520a363c931701b3dd459d204cec700267a421dc15573079",
    ),
    "dead_link.py": (
        ("1",),
        "d480a78c7be3887f66fac0c341ef91ba90edeb240bac3e603b3a0393c4b648d1",
    ),
    "enterprise_edition.py": (
        ("4",),
        "fbc8cba10d645350143afc78a08f2957be9488e67f8584efa1ba699e3bb59642",
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
    "glance_layout.py": (
        ("1",),
        "ea2956b8beed9d4f9f1bb3af15ffd3cdb02f9ab83d62f6a1f7a1d68a51f80fe7",
    ),
    "listed_type_count.py": (
        ("1",),
        "d6f3603cfaafb4c57957c9c650a1c32972472ec5b60288ad41bf9005ad57b903",
    ),
    "links.py": (
        ("2",),
        "59fa698291ad1610f892ba7d5a452dc17054d979d43eb29da50bc2dc2f90d881",
    ),
    "stale_package_version.py": (
        ("5",),
        "ea69011d1a78451b640269cbad80b965e4364d9c7d58613bc31cfcaac2f1f0ff",
    ),
    "stale_type_count.py": (
        ("1",),
        "b24921b7c8c707148dae63adac0fe6bb9eb70e2190b1dc850836255a9ce81811",
    ),
    "structure.py": (
        ("1", "1", "1"),
        "7c836b19f79488ef3f857c9e9b40df9813d717539e4cfe26050227ea9871c573",
    ),
    "type_description.py": (
        ("2",),
        "d27bc30388456f21a3f557db6445bb57518523fd488e6c79d1bd538694762c70",
    ),
    "versioned_link_target.py": (
        ("1",),
        "bc344c363ce398201946044fdf4c2ac9b92f2e490cfbd26a31b59bc777d3ffff",
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
