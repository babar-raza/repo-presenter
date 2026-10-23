"""coherence_batches() splits on whichever of two independent caps a task would first exceed:
the original unit-count cap, or the rendered-text-size cap added after a real max_output_tokens
truncation was observed (aspose-pdf-foss/TypeScript, 2026-10-23: a batch of only 16 units still
overran the manifest's 8000-token output budget because those units' own rendered text was
large). No test existed for this function before that fix.
"""

from __future__ import annotations

from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.composition.coherence import (
    _COHERENCE_BATCH_CHARS,
    _COHERENCE_BATCH_UNITS,
    coherence_batches,
)


def _task(section_id: str, *, slots: tuple[str, ...] = ("a",), chars: int = 0) -> SectionTask:
    lines = (("x" * chars,),) if chars else ()
    return SectionTask(
        section_id=section_id,
        packet={},
        accepted_ids=frozenset(),
        slots=slots,
        slot_render_lines={slots[0]: lines[0]} if chars else {},
    )


def test_small_tasks_batch_together_up_to_the_unit_count_cap() -> None:
    tasks = [_task(f"s{i}") for i in range(_COHERENCE_BATCH_UNITS)]
    batches = coherence_batches(tasks)
    assert len(batches) == 1
    assert [task.section_id for task in batches[0][1]] == [t.section_id for t in tasks]


def test_one_more_task_than_the_unit_count_cap_starts_a_second_batch() -> None:
    tasks = [_task(f"s{i}") for i in range(_COHERENCE_BATCH_UNITS + 1)]
    batches = coherence_batches(tasks)
    assert len(batches) == 2
    assert len(batches[0][1]) == _COHERENCE_BATCH_UNITS
    assert len(batches[1][1]) == 1


def test_a_batch_well_under_the_unit_count_cap_still_splits_on_rendered_text_size() -> None:
    """The real, live finding this fix closes: few units, but each carrying enough rendered text
    that the batch's reply would be at real risk of max_output_tokens truncation."""
    big = _COHERENCE_BATCH_CHARS // 3 + 1
    tasks = [_task(f"s{i}", chars=big) for i in range(3)]
    batches = coherence_batches(tasks)
    assert len(batches) == 2
    assert len(batches[0][1]) == 2
    assert len(batches[1][1]) == 1


def test_a_single_oversized_task_still_gets_its_own_batch_rather_than_being_dropped() -> None:
    """Matches the unit-count cap's own existing behaviour for an oversized single task: the
    ``if current and ...`` guard never splits an empty batch, so one task alone is never refused
    a batch merely for being larger than the cap."""
    tasks = [_task("huge", chars=_COHERENCE_BATCH_CHARS * 2)]
    batches = coherence_batches(tasks)
    assert len(batches) == 1
    assert len(batches[0][1]) == 1


def test_tasks_well_under_both_caps_are_unaffected() -> None:
    tasks = [_task(f"s{i}", chars=10) for i in range(4)]
    batches = coherence_batches(tasks)
    assert len(batches) == 1
    assert len(batches[0][1]) == 4
