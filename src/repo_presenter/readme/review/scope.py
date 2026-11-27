"""What a review unit may show the model: only the text an author wrote (reviewer logic 6).

The renderer prints the identity, badges, banner, navigation, At a Glance diagram, installation,
dependencies, third-party notices and license from facts. In the mixed sections it prints the
headings, tables, fenced examples, ``<details>`` wrappers, "Not verified" notes and the member
reference bullets. None of that is a claim an author made, and iteration 2 of the calibration found
130 of 159 unsupported-claim findings aimed at exactly such text. So it is never sent: a line the
reviewer is not shown cannot be cited (``reply.validate_review_reply`` rejects a citation of a line
outside the unit), which excludes renderer-owned text from every claim kind by construction.

``reviewable_lines`` is structural, not lexical: it reads the shell section a line is under and the
Markdown shape of the line, and it never looks at what the line says. A line is reviewable when it
is prose, under a section the renderer does not own wholesale, outside every fence.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
from repo_presenter.readme.composition.placement import ATTRIBUTED, ATTRIBUTION_LINE
from repo_presenter.readme.review.matching import present
from repo_presenter.readme.validation.text import section_lines

#: Sections the renderer prints wholesale from facts (owner ``D``) and the diagram.
RENDERER_SECTIONS: frozenset[str] = frozenset(
    {section.id for section in SEMANTIC_SHELL if section.owner == "D"} | {"at_a_glance"}
)
OPENING = "opening"
STRUCTURE = "structure"
_FENCE = re.compile(r"^\s*(```|~~~)")
_NOT_VERIFIED = "> **Not verified:**"
# Both spellings: the renderer's current one and the one sealed bundles carry (BL-002 K11).
_SURFACE_SUMMARY = re.compile(
    r"^The (?:verified public surface|public API) has \d+ types?\.\s*$"
)
_TABLE_DELIMITER = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
#: A Core API table row as the renderer prints it: ``| `Name` | description |``.
_TYPE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*)\|$")
#: Markup lines the renderer (or a reader's Markdown) owns rather than an author: headings, tables,
#: HTML tags, badge and banner images, horizontal rules, "Not verified" notes, and the attribution
#: line the renderer prints before maintainer content kept as PRESERVE_ATTRIBUTED (a label, not a
#: claim; the maintainer content under it stays shown).
_MARKUP_START = (
    "#", "|", "<", "[![", "![", "---", "***", "___", _NOT_VERIFIED, ATTRIBUTION_LINE
)
#: Sentences the renderer writes into a section an author otherwise owns (``composition.renderer``:
#: ``_development_sentences``, the resources and API summaries, the Enterprise lead, the issues
#: bullet). They are facts the renderer computed, not claims an author made, so they are removed from
#: what a unit shows; ``tests/readme/review/test_scope.py`` renders the fixture's
#: ``renderer_sentences`` and asserts every one is covered here.
_RENDERER_SENTENCES = tuple(
    re.compile(pattern)
    for pattern in (
        r"The suite covers \d+ test files under `[^`]*`\.",
        r"The \[[^\]]*\]\([^)]*\) runs .*?\.(?=\s|$)",
        # BL-700: the build/test asset locators of Development and Testing (``renderer._asset_locators``, R43(2)),
        # each printed only for a SUPPORTED ``build_test_asset`` fact. The sentence after the suite/CI/release
        # sentences was the one the patterns missed, so the line stayed "authored" and the audit flagged it
        # (Slides .NET 726: "... Project documentation lives under `docs/`.", round 6, not derivable).
        r"(?:Tests live under|Example programs live under|Project documentation lives under) `[^`]*`\.",
        r"Releases run through the \[[^\]]*\]\([^)]*\)\.",
        r"The (?:verified public surface|public API) has \d+ types?\.",
        (
            r"It covers all \d+ (?:verified )?public types; the \[API Reference\]\(#api-reference\) "
            r"section above covers the essentials\."
        ),
        # BL-500: the maintainers' own spelling of the same pointer on the full-reference link ("for all 968
        # public types (the API Reference section above covers the essentials)"): the count is the one
        # ``renderer.correct_stated_type_counts`` computes and the pointer is printed only when
        # ``renderer._reference_pointer`` knows the section is rendered above.
        (
            r"(?i)[ \t]*(?:\bfor\s+all\s+[\d,]+\s+public\s+types\s*)?"
            r"\((?:the\s+)?(?:\[API\s+reference\]\(#api-reference\)|API\s+reference)\s+section\s+above"
            r"\s+covers\s+[^()]*\)"
        ),
        r"These limitations don't apply to \[[^\]]*\]\([^)]*\)\.",
        r"See \[[^\]]* — Enterprise Edition\]\([^)]*\)\.",
        r"(?:- )?Found a bug or have a feature request\? \[Open an issue\]\([^)]*\)\.",
        # BL-582: a Documentation & Resources item whose description is the renderer's own fact-true one for
        # the link's target (``renderer.link_target_description``: the product site, the repository path, the
        # release page or the host) is a location the renderer computed, not a claim an author made. Hosted PSD
        # Java 44920305486: the review faulted "- **[GitHub Repository](...)** — On github.com." and, the line
        # being no unit's, the degrade could only delete the link (BC-17). The whole item is then not shown.
        r"^\s*-\s+\*\*\[[^\]]*\]\([^)]*\)\*\*\s+\u2014\s+(?:"
        r"A section of this README\.|In this repository\.|`[^`]+` in this repository\.|"
        r"The `[^`]+` directory in this repository\.|Release history\.|The product page\.|"
        r"Installation, walkthroughs, and feature guides for this library\.|"
        r"Task-focused how-to articles and answers to common questions\.|"
        r"The complete, browsable reference for the public API\.|On [A-Za-z0-9.-]+\.)\s*$",
    )
)


def shown_text(row: str) -> str:
    """``row`` without the sentences the renderer appended to it; blank when nothing else is left."""
    text = row
    for pattern in _RENDERER_SENTENCES:
        text = pattern.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip() if text != row else row


def renderer_sentence_texts(row: str) -> list[str]:
    """The renderer-appended sentences ``shown_text`` would remove from ``row``, as printed (BL-801)."""
    found: list[str] = []
    for pattern in _RENDERER_SENTENCES:
        found.extend(match.group(0).strip() for match in pattern.finditer(row) if match.group(0).strip())
    return found


def _first_heading(rows: list[str]) -> int | None:
    inside = False
    for index, row in enumerate(rows):
        if _FENCE.match(row):
            inside = not inside
        elif not inside and row.startswith("## "):
            return index
    return None


def _is_markup(stripped: str) -> bool:
    return stripped.startswith(_MARKUP_START)


def _member_bullet(stripped: str, section: str) -> bool:
    """The API reference's member reference is printed from the symbol facts."""
    return section == "api_reference" and (
        stripped.startswith("- `") or _SURFACE_SUMMARY.match(stripped) is not None
    )


def _table_delimiter(row: str) -> bool:
    return _TABLE_DELIMITER.match(row.strip()) is not None


def _table_data_row(rows: list[str], index: int) -> bool:
    """``rows[index]`` is a body row of a Markdown table: a ``|`` row that is neither the delimiter
    row (``| --- | --- |``) nor the header row right above one. A header row holds column labels; a
    body row holds whatever its author wrote in the cells, prose included."""
    row = rows[index].strip()
    if not row.startswith("|") or _table_delimiter(row):
        return False
    following = rows[index + 1] if index + 1 < len(rows) else ""
    return not _table_delimiter(following)


def authored_table_lines(readme: str, facts: FactsDocument) -> frozenset[int]:
    """The 1-based numbers of the API reference table rows whose description an author wrote.

    The renderer prints the Core API table from facts, but a type with no docstring gets the
    sentence authored for it in a bounded batch (``authoring.undocumented_types`` /
    ``renderer._symbol_description``: the ``type:<fact id>`` unit). That sentence is an author's
    claim like any other, and iteration 4 of the calibration found real unsupported claims in
    exactly such cells (own Cells C++, own HTML Python), which the reviewer was never shown.
    Structural, like ``reviewable_lines``: a row is authored when its type is a SUPPORTED class or
    enum with no docstring and its description is not one of the renderer's own fact-true rows
    (``renderer_row_descriptions``).

    BL-390: a type that also carries a ``signature`` is just as authored (the batch is written
    for every undocumented type and the renderer prints its sentence before it falls back to
    the signature), but this function skipped it, so the production review never showed
    Aspose.Note Python's 15 authored rows and the M9 audit, which shows every row, flagged 14 of
    them (hosted round 44588173276). The rule now matches the producer's."""
    return frozenset(authored_type_rows(readme, facts, reviewable=True))


def fact_true_row_forms(fact: Fact, facts: FactsDocument, nouns: Collection[str] = ()) -> frozenset[str]:
    """Every normalized description the renderer prints for ``fact``'s Core API row when NO author
    wrote a sentence for it and the type has no doc comment: the shared fact-true description of both
    lanes (``type_description.TypeDescriber``: "Declares the fields a and b.", "Class that declares the
    method load.", an enum's "Enumerates A, B and C.") with the row's optional stub marker
    (``renderer._stub_marked``) and "Not implemented.".

    BL-560 (hosted refresh runs 44898179900 HTML Python and 44898282006 PSD Java): after the BL-240
    degrade replaced every authored row the review faulted with this row, the production review faulted
    the fact-true rows themselves (``unsupported_claim`` on "Declares the fields condition_text and
    css_rules."): the packet lists a type's method names only, so a field or property the describer
    names is never shown to the reviewer, and no lever can change a row no unit owns. The row is the
    renderer's own text, derived from SUPPORTED facts by the one describer; it is not an author's
    claim (the same reasoning as ``renderer_row_descriptions``), so it is not reviewed as one."""
    from repo_presenter.readme.composition.authoring import type_values
    from repo_presenter.readme.correction.detectors.type_description import (
        DESCRIBED_VALUES,
        describer_for,
    )

    texts: list[str] = []
    # ``nouns`` (BL-897): the README's own kind word Lane L's correction keeps when the facts record no kind
    # ("Class that inherits from X ..."): ``describe(fact, noun)``, the same call ``type_description`` makes.
    for noun in ("", *nouns):
        described = describer_for(facts).describe(fact, noun)[0]
        if described and described not in texts:
            texts.append(described)
    if (fact.attributes or {}).get("symbol_kind") == "enum":
        values = type_values(fact, facts, limit=len(facts.facts))
        shown = values[:DESCRIBED_VALUES]
        if shown:
            listed = ", ".join(shown[:-1]) + (" and " if len(shown) > 1 else "") + shown[-1]
            lead = "Enumerates values including" if len(values) > len(shown) else "Enumerates"
            texts.append(f"{lead} {listed}.")
    forms = {"not implemented."}
    for text in texts:
        text = text.replace("|", "/").replace("`", "")
        # ``renderer._described`` also words a member list the facts refute as "members" (BL-080).
        for variant in dict.fromkeys((text, _kind_true(text, fact, facts))):
            forms.add(_row_form(variant))
            forms.add(_row_form(f"{variant.rstrip().removesuffix('.')} (some members not implemented)."))
    return frozenset(forms)


def _kind_true(text: str, fact: Fact, facts: FactsDocument) -> str:
    """``text`` as ``renderer._kind_true`` words it (``surface_claims.kind_true_text``)."""
    from repo_presenter.readme.validation.surface_claims import MemberIndex, kind_true_text

    cache = getattr(_kind_true, "_cache", None)
    if cache is None or cache[0] is not facts:
        cache = (facts, MemberIndex(facts))
        _kind_true._cache = cache  # type: ignore[attr-defined]
    return kind_true_text(text, fact, facts, cache[1])


def _row_form(text: str) -> str:
    """``text`` as the fact-true comparison reads it: Markdown, case and spacing aside."""
    from repo_presenter.readme.review.matching import plain

    return " ".join(plain(text).casefold().split())


def renderer_row_descriptions(fact: Fact) -> frozenset[str]:
    """Every description the renderer prints for ``fact``'s Core API row without an author's
    sentence: the ``Public <kind>.`` label, ``Defined as `<signature>`.`` for a type with a
    signature (``renderer._described``), and the fact-true row it substitutes for a type no library
    code throws (``code_path_claims.NOT_THROWN_DESCRIPTION``). None of them is an author's claim."""
    from repo_presenter.readme.validation.code_path_claims import NOT_THROWN_DESCRIPTION

    attributes = fact.attributes or {}
    out = {f"Public {attributes.get('symbol_kind', 'symbol')}.", NOT_THROWN_DESCRIPTION}
    signature = attributes.get("signature")
    if signature:
        out.add(f"Defined as `{signature.replace('|', '/').replace(chr(96), '')}`.")
    return frozenset(out)


def authored_type_rows(
    readme: str, facts: FactsDocument, *, reviewable: bool = False
) -> dict[int, Fact]:
    """``authored_table_lines`` with the type fact each row describes: the fact whose
    ``type:<fact id>`` unit the row's description is (``renderer._symbol_description``).

    ``reviewable`` (the production review's scope, ``authored_table_lines``) leaves out a row whose
    description is the renderer's own fact-true row for its type (``fact_true_row_forms``, BL-560); the
    default keeps it, because the independent audit shows every row and needs each row's type facts."""
    from repo_presenter.readme.composition.renderer import api_reference_names

    names = api_reference_names(facts)
    authored_types: dict[str, Fact] = {}
    fallbacks: dict[str, frozenset[str]] = {}
    doc_comments: dict[str, str] = {}
    for fact in facts.by_kind("public_symbol"):
        attributes = fact.attributes or {}
        kind = attributes.get("symbol_kind")
        if fact.polarity != "SUPPORTED" or kind not in {"class", "enum"}:
            continue
        if attributes.get("docstring"):
            continue
        name = names.get(fact.value, fact.value.rsplit(".", 1)[-1])
        authored_types.setdefault(name, fact)
        fallbacks[name] = renderer_row_descriptions(fact)
        full = attributes.get("docstring_full")
        if full:
            doc_comments.setdefault(name, _row_form(str(full)))
    if not authored_types:
        return {}
    owners = section_lines(readme)
    found: dict[int, Fact] = {}
    true_forms: dict[str, frozenset[str]] = {}
    for number, row in enumerate(readme.splitlines(), 1):
        if owners[number - 1] != "api_reference":
            continue
        match = _TYPE_ROW.match(row.strip())
        if match is None or match.group(1) not in authored_types:
            continue
        description = match.group(2).strip()
        if description and description not in fallbacks[match.group(1)]:
            # BL-700: a row that prints the type's own doc comment word for word (the SUPPORTED fact's
            # ``docstring_full``, which the source extractors record when no first-sentence ``docstring`` is
            # kept: every TypeScript type) is the source's text, not a sentence an author wrote. PDF TypeScript's
            # preserved API table rows for ``MdLink`` and ``MdTable`` were judged as author claims in the audit and
            # not derivable. A row an author or a seed changed no longer equals the doc comment and stays authored.
            if _row_form(description.replace("\\|", "|")) == doc_comments.get(match.group(1)):
                continue
            if reviewable:
                fact = authored_types[match.group(1)]
                if fact.id not in true_forms:
                    true_forms[fact.id] = fact_true_row_forms(fact, facts)
                if _row_form(description) in true_forms[fact.id]:
                    continue
            found[number] = authored_types[match.group(1)]
    return found


def changed_type_rows(
    readme: str, facts: FactsDocument, changed: Collection[int]
) -> dict[int, Fact]:
    """The type fact each CHANGED API reference table row describes (BL-870, Lane L review scope).

    A Lane L correction writes a row's description itself (``type_description``: the shared
    describer's "Class that inherits from X and declares the methods A and B.", derived from the type's
    SUPPORTED member facts). ``authored_type_rows`` only knows the rows an author wrote for a type with
    no docstring in a RENDERED candidate, so the review of a corrected live README showed the reviewer
    the rewritten rows with none of the member facts they restate, and the reviewer faulted eleven true
    rows as unsupported (hosted Lane L PDF Cpp run 45007577791: "no fact supports Icon"; the facts hold
    ``SoundAnnotation.Icon``). A changed row is resolved by its type name, exactly as the renderer's own
    api_reference names resolve (``api_reference_names``); a name that is not one SUPPORTED class or enum
    is not a row of this table and is left out."""
    from repo_presenter.readme.composition.renderer import api_reference_names

    wanted = set(changed)
    if not wanted:
        return {}
    names = api_reference_names(facts)
    types: dict[str, Fact] = {}
    for fact in facts.by_kind("public_symbol"):
        if fact.polarity != "SUPPORTED" or (fact.attributes or {}).get("symbol_kind") not in {"class", "enum"}:
            continue
        types.setdefault(names.get(fact.value, fact.value.rsplit(".", 1)[-1]), fact)
    owners = section_lines(readme)
    found: dict[int, Fact] = {}
    for number, row in enumerate(readme.splitlines(), 1):
        if number not in wanted or owners[number - 1] != "api_reference":
            continue
        match = _TYPE_ROW.match(row.strip())
        if match is not None and match.group(1) in types:
            found[number] = types[match.group(1)]
    return found


def derived_type_rows(
    readme: str, facts: FactsDocument, changed: Collection[int]
) -> frozenset[int]:
    """The CHANGED API reference rows whose description is exactly the shared describer's fact-true
    text for their type (BL-897; ``fact_true_row_forms``).

    A Lane L correction (``type_description``) writes "Class that inherits from X and declares the
    methods A and B." with the same ``TypeDescriber`` the renderer prints Core API rows with. BL-560
    already holds that text is the project's own derivation from SUPPORTED facts, not an author's
    claim, and does not review it in Lane R. The Lane L review had no such rule: hosted PDF Cpp
    run 45337643264 (BL-870 member facts already shown) still faulted 8 of the 118 rewritten rows
    ("no fact supports this inheritance"; the packet carries a type's member names, never its bases,
    which the describer derives from the declaration), a different 8 of the same class each round.
    A row that is ANY other text (a maintainer's sentence, an edit's other wording) is not equal to the
    describer's text and stays reviewed; the deterministic validators judge the row either way."""
    rows = changed_type_rows(readme, facts, changed)
    if not rows:
        return frozenset()
    from repo_presenter.readme.correction.detectors.type_description import _NOUNS

    nouns = tuple(dict.fromkeys(_NOUNS.values()))
    lines = readme.splitlines()
    true_forms: dict[str, frozenset[str]] = {}
    found: set[int] = set()
    for number, fact in rows.items():
        match = _TYPE_ROW.match(lines[number - 1].strip())
        if match is None:
            continue
        if fact.id not in true_forms:
            true_forms[fact.id] = fact_true_row_forms(fact, facts, nouns)
        form = _row_form(match.group(2).strip())
        if form and form != "not implemented." and form in true_forms[fact.id]:
            found.add(number)
    return frozenset(found)


def line_sections(
    readme: str, rendered: bool = True, authored: Collection[int] = (), *, headings: bool = False
) -> list[str | None]:
    """For each line (0-based), the section whose author-written prose it is, or ``None`` when the
    line is not reviewable text.

    ``rendered`` says the candidate was printed by this project's renderer (Lane R), which owns the
    deterministic sections, the diagram, the member reference and the sentences ``shown_text``
    removes. A corrected live README (Lane L) was written by the maintainers: nothing in it is the
    renderer's, so with ``rendered=False`` only Markdown that is never prose (fences, headings, HTML,
    images, horizontal rules, a table's header and delimiter rows) is withheld; a table's body rows
    are the maintainers' text and are shown, and sections are still named.

    ``authored`` (1-based, ``authored_table_lines``) are rows of a renderer-printed table whose cell
    an author wrote; they are reviewable in a rendered candidate too.

    ``headings`` (the M9 blind auditor only, ``scripts/run_m9_auditor.py``) makes a heading line
    reviewable too. The auditor's question is whether a defect sits anywhere in the document, and a
    sentence written onto the title line is prose the reader sees: the 2026-11-13 hosted round
    43445578226 missed all 11 of its D/D14 seeds because the seed operators append to the first
    paragraph, which is the ``# Title`` line, and a heading was never shown. Every other caller keeps
    the default, so its units and request hashes are unchanged byte for byte."""
    rows = readme.splitlines()
    owners = section_lines(readme)
    first = _first_heading(rows)
    classified: list[str | None] = []
    inside = False
    extra = set(authored)
    for index, row in enumerate(rows):
        stripped = row.strip()
        if _FENCE.match(row):
            inside = not inside
            classified.append(None)
            continue
        if inside or not stripped:
            classified.append(None)
            continue
        if rendered and index + 1 in extra:
            classified.append(owners[index] or STRUCTURE)
            continue
        heading = headings and stripped.startswith("#")
        if heading and not rendered:
            classified.append(OPENING if first is None or index < first else owners[index] or STRUCTURE)
            continue
        if _is_markup(stripped) and not heading and (rendered or not _table_data_row(rows, index)):
            classified.append(None)
            continue
        if rendered and not shown_text(stripped):
            classified.append(None)
            continue
        if first is None or index < first:
            section: str | None = OPENING
        else:
            section = owners[index] or STRUCTURE
        if rendered and (
            section in RENDERER_SECTIONS or _member_bullet(stripped, section)
        ):
            classified.append(None)
        else:
            classified.append(section)
    return classified


def reviewable_lines(readme: str, rendered: bool = True) -> tuple[int, ...]:
    """The 1-based numbers of the lines a reviewer may be shown and may cite, ascending."""
    return tuple(
        number
        for number, section in enumerate(line_sections(readme, rendered), 1)
        if section is not None
    )


def section_of_line(readme: str, number: int, rendered: bool = True) -> str | None:
    """The section a reviewable line belongs to, or ``None`` for a line that is not reviewable."""
    classified = line_sections(readme, rendered)
    return classified[number - 1] if 1 <= number <= len(classified) else None


#: BL-890: the disposition section whose kept-verbatim maintainers' sentences are the maintainers' statement of
#: what the library does not do or how it behaves at its edges.
LIMITS_SECTION = "scope_limitations"
#: The only fact kind a ``VERIFIED_*`` disposition may cite for :func:`maintainer_lines` to treat its unit as
#: unverified maintainer text: a public symbol proves that the NAME exists, never what the sentence says of it.
NAME_EXISTENCE_KINDS = frozenset({"public_symbol"})


def _limits_verified_by_names_only(row: Mapping[str, Any], kinds: Mapping[str, str]) -> bool:
    """BL-890: a maintainers' scope-limitation unit kept verbatim (``VERIFIED_PRESERVE`` / ``VERIFIED_MOVE``
    into ``scope_limitations``) whose cited facts prove only that the symbols it names exist. Its sentences
    about behaviour (``Stream payloads are not decoded on open``, ``Reader neither recomputes nor draws these
    barcodes``) are no fact's to support, so the model review kept filing ``unsupported_claim`` on them, each
    draw naming different bullets (hosted PDF TypeScript run 45040357304: four findings on three such units
    after four degrade passes, nothing sealed). They are the maintainers' unverified statements of limit,
    "unverified, not false" (docs/MAINTAINER_CONTENT_PRESERVATION.md, R36(a)(2)), so the maintainer-line
    contract judges them. A unit that cites any other fact kind (an example, a dependency, a command)
    keeps the full review, as does a unit outside this section; a CONTRADICTED fact removes the exemption
    in :func:`maintainer_lines` exactly as for ``PRESERVE_ATTRIBUTED``."""
    return (
        row.get("disposition") in ("VERIFIED_PRESERVE", "VERIFIED_MOVE")
        and row.get("destination_section") == LIMITS_SECTION
        and all(kinds.get(str(fact_id)) in NAME_EXISTENCE_KINDS for fact_id in row.get("fact_ids") or ())
    )


def maintainer_lines(
    readme: str, facts: FactsDocument, dispositions: Mapping[str, Any]
) -> frozenset[int]:
    """The 1-based numbers of the candidate lines that are attributed maintainer text: a line whose
    stripped text is a stripped line of an inherited unit reconciliation kept as
    ``PRESERVE_ATTRIBUTED`` (docs/MAINTAINER_CONTENT_PRESERVATION.md). Like ``reviewable_lines`` it
    reads only structure, never meaning: it matches the unit's own lines, so a kept line the
    renderer changed (an anchor it resolved) is not marked and stays judged like authored text.

    The exemption holds only while no fact contradicts the text (DECISION_LOG 2026-11-06, "reviewer
    rule for inherited text"; reviewer logic 10): a unit whose own fact is CONTRADICTED, or whose
    disposition cites a CONTRADICTED fact, marks no line, and a line holding the value of a
    CONTRADICTED product fact is not marked. Such text is judged like generated text, so a finding
    on it stands. Inherited text kept verbatim without the attribution (``VERIFIED_PRESERVE``,
    ``VERIFIED_MOVE``) is never marked either.

    A corrected live README (Lane L, ``rendered=False``) is reviewed without S4 dispositions, so it
    has no ``PRESERVE_ATTRIBUTED`` unit and this set is empty there: nothing changes for Lane L."""
    contradicted = {fact.id: fact for fact in facts.facts if fact.polarity == "CONTRADICTED"}
    kinds = {fact.id: fact.kind for fact in facts.facts}
    kept = {
        str(row.get("unit_id", ""))
        for row in dispositions.get("dispositions", [])
        if isinstance(row, Mapping)
        and not any(str(fact_id) in contradicted for fact_id in row.get("fact_ids") or ())
        and (row.get("disposition") == ATTRIBUTED or _limits_verified_by_names_only(row, kinds))
    }
    if not kept:
        return frozenset()
    texts = {
        line.strip()
        for fact in facts.by_kind("inherited_unit")
        if fact.id in kept and fact.polarity != "CONTRADICTED"
        for line in fact.value.splitlines()
        if line.strip()
    }
    refuted = [fact.value for fact in contradicted.values() if fact.kind != "inherited_unit"]
    return frozenset(
        number
        for number, row in enumerate(readme.splitlines(), 1)
        if row.strip()
        and row.strip() in texts
        and not any(present(value, row) for value in refuted)
    )
