"""The blocking checks this repository has ported, run over one candidate.

ADAPT (a reduced dispatch) from the old repository-presenter project's
``components/readme/validation/registry.py``: ``validate_candidate`` and its ``BLOCKING_CHECKS``
table. Kept from the old shell: one record per check with its verdict, its earliest causal stage,
its details, and its failures as fields. Not kept, each for the reason given:

* BC-10 (independent review verdict, ``record_review_verdict``): read the old LLM reviewer's
  ``review.json`` shape (second read, demotion, single-reader advisory), which this repository's
  reviewer never writes. Its own verdict is ``readme/review/independent_reviewer.py``, judged
  before any sealing.
* BC-11 (fresh-process no-op proof, ``record_replay_verdict``): stamped PASS without reading any
  evidence. The judgment is ``readme/bundle/evaluation.py`` over ``core/noop_proof.py``.
* The ``validation.json`` envelope (``write_validation``, ``summary``, ``advisory``, ``coverage``,
  ``protected_content_fingerprint``), the version table, and ``deferred_on_required_rows``: no
  consumer in this repository reads them yet, so they are deferred until a sealing stage does.

Nothing here is wired into the cascade yet; the checks are ported and tested, not run by
``cascade.py``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from repo_presenter.core.secrets import ConfiguredSecret, scan_for_secrets
from repo_presenter.readme.validation.failures import (
    Candidate,
    CausalStage,
    Failure,
    earliest,
)
from repo_presenter.readme.validation.install import install_failures
from repo_presenter.readme.validation.links import link_failures
from repo_presenter.readme.validation.provenance import (
    claim_failures,
    example_failures,
    source_failures,
)
from repo_presenter.readme.validation.structure import (
    canonical_name_failures,
    structure_failures,
)
from repo_presenter.readme.validation.units import (
    disposition_failures,
    protected_failures,
    unit_failures,
)

JUDGES: dict[str, Callable[[Candidate], list[Failure]]] = {
    "BC-01": source_failures,
    "BC-02": install_failures,
    "BC-03": example_failures,
    "BC-04": unit_failures,
    "BC-05": disposition_failures,
    "BC-06": link_failures,
    "BC-07": structure_failures,
    "BC-08": protected_failures,
    "BC-12": canonical_name_failures,
    "BC-14": claim_failures,
}
CHECK_NAMES: dict[str, str] = {
    "BC-01": "Source revision pinned; original README bytes exact; every fact carries evidence",
    "BC-02": "Install command verified against the manifest, registry and source-build receipts",
    "BC-03": "Every rendered example was executed or compiled in isolation at this revision",
    "BC-04": "Every content unit cites SUPPORTED facts; every identifier in prose is a fact value",
    "BC-05": "Every inherited unit has exactly one disposition; placed units appear in destination",
    "BC-06": "Every link resolves; Aspose links within the ceiling; Enterprise Edition naming",
    "BC-07": "Structure: one H1, one badge row, title case, abbreviations, fences, narration",
    "BC-08": "Protected content preserved",
    "BC-09": "No configured secret in the bundle",
    "BC-12": "Every product-name position spells the registry's canonical product name",
    "BC-14": "Version, install command and publication statements agree with the facts",
}


def secret_failures(
    transaction: Path, secrets: Sequence[ConfiguredSecret]
) -> list[Failure]:
    """BC-09: no configured secret's value appears anywhere under the transaction directory."""
    return [
        Failure(None, f"value of {leak.variable} found in {leak.path.name}")
        for leak in scan_for_secrets(transaction, secrets)
    ]


def validate_candidate(
    candidate: Candidate, transaction: Path, secrets: Sequence[ConfiguredSecret]
) -> dict[str, Any]:
    """Every ported blocking check, with its verdict, earliest causal stage, details and failures.

    Each check record carries ``failures`` as fields (section, causal stage, detail and, for an
    inherited unit, the unit ID) so a router reads fields and never parses ``details`` prose.
    """
    judges: dict[str, Callable[[Candidate], list[Failure]]] = {
        **JUDGES,
        "BC-09": lambda _candidate: secret_failures(transaction, secrets),
    }
    checks: list[dict[str, Any]] = []
    for check_id in sorted(judges):
        failures = judges[check_id](candidate)
        stage: CausalStage | None = earliest(failures)
        checks.append(
            {
                "id": check_id,
                "name": CHECK_NAMES[check_id],
                "verdict": "FAIL" if failures else "PASS",
                "causal_stage": stage,
                "details": [failure.detail for failure in failures],
                "failures": [
                    {
                        "section_id": failure.section,
                        "causal_stage": failure.stage,
                        "detail": failure.detail,
                        **(
                            {"unit_id": failure.unit}
                            if failure.unit is not None
                            else {}
                        ),
                    }
                    for failure in failures
                ],
            }
        )
    verdicts = Counter(record["verdict"] for record in checks)
    return {
        "repository": candidate.entry.repository,
        "source_revision": candidate.source_revision,
        "checks": checks,
        "summary": {"pass": verdicts.get("PASS", 0), "fail": verdicts.get("FAIL", 0)},
    }


def blocking_failures(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        check for check in document.get("checks", []) if check.get("verdict") == "FAIL"
    ]
