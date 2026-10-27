"""The facts artifact that crosses the hosted trust boundary between the two ``present`` jobs.

The ``facts`` job executes untrusted repository code (example builds) and therefore holds no
secrets; the ``present`` job holds the provider key and the write-scoped state token and executes no
repository code. What crosses between them is ``facts.json`` plus a small manifest naming the
repository, ecosystem, pinned revision and the SHA-256 of the facts bytes. The ``present`` job treats
both files as hostile input: it never executes them, it checks the manifest and the digest, and it
validates the facts through :func:`repo_presenter.core.facts.read_facts` plus the shape checks here
before any provider call is made.

The digest detects corruption or substitution in transit (and a mismatch with the digest the facts
job published as a job output); it cannot make a facts file from a compromised facts job trustworthy,
which is why the content is validated and why the consuming job holds the only authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from pathlib import Path

from repo_presenter.core.errors import PresenterError
from repo_presenter.core.facts import (
    FACTS_FILENAME,
    FactsDocument,
    read_facts,
    write_facts,
)

MANIFEST_FILENAME = "facts-manifest.json"
MAX_FACTS_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024
SUPPORTED_SCHEMA_VERSION = 1

_REVISION = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_MANIFEST_KEYS = frozenset(
    {"repository", "ecosystem", "source_revision", "facts_sha256"}
)


class FactsHandoffError(PresenterError):
    """The facts artifact is missing, tampered with, mismatched, or malformed; refused."""

    exit_code = 3


@dataclass(frozen=True)
class FactsManifest:
    repository: str
    ecosystem: str
    source_revision: str
    facts_sha256: str


def write_handoff(
    document: FactsDocument, ecosystem: str, directory: Path
) -> FactsManifest:
    """Write ``facts.json`` and its manifest under ``directory``; returns the manifest."""
    digest = write_facts(document, directory / FACTS_FILENAME)
    manifest = FactsManifest(
        document.repository, ecosystem, document.source_revision, digest
    )
    payload = {
        "repository": manifest.repository,
        "ecosystem": manifest.ecosystem,
        "source_revision": manifest.source_revision,
        "facts_sha256": manifest.facts_sha256,
    }
    (directory / MANIFEST_FILENAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _read_bounded(path: Path, limit: int, what: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise FactsHandoffError(f"{what} is missing or not a regular file: {path}")
    if path.stat().st_size > limit:
        raise FactsHandoffError(f"{what} exceeds {limit} bytes: {path}")
    return path.read_bytes()


def _read_manifest(path: Path) -> FactsManifest:
    raw = _read_bounded(path, MAX_MANIFEST_BYTES, "facts manifest")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise FactsHandoffError(f"facts manifest is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _MANIFEST_KEYS:
        raise FactsHandoffError(
            f"facts manifest must carry exactly {sorted(_MANIFEST_KEYS)}"
        )
    if not all(isinstance(value, str) for value in payload.values()):
        raise FactsHandoffError("facts manifest values must all be strings")
    if not _REVISION.fullmatch(payload["source_revision"]):
        raise FactsHandoffError(
            "facts manifest source_revision is not a 40-hex revision"
        )
    if not _DIGEST.fullmatch(payload["facts_sha256"]):
        raise FactsHandoffError("facts manifest facts_sha256 is not a 64-hex digest")
    return FactsManifest(
        payload["repository"],
        payload["ecosystem"],
        payload["source_revision"],
        payload["facts_sha256"],
    )


def _require_wellformed(document: FactsDocument) -> None:
    """Shape checks ``read_facts`` does not make: string-typed fields and repository-relative
    evidence paths (a facts file is data, but its evidence paths name files in the clone)."""
    if document.schema_version != SUPPORTED_SCHEMA_VERSION:
        raise FactsHandoffError(
            f"unsupported facts schema_version {document.schema_version!r}"
        )
    for fact in document.facts:
        if not (isinstance(fact.id, str) and isinstance(fact.value, str)):
            raise FactsHandoffError(f"fact {fact.id!r} has a non-string id or value")
        if isinstance(fact.confidence, bool) or not isinstance(
            fact.confidence, (int, float)
        ):
            raise FactsHandoffError(f"fact {fact.id} confidence is not a number")
        for item in fact.evidence:
            if not isinstance(item.path, str) or (
                item.detail is not None and not isinstance(item.detail, str)
            ):
                raise FactsHandoffError(f"fact {fact.id} has non-string evidence")
            if (
                "\x00" in item.path
                or item.path.startswith(("/", "\\"))
                or re.match(r"^[A-Za-z]:", item.path)
                or ".." in re.split(r"[\\/]", item.path)
            ):
                raise FactsHandoffError(
                    f"fact {fact.id} has an evidence path outside the repository: {item.path!r}"
                )


def load_handoff(
    directory: Path,
    *,
    repository: str,
    ecosystem: str,
    expected_sha256: str | None = None,
) -> tuple[FactsManifest, FactsDocument]:
    """Verify and parse the facts artifact in ``directory``; every mismatch fails closed.

    Checks, in order: the manifest is present and well formed and names ``repository`` and
    ``ecosystem``; ``expected_sha256`` (the digest the facts job published out of band), when given,
    equals the manifest's; the facts bytes hash to the manifest digest; the facts parse and validate;
    and the document names the same repository and revision as the manifest.
    """
    manifest = _read_manifest(directory / MANIFEST_FILENAME)
    if manifest.repository != repository or manifest.ecosystem != ecosystem:
        raise FactsHandoffError(
            f"facts manifest is for {manifest.repository} ({manifest.ecosystem}), "
            f"not {repository} ({ecosystem})"
        )
    if expected_sha256 is not None and not hmac.compare_digest(
        expected_sha256.lower(), manifest.facts_sha256
    ):
        raise FactsHandoffError(
            "facts manifest digest differs from the digest the facts job published"
        )
    facts_path = directory / FACTS_FILENAME
    data = _read_bounded(facts_path, MAX_FACTS_BYTES, "facts.json")
    actual = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(actual, manifest.facts_sha256):
        raise FactsHandoffError(
            f"facts.json sha256 {actual} does not match the manifest's {manifest.facts_sha256}"
        )
    try:
        document = read_facts(facts_path)
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise FactsHandoffError(f"facts.json failed validation: {exc}") from exc
    if (
        document.repository != repository
        or document.source_revision != manifest.source_revision
    ):
        raise FactsHandoffError(
            f"facts.json names {document.repository}@{document.source_revision}, the manifest "
            f"{repository}@{manifest.source_revision}"
        )
    _require_wellformed(document)
    return manifest, document
