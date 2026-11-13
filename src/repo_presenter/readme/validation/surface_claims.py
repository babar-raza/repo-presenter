"""BC-14, rules (h)-(m): mechanically checkable statements about the product's own surface.

Added 2026-11-06 after ``docs/investigations/2026-11-06-unsupported-claim-class-audit.md`` read every
registered real-defect case of reviewer-calibration iteration 5 against the upstream source: 20 of
the 23 false claims (class A) are decidable from the facts alone, and nothing deterministic judged
them, and four generator-authored statements (class D) printed a count or a verification the
pipeline never computed or made. Every rule here is a statement a SUPPORTED fact positively
contradicts, or one the pipeline itself must never author; like rules (a)-(g) in ``claims.py``, a
rule with no fact to hold a statement to is silent.

(h) Type counts. "N public types" (or "N public classes", "N classes and enumerations") in a
    sentence about the public surface equals the facts' count of type-level ``public_symbol``
    facts (class and enum), by either of the two ways the renderer itself counts them.
(i) API-table names. A row of an API type table (a table whose first cells are mostly verified
    public types) names a type no ``public_symbol`` fact states: not a value segment, not a name a
    public signature or docstring uses. The ``public_symbol`` facts are the public surface, so a
    type they do not hold does not exist or is not exported.
(j) Stubs sold as working. A SUPPORTED fact (the maintainers' limitation statement) says a type's
    or a member's body only throws (``NotImplementedError``/``NotImplementedException``,
    ``UnsupportedOperation``/``UnsupportedFeature``/``NotSupported``, "not implemented", "not
    functional"); a table row or sentence that names that type and describes the stubbed
    capability affirmatively, with no limitation cue of its own, contradicts it.
(k) Failing examples printed. An example the facts record CONTRADICTED, printed in full in a
    fence, where the receipt's failure is the API's own (``AttributeError``/``TypeError``) and not
    the verification environment's (an import guard, a build that would not run, a missing
    fixture, an extraction artifact).
(l) Stated package name. A code span the sentence calls the package's (or distribution's) name is
    the ``package:name`` identity; a truncation or near-miss of it (``aspose-font`` for
    ``aspose-font-foss``) that no SUPPORTED fact states verbatim contradicts it.
(m) Uncomputed structure and verification narrative (generator guard). A sentence the pipeline
    wrote (not quoted from the maintainers' README, i.e. from no SUPPORTED ``inherited_unit``) may
    not count modules/packages/namespaces against the facts' module count, and -- TC-017b work
    item 4, now its own finding function (``_verification_findings``), not part of (m) itself --
    may not narrate a verification ("everything below was exercised ... and confirmed", "fully
    tested", "real outputs ... fixture-backed") UNLESS every example fact in the document
    genuinely, fully passed (``_fully_verified``: SUPPORTED at confidence 1.0 -- post-TC-016, a
    TIMED_OUT receipt is UNRESOLVED and never counts). Quoted maintainer text is the
    reconciliation stage's, judged by (h)-(l) only.

(n) Member kinds and accessors (BL-063, K03). A "the methods A, B" / "A and B properties" /
    "the constructors ..." list names each member by a kind its ``public_symbol`` fact allows
    (``member_kind``; for older facts only what they prove: a signature without a parameter list is
    no method, a member named after its type is its constructor); a "classes" list names no struct
    (.NET), enum or interface; a member bullet or row under a type's heading says "Gets or sets"
    only for a settable member; read-only properties are not offered "for direct manipulation".
(o) Member attribution (BL-064, K04). A kind list attached to one type names that type's own (or
    inherited) members; an API-table row's code spans name members of its own type, not of a
    same-named namesake, and no name the surface does not state; "`X`-derived `Y`" holds only when
    ``Y`` derives from ``X``.
(h) also holds a count the sentence says "is listed below" to the table rows that follow it
    (BL-065, K05).

TC-017b (2026-11-07) also adds: a line-provenance classifier shared with every check here
(``readme/validation/line_provenance.py``, replacing this module's own former ``_Origin`` copy of
the same logic), and TC-017a's independent export-surface probes (``acceptance/probes/``) wired
in as a second, non-same-origin signal for (h) and (i) -- a probe's definite ``False``/mismatch is
now itself a finding even when the facts alone say a claim is fine, closing the common-mode gap
where an extractor bug could both write a wrong fact and fail to flag the claim it then wrongly
supports. A probe answering ``None`` never overturns a fact-backed pass, and never by itself
rejects a claim either: it is a second signal, never a replacement for the facts.

Each finding carries the line span it is about and, when the offending text is a SUPPORTED
``inherited_unit`` kept verbatim, that unit's id: ``provenance.claim_failures`` routes such a
finding to RECONCILING with the unit id (keeping contradicted maintainer text is a disposition
defect, not a composition one) and every other to COMPOSING with its section.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from pathlib import Path

from repo_presenter.core.facts import Fact, FactKind, FactsDocument
from repo_presenter.readme.validation import line_provenance
from repo_presenter.readme.validation.claims import (
    ClaimFinding,
    _fact,
    _Line,
    _paragraphs,
    _pep503,
    _sentence_spans,
    _stem,
)

TYPE_KINDS = ("class", "enum")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SEGMENTS = re.compile(r"[.:/\\]+")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")


def _plain(text: str) -> str:
    """Text as compared across a README and a fact: no code ticks, plain hyphens, single spaces."""
    return " ".join(text.replace("`", "").replace("‑", "-").replace("–", "-").split())


def _supported(facts: FactsDocument, kind: FactKind) -> list[Fact]:
    return [fact for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]


class _Origin:
    """Which README text is the maintainers' own: quoted inside a SUPPORTED ``inherited_unit``.

    TC-017b work item 1: this used to be the only place that notion lived; it now delegates to
    ``readme/validation/line_provenance.py`` so every other module (and this card's own new
    checks) shares exactly one definition of "inherited" rather than a second, parallel one.
    """

    def __init__(self, facts: FactsDocument) -> None:
        self._facts = facts

    def unit(self, text: str) -> str | None:
        """The inherited unit that quotes ``text`` verbatim, or ``None`` (pipeline-authored)."""
        return line_provenance.unit_for(text, self._facts)


def _ecosystem(facts: FactsDocument) -> str | None:
    """The repository's ecosystem, as the ``identity:ecosystem`` fact already records it
    (``readme/evidence/facts/extract.py`` writes ``fact_id("identity", "ecosystem")`` with the
    registry entry's own ``ecosystem`` string as its value) -- never re-derived here."""
    fact = _fact(facts, "identity:ecosystem")
    return fact.value if fact is not None else None


class _Probes:
    """TC-017b work item 3: TC-017a's independent export-surface probes, as a second,
    non-same-origin signal for the mechanical checks below.

    Bound to one repository's checked-out source tree (``probe_root``) and ecosystem, both
    resolved once per call to ``surface_findings``/``claim_findings``. Every method is three-
    valued (``True``/``False``/``None``), exactly as the underlying probe is: ``None`` means the
    probe could not tell (no ``probe_root`` was supplied, the ecosystem has no probe module, or
    the probe itself could not determine an answer) and is never coerced to ``True`` or ``False``
    by anything in this module -- the single most important contract property the probes package
    itself states, carried through here unchanged.
    """

    def __init__(self, facts: FactsDocument, probe_root: str | Path | None) -> None:
        self._root = Path(probe_root) if probe_root is not None else None
        self.ecosystem = _ecosystem(facts) if self._root is not None else None
        self._module = None
        if self.ecosystem is not None:
            from repo_presenter.acceptance import probes

            self._module = probes.ECOSYSTEMS.get(self.ecosystem)

    def __bool__(self) -> bool:
        return self._module is not None

    def count(self, kind: str) -> int | None:
        if self._module is None or self._root is None:
            return None
        return self._module.count(self._root, kind)

    def exists(self, qualified_name: str) -> bool | None:
        if self._module is None or self._root is None:
            return None
        return self._module.exists(self._root, qualified_name)

    def exported(self, qualified_name: str) -> bool | None:
        if self._module is None or self._root is None:
            return None
        return self._module.exported(self._root, qualified_name)

    def type_count(self) -> int | None:
        """The probe's own total of TYPE_KINDS (class + enum), or ``None`` when either kind's
        count is itself unknown -- a partial total is not a count anyone can hold a claim to."""
        counts = [self.count(kind) for kind in TYPE_KINDS]
        return None if any(value is None for value in counts) else sum(counts)  # type: ignore[misc]


def _finding(
    origin: _Origin, line: int, text: str, detail: str, *, last: int | None = None
) -> ClaimFinding:
    return ClaimFinding(line, "COMPOSING", detail, last=last, unit=origin.unit(text))


def _sentences(lines: list[_Line]) -> Iterable[tuple[str, int, int]]:
    """(sentence, first line, last line) for every prose sentence, wrapped lines joined."""
    for paragraph in _paragraphs(lines):
        for begin, end in _sentence_spans(paragraph.text):
            sentence = paragraph.text[begin:end]
            if sentence.strip():
                yield (
                    sentence,
                    paragraph.line_at(begin),
                    paragraph.line_at(max(begin, end - 1)),
                )


# --- (h) type counts -------------------------------------------------------------------------

_TYPE_COUNT = re.compile(
    r"""(?ix)
    (?<![\w.,])(?P<count>\d{1,3}(?:,\d{3})+|\d+)\s+
    (?P<qualifiers>(?:(?:public|verified|exported|documented|top-level|distinct)\s+){0,3})
    (?:API\s+)?
    (?P<noun>types|classes(?:\s+and\s+(?:enumerations|enums))?)\b
    """
)
_PUBLIC_CONTEXT = re.compile(r"(?i)\bpublic\s+(?:API\s+)?(?:surface|API)\b")
_PUBLIC_QUALIFIER = re.compile(r"(?i)\b(?:public|verified|exported)\b")


# BL-065 (K05, 2026-11-12 register row, Aspose.Cells-FOSS-for-Cpp): "The full public surface -- 195
# public types -- is listed below" over tables of 157 rows. A count the sentence says is listed is
# also held to the rows that follow it, up to the next second-level heading.
_LISTED_HERE = re.compile(
    r"(?i)\b(?:(?:is|are)\s+)?listed\s+(?:below|here|in\s+the\s+(?:table|tables)\s+below)\b"
    r"|\bas\s+follows\b"
)
_SECTION_HEADING = re.compile(r"^\s*#{1,2}\s")


def _rows_listed_after(lines: list[_Line], last: int) -> int:
    """The type-table rows (`` | `Name` | ``) after line ``last`` up to the next level-1/2
    heading; header and separator rows are not counted."""
    count = 0
    for line in lines:
        if line.index <= last or line.in_fence:
            continue
        if _SECTION_HEADING.match(line.text):
            break
        if _TABLE_ROW.match(line.text):
            count += 1
    return count


def type_counts(facts: FactsDocument) -> tuple[int, int]:
    """(types, classes) as the facts count them: SUPPORTED class and enum ``public_symbol`` facts,
    and the classes among them. ``readme/validation/structure.py`` counts by ``symbol_kind``; the
    renderer's reference sentence counts by the evidence locator (``"; class;"``)."""
    symbols = _supported(facts, "public_symbol")
    kinds = [(fact.attributes or {}).get("symbol_kind", "") for fact in symbols]
    return sum(kind in TYPE_KINDS for kind in kinds), sum(
        kind == "class" for kind in kinds
    )


def _evidence_type_count(facts: FactsDocument) -> int:
    return sum(
        1
        for fact in _supported(facts, "public_symbol")
        if fact.evidence
        and any(f"; {kind};" in (fact.evidence[0].detail or "") for kind in TYPE_KINDS)
    )


def _count_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin, probes: _Probes | None = None
) -> list[ClaimFinding]:
    types, classes = type_counts(facts)
    if types == 0:
        return []
    allowed_types = {types, _evidence_type_count(facts)}
    probe_types = probes.type_count() if probes is not None else None
    probe_classes = probes.count("class") if probes is not None else None
    findings: list[ClaimFinding] = []
    for sentence, first, last in _sentences(lines):
        plain = sentence.replace("`", "")
        for match in _TYPE_COUNT.finditer(plain):
            if not (
                _PUBLIC_QUALIFIER.search(match.group("qualifiers"))
                or _PUBLIC_CONTEXT.search(plain)
            ):
                continue
            stated = int(match.group("count").replace(",", ""))
            noun = match.group("noun").lower()
            allowed = allowed_types | ({classes} if noun == "classes" else set())
            probe_value = probe_classes if noun == "classes" else probe_types
            if _LISTED_HERE.search(plain):
                listed = _rows_listed_after(lines, last)
                if listed and listed < stated:
                    # Worded without the stated number, on purpose: a Lane L count correction
                    # (243 -> 303) leaves this pre-existing defect the same finding, a residual
                    # (R21), rather than one the edit introduced.
                    findings.append(
                        _finding(
                            origin,
                            first,
                            sentence,
                            "the README says its count of public types is listed in what follows, "
                            f"but the table rows that follow list only {listed}; state the count "
                            "of what is listed, or list every type",
                            last=last,
                        )
                    )
            if stated in allowed:
                # TC-017b work item 3: the facts call this stated count fine, but TC-017a's probe
                # is a second, non-same-origin signal -- an extractor bug that wrote a wrong fact
                # cannot also pass this check, the way it could pass the fact-only check alone.
                # A probe answer of None never overturns a fact-backed pass (open-world: "could
                # not help" is not a contradiction).
                if probe_value is not None and probe_value != stated:
                    findings.append(
                        _finding(
                            origin,
                            first,
                            sentence,
                            f"the README states {match.group(0).strip()!r} "
                            f"({_plain(sentence)!r}); the facts agree, but the independent "
                            f"{probes.ecosystem} export-surface probe counts {probe_value}, not "
                            f"{stated} -- the facts may themselves be wrong",
                            last=last,
                        )
                    )
                continue
            # Every type fact names a defining location, so a count BELOW the facts' is refuted
            # outright. A count above it can be the maintainers counting kinds the extractor does
            # not record (Aspose.PDF FOSS for .NET's live README: 983 = 969 class/enum facts + 14
            # public delegates): above the facts, only the pipeline's own sentences are held to
            # them, never quoted maintainer text.
            if stated > max(allowed_types) and origin.unit(sentence) is not None:
                if probe_value is not None and probe_value != stated:
                    findings.append(
                        _finding(
                            origin,
                            first,
                            sentence,
                            f"the README states {match.group(0).strip()!r} "
                            f"({_plain(sentence)!r}); the facts cannot refute it, but the "
                            f"independent {probes.ecosystem} export-surface probe counts "
                            f"{probe_value}, not {stated}",
                            last=last,
                        )
                    )
                continue
            findings.append(
                _finding(
                    origin,
                    first,
                    sentence,
                    f"the README states {match.group(0).strip()!r} ({_plain(sentence)!r}), but the "
                    f"facts record {types} public types ({classes} classes); state the computed "
                    "count or none",
                    last=last,
                )
            )
    return findings


# --- (i) API-table names ---------------------------------------------------------------------

_TABLE_ROW = re.compile(r"^\s*\|\s*`(?P<name>[^`|]+)`\s*\|")
_TABLE_MIN_ROWS = 3
# A row that says its type is one of the kinds the extractor does not record as a public_symbol
# (a .NET delegate, a callback or event-handler type, a type alias) is not held to the symbol
# facts: their absence there is a facts-coverage gap, not evidence the type is not public
# (Aspose.PDF FOSS for .NET's live README: seven public delegates, recorded by no fact).
_UNEXTRACTED_KIND = re.compile(
    r"(?i)\b(?:delegates?|callbacks?|event\s+handlers?|type\s+alias(?:es)?|typedefs?"
    r"|function\s+pointers?)\b"
)
# The share of a table's first cells that must be verified public types for it to be read as an
# API type table: tuned on the iteration-4 corpus, where every API table the reference outputs
# print is at least 0.84 types and the shortest the audit names is 5 of 6.
_TABLE_TYPE_SHARE = 0.6


def _surface_names(
    facts: FactsDocument,
) -> tuple[set[str], set[str], dict[str, str]]:
    """(every name the public surface uses, the type names, {type name: its fact's full dotted
    value}): ``public_symbol``, ``enum_member`` and ``import_path`` value segments, plus the
    identifiers public signatures and docstrings use (a return type, a base class). Never an
    ``inherited_unit``: the README's own text is what is being judged.

    The third element (TC-017b work item 3) is the fully-qualified name a type's own short name
    maps to -- a ``public_symbol`` fact's value is already the dotted path (``_row_name``/table
    cells only ever carry the short name), and TC-017a's probes need that full path, not a bare
    short name that could resolve to the wrong symbol or nothing at all.
    """
    known: set[str] = set()
    types: set[str] = set()
    qualified: dict[str, str] = {}
    for fact in facts.facts:
        if fact.polarity == "CONTRADICTED" or fact.kind not in (
            "public_symbol",
            "enum_member",
            "import_path",
        ):
            continue
        parts = [part for part in _SEGMENTS.split(fact.value) if part]
        known.update(parts)
        attributes = fact.attributes or {}
        for key in ("signature", "docstring", "defined_at", "public_paths"):
            known.update(_IDENTIFIER.findall(attributes.get(key, "")))
        if parts and attributes.get("symbol_kind") in TYPE_KINDS:
            types.add(parts[-1])
            qualified.setdefault(parts[-1], fact.value)
    return known, types, qualified


def _row_name(cell: str) -> str:
    """The type a first cell names: generic arguments, a call and a ``-Namespace`` disambiguator
    (``Rectangle-Aspose_Pdf``) removed."""
    name = re.split(r"[<(\s]", cell.strip(), maxsplit=1)[0]
    return name


def _consecutive_table_row_groups(text: str) -> list[list[tuple[str, str]]]:
    """``text`` split into separate runs of consecutive ``_TABLE_ROW`` lines -- one maintainers'
    table never bleeds into the next, non-adjacent one. A non-matching line (blank, prose, a
    different heading's table) ends the current run; ``_table_findings`` already groups this way
    for the VALIDATION finding, and this is that same grouping reused for the EDIT/restore
    reading, so the two can never disagree about which rows belong to which table."""
    groups: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = _TABLE_ROW.match(line)
        if match is not None:
            current.append((_row_name(match.group("name")), line))
            continue
        if current:
            groups.append(current)
        current = []
    if current:
        groups.append(current)
    return groups


def absent_type_rows(text: str, facts: FactsDocument) -> list[str]:
    """The rows of a maintainers' API TYPE table that name something the public surface lacks:
    the rows BC-14 rule (i) would flag. Empty unless the table reads as a type table (at least
    ``_TABLE_MIN_ROWS`` rows, at least ``_TABLE_TYPE_SHARE`` of whose first cells are verified public
    types). A delegate/callback row is never absent (a kind no ``public_symbol`` fact records).

    Judged per TABLE (``_consecutive_table_row_groups``), never pooled across every table in
    ``text``: a second, unrelated table (a short "Traits" table, say) sharing the same call would
    otherwise dilute the first table's own type share below ``_TABLE_TYPE_SHARE`` and silently
    stop any row of it being read as absent -- measured passing a whole multi-table README (Lane
    L's ``absent_type_row`` detector) where the isolated "Enumerations" table alone reads as a
    type table (len 30, type share high) but the same text pooled with the document's other
    tables did not."""
    known, types, _qualified = _surface_names(facts)
    if not types:
        return []

    def is_type(name: str) -> bool:
        return name in types or name.split("-", 1)[0] in types

    dropped: list[str] = []
    for rows in _consecutive_table_row_groups(text):
        if len(rows) < _TABLE_MIN_ROWS:
            continue
        if sum(is_type(name) for name, _ in rows) / len(rows) < _TABLE_TYPE_SHARE:
            continue
        dropped.extend(
            line
            for name, line in rows
            if name
            and not (
                name in known
                or name.split("-", 1)[0] in known
                or _SEGMENTS.split(name)[-1] in known
            )
            and not _UNEXTRACTED_KIND.search(line.split("|", 2)[-1])
        )
    return dropped


def without_absent_type_rows(text: str, facts: FactsDocument) -> str:
    """``text`` with the rows ``absent_type_rows`` names removed, every other line (header,
    separator, remaining rows, surrounding prose) exactly as written. The ONE printable form of a
    kept maintainers' type table: the renderer prints it, and BC-05 / the independent reviewer's
    ``disposition_coverage`` judge "printed" against it, so the three can never disagree. A row
    dropped here is dropped on evidence -- the facts hold no public type of that name (BC-14)."""
    drop = set(absent_type_rows(text, facts))
    if not drop:
        return text
    return "\n".join(line for line in text.split("\n") if line.rstrip("\r") not in drop)


def stub_rows(text: str, facts: FactsDocument) -> list[str]:
    """The table rows of ``text`` that BC-14 rule (j) reads as a stub described as working: the row's
    subject is a type or member a SUPPORTED maintainers' limitation statement says only throws, and
    the row's description sells it as working (Aspose.3D-FOSS-for-Python's API table: "`FbxExporter`
    | FbxExporter.save saves the given Scene ...", while the maintainers' own Scope and Limitations
    list says ``FbxExporter.save()`` raises ``NotImplementedError``). The same rule, run on the same
    text, so the filter and the check can never disagree."""
    from repo_presenter.readme.validation.claims import _lines

    rows = text.splitlines()
    flagged: list[str] = []
    for finding in _stub_findings(_lines(text), facts, _Origin(facts)):
        last = finding.last if finding.last is not None else finding.line
        for index in range(finding.line, last + 1):
            if 0 <= index < len(rows) and rows[index].lstrip().startswith("|"):
                flagged.append(rows[index])
    return flagged


def without_stub_rows(text: str, facts: FactsDocument) -> str:
    """``text`` with the rows ``stub_rows`` names removed, every other line exactly as written. A
    row dropped here is dropped on evidence (R14 rule, docs/DECISION_LOG.md 2026-11-13): the
    maintainers' own SUPPORTED limitation statement says its subject only throws, so printing the
    row verbatim states a falsehood BC-14 refuses; the type itself stays in the renderer's
    verified API table, which describes a stub as such."""
    drop = set(stub_rows(text, facts))
    if not drop:
        return text
    return "\n".join(line for line in text.split("\n") if line.rstrip("\r") not in drop)


def kept_table_form(text: str, facts: FactsDocument) -> str:
    """The ONE printable form of a kept maintainers' table: absent-type rows removed (BC-14 rule
    (i)), rows selling a maintainer-stated stub as working removed (BC-14 rule (j)), and any unsafe
    HTML element it names in prose shown in a code span (BC-06). The renderer, BC-05, the
    independent reviewer and the restore guard all judge "printed" against this form."""
    from repo_presenter.readme.validation.links import defang_unsafe_html

    return defang_unsafe_html(without_stub_rows(without_absent_type_rows(text, facts), facts))


#: Kept maintainers' unit kinds whose prose BC-12 judges and ``kept_unit_form`` corrects. A heading
#: is not one: reconciliation and the shell own heading text, and live_readme_loss matches a live
#: heading by its text, so rewriting a kept heading would turn it into a lost one.
_NAME_CORRECTED_KINDS = (".paragraph", ".list", ".blockquote", ".table")
#: What a name correction must never touch beyond the fenced blocks and inline code spans the
#: matcher already leaves alone: a link destination and a bare URL.
_NAME_PROTECTED = re.compile(r"\]\([^)\n]*\)|https?://[^\s)>\]]+")


def canonical_name_form(text: str, facts: FactsDocument) -> str:
    """``text`` with each separator, case or suffix variant of the product name that stands for it
    in running prose spelled as the canonical name (``Aspose.PDF FOSS`` -> ``Aspose.PDF FOSS for
    Cpp``): BC-12's own remedy applied deterministically, through the SAME matcher
    (``composition.components.identity.canonicalise_name_variants``) the authored prose is held to.
    Fenced blocks, inline code spans, link destinations and bare URLs are left byte for byte; a text
    that names the product in no variant is returned unchanged."""
    from repo_presenter.readme.composition.components.identity import (
        canonicalise_name_variants,
        product_name_of_repository,
    )

    canonical = product_name_of_repository(facts.repository)
    return canonicalise_name_variants(text, canonical, protect=_NAME_PROTECTED)


#: An inline markdown link ``[label](destination "optional title")`` that is not an image.
_INLINE_LINK = re.compile(
    r"(?<!!)\[(?P<label>(?:[^\[\]\n]|\[[^\[\]\n]*\])*)\]"
    r"\((?P<href>[^()\s]+(?:\([^()\s]*\)[^()\s]*)?)(?:\s+\"[^\"\n]*\")?\)"
)


def without_contradicted_links(text: str, facts: FactsDocument) -> str:
    """``text`` with every inline link whose destination a ``link_target`` fact records as
    CONTRADICTED (the target answered 404/410: it is gone) printed as its label alone; every other
    character exactly as written.

    A dead target is the only defect such a kept unit has, and printing it fails BC-06 ("is
    CONTRADICTED"): S4 used to fold the whole unit to ``VERIFIED_REWRITE`` for it, and the zero-call
    restore rolled the unit back for the BC-06 it brought, so the maintainers' section it carries was
    lost (R2/BC-17). Measured: Aspose.OMR-FOSS-for-Python, hosted run 43430687401 -- the README links
    its own files through a ``github.com/omr-python-for-foss/omr-python-for-foss/blob/main/...`` repository
    that does not exist, inside the units holding 'Developing in VS Code', 'Two ways to author a
    form', 'How recognition works', 'Known limitations / deviations' and 'Examples and API'. The
    label (here the file path in a code span) is the maintainers' own words and stays; only the
    dead destination goes, on the cited fact (R14: the CONTRADICTED ``link_target`` is the evidence,
    and BC-17 already exempts a contradicted link from its losses)."""
    dead = {
        str(fact.value)
        for fact in facts.by_kind("link_target")
        if fact.polarity == "CONTRADICTED" and fact.value
    }
    if not dead or "](" not in text:
        return text
    return _INLINE_LINK.sub(
        lambda match: match.group("label") if match.group("href") in dead else match.group(0), text
    )


def kept_unit_form(
    unit_id: str, text: str, facts: FactsDocument, false_quotes: Collection[str] = ()
) -> str:
    """The ONE printable form of a kept maintainers' unit, whatever its kind: a table without the
    rows naming absent types and with unsafe HTML in code spans (``kept_table_form``), and any
    paragraph, list, blockquote or table with the product named as BC-12 requires
    (``canonical_name_form``). The renderer, BC-05, the independent reviewer and the restore guard
    all judge "printed" against this form, so a restore of the maintainers' own wording no longer
    fails BC-12 on a short name (measured: PDF Cpp, Slides Cpp, Cells Cpp, Cells Go, 2026-11-11)."""
    if false_quotes and unit_id.endswith((".code_block", ".paragraph")):
        # A unit kept while its disposition cites an OPEN findings-register row prints without
        # exactly what that row confirms false (must_correct.withheld_form): a code block without
        # those lines, a paragraph without those sentences; everything else is kept as written.
        from repo_presenter.readme.validation.must_correct import withheld_form

        text = withheld_form(unit_id, text, false_quotes)
        if unit_id.endswith(".code_block"):
            return text
    if unit_id.endswith(".table"):
        text = kept_table_form(text, facts)
    if not unit_id.endswith(".code_block"):
        # A dead link target is printed as its label (``without_contradicted_links``); fenced code
        # carries no rendered link and is never edited.
        text = without_contradicted_links(text, facts)
    if unit_id.endswith(_NAME_CORRECTED_KINDS):
        text = canonical_name_form(text, facts)
    # The renderer corrects a stated "N public types" the facts contradict over the WHOLE README after
    # assembly (``renderer.correct_stated_type_counts``), so what a kept unit prints carries the facts'
    # number, never the maintainers' stale one. Judged against the uncorrected text, BC-05 said "placed
    # in scope_limitations but the candidate does not render it there" and the reviewer "kept but not
    # printed" for a paragraph that WAS printed, one digit apart (Cells Cpp 041.paragraph: "197" vs the
    # computed 195). Idempotent with the renderer's own pass; prose only, fenced code is never edited.
    from repo_presenter.readme.composition.renderer import correct_stated_type_counts

    return correct_stated_type_counts(text, facts)


def _table_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin, probes: _Probes | None = None
) -> list[ClaimFinding]:
    known, types, qualified = _surface_names(facts)
    if not types:
        return []
    tables: list[list[tuple[int, str, str]]] = []
    current: list[tuple[int, str, str]] = []
    for line in lines:
        match = None if line.in_fence else _TABLE_ROW.match(line.text)
        if match is not None:
            current.append((line.index, _row_name(match.group("name")), line.text))
            continue
        if current:
            tables.append(current)
        current = []
    if current:
        tables.append(current)

    def is_type(name: str) -> bool:
        return name in types or name.split("-", 1)[0] in types

    def is_known(name: str) -> bool:
        return (
            name in known
            or name.split("-", 1)[0] in known
            or (_SEGMENTS.split(name)[-1] in known)
        )

    findings: list[ClaimFinding] = []
    for table in tables:
        if len(table) < _TABLE_MIN_ROWS:
            continue
        if sum(is_type(name) for _, name, _ in table) / len(table) < _TABLE_TYPE_SHARE:
            continue
        for index, name, text in table:
            if not name:
                continue
            if not is_known(name):
                if _UNEXTRACTED_KIND.search(text.split("|", 2)[-1]):
                    continue  # a delegate/callback type: a kind no public_symbol fact records
                findings.append(
                    _finding(
                        origin,
                        index,
                        text,
                        f"the API table lists `{name}`, but no public_symbol fact states it (it "
                        "is not a type of the public surface: absent or not exported)",
                    )
                )
                continue
            # TC-017b work item 3: the facts call this name known -- the common-mode gap the
            # card exists to close is exactly here, where a wrong extractor fact would otherwise
            # go unchallenged. TC-017a's probe is a second, non-same-origin signal: only a
            # definite False (the probe itself finds the name not exported) is a finding; None
            # ("could not tell") never overturns the fact-backed pass.
            if probes is not None and is_type(name):
                qualified_name = qualified.get(name, name)
                if probes.exported(qualified_name) is False:
                    findings.append(
                        _finding(
                            origin,
                            index,
                            text,
                            f"the API table lists `{name}`, and a public_symbol fact calls it "
                            f"known, but the independent {probes.ecosystem} export-surface probe "
                            f"says `{qualified_name}` is not exported -- the facts may themselves "
                            "be wrong",
                        )
                    )
    return findings


# --- (n) member kinds and (o) member attribution (BL-063 K03, BL-064 K04) ---------------------
#
# 2026-11-13 Lane R false-claim review (docs/investigations/2026-11-13-lane-r-false-claim-review.md):
# eight API rows called a property, field or constant a "method" (Email .NET's MapiMessage
# ``AttachMethodByValue`` is a ``const int``), a static factory a "constructor" (``CfbDocument.
# FromFile``), methods "properties" (``DirectoryEntry.IsRoot``), a struct and an enum "classes"
# (Cells .NET ``Color``/``FillPattern``) and printed "Gets or sets" for a property whose setter is
# private (Cells .NET ``Style.Font``/``Borders``, Style.cs:68,73), or sold read-only properties "for
# direct manipulation" (3D Python ``GlobalTransform``). Eight more named members a type lacks
# (``Style`` "properties such as Color, FillPattern and Border"), bound one type's members to its
# same-named namesake (3D .NET GLTF ``Property`` "exposes GetExtra/SetExtra"), named a member no
# type has (``Tangents``) or a base the type does not derive from ("`Mesh`-derived `Entity`").
# Every one is decidable from the ``public_symbol`` facts: their ``member_kind``/``settable``/
# ``type_kind``/``bases`` attributes (extractor 7, python_surface) and, for facts sealed before
# those existed, only what the older facts already prove (a member whose signature has no
# parameter list is no method; a member named after its type is its constructor; a type's
# ``declaration`` names its kind). A member the facts cannot classify is never judged.

#: The README's word for a kind of member -> the kinds it may truthfully name. "nonmethod" is the
#: older facts' reading of a member with a signature but no parameter list (a property, field or
#: constant: which one the facts did not record).
_CLAIMED_MEMBER_KINDS: dict[str, frozenset[str]] = {
    "method": frozenset({"method", "constructor"}),
    "constructor": frozenset({"constructor"}),
    "property": frozenset({"property", "field", "constant", "nonmethod"}),
    "field": frozenset({"property", "field", "constant", "nonmethod"}),
    "constant": frozenset({"field", "constant", "nonmethod", "enum_value"}),
    "member": frozenset({"method", "constructor", "property", "field", "constant", "nonmethod"}),
}
#: The README's word for a kind of type -> the declared kinds it may truthfully name, per
#: ecosystem family: a C++ ``struct`` is a class with public default access, a C# ``struct`` is a
#: value type and not a class.
_CLAIMED_TYPE_KINDS: dict[str, frozenset[str]] = {
    "class": frozenset({"class", "record"}),
    "struct": frozenset({"struct"}),
    "enum": frozenset({"enum"}),
    "interface": frozenset({"interface", "trait"}),
}
_KIND_WORDS = {
    "methods": "method", "method": "method",
    "constructors": "constructor", "constructor": "constructor",
    "properties": "property", "property": "property",
    "fields": "field", "field": "field",
    "constants": "constant", "constant": "constant",
    "members": "member",
    "classes": "class", "class": "class",
    "structs": "struct", "struct": "struct", "structures": "struct",
    "enums": "enum", "enumerations": "enum",
    "interfaces": "interface", "interface": "interface",
}
_KIND_ALTERNATION = "|".join(sorted(_KIND_WORDS, key=len, reverse=True))
_LIST_ITEM = r"`?[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:\(\))?`?"
_LIST_SEP = r"(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+)"
_LIST = rf"{_LIST_ITEM}(?:{_LIST_SEP}{_LIST_ITEM})*"
_KIND_BEFORE = re.compile(
    rf"\b(?:the\s+)?(?P<kind>{_KIND_ALTERNATION})\s+"
    rf"(?:such\s+as\s+|like\s+|including\s+|named\s+|called\s+)?(?P<list>{_LIST})"
)
_KIND_AFTER = re.compile(rf"(?P<list>{_LIST})\s+(?P<kind>{_KIND_ALTERNATION})\b")
_LIST_SPLIT = re.compile(_LIST_SEP)
_LIST_STOPWORDS = frozenset(
    {
        "a", "all", "also", "an", "and", "any", "are", "as", "be", "both", "by", "can", "each",
        "for", "from", "in", "is", "it", "its", "may", "more", "of", "on", "or", "other", "such",
        "that", "the", "their", "these", "this", "those", "through", "to", "which", "with",
    }
)
#: An identifier that is shaped like an API name rather than an English word: it has an upper-case
#: letter after the first, an underscore, or a call suffix.
_API_SHAPED = re.compile(r"^(?:[A-Za-z_]\w*[A-Z_]\w*|[A-Z]\w*|\w+\(\))$")
_WRITE_CUE = re.compile(
    r"(?i)\b(?:for\s+(?:direct\s+)?manipulation|manipulat\w*|settable|writable|read[-/ ]write|"
    r"can\s+be\s+(?:set|changed|modified|assigned|written)|to\s+(?:set|change|modify|assign)\b|"
    r"gets?\s+(?:or|and)\s+sets?)"
)
_GETS_OR_SETS = re.compile(r"(?i)^\s*gets\s+or\s+sets\b")
_MEMBER_LINE = re.compile(
    r"^\s*(?:[-*+]\s+`(?P<bullet>[A-Za-z_]\w*)(?:\(\))?`\s*[:—-]\s*(?P<btext>.*)"
    r"|\|\s*`(?P<cell>[A-Za-z_]\w*)(?:\(\))?`\s*\|\s*(?P<ctext>[^|]*)\|)"
)
_HEADING = re.compile(r"^\s*(?P<marks>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
_DERIVED = re.compile(
    r"`(?P<base>[A-Za-z_]\w*)`-derived\s+`?(?P<sub>[A-Za-z_]\w*)`?"
    r"|`(?P<sub2>[A-Za-z_]\w*)`\s+(?:derives\s+from|inherits\s+from|is\s+a\s+subclass\s+of|"
    r"extends)\s+`(?P<base2>[A-Za-z_]\w*)`"
)
_DECLARED_KIND = re.compile(r"\b(record\s+struct|class|struct|record|interface|enum|trait)\b")
_GENERIC_ARGS = re.compile(r"<[^<>]*>")
_DOTTED = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
#: Words before a code span in an API-table row that say the row's type has it as a member.
_OWNERSHIP_CUE = re.compile(
    r"(?i)\b(?:exposes?|exposed\s+(?:via|through|as|by)|provides?|offers?|has|have|its)\s*$"
)
_SPAN_JOINER = re.compile(r"\s*(?:/|,|,?\s*(?:and|or))?\s*")
#: "the properties A and B of `Workbook`": the owner named right after the list.
_OWNER_AFTER = re.compile(r"\s+(?:of|on|in)\s+(?:the\s+|a\s+|an\s+)?`?(?P<owner>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)`?")
_NOT_A_NAME = frozenset({"null", "true", "false", "None", "True", "False", "self", "this", "void"})


def member_kind(fact: Fact, owner_name: str = "") -> str | None:
    """What a member ``public_symbol`` fact is: its recorded ``member_kind``, else what an older
    fact proves ("constructor" for a member named after its type, "nonmethod" for a signature
    without a parameter list), else ``None`` (not judged)."""
    attributes = fact.attributes or {}
    recorded = attributes.get("member_kind")
    if recorded:
        return recorded
    name = fact.value.rsplit(".", 1)[-1]
    if owner_name and name == owner_name:
        return "constructor"
    signature = attributes.get("signature", "")
    if signature and "(" not in signature:
        return "nonmethod"
    return None


def settable(fact: Fact) -> bool | None:
    """Whether a caller may assign the member, when the facts record it."""
    value = (fact.attributes or {}).get("settable")
    return None if value is None else value == "true"


_GETS_OR_SETS_LEAD = re.compile(r"(?i)^(\s*)(gets)\s+or\s+sets\b")


def caller_true_summary(text: str, fact: Fact) -> str:
    """``text`` (a member's doc comment) as true for a caller: a property the facts record as not
    settable keeps the getter half of a "Gets or sets ..." summary ("Gets border settings.").

    Decision (BL-063, 2026-11-13): rewrite, do not drop. The doc comment is the maintainers' own
    description and its getter half is true; only the setter half is false for a caller when the
    setter is private, protected, internal or absent (Cells .NET ``Style.Borders``,
    ``{ get; private set; }``, Style.cs:73). A member whose settability the facts do not record
    is left exactly as written."""
    if settable(fact) is not False:
        return text
    return _GETS_OR_SETS_LEAD.sub(lambda m: f"{m.group(1)}{m.group(2)}", text, count=1)


def type_kind(fact: Fact) -> str | None:
    """A type fact's declared kind: ``type_kind``, else the kind its ``declaration`` names, else
    "enum" for an enum and "class" for a Python ``class`` signature; ``None`` when unknown."""
    attributes = fact.attributes or {}
    if attributes.get("type_kind"):
        return attributes["type_kind"]
    declared = _DECLARED_KIND.search(attributes.get("declaration", ""))
    if declared is not None:
        word = declared.group(1)
        return "struct" if word.startswith("record") and "struct" in word else word
    if attributes.get("symbol_kind") == "enum":
        return "enum"
    if attributes.get("signature", "").startswith("class "):
        return "class"
    return None


def _base_names(fact: Fact) -> list[str]:
    """The simple names of a type's declared bases, from ``bases``, its ``declaration`` or a
    Python ``class X(A, B)`` signature."""
    attributes = fact.attributes or {}
    raw = attributes.get("bases", "")
    if not raw:
        declaration = attributes.get("declaration", "")
        if ":" in declaration:
            raw = declaration.split(":", 1)[1]
        elif " extends " in declaration or " implements " in declaration:
            raw = re.sub(r"\b(?:extends|implements)\b", ",", declaration.split(None, 1)[-1])
            raw = raw.split(",", 1)[1] if "," in raw else ""
        else:
            signature = attributes.get("signature", "")
            if signature.startswith("class ") and "(" in signature:
                raw = signature.split("(", 1)[1].rsplit(")", 1)[0]
    plain = raw
    while True:
        stripped = _GENERIC_ARGS.sub("", plain)
        if stripped == plain:
            break
        plain = stripped
    names = []
    for part in plain.split(","):
        part = part.strip().split("=")[0].strip()
        if part:
            names.append(_SEGMENTS.split(part.replace("::", "."))[-1].split()[-1])
    return names


def _declaration_known(fact: Fact) -> bool:
    """Whether the facts record how a type is declared (its kind and bases): without that, a
    member it inherits from an unrecorded base cannot be told from one it lacks, so no member is
    called missing (Aspose.PDF .NET's ``SectElement``, sealed with no declaration)."""
    attributes = fact.attributes or {}
    return bool(
        attributes.get("type_kind")
        or attributes.get("declaration")
        or attributes.get("bases")
        or attributes.get("signature", "").startswith("class ")
    )


class MemberIndex:
    """The public types and their members, as the ``public_symbol``/``enum_member`` facts state
    them, keyed for the checks below and for the renderer's and author's own use."""

    def __init__(self, facts: FactsDocument) -> None:
        symbols = _supported(facts, "public_symbol")
        self.types: dict[str, list[Fact]] = {}
        self.by_value: dict[str, Fact] = {}
        for fact in symbols:
            if (fact.attributes or {}).get("symbol_kind") in TYPE_KINDS:
                self.types.setdefault(fact.value.rsplit(".", 1)[-1], []).append(fact)
                self.by_value[fact.value] = fact
        self.members: dict[str, dict[str, list[Fact]]] = {}
        self.owners: dict[str, set[str]] = {}
        for fact in symbols:
            owner, _, name = fact.value.rpartition(".")
            if not name or owner not in self.by_value or fact.value in self.by_value:
                continue
            self.members.setdefault(owner, {}).setdefault(name, []).append(fact)
            self.owners.setdefault(name, set()).add(owner)
        self.values: dict[str, set[str]] = {}
        for fact in _supported(facts, "enum_member"):
            owner = str((fact.attributes or {}).get("enum", ""))
            self.values.setdefault(owner, set()).add(fact.value.rsplit(".", 1)[-1])
            self.owners.setdefault(fact.value.rsplit(".", 1)[-1], set()).add(owner)

    def __bool__(self) -> bool:
        return bool(self.types)

    def resolve(self, token: str) -> list[Fact]:
        """The type facts a README token names: a full or dotted-suffix value, a simple name, or
        a simple name with a ``-Qualifier`` naming one of its namespace segments."""
        token = token.strip().strip("`").removesuffix("()")
        token = _GENERIC_ARGS.sub("", token).replace("::", ".")
        if not token:
            return []
        if token in self.by_value:
            return [self.by_value[token]]
        if "." in token:
            simple = token.rsplit(".", 1)[-1]
            return [f for f in self.types.get(simple, []) if f.value.endswith("." + token)]
        if "-" in token:
            simple, _, qualifier = token.partition("-")
            found = [
                f
                for f in self.types.get(simple, [])
                if any(qualifier.lower() in seg.lower() for seg in f.value.split(".")[:-1])
            ]
            return found
        return list(self.types.get(token, []))

    def ancestors(self, fact: Fact, limit: int = 12) -> list[Fact]:
        """``fact`` and every type it derives from that the facts hold, nearest first."""
        found = [fact]
        pending = [fact]
        while pending and len(found) < limit:
            current = pending.pop(0)
            for name in _base_names(current):
                for base in self.types.get(name, []):
                    if base not in found:
                        found.append(base)
                        pending.append(base)
        return found

    def members_of(self, fact: Fact) -> dict[str, list[Fact]]:
        """Every member of ``fact`` and of the types it derives from, by name."""
        merged: dict[str, list[Fact]] = {}
        for owner in self.ancestors(fact):
            for name, found in self.members.get(owner.value, {}).items():
                merged.setdefault(name, []).extend(found)
        return merged

    def has_value(self, fact: Fact, name: str) -> bool:
        return any(name in self.values.get(owner.value, set()) for owner in self.ancestors(fact))


def _list_items(text: str) -> list[tuple[str, bool]]:
    """(name, written as a code span) for each item of a matched list, stopping at the first
    English stop word; the call suffix is removed."""
    items: list[tuple[str, bool]] = []
    for raw in _LIST_SPLIT.split(text):
        raw = raw.strip()
        if not raw:
            continue
        spanned = raw.startswith("`")
        name = raw.strip("`").removesuffix("()")
        if name.lower() in _LIST_STOPWORDS:
            if items:
                break
            continue
        items.append((name, spanned))
    return items


def _kind_lists(text: str) -> list[tuple[int, int, str, list[tuple[str, bool]], bool]]:
    """(start, end, claimed kind, items, kind word first) for every "the methods A, B and C" /
    "A and B properties" list in ``text``, non-overlapping, leftmost first."""
    found: list[tuple[int, int, str, list[tuple[str, bool]], bool]] = []
    for pattern in (_KIND_BEFORE, _KIND_AFTER):
        for match in pattern.finditer(text):
            items = _list_items(match.group("list"))
            if pattern is _KIND_AFTER and len(items) < 2:
                continue
            if not items:
                continue
            start, end = match.span()
            if any(start < other_end and other_start < end for other_start, other_end, *_ in found):
                continue
            found.append(
                (start, end, _KIND_WORDS[match.group("kind").lower()], items, pattern is _KIND_BEFORE)
            )
    return sorted(found, key=lambda item: item[0])


def _mentions(
    index: MemberIndex, text: str, spans: list[tuple[int, int]]
) -> list[tuple[int, list[Fact]]]:
    """(offset, type facts) for each type the text names outside the given list spans."""
    plain = text.replace("`", " ")
    found: list[tuple[int, list[Fact]]] = []
    for match in _DOTTED.finditer(plain):
        if any(start <= match.start() < end for start, end in spans):
            continue
        token = match.group(0)
        resolved = index.resolve(token)
        if not resolved and "." in token:
            # ``Scene.open`` names the type ``Scene``: the type is the part before the member.
            resolved = index.resolve(token.rsplit(".", 1)[0])
        if resolved:
            found.append((match.start(), resolved))
    return found


def _owner_before(
    index: MemberIndex,
    mentions: list[tuple[int, list[Fact]]],
    offset: int,
    default: list[Fact],
    items: list[tuple[str, bool]],
) -> list[Fact]:
    """The type a list's members belong to: the nearest type named before it that has one of
    the listed names as a member (a type in an earlier, ordinary list -- "List class exposes
    ListId, ListLevels, Style and methods like CompareTo" -- is not the owner), else the nearest
    type named before it, else ``default`` (a table row's own type)."""
    before = [facts for start, facts in mentions if start < offset]
    if default:
        before = [default, *before]
    names = {name.rsplit(".", 1)[-1] for name, _ in items}
    for candidates in reversed(before):
        if len(candidates) == 1 and names & set(index.members_of(candidates[0])):
            return candidates
    return before[-1] if before else default


def _ecosystem_family(facts: FactsDocument) -> str:
    return (_ecosystem(facts) or "").lower()


def _type_kind_ok(claimed: str, declared: str, ecosystem: str) -> bool:
    if declared in _CLAIMED_TYPE_KINDS.get(claimed, frozenset({declared})):
        return True
    # A C++ struct is a class (public default access); a Go/Rust struct has no "class" to be.
    return claimed == "class" and declared == "struct" and ecosystem not in ("net", "dotnet")


def _list_findings(
    index: MemberIndex,
    facts: FactsDocument,
    origin: _Origin,
    text: str,
    line: int,
    last: int | None,
    default_owner: list[Fact],
    member_coverage: bool,
) -> list[ClaimFinding]:
    """Rules (n)/(o) over one sentence or table description."""
    findings: list[ClaimFinding] = []
    lists = _kind_lists(text)
    if not lists:
        return findings
    mentions = _mentions(index, text, [(start, end) for start, end, *_ in lists])
    ecosystem = _ecosystem_family(facts)
    quoted = _plain(text)
    for start, end, claimed, items, kind_first in lists:
        if claimed in _CLAIMED_TYPE_KINDS:
            for name, _ in items:
                resolved = index.resolve(name)
                kinds = {type_kind(fact) for fact in resolved}
                if not resolved or None in kinds:
                    continue
                if not any(_type_kind_ok(claimed, kind, ecosystem) for kind in kinds if kind):
                    findings.append(
                        _finding(
                            origin,
                            line,
                            text,
                            f"the README calls `{name}` a {claimed} ({quoted!r}), but the facts "
                            f"declare it a {'/'.join(sorted(k for k in kinds if k))}",
                            last=last,
                        )
                    )
            continue
        after = _OWNER_AFTER.match(text, end)
        owners = (
            index.resolve(after.group("owner"))
            if after is not None and index.resolve(after.group("owner"))
            else _owner_before(index, mentions, start, default_owner, items)
        )
        if len(owners) != 1:
            continue
        owner = owners[0]
        owner_name = owner.value.rsplit(".", 1)[-1]
        members = index.members_of(owner)
        settables: list[bool | None] = []
        for name, spanned in items:
            target, member = owner, name
            if "." in name:
                prefix, _, member = name.rpartition(".")
                resolved = index.resolve(prefix)
                if len(resolved) != 1:
                    continue
                target = resolved[0]
            found = (
                members.get(member)
                if target is owner
                else index.members_of(target).get(member)
            )
            if found:
                kinds = {member_kind(fact, target.value.rsplit(".", 1)[-1]) for fact in found}
                if None in kinds:
                    settables.append(None)
                    continue
                allowed = _CLAIMED_MEMBER_KINDS[claimed]
                if not kinds & allowed:
                    shown = "/".join(sorted("property, field or constant" if k == "nonmethod"
                                            else k for k in kinds))
                    findings.append(
                        _finding(
                            origin,
                            line,
                            text,
                            f"the README calls `{target.value.rsplit('.', 1)[-1]}.{member}` a "
                            f"{claimed} ({quoted!r}), but the facts record it as a {shown}; "
                            "call it by its kind",
                            last=last,
                        )
                    )
                    continue
                values = {settable(fact) for fact in found}
                settables.append(False if values == {False} else (True if True in values else None))
                continue
            if index.has_value(target, member) or member == owner_name:
                continue
            # "the FieldIf and FieldCompare fields" names types by a domain word; only a list the
            # kind word introduces ("properties such as Color") claims a type name is a member.
            if not kind_first and index.resolve(member):
                continue
            # Python's surface records functions only (no instance attributes), so a name it
            # lacks proves nothing there (Aspose.Note Python ``Document.DisplayName``).
            if not member_coverage:
                continue
            if not index.members_of(target) or not _declaration_known(target):
                continue
            # A name is held to the members only when the README writes it as an API name: in a
            # code span, or as a call or mixed-case identifier after the kind word. A bare
            # acronym or word ("MAPI properties", "property ID") is English, not a member name.
            if not (spanned or (kind_first and _API_SHAPED.match(member) and not member.isupper())):
                continue
            elsewhere = sorted(
                other.rsplit(".", 1)[-1]
                for other in index.owners.get(member, set())
                if other != target.value
            )
            where = (
                f"; `{member}` is a member of {', '.join(f'`{o}`' for o in elsewhere[:3])}"
                if elsewhere
                else ""
            )
            findings.append(
                _finding(
                    origin,
                    line,
                    text,
                    f"the README names `{member}` as a {claimed} of "
                    f"`{target.value.rsplit('.', 1)[-1]}` ({quoted!r}), but `{target.value}` has "
                    f"no such member{where}",
                    last=last,
                )
            )
        if (
            claimed in ("property", "field", "member")
            and settables
            and all(value is False for value in settables)
            and _WRITE_CUE.search(text[start:])
        ):
            findings.append(
                _finding(
                    origin,
                    line,
                    text,
                    f"the README offers read-only members of `{owner_name}` for assignment "
                    f"({quoted!r}), but the facts record no setter for any of them",
                    last=last,
                )
            )
    return findings


def _derived_findings(
    index: MemberIndex, origin: _Origin, text: str, line: int, last: int | None
) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    for match in _DERIVED.finditer(text):
        base_name = match.group("base") or match.group("base2")
        sub_name = match.group("sub") or match.group("sub2")
        bases = index.resolve(base_name)
        subs = index.resolve(sub_name)
        if not subs and sub_name.endswith("ies"):
            subs = index.resolve(sub_name[:-3].capitalize() + "y")
        if not subs and sub_name.endswith("s"):
            subs = index.resolve(sub_name[:-1].capitalize())
        if not bases or not subs or {f.value for f in bases} & {f.value for f in subs}:
            continue
        if any(
            base.value in {ancestor.value for ancestor in index.ancestors(sub)}
            for base in bases
            for sub in subs
        ):
            continue
        # Without a single recorded base for any reading of the subject, nothing is refuted.
        if not any(_base_names(sub) for sub in subs):
            continue
        sub = subs[0]
        findings.append(
            _finding(
                origin,
                line,
                text,
                f"the README says `{sub.value.rsplit('.', 1)[-1]}` derives from `{base_name}` "
                f"({_plain(text)!r}), but its declared bases are "
                f"{', '.join(_base_names(sub)) or 'none'}",
                last=last,
            )
        )
    return findings


def _row_cells(text: str) -> tuple[str, str]:
    """(first cell, the rest of the row) of a Markdown table row."""
    body = text.strip().strip("|")
    first, _, rest = body.partition("|")
    return first.strip(), rest.strip().rstrip("|").strip()


def _row_span_findings(
    index: MemberIndex,
    origin: _Origin,
    known: set[str],
    row_type: Fact,
    description: str,
    line: int,
    text: str,
    member_coverage: bool = True,
) -> list[ClaimFinding]:
    """Rule (o) over one API-table row's description: every API-shaped code span names a member
    of the row's type (or of a type the row also names), or a type, or at least a name the
    surface states."""
    findings: list[ClaimFinding] = []
    named_types = [facts for _, facts in _mentions(index, description, [])]
    related = [row_type, *(fact for found in named_types for fact in found)]
    members = index.members_of(row_type)
    if not members or not _declaration_known(row_type):
        return findings
    row_name = row_type.value.rsplit(".", 1)[-1]
    owned = False
    previous_end = 0
    for span_match in _CODE_SPAN.finditer(description):
        span = span_match.group(1)
        between = description[previous_end : span_match.start()]
        previous_end = span_match.end()
        # Only a span the row says the type HAS is held to its members: "Exposes `GetExtra`",
        # "exposed via `Tangents`", and the spans joined to one by "/", "," or "and". A span the
        # row merely mentions ("a `TR` element", "added through `AddPagination`") is not.
        if _OWNERSHIP_CUE.search(between):
            owned = True
        elif not _SPAN_JOINER.fullmatch(between):
            owned = False
        for part in span.split("/"):
            token = part.strip().removesuffix("()")
            token = token.split("(", 1)[0]
            if not token or token in _NOT_A_NAME or not _IDENTIFIER.fullmatch(token.split(".")[-1]):
                continue
            if "." in token:
                prefix, _, member = token.rpartition(".")
                owners = index.resolve(prefix)
                if len(owners) != 1 or not index.members_of(owners[0]):
                    continue
                target = owners[0]
                if (
                    member in index.members_of(target)
                    or index.has_value(target, member)
                    or index.resolve(token)  # a nested type, ``Measure.NumberFormatList``
                ):
                    continue
                findings.append(
                    _finding(
                        origin,
                        line,
                        text,
                        f"the API table row for `{row_name}` names `{token}`, but "
                        f"`{target.value}` has no member `{member}`",
                    )
                )
                continue
            if not _API_SHAPED.match(token) or index.resolve(token) or token == row_name:
                continue
            if not owned or _EXCEPTION_NAME.search(token):
                continue
            # Python's surface holds functions only: a bare name may be an instance attribute it
            # never records, so only a name written as a call is held to the members.
            if not member_coverage and not part.strip().endswith(")"):
                continue
            if any(
                token in index.members_of(fact) or index.has_value(fact, token)
                for fact in related
            ):
                continue
            elsewhere = sorted(index.owners.get(token, set()))
            if elsewhere:
                findings.append(
                    _finding(
                        origin,
                        line,
                        text,
                        f"the API table row for `{row_name}` names `{token}`, a member of "
                        f"{', '.join(f'`{o}`' for o in elsewhere[:3])}, not of `{row_type.value}`",
                    )
                )
            elif token not in known:
                findings.append(
                    _finding(
                        origin,
                        line,
                        text,
                        f"the API table row for `{row_name}` names `{token}`, which no fact "
                        "states (no member or type of the public surface has that name)",
                    )
                )
    return findings


def _gets_or_sets_findings(
    lines: list[_Line], index: MemberIndex, origin: _Origin
) -> list[ClaimFinding]:
    """A member bullet or row under a type's heading that says "Gets or sets" for a member the
    facts record as not settable by a caller."""
    findings: list[ClaimFinding] = []
    heading: list[Fact] = []
    for line in lines:
        if line.in_fence:
            continue
        match = _HEADING.match(line.text)
        if match is not None:
            title = match.group("title").strip().strip("`")
            heading = index.resolve(title.split()[0]) if title else []
            continue
        member_line = _MEMBER_LINE.match(line.text)
        if member_line is None or len(heading) != 1:
            continue
        name = member_line.group("bullet") or member_line.group("cell")
        said = member_line.group("btext") or member_line.group("ctext") or ""
        if not _GETS_OR_SETS.match(said):
            continue
        found = index.members_of(heading[0]).get(name, [])
        if found and all(settable(fact) is False for fact in found):
            findings.append(
                _finding(
                    origin,
                    line.index,
                    line.text,
                    f"the README says `{heading[0].value.rsplit('.', 1)[-1]}.{name}` 'Gets or "
                    "sets', but the facts record no caller-visible setter (get-only for callers)",
                )
            )
    return findings


def _member_findings(lines: list[_Line], facts: FactsDocument, origin: _Origin) -> list[ClaimFinding]:
    """Rules (n) and (o): member kinds, accessors, member attribution and stated bases."""
    index = MemberIndex(facts)
    if not index:
        return []
    known, _, _ = _surface_names(facts)
    # Python's surface records functions only (no attributes, no fields): a name it lacks may be
    # an instance attribute, so only a claimed method or constructor is held to its members.
    vendored = _ecosystem_family(facts) not in ("python",)
    findings: list[ClaimFinding] = []
    for line in lines:
        if line.in_fence:
            continue
        row = _TABLE_ROW.match(line.text)
        if row is None:
            continue
        first, description = _row_cells(line.text)
        resolved = index.resolve(_row_name(first.strip("`")))
        if len(resolved) != 1 or not description:
            continue
        findings.extend(
            _list_findings(
                index, facts, origin, description, line.index, None, resolved, vendored
            )
        )
        findings.extend(_derived_findings(index, origin, description, line.index, None))
        findings.extend(
            _row_span_findings(
                index, origin, known, resolved[0], description, line.index, line.text, vendored
            )
        )
    for sentence, first_line, last_line in _sentences(lines):
        if sentence.lstrip().startswith("|"):
            continue
        findings.extend(
            _list_findings(index, facts, origin, sentence, first_line, last_line, [], vendored)
        )
        findings.extend(_derived_findings(index, origin, sentence, first_line, last_line))
    findings.extend(_gets_or_sets_findings(lines, index, origin))
    return findings


# --- (j) stubs described as working ----------------------------------------------------------

_STUB_MARKER = re.compile(
    r"""(?ix)
    \b(?:raises?|throws?|raising|throwing)\s+(?:an?\s+|the\s+)?`?
        (?:NotImplemented\w*|NotSupported\w*|UnsupportedOperation\w*)
  | \b(?:not\s+(?:yet\s+|currently\s+)?(?:implemented|functional)|unimplemented)\b
  | \b(?:always|unconditionally)\s+(?:throws?|raises?)\b
    """
)
# What follows a marker when the throw is conditional: "raises `X` for any other format", "throws
# when the stream is closed". Input validation, not a member whose body only throws.
_CONDITION = re.compile(
    r"(?i)^`?\w*`?\s*(?:\(\S*\)\s*)?(?:for\s+(?:any|every|an?|unsupported|other|invalid)\b"
    r"|if\b|when\b|whenever\b|unless\b|on\s+(?:invalid|unsupported|an?\s+unsupported)\b)"
)
_CLAUSE_BREAK = re.compile(r"(?:\.\s+|;\s+|\s+[—–]\s+|\n\s*[-*+]\s+|\n\s*\n)")
_SUBJECT_GAP_WORDS = 10
_EXCEPTION_NAME = re.compile(r"(?:Error|Exception)$")
_TYPE_NAME = re.compile(r"^[A-Z](?=[A-Za-z0-9_]*[a-z])[A-Za-z0-9_]*$")
_CONSTANT = re.compile(r"^(?P<member>[A-Z][A-Z0-9_]+)$")
_POSSESSIVE = re.compile(r"^['’]s\b")
_MEMBER = re.compile(
    r"^(?P<owner>[A-Z][A-Za-z0-9_]*)\.(?P<member>[A-Za-z_][A-Za-z0-9_]*)(?:\(.*\))?$"
)
_BARE_MEMBER = re.compile(r"^(?P<member>[a-z_][A-Za-z0-9_]*)\(.*\)$")
_COPULA_HEAD = re.compile(
    r"(?i)\b(?P<head>[a-z][a-z-]{3,})\s+(?:is|are)\s+(?:\w+\s+){0,1}$"
)
# A description that itself says the thing does not work is honest, whatever else it says.
_LIMITATION_CUE = re.compile(
    r"(?i)\bnot\b|\bno\b|\bcannot\b|\bcan't\b|\bnever\b|\bthrows?\b|\braises?\b|\bunimplemented\b"
    r"|\bunsupported\b|\bstub\b|\bplaceholder\b|\bno-op\b|\bout\s+of\s+scope\b|\bexcluded\b"
    r"|\breserved\b|\bunavailable\b|\bdeclares?\b"
)
# A description that opens with one of these says what the type does: "Maps workbook XML content",
# "Embeds and extracts text watermarks". A description that opens with a noun ("Base interface of
# a render target", "Document save format constants") names what the type is, and a stubbed type
# still is what it is.
_CAPABILITY_VERB = re.compile(
    r"(?i)^\W*(?:provides|enables|allows|lets|supports|maps|reads|writes|loads|saves|renders"
    r"|converts|encodes|decodes|embeds|extracts|exports|imports|generates|creates|computes"
    r"|evaluates|performs|applies|parses|serializes|handles|processes|produces|builds|samples"
    r"|triangulates|merges|opens|draws|signs|encrypts|decrypts|compresses|validates)\b"
)
_MEMBER_STOPWORDS = frozenset(
    {
        "get",
        "set",
        "from",
        "with",
        "to",
        "do",
        "is",
        "has",
        "can",
        "try",
        "on",
        "for",
        "as",
        "by",
    }
)


def _words(name: str) -> list[str]:
    """``encode_watermark`` and ``EncodeWatermark`` -> ["encode", "watermark"]."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
    return [word.lower() for word in spaced.split() if word]


_SUBJECT = re.compile(
    r"^\s*(?:[-*+]\s+)?\|?\s*(?:\*\*)?`(?P<name>[^`\n]+)`(?:\*\*)?(?:\(\))?"
)


def _verb_form(stem: str) -> re.Pattern[str]:
    """The stem as a verb: ``render`` -> render, renders, rendered, rendering; ``encode`` ->
    encode, encodes, encoded, encoding. Never a longer word built on it (``renderer``)."""
    base = re.escape(stem[:-1]) if stem.endswith("e") else re.escape(stem)
    tail = "(?:e|es|ed|ing)" if stem.endswith("e") else "(?:s|es|ed|ing)?"
    return re.compile(rf"(?i)\b{base}{tail}\b")


def _member_stem(member: str) -> str | None:
    words = [
        word
        for word in _words(member)
        if word not in _MEMBER_STOPWORDS and len(word) >= 4
    ]
    return words[0] if words else None


class StubIndex:
    """Which types and members a SUPPORTED fact says only throw.

    Read from the maintainers' own limitation statements (``inherited_unit`` facts): in a clause
    holding a stub marker, the code spans that lead up to the marker are its subject --
    ``Type.member()`` a stubbed member, a bare ``member()`` a member of the type named before it,
    a bare ``Type`` the whole type. A clause with no code span names its subject in words ("Text
    watermarking is not currently functional"): the head noun before the copula, when it begins
    with a verified public type's name, stubs that type."""

    def __init__(self, facts: FactsDocument) -> None:
        self.types: dict[str, str] = {}
        self.members: dict[str, dict[str, str]] = {}
        _, public_types, _ = _surface_names(facts)
        lowered = {name.lower(): name for name in public_types if len(name) >= 5}
        for fact in _supported(facts, "inherited_unit"):
            for clause in _CLAUSE_BREAK.split(fact.value):
                self._read(clause, fact.id, lowered)

    def _read(self, clause: str, fact_id: str, lowered: dict[str, str]) -> None:
        markers = list(_STUB_MARKER.finditer(clause))
        if not markers:
            return
        spans = list(_CODE_SPAN.finditer(clause))
        for marker in markers:
            if _CONDITION.match(clause[marker.end() :]):
                continue  # thrown for one input ("for any other format"): validation, not a stub
            before = [span for span in spans if span.end() <= marker.start()]
            if not before:
                head = _COPULA_HEAD.search(clause[: marker.start()])
                if head is not None:
                    word = head.group("head").lower()
                    for name_lower, name in lowered.items():
                        if word.startswith(name_lower):
                            self.types.setdefault(name, fact_id)
                continue
            chain: list[tuple[str, bool]] = []  # (token, followed by a possessive 's)
            boundary = marker.start()
            for span in reversed(before):
                gap = clause[span.end() : boundary]
                if len(re.findall(r"[A-Za-z]+", gap)) > _SUBJECT_GAP_WORDS:
                    break
                chain.insert(0, (span.group(1).strip(), bool(_POSSESSIVE.match(gap))))
                boundary = span.start()
            owner: str | None = None
            candidates: list[
                str
            ] = []  # types named with no member of theirs after them
            for token, possessive in chain:
                member = _MEMBER.match(token)
                if member is not None:
                    owner = member.group("owner")
                    self.members.setdefault(owner, {})[member.group("member")] = fact_id
                    continue
                bare = _BARE_MEMBER.match(token) or _CONSTANT.match(token)
                if bare is not None:
                    if owner is not None:
                        self.members.setdefault(owner, {})[bare.group("member")] = (
                            fact_id
                        )
                        if owner in candidates:
                            candidates.remove(owner)
                    continue
                if _TYPE_NAME.match(token) and not _EXCEPTION_NAME.search(token):
                    owner = token
                    # "`Mesh`'s height-map constructor path is not implemented" stubs a part of
                    # the type, not the type: a possessive subject is never the whole type.
                    if not possessive:
                        candidates.append(token)
            for token in candidates:
                self.types.setdefault(token, fact_id)

    def __bool__(self) -> bool:
        return bool(self.types or self.members)


def _stub_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin
) -> list[ClaimFinding]:
    stubs = StubIndex(facts)
    if not stubs:
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in _sentences(lines):
        if _LIMITATION_CUE.search(sentence.replace("`", " ")):
            continue
        # Only the statement's subject is judged: a table row's first cell, or the code span a
        # sentence opens with. A type mentioned in passing ("an optional entity (`Mesh`, ...)")
        # is not what the sentence describes.
        subject = _SUBJECT.match(sentence)
        if subject is None:
            continue
        name = subject.group("name").strip()
        owner = name.split(".", 1)[0]
        # The description is the text after the subject (a type's own name is not a verb).
        description = _CODE_SPAN.sub(" ", sentence[subject.end() :])
        reason: str | None = None
        source: str | None = None
        if owner in stubs.types and _CAPABILITY_VERB.search(description):
            reason, source = f"`{owner}` only throws", stubs.types[owner]
        else:
            for member, fact_id in sorted(stubs.members.get(owner, {}).items()):
                stem = _member_stem(member)
                if stem and _verb_form(stem).search(description):
                    reason, source = f"`{owner}.{member}` only throws", fact_id
                    break
        if reason is None:
            continue
        findings.append(
            _finding(
                origin,
                first,
                sentence,
                f"the README describes `{name}` as working ({_plain(sentence)!r}), but "
                f"{source} states {reason} (a stub): describe it as not implemented or omit it",
                last=last,
            )
        )
    return findings


# --- (k) CONTRADICTED examples printed --------------------------------------------------------

_FAILED = re.compile(r"\bFAILED;\s*(?P<error>[\w.]+)")
# The failures an example's own code causes against this API. Every other recorded failure here is
# the verification environment's (an ImportError from an optional extra's guard, a FileExistsError
# from a staged fixture, an IndentationError from extraction, a C++ prelude's incomplete type) or
# undecidable from the receipt (a RuntimeError the library raises on purpose, a NameError on a
# variable an earlier snippet defines): tuned on the iteration-4 and iteration-5 clean twins,
# which print such examples as the maintainers wrote them.
_API_ERRORS = frozenset({"AttributeError", "TypeError"})
_ENVIRONMENT_CAVEAT = re.compile(r"(?i)would not build|retried after installing")


def _failure(fact: Fact) -> str | None:
    """The API-level error a CONTRADICTED example's receipt records, or ``None``."""
    details = " ".join(evidence.detail or "" for evidence in fact.evidence)
    if _ENVIRONMENT_CAVEAT.search(details):
        return None
    match = _FAILED.search(details)
    error = match.group("error") if match else None
    return error if error in _API_ERRORS else None


def _fence_blocks(lines: list[_Line]) -> list[tuple[int, int, list[str]]]:
    """(opening line, closing line, stripped body lines) of every fenced block."""
    blocks: list[tuple[int, int, list[str]]] = []
    start: int | None = None
    body: list[str] = []
    for line in lines:
        if line.in_fence and line.text.strip().startswith(("```", "~~~")):
            if start is None:
                start, body = line.index, []
            else:
                blocks.append((start, line.index, body))
                start = None
            continue
        if start is not None:
            body.append(line.text.strip())
    return blocks


def _prints_all(body: list[str], code: str) -> bool:
    """Whether every non-blank line of ``code`` is in ``body``, in order."""
    wanted = [line.strip() for line in code.splitlines() if line.strip()]
    if not wanted:
        return False
    position = 0
    for line in body:
        if position < len(wanted) and line == wanted[position]:
            position += 1
    return position == len(wanted)


def _example_findings(lines: list[_Line], facts: FactsDocument) -> list[ClaimFinding]:
    failing = [
        (fact, error)
        for fact in facts.by_kind("example")
        if fact.polarity == "CONTRADICTED" and (error := _failure(fact)) is not None
    ]
    if not failing:
        return []
    findings: list[ClaimFinding] = []
    for start, end, body in _fence_blocks(lines):
        for fact, error in failing:
            if not _prints_all(body, fact.value):
                continue
            unit = next(
                (
                    match.group(1)
                    for evidence in fact.evidence
                    if (
                        match := re.search(
                            r"unit (inherited_unit:\S+)", evidence.detail or ""
                        )
                    )
                ),
                None,
            )
            findings.append(
                ClaimFinding(
                    start,
                    "COMPOSING",
                    f"the README prints {fact.id}, which the facts record CONTRADICTED (running it "
                    f"failed with {error}): repair the example or omit it",
                    last=end,
                    unit=unit,
                )
            )
            break
    return findings


# --- (l) the package name a sentence states ---------------------------------------------------

_NAME_FRAME = re.compile(
    r"(?i)\b(?:distribution|package|project|artifact|crate|module)\s+(?:name|id)\b"
    r"|\bpublished\s+(?:as|under)\b|\binstall(?:ed|s)?\s+(?:it\s+)?as\b"
)
_PACKAGE_TOKEN = re.compile(r"^@?[A-Za-z][\w@.-]*[-_.][\w@.-]+$")


def _name_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin
) -> list[ClaimFinding]:
    identity = _fact(facts, "package:name")
    if identity is None:
        return []
    exact = {fact.value.lower() for fact in facts.facts if fact.polarity == "SUPPORTED"}
    stem = _stem(identity.value)
    findings: list[ClaimFinding] = []
    for sentence, first, last in _sentences(lines):
        if not _NAME_FRAME.search(sentence):
            continue
        for token in dict.fromkeys(
            span.strip() for span in _CODE_SPAN.findall(sentence)
        ):
            if not _PACKAGE_TOKEN.match(token) or token.lower() in exact:
                continue
            if _pep503(token) == _pep503(identity.value):
                continue
            # A near-miss: the identity's stem without its ``-foss`` (``aspose-font`` for
            # ``aspose-font-foss``) or a truncation of it. A longer name built on the identity is
            # rule (f)'s; an unrelated name is not this package's.
            candidate = _stem(token)
            if not candidate or not stem.startswith(candidate):
                continue
            findings.append(
                _finding(
                    origin,
                    first,
                    sentence,
                    f"the README states the package name is {token!r} ({_plain(sentence)!r}), but "
                    f"the package identity is {identity.value!r}",
                    last=last,
                )
            )
    return findings


# --- (m) generator guard: uncomputed structure, verification narrative ------------------------

_NUMBER_WORDS = {
    "one": 1,
    "a single": 1,
    "single": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}
_STRUCTURE = re.compile(
    r"""(?ix)
    \b(?:organi[sz]ed|grouped|arranged|split|divided|packaged)\s+(?:in(?:to)?|across)\s+
        (?P<count>one|a\s+single|single|two|three|four|five|\d+)\s+
        (?P<noun>modules?|packages?|namespaces?)\b
  | \bacross\s+(?P<count2>\d+)\s+(?P<noun2>modules|packages|namespaces)\b
    """
)
_VERIFICATION_NARRATIVE = re.compile(
    r"""(?ix)
    \b(?:everything|all\s+(?:of\s+)?(?:the\s+|these\s+)?(?:examples?|code|snippets?|capabilit\w+
        |features?|outputs?|samples?)|each\s+(?:example|snippet|capability|feature|sample)
        |every\s+(?:example|snippet|capability|feature|sample))\b
        [^.]{0,60}?\b(?:was|were|has\s+been|have\s+been)\s+(?:\w+\s+){0,2}?
        (?:exercised|verified|tested|confirmed|validated|checked|executed)\b
  | \b(?:fully|thoroughly|extensively|comprehensively|battle)[-\s]tested\b
  | (?<!not\s)\b(?:fully|independently)\s+verified\b
  | (?<!not\s)\bverified\s+on\s+(?:every|all|each)\b
  | \breal\s+outputs?\b[^.]{0,80}\b(?:mirror|match|generated|fixture)
  | \bfixture-backed\b
    """
)


def _module_count(facts: FactsDocument) -> int:
    return sum(
        1
        for fact in _supported(facts, "public_symbol")
        if (fact.attributes or {}).get("symbol_kind") == "module"
    )


def _generated_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin
) -> list[ClaimFinding]:
    modules = _module_count(facts)
    findings: list[ClaimFinding] = []
    for sentence, first, last in _sentences(lines):
        if origin.unit(sentence) is not None:
            continue  # the maintainers' own words: judged by (h)-(l) and the disposition stage
        plain = _plain(sentence)
        structure = _STRUCTURE.search(plain)
        if structure is not None and modules:
            word = (structure.group("count") or structure.group("count2") or "").lower()
            stated = _NUMBER_WORDS.get(" ".join(word.split()))
            stated = (
                stated if stated is not None else int(word) if word.isdigit() else None
            )
            # Only "one module" is held to the module facts: a module symbol is a namespace or a
            # package directory, and a reference site's own grouping of N modules is a different
            # count the facts cannot confirm or refute (iteration 4: "881 public types across 37
            # modules" beside 31 module facts). That a multi-module surface is "one module" they
            # refute outright.
            if stated == 1 and modules >= 2:
                findings.append(
                    ClaimFinding(
                        first,
                        "COMPOSING",
                        f"the README says the surface is {structure.group(0)!r} ({plain!r}), but "
                        f"the facts record {modules} module symbols; never state a structure count "
                        "the facts do not give",
                        last=last,
                    )
                )
    return findings


# --- TC-017b work item 4: the verification-narrative ban -------------------------------------
#
# Rule (m) above already refuses an uncomputed structure count; the verification-narrative half
# of its old docstring now lives here, as its own finding function, because it gained a condition
# plain prohibition never had: a generated sentence MAY narrate a verification when a real
# verification record actually backs it. "Real" is deliberately narrow -- post-TC-016's own fix
# (GATE5_DELIVERY_PROGRAM/TC-016: a TIMED_OUT receipt was being mislabelled CONTRADICTED; it is
# correctly UNRESOLVED, confidence 0.5, in this codebase) a TIMED_OUT/NEEDS_INPUT/NOT_VERIFIED
# example proves nothing either way, so it must never, by itself, license a narrative claim.


def _fully_verified(facts: FactsDocument) -> bool:
    """Whether every ``example`` fact in this document genuinely passed a real run: SUPPORTED
    (an ``EXECUTED``/``COMPILED`` receipt -- never merely "not UNRESOLVED") at full confidence
    (``readme/evidence/facts/examples.py``: only ``EXECUTED``/``FAILED`` ever carry
    ``confidence=1.0``; a ``FAILED`` example is ``CONTRADICTED``, so a confidence-1.0 ``SUPPORTED``
    example fact is, in this codebase, exactly an ``EXECUTED`` one).

    A document with no example facts at all backs nothing (``False``): a generator with zero
    verification evidence cannot narrate one just because it also printed no failure. A blanket
    "everything below was exercised and confirmed" is true only when every example this pipeline
    actually ran did, in fact, pass -- one real pass among other real failures, or a TIMED_OUT
    receipt alone, does not back it either.
    """
    examples = facts.by_kind("example")
    if not examples:
        return False
    return all(fact.polarity == "SUPPORTED" and fact.confidence == 1.0 for fact in examples)


def _verification_findings(
    lines: list[_Line], facts: FactsDocument, origin: _Origin
) -> list[ClaimFinding]:
    """A generated sentence may never state or imply that something was verified, tested,
    exercised, or confirmed working unless ``_fully_verified`` backs it. Quoted maintainer text
    (``origin.unit(sentence) is not None``) is never judged here -- the maintainers' own claims
    about their own verification are the disposition stage's concern, not a thing this pipeline
    invented and must therefore justify."""
    if _fully_verified(facts):
        return []
    findings: list[ClaimFinding] = []
    for sentence, first, last in _sentences(lines):
        if origin.unit(sentence) is not None:
            continue  # the maintainers' own words: never judged by this generator-only ban
        plain = _plain(sentence)
        narrative = _VERIFICATION_NARRATIVE.search(plain)
        if narrative is not None:
            findings.append(
                ClaimFinding(
                    first,
                    "COMPOSING",
                    f"the README narrates a verification ({narrative.group(0)!r} in {plain!r}) that "
                    "no real, fully-passed verification record backs; state what the library does, "
                    "never how it was checked",
                    last=last,
                )
            )
    return findings


def surface_findings(
    lines: list[_Line], facts: FactsDocument, probe_root: str | Path | None = None
) -> list[ClaimFinding]:
    """Rules (h)-(m) over one README's lines, plus the TC-017b work item 4 verification-narrative
    ban.

    ``probe_root`` (TC-017b work item 3) is the repository's own checked-out source tree, when a
    caller has one on disk; without it (the default, and every production caller today -- see
    ``readme/validation/provenance.py``'s ``claim_failures``) the TC-017a probes are never
    consulted and every probe-based check below answers ``None`` throughout, exactly as if this
    card had never run: the fact-only checks are completely unaffected either way.
    """
    origin = _Origin(facts)
    probes = _Probes(facts, probe_root)
    return [
        *_count_findings(lines, facts, origin, probes),
        *_table_findings(lines, facts, origin, probes),
        *_member_findings(lines, facts, origin),
        *_stub_findings(lines, facts, origin),
        *_example_findings(lines, facts),
        *_name_findings(lines, facts, origin),
        *_generated_findings(lines, facts, origin),
        *_verification_findings(lines, facts, origin),
    ]
