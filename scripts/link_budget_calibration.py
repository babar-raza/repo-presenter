"""Measure the automatic Aspose-link ceiling against aspose.org's own finalized READMEs (read-only).

Reads every candidate directly from the sibling aspose.org checkout at run time; nothing from it is
stored or copied into this repository, only the counts this script prints. This is the tooling
``link_budget.py``'s ``_automatic_total`` calibration cites -- a docstring that asserts a specific
number without a script a reviewer can rerun to get the same number is model narration, not evidence
(``AGENTS.md``: "Evidence records come from tooling, never from model narration"); this script is
that evidence, and its output is reproducible by anyone with the sibling checkout, not fixed in prose.

Usage:
    python scripts/link_budget_calibration.py [--aspose-root PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.readme.composition.link_budget import (  # noqa: E402
    ContentMeasurement,
    classify_link,
    measure_content,
    resolve_link_budget,
    slot_violations,
)
from repo_presenter.readme.validation.links import extract_links  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _measure_one(path: Path, family: str, platform: str) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    banner = f"https://products.aspose.org/{family}/{platform}/"
    hrefs_all: list[str] = []
    hrefs_ctx: list[str] = []
    for token in extract_links(text):
        if token.kind != "external":
            continue
        host = (urlsplit(token.href).hostname or "").lower()
        if not (
            host == "aspose.org"
            or host.endswith(".aspose.org")
            or host == "aspose.com"
            or host.endswith(".aspose.com")
        ):
            continue
        hrefs_all.append(token.href)
        is_banner = token.href.rstrip("/") == banner.rstrip("/")
        is_enterprise = host == "products.aspose.com" or host.endswith(".products.aspose.com")
        if not (is_banner or is_enterprise):
            hrefs_ctx.append(token.href)
    fences = len(re.findall(r"^```(?!mermaid)", text, re.M)) // 2
    strict = measure_content(text, [])  # nothing counted as a verified example
    budget_strict = resolve_link_budget(strict)
    surfaces = Counter(
        (classify_link(href).surface or "other") for href in hrefs_ctx if classify_link(href)
    )
    return {
        "name": f"{family}/{platform}",
        "aspose_links_all": len(hrefs_all),
        "aspose_links_contextual": len(hrefs_ctx),
        "visible_prose_words": strict.visible_prose_words,
        "non_mermaid_fences": fences,
        "automatic_cap_strict": budget_strict.max_total,
        "fails_bc06_strict": bool(slot_violations(budget_strict, hrefs_ctx)),
        "contextual_surfaces": dict(surfaces),
    }


def measure(aspose_root: Path, registry_entries: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for entry in registry_entries:
        path = aspose_root / "reports" / "repo-presenter-regen-full" / entry["family"] / entry["platform"] / "readme.md"
        if not path.is_file():
            continue
        rows.append(_measure_one(path, entry["family"], entry["platform"]))
    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    words = [int(r["visible_prose_words"]) for r in rows]
    contextual = [int(r["aspose_links_contextual"]) for r in rows]
    all_links = [int(r["aspose_links_all"]) for r in rows]
    return {
        "candidates_measured": len(rows),
        "visible_prose_words_min": min(words) if words else None,
        "visible_prose_words_median": statistics.median(words) if words else None,
        "visible_prose_words_max": max(words) if words else None,
        "aspose_links_contextual_distribution": dict(sorted(Counter(contextual).items())),
        "aspose_links_all_distribution": dict(sorted(Counter(all_links).items())),
        "fails_bc06_strict_count": sum(1 for r in rows if r["fails_bc06_strict"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aspose-root", type=Path, default=REPO_ROOT.parent / "aspose.org")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.aspose_root.is_dir():
        print(f"error: {args.aspose_root} is not a directory", file=sys.stderr)
        return 1
    entries = json.loads(args.registry.read_text(encoding="utf-8"))["entries"]
    rows = measure(args.aspose_root, entries)
    summary = summarize(rows)
    if args.json:
        print(json.dumps({"rows": rows, "summary": summary}, indent=2))
    else:
        for row in rows:
            print(
                f"{row['name']:<60} words={row['visible_prose_words']:>5} "
                f"ctx_links={row['aspose_links_contextual']} all_links={row['aspose_links_all']} "
                f"cap_strict={row['automatic_cap_strict']} fails_bc06={row['fails_bc06_strict']}"
            )
        print()
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
