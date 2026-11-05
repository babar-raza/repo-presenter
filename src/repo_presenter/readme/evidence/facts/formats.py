"""``format`` facts: the extensions the product reads or writes, corroborated two ways.

A format claim lives in an example's code and the platform plugin reads it from the syntax tree;
an extension an executed example loaded or saved is SUPPORTED, and a repository file staged for an
executed example proves its extension as input. A claim no executed example makes is SUPPORTED
only when two independent static sources agree: the product's format declarations state the
extension and a registered, non-stub importer or exporter implements that direction. One source
alone, or a failed or unverified example alone, leaves the fact UNRESOLVED; nothing is inferred
from prose. Direction is part of the ID: ``format:input.obj``, ``format:output.stl``.

Ported (REUSE, near-verbatim) from the old repository-presenter project's
``evidence/facts/formats.py`` per migration/reuse-manifest.yaml.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from repo_presenter.core.examples import (
    ExampleCandidate,
    ExampleOutcome,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
)
from repo_presenter.core.facts import Evidence, Fact, fact_id

#: ``.htm``/``.html`` name the same format everywhere this tool has measured: every real HTML
#: parser/writer treats them identically, even when a product's own source only ever spells the
#: literal string ``"html"`` (never also ``"htm"``) in its own format-dispatch code -- the one
#: alias this module may assert without a claim or a static source naming it, because it is a
#: deterministic fact about file extensions, not an inference from README prose.
_HTM_HTML_ALIAS = ".htm"
_HTM_HTML_CANONICAL = ".html"


def _htm_alias_facts(facts: Sequence[Fact], evidence: dict[tuple[str, str], list[Evidence]]) -> list[Fact]:
    """A SUPPORTED ``.htm`` fact for each direction whose ``.html`` fact is SUPPORTED, unless a
    fact already exists for ``.htm`` in that direction (real evidence is never overwritten).

    Measured live (aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript, run in the ninth cascade this
    session's history records): the README correctly claims both ``.html`` and ``.htm`` are
    recognized, but the extractor only ever confirmed ``.html`` -- the product's own source
    literally compares against ``"html"``, never also ``"htm"`` -- so format_overclaim held the
    candidate open as an unrepairable Lane R defect for a true, safe claim. ``.htm``/``.html`` are
    the same format everywhere; this fold is a deterministic extension-alias rule, not a guess
    from unverified prose, and never applies in the other direction (a SUPPORTED ``.htm`` fact
    never implies ``.html``, since no real product has been measured declaring ``.htm`` alone).
    """
    aliases: list[Fact] = []
    for fact in facts:
        if fact.value != _HTM_HTML_CANONICAL or fact.polarity != "SUPPORTED":
            continue
        direction = fact.id.split(".", 1)[0].removeprefix("format:")
        if (direction, _HTM_HTML_ALIAS) in evidence:
            continue
        aliases.append(
            Fact(
                fact_id("format", direction, _HTM_HTML_ALIAS.lstrip(".")),
                "format",
                _HTM_HTML_ALIAS,
                (Evidence(fact.evidence[0].path, f"alias of {fact.id} ({_HTM_HTML_CANONICAL})"),),
                polarity="SUPPORTED",
                confidence=fact.confidence,
            )
        )
    return aliases


def format_facts(
    candidates: Sequence[ExampleCandidate],
    receipts: Sequence[ExampleReceipt],
    claims_for: Callable[[str], Sequence[FormatClaim]],
    receipts_path: str,
    declarations: Sequence[FormatDeclaration] = (),
) -> list[Fact]:
    """One fact per (direction, extension) across the examples and the static sources."""
    by_ordinal = {receipt.ordinal: receipt for receipt in receipts}
    evidence: dict[tuple[str, str], list[Evidence]] = {}
    executed: set[tuple[str, str]] = set()
    for candidate in candidates:
        receipt = by_ordinal.get(candidate.ordinal)
        outcome: ExampleOutcome = receipt.outcome if receipt else "NOT_VERIFIED"
        detail = receipt.detail if receipt else "no verification receipt"
        claimed_directions: dict[str, set[str]] = {}
        claims = list(claims_for(candidate.code))
        for claim in claims:
            key: tuple[str, str] = (claim.direction, claim.extension)
            line = candidate.start_line + claim.line
            evidence.setdefault(key, []).extend(
                (
                    Evidence(
                        candidate.source_path,
                        f"line {line}; example {candidate.ordinal}: {claim.direction} "
                        f"{claim.extension}",
                    ),
                    Evidence(receipts_path, f"example {candidate.ordinal}: {outcome}; {detail}"),
                )
            )
            if outcome == "EXECUTED":
                executed.add(key)
            claimed_directions.setdefault(claim.extension, set()).add(claim.direction)
        if receipt is None or outcome != "EXECUTED":
            continue
        for binding in receipt.fixtures:
            extension = Path(binding.literal).suffix.lower()
            if not extension:
                continue
            if "output" in claimed_directions.get(extension, ()):
                saved = {
                    literal
                    for claim in claims
                    if claim.direction == "output" and claim.extension == extension
                    for literal in claim.literals
                }
                if not saved or binding.literal in saved:
                    continue
            key = ("input", extension)
            evidence.setdefault(key, []).append(
                Evidence(
                    binding.source_path,
                    f"staged as {binding.literal}; example {candidate.ordinal} read it: EXECUTED",
                )
            )
            executed.add(key)
    declared: dict[str, list[FormatDeclaration]] = {}
    registered: dict[tuple[str, str], list[FormatDeclaration]] = {}
    for declaration in declarations:
        if declaration.kind == "declaration":
            declared.setdefault(declaration.extension, []).append(declaration)
        elif declaration.direction is not None:
            registered.setdefault((declaration.direction, declaration.extension), []).append(
                declaration
            )
    corroborated: set[tuple[str, str]] = set()
    for key, registrations in sorted(registered.items()):
        direction, extension = key
        entries = evidence.setdefault(key, [])
        for statement in declared.get(extension, []):
            entries.append(
                Evidence(statement.source_path, f"line {statement.line}; {statement.detail}")
            )
        for registration in registrations:
            entries.append(
                Evidence(
                    registration.source_path, f"line {registration.line}; {registration.detail}"
                )
            )
        if extension in declared:
            corroborated.add(key)
    supported = executed | corroborated
    facts: list[Fact] = []
    for key in sorted(evidence):
        direction, extension = key
        facts.append(
            Fact(
                fact_id("format", direction, extension.lstrip(".")),
                "format",
                extension,
                tuple(evidence[key]),
                polarity="SUPPORTED" if key in supported else "UNRESOLVED",
                confidence=1.0 if key in supported else 0.5,
            )
        )
    facts.extend(_htm_alias_facts(facts, evidence))
    return facts


#: An enum whose name says which way its members go (``SaveFormat`` members are formats the API
#: writes, ``LoadFormat`` members formats it reads). A neutral ``FileFormat``-style enum says neither
#: and is not read: a declaration of a format is not a statement of its direction.
_OUTPUT_ENUM = re.compile(r"(?:Save|Export|Write|Output)(?:Format|FileFormat|Type)s?$")
_INPUT_ENUM = re.compile(r"(?:Load|Import|Read|Input|Open)(?:Format|FileFormat|Type)s?$")
_EXTENSION_MEMBER = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,5}$")
#: Members that name a behaviour, not a format.
_NOT_A_FORMAT = frozenset(
    {"auto", "unknown", "default", "none", "detect", "any", "all", "custom", "other", "native",
     "max", "min", "count", "invalid", "undefined", "notset"}
)


def declared_format_facts(facts: Sequence[Fact]) -> list[Fact]:
    """UNRESOLVED format facts for the formats a directional format enum declares (owner decision
    2026-11-05: declared is not working -- Aspose.3D for Java declares about 30 formats and
    handles 4 -- so a declaration never makes a format SUPPORTED; that still takes an executed
    example or a corroborated dispatch path). Added only where no format fact of that direction and
    extension exists, so an executed or contradicted one is never touched. Read from the
    ``enum_member`` facts (``SaveFormat.Pdf`` -> output ``.pdf``)."""
    existing = {f.id for f in facts if f.kind == "format"}
    found: dict[str, list[Evidence]] = {}
    for fact in facts:
        if fact.kind != "enum_member":
            continue
        enum = str((fact.attributes or {}).get("enum", ""))
        enum_name = enum.rsplit(".", 1)[-1]
        if _OUTPUT_ENUM.search(enum_name):
            direction = "output"
        elif _INPUT_ENUM.search(enum_name):
            direction = "input"
        else:
            continue
        member = fact.value.rsplit(".", 1)[-1]
        if not _EXTENSION_MEMBER.match(member) or member.lower() in _NOT_A_FORMAT:
            continue
        extension = "." + member.lower()
        identifier = fact_id("format", direction, extension.lstrip("."))
        if identifier in existing:
            continue
        found.setdefault(identifier, []).append(
            Evidence(
                fact.evidence[0].path if fact.evidence else "",
                f"declared by {enum} member {member}; declared is not verified",
            )
        )
    return [
        Fact(
            identifier,
            "format",
            "." + identifier.rsplit(".", 1)[-1],
            tuple(evidence),
            polarity="UNRESOLVED",
            confidence=0.5,
            attributes={"source": "enum_declaration"},
        )
        for identifier, evidence in sorted(found.items())
    ]
