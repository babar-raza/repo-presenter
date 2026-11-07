#!/usr/bin/env python3
"""TC-018: build the byte-computed content ledger for one or more sealed bundles.

Zero provider calls, zero writes to any sealed bundle or candidate: this script only reads
already-materialized bundle directories (``facts.json``, ``dispositions.json``, ``README.md``)
and writes one ``content_ledger.json`` per bundle, next to the bundle unless ``--out`` says
otherwise.

Three ways to point it at bundles, in order of preference for an offline, read-only run:

* ``--bundle-dir PATH`` (repeatable): an already-materialized bundle directory -- this
  repository's own committed ``candidates/<slug>/<revision>/`` trees qualify directly, with no
  network at all.
* ``--repository ORG/NAME --lane {R,L}`` (repeatable pair): read the sealed history of one
  lane/repository off the state remote (``core.state.bundle_store.seal_history``; network,
  read-only, nothing pushed) and build a ledger for its latest good seal.
* ``--self-test``: no bundle, no network -- builds a ledger over a small in-memory fixture that
  exercises every piece kind (code_block, table_item, list_item, sentence, heading, badge_row)
  and asserts it accounts for every one of them, then exits 0. This is what
  ``project/taskcards/TC-018.yaml``'s own ``checks[]`` runs; the other two modes are this card's
  "run it over at least 3 real existing sealed bundles" evidence, run by hand (see the card's
  closeout) since they need either a local candidates/ checkout or network reachability this
  automated check must not depend on.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.readme.obligations.ledger import (  # noqa: E402
    LedgerEntry,
    build_ledger,
    example_polarity_by_unit,
    public_symbol_names,
)


def _tree_paths_from_dependencies(bundle_dir: Path) -> list[str]:
    """Best-effort file list for path-existence checks, from ``dependencies.json`` when present
    (its own file inventory is the closest thing a materialized bundle carries to the original
    tree listing; when it is absent or unreadable, link/path obligations fall back to
    ``undecided`` rather than a guess, exactly like a missing probe answer)."""
    path = bundle_dir / "dependencies.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict) and isinstance(data.get("tree_paths"), list):
        return [str(p) for p in data["tree_paths"]]
    return []


def ledger_from_bundle_dir(bundle_dir: Path) -> list[LedgerEntry]:
    """Read one materialized bundle directory and build its content ledger."""
    facts_doc = json.loads((bundle_dir / "facts.json").read_text(encoding="utf-8"))
    facts = facts_doc["facts"]
    dispositions_doc = json.loads((bundle_dir / "dispositions.json").read_text(encoding="utf-8"))
    dispositions = {
        str(entry.get("unit_id", "")): str(entry.get("disposition", ""))
        for entry in dispositions_doc.get("dispositions", [])
    }
    readme = (bundle_dir / "README.md").read_text(encoding="utf-8")
    inherited = [
        {
            "id": fact["id"],
            "kind": fact["id"].rsplit(".", 1)[-1] if "." in fact["id"] else "",
            "text": str(fact.get("value") or ""),
        }
        for fact in facts
        if fact.get("kind") == "inherited_unit"
    ]
    return build_ledger(
        inherited_units=inherited,
        readme=readme,
        public_names=public_symbol_names(facts),
        example_polarity=example_polarity_by_unit(facts),
        tree_paths=_tree_paths_from_dependencies(bundle_dir),
        dispositions=dispositions,
    )


def _write_ledger(entries: list[LedgerEntry], out_path: Path, *, repository: str, lane: str, revision: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "repository": repository,
        "lane": lane,
        "revision": revision,
        "entries": [entry.to_dict() for entry in entries],
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summarize(label: str, entries: list[LedgerEntry]) -> None:
    from collections import Counter

    by_obligation = Counter(entry.obligation for entry in entries)
    violations = sum(1 for entry in entries if entry.obligation == "must_carry" and entry.carried is False)
    print(
        f"{label}: {len(entries)} piece(s) -- "
        f"must_carry={by_obligation['must_carry']} may_drop={by_obligation['may_drop']} "
        f"undecided={by_obligation['undecided']} ; {violations} must_carry piece(s) not stated"
    )


def _run_self_test() -> int:
    """No bundle, no network: every piece kind, decided, and the ledger accounts for all of them."""
    readme = "\n".join(
        [
            "# Foo",
            "",
            "## API Reference",
            "",
            "| Name | Description |",
            "| --- | --- |",
            "| `Widget` | Represents a widget and its drawing surface. |",
            "",
            "Call `Widget.Save()` to persist a widget. Requires version 1.2.3.",
            "",
            f"{'`' * 3}mermaid",
            "graph TD\n  A --> B",
            f"{'`' * 3}",
        ]
    )
    inherited = [
        {"id": "inherited_unit:001.heading", "kind": "heading", "text": "# Foo"},
        {
            "id": "inherited_unit:002.badge_row",
            "kind": "badge_row",
            "text": "[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)",
        },
        {
            "id": "inherited_unit:003.code_block",
            "kind": "code_block",
            "text": f"{'`' * 3}python\nwidget = Widget()\nwidget.save()\n{'`' * 3}",
        },
        {
            "id": "inherited_unit:004.table",
            "kind": "table",
            "text": "| `Widget` | Represents a widget and its drawing surface. |\n"
            "| `_InternalCache` | Internal cache, not part of the public API. |",
        },
        {
            "id": "inherited_unit:005.list",
            "kind": "list",
            "text": "- See [the guide](docs/guide.md) for more.\n- Collected below for reference.",
        },
        {
            "id": "inherited_unit:006.paragraph",
            "kind": "paragraph",
            "text": "Call `Widget.Save()` to persist a widget. Requires version 1.2.3.",
        },
    ]
    dispositions = {
        "inherited_unit:001.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:002.badge_row": "SUPERSEDE_REDUNDANT",
        "inherited_unit:003.code_block": "OMIT_UNSUPPORTED",
        "inherited_unit:004.table": "VERIFIED_REWRITE",
        "inherited_unit:005.list": "OMIT_UNSUPPORTED",
        "inherited_unit:006.paragraph": "VERIFIED_PRESERVE",
    }
    entries = build_ledger(
        inherited_units=inherited,
        readme=readme,
        public_names=frozenset({"widget", "save"}),
        example_polarity={},
        tree_paths=["docs/guide.md"],
        dispositions=dispositions,
    )
    expected_pieces = {
        ("heading", "heading"),
        ("badge_row", "badge_row"),
        ("code_block", "code_block"),
        ("table", "Widget"),
        ("table", "_InternalCache"),
    }
    seen_units = {entry.unit_id for entry in entries}
    assert len(entries) >= 6, f"expected at least 6 pieces, built {len(entries)}"
    assert seen_units == set(dispositions), (seen_units, set(dispositions))
    kinds = {entry.piece_kind for entry in entries}
    assert kinds == {"heading", "badge_row", "code_block", "table_item", "list_item", "sentence"}, kinds
    widget_row = next(
        e for e in entries if e.piece_kind == "table_item" and "_InternalCache" not in e.text
    )
    internal_row = next(e for e in entries if e.piece_kind == "table_item" and "_InternalCache" in e.text)
    assert widget_row.obligation == "must_carry", widget_row
    assert internal_row.obligation == "may_drop", internal_row
    heading = next(e for e in entries if e.piece_kind == "heading")
    assert heading.obligation == "may_drop", heading
    badge = next(e for e in entries if e.piece_kind == "badge_row")
    assert badge.obligation == "may_drop", badge
    for entry in entries:
        assert entry.obligation in ("must_carry", "may_drop", "undecided"), entry
        if entry.obligation == "must_carry":
            assert entry.carried in (True, False), entry
        else:
            assert entry.carried is None, entry
    _summarize("self-test", entries)
    print("OK: build_content_ledger.py self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--bundle-dir", action="append", default=[], metavar="PATH")
    parser.add_argument("--repository", action="append", default=[], metavar="ORG/NAME")
    parser.add_argument("--lane", action="append", default=[], choices=["R", "L"])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--out", default=None, metavar="DIR")
    args = parser.parse_args(argv)

    if args.self_test:
        return _run_self_test()

    ran = False
    for raw in args.bundle_dir:
        bundle_dir = Path(raw)
        entries = ledger_from_bundle_dir(bundle_dir)
        repository = bundle_dir.parent.name
        revision = bundle_dir.name
        out_dir = Path(args.out) if args.out else bundle_dir
        out_path = out_dir / "content_ledger.json"
        _write_ledger(entries, out_path, repository=repository, lane="?", revision=revision)
        _summarize(f"{bundle_dir}", entries)
        print(f"wrote {out_path}")
        ran = True

    if args.repository:
        from repo_presenter.core.state.bundle_store import seal_history

        import tempfile

        lanes = args.lane or ["R"]
        wanted = set(args.repository)
        with tempfile.TemporaryDirectory(prefix="content-ledger-") as scratch:
            history = seal_history(remote=args.remote, scratch=Path(scratch))
            for (repository, lane), seals in history.items():
                if repository not in wanted or lane not in lanes:
                    continue
                good = [s for s in seals if s.pipeline_good and s.bundle is not None]
                if not good:
                    print(f"{repository} ({lane}): no pipeline-good seal to read", file=sys.stderr)
                    continue
                latest = good[-1]
                entries = ledger_from_bundle_dir(latest.bundle)
                out_dir = Path(args.out) if args.out else Path("content_ledgers") / lane
                out_path = out_dir / f"{repository.replace('/', '__')}.content_ledger.json"
                _write_ledger(entries, out_path, repository=repository, lane=lane, revision=latest.revision)
                _summarize(f"{repository} ({lane}) @ {latest.revision[:12]}", entries)
                print(f"wrote {out_path}")
                ran = True

    if not ran:
        parser.error("nothing to do: pass --self-test, --bundle-dir, or --repository/--lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
