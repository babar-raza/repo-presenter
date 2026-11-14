"""Report-only measurement of the M9 auditor's derivation rule (``run_m9_auditor.derivation``) over
every sealed README (O6 / docs/RULINGS.md checklist item 13: a new deterministic rule lands only after a
report-only run shows its false-positive rate). Zero provider calls.

For every seal of every bundle ref (or a materialized seal tree, ``--seals``), the rule is run with the
seal's own README as the case text: a clean seal is its own clean control, so every underived line is
a false positive of the rule unless that seal no longer re-derives under current code (a stale seal,
reported separately). Writes one JSON document and prints the per-lane rates.

    PYTHONPATH=src python scripts/measure_m9_derivation.py --seals DIR --out FILE [--fetch-trees]

``replay`` re-scores one hosted round's FROZEN findings under the current auditor and writer, zero calls
(BL-013): the case texts are rebuilt from the seals the seeder read (the latest seal of each case at its
revision sealed no later than ``--seeded-at``; each seeded case re-seeded by the operator whose line the
published ``missed_seeded`` list or a frozen flag names), every case's derivation is applied to its frozen
rows (``run_m9_auditor.apply_derivation``), the writer's deterministic adjudication runs over the result,
and ``run_acceptance_writer.evaluate_gates`` scores it with the round's own controls-not-recertified list.
``--texts recertified`` replaces each control's text by its re-certification under current code (the seal
the next round would audit), keeping the frozen flags on their lines -- a projection, reported as such.

    PYTHONPATH=src python scripts/measure_m9_derivation.py replay --case-index F --findings F --records F \\
        --seeded-at 2026-11-14T05:02:48Z --out FILE [--texts frozen|recertified] [--no-provenance]
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


def _seal_time(seal: SimpleNamespace) -> str:
    try:
        manifest = json.loads((Path(seal.bundle) / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ""
    return str(manifest.get("recertified_at") or manifest.get("sealed_at") or "")


def _history(seals_dir: Path | None, remote: str, work: Path) -> dict:
    """``seal_history`` -- or, with ``seals_dir`` (a tree ``seal_history(scratch=...)`` left), the same
    records read from disk, each lane's seals ordered by their manifest's seal time."""
    if seals_dir is None:
        from repo_presenter.core.state.bundle_store import seal_history

        return seal_history(remote=remote, scratch=work / "seals")
    history: dict = {}
    for seal in materialized_seals(seals_dir):
        seal.commit, seal.error = Path(seal.bundle).parent.name, ""
        history.setdefault((seal.repository, seal.lane), []).append(seal)
    for seals in history.values():
        seals.sort(key=_seal_time)
    return history


def _seeded_text(case_id: str, text: str, missed_line: int | None, flagged: set[int]) -> tuple[str, dict] | None:
    """The seeder's mutation of ``text`` whose seeded line is ``missed_line`` (a published miss) or,
    when none is given, one a frozen flag sits on; ``None`` when no operator reproduces either."""
    from repo_presenter.acceptance.audit.seed import OPERATORS_BY_SHAPE, SeedingError, seed_defect

    for shape, operators in OPERATORS_BY_SHAPE.items():
        for operator in operators:
            try:
                result = seed_defect(case_id, text, operator)
            except SeedingError:
                continue
            line = result.record.line
            entry = {"candidate_id": case_id, "shape": shape, "operator": operator, "line": line}
            if (missed_line is not None and line == missed_line) or (missed_line is None and line in flagged):
                return result.seeded_readme, entry
    return None


def replay(args: argparse.Namespace) -> dict:
    """See the module docstring (``replay``)."""
    from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE
    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed
    from repo_presenter.recertify import current_surface as shipped_facts, fetch_source, recertify_bundle

    spec = importlib.util.spec_from_file_location("run_acceptance_writer", REPO_ROOT / "scripts" / "run_acceptance_writer.py")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    if args.no_provenance:  # the auditor before the K05/K10 provenance step, for the per-step report
        auditor.class_provenance = lambda *_a, **_k: None
        auditor.count_provenance = lambda *_a, **_k: None
    case_index = json.loads(args.case_index.read_text(encoding="utf-8"))
    frozen = json.loads(args.findings.read_text(encoding="utf-8"))
    records = json.loads(args.records.read_text(encoding="utf-8"))
    roles = {r["case_id"]: r["role"] for r in records["records"]}
    missed = {m["case_id"]: m["line"] for m in records.get("missed_seeded", [])}
    not_recertified = list(records["gates"].get("controls_not_recertified", []))
    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    rows_by_case: dict[str, list[dict]] = {}
    for row in frozen:
        rows_by_case.setdefault(str(row["candidate_id"]), []).append(row)
    out: dict = {"schema": "m9-round-replay/1", "texts": args.texts, "provenance_step": not args.no_provenance,
                 "cases": []}
    with tempfile.TemporaryDirectory(prefix="m9-replay-") as tmp:
        work = Path(tmp)
        history = _history(args.seals, args.remote, work)
        sources: dict[tuple[str, str], object] = {}

        def fetch(repository: str, revision: str, _workdir: Path | None = None):
            if (repository, revision) not in sources:
                sources[(repository, revision)] = fetch_source(repository, revision, work / "src")
            return sources[(repository, revision)]

        manifest: list[dict] = []
        findings: list[dict] = []
        evidence: dict = {}
        texts: dict[str, str] = {}
        for entry in case_index:
            case_id, repository, lane, revision = (str(entry[k]) for k in ("case_id", "repository", "lane", "revision"))
            listed = require_listed(registry, repository)
            seals = [s for s in history.get((repository, lane), []) if s.revision == revision and s.bundle
                     and not s.error and _seal_time(s) <= args.seeded_at]
            row: dict = {"case_id": case_id, "repository": repository, "lane": lane, "role": roles.get(case_id)}
            out["cases"].append(row)
            if not seals:
                row["status"] = "no seal"
                continue
            seal = seals[-1]
            row["seal_commit"] = seal.commit
            sealed = (Path(seal.bundle) / "README.md").read_text(encoding="utf-8")
            text = sealed
            mine = rows_by_case.get(case_id, [])
            flagged = {r["line"] for r in mine if r.get("verdict") != "supported"}
            if roles.get(case_id) == "seeded":
                seeded = _seeded_text(case_id, sealed, missed.get(case_id), flagged)
                if seeded is None:
                    row["status"] = "seed not reproduced"
                    continue
                text, record = seeded
                manifest.append(record)
                row["seed"] = record
            else:
                manifest.append({"candidate_id": case_id, "shape": CLEAN_SHAPE, "line": None})
                if args.texts == "recertified":
                    rec = recertify_bundle(Path(seal.bundle), lane, entry=listed, source=fetch(repository, revision))
                    if rec.readme is not None:
                        text = rec.readme.decode("utf-8")
                        row["recertified"] = {"outcome": rec.outcome, "readme_changed": text != sealed,
                                              "same_line_count": len(text.splitlines()) == len(sealed.splitlines())}
            texts[case_id] = text
            asked = frozenset(r["line"] for r in mine if r.get("source") == "llm" and r.get("located")
                              and r.get("verdict") != "supported")
            derived = auditor.case_derivation(seal, text, work / "trees", fetch=fetch, ask=asked)
            applied = auditor.apply_derivation(case_id, text, mine, derived)
            findings.extend(applied)
            row.update(status="ok" if derived is not None else "derivation unavailable",
                       flags=[{"line": r["line"], "source": r.get("source"), "kept_because": r.get("kept_because"),
                               "claim": str(r.get("claim", ""))[:160]}
                              for r in applied if r.get("verdict") != "supported"],
                       cleared=[{"line": r["line"], "provenance": r.get("provenance")}
                                for r in applied if r.get("cleared_by") == "derivation"])
            facts = read_facts(Path(seal.bundle) / "facts.json")
            if lane == "L" or listed.ecosystem == "python":  # the facts the current pipeline holds (BL-065)
                facts = shipped_facts(facts, listed.ecosystem, fetch(repository, revision))[0]
            original_path = Path(seal.bundle) / "README.original.md"
            original = original_path.read_text(encoding="utf-8") if original_path.is_file() else ""
            clearable = auditor.case_derivation(seal, text, work / "trees", fetch=fetch, ask=frozenset(flagged))
            derived_lines = writer.derived_lines(lane, text, facts, Path(seal.bundle), original)
            evidence[case_id] = writer.CaseEvidence(
                lane=lane, facts=facts, sealed=text,
                derived=derived_lines & clearable.clearable if clearable is not None else frozenset(),
                certified=case_id not in not_recertified,
            )
        adjudications = writer.deterministic_adjudications(findings, texts, evidence)
        gates, reasons = writer.evaluate_gates(manifest, findings, adjudications, not_recertified)
    adjudicated = {(a["candidate_id"], a["line"]): a["adjudication"] for a in adjudications}
    for row in out["cases"]:
        for flag in row.get("flags", []):
            flag["adjudication"] = adjudicated.get((row["case_id"], flag["line"]))
    clean = {m["candidate_id"] for m in manifest if m["shape"] == CLEAN_SHAPE and m["candidate_id"] not in not_recertified}
    flagged_controls = sorted({
        str(f["candidate_id"]) for f in findings
        if str(f["candidate_id"]) in clean and f.get("verdict") != "supported"
        and adjudicated.get((str(f["candidate_id"]), f.get("line"))) != "confirmed"
    })
    out.update(gates=gates, failed_reasons=reasons, flagged_controls=flagged_controls,
               reproduced=f"{len(manifest)}/{len(case_index)} cases")
    return out


def classes(args: argparse.Namespace) -> dict:
    """Report-only (O6): every K05 count / K10 Enterprise Edition line of every latest seal and of its
    live README, with whether its provenance verifies it under current code (``class_provenance`` over
    the facts after ``recertify.shipped_facts``) and whether an OPEN register row refutes it. A verified
    line a register row refutes is a false positive of the provenance rule taken alone."""
    import re

    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed
    from repo_presenter.recertify import current_surface as shipped_facts, fetch_source

    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    register = auditor.load_register()
    patterns = {label: re.compile(p, re.I) for label, p in auditor.KNOWN_FALSE_PATTERNS if label[:3] in ("K05", "K10")}
    rows_out: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="m9-classes-") as tmp:
        history = _history(args.seals, args.remote, Path(tmp))
        for (repository, lane), seals in sorted(history.items()):
            latest = next((s for s in reversed(seals) if s.bundle and not s.error), None)
            if latest is None:
                continue
            listed = require_listed(registry, repository)
            facts = read_facts(Path(latest.bundle) / "facts.json")
            try:
                facts = shipped_facts(facts, listed.ecosystem, fetch_source(repository, latest.revision, Path(tmp) / "src"))[0]
            except Exception as error:  # noqa: BLE001 -- unreadable source: the sealed facts as they are
                print(f"{repository}: source unreadable ({error}); sealed facts used", file=sys.stderr)
            for kind, name in (("seal", "README.md"), ("live", "README.original.md")):
                path = Path(latest.bundle) / name
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
                refuted = auditor.refuted_lines(text, facts, repository, register)
                for number, row in enumerate(lines, 1):
                    for label, pattern in patterns.items():
                        if not pattern.search(row):
                            continue
                        proof = auditor.class_provenance(label, lines, number, facts)
                        rows_out.append({"repository": repository, "lane": lane, "readme": kind, "line": number,
                                         "class": label[:3], "verified": proof is not None,
                                         "refuted_by": refuted.get(number), "text": row.strip()[:200]})
    summary: dict = {}
    for kind in ("seal", "live"):
        for label in ("K05", "K10"):
            mine = [r for r in rows_out if r["readme"] == kind and r["class"] == label]
            verified = [r for r in mine if r["verified"]]
            summary[f"{kind}/{label}"] = {
                "lines": len(mine), "verified": len(verified),
                "verified_but_refuted": sum(1 for r in verified if r["refuted_by"]),
                "false_positive_rate": round(sum(1 for r in verified if r["refuted_by"]) / len(verified), 4) if verified else None,
            }
    return {"schema": "m9-known-false-classes/1", "summary": summary, "lines": rows_out}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "classes":
        parser = argparse.ArgumentParser(description="report-only K05/K10 provenance over every latest seal")
        parser.add_argument("cmd")
        parser.add_argument("--remote", default="origin")
        parser.add_argument("--seals", type=Path, help="materialized seal tree (seal_history scratch)")
        parser.add_argument("--out", type=Path, required=True)
        args = parser.parse_args()
        document = classes(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(document["summary"], sort_keys=True))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        parser = argparse.ArgumentParser(description="replay a frozen M9 round (module docstring)")
        parser.add_argument("cmd")
        parser.add_argument("--case-index", type=Path, required=True)
        parser.add_argument("--findings", type=Path, required=True)
        parser.add_argument("--records", type=Path, required=True)
        parser.add_argument("--seeded-at", required=True, help="the seed commit's time (ISO 8601, UTC)")
        parser.add_argument("--texts", choices=("frozen", "recertified"), default="frozen")
        parser.add_argument("--no-provenance", action="store_true", help="measure without the K05/K10 provenance step")
        parser.add_argument("--remote", default="origin")
        parser.add_argument("--seals", type=Path, help="materialized seal tree (seal_history scratch)")
        parser.add_argument("--out", type=Path, required=True)
        args = parser.parse_args()
        document = replay(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"gates": {k: document["gates"].get(k) for k in ("seeded_recall", "false_flag_rate")},
                          "flagged_controls": document["flagged_controls"], "reproduced": document["reproduced"]},
                         sort_keys=True))
        return 0
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
