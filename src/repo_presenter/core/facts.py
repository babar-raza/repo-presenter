"""Typed fact records: the deterministic evidence every README claim binds to.

A fact is ``{id, kind, value, evidence[], polarity, confidence}``. IDs are stable and
unique within a document (``<kind>:<slug>``), evidence names the repository paths that
support the value, and the document is written with sorted keys and sorted records so
the same revision always produces the same bytes.

Ported (REUSE, near-verbatim) from the old repository-presenter project's
``core/facts.py`` per migration/reuse-manifest.yaml -- small, self-contained, no
entanglement beyond stdlib. This is the shared data model both Lane L (readme
correction) and Lane R (full composition) consume; the extraction layer is the
only producer. See migration/reuse-manifest.yaml for the disposition record.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, get_args

FactKind = Literal[
    "identity",
    "package",
    "install_command",
    "import_path",
    "public_symbol",
    "example",
    "format",
    "capability",
    "dependency",
    "license",
    "third_party_notices",
    "build_test_asset",
    "link_target",
    "inherited_unit",
]
Polarity = Literal["SUPPORTED", "CONTRADICTED", "UNRESOLVED"]
FACT_KINDS: tuple[str, ...] = get_args(FactKind)
POLARITIES: tuple[str, ...] = get_args(Polarity)
FACTS_FILENAME = "facts.json"
REPOSITORY_FILES_ATTRIBUTE = "repository_files"
SOURCE_CHECKOUT_COMMAND_ATTRIBUTE = "source_checkout_command"
SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE = "source_checkout_unverified"
REGISTRY_STATE_ATTRIBUTE = "registry_state"
NOT_PUBLISHED = "not_published"
REGISTRY_COMMAND_ATTRIBUTE = "registry_command"
SOURCE_BASIS_ATTRIBUTE = "source_basis"
DOCUMENTED_SOURCE_BASIS = "documented"
DOCUMENTED_COMMAND_ATTRIBUTE = "documented_command"

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_UNSAFE = re.compile(r"[^a-z0-9._-]+")
_SEPARATOR_RUN = re.compile(r"[._-]{2,}")


def slug(text: str) -> str:
    """A lowercase identifier-safe form of ``text`` for use inside a fact ID."""
    cleaned = _UNSAFE.sub("-", text.strip().lower()).strip("._-")
    cleaned = _SEPARATOR_RUN.sub(lambda match: match.group(0)[0], cleaned)
    if not cleaned or not _SLUG_PATTERN.fullmatch(cleaned):
        raise ValueError(f"cannot derive a fact ID slug from {text!r}")
    return cleaned


def fact_id(kind: FactKind, *parts: str) -> str:
    """Compose ``<kind>:<slug>[.<slug>...]``."""
    if not parts:
        raise ValueError("a fact ID needs at least one part")
    return f"{kind}:" + ".".join(slug(part) for part in parts)


@dataclass(frozen=True)
class Evidence:
    """One repository path that supports a fact, with an optional locator or note."""

    path: str
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("evidence needs a path")


@dataclass(frozen=True)
class Fact:
    """One deterministic claim about the repository at its pinned revision."""

    id: str
    kind: FactKind
    value: str
    evidence: tuple[Evidence, ...]
    polarity: Polarity = "SUPPORTED"
    confidence: float = 1.0
    attributes: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.kind not in FACT_KINDS:
            raise ValueError(f"unknown fact kind {self.kind!r}")
        if not self.id.startswith(f"{self.kind}:") or not _SLUG_PATTERN.fullmatch(
            self.id[len(self.kind) + 1 :]
        ):
            raise ValueError(f"fact ID {self.id!r} must be <kind>:<slug> for kind {self.kind!r}")
        if not self.value:
            raise ValueError(f"fact {self.id} has an empty value")
        if not self.evidence:
            raise ValueError(f"fact {self.id} carries no evidence")
        if self.polarity not in POLARITIES:
            raise ValueError(f"fact {self.id} has unknown polarity {self.polarity!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"fact {self.id} confidence must be between 0 and 1")
        if self.attributes is not None and not all(
            isinstance(k, str) and isinstance(v, str) and k and v
            for k, v in self.attributes.items()
        ):
            raise ValueError(f"fact {self.id} attributes must map non-empty strings to strings")


@dataclass(frozen=True)
class FactsDocument:
    """Every fact extracted for one repository at one revision."""

    repository: str
    source_revision: str
    facts: tuple[Fact, ...]
    schema_version: int = field(default=1)

    def __post_init__(self) -> None:
        ids = [fact.id for fact in self.facts]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate fact IDs: {duplicates}")

    def by_kind(self, kind: FactKind) -> tuple[Fact, ...]:
        return tuple(fact for fact in self.facts if fact.kind == kind)

    def canonical(self) -> FactsDocument:
        """The same document with its facts in ID order: the one order a bundle stores
        (``to_json``) and the renderer reads, so a candidate renders the same bytes live
        and again from its own ``facts.json``.
        """
        return FactsDocument(
            self.repository,
            self.source_revision,
            tuple(sorted(self.facts, key=lambda fact: fact.id)),
            self.schema_version,
        )

    def to_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "source_revision": self.source_revision,
            "facts": [asdict(fact) for fact in self.canonical().facts],
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


SYMBOL_MAX_DEPTH = 3
SYMBOL_CAP = 6000
LINK_CAP = 100
EXAMPLE_CAP = 30

_EXCLUDED_FROM_PACKETS = frozenset({"identity:revision"})

DECLARED_SYMBOL_KINDS = frozenset({"module", "class", "enum", "function"})


def _admits_symbol(fact: Fact, symbol_kinds: Collection[str] | None, symbol_max_depth: int) -> bool:
    """Whether one ``public_symbol`` fact enters a packet, before the cap is applied."""
    recorded = (fact.attributes or {}).get("symbol_kind")
    if symbol_kinds is not None and recorded not in (None, "", "unknown"):
        return recorded in symbol_kinds
    return fact.value.count(".") < symbol_max_depth


def bounded_records(
    document: FactsDocument,
    kinds: Iterable[str],
    polarities: Iterable[str] = ("SUPPORTED",),
    *,
    symbol_max_depth: int = SYMBOL_MAX_DEPTH,
    symbol_cap: int = SYMBOL_CAP,
    symbol_kinds: Collection[str] | None = None,
    link_cap: int = LINK_CAP,
    example_cap: int = EXAMPLE_CAP,
) -> list[dict[str, str]]:
    """Facts of ``kinds`` and ``polarities`` as packet records, with public symbols,
    links, and examples all bounded so a job's packet stays bounded however large the
    repository's own surface, link count, or example count is.
    """
    admitted_kinds = set(kinds)
    admitted_polarities = set(polarities)
    records: list[dict[str, str]] = []
    symbols = 0
    links = 0
    examples = 0
    for fact in document.facts:
        if fact.id in _EXCLUDED_FROM_PACKETS:
            continue
        if fact.kind not in admitted_kinds or fact.polarity not in admitted_polarities:
            continue
        if fact.kind == "public_symbol":
            if symbols >= symbol_cap or not _admits_symbol(fact, symbol_kinds, symbol_max_depth):
                continue
            symbols += 1
        elif fact.kind == "link_target":
            if links >= link_cap:
                continue
            links += 1
        elif fact.kind == "example":
            if examples >= example_cap:
                continue
            examples += 1
        record = {"id": fact.id, "kind": fact.kind, "value": fact.value}
        if admitted_polarities != {"SUPPORTED"}:
            record["polarity"] = fact.polarity
        records.append(record)
    return records


def write_facts(document: FactsDocument, path: Path) -> str:
    """Write ``facts.json`` and return the SHA-256 of its bytes."""
    data = document.to_json().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_facts(path: Path) -> FactsDocument:
    """Parse a ``facts.json`` written by :func:`write_facts` back into a :class:`FactsDocument`."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    facts = tuple(
        Fact(
            id=record["id"],
            kind=record["kind"],
            value=record["value"],
            evidence=tuple(
                Evidence(item["path"], item.get("detail")) for item in record["evidence"]
            ),
            polarity=record.get("polarity", "SUPPORTED"),
            confidence=record.get("confidence", 1.0),
            attributes=record.get("attributes"),
        )
        for record in payload["facts"]
    )
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=facts,
        schema_version=payload.get("schema_version", 1),
    )
