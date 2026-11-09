"""Supervisor-run, REAL-provider-call measurement of mechanism M8's classification shape
(promotional vs. none) at the design's own n>=30-per-class minimum
(docs/design/2026-11-06-acceptance-redesign.md section 4.1), against real committed README
sentences and real/synthetic promotional spans, through TC-023b's live wiring
(``prose_judge_live.py``).

Clean spans: real sentences from six already-committed README texts (the same ones
``measure_m7.py`` and the existing self-parity test use) -- 50 real candidate sentences
available across them, well over the 30 needed.

Promotional spans: the two real sentences
``src/repo_presenter/acceptance/audit/seed.py::op_add_promotional_filler`` actually inserts
during M9 seeding (reused here, not re-typed), plus 28 additional synthetic marketing-style
sentences, varied in structure and vocabulary (never the same clause repeated), so recall is
measured on real variety, not one template restated.

Usage: ``python scripts/measure_m8_live.py [--write]``. A single invocation either makes the
real calls and prints them (no flag), or makes them AND writes the certificate (``--write``) --
it never makes the calls twice: results are cached to ``scripts/.m8_live_cache.json`` after the
first real run in a given invocation chain, so re-running with ``--write`` after a bare run
reuses the cache instead of re-spending. ``--dry-run`` makes no call at all. ``--fresh`` ignores
any existing cache and forces a new real run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.seed import _PROMOTIONAL_FILLER_SENTENCES  # noqa: E402
from repo_presenter.core.config import load_gateway_config  # noqa: E402
from repo_presenter.readme.review.prose_judge import (  # noqa: E402
    ClassificationRequest,
    load_prose_judge_prompts,
)
from repo_presenter.readme.review.prose_judge_live import judge_classification_live  # noqa: E402

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"
PROMPT_PATH = REPO_ROOT / "prompts" / "m8" / "prose_judge.yaml"
CACHE_PATH = Path(__file__).resolve().parent / ".m8_live_cache.json"

CLEAN_TEXTS = [
    (
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET (candidate)",
        REPO_ROOT / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
        / "52b0f00ebf28a0b4173921725ff170685ec2c502/README.md",
    ),
    (
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET (live)",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-3d-foss__Aspose.3D-FOSS-for-.NET/live_readme.md",
    ),
    (
        "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET/live_readme.md",
    ),
    (
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-cells-foss__Aspose.Cells-FOSS-for-Rust/live_readme.md",
    ),
    (
        "aspose-email-foss/Aspose.Email-FOSS-for-.Net",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-email-foss__Aspose.Email-FOSS-for-.Net/live_readme.md",
    ),
    (
        "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/live_readme.md",
    ),
]

#: Clearly synthetic marketing-style sentences -- never claimed as real README text, varied in
#: structure/vocabulary rather than one template restated.
SYNTHETIC_PROMOTIONAL = (
    "Our solution is the industry-leading, award-winning choice trusted by Fortune 500 companies "
    "everywhere.",
    "Experience next-generation performance that blows every competitor out of the water.",
    "It delivers unmatched quality and blazing speed, setting a brand new standard for excellence.",
    "Join thousands of satisfied developers who have transformed their workflow with our "
    "game-changing technology.",
    "This is, without question, the most innovative and powerful library ever created for this "
    "task.",
    "Unlock limitless possibilities with our best-in-class, enterprise-grade platform.",
    "Nothing else on the market comes close to the seamless, world-class experience we provide.",
    "It is the ultimate solution, engineered to exceed every expectation you could possibly have.",
    "Developers everywhere are raving about the incredible speed and reliability this library "
    "delivers.",
    "Say goodbye to slow, clunky tools -- this is the lightning-fast future of development.",
    "Built by engineers obsessed with perfection, this library sets a new gold standard.",
    "There has never been a better time to upgrade to the fastest, most capable library on the "
    "market.",
    "Our customers consistently tell us this is the single best investment they have made this "
    "year.",
    "From startups to global enterprises, everyone agrees: this is simply the best choice "
    "available.",
    "Designed from the ground up to crush every benchmark and leave the competition behind.",
    "This revolutionary approach changes everything you thought you knew about building software.",
    "With zero compromises and maximum performance, it truly has no equal in its category.",
    "Millions of downloads later, it's clear this is the gold standard the whole industry follows.",
    "Why settle for ordinary when you can have the extraordinary power of this groundbreaking "
    "library?",
    "It consistently outperforms every rival, delivering jaw-dropping results every single time.",
    "This isn't just an upgrade -- it's a complete reinvention of what's possible.",
    "Trusted, battle-tested, and beloved by developers who demand nothing but the very best.",
    "Get ready to be amazed by a level of quality and polish you simply won't find anywhere else.",
    "It's no exaggeration to call this the single greatest leap forward the ecosystem has ever "
    "seen.",
    "The feedback has been overwhelming: users call it a total game-changer for their workflow.",
    "Supercharge your productivity with a tool engineers everywhere can't stop talking about.",
    "Setting the bar impossibly high, this library leaves every alternative in the dust.",
    "A masterpiece of engineering that redefines what developers should expect from their tools.",
)


def _clean_sentences(limit: int = 30) -> list[tuple[str, str]]:
    import re

    out: list[tuple[str, str]] = []
    for repo, path in CLEAN_TEXTS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            s = sentence.strip()
            if 40 < len(s) < 220 and not s.startswith(("#", "|", "-", "`", "![")):
                out.append((repo, s))
            if len(out) >= limit:
                return out
    return out


def _cases() -> list[tuple[str, str, str, bool]]:
    clean = _clean_sentences(30)
    promotional = [("seed.py:op_add_promotional_filler", s) for s in _PROMOTIONAL_FILLER_SENTENCES]
    promotional += [("synthetic", s) for s in SYNTHETIC_PROMOTIONAL]
    cases = [("clean", label, text, False) for label, text in clean]
    cases += [("promotional", label, text, True) for label, text in promotional]
    return cases


def _run_live(cases: list[tuple[str, str, str, bool]]) -> list[dict]:
    prompts = load_prose_judge_prompts(PROMPT_PATH)
    gateway = load_gateway_config(os.environ)
    results = []
    for category, label, text, expected_promotional in cases:
        request = ClassificationRequest(
            span_id=f"{category}:{label}:{hash(text) & 0xffff}", text=text
        )
        verdict = judge_classification_live(
            request, gateway=gateway, prompts=prompts,
            repository=label if category == "clean" else "synthetic/m8-calibration",
            source_revision="0" * 40,
        )
        results.append({
            "category": category, "label": label, "text": text,
            "expected_promotional": expected_promotional,
            "verdict": verdict.verdict, "draws": list(verdict.draws),
            "agreement": verdict.agreement,
        })
    return results


def _summarize(results: list[dict]):
    correct = 0
    by_category = {"clean": [0, 0], "promotional": [0, 0]}
    for r in results:
        got_promotional = r["verdict"] == "promotional"
        ok = got_promotional == r["expected_promotional"]
        correct += int(ok)
        by_category[r["category"]][0] += int(ok)
        by_category[r["category"]][1] += 1
        print(f"[{r['category']:11s}] {r['label']:55s} -> {r['verdict']:12s} "
              f"(agreement={r['agreement']}, draws={r['draws']}) {'OK' if ok else 'WRONG'}")
    print(f"\noverall: {correct}/{len(results)} correct")
    for category, (ok, n) in by_category.items():
        print(f"  {category}: {ok}/{n}")
    return by_category


def main() -> int:
    argv = sys.argv[1:]
    cases = _cases()
    if "--dry-run" in argv:
        print(f"(dry run, no provider calls -- {len(cases)} cases would be sent)")
        return 0

    if CACHE_PATH.exists() and "--fresh" not in argv:
        results = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"(reusing cached results from {CACHE_PATH}, no new provider calls)")
    else:
        results = _run_live(cases)
        CACHE_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    by_category = _summarize(results)

    if "--write" in argv:
        clean_ok, clean_n = by_category["clean"]
        promo_ok, promo_n = by_category["promotional"]
        gate_recall = {
            "name": "M8.recall[promotional]", "direction": ">=", "threshold": 0.9,
            "n": promo_n, "value": round(promo_ok / promo_n, 4) if promo_n else None,
            "passed": promo_n >= 30 and (promo_ok / promo_n) >= 0.9 if promo_n else False,
        }
        gate_fr = {
            "name": "M8.false_reject_rate", "direction": "<=", "threshold": 0.02,
            "n": clean_n, "value": round((clean_n - clean_ok) / clean_n, 4) if clean_n else None,
            "passed": clean_n >= 30 and ((clean_n - clean_ok) / clean_n) <= 0.02 if clean_n else False,
        }
        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        certs = [c for c in doc["certificates"] if c.get("mechanism_class") != "M8"]
        certs.append({
            "mechanism_class": "M8",
            "status": "PASSED" if gate_recall["passed"] and gate_fr["passed"] else "NOT_PASSED",
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": f"{clean_n} real README sentences (clean, across 6 real committed texts) + "
                      f"{promo_n} promotional spans (2 real seed.py operator sentences + 28 "
                      "varied synthetic marketing sentences), classification shape only -- not "
                      "pairwise or paraphrase",
            "provider_calls": sum(len(r["draws"]) for r in results),
            "provisional": True,
            "gates": [gate_recall, gate_fr],
            "note": f"Real result: {clean_ok}/{clean_n} clean correctly NOT flagged promotional; "
                    f"{promo_ok}/{promo_n} promotional spans correctly caught, at the design's "
                    "own n>=30-per-class minimum for this one category pair. Status reflects "
                    "the literal gate math (recall >= 0.90 and false_reject <= 0.02, n >= 30).",
        })
        doc["certificates"] = certs
        CALIBRATION_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
