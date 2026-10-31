"""Measure how close our README is to the aspose.org candidate for the same product (read-only).

Reads the aspose.org candidate from the sibling checkout at run time and prints counts and heading
names only; nothing from it is stored. Our README comes from --readme, or is restored from the
durable bundle ref on origin for --repository / --lane.

Usage:
    python scripts/aspose_parity.py --repository aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET
    python scripts/aspose_parity.py --all-bundles
    python scripts/aspose_parity.py --repository <owner/name> --readme path/to/README.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.aspose_parity import compare, reference_path, render
from repo_presenter.core.candidates import CURRENT_FILENAME, lane_directory
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.state.bundle_store import BUNDLE_REF_PREFIX, BundleStoreError, export_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ASPOSE_ROOT = REPO_ROOT.parent / "aspose.org"


def _our_readme(repository: str, lane: str, remote: str, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    out = Path(tempfile.mkdtemp(prefix="parity-"))
    root = export_bundle(repository, lane, out, remote=remote)
    revision = (root / CURRENT_FILENAME).read_text(encoding="utf-8").strip()
    return root / revision / "README.md"


def _stored_repositories(remote: str, lane: str) -> set[str]:
    listed = subprocess.run(
        ["git", "ls-remote", remote, f"{BUNDLE_REF_PREFIX}/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    suffix = "@lane-l" if lane == "L" else ""
    names: set[str] = set()
    for line in listed.splitlines():
        key = line.split("\t")[1].rsplit("/", 1)[-1]
        if lane == "L" and not key.endswith(suffix):
            continue
        if lane == "R" and key.endswith("@lane-l"):
            continue
        names.add(key.removesuffix(suffix).replace("__", "/", 1))
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository")
    parser.add_argument("--all-bundles", action="store_true")
    parser.add_argument("--lane", default="R", choices=["R", "L"])
    parser.add_argument("--readme", type=Path)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--aspose-root", type=Path, default=DEFAULT_ASPOSE_ROOT)
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    args = parser.parse_args(argv)
    entries = {e.repository: e for e in load_registry(args.registry).entries}
    if args.all_bundles:
        targets = sorted(_stored_repositories(args.remote, args.lane) & set(entries))
    elif args.repository:
        targets = [args.repository]
    else:
        parser.error("give --repository or --all-bundles")
    status = 0
    for repository in targets:
        entry = entries[repository]
        reference = reference_path(args.aspose_root, entry.family, entry.platform)
        if not reference.is_file():
            print(f"{repository}: no aspose.org candidate at the expected path")
            status = 1
            continue
        try:
            ours = _our_readme(repository, args.lane, args.remote, args.readme)
        except BundleStoreError as exc:
            print(f"{repository}: {exc}")
            status = 1
            continue
        parity = compare(ours.read_text(encoding="utf-8"), reference.read_text(encoding="utf-8"))
        print(render(f"{repository} (Lane {args.lane})", parity))
        print()
    return status


if __name__ == "__main__":
    raise SystemExit(main())
