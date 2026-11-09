"""Supervisor-run, REAL-provider-call measurement of mechanism M8's classification shape
(promotional vs. none), against real committed README sentences and real/synthetic promotional
spans, through TC-023b's live wiring (``prose_judge_live.py``).

This is a bounded PROOF run, not a full n>=30-per-class certification (the design's own minimum,
docs/design/2026-11-06-acceptance-redesign.md section 4.1): ~10 clean cases and ~10 promotional
cases, run through the real qwen3-next gateway, charged against an open
``data/provider_budget.json`` batch. Honestly reported as such in the written certificate.

Clean spans: real sentences from six already-committed README texts (the same ones
``measure_m7.py`` and the existing self-parity test use).

Promotional spans: the two real sentences
``src/repo_presenter/acceptance/audit/seed.py::op_add_promotional_filler`` actually inserts
during M9 seeding (reused here, not re-typed), plus eight additional synthetic marketing-style
sentences built the same way this session's earlier single positive-control case was, so recall
is measured on more than one fixed string.

Usage: ``python scripts/measure_m8_live.py [--write]``. ALWAYS makes real provider calls when
run without ``--dry-run``; requires an open batch in ``data/provider_budget.json`` with enough
headroom (checked before any call, via the same budget gate every other call goes through).
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

CLEAN_TEXTS = [
    (
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        REPO_ROOT / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
        / "52b0f00ebf28a0b4173921725ff170685ec2c502/README.md",
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
        "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
        REPO_ROOT / "evidence/build/P1_PORTFOLIO_SCALE"
        / "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/live_readme.md",
    ),
]

#: Additional, clearly synthetic marketing-style sentences -- never claimed as real README text,
#: built the same way this session's first M8 positive control was.
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
)


def _clean_sentences(limit: int = 10) -> list[tuple[str, str]]:
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


def measure(*, dry_run: bool):
    prompts = load_prose_judge_prompts(PROMPT_PATH)
    gateway = None if dry_run else load_gateway_config(os.environ)

    clean = _clean_sentences(10)
    promotional = [("seed.py:op_add_promotional_filler", s) for s in _PROMOTIONAL_FILLER_SENTENCES]
    promotional += [("synthetic", s) for s in SYNTHETIC_PROMOTIONAL]

    cases = []
    for label, text in clean:
        cases.append(("clean", label, text, False))
    for label, text in promotional:
        cases.append(("promotional", label, text, True))

    results = []
    for category, label, text, expected_promotional in cases:
        request = ClassificationRequest(span_id=f"{category}:{label}:{hash(text) & 0xffff}", text=text)
        if dry_run:
            results.append((category, label, text, expected_promotional, None))
            continue
        verdict = judge_classification_live(
            request, gateway=gateway, prompts=prompts,
            repository=label if category == "clean" else "synthetic/m8-calibration",
            source_revision="0" * 40,
        )
        results.append((category, label, text, expected_promotional, verdict))
    return results


def _summarize(results):
    correct = 0
    total = 0
    by_category = {"clean": [0, 0], "promotional": [0, 0]}
    for category, label, text, expected_promotional, verdict in results:
        if verdict is None:
            continue
        total += 1
        got_promotional = verdict.verdict == "promotional"
        ok = got_promotional == expected_promotional
        correct += int(ok)
        by_category[category][0] += int(ok)
        by_category[category][1] += 1
        print(f"[{category:11s}] {label:50s} -> {verdict.verdict:12s} "
              f"(agreement={verdict.agreement}, draws={verdict.draws}) {'OK' if ok else 'WRONG'}")
    print(f"\noverall: {correct}/{total} correct")
    for category, (ok, n) in by_category.items():
        print(f"  {category}: {ok}/{n}")
    return by_category, total


def main() -> int:
    dry_run = "--dry-run" in sys.argv[1:]
    results = measure(dry_run=dry_run)
    if dry_run:
        print(f"(dry run, no provider calls -- {len(results)} cases would be sent)")
        return 0

    by_category, total = _summarize(results)
    if "--write" in sys.argv[1:]:
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
            "corpus": f"{clean_n} real README sentences (clean) + {promo_n} promotional spans "
                      "(2 real seed.py operator sentences + synthetic marketing sentences), "
                      "classification shape only -- not pairwise or paraphrase; still short of "
                      "the design's n>=30-per-class minimum",
            "provider_calls": sum(len(v.draws) for *_x, v in [r for r in results if r[-1] is not None]),
            "provisional": True,
            "gates": [gate_recall, gate_fr],
            "note": f"Real result: {clean_ok}/{clean_n} clean correctly NOT flagged promotional; "
                    f"{promo_ok}/{promo_n} promotional spans correctly caught. Status is "
                    "NOT_PASSED whenever n<30 per class regardless of the observed rate, per the "
                    "design's own minimum -- this is a calibration PROOF at larger n than the "
                    "first 2-case run, not yet a certification.",
        })
        doc["certificates"] = certs
        CALIBRATION_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
