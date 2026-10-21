"""The consumed-scope recheck: is a sealed candidate still current under the running code?

PARTIAL PORT (see migration/reuse-manifest.yaml, "readme/bundle/recheck.py + evaluation.py +
invalidation.py"). The old repository-presenter's ``components/readme/bundle/recheck.py`` is
1005 lines; this file ports the currency-state data model, the classification rule, the receipt
cache mechanics and the patch round-trip -- every piece that is genuinely self-contained -- but
does NOT port ``recheck_bundle`` / ``recheck_portfolio`` and the five per-scope runners
(``_recheck_presentation`` / ``_recheck_authoring`` / ``_recheck_validator`` /
``_recheck_reviewer`` / ``_recheck_extraction``), because those transitively require modules this
repository has not pulled yet and that have no disposition of their own in
migration/reuse-manifest.yaml:

- ``core/candidates.py`` (the sealed-bundle manifest format, ``verify_bundle``, ``BundleError``,
  directory conventions ``CANDIDATES_DIRNAME``/``CURRENT_FILENAME``/``DEPENDENCIES_FILENAME``)
- ``core/registry/`` (``RegistryEntry``, ``load_registry``, ``find_entry``)
- ``core/llm/prompts.py`` (``PromptRegistry``, ``load_manifests``)
- ``components/readme/composition/authoring.py`` and the rest of ``renderer.py`` (only
  ``render_patch`` is small and self-contained enough to port here, see below)
- ``components/readme/evidence/facts/inherited.py``, ``extractors/platforms/registry.py``
- ``components/readme/review/independent/review.py``
- ``components/readme/validation/registry.py``

Porting ``recheck_bundle``/``recheck_portfolio`` faithfully would mean first porting most of the
rest of the Lane R pipeline (composition, validation, review, the bundle-storage layer) -- a much
larger task than "the bundle recheck/invalidation layer" this component is. Reproducing them as
stubs that always return UNVERIFIED would not prove anything real, so they are left out rather
than faked; new callers get a clear ``NotImplementedError`` naming the missing module instead of
a function that silently does nothing. ``evaluate()`` (evaluation.py) and ``route()``
(invalidation.py) -- the part of this layer mission §8 cares about most, the proof that a
candidate is reopened only through a fact it actually consumed -- are fully ported and tested
with no gap.

THE CURRENCY STATES (unchanged from the old module; a currency is computed beside the manifest
state, the state itself is untouched):

- ``CURRENT``: no consumed input differs from the running code.
- ``RECHECKED_CURRENT``: inputs differ and every triggered recheck passed.
- ``UPDATE_OPTIONAL``: only provenance differs - a prompt hash, the policy, a label
  (``contract_version``, ``acceptance_profile_version``). A prompt shapes how a unit was made, not
  whether it is valid, so it never stales a candidate.
- ``UPDATE_REQUIRED``: a triggered recheck failed. ``cost`` splits it for planning:
  ``rerender_only`` (only the presentation differs) versus ``recompose`` (a content gate, the
  extraction or the replayed review fails).
- ``UNVERIFIED``: a triggered recheck could not run. Conservative: it is never counted, and it
  does not count as independently accepted.

WHAT RUNS PER SCOPE (:data:`RECHECKS`, a table whose lookup miss raises, as ``scope_of`` does):
presentation / authoring / validator / reviewer / extraction / provenance -- see the old module's
own docstring (reproduced in migration/reuse-manifest.yaml and docs/MISSION_AUTHORITY.md §8) for
what each scope checks; this file carries only the table and the classification of its outcomes,
since the runners themselves are out of scope here.
"""

from __future__ import annotations

import difflib
import hashlib
import itertools
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_presenter.readme.bundle.invalidation import ScopeError

RECHECK_VERSION = "1"
RECHECKS_DIRNAME = "rechecks"
RAW_CALLS_FILENAME = "raw_calls.json"

CURRENT = "CURRENT"
RECHECKED_CURRENT = "RECHECKED_CURRENT"
UPDATE_OPTIONAL = "UPDATE_OPTIONAL"
UPDATE_REQUIRED = "UPDATE_REQUIRED"
UNVERIFIED = "UNVERIFIED"
CURRENCY_STATES: tuple[str, ...] = (
    CURRENT,
    RECHECKED_CURRENT,
    UPDATE_OPTIONAL,
    UPDATE_REQUIRED,
    UNVERIFIED,
)
# The headline counts a bundle only in these (doc 13 section 6.3). UNVERIFIED is deliberately not
# among them: a recheck that could not run is not evidence of currency.
COUNTING: frozenset[str] = frozenset({CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL})

COST_RERENDER_ONLY = "rerender_only"
COST_RECOMPOSE = "recompose"

PASSED = "PASSED"
FAILED = "FAILED"
UNVERIFIED_OUTCOME = "UNVERIFIED"
PROVENANCE = "PROVENANCE"

# dependency class -> the recheck scope it triggers. A dotted class (``components.<name>``) is
# looked up by its full name, then its family; a miss raises rather than guessing (a guessed
# recheck is a hidden policy). ``provenance`` is a scope with no recheck: it is reported, never
# judged.
RECHECKS: dict[str, str] = {
    "components.renderer": "presentation",
    "components.shell": "presentation",
    "components.normalisation": "authoring",
    "components.reviewer_logic": "reviewer",
    "validators": "validator",
    "environment.inherited_units_version": "extraction",
    "environment.extractor_version": "extraction",
    "contract_version": "provenance",
    "acceptance_profile_version": "provenance",
    "policy": "provenance",
}
RECHECK_FAMILIES: dict[str, str] = {"prompts": "provenance"}
SCOPE_ORDER: tuple[str, ...] = (
    "extraction",
    "presentation",
    "authoring",
    "validator",
    "reviewer",
    "provenance",
)

# Judges that see less than a real run does, and what they cannot see (doc 13 section 6.5).
PARTIAL_JUDGES: dict[str, str] = {
    "BC-01": "original_unavailable",
    "BC-06": "tree_approximated",
    "BC-09": "secret_scan_not_rerun",
}


def recheck_scope(dependency: str) -> str:
    """The recheck scope a changed dependency class triggers."""
    scope = RECHECKS.get(dependency)
    if scope is None:
        family, _, name = dependency.partition(".")
        if name:
            scope = RECHECK_FAMILIES.get(family)
    if scope is None:
        raise ScopeError(f"no recheck for the dependency {dependency!r}")
    return scope


@dataclass(frozen=True)
class ScopeResult:
    scope: str
    outcome: str  # PASSED, FAILED, UNVERIFIED or PROVENANCE
    triggers: tuple[str, ...]
    detail: str = ""
    failures: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "outcome": self.outcome,
            "triggers": list(self.triggers),
            "detail": self.detail,
            "failures": list(self.failures),
            "partial": list(self.partial),
        }


@dataclass(frozen=True)
class Recheck:
    """One bundle's currency, with the scopes that decided it."""

    repository_dir: str
    revision: str
    currency: str
    cost: str | None  # rerender_only or recompose, for UPDATE_REQUIRED only
    differences: tuple[str, ...]
    unrecorded: tuple[str, ...]
    scopes: tuple[ScopeResult, ...]
    key: str = ""
    cached: bool = False
    error: str | None = None  # why no recheck ran at all (integrity, unreadable record)

    @property
    def counted(self) -> bool:
        return self.currency in COUNTING

    def to_json(self) -> dict[str, Any]:
        return {
            "repository_dir": self.repository_dir,
            "revision": self.revision,
            "currency": self.currency,
            "cost": self.cost,
            "differences": list(self.differences),
            "unrecorded": list(self.unrecorded),
            "scopes": [scope.to_json() for scope in self.scopes],
            "error": self.error,
        }


def _canonical(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    """SHA-256 of a JSON-serialisable value in its canonical form.

    Inlined from the old repo's ``core/llm/ledger.py`` (a two-line function, not worth a
    dependency on the LLM call-ledger module this repository has not pulled) -- used only by
    :func:`receipt_key` below, exactly as the old module used it.
    """
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def receipt_key(manifest_sha256: str, current_code: Mapping[str, Any]) -> str:
    """The cache key of a receipt: the manifest digest, the running code's consumed inputs, and the
    recheck's own version. A receipt under any other key is not this bundle under this code."""
    return canonical_hash(
        {
            "manifest_sha256": manifest_sha256,
            "constants": dict(current_code),
            "recheck_version": RECHECK_VERSION,
        }
    )


def receipt_path(root: Path, repository_dir: str, revision: str) -> Path:
    return root / "candidates" / repository_dir / RECHECKS_DIRNAME / f"{revision}.json"


def _receipt_document(result: Recheck, manifest_sha256: str) -> dict[str, Any]:
    body = {
        "schema_version": 1,
        "recheck_version": RECHECK_VERSION,
        "key": result.key,
        "manifest_sha256": manifest_sha256,
        **result.to_json(),
    }
    return {**body, "digest": canonical_hash(body)}


def write_receipt(root: Path, result: Recheck, manifest_sha256: str) -> Path:
    """Write ``result`` as its receipt. The only file this module ever writes, and never inside the
    sealed bundle: a sibling ``rechecks/`` directory, so the manifest's inventory is untouched."""
    path = receipt_path(root, result.repository_dir, result.revision)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(_receipt_document(result, manifest_sha256)))
    return path


def read_receipt(root: Path, repository_dir: str, revision: str, key: str) -> Recheck | None:
    """The cached recheck for ``key``, or None when there is none or it cannot be trusted: absent,
    unreadable, under another key, or whose body no longer hashes to its own digest."""
    try:
        document = json.loads(receipt_path(root, repository_dir, revision).read_text("utf-8"))
        digest = document.pop("digest")
        if document.get("key") != key or digest != canonical_hash(document):
            return None
        if document["currency"] not in CURRENCY_STATES:
            return None
        return Recheck(
            repository_dir=document["repository_dir"],
            revision=document["revision"],
            currency=document["currency"],
            cost=document["cost"],
            differences=tuple(document["differences"]),
            unrecorded=tuple(document["unrecorded"]),
            scopes=tuple(
                ScopeResult(
                    row["scope"],
                    row["outcome"],
                    tuple(row["triggers"]),
                    row["detail"],
                    tuple(row["failures"]),
                    tuple(row["partial"]),
                )
                for row in document["scopes"]
            ),
            key=key,
            cached=True,
            error=document.get("error"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def render_patch(original: str, rendered: str) -> str:
    """A unified diff from the existing README to the candidate, LF endings, empty when equal.

    Inlined from the old repo's ``components/readme/composition/renderer.py`` (``render_patch``
    is eight lines of stdlib ``difflib``, with no dependency on the rest of that module) -- needed
    here only so :func:`original_readme` can round-trip-verify a recovered README, exactly as the
    old ``recheck.py`` used it.
    """
    lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile="a/README.md",
        tofile="b/README.md",
    )
    text = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    return text


def reverse_apply(new_text: str, patch: str) -> str:
    """The text ``patch`` (a ``render_patch`` unified diff) was made from, given the text it made.

    Lines the patch removes come back, lines it adds go. The result is only trusted after
    :func:`original_readme` re-diffs it to the same patch.
    """
    new_lines = new_text.splitlines(keepends=True)
    old: list[str] = []
    position = 0
    lines = patch.splitlines(keepends=True)
    index = 0
    while index < len(lines) and not lines[index].startswith("@@"):
        index += 1
    while index < len(lines):
        header = _HUNK.match(lines[index])
        if header is None:
            index += 1
            continue
        count = int(header.group(4)) if header.group(4) is not None else 1
        new_start = int(header.group(3))
        start = new_start if count == 0 else new_start - 1
        old.extend(new_lines[position:start])
        position = start
        index += 1
        while index < len(lines) and not lines[index].startswith("@@"):
            tag, body = lines[index][:1], lines[index][1:]
            if tag == " ":
                old.append(body)
                position += 1
            elif tag == "-":
                old.append(body)
            elif tag == "+":
                position += 1
            index += 1
    old.extend(new_lines[position:])
    return "".join(old)


def original_readme(readme: str, patch: str) -> str | None:
    """The upstream README the candidate was made from, recovered from the sealed patch, or None
    when the recovery does not round-trip (re-diffing it must reproduce the sealed patch)."""
    candidate = reverse_apply(readme, patch)
    return candidate if render_patch(candidate, readme) == patch else None


def classify(scopes: Sequence[ScopeResult]) -> tuple[str, str | None]:
    """(currency, cost) from the scope results: a failure outranks an unverifiable scope, which
    outranks provenance; only passed rechecks (with or without provenance) are current."""
    rechecked = [s for s in scopes if s.outcome != PROVENANCE]
    if any(s.outcome == FAILED for s in rechecked):
        recompose = any(s.outcome == FAILED and s.scope != "presentation" for s in rechecked)
        return UPDATE_REQUIRED, COST_RECOMPOSE if recompose else COST_RERENDER_ONLY
    if any(s.outcome == UNVERIFIED_OUTCOME for s in rechecked):
        return UNVERIFIED, None
    if rechecked:
        return RECHECKED_CURRENT, None
    return (UPDATE_OPTIONAL if scopes else CURRENT), None


def recheck_bundle(*_args: Any, **_kwargs: Any) -> Recheck:
    """Not ported: the full per-bundle recheck needs ``core/candidates.py``, ``core/registry/``,
    ``core/llm/prompts.py``, composition/validation/review -- none pulled into this repository yet
    (see this module's docstring). Raises rather than silently returning a fabricated result."""
    raise NotImplementedError(
        "recheck_bundle is not ported: it needs core.candidates, core.registry, "
        "core.llm.prompts and the composition/validation/review stack, none of which this "
        "repository has pulled yet (see repo_presenter.readme.bundle.recheck module docstring "
        "and migration/reuse-manifest.yaml). The currency model, classify(), the receipt cache "
        "and evaluate()/route() are ported and usable without it."
    )


def recheck_portfolio(*_args: Any, **_kwargs: Any) -> list[Recheck]:
    """Not ported for the same reason as :func:`recheck_bundle`; see its docstring."""
    raise NotImplementedError(
        "recheck_portfolio is not ported: see repo_presenter.readme.bundle.recheck's module "
        "docstring and recheck_bundle's docstring."
    )


def currency_map(rows: Iterable[Recheck]) -> dict[str, str]:
    """``owner__name`` -> currency, the shape a portfolio assessor would take."""
    return {row.repository_dir: row.currency for row in rows}


def currency_counts(rows: Iterable[Recheck]) -> dict[str, int]:
    tally = Counter(row.currency for row in rows)
    return {state: tally.get(state, 0) for state in CURRENCY_STATES}


def render_lines(rows: Sequence[Recheck], *, verbose: bool = True) -> list[str]:
    """The plain-text table a ``recheck`` command would print."""
    lines = [
        f"recheck: {len(rows)} current bundle(s), offline, no provider call, no writes to bundles"
    ]
    for row in rows:
        cost = f" ({row.cost})" if row.cost else ""
        cached = " [receipt]" if row.cached else ""
        lines.append(f"  {row.repository_dir} @ {row.revision[:12]}: {row.currency}{cost}{cached}")
        if row.error:
            lines.append(f"    {row.error}")
        if not verbose:
            continue
        for scope in row.scopes:
            lines.append(f"    {scope.scope}: {scope.outcome} - {scope.detail}")
            lines.extend(f"      {failure}" for failure in scope.failures[:4])
        if row.unrecorded:
            lines.append(f"    ran inputs the sealed record lacks: {', '.join(row.unrecorded)}")
    counts = currency_counts(rows)
    split = Counter(row.cost for row in rows if row.currency == UPDATE_REQUIRED)
    lines.append(
        "currency: "
        + ", ".join(f"{state} {counts[state]}" for state in CURRENCY_STATES)
        + f" (UPDATE_REQUIRED: rerender_only {split.get(COST_RERENDER_ONLY, 0)}, "
        f"recompose {split.get(COST_RECOMPOSE, 0)}); counted "
        f"{sum(counts[s] for s in COUNTING)} of {len(rows)}"
    )
    return lines
