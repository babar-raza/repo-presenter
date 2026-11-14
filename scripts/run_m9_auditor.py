"""M9 hosted blind auditor and frozen-findings resolver (owner, 2026-11-13, R37: the M9 round runs itself
on GitHub Actions; earlier rounds' auditors were supervisor subagents).

``audit`` reviews every case of one seed batch with the EXISTING independent reviewer
(``readme.review.llm_review.review_with_model``: job ``independent_review``, ``prompts/independent_review.yaml``,
its configured route, its contract, ledger, call store and the R25/R31 budget gate inside ``run_job``)
plus its deterministic claim-contradiction rule, and writes the findings in exactly the shape
``run_m9_scorer.py`` and ``run_acceptance_writer.py`` read::

    [{"candidate_id": <case_id>, "claim": ..., "verdict": "supported|false|unverifiable",
      "path": "<case_id>.md", "line": <1-based line of the case text>, "evidence": ...}, ...]

Blindness: its only inputs are the public ``case_index.json``, the case texts (``candidates/<case_id>.md``)
and each case's own seal (``bundle_store.seal_history``: the facts, plan and dispositions it was sealed
with, and the live README it was made from -- the same pinned evidence the reviewer always uses). It never
takes the encrypted manifest or the key; the workflow job that runs it has no ``acceptance-audit``
environment and downloads only the candidates artifact. Each case is reviewed as a whole document
(``rendered=False``, no Lane L edit scope), so nothing tells the reviewer which lines differ from the seal.

Scope (BL-013, the R36(b) diagnosis of hosted round 43445578226): the review is ``audit=True``, so the
reviewer is shown every heading line too (a sentence written onto the ``# Title`` line is prose; the round
missed all 11 of its D/D14 seeds there) and authored API reference rows carry their type facts as in the
production Lane R review. A Lane L case is judged as the production Lane L review judges a correction: the
lines that differ from the live README at the audited revision (``README.original.md``, the public upstream
file -- never the seal, whose edit list would tell the reviewer which change is genuine), with the live
text around them as context. Unchanged maintainer text is not the candidate's claim (R21: a defect that
already existed there is a recorded residual, never a blocker), and in that round 26 of the 31 model
flags on Lane L controls were on such text. The deterministic claim rule keeps every finding on a Lane R
case and, on a Lane L case, every finding whose quote touches a changed line.

Verdict mapping: a finding the reviewer's own clearances proved false is ``supported``; a BLOCKING
``contradiction``/``name_denial`` is ``false`` (class A/D9: a checkable claim the facts contradict); any
other BLOCKING finding is ``unverifiable`` (class D: not grounded). A finding is written at every case
line its quote spans, up to ``MAX_ANCHOR_LINES`` (one wrapped sentence; the reviewer derives the quote from
the lines it cites); a longer quote is written at its first line only, so a wide citation can never cover
a seed by accident. In round 43445578226 two class A seeds were caught on the right sentence but written
one line early (the count sat on the second line of a wrapped sentence). A finding with no locatable line
is written at line ``len(lines) + 1``, past the end of the text: it still flags its candidate (fail closed
for a clean control) and can never match a seeded line by accident. Each row records the finding's
``source`` (``llm`` or ``deterministic``) for the post-freeze adjudication (``run_acceptance_writer.py``).

Fail closed: a case whose review stays unavailable after one retry, a budget refusal or a missing seal ends
the run with exit 1 and NO findings file, so nothing incomplete is ever frozen; the workflow's bounded
attempts (``run_m9_seeder.MAX_AUDIT_ATTEMPTS``) decide what happens next.

Adjudication of flags on clean controls (docs/DECISION_LOG.md 2026-11-12) is NOT done here: a second pass
of the same model, prompt and evidence is not an independent check. It is done after the findings are
frozen, by the acceptance writer's deterministic adjudicator (no model: the pinned facts, the renderer's
line ownership, the Lane L engine's recorded derivations and re-certification), plus any committed
adjudication file on main through the run-request ``acceptance-write`` override; every flag neither
decides stays unadjudicated and counts against both the candidate and the auditor (fail closed).

``resolve`` copies a FROZEN findings file out of git for the scorer and the writer: from main (the
checkout), or from the hosted auditor's bot branch ``audit-findings/run-<seed_run_id>``, which must hold
exactly one commit, made by github-actions[bot], on top of a commit of main, adding only
``evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/findings-<seed_run_id>.json``.

    python scripts/run_m9_auditor.py audit --case-index DIR/case_index.json --candidates DIR/candidates \\
        --out findings.json [--max-calls 600]
    python scripts/run_m9_auditor.py resolve --seed-run-id ID --findings-path PATH [--findings-ref REF] --out FILE
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Collection, Mapping, Sequence
from pathlib import Path
import re
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_rr_spec = importlib.util.spec_from_file_location("run_request", REPO_ROOT / "scripts" / "run_request.py")
run_request = importlib.util.module_from_spec(_rr_spec)
_rr_spec.loader.exec_module(run_request)

FALSE_KINDS = frozenset({"contradiction", "name_denial"})
DEFAULT_MAX_CALLS = 600
#: The most case lines one finding is written at: a wrapped sentence (see the module docstring).
MAX_ANCHOR_LINES = 3


class AuditError(RuntimeError):
    """The audit cannot produce a complete, honest findings file."""


# --- findings: one reviewer verdict -> M9 finding rows ------------------------------------------------


def locate(quote: str, rows: Sequence[str]) -> int | None:
    """The 1-based line of ``rows`` holding the first non-blank line of ``quote`` (exact, then contained)."""
    first = next((ln.strip() for ln in (quote or "").splitlines() if ln.strip()), "")
    if not first:
        return None
    for index, row in enumerate(rows):
        if row.strip() == first:
            return index + 1
    for index, row in enumerate(rows):
        if first in row:
            return index + 1
    return None


def quote_lines(quote: str, rows: Sequence[str]) -> tuple[int, ...]:
    """The 1-based case lines ``quote`` spans, ``()`` when it cannot be located. The first place where
    every line of the quote matches consecutively wins (a quote whose first line is common -- a
    ```` ```python ```` fence, a table delimiter -- is located by the whole quote, not by the first
    row equal to its first line); otherwise its first line (``locate``) and each following case line
    that holds the quote's next non-blank line."""
    whole = [ln.strip() for ln in (quote or "").strip("\n").splitlines()]
    if len(whole) > 1:
        for start in range(len(rows) - len(whole) + 1):
            if all(rows[start + k].strip() == piece for k, piece in enumerate(whole)):
                return tuple(range(start + 1, start + 1 + len(whole)))
    first = locate(quote, rows)
    if first is None:
        return ()
    wanted = [ln.strip() for ln in (quote or "").splitlines() if ln.strip()]
    found = [first]
    number = first
    for piece in wanted[1:]:
        if number >= len(rows) or piece not in rows[number]:
            break
        number += 1
        found.append(number)
    return tuple(found)


def anchor_lines(quote: str, rows: Sequence[str]) -> tuple[int, ...]:
    """The lines one finding is written at: every line of a quote of at most ``MAX_ANCHOR_LINES``
    lines, else the quote's first line only (see the module docstring)."""
    spanned = quote_lines(quote, rows)
    return spanned if len(spanned) <= MAX_ANCHOR_LINES else spanned[:1]


def findings_for(case_id: str, text: str, findings: Sequence[Any]) -> list[dict[str, Any]]:
    """The M9 rows for one case from the reviewer's final ``Finding`` objects (see module docstring)."""
    rows = text.splitlines()
    past_end = len(rows) + 1
    out: list[dict[str, Any]] = []
    for finding in findings:
        if finding.status == "CLEARED":
            verdict = "supported"
        elif finding.claim_kind in FALSE_KINDS:
            verdict = "false"
        else:
            verdict = "unverifiable"
        lines = anchor_lines(finding.quote, rows)
        for line in lines or (past_end,):
            out.append({
                "candidate_id": case_id,
                "claim": f"[{finding.claim_kind}] {finding.message}".strip()[:2000],
                "verdict": verdict,
                "path": f"{case_id}.md",
                "line": line,
                "evidence": (finding.evidence or finding.rule or finding.source)[:500],
                "located": bool(lines),
                "source": finding.source,
            })
    return out


def scoped_deterministic(
    findings: Sequence[Any], text: str, changed: frozenset[int] | None
) -> tuple[Any, ...]:
    """The deterministic claim findings one case's review carries: all of them when ``changed`` is
    ``None`` (Lane R), else those whose quote touches a changed line (Lane L, see the module docstring)."""
    if changed is None:
        return tuple(findings)
    rows = text.splitlines()
    return tuple(f for f in findings if set(quote_lines(f.quote, rows)) & changed)


def audit_scope(lane: str, source: Any, text: str) -> tuple[Mapping[str, Any], frozenset[int] | None]:
    """(the ``validation`` the review is given, the Lane L changed lines or ``None``). A Lane L case gets
    ``{"lane": "L"}`` and nothing else from its seal -- no edit list, no derivations, no residuals -- so
    ``llm_review.edit_scope`` scopes it to the lines that differ from the live README (blind: a seed is
    one more differing line, and nothing says which differing line is a genuine edit)."""
    from repo_presenter.readme.review.llm_review import edit_scope

    if lane == "L":
        validation: Mapping[str, Any] = {"lane": "L"}
        return validation, edit_scope(rendered=False, validation=validation,
                                      candidate_readme=text, original_readme=source.original)
    return source.validation, None


# --- derivation: the lines the pipeline's own deterministic stages re-derive (BL-013, round 2) ----------
#
# Hosted round 43559491132 (recall 0.421, false-flag 0.318): 10 of the 11 missed seeds sat on a line a
# deterministic stage owns (the ``# Title`` line the Lane R renderer prints, or a Lane L line no
# correction writes), and 20 of the 31 model flags on re-certifying controls were on lines such a stage
# writes. The auditor re-derives those lines itself, blind -- the Lane L engine re-run over the PUBLIC
# live README with the pinned facts and tree, the Lane R renderer re-run over the pinned facts, plan,
# units and dispositions -- and never reads the seal's README.
#
# DETECTION: a deterministic-owned line the re-derivation does not produce is a deterministic finding.
#
# CLEARANCE is narrower (supervisor review, R36 "question the checks"): a reproduced line is only
# consistent with OUR facts, and the 2026-11-13 fact-check registered real false claims those very stages
# print. A model flag on a reproduced line is cleared only when (1) the line derives from SUPPORTED facts
# -- a Lane L engine edit whose every cited fact is SUPPORTED (never unchanged maintainer text, never a
# locator-only structure fix), a Lane R line the renderer prints from facts alone (identical when every
# authored unit is replaced by a sentinel, so no authored unit text is ever cleared); (2) no row of the
# findings register (``data/readme_findings.json``) and no claim detector refutes it; and (3) its origin
# is not a known-false class: counts (K05), "Enterprise Edition" naming and its detector (K10), "Gets or
# sets" (K03), throw/raise/not-implemented behaviour (K02). Every other flag stays.

#: Line-text classes the 2026-11-13 fact-check found false in deterministic output
#: (docs/investigations/2026-11-13-lane-r-false-claim-review.md, K01-K11).
KNOWN_FALSE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("K05 type count", r"\b\d+\s+(?:verified\s+)?(?:public\s+)?(?:types?|classes|enums|interfaces)\b"),
    ("K10 Enterprise Edition naming", r"Enterprise\s+Edition"),
    ("K03 accessor wording", r"\bGets\s+or\s+sets\b"),
    ("K02 behaviour claim", r"\b(?:throws?|thrown|raises?|raised|not\s+implemented|always\s+returns|succeeds?|succeeded|fails?|failed)\b"),
)
#: Lane L detectors whose output is a known-false class.
KNOWN_FALSE_DETECTORS: Mapping[str, str] = {
    "enterprise_edition_naming": "K10 Enterprise Edition naming",
    "stale_type_count": "K05 type count",
    "listed_type_count": "K05 type count",
}
#: The text every authored unit is replaced by in the facts-only Lane R render.
_SENTINEL = "Authored unit {index} placeholder."

# --- K05 / K10 by provenance (BL-013 round 2, after BL-065 and BL-070) -------------------------------
#
# The 2026-11-13 fact-check's K05 and K10 instances were each a defect of the producer, now fixed at the
# root: counts over tree packages the build never ships (BL-065, ``recertify.shipped_facts``) or over
# types public only under ``#if`` / nested in internal types (BL-065, C#: registered rows in
# ``data/readme_findings.json`` until re-sealed), and an Enterprise Edition name that repeats the link
# just before it or drops the platform (BL-070, ``enterprise_edition_naming`` v4). So a K05 / K10 line no
# longer stays kept for its class alone: it stays kept unless its provenance VERIFIES it --
#
# * K05: every count the line states is the computation from the (shipped-package) facts: N "types" =
#   SUPPORTED class + enum ``public_symbol`` facts, "classes" = the classes among them, "enums" = the
#   enums; "N of them listed below" = the type-table rows that follow, to the next level-1/2 heading. A
#   kind no fact counts ("interfaces") or any other number stays kept;
# * K10: every "<name> — Enterprise Edition" on the line names the product as the README's own H1 does
#   (" FOSS" removed; the family alone at a family-level target), the ``link_target:product.enterprise``
#   fact is SUPPORTED, any link carrying it targets that fact's URL, and no bare name follows a link that
#   already names it (the Cells C++ duplicate).
#
# The register and the claim detectors still refute first (Words .NET "618 public types" is a registered
# K05 row), K02/K03 are unchanged, and the verified computation is written into the cleared row
# (``provenance``) so the model's flag is answered by evidence, never by silence.

#: The K05 statement shape (``KNOWN_FALSE_PATTERNS``) with its parts captured.
_K05_COUNT = re.compile(
    r"(?i)(?<![\w.,])(?P<count>\d{1,3}(?:,\d{3})+|\d+)\s+(?:verified\s+)?(?:public\s+)?"
    r"(?P<noun>types?|classes(?:\s+and\s+(?:enumerations|enums))?|enums|interfaces)\b"
)
_LISTED_OF_THEM = re.compile(r"(?i)(?<![\w.,])(?P<count>\d{1,3}(?:,\d{3})+|\d+)\s+of\s+them\s+(?:are\s+)?listed\b")
_TYPE_TABLE_ROW = re.compile(r"^\s*\|\s*`[^`]+`\s*\|")
_LEVEL_1_2 = re.compile(r"^\s*#{1,2}\s")
_EE_NAME = re.compile(r"(\[)?(?P<name>Aspose\.[^\]\[]*?)\s*[—–]\s*Enterprise\s+Edition(?:\]\((?P<url>[^)\s]+)\))?")
_H1 = re.compile(r"^#(?!#)[ \t]+(\S.*)$")
_BELOW = re.compile(r"(?i)\b(?:below|as\s+follows|(?:table|tables)\s+that\s+follows?|following\s+tables?)\b")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _count_value(text: str) -> int:
    return int(text.replace(",", ""))


def count_provenance(rows: Sequence[str], number: int, facts: Any) -> str | None:
    """The verified computation of every count line ``number`` (1-based) of ``rows`` states, or
    ``None`` when any count on it is not the facts' computation (see the section comment)."""
    from repo_presenter.readme.validation.surface_claims import _evidence_type_count, type_counts

    row = rows[number - 1]
    types, classes = type_counts(facts)
    by_locator = _evidence_type_count(facts)
    if types == 0 or by_locator != types:
        return None
    enums = types - classes
    roots: dict[str, int] = {}
    for fact in getattr(facts, "facts", ()):
        if fact.kind == "public_symbol" and fact.polarity == "SUPPORTED" and \
                (fact.attributes or {}).get("symbol_kind") in ("class", "enum") and fact.evidence:
            parts = fact.evidence[0].path.split("/")
            root = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
            roots[root] = roots.get(root, 0) + 1
    # a hard-wrapped sentence ("... ships 198" / "public types across ..."): read the line with the next
    # prose line, counting only the statements that start on this line
    following = rows[number] if number < len(rows) else ""
    joined = row
    if following.strip() and not following.lstrip().startswith(("|", "#", "```", "- ", "* ")):
        joined = f"{row} {following.strip()}"
    listed = 0
    for later in rows[number:]:
        if _LEVEL_1_2.match(later):
            break
        listed += bool(_TYPE_TABLE_ROW.match(later))
    stated = []
    for match in _K05_COUNT.finditer(joined):
        if match.start() >= len(row):
            continue
        value, noun = _count_value(match.group("count")), match.group("noun").lower()
        expected = types if noun.startswith("type") or " and " in noun else classes if noun == "classes" else \
            enums if noun == "enums" else None
        if expected is None or value != expected:
            return None
        # a total said to be listed/organized/summarized below is also held to the rows that follow
        # (rule (h)'s listed-count, widened to every "below" phrasing): PDF Python's "385 public types are
        # organized by module below" heads 284 rows, Cells C++'s "195 ... is listed below" 157
        sentence = _SENTENCE_END.split(joined[match.start():], maxsplit=1)[0]
        if _BELOW.search(sentence) and not _LISTED_OF_THEM.search(sentence) and value != listed:
            return None
        stated.append(" ".join(match.group(0).split()))
    for match in _LISTED_OF_THEM.finditer(joined):
        if match.start() >= len(row):
            continue
        if _count_value(match.group("count")) != listed:
            return None
        stated.append(f"{listed} listed (type-table rows that follow)")
    if not stated:
        return None
    within = ", ".join(f"{root} {n}" for root, n in sorted(roots.items()))
    return (f"K05 verified: {'; '.join(stated)} = SUPPORTED class/enum public_symbol facts "
            f"({classes} classes + {enums} enums = {types}; by source root: {within}), after the "
            "build's package list (recertify.shipped_facts)")


def enterprise_provenance(rows: Sequence[str], number: int, facts: Any) -> str | None:
    """The verified naming of every "— Enterprise Edition" mention on line ``number``, or ``None``."""
    enterprise = next((f for f in getattr(facts, "facts", ()) if f.id == "link_target:product.enterprise"), None)
    if enterprise is None or enterprise.polarity != "SUPPORTED":
        return None
    h1 = next((m.group(1).strip() for m in map(_H1.match, rows) if m), None)
    if not h1:
        return None
    expected = re.sub(r"[ .]FOSS\b", "", h1)  # as enterprise_edition_naming derives it
    if (enterprise.attributes or {}).get("level") == "family":
        expected = expected.split(" for ", 1)[0]
    row = rows[number - 1]
    previous = rows[number - 2] if number > 1 else ""
    found = False
    for match in _EE_NAME.finditer(row):
        found = True
        name = " ".join(match.group("name").split())
        if name.lower() != " ".join(expected.split()).lower():
            return None
        if match.group(1) and match.group("url") and match.group("url").rstrip("/") != enterprise.value.rstrip("/"):
            return None
        if not match.group(1):
            before = row[: match.start()]
            if not before.strip():
                before = previous + " " + before
            if re.search(r"\[[^\]]*\bAspose\.[^\]]*\]\([^)\s]+\)\s*[,;:—–-]?\s*(?:the\s*)?$", before, re.I):
                return None
    if not found:
        return None
    return (f"K10 verified: named '{expected} — Enterprise Edition' as the README's H1 names the product "
            f"({(enterprise.attributes or {}).get('level', 'platform')}-level target {enterprise.value}, SUPPORTED)")


def class_provenance(label: str, rows: Sequence[str], number: int, facts: Any) -> str | None:
    if label.startswith("K05"):
        return count_provenance(rows, number, facts)
    if label.startswith("K10"):
        return enterprise_provenance(rows, number, facts)
    return None


class Rederived(NamedTuple):
    """The README a deterministic stage writes, and per line (0-based) where it came from: ``{"source":
    "edit", "detector", "fact_ids"}`` or ``{"source": "maintainer"}`` (Lane L); ``{"source": "renderer"}``
    or ``{"source": "authored"}`` (Lane R)."""

    text: str
    origins: tuple[Mapping[str, Any], ...]


class Derivation(NamedTuple):
    """For one case text: ``derivable`` -- deterministic-owned lines the re-derivation reproduces;
    ``underived`` -- deterministic-owned lines it does not (each a deterministic finding);
    ``clearable`` -- the derivable lines a model flag may be cleared on; ``kept`` -- every other
    derivable line, with why a flag there stays."""

    derivable: frozenset[int]
    underived: frozenset[int]
    clearable: frozenset[int] = frozenset()
    kept: Mapping[int, str] = {}
    #: clearable lines of a K05/K10 class: the verified computation (``class_provenance``)
    provenance: Mapping[int, str] = {}


def owned_lines(lane: str, text: str, facts: Any) -> frozenset[int]:
    """The non-blank lines of ``text`` a deterministic stage owns: every line of a Lane L candidate,
    the lines the renderer prints of a Lane R one (structural, as the production Lane R review)."""
    from repo_presenter.readme.review.scope import authored_table_lines, line_sections

    rows = text.splitlines()
    if lane == "L":
        return frozenset(n for n, row in enumerate(rows, 1) if row.strip())
    sections = line_sections(text, True, authored_table_lines(text, facts))
    return frozenset(n for n, (row, section) in enumerate(zip(rows, sections), 1)
                     if row.strip() and section is None)


def keep_reason(
    lane: str, row: str, origin: Mapping[str, Any] | None, facts: Any,
    rows: Sequence[str] = (), number: int = 0, verified: dict[int, str] | None = None,
) -> str | None:
    """Why a model flag on this reproduced line must stay (``None``: it may be cleared). See the
    section comments: SUPPORTED-fact origin, and a known-false class only when its provenance does not
    verify it (``class_provenance`` over ``rows``, the whole case text; a verified line's computation is
    recorded in ``verified``). The register and the claim detectors are checked by the caller."""
    if not origin:
        return "no recorded origin"
    source = origin.get("source")

    def unverified(label: str) -> str | None:
        proof = class_provenance(label, rows, number, facts) if rows and number else None
        if proof is None:
            return label
        if verified is not None and proof not in verified.get(number, ""):
            verified[number] = "; ".join(filter(None, [verified.get(number), proof]))
        return None

    if lane == "L":
        if source != "edit":
            return "maintainer text, not derived from a fact"
        detector = str(origin.get("detector") or "")
        if detector in KNOWN_FALSE_DETECTORS and (why := unverified(KNOWN_FALSE_DETECTORS[detector])):
            return why
        fact_ids = list(origin.get("fact_ids") or ())
        if not fact_ids:
            return "edit cites no fact (locator only)"
        known = {fact.id: fact for fact in getattr(facts, "facts", ())}
        if any(known.get(fid) is None or known[fid].polarity != "SUPPORTED" for fid in fact_ids):
            return "edit cites a fact that is not SUPPORTED"
    elif source != "renderer":
        return "authored unit text"
    else:
        polarities = facts_in_line(row, facts)
        # a computed count is a fact-derived statement when its computation verifies (K05 below)
        if not polarities and not (rows and number and count_provenance(rows, number, facts)):
            return "no fact value in the line"
        if any(p != "SUPPORTED" for p in polarities):
            return "the line carries a fact that is not SUPPORTED"
    for label, pattern in KNOWN_FALSE_PATTERNS:
        if re.search(pattern, row, re.IGNORECASE) and (why := unverified(label)):
            return why
    return None


_FACT_INDEX: dict[int, tuple[Any, dict[str, list[str]], list[tuple[str, str]]]] = {}


def _fact_index(facts: Any) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """(symbol name -> polarities, by qualified value and by last segment; [(spaced value, polarity)] of
    every other fact), built once per facts document."""
    from repo_presenter.readme.review.matching import spaced

    cached = _FACT_INDEX.get(id(facts))
    if cached is not None and cached[0] is facts:
        return cached[1], cached[2]
    symbols: dict[str, list[str]] = {}
    others: list[tuple[str, str]] = []
    for fact in getattr(facts, "facts", ()):
        value = str(fact.value or "")
        if len(value) < 4 or fact.kind == "inherited_unit":
            continue
        if fact.kind == "public_symbol":
            for name in {value, value.rsplit(".", 1)[-1]}:
                symbols.setdefault(name, []).append(str(fact.polarity))
        else:
            others.append((spaced(value), str(fact.polarity)))
    _FACT_INDEX[id(facts)] = (facts, symbols, others)
    return symbols, others


def facts_in_line(row: str, facts: Any) -> list[str]:
    """The polarities of the facts a renderer-printed line states: a fact whose value occurs in the line
    (``matching.present``, the strict reader), or a ``public_symbol`` whose qualified value or last name
    segment is a backticked identifier of the line. Values shorter than four characters are ignored."""
    import re

    from repo_presenter.readme.review.matching import present, spaced

    symbols, others = _fact_index(facts)
    found: list[str] = []
    for ticked in set(re.findall(r"`([^`]+)`", row)):
        for name in {ticked, ticked.rsplit(".", 1)[-1]}:
            found.extend(symbols.get(name, ()))
    flat = spaced(row)
    for value, polarity in others:
        if value in flat and present(value, row):
            found.append(polarity)
    return found


def refuted_lines(text: str, facts: Any, repository: str, register: Sequence[Mapping[str, Any]] = ()) -> dict[int, str]:
    """1-based lines of ``text`` a claim detector or an OPEN register row of ``repository`` refutes."""
    out: dict[int, str] = {}
    try:
        from repo_presenter.readme.validation.claims import claim_findings

        for finding in claim_findings(text, facts):
            last = finding.last if finding.last is not None else finding.line
            for number in range(finding.line + 1, last + 2):
                out.setdefault(number, "claim detector")
    except Exception:  # noqa: BLE001 -- a detector that cannot run refutes nothing; the flag is not cleared either
        return {n: "claim detector unavailable" for n in range(1, len(text.splitlines()) + 1)}
    quotes = [" ".join(str(r.get("quote") or "").split()) for r in register
              if r.get("repository") == repository and r.get("status") == "OPEN"]
    for number, row in enumerate(text.splitlines(), 1):
        flat = " ".join(row.split())
        if len(flat) >= 12 and any(q and (q in flat or flat in q) for q in quotes):
            out.setdefault(number, "findings register")
    return out


def load_register(path: Path = REPO_ROOT / "data" / "readme_findings.json") -> list[Mapping[str, Any]]:
    try:
        return list(json.loads(path.read_text(encoding="utf-8")).get("findings") or [])
    except (OSError, ValueError):
        return []


def derivation(
    lane: str, text: str, facts: Any, rederived: str | Rederived, *, repository: str = "",
    register: Sequence[Mapping[str, Any]] = (), ask: Collection[int] | None = None,
) -> Derivation:
    """Align ``text`` with the re-derived README (``difflib`` over whole lines). A deterministic-owned
    line in an ``equal`` block is derivable, any other deterministic-owned line is underived; a
    derivable line is clearable only under the section comment's three conditions. ``ask`` (the lines a
    model flag sits on) limits that judgement to those lines; every other derivable line is ``kept``."""
    import difflib

    if isinstance(rederived, str):
        rederived = Rederived(rederived, ())
    owned = owned_lines(lane, text, facts)
    rows = text.splitlines()
    source_of: dict[int, Mapping[str, Any] | None] = {}
    matcher = difflib.SequenceMatcher(None, rederived.text.splitlines(), rows, autojunk=False)
    for tag, i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(j2 - j1):
                i = i1 + k
                source_of[j1 + k + 1] = rederived.origins[i] if i < len(rederived.origins) else None
    derivable = frozenset(owned & set(source_of))
    refuted = refuted_lines(text, facts, repository, register) if derivable and (ask is None or ask) else {}
    kept: dict[int, str] = {}
    verified: dict[int, str] = {}
    for number in sorted(derivable):
        if ask is not None and number not in ask:
            kept[number] = "not asked"
            continue
        why = refuted.get(number) or keep_reason(lane, rows[number - 1], source_of[number], facts,
                                                 rows, number, verified)
        if why:
            kept[number] = why
    clearable = frozenset(derivable - set(kept))
    return Derivation(derivable=derivable, underived=frozenset(owned - set(source_of)),
                      clearable=clearable, kept=kept,
                      provenance={n: p for n, p in verified.items() if n in clearable})


def _line_origins(text: str, spans: Sequence[tuple[int, int]], edits: Sequence[Any]) -> tuple[Mapping[str, Any], ...]:
    """Per line of the corrected ``text``: the engine edit whose output span covers it, else maintainer."""
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    origins: list[Mapping[str, Any]] = []
    for number, start in enumerate(starts[: len(text.splitlines())]):
        end = starts[number + 1] - 1 if number + 1 < len(starts) else len(text)
        found: Mapping[str, Any] = {"source": "maintainer"}
        for edit, (a, b) in zip(edits, spans):
            if b > a and a < end + 1 and b > start:  # a deletion (empty span) writes no line
                found = {"source": "edit", "detector": edit.detector, "fact_ids": tuple(edit.fact_ids)}
                break
        origins.append(found)
    return tuple(origins)


def rederived_readme(
    lane: str, bundle: Path, entry: Any, original: str, tree_paths: Sequence[str] = (), facts: Any = None,
) -> Rederived:
    """The README the pipeline's deterministic stage writes from the pinned inputs, zero calls, with each
    line's origin: Lane L, the correction engine over the live README (``recertify._rerun_lane_l``'s
    context); Lane R, the renderer over the stored facts, plan, content units and dispositions, and once
    more with every authored unit replaced by a sentinel (a line identical in both is printed from facts
    alone). The seal's README is never read. ``facts`` (default: the bundle's) is the document after
    ``recertify.shipped_facts``, as the current pipeline re-derives it."""
    from repo_presenter.core.facts import read_facts

    if facts is None:
        facts = read_facts(bundle / "facts.json")
    if lane == "L":
        from repo_presenter.core.registry_entry_stub import RegistryEntryStub
        from repo_presenter.readme.correction.engine import correct
        from repo_presenter.readme.correction.model import Context

        corrections = bundle / "corrections.json"
        readme_path = "README.md"
        if corrections.is_file():
            readme_path = str(json.loads(corrections.read_text(encoding="utf-8")).get("readme_path") or "README.md")
        ctx = Context(
            entry=RegistryEntryStub(repository=entry.repository, family=entry.family,
                                    platform=entry.platform, ecosystem=entry.ecosystem),
            facts=facts, readme=original, tree_paths=tuple(tree_paths), readme_path=readme_path,
        )
        result = correct(ctx)
        return Rederived(result.corrected, _line_origins(result.corrected, result.output_spans, result.edits))
    import contextlib
    import copy
    import difflib

    from repo_presenter.extractors.platforms.registry import plugin_for
    from repo_presenter.readme.composition.renderer import render_readme

    # As recertify_bundle: a platform registers its ecosystem spec when its plugin is imported.
    with contextlib.suppress(Exception):
        plugin_for(entry.ecosystem)

    def read(name: str) -> dict[str, Any]:
        path = bundle / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    units_name = "content_units.coherent.json" if (bundle / "content_units.coherent.json").is_file() else "content_units.json"
    plan, units, dispositions = read("plan.json"), read(units_name), read("dispositions.json")
    full = render_readme(entry, facts, plan, units, dispositions)
    blank = copy.deepcopy(units)
    for index, unit in enumerate(blank.get("units") or []):
        if isinstance(unit, dict) and isinstance(unit.get("text"), str):
            unit["text"] = _SENTINEL.format(index=index)
    origins: list[Mapping[str, Any]] = [{"source": "authored"}] * len(full.splitlines())
    try:
        facts_only = render_readme(entry, facts, plan, blank, dispositions)
    except Exception:  # noqa: BLE001 -- no facts-only render: nothing is known to be fact-derived
        return Rederived(full, tuple(origins))
    matcher = difflib.SequenceMatcher(None, facts_only.splitlines(), full.splitlines(), autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for j in range(j1, j2):
                origins[j] = {"source": "renderer"}
    return Rederived(full, tuple(origins))


def apply_derivation(case_id: str, text: str, rows: Sequence[Mapping[str, Any]], derived: Derivation | None) -> list[dict[str, Any]]:
    """The case's finding rows with the derivation applied (see the section comment): a located model
    flag on a CLEARABLE line is cleared (``supported``, ``cleared_by``); a flag on any other derivable
    line stays and records why (``kept_because``); every underived line gets one deterministic finding.
    ``None`` (no re-derivation) changes nothing: nothing is cleared, nothing is added (fail closed)."""
    out = [dict(r) for r in rows]
    if derived is None:
        return out
    for row in out:
        if row.get("source") != "llm" or row.get("verdict") == "supported" or not row.get("located"):
            continue
        line = row.get("line")
        if line in derived.clearable:
            row["verdict"] = "supported"
            row["cleared_by"] = "derivation"
            proof = derived.provenance.get(line)
            row["evidence"] = ("cleared: the line is printed from SUPPORTED facts by a deterministic stage "
                               "(zero-call re-derivation), no register row or claim detector refutes it, and it is "
                               + (f"verified by its provenance ({proof})" if proof else "in no known-false class")
                               + f"; was: {row.get('evidence', '')}")[:900]
            if proof:
                row["provenance"] = proof
        elif line in derived.kept:
            row["kept_because"] = derived.kept[line]
    lines = text.splitlines()
    for number in sorted(derived.underived):
        out.append({
            "candidate_id": case_id,
            "claim": f"[unsupported_claim] no deterministic stage writes this line from the pinned evidence: "
                     f"{lines[number - 1].strip()}"[:2000],
            "verdict": "unverifiable", "path": f"{case_id}.md", "line": number,
            "evidence": "m9_underived_line: the line is owned by a deterministic stage (Lane L correction engine / "
                        "Lane R renderer) but its zero-call re-derivation from the pinned evidence does not produce it",
            "located": True, "source": "deterministic",
        })
    return out


# --- sources: each case's own seal, as the reviewer's evidence -----------------------------------------


def seal_for(history: Mapping[tuple[str, str], Sequence[Any]], repository: str, lane: str, revision: str) -> Any:
    """The latest materialized seal of ``(repository, lane)`` at ``revision`` (the seeder takes the latest)."""
    for seal in reversed(list(history.get((repository, lane), ()))):
        if seal.revision == revision and seal.bundle is not None and not seal.error:
            return seal
    raise AuditError(f"no readable seal of {repository} lane {lane} at {revision}")


def source_for(seal: Any, case_id: str) -> Any:
    """The reviewer's ``SourceCandidate`` for one seal, judged as a whole document (``rendered=False``)."""
    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed
    from repo_presenter.readme.bundle.recheck import original_readme
    from repo_presenter.readme.review.calibration.sources import (
        build_source,
        load_lane_l_bundle_candidate,
    )

    bundle = Path(seal.bundle)
    if seal.lane == "L":
        return load_lane_l_bundle_candidate(bundle, name=case_id)

    def read(name: str) -> dict[str, Any]:
        path = bundle / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    facts = read_facts(bundle / "facts.json")
    entry = require_listed(load_registry(REPO_ROOT / "data" / "registry.json"), seal.repository)
    sealed = (bundle / "README.md").read_text(encoding="utf-8", newline="")
    patch_path = bundle / "README.patch.diff"
    original = original_readme(sealed, patch_path.read_text(encoding="utf-8", newline="")) if patch_path.is_file() else None
    if original is None:
        from repo_presenter.recertify import fetch_source

        with tempfile.TemporaryDirectory(prefix="m9-audit-src-") as work:
            snapshot = fetch_source(seal.repository, seal.revision, Path(work))
        if snapshot.readme is None:
            raise AuditError(f"the live README of {seal.repository}@{seal.revision} cannot be read")
        original = snapshot.readme.decode("utf-8", errors="replace")
    units_name = "content_units.coherent.json" if (bundle / "content_units.coherent.json").is_file() else "content_units.json"
    source = build_source(
        name=case_id, entry=entry, facts=facts, plan=read("plan.json"), units=read(units_name),
        dispositions=read("dispositions.json"), investigation=read("investigation.json"),
        original=original, tree_paths=[], scratch=bundle, recorded_readme=sealed,
    )
    return dataclasses.replace(source, rendered=False)


# --- the audit -------------------------------------------------------------------------------------------

#: ((lane, source), case text) -> the reviewer's ReviewVerdict; raises ReviewUnavailable when no valid review
#: exists.
Reviewer = Callable[[Any, str], Any]


def audit_cases(
    case_index: Sequence[Mapping[str, Any]],
    texts: Mapping[str, str],
    sources: Callable[[Mapping[str, Any]], Any],
    review: Reviewer,
    *,
    retries: int = 1,
    derive: Callable[[Mapping[str, Any], str, frozenset[int]], Derivation | None] | None = None,
) -> list[dict[str, Any]]:
    """Every case reviewed, in case-index order; ``AuditError`` when any case has no valid review after
    ``retries`` more attempts (a partial findings file is never returned). ``derive`` (the hosted run:
    ``case_derivation``) gives each case's zero-call re-derivation, applied by ``apply_derivation``."""
    from repo_presenter.readme.review.verdict import ReviewUnavailable

    findings: list[dict[str, Any]] = []
    for entry in case_index:
        case_id = str(entry["case_id"])
        if case_id not in texts:
            raise AuditError(f"case {case_id} has no candidate text")
        source = sources(entry)
        verdict, problem = None, None
        for _attempt in range(retries + 1):
            try:
                verdict = review(source, texts[case_id])
                break
            except ReviewUnavailable as error:
                problem = error
        if verdict is None:
            raise AuditError(f"case {case_id}: no valid review ({getattr(problem, 'reason', problem)})")
        rows = findings_for(case_id, texts[case_id], verdict.findings)
        if derive is not None:
            asked = frozenset(r["line"] for r in rows if r.get("source") == "llm" and r.get("located")
                              and r.get("verdict") != "supported")
            rows = apply_derivation(case_id, texts[case_id], rows, derive(entry, texts[case_id], asked))
        findings.extend(rows)
        print(f"{case_id} {entry.get('lane')} {verdict.verdict}: {len(rows)} findings", file=sys.stderr)
    return findings


def live_reviewer(ledger_path: Path, store_dir: Path, max_calls: int) -> Reviewer:
    """The existing reviewer as the gateway runs it (GPT_OSS_ENDPOINT/GPT_OSS_API_KEY from the environment,
    never printed), every attempt a ledger record, the program budget checked by ``run_job``."""
    from repo_presenter.core.config import load_gateway_config
    from repo_presenter.core.llm.jobs import CallStore, JobContext
    from repo_presenter.core.llm.ledger import Ledger
    from repo_presenter.core.llm.prompts import load_manifests
    from repo_presenter.readme.review.independent_reviewer import claim_contradiction_rule
    from repo_presenter.readme.review.llm_review import review_with_model

    prompts = load_manifests(REPO_ROOT / "prompts")
    config = load_gateway_config(os.environ)
    ledger = Ledger(ledger_path, call_budget=max_calls)
    store = CallStore(store_dir)

    def review(case: Any, text: str) -> Any:
        lane, source = case
        validation, changed = audit_scope(lane, source, text)
        return review_with_model(
            prompts=prompts, config=config, ledger=ledger, store=store,
            context=JobContext(repository=source.repository, source_revision=source.facts.source_revision),
            candidate_readme=text, original_readme=source.original, facts=source.facts,
            plan=source.plan, dispositions=source.dispositions, validation=validation,
            deterministic_findings=scoped_deterministic(claim_contradiction_rule(text, source.facts), text, changed),
            rendered=False, audit=True,
        )

    return review


def cmd_audit(args: argparse.Namespace) -> int:
    from repo_presenter.core.state.bundle_store import seal_history

    case_index = json.loads(args.case_index.read_text(encoding="utf-8"))
    texts = {
        str(e["case_id"]): (args.candidates / f"{e['case_id']}.md").read_text(encoding="utf-8")
        for e in case_index if (args.candidates / f"{e['case_id']}.md").is_file()
    }
    work = args.work or Path(tempfile.mkdtemp(prefix="m9-audit-"))
    history = seal_history(remote=args.remote, scratch=work / "seals")
    review = live_reviewer(work / "ledger.jsonl", work / "calls", args.max_calls)

    def sources(entry: Mapping[str, Any]) -> Any:
        seal = seal_for(history, str(entry["repository"]), str(entry["lane"]), str(entry["revision"]))
        return str(entry["lane"]), source_for(seal, str(entry["case_id"]))

    def derive(entry: Mapping[str, Any], text: str, asked: frozenset[int]) -> Derivation | None:
        seal = seal_for(history, str(entry["repository"]), str(entry["lane"]), str(entry["revision"]))
        return case_derivation(seal, text, work / "trees", ask=asked)

    try:
        findings = audit_cases(case_index, texts, sources, review, derive=derive)
    except AuditError as error:
        print(f"FAIL: {error}; no findings written", file=sys.stderr)
        return 1
    valid, why = evidence_validity(findings)
    if not valid:
        print(f"FAIL: findings are not structurally valid ({why}); none written", file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    flagged = sum(1 for f in findings if f["verdict"] != "supported")
    print(f"audited {len(case_index)} cases: {len(findings)} findings, {flagged} flagged -> {args.out}")
    return 0


def case_derivation(
    seal: Any, text: str, work: Path, fetch: Callable[..., Any] | None = None, ask: Collection[int] | None = None,
) -> Derivation | None:
    """``derivation`` for one case from its seal's pinned inputs (never its README): Lane L reads the
    public live README the bundle records and the revision's tracked tree (``recertify.fetch_source``,
    read-only, for the link detectors); ``None`` when anything cannot be re-derived (fail closed)."""
    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed

    bundle = Path(seal.bundle)
    try:
        from repo_presenter.recertify import shipped_facts

        facts = read_facts(bundle / "facts.json")
        entry = require_listed(load_registry(REPO_ROOT / "data" / "registry.json"), seal.repository)
        original, tree_paths = "", ()
        if fetch is None:
            from repo_presenter.recertify import fetch_source as fetch
        snapshot = None
        if seal.lane == "L" or entry.ecosystem == "python":  # the build's package list (BL-065)
            work.mkdir(parents=True, exist_ok=True)
            snapshot = fetch(seal.repository, seal.revision, work)
            facts = shipped_facts(facts, entry.ecosystem, snapshot)[0] if getattr(snapshot, "manifests", None) else facts
        if seal.lane == "L":
            original = (bundle / "README.original.md").read_text(encoding="utf-8")
            tree_paths = snapshot.tree_paths
        rederived = rederived_readme(seal.lane, bundle, entry, original, tree_paths, facts)
    except Exception as error:  # noqa: BLE001 -- no re-derivation is no derivation, never a crash
        print(f"derivation unavailable for {seal.repository} lane {seal.lane}: {error}", file=sys.stderr)
        return None
    return derivation(seal.lane, text, facts, rederived, repository=seal.repository, register=load_register(), ask=ask)


def evidence_validity(findings: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    """The acceptance writer's own structural check (imported, never re-implemented)."""
    spec = importlib.util.spec_from_file_location("run_acceptance_writer", REPO_ROOT / "scripts" / "run_acceptance_writer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evidence_validity(findings)


# --- resolve: the frozen findings file, from main or from the hosted auditor's bot branch ---------------


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=cwd).stdout


def resolve_findings(
    seed_run_id: str, findings_path: str, findings_ref: str = "", *, remote: str = "origin",
    base_branch: str = "main", cwd: Path | None = None,
) -> bytes:
    """The bytes of the frozen findings file (see module docstring); ``AuditError`` otherwise."""
    if not run_request.is_run_id(seed_run_id):
        raise AuditError(f"seed run id {seed_run_id!r} is not a run id")
    if findings_path != run_request.findings_path_for(seed_run_id):
        raise AuditError(f"findings path {findings_path!r} is not {run_request.findings_path_for(seed_run_id)!r}")
    try:
        _git("fetch", "--no-tags", "--quiet", remote, f"+refs/heads/{base_branch}:refs/m9/base", cwd=cwd)
        if not findings_ref:
            return subprocess.run(["git", "show", f"refs/m9/base:{findings_path}"], capture_output=True,
                                  check=True, cwd=cwd).stdout
        if findings_ref != run_request.findings_ref_for(seed_run_id):
            raise AuditError(f"findings ref {findings_ref!r} is not {run_request.findings_ref_for(seed_run_id)!r}")
        _git("fetch", "--no-tags", "--quiet", remote, f"+refs/heads/{findings_ref}:refs/m9/findings", cwd=cwd)
        tip = _git("rev-parse", "refs/m9/findings", cwd=cwd).strip()
        parents = _git("rev-list", "--parents", "-n", "1", tip, cwd=cwd).split()[1:]
        if len(parents) != 1:
            raise AuditError(f"{findings_ref} tip {tip} has {len(parents)} parents, not one")
        if subprocess.run(["git", "merge-base", "--is-ancestor", parents[0], "refs/m9/base"],
                          capture_output=True, cwd=cwd).returncode != 0:
            raise AuditError(f"{findings_ref} is not one commit on top of a commit of {base_branch}")
        changed = _git("diff", "--name-only", "--no-renames", parents[0], tip, cwd=cwd).split()
        if changed != [findings_path]:
            raise AuditError(f"{findings_ref} changes {changed}, not only {findings_path}")
        emails = _git("log", "-1", "--format=%ae%n%ce", tip, cwd=cwd).split()
        if emails != [run_request.BOT_EMAIL, run_request.BOT_EMAIL]:
            raise AuditError(f"{findings_ref} tip was not made by github-actions[bot] ({emails})")
        return subprocess.run(["git", "show", f"{tip}:{findings_path}"], capture_output=True, check=True,
                              cwd=cwd).stdout
    except subprocess.CalledProcessError as error:
        raise AuditError(f"git failed: {(error.stderr or '').strip() or error}") from error


def cmd_resolve(args: argparse.Namespace) -> int:
    try:
        blob = resolve_findings(args.seed_run_id, args.findings_path, args.findings_ref, remote=args.remote)
        json.loads(blob)
    except (AuditError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(blob)
    print(f"resolved {args.findings_path} from {args.findings_ref or 'main'} -> {args.out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--case-index", type=Path, required=True)
    audit.add_argument("--candidates", type=Path, required=True)
    audit.add_argument("--out", type=Path, required=True)
    audit.add_argument("--remote", default="origin")
    audit.add_argument("--work", type=Path, default=None, help="ledger, call store and seal scratch")
    audit.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--seed-run-id", required=True)
    resolve.add_argument("--findings-path", required=True)
    resolve.add_argument("--findings-ref", default="")
    resolve.add_argument("--out", type=Path, required=True)
    resolve.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    return cmd_audit(args) if args.command == "audit" else cmd_resolve(args)


if __name__ == "__main__":
    raise SystemExit(main())
