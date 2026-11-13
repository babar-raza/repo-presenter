"""Which printed README examples were actually executed? An exact, zero-call audit of the seals.

The owner's question "are all examples verified?" answered from the sealed bundles themselves: for
every certified seal, every fence of the README whose language is one of the ecosystem's example
aliases (``EcosystemSpec.example_fences``, the fences BC-03 judges) is mapped to its ``example``
fact by the pipeline's own identity - the normalized code (``retained_examples.normalized_code``)
of the fact's value or of ``printed_example(fact)`` (the value with the verifier's prelude) - and
reported with that fact's polarity (SUPPORTED = executed or compiled, CONTRADICTED = failed,
UNRESOLVED = never checked) and the cause class its receipt names.

    python scripts/printed_example_audit.py                              # data/recertification_baseline.json
    python scripts/printed_example_audit.py --rows recert_all.json --json out.json

Rows are RECERTIFIED entries carrying repository, lane, revision and the seal commit (``commit``
or ``seal_commit``); bundles are read with ``git show`` from the fetched state refs
(``git fetch origin '+refs/repository-presenter-state/*:refs/repository-presenter-state/*'``).
No provider call, no upstream access.
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import printed_example
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.retained_examples import (
    normalized_code,
)
from repo_presenter.readme.validation.text import fences

#: Receipt wording -> cause class, first match wins. Each phrase is one a verifier writes.
CAUSES: tuple[tuple[str, str], ...] = (
    ("NU190", "toolchain: NuGet vulnerability audit as error (date-dependent, not the revision)"),
    ("Cargo toolchain did not report a version", "toolchain: rustup proxy started as rustup"),
    ("this tsc refuses these options", "toolchain: machine tsc refuses the package's options"),
    ("the product's own build failed", "product build failed (LFS pointer build inputs)"),
    ("BLOCKED_TOOLCHAIN", "toolchain: other"),
    ("without binding it", "fragment: uses a name bound elsewhere"),
    ("fragment, not a contradiction", "fragment: uses a name bound elsewhere"),
    ("cannot tell which import binds it", "fragment: ambiguous import"),
    ("NEEDS_INPUT", "needs an input file the repository does not provide"),
    ("TIMED_OUT", "timed out"),
    (": FAILED; NameError", "failed: NameError (README import not supplied)"),
    (": FAILED", "failed: the code is wrong at this revision"),
)


def cause(receipt: str) -> str:
    """The cause class a receipt's own wording names, or 'other'."""
    for phrase, label in CAUSES:
        if phrase in receipt:
            return label
    return "other"


def _receipt(fact: Fact) -> str:
    return " | ".join(evidence.detail or "" for evidence in fact.evidence[1:])


def audit_readme(readme: str, facts: FactsDocument, ecosystem: str) -> list[dict[str, Any]]:
    """One row per printed example fence: its fact, polarity, and the cause its receipt names."""
    plugin_for(ecosystem)  # a platform registers its EcosystemSpec on import
    aliases = spec_for(ecosystem).example_fences
    examples = facts.by_kind("example")
    by_code: dict[str, Fact] = {}
    for fact in examples:
        for code in (normalized_code(fact.value), normalized_code(printed_example(fact))):
            by_code.setdefault(code, fact)
    rows: list[dict[str, Any]] = []
    for language, body in fences(readme):
        if language not in aliases:
            continue
        fact = by_code.get(normalized_code(body))
        receipt = _receipt(fact) if fact else ""
        rows.append(
            {
                "language": language,
                "fact": fact.id if fact else None,
                "polarity": fact.polarity if fact else "NO_FACT",
                "cause": "" if fact is None or fact.polarity == "SUPPORTED" else cause(receipt),
                "receipt": receipt[:300],
                "first_line": next((line for line in body.splitlines() if line.strip()), "")[:80],
            }
        )
    return rows


def _facts(payload: Mapping[str, Any]) -> FactsDocument:
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(
            Fact(
                id=record["id"],
                kind=record["kind"],
                value=record["value"],
                evidence=tuple(Evidence(e["path"], e.get("detail")) for e in record["evidence"]),
                polarity=record.get("polarity", "SUPPORTED"),
                confidence=record.get("confidence", 1.0),
                attributes=record.get("attributes"),
            )
            for record in payload["facts"]
        ),
        schema_version=payload.get("schema_version", 1),
    )


def _show(commit: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], capture_output=True, text=True, check=True
    ).stdout


def audit_seals(
    rows: Iterable[Mapping[str, Any]], ecosystems: Mapping[str, str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("outcome") != "RECERTIFIED":
            continue
        commit = row.get("seal_commit") or row["commit"]
        revision = row["revision"]
        readme = _show(commit, f"{revision}/README.md")
        facts = _facts(json.loads(_show(commit, f"{revision}/facts.json")))
        ecosystem = ecosystems[row["repository"]]
        for printed in audit_readme(readme, facts, ecosystem):
            out.append(
                {"repository": row["repository"], "lane": row["lane"], "ecosystem": ecosystem,
                 **printed}
            )
    return out


def summary(printed: list[dict[str, Any]]) -> dict[str, Any]:
    def count(key: Any) -> dict[str, dict[str, int]]:
        table: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        for row in printed:
            table[key(row)][row["polarity"]] += 1
        return {name: dict(counter) for name, counter in sorted(table.items())}

    return {
        "printed": len(printed),
        "polarity": dict(collections.Counter(row["polarity"] for row in printed)),
        "by_lane": count(lambda row: row["lane"]),
        "by_ecosystem": count(lambda row: row["ecosystem"]),
        "by_seal": count(lambda row: f"{row['lane']} {row['repository']}"),
        "causes": dict(
            collections.Counter(row["cause"] for row in printed if row["cause"]).most_common()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, default=None,
                        help="recertification rows JSON (a list); default: the baseline's seals")
    parser.add_argument("--baseline", type=Path, default=Path("data/recertification_baseline.json"))
    parser.add_argument("--registry", type=Path, default=Path("data/registry.json"))
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = (
        json.loads(args.rows.read_text("utf-8"))
        if args.rows
        else json.loads(args.baseline.read_text("utf-8"))["seals"]
    )
    ecosystems = {
        entry["repository"]: entry["ecosystem"]
        for entry in json.loads(args.registry.read_text("utf-8"))["entries"]
    }
    printed = audit_seals(rows, ecosystems)
    report = summary(printed)
    print(json.dumps(report, indent=2))
    if args.json:
        args.json.write_text(json.dumps({"summary": report, "printed": printed}, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
