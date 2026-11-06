"""A zero-call estimate of what a calibration run will spend, before it is run.

A live review sends one request per review unit and the call store replays any request it has
answered before (a mutant re-asks only the units it changed; a resumed run re-asks nothing it has
stored). ``estimate_run`` walks the selected cases in the order ``run_corpus`` asks them, computes
each unit's request hash with ``llm_review.planned_requests`` (the same function the live review
uses to decide what it sends, so the two cannot drift), and counts the requests the store would not
replay: the first pass shares one store, every stability repeat gets a fresh one
(the calibration adapter's ``ask0001``, ``ask0002``, ... stores). A request already in
the store directory on disk is free, so the estimate of a resumed run is what is left to spend.

Each request costs one call when its first reply is valid and two when the reply needs the one
re-ask; ``reask_rate`` (iteration 4 measured 17 of 196 first replies contract-invalid, 0.09) turns the
request count into an expected call count, and ``worst_case`` assumes every request is re-asked.
Transport retries of a dropped connection are not modelled. Nothing here sends a request.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from repo_presenter.core.llm.fallback import ModelSelection
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.readme.review.calibration.corpus import Case
from repo_presenter.readme.review.calibration.reviewers import review_key
from repo_presenter.readme.review.llm_review import JOB, planned_requests

#: Iteration 4's measured share of unit first replies that broke the contract (17 / 196).
DEFAULT_REASK_RATE = 0.10


@dataclass(frozen=True)
class Estimate:
    cases: int
    #: Unit requests of the first pass, all of them, and those the shared store would not replay.
    first_pass_units: int
    first_pass_new: int
    stability_cases: int
    stability_new: int
    reask_rate: float
    #: role -> (cases, new requests) of the first pass.
    by_role: dict[str, tuple[int, int]] = field(default_factory=dict)
    #: base -> new requests of the first pass.
    by_base: dict[str, int] = field(default_factory=dict)

    @property
    def requests(self) -> int:
        return self.first_pass_new + self.stability_new

    @property
    def expected_calls(self) -> int:
        return math.ceil(self.requests * (1 + self.reask_rate))

    @property
    def worst_case(self) -> int:
        return 2 * self.requests

    def lines(self, cap: int | None = None) -> list[str]:
        out = [
            (
                f"cases {self.cases}: {self.first_pass_units} unit requests, "
                f"{self.first_pass_new} not replayable from the store"
            ),
            (
                f"stability {self.stability_cases} cases x 3 fresh reviews: "
                f"{self.stability_new} requests"
            ),
        ]
        for role, (n, new) in sorted(self.by_role.items()):
            out.append(f"  {role:14s} cases {n:4d} new requests {new:4d}")
        costly = sorted(self.by_base.items(), key=lambda item: (-item[1], item[0]))[:12]
        out.append(
            "  costliest bases: " + ", ".join(f"{base} {new}" for base, new in costly)
        )
        out.append(
            f"requests {self.requests}; expected calls {self.expected_calls} at re-ask rate "
            f"{self.reask_rate:.2f}; worst case {self.worst_case} (every request re-asked)"
        )
        if cap is not None:
            out.append(
                f"cap {cap}: expected {self.expected_calls} leaves "
                f"{cap - self.expected_calls} ({(cap - self.expected_calls) / cap:.0%}) headroom"
            )
        return out


def case_requests(
    case: Case, prompts: PromptRegistry, models: ModelSelection | None = None
) -> tuple[str, ...]:
    """The request hashes a live review of ``case`` sends, one per review unit."""
    source = case.source
    _, _, planned = planned_requests(
        prompts=prompts,
        context=JobContext(
            repository=source.repository,
            source_revision=source.facts.source_revision,
            models=models,
        ),
        candidate_readme=case.readme,
        original_readme=source.original,
        facts=source.facts,
        plan=source.plan,
        dispositions=source.dispositions,
        rendered=source.rendered,
    )
    return tuple(request.request_sha256 for request in planned)


def _stored(store: CallStore, hashes: Sequence[str]) -> set[str]:
    return {h for h in hashes if store.get(h) is not None}


def estimate_run(
    selected: Sequence[Case],
    stability: Sequence[Case],
    prompts: PromptRegistry,
    *,
    store_dir: Path,
    stability_dir: Path,
    models: ModelSelection | None = None,
    reask_rate: float = DEFAULT_REASK_RATE,
    journaled: frozenset[str] = frozenset(),
) -> Estimate:
    """What ``run_corpus(selected)`` then three fresh reviews of each ``stability`` case would send.
    ``journaled`` are the review keys (``reviewers.review_key``) a resumed run takes from its
    journal without a request."""
    store = CallStore(store_dir)
    prompt_sha = prompts[JOB].sha256
    route = prompts[JOB].manifest.model_route
    model = route if models is None else models.model_for(route)
    seen: set[str] = set()
    units = new = 0
    by_role: dict[str, list[int]] = {}
    by_base: dict[str, int] = {}
    requests_of: dict[str, tuple[str, ...]] = {}
    for case in selected:
        hashes = case_requests(case, prompts, models)
        requests_of[case.case_id] = hashes
        units += len(hashes)
        key = review_key(store_dir.name, case, prompt_sha, model)
        fresh = [] if key in journaled else [h for h in hashes if h not in seen]
        fresh = [h for h in fresh if h not in _stored(store, fresh)]
        seen.update(hashes)
        new += len(fresh)
        role = by_role.setdefault(case.role, [0, 0])
        role[0] += 1
        role[1] += len(fresh)
        by_base[case.base] = by_base.get(case.base, 0) + len(fresh)
    stable_new = 0
    ask = 0
    for case in stability:
        hashes = requests_of.get(case.case_id) or case_requests(case, prompts, models)
        for _ in range(3):
            ask += 1
            scope = f"{stability_dir.name}/ask{ask:04d}"
            if review_key(scope, case, prompt_sha, model) in journaled:
                continue
            ask_store = CallStore(stability_dir / f"ask{ask:04d}")
            # within one fresh review, two units with identical requests are asked once
            distinct = list(dict.fromkeys(hashes))
            stable_new += len(distinct) - len(_stored(ask_store, distinct))
    return Estimate(
        cases=len(selected),
        first_pass_units=units,
        first_pass_new=new,
        stability_cases=len(stability),
        stability_new=stable_new,
        reask_rate=reask_rate,
        by_role={k: (v[0], v[1]) for k, v in by_role.items()},
        by_base=dict(sorted(by_base.items())),
    )
