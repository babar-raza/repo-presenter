"""Supervisor-run, zero-provider-call measurement of M6's promotional/superlative wording-ban
rule (``repo_presenter.readme.validation.wording.promotional_wording_matches``) -- the lexicon-
ban half of M8's rung-(c) fallback (R26). Adds a second, independently-gated case group
(``wording_ban``) alongside M6's existing ``duplicate_paragraph`` case group
(``scripts/measure_m4_m6.py``); both must clear recall >= 0.90 on their own, never averaged
together, so one rule's strength cannot hide the other's weakness.

Corpus, reused rather than re-typed (R10/TC-022a's own convention: reuse existing, real,
already-trusted material instead of inventing a parallel one): the EXACT 60 cases
(30 real clean README sentences, 30 promotional spans: 2 real `seed.py` sentences + 28 synthetic
marketing sentences) ``scripts/measure_m8_live.py`` built and real-measured M8's classification
shape against, plus the existing ``mutations.py::add_promotional_filler`` fixture case
``measure_m4_m6.py`` already uses for M6.

Honest limitation, stated once here rather than scattered across call sites (see
``wording.py``'s own module docstring for the full argument): this is a dev-corpus measurement,
not an independent held-out one -- the lexicon was tuned directly against misses found on this
same corpus. It is the lexicon-ban HALF of rung (c) only; the construction half (bounding what a
generator can emit) is TC-019's separate, not-yet-built scope. Recall here is not a promise about
novel promotional phrasing a future generator might emit outside this lexicon.

Usage: ``python scripts/measure_m6_wording_ban.py [--write]``, same convention as
``measure_m4_m6.py``/``measure_m5.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m4_or_m6,
)
from repo_presenter.readme.review.calibration.mutations import OPERATORS  # noqa: E402
from repo_presenter.readme.review.independent_reviewer import (  # noqa: E402
    duplicate_paragraph_rule,
)
from repo_presenter.readme.validation.wording import promotional_wording_matches  # noqa: E402
from tests.readme.review.calibration.synthetic import make_source  # noqa: E402

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"


def _load_m8_live_module():
    spec = importlib.util.spec_from_file_location(
        "measure_m8_live", REPO_ROOT / "scripts" / "measure_m8_live.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def measure() -> tuple:
    m8_live = _load_m8_live_module()
    m8_cases = m8_live._cases()  # (category, label, text, expected_promotional)

    wording_cases: list[CaseVerdict] = []
    for category, label, text, expected_promotional in m8_cases:
        flagged = bool(promotional_wording_matches(text))
        wording_cases.append(
            CaseVerdict(
                case_id=f"{category}:{label}", group="wording_ban",
                expected=expected_promotional, flagged=flagged,
            )
        )

    dup_cases: list[CaseVerdict] = []
    with tempfile.TemporaryDirectory(prefix="m6wb-") as tmp:
        source = make_source(Path(tmp))
        dup_cases.append(
            CaseVerdict(
                case_id="clean", group="duplicate_paragraph", expected=False,
                flagged=bool(duplicate_paragraph_rule(source.readme)),
            )
        )
        mutation = OPERATORS["duplicate_paragraph"](source)
        if mutation is not None:
            dup_cases.append(
                CaseVerdict(
                    case_id="duplicate_paragraph", group="duplicate_paragraph", expected=True,
                    flagged=bool(duplicate_paragraph_rule(mutation.readme)),
                )
            )
        # The wording-ban rule must also clear the SAME fixture mutation used to prove M6's other
        # rule (add_promotional_filler), not only the larger M8 dev corpus above.
        promo_mutation = OPERATORS["add_promotional_filler"](source)
        if promo_mutation is not None:
            wording_cases.append(
                CaseVerdict(
                    case_id="fixture:add_promotional_filler", group="wording_ban", expected=True,
                    flagged=bool(promotional_wording_matches(promo_mutation.readme)),
                )
            )
            wording_cases.append(
                CaseVerdict(
                    case_id="fixture:clean", group="wording_ban", expected=False,
                    flagged=bool(promotional_wording_matches(source.readme)),
                )
            )

    all_cases = dup_cases + wording_cases
    return score_m4_or_m6("M6", all_cases), len(all_cases), wording_cases, dup_cases


def _merge_certificate(result, n: int) -> dict:
    if CALIBRATION_PATH.exists():
        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    else:
        doc = {
            "schema": "acceptance-calibration/1",
            "harness_version": HARNESS_VERSION,
            "harness_schema_version": SCHEMA_VERSION,
            "certificates": [],
        }
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M6"]
    certificates.append({
        "mechanism_class": result.mechanism,
        "status": result.status,
        "measured_at": "2026-11-09T00:00:00Z",
        "corpus": (
            "readme.review.calibration.mutations OPERATORS + "
            "independent_reviewer.duplicate_paragraph_rule (duplicate_paragraph group) + "
            "readme.validation.wording.promotional_wording_matches against the real M8 "
            "classification dev corpus (scripts/measure_m8_live.py: 30 real clean README "
            "sentences, 30 promotional spans) plus the add_promotional_filler fixture "
            "(wording_ban group) -- rung-(c) fallback, R26; dev-corpus measurement, not "
            "independently held out (see wording.py module docstring)"
        ),
        "provider_calls": result.provider_calls,
        "provisional": result.provisional,
        "gates": [gate.__dict__ for gate in result.gates],
    })
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n, wording_cases, dup_cases = measure()
    print("M6:", json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n} cases -- {len(dup_cases)} duplicate_paragraph, "
          f"{len(wording_cases)} wording_ban -- 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result, n)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
