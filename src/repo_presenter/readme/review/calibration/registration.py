"""Pre-registration: the exact cases a measurement asks and what each is expected to be, frozen in a
file before any reviewer output exists.

``registration_document`` writes, per selected case, its id, role, expected verdict, defect class
and label, and the SHA-256 of the README it puts to the reviewer and of the defect text a catch must
cite. Digests, not text: a reference base's README is aspose.org's and stays local (decision log
2026-10-31, decision 1), but its digest pins it exactly. ``registered_cases`` rebuilds the selection
from a freshly built corpus and refuses any difference (a case missing, a role, label or README that
changed), so a run cannot measure a corpus other than the one registered, and the labels cannot be
edited after a result is seen without the committed file's own digest changing.

The stability subset is registered too, so which cases are repeated is fixed before the first pass.
Nothing here calls a model.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.readme.review.calibration.corpus import Case
from repo_presenter.readme.review.calibration.harness import defect_label

SCHEMA = "reviewer-calibration-registration/1"


class RegistrationMismatch(ValueError):
    """The built corpus is not the registered one; the message lists every difference."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def case_entry(case: Case) -> dict[str, Any]:
    return {
        "case": case.case_id,
        "base": case.base,
        "role": case.role,
        "expected": case.expected,
        "klass": case.klass,
        "label": defect_label(case),
        "readme_sha256": _sha(case.readme),
        "facts_revision": case.source.facts.source_revision,
        "defect_sha256": _sha(case.defect_text) if case.defect_text else None,
    }


def registration_document(
    selected: Sequence[Case],
    stability: Sequence[Case],
    *,
    corpus_size: int,
    notes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ids = {case.case_id for case in selected}
    stray = [case.case_id for case in stability if case.case_id not in ids]
    if stray:
        raise ValueError(f"stability cases that are not selected: {stray}")
    by_role: dict[str, int] = {}
    for case in selected:
        by_role[case.role] = by_role.get(case.role, 0) + 1
    return {
        "schema": SCHEMA,
        "corpus_cases": corpus_size,
        "selected": len(selected),
        "by_role": dict(sorted(by_role.items())),
        "notes": dict(notes or {}),
        "cases": [case_entry(case) for case in selected],
        "stability": [case.case_id for case in stability],
    }


def registered_cases(
    document: Mapping[str, Any], cases: Sequence[Case]
) -> tuple[list[Case], list[Case]]:
    """``(selected, stability)`` in registered order, from ``cases`` (a freshly built corpus).
    Raises ``RegistrationMismatch`` naming every registered case that is missing or differs."""
    if document.get("schema") != SCHEMA:
        raise RegistrationMismatch(f"not a {SCHEMA} document")
    built = {case.case_id: case for case in cases}
    problems: list[str] = []
    selected: list[Case] = []
    for entry in document["cases"]:
        case = built.get(entry["case"])
        if case is None:
            problems.append(f"{entry['case']}: not in the built corpus")
            continue
        current = case_entry(case)
        changed = sorted(k for k, v in entry.items() if current.get(k) != v)
        if changed:
            problems.append(f"{entry['case']}: {', '.join(changed)} differ from the registration")
            continue
        selected.append(case)
    chosen = {case.case_id: case for case in selected}
    stability = [chosen[i] for i in document.get("stability", []) if i in chosen]
    if len(stability) != len(document.get("stability", [])) and not problems:
        problems.append("a registered stability case is not a selected case")
    if problems:
        raise RegistrationMismatch(
            f"{len(problems)} registered case(s) differ from the built corpus:\n  "
            + "\n  ".join(problems[:50])
        )
    return selected, stability
