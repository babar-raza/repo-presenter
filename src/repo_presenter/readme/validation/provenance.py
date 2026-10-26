"""BC-01, BC-03 and BC-14: the snapshot is pinned, examples ran, and claims agree with the facts.

ADAPT (import paths, public names) from the old repository-presenter project's
``components/readme/validation/registry.py``: ``_check_source`` (BC-01), ``_check_examples``
(BC-03) and ``_check_claims`` (BC-14). BC-14's own rules live in ``readme/validation/claims.py``
(ported 2026-10-23); this module only routes its findings to a causal stage and a section.
"""

from __future__ import annotations

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import printed_example
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.failures import Candidate, CausalStage, Failure
from repo_presenter.readme.validation.text import fences, section_lines, sha256

# The markers an example fact's evidence carries once it has actually run (BC-03's own list).
EXECUTION_MARKERS = (": EXECUTED", ": COMPILED")


def source_failures(candidate: Candidate) -> list[Failure]:
    """BC-01: the facts pin the snapshot revision, the original bytes match their digest, and
    every fact carries evidence."""
    failures: list[Failure] = []
    facts = candidate.facts
    if facts.source_revision != candidate.source_revision:
        failures.append(
            Failure(
                "EXTRACTING",
                f"facts.json records revision {facts.source_revision}; the snapshot pinned "
                f"{candidate.source_revision}",
            )
        )
    revision = next((f for f in facts.facts if f.id == "identity:revision"), None)
    if revision is not None and revision.value != candidate.source_revision:
        failures.append(
            Failure(
                "EXTRACTING",
                f"identity:revision is {revision.value}, not the pinned revision",
            )
        )
    if candidate.original_readme is not None and (
        sha256(candidate.original_readme) != candidate.readme_sha256
    ):
        failures.append(
            Failure(
                "EXTRACTING",
                "the original README bytes differ from the snapshot digest",
            )
        )
    for fact in facts.facts:
        if not fact.evidence:
            failures.append(Failure("EXTRACTING", f"{fact.id} carries no evidence"))
    return failures


def example_failures(candidate: Candidate) -> list[Failure]:
    """BC-03: every planned example was executed or compiled at this revision, and every fence
    in the ecosystem's declared aliases is one of the planned, verified bodies."""
    failures: list[Failure] = []
    by_id = {fact.id: fact for fact in candidate.facts.facts}
    plan = candidate.plan
    planned = [
        fact_id
        for fact_id in [
            plan.get("quick_start_example_id"),
            plan.get("second_quick_start_example_id"),
            *plan.get("additional_example_ids", []),
        ]
        if fact_id
    ]
    for fact_id in planned:
        fact = by_id.get(fact_id)
        if fact is None or fact.kind != "example":
            failures.append(Failure("PLANNING", f"{fact_id} is not an example fact"))
            continue
        executed = any(
            marker in (evidence.detail or "")
            for evidence in fact.evidence
            for marker in EXECUTION_MARKERS
        )
        if fact.polarity != "SUPPORTED" or not executed:
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact_id} was not executed or compiled at this revision ({fact.polarity})",
                )
            )
    # A printed example is the program its receipt compiled: the snippet with the usings or
    # imports the verifier supplied in front of it (core/examples.py ``printed_example``).
    values = {
        printed_example(by_id[fact_id]).rstrip("\n")
        for fact_id in planned
        if fact_id in by_id
    }
    # A fence's language is compared against the ecosystem's declared aliases
    # (EcosystemSpec.example_fences - `py`/`python3` for Python, `csharp`/`cs`/`c#` for .NET),
    # never against the bare ecosystem string: a .NET example is fenced ```csharp, never ```net.
    example_fences = spec_for(candidate.entry.ecosystem).example_fences
    for language, body in fences(candidate.readme):
        if language in example_fences and body.rstrip("\n") not in values:
            first = body.strip().splitlines()[0] if body.strip() else ""
            failures.append(
                Failure(
                    "COMPOSING",
                    f"a {language} code block is not a planned verified example: {first[:60]!r}",
                )
            )
    return failures


def claim_failures(candidate: Candidate) -> list[Failure]:
    """BC-14: version, install-package and publication statements agree with the facts."""
    lines = section_lines(candidate.readme)
    failures: list[Failure] = []
    for finding in claim_findings(candidate.readme, candidate.facts):
        stage: CausalStage = (
            "EXTRACTING" if finding.stage == "EXTRACTING" else "COMPOSING"
        )
        section = lines[finding.line] if finding.line < len(lines) else None
        failures.append(Failure(stage, finding.detail, section))
    return failures
