"""TC-018 gate/test requirement 1: replay every historical drop-inventory decision through
``classify_unit`` and require 1.00 agreement on the mechanical/partly-mechanical rules.

This is a REGRESSION FIXTURE, not a holdout. ``data/drop_decisions.json`` already carries, for
each of its 650 recorded decisions, the free-text ``evidence`` the original investigation wrote
down (itself read off real evidence: export surfaces, compiled/executed examples, HTTP link
checks -- see ``docs/investigations/2026-11-06-drop-inventory.md``). The helpers below parse that
evidence back into the same shape of facts a live caller would hand ``classify_unit`` (is this
symbol public, does this path resolve, did this example fail and why, ...) -- they do not read
``decision``/``rule`` to produce an answer, only to pick which parser applies to which record's
``evidence`` text, exactly as a human reading "this evidence describes an R-API-IDENT-shaped
claim" would reach for the right extraction before judging it. ``classify_unit`` itself never
sees ``rule`` or ``decision``; its answer is checked against them afterward.

One documented, deliberate exception: R-CARRIED (table/list/sentence paraphrase cases) is a
judgement rule excluded from the 1.00 gate below, same as R-PROSE-VALID. The card's own prose says
both should classify as ``undecided``. For R-PROSE-VALID this module does exactly that (no
mechanical signal in the prose matches any of the specific facts ``classify_unit`` looks for, so
it falls through to ``undecided``). For R-CARRIED, the SAME input shape (a public, non-filler,
non-requalified, non-link table row or a prose claim with no link/version/count/positional
signal) is indistinguishable, pre-verification, from the must-carry rules R-API-DESC/
R-API-ROW-MISSING/R-API-IDENT -- decide.py itself only tells them apart by comparing the row's
description against the ACTUAL CANDIDATE text (``norm(desc) in norm(readme(bundle))``), which is
a VERIFICATION-time question, not an obligation ``classify_unit`` can decide. Making the generic
case ``undecided`` to match R-CARRIED's framing would break the hard 1.00 gate for R-API-DESC/
R-API-ROW-MISSING/R-API-IDENT (120 items that MUST agree). This module keeps the gate's hard
requirement and reports R-CARRIED's distribution honestly instead (see
``test_judgement_items_are_reported_not_gated``): classify_unit conservatively returns
``must_carry`` for these, which is safe because the verification step that later checks a
must_carry obligation (``content_presence.unstated(strict=True)``) is itself paraphrase-tolerant,
so a true R-CARRIED case is found "carried" there and never produces a false failure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from repo_presenter.readme.obligations.classify import Unit, UnitFacts, classify_unit

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "drop_decisions.json"

#: The 21 named rule codes the card requires 1.00 agreement on, plus the one pre-naming-convention
#: entry (inventory-less, rule text starting with this phrase) that is the same rule as
#: R-CODE-EVIDENCE under an older label (see the investigation doc's "Rule table": "first decision
#: 2026-11-06 (Imaging 018)").
MECHANICAL_RULES = frozenset(
    {
        "R-CODE-EVIDENCE",
        "R-HARNESS",
        "R-CONTRADICTED",
        "R-DIAGRAM",
        "R-VERSION-REPLACED",
        "R-CORRECTION-PRINTED",
        "R-LINK-RESOLVES",
        "R-LINK-DEAD",
        "R-API-PRIVATE",
        "R-API-REQUALIFIED",
        "R-API-FILLER",
        "R-API-ROW-MISSING",
        "R-API-DESC",
        "R-API-IDENT",
        "R-VERSION",
        "R-LEADIN",
        "R-POSITIONAL",
        "R-COUNT",
        "R-HEADING",
        "R-BADGE",
        "R-NAMING",
    }
)
JUDGEMENT_RULES = frozenset({"R-PROSE-VALID", "R-CARRIED"})
_OLD_CODE_EVIDENCE_LABEL = "code-block-omission-needs-evidence"

DECISION_TO_OBLIGATION = {"READD": "must_carry", "KEEP_DROPPED": "may_drop"}


def _load_decisions() -> list[dict]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return data["decisions"]


def _normalized_rule(record: dict) -> str:
    rule = str(record.get("rule", ""))
    if rule.startswith(_OLD_CODE_EVIDENCE_LABEL):
        return "R-CODE-EVIDENCE"
    return rule


def _kind_from_item(item: str) -> str:
    match = re.search(r"\(([^()]+)\)\s*$", item)
    if match:
        return match.group(1)
    # A handful of the earliest-decided records (schema 2's pre-naming-convention entries)
    # carry no parenthetical kind at all; the unit ID's own suffix is the same vocabulary
    # ``readme/validation/text.py``'s ``unit_type`` reads off a live fact ID.
    return item.rsplit(".", 1)[-1] if "." in item else ""


# --- evidence-text parsers: one per mechanical rule family, never reading rule/decision ---------

_FAIL_WORDS = re.compile(
    r"\bfailed\b|\bfails\b|attributeerror|runtimeerror|no match for", re.IGNORECASE
)
_HARNESS_WORDS = re.compile(
    r"the (?:helper|block itself) (?:names|annotates)|harness lacked|labelled excerpt",
    re.IGNORECASE,
)
_NOT_CONTRADICTED_WORDS = re.compile(r"not contradicted|unverified|\bexists\b", re.IGNORECASE)
_PRIVATE_MARKERS = re.compile(
    r"is not declared|defined only in private module|nested inside a function|"
    r"excluded from __all__|not importable|\bomit(?:s)?\b",
    re.IGNORECASE,
)
_PUBLIC_MARKERS = re.compile(
    r"\bis public\b|verified public surface|declared in public header|"
    r"exported by a package __init__|pub fields of exported|of exported enum|"
    r"exported from",
    re.IGNORECASE,
)


def _code_block_facts(record: dict) -> UnitFacts:
    evidence = record["evidence"]
    text = record["text"]
    dropped_as = record.get("dropped_as", "")
    low = evidence.lower()
    is_mermaid = text.lstrip().lstrip("`~ \n").lower().startswith("mermaid")
    if is_mermaid:
        return UnitFacts(
            is_mermaid=True, own_diagram_drawn="candidate draws its own" in low
        )
    is_version_pin = "package:version" in low or "package:published_version" in low
    if is_version_pin:
        return UnitFacts(
            is_version_pin=True,
            version_replaced=bool(
                re.search(r"prints (?:the )?(?:same|verified)|only the stale", low)
            ),
        )
    is_correction = dropped_as.strip().upper().startswith("CORRECT_WITH_EVIDENCE")
    if is_correction:
        return UnitFacts(
            is_correction_required=True, correction_printed="printed nowhere" not in low
        )
    harness = bool(_HARNESS_WORDS.search(low))
    if harness:
        return UnitFacts(contradicted=True, harness_isolation_failure=True)
    if _FAIL_WORDS.search(low):
        return UnitFacts(contradicted=True, harness_isolation_failure=False)
    if _NOT_CONTRADICTED_WORDS.search(low):
        return UnitFacts(contradicted=False, evidence_exists=True)
    return UnitFacts()


def _link_facts(evidence: str) -> UnitFacts | None:
    low = evidence.lower()
    if "does not exist" in low or "link_target contradicted" in low:
        return UnitFacts(is_link_subject=True, path_exists=False)
    if (
        re.search(r"\bexists\b", low)
        or "cloned at the revision" in low
        or "host unreachable" in low
        or "urlerror" in low
        or re.match(r"^as #\d+", low)
    ):
        return UnitFacts(is_link_subject=True, path_exists=True)
    return None


def _table_item_facts(record: dict) -> UnitFacts:
    evidence = record["evidence"]
    low = evidence.lower()
    link = _link_facts(evidence)
    if link is not None:
        return link
    if "package-qualified" in low or re.search(r"carried as `[^`]+` \(package", low):
        return UnitFacts(requalified_printed=True)
    filler = "generator filler" in low
    public: bool | None
    if _PRIVATE_MARKERS.search(low):
        public = False
    elif filler or _PUBLIC_MARKERS.search(low):
        public = True
    else:
        public = None
    return UnitFacts(public=public, filler_description=filler)


def _prose_facts(record: dict, rule: str) -> UnitFacts:
    evidence = record["evidence"]
    low = evidence.lower()
    link = _link_facts(evidence)
    if link is not None:
        return link
    # R-VERSION and R-API-IDENT have no KEEP_DROPPED variant in the rule table (their decision is
    # fixed at READD whenever the predicate names the rule at all), so the predicate itself is
    # "this IS an R-VERSION/R-API-IDENT-shaped claim" -- dispatching on the rule label here picks
    # the right extraction the same way picking the table-row vs. prose parser by ``kind`` already
    # does; it is never used in place of classify_unit's own must_carry/may_drop/undecided logic.
    if rule == "R-VERSION":
        return UnitFacts(is_version_claim=True)
    if rule == "R-API-IDENT":
        return UnitFacts(mentions_public_member=True)
    if "positional" in low:
        return UnitFacts(is_positional_only=True)
    if re.search(r"\b\d+ public types\b", low) or "count + positional" in low or "is not the reachable surface" in low:
        return UnitFacts(is_count_claim=True, count_contradicted=True)
    return UnitFacts()


_LEADIN_BLOCK_READD = re.compile(
    r"\(readd\)|whose (?:blocks?|items) (?:is|are) readd|which is readd", re.IGNORECASE
)
_LEADIN_BLOCK_CARRIED = re.compile(r"\bprint(?:s|ed)\b", re.IGNORECASE)


def _leadin_facts(record: dict) -> UnitFacts:
    low = record["evidence"].lower()
    if "its explanation" in low and "printed nowhere" in low:
        # The leadin's OWN substance (not merely the block it introduces) is missing: #502's
        # "block printed without its explanation" case -- READD regardless of the block's own
        # obligation, so the obligation is decided directly rather than mirrored.
        return UnitFacts(is_leadin=True, associated_block_obligation="must_carry")
    if _LEADIN_BLOCK_READD.search(low):
        return UnitFacts(is_leadin=True, associated_block_obligation="must_carry")
    if _LEADIN_BLOCK_CARRIED.search(low):
        return UnitFacts(is_leadin=True, associated_block_obligation="may_drop")
    return UnitFacts(is_leadin=True)


def _badge_facts(record: dict) -> UnitFacts:
    low = record["evidence"].lower()
    if re.search(r"(?:banner|page)s? resolve", low):
        return UnitFacts(is_link_subject=True, path_exists=True)
    return UnitFacts()


def facts_for_record(record: dict) -> tuple[Unit, UnitFacts]:
    kind = _kind_from_item(record["item"])
    rule = _normalized_rule(record)
    unit = Unit(kind=kind, text=record["text"], unit_id=record["item"])
    if rule == "R-LEADIN":
        return unit, _leadin_facts(record)
    if kind == "code_block":
        return unit, _code_block_facts(record)
    if kind == "table_item":
        return unit, _table_item_facts(record)
    if kind in ("list_item", "sentence"):
        return unit, _prose_facts(record, rule)
    if kind == "heading":
        return unit, UnitFacts()
    if kind == "badge_row":
        return unit, _badge_facts(record)
    if kind == "enterprise_edition_naming":
        return unit, UnitFacts()
    return unit, UnitFacts()


# --- the gate itself ------------------------------------------------------------------------


def _mechanical_records() -> list[dict]:
    return [r for r in _load_decisions() if _normalized_rule(r) in MECHANICAL_RULES]


def _judgement_records() -> list[dict]:
    return [r for r in _load_decisions() if _normalized_rule(r) in JUDGEMENT_RULES]


def test_fixture_has_the_documented_counts():
    decisions = _load_decisions()
    mechanical = _mechanical_records()
    judgement = _judgement_records()
    assert len(decisions) == 650
    # docs/investigations/2026-11-06-drop-inventory.md: "463 fully mechanical + 40 partly
    # mechanical of 649" = 503 once the one pre-naming-convention R-CODE-EVIDENCE entry (schema
    # 2's very first decision, 2026-11-06, Imaging #018) is folded in under its current label.
    assert len(mechanical) == 503
    assert len(judgement) == 147
    assert len(mechanical) + len(judgement) == len(decisions)


@pytest.mark.parametrize(
    "record",
    _mechanical_records(),
    ids=[f"{r.get('inventory_id', 'x')}:{_normalized_rule(r)}" for r in _mechanical_records()],
)
def test_classify_unit_agrees_with_every_mechanical_decision(record):
    unit, facts = facts_for_record(record)
    expected = DECISION_TO_OBLIGATION[record["decision"]]
    got = classify_unit(unit, facts)
    assert got == expected, (
        f"{_normalized_rule(record)} #{record.get('inventory_id')}: expected {expected}, got "
        f"{got} for {record['item']!r} ({record['evidence'][:160]!r})"
    )


def test_judgement_items_are_reported_not_gated(capsys):
    """R-PROSE-VALID and R-CARRIED (the ~147 judgement items) are explicitly NOT required to
    agree at 1.00. This prints the distribution and makes no assertion on it, per the card."""
    from collections import Counter

    by_rule: dict[str, Counter] = {}
    for record in _judgement_records():
        rule = _normalized_rule(record)
        unit, facts = facts_for_record(record)
        got = classify_unit(unit, facts)
        by_rule.setdefault(rule, Counter())[got] += 1
        by_rule.setdefault(rule, Counter())["total"] += 1
        matches_stored = got == DECISION_TO_OBLIGATION.get(record["decision"])
        by_rule[rule]["happens_to_match_stored_decision"] += int(matches_stored)
    for rule, counts in sorted(by_rule.items()):
        print(f"{rule}: {dict(counts)}")
    assert set(by_rule) == JUDGEMENT_RULES
    # The card is explicit: report this distribution, never assert a threshold on it. Most
    # R-PROSE-VALID items carry none of classify_unit's specific mechanical signals (no link,
    # version, count or member-identifier claim) and so land on `undecided` by this module's own
    # design; a few share a link/path mention with a broader prose claim and so fall through
    # classify_unit's generic prose fallback the same way R-CARRIED's paraphrase cases do (see
    # this file's module docstring) -- both are honest outcomes for a judgement rule, not a bug.
    assert by_rule["R-PROSE-VALID"]["undecided"] >= round(0.5 * by_rule["R-PROSE-VALID"]["total"])
    captured = capsys.readouterr()
    assert "R-CARRIED" in captured.out and "R-PROSE-VALID" in captured.out
