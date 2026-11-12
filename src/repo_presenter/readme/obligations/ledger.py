"""TC-018: the byte-computed content ledger -- one record per live-README item, its obligation
(``classify.py``), its actual disposition in a candidate, and the evidence for that outcome.

``build_ledger`` is the pure function: every input is already-extracted, in-memory data (no file
I/O, no network, no provider call), so it is the one place both the verification wiring
(``readme/validation/supersession.py``) and the standalone script (``scripts/
build_content_ledger.py``) go through. ``ledger_from_candidate`` adapts a real
``readme.validation.failures.Candidate`` (or an equivalently-shaped object: anything with
``.facts.by_kind``, ``.dispositions`` and ``.readme``) into ``build_ledger``'s inputs.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from repo_presenter.readme.composition.list_coverage import list_items
from repo_presenter.readme.composition.references import positional_only
from repo_presenter.readme.obligations.classify import (
    FILLER_DESCRIPTION,
    Obligation,
    Unit,
    UnitFacts,
    classify_unit,
)
from repo_presenter.readme.validation.content_presence import unstated

#: The disposition vocabulary (``readme/reconciliation/dispositions.py``'s module docstring) a
#: ledger entry's ``disposition`` field carries, unchanged, from ``dispositions.json``.
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{2,}:?$")
_LEADING_SUBJECT = re.compile(r"^\s*`([^`\n]+)`")
_PATH_LIKE = re.compile(r"^[\w.\-/]+\.[A-Za-z0-9]{1,6}$")
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_BARE_URL = re.compile(r"https?://\S+")
_VERSION_NUMBER = re.compile(r"\b\d+\.\d+(?:\.\d+)*\b")
_VERSION_WORDS = re.compile(r"\bversion[s]?\b|\bpin(?:s|ned)?\b", re.IGNORECASE)
_COUNT_CLAIM = re.compile(
    r"\b\d+\s+(?:public\s+)?(?:types?|symbols?|classes?|members?)\b", re.IGNORECASE
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[(])")


def _core(name: str) -> str:
    """An identifier's last path segment, arguments and return type removed, lower case.

    Reproduced unchanged from ``readme/validation/supersession.py``'s own ``_core`` (not
    imported, to keep this module's only product-code dependency on that one a one-way import
    of ``public_names``/``owed``, never a cycle).
    """
    head = re.split(r"[(\s]", name.strip(), maxsplit=1)[0]
    return re.split(r"::|\.", head)[-1].lower()


def public_symbol_names(facts: Sequence[Any]) -> frozenset[str]:
    """The last segment of every SUPPORTED ``public_symbol``/``enum_member`` fact's value.

    Accepts either real ``Fact`` objects (``.kind``/``.polarity``/``.value``) or the plain dict
    rows a materialized bundle's ``facts.json`` holds -- both shapes this codebase already uses
    (``readme/validation/parity.py``'s ``_fact_rows`` is the dict one).
    """
    names: set[str] = set()
    for fact in facts:
        kind = fact.get("kind") if isinstance(fact, Mapping) else fact.kind
        if kind not in ("public_symbol", "enum_member"):
            continue
        polarity = fact.get("polarity") if isinstance(fact, Mapping) else fact.polarity
        if polarity != "SUPPORTED":
            continue
        value = fact.get("value") if isinstance(fact, Mapping) else fact.value
        names.add(_core(str(value)))
    return frozenset(names)


def example_polarity_by_unit(facts: Sequence[Any]) -> dict[str, str]:
    """``{code_block unit_id: example fact polarity}`` for every example fact an evidence entry
    names with "unit <id>" (the same marker ``readme/validation/units.py``'s
    ``_example_for_unit`` reads)."""
    out: dict[str, str] = {}
    for fact in facts:
        kind = fact.get("kind") if isinstance(fact, Mapping) else fact.kind
        if kind != "example":
            continue
        polarity = fact.get("polarity") if isinstance(fact, Mapping) else fact.polarity
        evidence = fact.get("evidence") if isinstance(fact, Mapping) else fact.evidence
        for item in evidence or ():
            detail = item.get("detail") if isinstance(item, Mapping) else item.detail
            match = re.search(r"\bunit (inherited_unit:\S+)", detail or "")
            if match:
                out[match.group(1)] = str(polarity)
    return out


def _table_rows(text: str) -> list[tuple[str, list[str]]]:
    """Every data row of a Markdown table: the header row and the ``---`` separator row are
    never pieces of their own (the heading's own obligation, if any, is decided separately), so
    only a row whose leading cell is a backtick-quoted subject -- the API Reference convention
    this whole rule table assumes, same as ``readme/validation/supersession.py``'s own
    ``_LEADING_SPAN`` -- counts as a table_item piece."""
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = _TABLE_ROW.match(line)
        if match is None:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if all(_SEPARATOR_CELL.match(cell) for cell in cells if cell):
            continue
        if not cells or not _LEADING_SUBJECT.match(cells[0]):
            continue
        rows.append((line.strip(), cells))
    return rows


def _resolves(target: str, tree_paths: Sequence[str]) -> bool | None:
    if target.startswith(("http://", "https://", "#")):
        return None  # a network check is out of scope for the offline, zero-provider-call ledger
    cleaned = target.lstrip("./")
    if not tree_paths:
        return None
    return any(path == cleaned or path.endswith("/" + cleaned) for path in tree_paths)


def _table_item_facts(
    subject: str,
    description: str,
    public_names: frozenset[str],
    readme: str,
    tree_paths: Sequence[str] = (),
) -> UnitFacts:
    requalify = re.match(r"^([A-Za-z_]\w*)-([A-Za-z_]\w*)$", subject)
    if _PATH_LIKE.match(subject) and "/" in subject:
        return UnitFacts(is_link_subject=True, path_exists=_resolves(subject, tree_paths))
    if requalify is not None:
        base, suffix = requalify.group(1), requalify.group(2)
        wanted = {token.lower() for token in re.split(r"[_.]", suffix) if token}
        requalified_printed = False
        for span in re.findall(r"`([^`\n]+)`", readme):
            parts = span.split(".")
            if len(parts) > 1 and parts[-1] == base:
                qualifiers = {t.lower() for p in parts[:-1] for t in re.split(r"[_.]", p)}
                if wanted & qualifiers:
                    requalified_printed = True
                    break
        if requalified_printed:
            return UnitFacts(requalified_printed=True)
        subject = base
    public = _core(subject) in public_names if public_names else None
    filler = bool(FILLER_DESCRIPTION.match(description.strip()))
    return UnitFacts(public=public, filler_description=filler)


def _prose_facts(text: str, public_names: frozenset[str], tree_paths: Sequence[str]) -> UnitFacts:
    link_match = _MARKDOWN_LINK.search(text) or _BARE_URL.search(text)
    if link_match:
        target = link_match.group(2) if link_match.lastindex else link_match.group(0)
        return UnitFacts(is_link_subject=True, path_exists=_resolves(target, tree_paths))
    if _COUNT_CLAIM.search(text):
        claimed = int(re.search(r"\d+", _COUNT_CLAIM.search(text).group(0)).group(0))
        contradicted = bool(public_names) and claimed > len(public_names) * 2
        return UnitFacts(is_count_claim=True, count_contradicted=contradicted)
    if positional_only(text):
        return UnitFacts(is_positional_only=True)
    if _VERSION_NUMBER.search(text) and _VERSION_WORDS.search(text):
        return UnitFacts(is_version_claim=True)
    mentioned = [
        _core(span)
        for span in re.findall(r"`([^`\n]+)`", text)
        if re.match(r"^[A-Za-z_][\w.:<>&-]*$", span.strip())
    ]
    if public_names and mentioned:
        found = [name for name in mentioned if name in public_names]
        if found:
            return UnitFacts(mentions_public_member=True)
    return UnitFacts()


@dataclass(frozen=True)
class LedgerEntry:
    """One live-README item's record: its obligation class, actual disposition, and evidence."""

    unit_id: str
    piece_kind: str
    text: str
    obligation: Obligation
    disposition: str
    carried: bool | None
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "piece_kind": self.piece_kind,
            "text": self.text[:4000],
            "obligation": self.obligation,
            "disposition": self.disposition,
            "carried": self.carried,
            "evidence": self.evidence,
        }


def _piece_for_presence(piece_kind: str) -> str:
    """The ``content_presence.unstated`` ``kind`` argument for one decomposed piece: a single
    table row or list bullet is tested the same mechanical way a whole table/list is."""
    return {"table_item": "table", "list_item": "list", "sentence": "paragraph"}.get(
        piece_kind, piece_kind
    )


def build_ledger(
    *,
    inherited_units: Sequence[Mapping[str, Any]],
    readme: str,
    public_names: frozenset[str] = frozenset(),
    example_polarity: Mapping[str, str] | None = None,
    tree_paths: Sequence[str] = (),
    dispositions: Mapping[str, str] | None = None,
    probe_public: Callable[[str], bool | None] | None = None,
) -> list[LedgerEntry]:
    """One :class:`LedgerEntry` per decomposed piece of every entry of ``inherited_units``.

    ``inherited_units`` is ``[{"id": "inherited_unit:031.table", "kind": "table", "text": ...}, ...]``
    (``kind`` the whole-unit vocabulary ``readme/validation/text.py``'s ``unit_type`` returns).
    ``dispositions`` is ``{unit_id: disposition}``. ``probe_public`` (TC-017a) is consulted as an
    ADDITIONAL, independent signal alongside ``public_names``: when both answer and disagree, the
    obligation is decided as ``undecided`` rather than picking a side (never a silent guess).
    """
    example_polarity = example_polarity or {}
    dispositions = dispositions or {}
    entries: list[LedgerEntry] = []
    for unit in inherited_units:
        unit_id = str(unit.get("id", ""))
        kind = str(unit.get("kind", ""))
        text = str(unit.get("text", ""))
        disposition = dispositions.get(unit_id, "")
        if kind == "code_block":
            pieces: list[tuple[str, str]] = [("code_block", text)]
        elif kind == "table":
            pieces = [("table_item", row) for row, _cells in _table_rows(text)]
        elif kind == "list":
            pieces = [("list_item", item) for item in list_items(text)]
        elif kind == "paragraph":
            pieces = [
                ("sentence", part)
                for part in _SENTENCE_END.split(re.sub(r"\s+", " ", text).strip())
                if part
            ] or [("sentence", text)]
        elif kind in ("heading", "badge_row"):
            pieces = [(kind, text)]
        else:
            pieces = [(kind or "sentence", text)]
        for piece_kind, piece_text in pieces:
            if piece_kind == "code_block":
                polarity = example_polarity.get(unit_id)
                is_mermaid = piece_text.lstrip().lstrip("`~ \n").lower().startswith("mermaid")
                facts = UnitFacts(
                    is_mermaid=is_mermaid,
                    own_diagram_drawn=("```mermaid" in readme) if is_mermaid else None,
                    contradicted=(polarity == "CONTRADICTED") if polarity else None,
                    evidence_exists=(polarity in ("SUPPORTED", "UNRESOLVED")) if polarity else None,
                )
            else:
                facts = _facts_for_piece(
                    piece_kind, piece_text, public_names, readme, tree_paths, probe_public
                )
            obligation = classify_unit(Unit(piece_kind, piece_text, unit_id), facts)
            carried: bool | None = None
            evidence = "undecided -- model decision"
            if obligation == "must_carry":
                missing = unstated(
                    piece_text, readme, kind=_piece_for_presence(piece_kind), strict=True
                )
                carried = not missing
                evidence = (
                    "stated in the candidate README"
                    if carried
                    else f"unstated(strict=True) found {len(missing)} missing piece(s)"
                )
            elif obligation == "may_drop":
                evidence = "mechanically exempt (private surface, dead link, renderer-owned markup, or equivalent)"
            entries.append(
                LedgerEntry(unit_id, piece_kind, piece_text, obligation, disposition, carried, evidence)
            )
    return entries


def _facts_for_piece(
    piece_kind: str,
    text: str,
    public_names: frozenset[str],
    readme: str,
    tree_paths: Sequence[str],
    probe_public: Callable[[str], bool | None] | None,
) -> UnitFacts:
    if piece_kind == "heading":
        return UnitFacts()
    if piece_kind == "badge_row":
        return UnitFacts()
    if piece_kind == "table_item":
        match = _LEADING_SUBJECT.match(text.strip().strip("|").strip())
        cells = [c.strip() for c in text.strip().strip("|").split("|")]
        subject_cell = cells[0] if cells else text
        subject = match.group(1) if match else subject_cell.strip("`")
        description = cells[-1] if len(cells) > 1 else ""
        facts = _table_item_facts(subject, description, public_names, readme, tree_paths)
        if probe_public is not None and facts.public is None and not facts.filler_description:
            probed = probe_public(subject)
            if probed is not None:
                facts = UnitFacts(
                    public=probed,
                    filler_description=facts.filler_description,
                    requalified_printed=facts.requalified_printed,
                    is_link_subject=facts.is_link_subject,
                    path_exists=facts.path_exists,
                )
        elif probe_public is not None and facts.public is not None:
            probed = probe_public(subject)
            if probed is not None and probed != facts.public:
                facts = UnitFacts(
                    public=None,
                    filler_description=facts.filler_description,
                    requalified_printed=facts.requalified_printed,
                )
        return facts
    return _prose_facts(text, public_names, tree_paths)


def ledger_from_candidate(
    candidate: Any, probe_public: Callable[[str], bool | None] | None = None
) -> list[LedgerEntry]:
    """Adapt a real ``Candidate`` (or an equivalently-shaped object) into :func:`build_ledger`."""
    from repo_presenter.readme.validation.text import unit_type

    inherited = [
        {"id": fact.id, "kind": unit_type(fact.id), "text": str(fact.value or "")}
        for fact in candidate.facts.by_kind("inherited_unit")
    ]
    public = public_symbol_names(candidate.facts.facts)
    examples = example_polarity_by_unit(candidate.facts.facts)
    dispositions = {
        str(entry.get("unit_id", "")): str(entry.get("disposition", ""))
        for entry in (candidate.dispositions or {}).get("dispositions", [])
    }
    return build_ledger(
        inherited_units=inherited,
        readme=candidate.readme,
        public_names=public,
        example_polarity=examples,
        tree_paths=list(getattr(candidate, "tree_paths", []) or []),
        dispositions=dispositions,
        probe_public=probe_public,
    )
