"""Report-only measurement of the M9 auditor's derivation rule (``run_m9_auditor.derivation``) over
every sealed README (O6 / docs/RULINGS.md checklist item 13: a new deterministic rule lands only after a
report-only run shows its false-positive rate). Zero provider calls.

For every seal of every bundle ref (or a materialized seal tree, ``--seals``), the rule is run with the
seal's own README as the case text: a clean seal is its own clean control, so every underived line is
a false positive of the rule unless that seal no longer re-derives under current code (a stale seal,
reported separately). Writes one JSON document and prints the per-lane rates.

    PYTHONPATH=src python scripts/measure_m9_derivation.py --seals DIR --out FILE [--fetch-trees]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_spec = importlib.util.spec_from_file_location("run_m9_auditor", REPO_ROOT / "scripts" / "run_m9_auditor.py")
auditor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditor)


def materialized_seals(root: Path) -> list[SimpleNamespace]:
    """``<root>/<lane>/<owner>__<name>/<seal commit>/<revision>/`` trees as ``seal_history(scratch=...)``
    leaves them (every directory holding a README.md and facts.json)."""
    seals = []
    for readme in sorted(root.glob("*/*/*/*/README.md")):
        bundle = readme.parent
        lane, slug, revision = bundle.parts[-4], bundle.parts[-3], bundle.parts[-1]
        if (bundle / "facts.json").is_file():
            seals.append(SimpleNamespace(bundle=str(bundle), lane=lane, revision=revision,
                                         repository=slug.replace("__", "/", 1)))
    return seals


def measure(seals: list[SimpleNamespace], fetch_trees: bool, work: Path) -> dict:
    rows = []
    trees: dict[tuple[str, str], object] = {}

    def fetch(repository: str, revision: str, workdir: Path):
        if (repository, revision) not in trees:
            if fetch_trees:
                from repo_presenter.recertify import fetch_source

                trees[(repository, revision)] = fetch_source(repository, revision, workdir)
            else:
                trees[(repository, revision)] = SimpleNamespace(tree_paths=())
        return trees[(repository, revision)]

    for seal in seals:
        text = (Path(seal.bundle) / "README.md").read_text(encoding="utf-8")
        derived = auditor.case_derivation(seal, text, work, fetch=fetch)
        row = {"repository": seal.repository, "lane": seal.lane, "revision": seal.revision,
               "seal_commit": Path(seal.bundle).parent.name}
        if derived is None:
            row["status"] = "unavailable"
        else:
            lines = text.splitlines()
            row.update(status="flagged" if derived.underived else "clean",
                       derivable=len(derived.derivable), underived=sorted(derived.underived),
                       underived_text=[lines[n - 1][:160] for n in sorted(derived.underived)][:10])
        rows.append(row)
    summary = {}
    for lane in ("L", "R"):
        mine = [r for r in rows if r["lane"] == lane]
        flagged = sum(r["status"] == "flagged" for r in mine)
        summary[lane] = {"seals": len(mine), "flagged": flagged,
                         "unavailable": sum(r["status"] == "unavailable" for r in mine),
                         "flag_rate": round(flagged / len(mine), 4) if mine else None}
    return {"schema": "m9-derivation-measurement/1", "fetch_trees": fetch_trees, "summary": summary, "seals": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seals", type=Path, help="materialized seal tree (seal_history scratch)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fetch-trees", action="store_true", help="read each Lane L revision's tracked tree")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="m9-derivation-") as work:
        root = args.seals
        if root is None:
            from repo_presenter.core.state.bundle_store import seal_history

            root = Path(work) / "seals"
            seal_history(remote=args.remote, scratch=root)
        seals = materialized_seals(root)
        document = measure(seals, args.fetch_trees, Path(work) / "trees")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
