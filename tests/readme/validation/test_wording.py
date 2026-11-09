"""Tests for the M6 promotional/superlative wording-ban rule (rung-(c) fallback, R26). Real
text: the exact fixture mutations.py already uses for M6 (PROMOTIONAL_FILLER) and the real
sentences this project already measured M8's classification shape against
(scripts/measure_m8_live.py's clean/promotional corpus) -- not invented strings."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from repo_presenter.readme.review.calibration.mutations import PROMOTIONAL_FILLER
from repo_presenter.readme.validation.wording import promotional_wording_matches

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_m8_live_cases():
    spec = importlib.util.spec_from_file_location(
        "measure_m8_live", REPO_ROOT / "scripts" / "measure_m8_live.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec.loader.exec_module(module)
    return module._cases()


def test_the_real_promotional_filler_fixture_is_caught():
    assert promotional_wording_matches(PROMOTIONAL_FILLER)


def test_a_plain_technical_sentence_is_not_flagged():
    clean = (
        "Call `Image.load(path)` to open a raster image and `image.save(output_path)` to write "
        "it back in the requested format."
    )
    assert promotional_wording_matches(clean) == ()


def test_a_legitimate_technical_use_of_a_near_promotional_word_is_not_flagged():
    # "unmatched" in its ordinary sense (nothing paired it, not "has no equal") must not trip the
    # ban -- the real false positive this rule's own dev measurement caught and removed from the
    # lexicon (the term "unmatched" alone was in an earlier version of PROMOTIONAL_TERMS).
    technical = "`ImageFormat` -- enum of the 14 detectable formats, plus `Unknown` for anything unmatched."
    assert promotional_wording_matches(technical) == ()


def test_real_m8_dev_corpus_recall_and_false_reject_both_meet_the_090_gate():
    """Real, honest measurement against the exact corpus scripts/measure_m8_live.py built for
    M8's own classification calibration (30 real clean README sentences, 30 promotional spans:
    2 real seed.py sentences + 28 synthetic). This is the same dev corpus the lexicon itself was
    tuned against (see wording.py's module docstring) -- the gate here is a regression floor for
    that already-tuned lexicon, not a claim of held-out generalization."""
    cases = _load_m8_live_cases()
    promo = [c for c in cases if c[3]]
    clean = [c for c in cases if not c[3]]
    assert len(promo) >= 30 and len(clean) >= 30
    caught = sum(1 for _, _, text, _ in promo if promotional_wording_matches(text))
    false_flagged = sum(1 for _, _, text, _ in clean if promotional_wording_matches(text))
    assert caught / len(promo) >= 0.90
    assert false_flagged == 0


def test_matches_are_returned_in_a_stable_order_and_empty_for_no_match():
    assert promotional_wording_matches("nothing promotional here at all") == ()
    first_call = promotional_wording_matches(PROMOTIONAL_FILLER)
    second_call = promotional_wording_matches(PROMOTIONAL_FILLER)
    assert first_call == second_call
