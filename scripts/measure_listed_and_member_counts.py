"""Report-only (O6 / docs/RULINGS.md checklist 13) measurement of two rule changes over every latest seal's
README and its live README, zero provider calls:

* BL-093 -- rule (h)'s listing phrase widened from "listed below" to every listing verb
  (``surface_claims._LISTED_HERE``): each count sentence the widened rule holds to the type-table rows
  that follow, the rows, and whether the old rule read it too. A hit is a sentence stating more public
  types than the rows that follow, not saying how many are listed;
* BL-098 -- count cells ("Class with 11 properties.") held to each class fact's ``member_counts``
  (``type_description.true_count_cell``), with the facts as re-certification reads them
  (``recertify.current_surface``: the build's package list, member counts from the pinned sources).

Every hit is listed with its text, so each can be judged by hand; the summary gives the counts.

    PYTHONPATH=src python scripts/measure_listed_and_member_counts.py --seals DIR --out FILE
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

#: rule (h)'s listing phrase before BL-093, for the before/after comparison
_OLD_LISTED = re.compile(
    r"(?i)\b(?:(?:is|are)\s+)?listed\s+(?:below|here|in\s+the\s+(?:table|tables)\s+below)\b|\bas\s+follows\b"
)


def latest_bundles(seals: Path) -> dict[tuple[str, str], Path]:
    found: dict[tuple[str, str], tuple[str, Path]] = {}
    for manifest in seals.glob("*/*/*/*/manifest.json"):
        lane, slug = manifest.parts[-5], manifest.parts[-4]
        data = json.loads(manifest.read_text(encoding="utf-8"))
        when = str(data.get("recertified_at") or data.get("sealed_at") or "")
        if (lane, slug) not in found or when > found[(lane, slug)][0]:
            found[(lane, slug)] = (when, manifest.parent)
    return {key: bundle for key, (_when, bundle) in found.items()}


def listed_hits(text: str, facts) -> list[dict]:
    from repo_presenter.readme.validation import surface_claims as sc

    from repo_presenter.readme.validation.claims import _lines

    lines = _lines(text)
    out = []
    types, _classes = sc.type_counts(facts)
    for sentence, first, last in sc._sentences(lines):
        plain = sentence.replace("`", "")
        for match in sc._TYPE_COUNT.finditer(plain):
            if not (sc._PUBLIC_QUALIFIER.search(match.group("qualifiers")) or sc._PUBLIC_CONTEXT.search(plain)):
                continue
            new, old = sc._LISTED_HERE.search(plain), _OLD_LISTED.search(plain)
            if not new:
                continue
            stated = int(match.group("count").replace(",", ""))
            rows = sc._rows_listed_after(lines, last)
            hit = bool(rows) and rows < stated and not sc.states_listed_count(plain, rows)
            out.append({"line": first + 1, "stated": stated, "facts_types": types, "rows": rows, "hit": hit,
                        "old_rule_reads_it": bool(old), "phrase": new.group(0), "text": " ".join(plain.split())[:220]})
    return out


def count_cell_hits(text: str, facts) -> list[dict]:
    from repo_presenter.readme.correction.detectors import type_description as td

    types = td.type_facts_by_name(list(facts.facts))
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        row = re.match(r"^\s*\|\s*`([A-Za-z_][\w.]*)`\s*\|\s*([^|]+?)\s*\|\s*$", line)
        if not row or not td._COUNT.match(td._plain(row.group(2))):
            continue
        candidates = types.get(row.group(1)) or types.get(row.group(1).rsplit(".", 1)[-1]) or []
        if len(candidates) != 1 or td.member_counts(candidates[0]) is None:
            out.append({"line": number, "type": row.group(1), "cell": row.group(2), "judged": False})
            continue
        fixed = td.true_count_cell(row.group(2), candidates[0])
        out.append({"line": number, "type": row.group(1), "cell": row.group(2), "judged": True,
                    "member_counts": (candidates[0].attributes or {}).get("member_counts"),
                    "hit": fixed is not None, "true_cell": fixed})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seals", type=Path, required=True, help="materialized seal tree (seal_history scratch)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed
    from repo_presenter.recertify import current_surface, fetch_source

    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="measure-listed-") as work:
        sources: dict = {}
        for (lane, slug), bundle in sorted(latest_bundles(args.seals).items()):
            repository = slug.replace("__", "/", 1)
            ecosystem = require_listed(registry, repository).ecosystem
            facts = read_facts(bundle / "facts.json")
            key = (repository, bundle.name)
            if key not in sources:
                try:
                    sources[key] = fetch_source(repository, bundle.name, Path(work))
                except Exception as error:  # noqa: BLE001 -- sealed facts as they are
                    print(f"{repository}: {error}", file=sys.stderr)
                    sources[key] = None
            if sources[key] is not None:
                facts = current_surface(facts, ecosystem, sources[key])[0]
            for name, kind in (("README.md", "seal"), ("README.original.md", "live")):
                path = bundle / name
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                for hit in listed_hits(text, facts):
                    rows.append({"rule": "listed", "repository": repository, "lane": lane, "readme": kind, **hit})
                for hit in count_cell_hits(text, facts):
                    rows.append({"rule": "member_count", "repository": repository, "lane": lane, "readme": kind, **hit})
    summary: dict = {}
    for kind in ("seal", "live"):
        listed = [r for r in rows if r["rule"] == "listed" and r["readme"] == kind]
        cells = [r for r in rows if r["rule"] == "member_count" and r["readme"] == kind]
        summary[kind] = {
            "listed_sentences_read": len(listed),
            "listed_hits": sum(r["hit"] for r in listed),
            "listed_hits_new_to_widened_rule": sum(r["hit"] and not r["old_rule_reads_it"] for r in listed),
            "count_cells": len(cells),
            "count_cells_judged": sum(r["judged"] for r in cells),
            "count_cell_hits": sum(bool(r.get("hit")) for r in cells),
        }
    document = {"schema": "listed-and-member-counts/1", "summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
