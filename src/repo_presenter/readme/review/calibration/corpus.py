"""The forest calibration corpus (plan D9 V4): clean twins, mutants, and recorded real defects.

A ``Base`` is a real complete candidate plus the curated ``Repair`` list that turns it into its
clean twin: each repair removes ONE defect that this project's own reading of the candidate found
(an unsupported claim, a claim a SUPPORTED fact contradicts, a lint-level flaw), recorded as data
so nothing about the twin is hand-waved. A repair that removes a classed defect also yields a
*real* case: the twin with only that repair undone, whose expected verdict is REJECT.

``build_corpus`` returns, per base, its clean twin (expected ACCEPT), one mutant per applicable
operator (expected REJECT, each differing from the twin in exactly one declared span), and the
real-defect cases. ``RecordedDefect`` adds a defect kept on record as written (the aspose-font-foss
inherited install command, the duplicate opening) with its repaired twin.

Nothing here calls a model, and nothing here decides what a reviewer should find: a case states
the expected verdict and the class of the injected or recorded defect, and the metrics harness
compares a reviewer's verdict with it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from repo_presenter.readme.review.calibration.mutations import OPERATORS, Mutation
from repo_presenter.readme.review.calibration.outcomes import ACCEPT, REJECT
from repo_presenter.readme.review.calibration.sources import (
    SourceCandidate,
    blocking_check,
)
from repo_presenter.readme.review.independent_reviewer import review_candidate
from repo_presenter.readme.validation.blocking import blocking_failures

Role = Literal["clean", "mutant", "real_defect", "unscored_twin"]


@dataclass(frozen=True)
class Repair:
    """Replace ``old`` by ``new`` (exactly ``count`` occurrences). ``klass`` names the defect
    class the repair removes (``None`` for a lint-level fix that is not a class)."""

    old: str
    new: str
    reason: str
    klass: str | None = None
    count: int = 1
    #: Lower-case words a finding must contain to be about the defect this repair removes.
    targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Base:
    source: SourceCandidate
    repairs: tuple[Repair, ...] = ()
    #: Blocking checks that fail on the clean twin and are not about its text (for example the
    #: package registry's ownership receipt, a property of the registry and not of the README).
    tolerated_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecordedDefect:
    """A real defect kept as written, with the repairs that make its clean twin."""

    source: SourceCandidate
    klass: str
    repairs: tuple[Repair, ...]
    note: str
    targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Case:
    case_id: str
    base: str
    ecosystem: str
    role: Role
    klass: str | None
    operator: str | None
    source: SourceCandidate
    expected: str
    twin_of: str | None
    #: Blocking checks already failing on this case's clean twin; only a NEW failure counts as the
    #: candidate being blocked before the model is asked.
    baseline_checks: tuple[str, ...]
    note: str
    mutation: Mutation | None = None
    #: What a finding must mention to be about this case's defect (see ``Mutation.targets``).
    targets: tuple[str, ...] = ()
    #: Deterministic rules that already fire on this case's twin: a candidate built from a base the
    #: deterministic stage blocks anyway (its dispositions predate the accounting step). A rule
    #: that fires on the twin is not a catch of anything injected into it.
    baseline_rules: tuple[str, ...] = ()
    #: The text that IS the defect (the injected span, or the span a repair removes): a rejection is
    #: on target when it cites lines holding it. Empty when the defect is an absence (a dropped
    #: section) and only keywords can locate it.
    defect_text: str = ""

    @property
    def readme(self) -> str:
        return self.source.readme


def apply_repairs(text: str, repairs: Sequence[Repair]) -> str:
    for repair in repairs:
        found = text.count(repair.old)
        if found != repair.count:
            raise ValueError(
                f"repair ({repair.reason}) expects {repair.count} occurrence(s) of "
                f"{repair.old[:60]!r}, found {found}"
            )
        text = text.replace(repair.old, repair.new)
    return text


def with_readme(
    source: SourceCandidate, readme: str, *, validate: bool
) -> SourceCandidate:
    """``source`` with ``readme`` as its candidate text; the S9 validation is re-run when the
    source is one the blocking checks can judge."""
    changed = replace(source, readme=readme)
    if validate and source.validation.get("checks"):
        changed = replace(changed, validation=blocking_check(changed, readme))
    return changed


def failing_checks(source: SourceCandidate) -> tuple[str, ...]:
    return tuple(sorted(check["id"] for check in blocking_failures(source.validation)))


def new_blocking_checks(case: Case) -> tuple[str, ...]:
    """The blocking checks that fail on ``case``'s README and did not already fail on its twin."""
    if not case.source.validation.get("checks"):
        return ()
    failing = blocking_failures(blocking_check(case.source, case.readme))
    return tuple(
        sorted(c["id"] for c in failing if c["id"] not in case.baseline_checks)
    )


def deterministic_rules(case: Case) -> tuple[str, ...]:
    """The rules of ``review_candidate`` that fire on ``case``'s README."""
    source = case.source
    verdict = review_candidate(
        readme_text=case.readme,
        units=source.units.get("units", []),
        facts=source.facts,
        dispositions=source.dispositions,
        original_readme=source.original,
    )
    return tuple(sorted({finding.rule for finding in verdict.findings}))


def _clean_case(base: Base) -> Case:
    twin = with_readme(
        base.source, apply_repairs(base.source.readme, base.repairs), validate=True
    )
    baseline = failing_checks(twin)
    unexpected = sorted(set(baseline) - set(base.tolerated_checks))
    if unexpected:
        raise ValueError(
            f"{base.source.name}: the clean twin still fails {unexpected}; repair it or tolerate "
            "the check with a stated reason"
        )
    return Case(
        case_id=f"{base.source.name}/clean",
        base=base.source.name,
        ecosystem=twin.ecosystem,
        role="clean",
        klass=None,
        operator=None,
        source=twin,
        expected=ACCEPT,
        twin_of=None,
        baseline_checks=baseline,
        note="the repaired real candidate",
    )


def base_cases(base: Base) -> list[Case]:
    """The clean twin, the real-defect cases and the mutants of one base."""
    clean = _clean_case(base)
    baseline_rules = deterministic_rules(clean)
    if baseline_rules:
        # The pipeline would never send this twin to the model, so a verdict on it measures the
        # base and not the reviewer: it is kept on record, asked, and not scored as clean.
        clean = replace(
            clean,
            role="unscored_twin",
            baseline_rules=baseline_rules,
            note="the repaired real candidate; the deterministic stage already blocks it "
            f"({', '.join(baseline_rules)})",
        )
    cases = [clean]
    for index, repair in enumerate(base.repairs):
        if repair.klass is None:
            continue
        others = [r for k, r in enumerate(base.repairs) if k != index]
        readme = apply_repairs(base.source.readme, others)
        cases.append(
            replace(
                clean,
                case_id=f"{base.source.name}/real:{repair.klass}:{index}",
                role="real_defect",
                klass=repair.klass,
                source=with_readme(clean.source, readme, validate=False),
                expected=REJECT,
                twin_of=clean.case_id,
                note=f"recorded in the candidate as written: {repair.reason}",
                targets=repair.targets,
                defect_text=repair.old.strip(),
            )
        )
    for name, operator in OPERATORS.items():
        mutation = operator(clean.source)
        if mutation is None:
            continue
        cases.append(
            replace(
                clean,
                case_id=f"{base.source.name}/{name}",
                role="mutant",
                klass=mutation.klass,
                operator=name,
                source=with_readme(clean.source, mutation.readme, validate=False),
                expected=mutation.expected,
                twin_of=clean.case_id,
                note=mutation.note,
                mutation=mutation,
                targets=mutation.targets,
                defect_text=mutation.replacement.strip(),
            )
        )
    return cases


def recorded_cases(recorded: RecordedDefect) -> list[Case]:
    """The defect case and, when it has repairs, its twin. A recorded defect with no repair has
    no twin: a twin identical to the defect would be asked the same question twice."""
    name = recorded.source.name
    twin_readme = apply_repairs(recorded.source.readme, recorded.repairs)
    twin = Case(
        case_id=f"{name}/clean",
        base=name,
        ecosystem=recorded.source.ecosystem,
        role="clean",
        klass=None,
        operator=None,
        source=replace(recorded.source, readme=twin_readme),
        expected=ACCEPT,
        twin_of=None,
        baseline_checks=(),
        note="the recorded candidate with its recorded defect repaired",
    )
    # A recorded candidate is judged against today's facts and dispositions; where those no longer
    # fit it (the live README moved on), its repaired twin is kept on record but not scored,
    # because a verdict on it would measure the staleness and not the reviewer.
    clean = (
        twin if not deterministic_rules(twin) else replace(twin, role="unscored_twin")
    )
    defect = replace(
        clean,
        case_id=f"{name}/recorded:{recorded.klass}",
        role="real_defect",
        klass=recorded.klass,
        source=recorded.source,
        expected=REJECT,
        twin_of=clean.case_id if recorded.repairs else None,
        note=recorded.note,
        targets=recorded.targets,
        defect_text=recorded.repairs[0].old.strip() if recorded.repairs else "",
    )
    return [clean, defect] if recorded.repairs else [defect]


def build_corpus(
    bases: Sequence[Base], recorded: Sequence[RecordedDefect] = ()
) -> list[Case]:
    cases = [case for base in bases for case in base_cases(base)]
    cases.extend(case for item in recorded for case in recorded_cases(item))
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case ids in the corpus")
    return cases
