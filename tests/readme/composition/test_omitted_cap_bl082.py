"""BL-082: a section_authoring reply is bounded to fit the job's max_output_tokens.

Hosted Lane R run 43516334907 (Aspose.Cells-FOSS-for-Rust at 1a6004af) failed with "section_authoring:
output truncated at the manifest's max_output_tokens (8000); raise the budget or bound the output,
never retry". Re-extracted locally, its api_reference task has 13 slots and 88 facts a reply may list
in ``omitted``; at the measured 95th-percentile sizes (923 chars a unit, 218 an omitted entry) that
reply is about 8,200 tokens. The cap bounds ``omitted`` (internal accounting) so the reply fits;
a task that already fits, and a type batch, keep their schema byte for byte.
"""

from __future__ import annotations

from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.composition.output_bounds import (
    CHARS_PER_TOKEN,
    OMITTED_P95_CHARS,
    PLANNED_SHARE,
    UNIT_P95_CHARS,
    bound_authoring_citations,
    omitted_cap,
)

BUDGET = 8000


def _task(slots: int, accepted: int, *, key: str = "", must_carry: int = 0) -> SectionTask:
    ids = frozenset(f"public_symbol:aspose_cells_foss::m{i}" for i in range(accepted))
    names = tuple(["intro", *(f"hub:public_symbol:aspose_cells_foss::t{i}" for i in range(slots - 1))])
    return SectionTask(
        "api_reference",
        {},
        ids,
        names,
        key=key,
        slot_facts={name: frozenset() for name in names},
        must_carry=frozenset(f"inherited_unit:{i:03d}.paragraph" for i in range(must_carry)),
    )


def _schema(task: SectionTask) -> dict:
    return {
        "type": "object",
        "properties": {
            "units": {"type": "array", "prefixItems": [
                {"properties": {"fact_ids": {"type": "array"}}} for _ in task.slots
            ]},
            "omitted": {"type": "array"},
        },
    }


def test_the_rust_api_reference_reply_is_capped_to_fit() -> None:
    task = _task(13, 88)
    cap = omitted_cap(task, BUDGET)
    assert cap is not None and cap < 88
    planned = 13 * UNIT_P95_CHARS + cap * OMITTED_P95_CHARS
    assert planned <= BUDGET * CHARS_PER_TOKEN * PLANNED_SHARE
    bounded = bound_authoring_citations(_schema(task), task, BUDGET)
    assert bounded["properties"]["omitted"]["maxItems"] == cap


def test_negative_control_uncapped_the_reply_does_not_fit() -> None:
    planned = 13 * UNIT_P95_CHARS + 88 * OMITTED_P95_CHARS
    assert planned / CHARS_PER_TOKEN > BUDGET


def test_a_task_that_fits_keeps_its_schema() -> None:
    task = _task(1, 10)
    assert omitted_cap(task, BUDGET) is None
    assert bound_authoring_citations(_schema(task), task, BUDGET) == bound_authoring_citations(
        _schema(task), task
    )


def test_a_type_batch_is_left_to_its_batch_size() -> None:
    task = _task(40, 120, key="api_reference#types-1")
    assert omitted_cap(task, BUDGET) is None


def test_the_cap_never_drops_below_the_units_the_section_must_carry() -> None:
    task = _task(19, 200, must_carry=5)
    assert omitted_cap(task, BUDGET) == 5
