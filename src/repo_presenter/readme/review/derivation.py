"""The lines a deterministic stage prints from SUPPORTED facts, and the clearance a model flag on such a
line earns (BL-013 round 2 for the M9 auditor; BL-400 for the production review).

One predicate, two consumers. ``scripts/run_m9_auditor.py`` re-derives a case (the Lane L engine over the
public live README, the Lane R renderer over the pinned facts, plan, units and dispositions) and clears a model
flag on a line a deterministic stage printed from SUPPORTED facts; the production independent review
(``clearances.derived_from_supported_facts``) asks the same question of the candidate it has just rendered. Before
BL-400 the predicate lived only in the script, so the audit cleared what the seal gate could not (hosted
re-runs 2026-11-20: Page Python's opening, printed from SUPPORTED format facts, blocked at seal time).

Nothing here weakens a check: a line is clearable only when it is printed by a deterministic stage from facts
alone (an authored unit is replaced by a sentinel, so no authored text is ever cleared), every fact in it is
SUPPORTED, no claim detector or open findings-register row refutes it, and its origin is not a known-false class.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

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
_LISTED_OF_THEM = re.compile(
    r"(?i)(?<![\w.,])(?P<count>\d{1,3}(?:,\d{3})+|\d+)\s+of\s+them\s+(?:are\s+)?"
    r"(?:listed|organi[sz]ed|grouped|shown|documented|tabulated)\b"  # rule (h)'s verbs (BL-093)
)
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
    from repo_presenter.readme.validation.surface_claims import (
        _evidence_type_count,
        type_counts,
    )

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
        # organized by module below" heads 284 rows, Cells C++'s "195 ... is listed below" 157. The rows
        # must reach the total, as BC-14's ``_count_findings`` holds them (``listed < stated``); rows beyond
        # it are the member tables under the types (BL-543: HTML Python's 303 over 517 rows, where this
        # check said ``!=`` and BC-14 passed the same sentence)
        sentence = _SENTENCE_END.split(joined[match.start():], maxsplit=1)[0]
        if _BELOW.search(sentence) and not _LISTED_OF_THEM.search(sentence) and value > listed:
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
            if re.search(r"\[[^\]]*\bAspose\.[^\]]*\]\([^)\s]+\)\s*[,;:—–-]?\s*(?:the\s*)?$", before, re.IGNORECASE):
                return None
    if not found:
        return None
    return (f"K10 verified: named '{expected} — Enterprise Edition' as the README's H1 names the product "
            f"({(enterprise.attributes or {}).get('level', 'platform')}-level target {enterprise.value}, SUPPORTED)")


def not_thrown_provenance(rows: Sequence[str], number: int, facts: Any) -> str | None:
    """The verified basis of a ``| `Type` | Declared; not thrown by library code. |`` row (BL-390): the renderer
    prints that constant only for a type a SUPPORTED ``implementation`` fact of aspect ``never_thrown`` says no
    library code throws or constructs, so the K02 "behaviour claim" is the fact itself, stated back. ``None``
    for any other line, a type with no such SUPPORTED fact, or a description that is not the constant."""
    from repo_presenter.readme.validation.code_path_claims import NOT_THROWN_DESCRIPTION

    match = _TYPE_TABLE_ROW.match(rows[number - 1])
    if match is None or not rows[number - 1].rstrip().endswith(f"| {NOT_THROWN_DESCRIPTION} |"):
        return None
    name = rows[number - 1].split("|")[1].strip().strip("`")
    for fact in getattr(facts, "facts", ()):
        attributes = fact.attributes or {}
        if (fact.kind == "implementation" and fact.polarity == "SUPPORTED"
                and attributes.get("aspect") == "never_thrown"
                and str(attributes.get("type") or "").rsplit(".", 1)[-1] == name.rsplit(".", 1)[-1]):
            return f"K02 verified: {fact.id} (SUPPORTED, never_thrown) states: {fact.value}"
    return None


#: ``| `Type` | Not implemented. |``: the Core API row the renderer prints for a whole-stub type
#: (``renderer._stub_marked``, ``type_description.STUB_DESCRIPTION``), and nothing else.
_STUB_ROW = re.compile(r"^\s*\|\s*`(?P<name>[^`|]+)`\s*\|\s*Not implemented\.\s*\|\s*$")
_STUB_INDEX: dict[int, tuple[Any, Any]] = {}


def stub_provenance(rows: Sequence[str], number: int, facts: Any) -> str | None:
    """The verified basis of a ``| `Type` | Not implemented. |`` row (BL-700): the renderer prints that exact
    description only for a type the maintainers' own limitation statements say only throws
    (``surface_claims.StubIndex``, read from SUPPORTED ``inherited_unit`` facts), so the K02 "behaviour claim"
    is that fact, stated back. ``None`` for any other line, a type the index does not name as a whole stub
    (a stubbed member alone is not the type), a type whose every read method body returns a value
    (``type_returns_values``: the limitation statement is then the false one, as in the Lane L correction),
    or a description that is not exactly the stub marker. A fabricated 'Not implemented.' row therefore keeps
    its flag."""
    from repo_presenter.readme.validation.code_path_claims import type_returns_values
    from repo_presenter.readme.validation.surface_claims import StubIndex

    match = _STUB_ROW.match(rows[number - 1])
    if match is None:
        return None
    name = match.group("name").strip()
    owner = name.split(".", 1)[0]
    cached = _STUB_INDEX.get(id(facts))
    if cached is None or cached[0] is not facts:
        cached = (facts, StubIndex(facts))
        _STUB_INDEX.clear()
        _STUB_INDEX[id(facts)] = cached
    fact_id = cached[1].types.get(owner)
    if fact_id is None or type_returns_values(owner, facts):
        return None
    source = next((f for f in getattr(facts, "facts", ()) if f.id == fact_id), None)
    if source is None or source.polarity != "SUPPORTED":
        return None
    return (f"K02 verified: {fact_id} (SUPPORTED, the maintainers' limitation statement) names `{owner}` "
            "as a type that only throws; the row is the renderer's fact-true 'Not implemented.'")


def class_provenance(label: str, rows: Sequence[str], number: int, facts: Any) -> str | None:
    if label.startswith("K05"):
        return count_provenance(rows, number, facts)
    if label.startswith("K10"):
        return enterprise_provenance(rows, number, facts)
    if label.startswith("K02"):
        return not_thrown_provenance(rows, number, facts) or stub_provenance(rows, number, facts)
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
    #: clearable lines whose origin cites facts (a Lane L edit's, or the opening's format facts): their ids
    cited: Mapping[int, tuple[str, ...]] = {}
    #: clearable lines that are the maintainers' kept text with the type count the renderer corrected to the
    #: facts' computation (BL-543): a flag on one is cleared only when it is about that count
    #: (``flag_is_about_count``), never for any other statement of the same paragraph
    corrected: frozenset[int] = frozenset()


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
        # a line the renderer prints from the facts a unit CITES (the opening's format sentence, BL-400) states
        # exactly those facts: they are its fact values, whatever spelling the line gives them
        known = {fact.id: fact for fact in getattr(facts, "facts", ())}
        cited = [str(f) for f in origin.get("fact_ids") or ()]
        if cited:
            if any(fid not in known for fid in cited):
                return "the line cites a fact that is not on record"
            polarities = [*polarities, *(str(known[fid].polarity) for fid in cited)]
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


def load_register(path: Path = Path("data/readme_findings.json")) -> list[Mapping[str, Any]]:
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
    # BL-400: a line in an authored region that the renderer prints from the facts a unit cites (the opening's
    # format sentence) is a deterministic stage's line too, though the structural reading calls it prose.
    if lane == "R":
        owned = owned | {
            number for number, origin in source_of.items()
            if origin and origin.get("source") == "renderer" and origin.get("fact_ids")
        }
        # BL-543: the maintainers' kept line whose count the renderer corrected
        owned = owned | {number for number, origin in source_of.items() if origin and origin.get("count_corrected")}
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
                      provenance={n: p for n, p in verified.items() if n in clearable},
                      cited={n: tuple(str(f) for f in (source_of[n] or {}).get("fact_ids") or ())
                             for n in clearable if (source_of[n] or {}).get("fact_ids")},
                      corrected=frozenset(n for n in clearable if (source_of[n] or {}).get("count_corrected")))


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

    def read(name: str) -> dict[str, Any]:
        path = bundle / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    units_name = "content_units.coherent.json" if (bundle / "content_units.coherent.json").is_file() else "content_units.json"
    return rederive_lane_r(entry, facts, read("plan.json"), read(units_name), read("dispositions.json"))


def fact_true_opening_text(unit: Mapping[str, Any], facts: Any) -> str | None:
    """The sentence the format facts state about the product when ``unit`` is the opening unit whose text IS that
    sentence (BL-220 ``recover_restated_opening`` and BL-350 ``must_correct._opening_fact_true`` write it, the
    words ``renderer._scope_statement`` prints), else ``None``. A pure function of the facts: the unit is
    recognised by recomputing the sentence, never by a flag the unit carries, so an authored opening that merely
    resembles it is not (the comparison is byte for byte)."""
    if (str(unit.get("section")), str(unit.get("slot"))) != ("opening", "opening"):
        return None
    from repo_presenter.readme.composition.authoring_retry import (
        _fact_true_opening_unit,
    )
    from repo_presenter.readme.composition.components.identity import (
        product_name_of_repository,
    )

    replaced = _fact_true_opening_unit(dict(unit), facts=facts, name=product_name_of_repository(facts.repository))
    if replaced is None or replaced["text"] != unit.get("text"):
        return None
    return str(replaced["text"])


def _count_corrected_rows(rows: Sequence[str], facts: Any, dispositions: Mapping[str, Any]) -> set[int]:
    """0-based indices of the ``rows`` that print a kept inherited unit's text with the type count
    ``renderer.correct_stated_type_counts`` corrected (the row is in the corrected unit and not in the original)."""
    from repo_presenter.readme.composition.placement import PLACED
    from repo_presenter.readme.composition.renderer import correct_stated_type_counts

    kept = {str(r.get("unit_id")) for r in dispositions.get("dispositions", []) if r.get("disposition") in PLACED}
    pairs: list[tuple[str, str]] = []
    for fact in facts.by_kind("inherited_unit"):
        if fact.id in kept and re.search(r"\d", fact.value):
            fixed = correct_stated_type_counts(fact.value, facts)
            if fixed != fact.value:
                pairs.append((" ".join(fact.value.split()), " ".join(fixed.split())))
    found: set[int] = set()
    for index, row in enumerate(rows):
        flat = " ".join(row.split())
        if len(flat) >= 12 and re.search(r"\d", flat) and any(flat in fixed and flat not in raw for raw, fixed in pairs):
            found.add(index)
    return found


def flag_is_about_count(claim: str, row: str) -> bool:
    """Whether a model flag's ``claim`` text states one of the type counts ``row`` states (the K05 reading).
    A flag on a count-corrected maintainers' line is answered by the count's provenance only when it is about
    the count; a flag on any other statement of that paragraph is not."""
    stated = {_count_value(m.group("count")) for m in _K05_COUNT.finditer(row)}
    named = {_count_value(m.group(0)) for m in re.finditer(r"\d{1,3}(?:,\d{3})+|\d+", claim)}
    return bool(stated & named)


def rederive_lane_r(
    entry: Any, facts: Any, plan: Mapping[str, Any], units: Mapping[str, Any], dispositions: Mapping[str, Any],
) -> Rederived:
    """The Lane R renderer over the given inputs, and once more with every authored unit replaced by a sentinel
    (a line identical in both is printed from facts alone). An opening unit that is the format-facts sentence
    (``fact_true_opening_text``) keeps its text in the second render: it is the renderer's own fact-true
    statement whoever wrote the unit's slot, not an authored claim (BL-400)."""
    import contextlib
    import copy
    import difflib

    from repo_presenter.extractors.platforms.registry import plugin_for
    from repo_presenter.readme.composition.renderer import render_readme

    # As recertify_bundle: a platform registers its ecosystem spec when its plugin is imported.
    with contextlib.suppress(Exception):
        plugin_for(entry.ecosystem)

    full = render_readme(entry, facts, plan, units, dispositions)
    blank = copy.deepcopy(dict(units))
    for index, unit in enumerate(blank.get("units") or []):
        if (
            isinstance(unit, dict)
            and isinstance(unit.get("text"), str)
            and fact_true_opening_text(unit, facts) is None
        ):
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
    # BL-390: a Core API row whose authored sentence the renderer REPLACED with the fact-true
    # ``NOT_THROWN_DESCRIPTION`` (``renderer._not_thrown_marked``: a type no library code throws) differs from
    # the sentinel render (the sentinel is not a "thrown when" clause, so it is kept) and was labelled
    # authored, so a model "contradiction" on it could never be cleared (Aspose.Note Python line 301, round
    # 44588173276: "Declared; not thrown by library code." against SUPPORTED never_thrown fact). Only the
    # renderer can print that constant, from that fact, so the row is the renderer's whatever the author wrote.
    from repo_presenter.readme.validation.code_path_claims import NOT_THROWN_DESCRIPTION

    rows = full.splitlines()
    for j, row in enumerate(rows):
        match = _TYPE_TABLE_ROW.match(row)
        if match and row.rstrip().endswith(f"| {NOT_THROWN_DESCRIPTION} |"):
            origins[j] = {"source": "renderer"}
    # BL-400: the opening unit that IS the format-facts sentence is printed from the format facts it cites
    for unit in units.get("units") or []:
        if not isinstance(unit, Mapping):
            continue
        sentence = fact_true_opening_text(unit, facts)
        at = [j for j, row in enumerate(rows) if sentence and row.strip() == sentence]
        if len(at) == 1 and origins[at[0]].get("source") == "renderer":
            origins[at[0]] = {"source": "renderer", "fact_ids": tuple(str(f) for f in unit.get("fact_ids") or ())}
    # BL-543: a kept maintainers' line whose type count the renderer corrected to the facts' computation
    # (``renderer.correct_stated_type_counts``) is a deterministic stage's correction of text the maintainers
    # wrote, not authored prose. The line is recognised by recomputing the correction over each kept inherited
    # unit and finding the printed row in the corrected text and not in the original; the clearance still
    # needs the count to verify (``count_provenance``) and the flag to be about the count.
    for j in _count_corrected_rows(full.splitlines(), facts, dispositions):
        origins[j] = {"source": "renderer", "count_corrected": True}
    # BL-542: the "No required third-party package dependencies; in `pom.xml`, ..." line is the
    # ``dependency:none`` fact's own evidence, printed word for word, and the renderer prints it only when no
    # required dependency is on record; so the line states exactly that SUPPORTED fact, and its origin cites
    # it (PSD Java 83, flagged in 4 of 4 audit samples because "provided" and "optional" occur in no fact
    # VALUE, though the fact's evidence says every declared dependency is test, provided or optional). Only
    # that exact line qualifies: any other wording stays unrecognised and keeps its flag.
    from repo_presenter.readme.composition.renderer import no_required_dependencies_line

    marker = next((f for f in facts.facts if f.id == "dependency:none"), None)
    clause = no_required_dependencies_line(marker) if marker is not None else None
    required = [
        f for f in facts.facts
        if f.kind == "dependency" and f.polarity == "SUPPORTED" and f.id != "dependency:none"
        and not f.id.startswith(("dependency:optional.", "dependency:development."))
    ]
    if clause is not None and not required:
        for j, row in enumerate(rows):
            if row.strip() == clause and origins[j].get("source") == "renderer":
                origins[j] = {"source": "renderer", "fact_ids": ("dependency:none",)}
    # BL-591: the "- Requires Python 3.10 or later." line under "Native and System Requirements" is the
    # ``package:python_requires`` fact's floor in aspose.org's words (``renderer.python_floor_sentence``), printed
    # only for a SUPPORTED floor of that exact shape; its origin cites the fact (Page Python line 115, flagged as an
    # "omission" because ">=3.10" is the fact VALUE and the line says "3.10 or later"). Any other wording keeps its flag.
    from repo_presenter.readme.composition.renderer import _FLOOR, PYTHON_FLOOR_FACT_ID, python_floor_sentence

    floor_fact = next((f for f in facts.facts if f.id == PYTHON_FLOOR_FACT_ID and f.polarity == "SUPPORTED"), None)
    floor = _FLOOR.fullmatch(str(floor_fact.value).strip()) if floor_fact is not None else None
    if floor is not None:
        printed = f"- {python_floor_sentence(floor.group(1))}"
        for j, row in enumerate(rows):
            if row.strip() == printed and origins[j].get("source") == "renderer":
                origins[j] = {"source": "renderer", "fact_ids": (PYTHON_FLOOR_FACT_ID,)}
    return Rederived(full, tuple(origins))


def lane_r_derivation(
    readme: str,
    *,
    entry: Any,
    facts: Any,
    plan: Mapping[str, Any],
    units: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    ask: Collection[int],
    register_path: Path | None = None,
) -> Derivation | None:
    """The derivation of a Lane R candidate the pipeline has just rendered: which of the lines in ``ask`` the
    renderer printed from SUPPORTED facts (``derivation`` over ``rederive_lane_r`` of the very inputs that
    produced ``readme``), zero provider calls. ``None`` -- nothing is cleared -- when anything cannot be
    established: the findings register is missing or unreadable (a missing register would silently drop the
    refutations it holds), or the renderer fails over these inputs."""
    from repo_presenter.readme_findings import DEFAULT_FINDINGS_PATH

    path = register_path if register_path is not None else DEFAULT_FINDINGS_PATH
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        register = list(document.get("findings") or [])
        rederived = rederive_lane_r(entry, facts, plan, units, dispositions)
        return derivation(
            "R", readme, facts, rederived,
            repository=str(getattr(entry, "repository", "") or facts.repository),
            register=register, ask=set(ask),
        )
    except Exception:  # noqa: BLE001 -- no re-derivation: a flag is never cleared on a guess
        return None
