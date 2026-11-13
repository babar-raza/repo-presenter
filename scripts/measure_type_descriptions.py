"""Measure the shape of every API-reference type description across the portfolio's latest seals,
before (the sealed README) and after (the README current code re-certifies it to).

The Pareto measurement behind the 2026-11-13 type-description rule (``docs/DECISION_LOG.md``):
every two-column table row whose first cell names a verified type is classified by the one shared
classifier, ``readme.correction.detectors.type_description.cell_shape``:

* ``doc_comment`` -- the type's own doc comment summary;
* ``count_only`` -- "Class with 18 methods and 6 properties.", "Enum with 2 members.";
* ``boilerplate_label`` -- "Interface in the 3D JAVA API.", "X is a public symbol with members ...";
* ``doc_bookkeeping`` -- "Created by lexchou on 12/14/2016." and other file-header text;
* ``other_prose`` -- anything else (a purpose sentence written by the maintainers or authored).

"After" is exactly what ``python -m repo_presenter.recertify`` would re-certify each seal to
(``recertify_history``: zero provider calls, read-only, nothing written). Lane R's after equals its
before unless re-rendering changes a row: its type sentences are stored authored outputs, and the
authoring rule only takes effect on the next authoring run.

Usage:
    python scripts/measure_type_descriptions.py [--remote origin] [--certified-only] [--json PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.facts import read_facts
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry_entry_stub import RegistryEntryStub
from repo_presenter.core.state.bundle_store import seal_history
from repo_presenter.core.version_set import current_fingerprints
from repo_presenter.readme.correction.detectors.type_description import (
    NON_DESCRIPTIVE,
    cell_shape,
    description_rows,
    type_facts_by_name,
)
from repo_presenter.readme.correction.model import Context
from repo_presenter.recertify import fetch_source, recertify_history

REPO_ROOT = Path(__file__).resolve().parent.parent
SHAPES = ("doc_comment", "other_prose", "count_only", "boilerplate_label", "doc_bookkeeping")


def classify(readme: str, facts, repository: str) -> list[dict[str, object]]:
    """Every type description row of ``readme`` with its shape."""
    ctx = Context(
        entry=RegistryEntryStub(repository=repository, family="", platform="", ecosystem=""),
        facts=facts, readme=readme, tree_paths=(),
    )
    types = type_facts_by_name(list(facts.facts))
    rows: list[dict[str, object]] = []
    for number, _offset, name, cell in description_rows(ctx):
        found = types.get(name) or types.get(name.rsplit(".", 1)[-1]) or []
        if not found:
            continue
        fact = found[0]
        doc = (fact.attributes or {}).get("docstring") or ""
        rows.append(
            {"line": number, "type": name, "cell": cell[:160], "has_doc": bool(doc),
             "shape": cell_shape(cell, doc, fact.value)}
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--prompts", type=Path, default=REPO_ROOT / "prompts")
    parser.add_argument("--certified-only", action="store_true",
                        help="count only seals that re-certify under current code")
    parser.add_argument("--json", type=Path, default=None, help="write every row here")
    args = parser.parse_args(argv)
    entries = {entry.repository: entry for entry in load_registry(args.registry).entries}
    current = current_fingerprints(args.prompts)
    report: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="type-descriptions-") as tmp:
        scratch = Path(tmp)
        history = seal_history(remote=args.remote, scratch=scratch / "seals")
        results = recertify_history(
            history, entries=entries, current=current,
            fetch=lambda repo, rev: fetch_source(repo, rev, scratch / "src"),
        )
        for rec in results:
            seals = history.get((rec.repository, rec.lane)) or []
            bundle = getattr(seals[-1], "bundle", None) if seals else None
            if bundle is None or not (Path(bundle) / "facts.json").is_file():
                continue
            if args.certified_only and not rec.recertified:
                continue
            facts = read_facts(Path(bundle) / "facts.json")
            sealed = (Path(bundle) / "README.md").read_text(encoding="utf-8")
            after = rec.readme.decode("utf-8") if rec.readme else sealed
            report.append({
                "repository": rec.repository, "lane": rec.lane, "outcome": rec.outcome,
                "before": classify(sealed, facts, rec.repository),
                "after": classify(after, facts, rec.repository),
            })
    totals = {"before": Counter(), "after": Counter()}
    print(f"{'lane':<4} {'repository':<50} " + " ".join(f"{s[:9]:>9}" for s in SHAPES) + "  (before -> after)")
    for row in sorted(report, key=lambda r: (r["lane"], r["repository"])):
        before = Counter(r["shape"] for r in row["before"])
        after = Counter(r["shape"] for r in row["after"])
        totals["before"].update(before)
        totals["after"].update(after)
        if not row["before"]:
            continue
        cells = " ".join(
            f"{before[s]:>4}" + ("" if before[s] == after[s] else f">{after[s]}").ljust(5) for s in SHAPES
        )
        print(f"{row['lane']:<4} {row['repository']:<50} {cells}")
    for when in ("before", "after"):
        bad = sum(totals[when][s] for s in NON_DESCRIPTIVE)
        print(f"{when}: {dict(totals[when])}; non-descriptive {bad}")
    undocumented = sum(
        1 for row in report for r in row["after"] if r["shape"] in NON_DESCRIPTIVE and not r["has_doc"]
    )
    print(f"after, non-descriptive with no doc comment (reported, Lane R's to author): {undocumented}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
