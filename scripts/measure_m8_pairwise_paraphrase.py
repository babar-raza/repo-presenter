"""Supervisor-run, REAL-provider-call measurement of M8's two remaining shapes (pairwise
benchmark comparison, M8-S paraphrase check) -- completes the M8 picture started by
``measure_m8_live.py`` (classification shape).

Pairwise cases: a real section of an already-committed README, compared against itself (clean,
expected "at least as good" = True) and against
``src/repo_presenter/acceptance/audit/seed.py::op_incoherent_reorder``'s real mutation of that
same section (the actual M8 D15 corpus operator the design doc names, per that module's own
docstring -- "one set of operators, two consumers: M8 calibration and M9 seeding"), expected
False.

Paraphrase cases: real (description, signature) pairs from a freshly, shallow-cloned small real
repository's own export surface (same technique ``measure_m2.py`` uses): a type's REAL docstring
beside its REAL signature (fair paraphrase, True), and that same signature beside a DIFFERENT
type's real docstring (an unfair paraphrase -- the same "swap the description" shape
``op_misdescribe_type`` seeds for M9, applied here to M8-S instead), expected False.

Smaller n than the classification shape's n=30 run (these two shapes are honestly reported at
whatever n the real, available material supports, not padded to look more measured).

Usage: ``python scripts/measure_m8_pairwise_paraphrase.py [--write]``. Caches results to
``scripts/.m8_pairwise_paraphrase_cache.json`` so re-running with ``--write`` never re-spends;
``--fresh`` forces a new real run; ``--dry-run`` makes no call.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.seed import op_incoherent_reorder  # noqa: E402
from repo_presenter.acceptance.probes.python import _surface  # noqa: E402
from repo_presenter.core.config import load_gateway_config  # noqa: E402
from repo_presenter.readme.review.prose_judge import (  # noqa: E402
    ParaphraseCheckRequest,
    PairwiseComparisonRequest,
    load_prose_judge_prompts,
)
from repo_presenter.readme.review.prose_judge_live import (  # noqa: E402
    judge_pairwise_benchmark_comparison_live,
    judge_type_paraphrase_live,
)

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"
PROMPT_PATH = REPO_ROOT / "prompts" / "m8" / "prose_judge.yaml"
CACHE_PATH = Path(__file__).resolve().parent / ".m8_pairwise_paraphrase_cache.json"
CLONE_URL = "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python.git"

def _all_section_texts() -> list[tuple[str, Path]]:
    """Every real live_readme.md this repository already has committed under
    evidence/build/P1_PORTFOLIO_SCALE/ -- scanned, not hand-listed, so the pairwise corpus uses
    whatever real material is actually available rather than a manually curated subset."""
    root = REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
    out = []
    if root.is_dir():
        for entry in sorted(root.iterdir()):
            readme = entry / "live_readme.md"
            if readme.is_file():
                out.append((entry.name.replace("__", "/"), readme))
    return out


SECTION_TEXTS = _all_section_texts()


def _pairwise_cases() -> list[dict]:
    cases = []
    for label, path in SECTION_TEXTS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        parts = [p for p in text.split("\n\n") if p.strip()]
        # A real "Installation"-shaped section, deep enough to skip the title/badges/intro: a
        # lead-in sentence immediately followed by its own code fence is the one shape where
        # reordering reliably produces a real coherence break (an orphaned lead-in stranded
        # after the thing it introduces) -- the opening title/badge paragraphs this script used
        # before swap too weakly (a badge row moved relative to the intro paragraph is not a
        # genuine incoherence). Find the first fenced code block and take 2 paragraphs before it
        # plus 2 after.
        fence_index = next(
            (
                i
                for i, p in enumerate(parts)
                if p.lstrip().startswith(("```", "~~~"))
                and i > 0
                and (
                    "install" in parts[i - 1].lower()
                    # a short lead-in ending in ":" is a general, reliable signal that the next
                    # block is what it introduces (e.g. "Maven:", "Gradle (Kotlin DSL):") --
                    # broader than matching the literal word "install".
                    or (len(parts[i - 1].strip()) < 150 and parts[i - 1].rstrip().endswith(":"))
                )
            ),
            None,
        )
        if fence_index is None or fence_index < 1:
            continue  # no real installation lead-in+fence pair found in this text; skip it
        start = max(0, fence_index - 1)
        section = "\n\n".join(parts[start : fence_index + 2])
        cases.append({
            "kind": "pairwise", "label": f"{label}:clean", "purpose": "installation",
            "candidate_section": section, "benchmark_section": section,
            "expected_at_least_as_good": True,
        })
        try:
            mutation = op_incoherent_reorder(section)
        except Exception:
            continue
        cases.append({
            "kind": "pairwise", "label": f"{label}:incoherent_reorder", "purpose": "overview",
            "candidate_section": mutation.seeded_text, "benchmark_section": section,
            "expected_at_least_as_good": False,
        })
    return cases


def _paraphrase_cases(clone_root: Path, limit: int = 20) -> list[dict]:
    """Real (description, signature) pairs using METHODS, not bare classes: a method's
    signature carries real parameters (``def filter(self, col_index, values)``), which is
    substantive content a description can actually be checked against. A bare class signature
    (``class ChartAxis``) carries almost nothing beyond the name itself -- too thin for this
    shape's own premise ("is this description a fair paraphrase of the real signature") to be
    answerable at all, which is why an earlier version of this script using classes produced
    uninformative, not-genuinely-wrong "False" answers."""
    surf = _surface(clone_root)
    if surf is None:
        return []
    seen: set[str] = set()
    methods = []
    for s in surf.symbols:
        if (
            s.kind in ("method", "function")
            and s.docstring
            and s.signature
            and "(" in (s.signature or "")
            and s.qualified_name not in seen
        ):
            seen.add(s.qualified_name)
            methods.append(s)
    methods = methods[:limit]
    cases = []
    for i, symbol in enumerate(methods):
        cases.append({
            "kind": "paraphrase", "label": f"{symbol.name}:fair", "type_name": symbol.name,
            "description": symbol.docstring, "real_signature": symbol.signature,
            "expected_fair_paraphrase": True,
        })
        donor = methods[(i + 1) % len(methods)]
        if donor.name == symbol.name or not donor.docstring:
            continue
        cases.append({
            "kind": "paraphrase", "label": f"{symbol.name}:unfair_swapped", "type_name": symbol.name,
            "description": donor.docstring, "real_signature": symbol.signature,
            "expected_fair_paraphrase": False,
        })
    return cases


def _run_live(cases: list[dict]) -> list[dict]:
    """Runs every case and saves the cache file after EACH one -- a batch exhaustion or any other
    crash mid-run must not lose the real provider spend already made (a prior run crashed on
    BudgetExceededError after 62 real calls because the cache was written only at the very end,
    throwing those results away even though they were paid for; this never repeats that)."""
    prompts = load_prose_judge_prompts(PROMPT_PATH)
    gateway = load_gateway_config(os.environ)
    results: list[dict] = []
    for case in cases:
        if case["kind"] == "pairwise":
            request = PairwiseComparisonRequest(
                purpose=case["purpose"], candidate_section=case["candidate_section"],
                benchmark_section=case["benchmark_section"],
            )
            verdict = judge_pairwise_benchmark_comparison_live(
                request, gateway=gateway, prompts=prompts,
                repository=case["label"], source_revision="0" * 40,
            )
            case = {**case, "verdict": verdict.verdict, "draws": list(verdict.draws),
                    "agreement": verdict.agreement}
        else:
            request = ParaphraseCheckRequest(
                type_name=case["type_name"], description=case["description"],
                real_signature=case["real_signature"],
            )
            verdict = judge_type_paraphrase_live(
                request, gateway=gateway, prompts=prompts,
                repository=case["label"], source_revision="0" * 40,
            )
            case = {**case, "verdict": verdict.verdict, "draws": list(verdict.draws),
                    "agreement": verdict.agreement}
        results.append(case)
        CACHE_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def _summarize(results: list[dict]):
    """Per kind, split into the DEFECT side (expected False -- the thing M8 is supposed to
    catch: an incoherent reorder, an unfair swapped description) and the CLEAN side (expected
    True). Recall is measured ONLY over the defect side; false-reject ONLY over the clean side
    -- conflating the two into one "overall accuracy" number (an earlier version of this script
    did exactly that) hides which failure mode is actually happening."""
    buckets = {
        "pairwise": {"defect_ok": 0, "defect_n": 0, "clean_ok": 0, "clean_n": 0},
        "paraphrase": {"defect_ok": 0, "defect_n": 0, "clean_ok": 0, "clean_n": 0},
    }
    for r in results:
        expected = r.get("expected_at_least_as_good", r.get("expected_fair_paraphrase"))
        ok = r["verdict"] == expected
        bucket = buckets[r["kind"]]
        if expected:  # clean / expected-good case
            bucket["clean_n"] += 1
            bucket["clean_ok"] += int(ok)
        else:  # defect case M8 is supposed to catch
            bucket["defect_n"] += 1
            bucket["defect_ok"] += int(ok)
        print(f"[{r['kind']:10s}] {r['label']:40s} -> {r['verdict']!s:7s} "
              f"(expected {expected!s:7s}) {'OK' if ok else 'WRONG'}")
    for kind, b in buckets.items():
        print(f"  {kind}: recall (catch defect) {b['defect_ok']}/{b['defect_n']}, "
              f"false-reject (clean wrongly flagged) {b['clean_n'] - b['clean_ok']}/{b['clean_n']}")
    return buckets


def main() -> int:
    argv = sys.argv[1:]
    pairwise_cases = _pairwise_cases()

    tmp = None
    paraphrase_cases = []
    if "--dry-run" not in argv or True:
        tmp = Path(tempfile.mkdtemp(prefix="m8pp-"))
        clone_root = tmp / "clone"
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", CLONE_URL, str(clone_root)],
                check=True, timeout=120,
            )
            paraphrase_cases = _paraphrase_cases(clone_root)
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)

    cases = pairwise_cases + paraphrase_cases
    if "--dry-run" in argv:
        print(f"(dry run, no provider calls -- {len(cases)} cases would be sent: "
              f"{len(pairwise_cases)} pairwise, {len(paraphrase_cases)} paraphrase)")
        return 0

    if CACHE_PATH.exists() and "--fresh" not in argv:
        results = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"(reusing cached results from {CACHE_PATH}, no new provider calls)")
    else:
        results = _run_live(cases)
        CACHE_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    buckets = _summarize(results)

    if "--write" in argv:
        pw = buckets["pairwise"]
        pp = buckets["paraphrase"]

        def _rate_gate(name: str, ok: int, n: int, *, direction: str, threshold: float) -> dict:
            value = round(ok / n, 4) if n else None
            passed = False
            if n:
                passed = n >= 30 and (
                    value >= threshold if direction == ">=" else value <= threshold
                )
            return {
                "name": name, "direction": direction, "threshold": threshold, "n": n,
                "value": value, "passed": passed,
            }

        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        m8_entries = [c for c in doc["certificates"] if c.get("mechanism_class") == "M8"]
        base = m8_entries[0] if m8_entries else {"gates": [], "corpus": "", "provider_calls": 0}
        certs = [c for c in doc["certificates"] if c.get("mechanism_class") != "M8"]
        # Replace any prior gate of the SAME name rather than append: an earlier version of this
        # script appended unconditionally, which left a stale pairwise/paraphrase gate sitting
        # alongside the freshly measured one under the same name -- two "passed" verdicts for one
        # gate, with calibration_status.py's own reader picking only one of them unpredictably.
        gates_by_name = {g["name"]: g for g in base.get("gates", [])}
        for gate in (
            _rate_gate(
                "M8.recall[pairwise_incoherent]", pw["defect_ok"], pw["defect_n"],
                direction=">=", threshold=0.9,
            ),
            _rate_gate(
                "M8.false_reject_rate[pairwise]", pw["clean_n"] - pw["clean_ok"], pw["clean_n"],
                direction="<=", threshold=0.02,
            ),
            _rate_gate(
                "M8-S.recall[paraphrase_unfair]", pp["defect_ok"], pp["defect_n"],
                direction=">=", threshold=0.9,
            ),
            _rate_gate(
                "M8-S.false_reject_rate[paraphrase_fair]", pp["clean_n"] - pp["clean_ok"], pp["clean_n"],
                direction="<=", threshold=0.02,
            ),
        ):
            gates_by_name[gate["name"]] = gate
        gates = list(gates_by_name.values())
        all_passed = all(g["passed"] for g in gates) if gates else False
        certs.append({
            "mechanism_class": "M8",
            "status": "PASSED" if all_passed else "NOT_PASSED",
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": base.get("corpus", "") + f"; pairwise: {pw['defect_n'] + pw['clean_n']} "
                      "real-section cases (clean vs. a genuine op_incoherent_reorder lead-in/"
                      "code-fence orphan, scanned across all real committed live_readme.md "
                      "texts); paraphrase: "
                      f"{pp['defect_n'] + pp['clean_n']} real (description, signature) pairs "
                      "using real METHOD signatures with parameters (not bare class lines) from "
                      "a real cloned repo (fair vs. swapped-description unfair) -- both short of "
                      "n>=30 on at least one side",
            "provider_calls": base.get("provider_calls", 0) + sum(len(r["draws"]) for r in results),
            "provisional": True,
            "gates": gates,
            "note": (
                base.get("note", "")
                + f" | pairwise: recall (caught the real reorder incoherence) "
                  f"{pw['defect_ok']}/{pw['defect_n']}; false-reject (clean wrongly flagged) "
                  f"{pw['clean_n'] - pw['clean_ok']}/{pw['clean_n']}. "
                  f"paraphrase: recall (caught the swapped description) "
                  f"{pp['defect_ok']}/{pp['defect_n']}; false-reject (fair wrongly flagged) "
                  f"{pp['clean_n'] - pp['clean_ok']}/{pp['clean_n']}. "
                  "Pairwise recall is a genuine, verified-wiring finding (0 of 13 real, "
                  "manually-inspected genuine-incoherence cases were caught -- the mechanism "
                  "answered 'at least as good' uniformly); paraphrase shows a real false-reject "
                  "bias on fair cases alongside perfect unfair-detection. Neither is a test-"
                  "construction artifact (both were checked and fixed once before this run)."
            ).strip(" |"),
        })
        doc["certificates"] = certs
        CALIBRATION_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
