"""What section_authoring does once the model's universal re-ask has not converged.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/authoring_retry.py``, 2026-10-23. Found while investigating the
title-restatement rejection that failed closed twice, independently, on
aspose-words-foss/.NET's section_authoring (S6) stage -- all five of this module's dependencies
(authoring.py, output_bounds.py, core/facts.py, core/llm/narrowing.py, core/llm/prompts.py) were
already present in this repository under the same names, confirmed genuinely self-contained on a
full read, so it was ported the same day rather than left as a known-but-unported fix. See
migration/reuse-manifest.yaml for the disposition record.

Wave 3 (cut f69f75c7): nine of thirty-six repositories failed with ``section_authoring: output
rejected twice``. Read from the archived ``rejected-*.json`` of each, the causes were these, and
none was a section the model could not write:

* a rejection named the first of several violations of one kind (TeX-Python restated two commands
  and was told about one), so the re-ask fixed what it was told and kept the rest;
* a reply fixed the stray identifier it was told about and, in doing so, restated its slot's title
  (PDF-Cpp) or left one list item unstated (Slides-Java), faults the first message had no reason to
  name - and the single re-ask was spent;
* the re-ask returned the same reply byte for byte (Words-Python, Email-Python), because it was
  asked the same question.

``authoring.unit_checks`` now names every violation of every unit in one rejection. This module is
the rest of the unit-level remedy:

* :func:`authoring_narrowing` - one further ask, after the two the job already makes, for only the
  slots still failing. It is a different request (the same prompt, packet and schema narrowed to
  those slots, with the complete defect list and the unit each one replaces), so it is not a third
  equivalent attempt, and the accepted units are kept exactly as the second reply gave them.
  Whatever the merged reply gets wrong is judged by the ordinary checks; a rejection that names no
  slot (a must-carry unit nobody cited) cannot be narrowed and fails as before. A slot the second
  reply returned exactly as the first did (:func:`repeated_slots`) was not changed by being told,
  so for it the narrowed ask changes the evidence - it says the unit was returned twice and
  rejected twice, and what changing it means - instead of putting the same question a third time.
* :func:`recover_restating_sentences` - the deterministic last resort that removes a sentence only
  when it restates something the page already prints (the slot's title; a command the renderer
  prints verbatim beside the unit). It never rewrites a word and never touches a unit that does
  not restate. A stray identifier is deliberately NOT rewritten into words: that would launder an
  unevidenced claim, which is the check's whole purpose, not remove it.

It sits beside ``authoring.py`` rather than inside it so the change moves no governed constant.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
import string
from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.narrowing import Narrowing
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.readme.composition.authoring import (
    _VERBATIM_PRESERVED_DISPOSITIONS,
    OPENING_RESTATED_OMISSION_REASON,
    VALUE_FREE_SECTIONS,
    SectionTask,
    authoring_schema,
    citable,
    opening_adds_nothing,
    opening_releasable,
    preserved_section_text,
    recover_opening_duplicates_preserved,
    restated_command_lines,
    restates_own_title,
    slots_clause,
    value_tokens,
)
from repo_presenter.readme.composition.coverage import states_all
from repo_presenter.readme.composition.output_bounds import (
    bound_authoring_citations,
    omittable_ids,
)

_SLOT_SET_ERROR = "units must fill exactly these slots once each"
# Accepted units are shown to the narrowed ask so it does not repeat them; a long section shows
# the first of them only, which is all a sentence-level repeat needs.
_ACCEPTED_SHOWN_CHARS = 6000
# Said to the narrowed ask for units the model returned unchanged after the re-ask told it what was
# wrong (wave 4, Slides-Java and Slides-Cpp: the same text in all three replies). The model is told
# the rule it keeps meeting and what changing the unit means for each kind of refusal, so the third
# reply answers a different request instead of being the same answer a third time.
_REPEATED_NOTE = (
    "Your first two replies gave {slots} exactly as shown above, and both were rejected for the "
    "reasons listed below, so that text is not to be returned again: it fails the job. Change each "
    "unit named. Where a reason says an identifier is not an accepted fact value, delete the "
    "clause that uses it, or say the same thing in plain words with no identifier in it (a reason "
    "that names an accepted spelling near it offers that spelling instead); where a reason says "
    "the unit restates its title or a command, say what the title or command does not, or leave "
    "the sentence out."
)
# A sentence ends at ``.``/``!``/``?`` that follows a word and precedes a capital, a digit, a quote
# or an opening bracket. A full stop standing alone ("ruff check . to lint") or followed by a
# lower-case word ("e.g. the") ends nothing: cutting there would leave half a sentence behind.
_SENTENCE_BREAK = re.compile(r"(?<=\S[.!?])(\s+)(?=[A-Z0-9\"'(\[`])")


def _slots_of(task: SectionTask, error: str) -> list[str] | None:
    """The slot one rejection concerns: a unit's own refusal names it. ``None`` when the rejection
    names no slot (a must-carry unit nobody cited, a schema error), which no narrowed ask can
    address."""
    for slot in sorted(task.slots, key=len, reverse=True):
        if error.startswith(f"unit {slot}: "):
            return [slot]
    return None


def _units(content: str) -> list[dict[str, Any]] | None:
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return None
    units = document.get("units") if isinstance(document, dict) else None
    if not isinstance(units, list):
        return None
    return [unit for unit in units if isinstance(unit, dict)]


def failing_slots(task: SectionTask, content: str, rejection: Sequence[str]) -> list[str]:
    """The slots of ``task``, in its order, that the rejection of ``content`` is about; empty when
    the rejection is about anything else too (then nothing is narrowed and the job fails as it
    always did), or when ``content`` is not a reply to this task."""
    units = _units(content)
    if units is None or not rejection:
        return []
    produced = Counter(str(unit.get("slot")) for unit in units)
    failing: set[str] = set()
    for error in rejection:
        if error.startswith(_SLOT_SET_ERROR):
            failing.update(slot for slot in task.slots if produced[slot] != 1)
            continue
        owned = _slots_of(task, error)
        if owned is None:
            return []
        failing.update(owned)
    return [slot for slot in task.slots if slot in failing]


def _defects(
    task: SectionTask, rejection: Sequence[str], slots: Sequence[str], content: str
) -> list[str]:
    """The rejection lines that concern ``slots``, whole, plus one line per slot the reply did not
    return exactly once (the slot-set rule's own line names every slot of the section, which would
    mislead a narrowed ask)."""
    produced = Counter(str(unit.get("slot")) for unit in _units(content) or [])
    lines: list[str] = []
    for error in rejection:
        if error.startswith(_SLOT_SET_ERROR):
            continue
        if error.startswith(_TRUNCATED_PREFIX):
            lines.append(_TRUNCATED_DEFECT)
            continue
        owned = _slots_of(task, error) or []
        if set(owned) & set(slots):
            lines.append(error)
    for slot in slots:
        if produced[slot] == 0:
            lines.append(f"unit {slot}: no unit was returned for this slot")
        elif produced[slot] > 1:
            lines.append(f"unit {slot}: returned {produced[slot]} times; return it exactly once")
    return lines


_TRUNCATED_PREFIX = "output truncated"
_TRUNCATED_DEFECT = (
    "the earlier reply was cut off at the output limit before it returned these slots: keep each "
    "unit short, one plain sentence where the slot allows, and leave the explanation of a fact "
    "out rather than run long"
)
_UNITS_KEY = re.compile(r'"units"\s*:\s*\[')


def completed_units(partial: str) -> list[dict[str, Any]]:
    """The units a reply cut off mid-way finished before the cut, in order: the whole ones only,
    never the half-written one. ``[]`` when the text holds no ``units`` array at all."""
    found = _UNITS_KEY.search(partial)
    if found is None:
        return []
    decoder = json.JSONDecoder()
    position = found.end()
    units: list[dict[str, Any]] = []
    while True:
        while position < len(partial) and partial[position] in " \t\r\n,":
            position += 1
        if position >= len(partial) or partial[position] != "{":
            break
        try:
            unit, position = decoder.raw_decode(partial, position)
        except json.JSONDecodeError:
            break
        if isinstance(unit, dict):
            units.append(unit)
    return units


def _complete_truncated(
    task: SectionTask, merged: str, partial: str
) -> tuple[str, list[str]]:
    """``merged`` extended with the units of a reply cut off at the output limit that were finished
    (:func:`completed_units`, for the slots ``merged`` has none for yet), and the slots still
    without exactly one unit, in the task's order (BL-370). ``""`` for the merged reply when no
    unit exists at all."""
    held = _units(merged) or []
    have = {str(unit.get("slot")) for unit in held}
    taken = list(held)
    for unit in completed_units(partial):
        slot = str(unit.get("slot"))
        if slot in task.slots and slot not in have:
            taken.append(unit)
            have.add(slot)
    if not taken:
        return "", list(task.slots)
    order = {slot: index for index, slot in enumerate(task.slots)}
    taken.sort(key=lambda unit: order.get(str(unit.get("slot")), len(order)))
    counted = Counter(str(unit.get("slot")) for unit in taken)
    omitted: dict[str, Any] = {}
    try:
        document = json.loads(merged) if merged else {}
    except json.JSONDecodeError:
        document = {}
    for item in document.get("omitted", []) if isinstance(document, dict) else []:
        if isinstance(item, dict) and "fact_id" in item:
            omitted[str(item["fact_id"])] = item
    missing = [slot for slot in task.slots if counted[slot] != 1]
    return json.dumps({"units": taken, "omitted": list(omitted.values())}), missing


def _listing(units: Sequence[Mapping[str, Any]], limit: int) -> str:
    shown: list[str] = []
    used = 0
    for unit in units:
        line = f"- {unit.get('slot')}: {unit.get('text')}"
        if used + len(line) > limit:
            shown.append(f"- (and {len(units) - len(shown)} more accepted slots)")
            break
        shown.append(line)
        used += len(line)
    return "\n".join(shown)


def _objective(
    task: SectionTask,
    manifest: LoadedManifest,
    slots: Sequence[str],
    content: str,
    rejection: Sequence[str],
    repeated: Sequence[str] = (),
) -> str:
    """The task's objective, re-stated for ``slots`` alone and followed by the correction: the
    complete defect list, the unit each slot is to replace, and the units already accepted. For
    the slots the model returned unchanged after being told (``repeated``) the correction says
    so: the same question put a third time is not a new attempt."""
    base = str(task.packet.get("objective", ""))
    objective = base.replace(slots_clause(task.slots), slots_clause(slots), 1)
    if objective == base and len(slots) != len(task.slots):
        objective = f"{base} {slots_clause(slots)}"
    previous = {str(unit.get("slot")): unit for unit in _units(content) or []}
    template = string.Template(manifest.manifest.rejection_template)
    reasons = template.substitute(
        errors="\n- ".join(_defects(task, rejection, slots, content))
    ).strip()
    again = "\n".join(
        f"- {slot}: {previous[slot].get('text')}"
        if slot in previous
        else f"- {slot}: (none returned)"
        for slot in slots
    )
    earlier = (
        "was accepted for every other slot of this section; only the slots named above are asked "
        "for again"
        if len(slots) < len(task.slots)
        else "was rejected"
    )
    parts = [
        objective,
        f"Correction: an earlier reply to this request {earlier}, and each unit you write "
        "replaces its earlier one entirely, so it keeps everything that unit already said "
        "correctly.",
        f"Earlier text of each slot asked for again:\n{again}",
    ]
    accepted = [unit for slot, unit in previous.items() if slot not in set(slots)]
    if accepted and not task.is_batch:
        parts.append(
            "Already accepted, shown so that you do not repeat it:\n"
            + _listing(accepted, _ACCEPTED_SHOWN_CHARS)
        )
    if repeated:
        parts.append(_REPEATED_NOTE.format(slots=", ".join(repeated)))
    parts.append(reasons)
    return "\n\n".join(parts)


def _narrowed_task(
    task: SectionTask,
    manifest: LoadedManifest,
    slots: Sequence[str],
    content: str,
    rejection: Sequence[str],
    repeated: Sequence[str] = (),
) -> SectionTask:
    wanted = tuple(slot for slot in task.slots if slot in set(slots))
    packet = dict(task.packet)
    packet["slots"] = [
        record
        for record in task.packet.get("slots", [])
        if isinstance(record, dict) and record.get("slot") in set(wanted)
    ]
    packet["objective"] = _objective(task, manifest, wanted, content, rejection, repeated)
    return dataclasses.replace(task, packet=packet, slots=wanted)


def _merge(task: SectionTask, merged: str, narrowed: str, slots: Sequence[str]) -> str:
    """``merged`` with the units of ``slots`` taken from the ``narrowed`` reply and every other
    unit exactly as it was. A narrowed reply that is not exactly the slots asked for is returned
    as it stands, to be refused by the ordinary slot-set rule rather than quietly repaired."""
    try:
        base, extra = json.loads(merged), json.loads(narrowed)
    except json.JSONDecodeError:
        return narrowed
    if not (isinstance(base, dict) and isinstance(extra, dict)):
        return narrowed
    asked = set(slots)
    replaced = [unit for unit in extra.get("units", []) if isinstance(unit, dict)]
    if sorted(str(unit.get("slot")) for unit in replaced) != sorted(asked):
        return narrowed
    kept = [
        unit
        for unit in base.get("units", [])
        if isinstance(unit, dict) and str(unit.get("slot")) not in asked
    ]
    order = {slot: index for index, slot in enumerate(task.slots)}
    units = sorted(
        [*kept, *replaced], key=lambda unit: order.get(str(unit.get("slot")), len(order))
    )
    omitted: dict[str, Any] = {}
    for source in (base, extra):
        for item in source.get("omitted", []):
            if isinstance(item, dict) and "fact_id" in item:
                omitted[str(item["fact_id"])] = item
    return json.dumps({"units": units, "omitted": list(omitted.values())})


def repeated_slots(first: str, second: str, slots: Sequence[str]) -> list[str]:
    """The ``slots`` whose unit ``second`` gives exactly as ``first`` did - text, facts and all.
    The universal re-ask quoted the complete defect list, so a unit returned unchanged was not
    changed by being told: asking for it again with the same defects is the third equivalent
    attempt (Slides-Java, Slides-Cpp, wave 4: the same text three times)."""
    before = {str(unit.get("slot")): unit for unit in _units(first) or []}
    after = {str(unit.get("slot")): unit for unit in _units(second) or []}
    return [slot for slot in slots if slot in before and before[slot] == after.get(slot)]


def authoring_narrowing(task: SectionTask, manifest: LoadedManifest) -> Narrowing:
    """The ``narrow`` argument of ``run_job`` for one section_authoring task: after the job's two
    asks, one more for only the slots whose units are still refused (see the module docstring)."""

    def ask(
        slots: Sequence[str], content: str, rejection: Sequence[str], repeated: Sequence[str]
    ) -> tuple[Mapping[str, Any], dict[str, Any]]:
        narrowed = _narrowed_task(task, manifest, slots, content, rejection, repeated)
        return narrowed.packet, bound_authoring_citations(
            authoring_schema(manifest, narrowed), narrowed, manifest.manifest.sampling.max_output_tokens
        )

    return Narrowing(
        pending=lambda content, rejection: failing_slots(task, content, rejection),
        ask=ask,
        merge=lambda merged, narrowed, slots: _merge(task, merged, narrowed, slots),
        subject="the units still failing",
        repeated=repeated_slots,
        truncated=lambda merged, partial: _complete_truncated(task, merged, partial),
    )


def _without_sentences_naming(text: str, phrases: Sequence[str]) -> str | None:
    """``text`` without each sentence that spells one of ``phrases`` (case-insensitive), the other
    sentences exactly as written; ``None`` when no sentence names one or nothing would be left."""
    pieces = _SENTENCE_BREAK.split(text)
    sentences, separators = pieces[0::2], pieces[1::2]
    lowered = [phrase.lower() for phrase in phrases]
    keep = [
        index
        for index, sentence in enumerate(sentences)
        if not any(phrase in sentence.lower() for phrase in lowered)
    ]
    if not keep or len(keep) == len(sentences):
        return None
    rebuilt = ""
    for position, index in enumerate(keep):
        rebuilt += sentences[index]
        if position < len(keep) - 1:
            rebuilt += separators[index] if index < len(separators) else " "
    return rebuilt.strip()


def recover_restating_sentences(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``section_authoring``'s own ``run_job`` call (``recover=``,
    composed in ``type_fallback``): a unit that restates what the page already prints loses the
    sentences that do, when others remain.

    Two restatements only, each the exact test ``unit_checks`` refuses it by: the slot's own title,
    which is printed immediately before the unit (``restates_own_title``), and a command line the
    renderer prints verbatim in a fenced block right after it (``restated_command_lines``). Both
    are text the reader sees anyway, so dropping the sentence that repeats it loses no claim the
    page does not make, and no word of what remains is changed. A unit that is nothing but the
    restatement is left alone (the job fails as before rather than ship an empty unit), and so is
    a unit that restates neither. ``run_job`` re-validates the result through the real checks.

    Returns ``None`` when nothing was removed, never a no-op copy of ``output``.
    """
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        slot, text = str(unit.get("slot")), unit["text"]
        phrases: list[str] = []
        title = task.slot_titles.get(slot)
        if title and restates_own_title(text, title, facts):
            phrases.append(title)
        phrases.extend(restated_command_lines(text, task.slot_render_lines.get(slot, ())))
        if not phrases:
            continue
        kept = _without_sentences_naming(text, phrases)
        if kept is not None:
            unit["text"] = kept
            changed = True
    return output if changed else None


def recover_targeted_repair_restatements(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for a ``targeted_repair`` job's own final rejected attempt: the same
    recovery ``section_authoring``'s own ``recover=`` already gives a fresh draft
    (:func:`recover_restating_sentences`), applied to ``targeted_repair``'s wrapped
    ``revised_output`` shape instead of a bare units list.

    Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Rust, run 41112836454): a targeted
    repair fixing a real factuality finding ("tests are not reported by the standard test runner")
    rewrote the unit to say ``cargo test --all-targets`` reports 0 tests -- correct per the
    finding's own repair text -- but in doing so restated that exact command, which the renderer
    already prints verbatim in a fenced block right after the unit. Rejected for a real but
    different reason than the one the repair was fixing, and the job's own two asks were spent on
    the original finding, not this new restatement -- ``repair/loop.py``'s own ``_repair_section``
    passed only ``recover_title_verbatim_opening`` (a narrower, title-only recovery) as its
    ``recover=``, never this module's own general restatement recovery.
    """
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return None
    fixed = recover_restating_sentences(revised, task=task, facts=facts)
    if fixed is None:
        return None
    output = dict(output)
    output["revised_output"] = fixed
    return output


def recover_targeted_repair_dropped_citation(
    output: dict[str, Any], *, original: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Last-resort correction for a ``targeted_repair`` job's own final rejected attempt: restore
    an ``inherited_unit:*`` citation a revised unit's own fact_ids dropped relative to the same
    slot's original fact_ids.

    Measured live (aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp, run 41156451223): a BC-08 repair
    correctly restored a dropped protected command, but its own reply also re-cited the unit's
    fact_ids from ``[inherited_unit:028.paragraph]`` to ``[package:name]`` -- a change the repair
    was never asked for. ``cited_inherited_identifiers`` only exempts tokens spelled verbatim
    inside a SUPPORTED ``inherited_unit`` fact named in a unit's own fact_ids; dropping that
    citation un-exempted the unit's own already-rendered filenames (``aspose_pdf_foss.lib``,
    ``libaspose_pdf_foss.a``), rejecting the repair for an identifier violation the original,
    accepted unit never had. A targeted repair's job is to patch the content a defect names, not
    to re-decide which facts a unit cites, so any ``inherited_unit:*`` id the original unit cited
    is restored (added back, never removed) for the same slot in the revised unit.
    """
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return None
    original_units = {
        unit.get("slot"): unit
        for unit in original.get("units", [])
        if isinstance(unit, dict)
    }
    changed = False
    fixed_units = []
    for unit in revised.get("units", []):
        if not isinstance(unit, dict):
            fixed_units.append(unit)
            continue
        prior = original_units.get(unit.get("slot"))
        if isinstance(prior, dict):
            dropped = [
                fact_id
                for fact_id in prior.get("fact_ids", [])
                if isinstance(fact_id, str)
                and fact_id.startswith("inherited_unit:")
                and fact_id not in unit.get("fact_ids", [])
            ]
            if dropped:
                unit = dict(unit)
                unit["fact_ids"] = [*unit.get("fact_ids", []), *dropped]
                changed = True
        fixed_units.append(unit)
    if not changed:
        return None
    fixed_revised = dict(revised)
    fixed_revised["units"] = fixed_units
    output = dict(output)
    output["revised_output"] = fixed_revised
    return output


_SPELLING_MIN_CHARS = 3


def withdraw_out_of_slot_citations(
    unit: dict[str, Any], allowed: Collection[str], facts: FactsDocument
) -> bool:
    """Remove, from ``unit`` in place, every citation outside ``allowed`` together with the
    sentences that spell the cited fact's own value; ``False`` (``unit`` untouched) when that is
    not possible.

    Only deletions: no citation is added and no word of a remaining sentence changes. A citation
    is removed only when some sentence spells its value, so the sentence it supports is known and
    goes with it; a fact no sentence spells could be supporting any sentence, so nothing is
    guessed and the unit is left for the caller to fail closed. A unit with nothing left is left
    alone too. The caller re-validates the result through the real checks."""
    text, cited = unit.get("text"), unit.get("fact_ids")
    if not isinstance(text, str) or not isinstance(cited, list):
        return False
    outside = [fact_id for fact_id in cited if fact_id not in allowed]
    if not outside:
        return False
    by_id = {fact.id: fact for fact in facts.facts}
    phrases: list[str] = []
    for fact_id in outside:
        fact = by_id.get(fact_id)
        value = " ".join(fact.value.split()).lower() if fact is not None else ""
        if len(value) < _SPELLING_MIN_CHARS or value not in text.lower():
            return False
        phrases.append(value)
    kept = _without_sentences_naming(text, phrases)
    if kept is None:
        return False
    unit["text"] = kept
    unit["fact_ids"] = [fact_id for fact_id in cited if fact_id in allowed]
    return True


def recover_out_of_slot_citations(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``section_authoring``'s own ``run_job`` call (``recover=``): a
    unit that cites a fact outside its own slot's set (``citable``) loses that citation and the
    sentence it supports (:func:`withdraw_out_of_slot_citations`), when others remain. Returns
    ``None`` when nothing was removed."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or unit.get("slot") not in task.slots:
            continue
        if withdraw_out_of_slot_citations(unit, citable(task, str(unit["slot"])), facts):
            changed = True
    return output if changed else None


#: Where an API-row fallback is recorded for the run's evidence: ``run_job`` pops this key from a
#: recovered reply before re-validating it and writes it into the ``.repaired-<attempt>.json``
#: record beside the call store (``CallStore.record_repairs``), with the slots, symbols and the
#: rejection lines each fallback answered.
RECOVERY_NOTES_KEY = "_recovery_notes"


def recover_failing_api_rows(
    output: dict[str, Any],
    *,
    task: SectionTask,
    facts: FactsDocument,
    checks: Callable[[dict[str, Any]], Sequence[str]],
) -> dict[str, Any] | None:
    """Owner ruling R43(4) (BL-104): a ``type:`` or ``hub:`` unit that still fails its checks
    after every ask is blanked - left out of ``units`` and recorded in ``omitted`` against its
    symbol fact with :data:`authoring.API_ROW_FALLBACK_REASON` - so the renderer prints that
    type's fact-true row (``renderer._symbol_description``: docstring, else signature or enum
    values, else "Public <kind>.") instead of the job failing. Fallback only, never render-all:
    a unit that passes is kept as written, and the model still writes every row.

    Only when every remaining rejection line belongs to a ``type:``/``hub:`` slot: with any
    other defect left the job fails as before, so a fallback never hides one. A unit that cites
    an inherited unit the section must carry is not blanked (its substance would lose its only
    carrier, R14). Real rejected shapes: enum members the facts do not list (PDF Java
    ``Permissions``, Words .NET ``RevisionType``), HTML in a summary (HTML Python
    ``HTMLAnchorElement`` "<a>"), unknown identifiers (Cells C++ ``uint8_t``, Imaging ``DjVu``).

    ``checks`` is the job's own ``unit_checks`` closure, run on a copy (it normalises in place).
    Returns ``None`` when nothing was blanked."""
    from repo_presenter.readme.composition.authoring import (
        API_ROW_FALLBACK_REASON,
        API_ROW_SLOT_PREFIXES,
    )

    units = output.get("units")
    if not isinstance(units, list):
        return None
    rejection = list(checks(copy.deepcopy(output)))
    if not rejection:
        return None
    failing: dict[str, list[str]] = {}
    returned = Counter(str(unit.get("slot")) for unit in units if isinstance(unit, dict))
    for error in rejection:
        if error.startswith(_SLOT_SET_ERROR):
            # A type:/hub: slot the reply left out is a failing row too; any other slot-set
            # fault (a missing prose slot, a slot returned twice) is not an API row.
            absent = [slot for slot in task.slots if returned[slot] != 1]
            if not absent or any(
                returned[slot] or not slot.startswith(API_ROW_SLOT_PREFIXES) for slot in absent
            ):
                return None
            for slot in absent:
                failing.setdefault(slot, []).append(error)
            continue
        owned = _slots_of(task, error)
        if owned is None or not owned[0].startswith(API_ROW_SLOT_PREFIXES):
            return None
        failing.setdefault(owned[0], []).append(error)
    by_slot = {str(unit.get("slot")): unit for unit in units if isinstance(unit, dict)}
    for slot in failing:
        cited = by_slot.get(slot, {}).get("fact_ids") or []
        if any(fact_id in task.must_carry for fact_id in cited):
            return None
    known = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    notes: list[dict[str, Any]] = []
    omitted = [item for item in output.get("omitted", []) if isinstance(item, dict)]
    for slot, errors in failing.items():
        symbol = slot.split(":", 1)[1]
        if symbol not in known:
            return None
        if not any(item.get("fact_id") == symbol for item in omitted):
            omitted.append({"fact_id": symbol, "reason": API_ROW_FALLBACK_REASON})
        notes.append(
            {
                "fallback": "api_row",
                "ruling": "R43(4)",
                "slot": slot,
                "symbol_fact_id": symbol,
                "rejected_text": str(by_slot.get(slot, {}).get("text", "")),
                "rejection": errors,
            }
        )
    kept = [
        unit for unit in units if not (isinstance(unit, dict) and str(unit.get("slot")) in failing)
    ]
    if not kept:
        # The output contract holds at least one unit (``units.minItems``), so when every row of a
        # batch fails, one of them carries the fact-true sentence itself - the same words the
        # renderer's fallback row would print - instead of being left out.
        slot = sorted(failing, key=lambda s: (not _is_enum_slot(s, facts), task.slots.index(s)))[0]
        symbol = slot.split(":", 1)[1]
        kept = [
            {
                "section": task.section_id,
                "slot": slot,
                "text": fact_true_type_sentence(symbol, facts),
                "fact_ids": [symbol],
            }
        ]
        omitted = [item for item in omitted if item.get("fact_id") != symbol]
        for note in notes:
            if note["slot"] == slot:
                note["fallback"] = "api_row_fact_true_unit"
                note["text"] = kept[0]["text"]
        candidate = {**output, "units": kept, "omitted": omitted}
        candidate.pop(RECOVERY_NOTES_KEY, None)
        if list(checks(copy.deepcopy(candidate))):
            return None
    output["units"] = kept
    output["omitted"] = omitted
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def _is_enum_slot(slot: str, facts: FactsDocument) -> bool:
    fact = next((f for f in facts.facts if f.id == slot.split(":", 1)[1]), None)
    return fact is not None and (fact.attributes or {}).get("symbol_kind") == "enum"


def fact_true_type_sentence(symbol_id: str, facts: FactsDocument) -> str:
    """The fact-true sentence for one public type with no usable authored one: an enum's verified
    values ("Enumerates A, B and C."), else "Public <kind>." - the renderer's own fallback words
    (``renderer._described``), with no identifier beyond the type's own verified values."""
    from repo_presenter.readme.composition.authoring import type_values

    fact = next((f for f in facts.facts if f.id == symbol_id), None)
    kind = str((fact.attributes or {}).get("symbol_kind", "symbol")) if fact else "symbol"
    if fact is not None and kind == "enum":
        values = type_values(fact, facts, limit=len(facts.facts))
        shown = values[:8]
        if shown:
            listed = ", ".join(shown[:-1]) + (" and " if len(shown) > 1 else "") + shown[-1]
            lead = "Enumerates values including" if len(values) > len(shown) else "Enumerates"
            return f"{lead} {listed}."
    return f"Public {kind}."


_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")


def _without_values(text: str, name: str, facts: FactsDocument) -> str | None:
    """``text`` with no value R43(2) forbids (:func:`authoring.value_tokens`), by deletion only:
    each sentence that spells one goes when another sentence is left; otherwise each parenthesis
    that spells one goes when what is left spells none. ``None`` when neither removes them all, so
    the caller fails closed rather than ship a value or an empty unit. No word is rewritten."""
    if not value_tokens(text, name, facts):
        return None
    pieces = _SENTENCE_BREAK.split(text)
    sentences, separators = pieces[0::2], pieces[1::2]
    keep = [i for i, sentence in enumerate(sentences) if not value_tokens(sentence, name, facts)]
    if keep and len(keep) < len(sentences):
        rebuilt = ""
        for position, index in enumerate(keep):
            rebuilt += sentences[index]
            if position < len(keep) - 1:
                rebuilt += separators[index] if index < len(separators) else " "
        return rebuilt.strip()
    stripped = _PARENTHETICAL.sub(
        lambda match: "" if value_tokens(match.group(0), name, facts) else match.group(0), text
    ).strip()
    if stripped and stripped != text and not value_tokens(stripped, name, facts):
        return stripped
    return None


def recover_value_sentences(
    output: dict[str, Any], *, task: SectionTask, facts: FactsDocument, name: str
) -> dict[str, Any] | None:
    """Last-resort correction for an opening or key-capability ``section_authoring`` reply still
    refused for R43(2)'s no-values rule after every ask (BL-170): the sentence, or the parenthesis,
    that spells the number, count, file or key name is removed (:func:`_without_values`), and the
    rest of the unit is kept as written. Before it, one stray number (Words Java, hosted run
    43672441969: the opening's ``'8'``, ``'2003'``) cost the whole paid Lane R run as a job error.
    ``run_job`` re-validates the result through the real checks. ``None`` when nothing changed."""
    if task.section_id not in VALUE_FREE_SECTIONS or not name:
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        kept = _without_values(unit["text"], name, facts)
        if kept is not None:
            unit["text"] = kept
            changed = True
    return output if changed else None


#: The rule id a terminal-safe fallback (BL-220, R46) writes into the repair notes beside the call
#: store (``.repaired-<attempt>.json``): R14, every deviation recorded with a rule id and evidence.
TERMINAL_SAFE_RULE = "BL-220"
TERMINAL_SAFE_RULE_370 = "BL-370"
TERMINAL_SAFE_RULE_460 = "BL-460"


def _fact_true_opening_unit(
    unit: dict[str, Any], *, facts: FactsDocument, name: str
) -> dict[str, Any] | None:
    """The one sentence the format facts state about the product ("<name> reads A and writes B
    files.", the words ``renderer._scope_statement`` prints) as an opening unit citing those facts,
    or ``None`` when the facts hold no format."""
    from repo_presenter.readme.composition.renderer import format_name

    directions: dict[str, list[str]] = {"input": [], "output": []}
    cited: list[str] = []
    for fact in facts.by_kind("format"):
        if fact.polarity != "SUPPORTED":
            continue
        direction = fact.id.split(":", 1)[-1].split(".", 1)[0]
        label = format_name(fact.value)
        if direction in directions:
            cited.append(fact.id)
            if label not in directions[direction]:
                directions[direction].append(label)
    reads, writes = directions["input"], directions["output"]

    def listed(items: list[str]) -> str:
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]

    if reads and writes:
        text = f"{name} reads {listed(reads)} files and writes {listed(writes)} files."
    elif reads:
        text = f"{name} reads {listed(reads)} files."
    elif writes:
        text = f"{name} writes {listed(writes)} files."
    else:
        return None
    return {**unit, "text": text, "fact_ids": cited}


def _release_restated_opening(
    output: dict[str, Any],
    index: int,
    unit: dict[str, Any],
    placeholder: dict[str, Any] | None,
    *,
    task: SectionTask,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
) -> dict[str, Any] | None:
    """BL-580: the opening says nothing the maintainers' paragraph printed beside it lacks and no fact-true
    sentence of its own adds anything (the facts state no format, or the format sentence is stated by that
    paragraph too, hosted HTML Python 44916810423 and PSD Python 44898209273): the slot is released on the
    record (``OPENING_RESTATED_OMISSION_REASON``, an R14 decision) and that paragraph is the opening. The
    reply keeps a placeholder unit (the job's schema owes the section one), which ``merge_units`` drops; the
    omission cites a fact, and each inherited unit the opening carried (all kept verbatim, else nothing is
    released) is listed omitted with the reason so BC-04 and the carry rule still account for it. ``None``
    when anything the opening says would be lost."""
    kept = {
        str(row.get("unit_id"))
        for row in dispositions.get("dispositions", [])
        if row.get("disposition") in _VERBATIM_PRESERVED_DISPOSITIONS
    }
    if not opening_releasable(unit, dispositions=dispositions, facts=facts):
        return None
    if any(str(fact_id) not in kept for fact_id in task.must_carry):
        return None
    known = {fact.id for fact in facts.facts}
    cited = [
        str(f) for f in unit.get("fact_ids") or [] if str(f).startswith("inherited_unit:") and str(f) in known
    ]
    cited += [str(f) for f in sorted(task.must_carry) if str(f) not in cited]
    anchor = [fid for fid in ("package:name", "identity:repository") if fid in known][:1]
    ids = list(dict.fromkeys(cited or anchor))
    if not ids:
        return None
    if placeholder is not None:
        output["units"][index] = placeholder
    omitted = [item for item in output.get("omitted") or [] if isinstance(item, dict)]
    omitted.extend({"fact_id": fid, "reason": OPENING_RESTATED_OMISSION_REASON} for fid in ids)
    output["omitted"] = omitted
    return {
        "fallback": "opening_released_for_preserved_paragraph",
        "rule": "BL-580",
        "slot": str(unit.get("slot")),
        "rejected_text": str(unit.get("text")),
        "rejection": "restates the inherited paragraph the renderer preserves verbatim",
        "text": "",
    }


def recover_restated_opening(
    output: dict[str, Any],
    *,
    task: SectionTask,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
    name: str,
) -> dict[str, Any] | None:
    """Terminal-safe floor for an opening that, after the trim of ``recover_opening_output``, still
    only restates the inherited paragraph the renderer preserves verbatim beside it (BL-220;
    hosted Font Python run 44297210403): the unit becomes the format-facts sentence
    (:func:`_fact_true_opening_unit`). The inherited paragraph is kept as it was (R14), the unit
    is re-validated by ``run_job`` through the real checks, and the replacement is recorded in the
    repair notes. ``None`` when the opening does not restate it or the facts state no format."""
    preserved = preserved_section_text(dispositions, facts, "opening")
    units = output.get("units")
    if not preserved or not isinstance(units, list):
        return None
    notes: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        text = unit.get("text") if isinstance(unit, dict) else None
        if not isinstance(text, str):
            continue
        if not (states_all(preserved, text) or states_all(text, preserved)):
            continue
        replaced = _fact_true_opening_unit(unit, facts=facts, name=name)
        placeholder = None
        if replaced is not None and opening_adds_nothing(
            replaced["text"], dispositions=dispositions, facts=facts
        ):
            # BL-580: the format sentence is itself stated by the maintainers' paragraph (hosted PSD
            # Python 44898209273: "reads PSD files" against "reading ... Adobe Photoshop files").
            placeholder, replaced = replaced, None
        if replaced is None:
            released = _release_restated_opening(
                output, index, unit, placeholder, task=task, facts=facts, dispositions=dispositions
            )
            if released is not None:
                notes.append(released)
            continue
        units[index] = replaced
        notes.append(
            {
                "fallback": "opening_fact_true_sentence",
                "rule": TERMINAL_SAFE_RULE,
                "slot": str(unit.get("slot")),
                "rejected_text": text,
                "rejection": "restates the inherited paragraph the renderer preserves verbatim",
                "text": replaced["text"],
            }
        )
    if not notes:
        return None
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def recover_opening_output(
    output: dict[str, Any],
    *,
    task: SectionTask,
    facts: FactsDocument,
    dispositions: Mapping[str, Any],
    name: str,
) -> dict[str, Any] | None:
    """The one ``recover=`` for the opening task: the preserved-paragraph trim
    (``authoring.recover_opening_duplicates_preserved``), then the no-values deletion
    (:func:`recover_value_sentences`), then, for what still only restates the inherited paragraph,
    the format-facts floor (:func:`recover_restated_opening`, BL-220)."""
    unowed = recover_unowed_omissions(output, task=task)
    output = output if unowed is None else unowed
    headed = recover_heading_markers(output)
    output = output if headed is None else headed
    trimmed = recover_opening_duplicates_preserved(output, dispositions=dispositions, facts=facts)
    current = output if trimmed is None else trimmed
    valued = recover_value_sentences(current, task=task, facts=facts, name=name)
    best = valued if valued is not None else trimmed
    if best is None:
        best = headed if headed is not None else unowed
    floored = recover_restated_opening(
        output if best is None else best,
        task=task, facts=facts, dispositions=dispositions, name=name,
    )
    return floored if floored is not None else best


_EDITION_NAME = "Enterprise Edition"
#: Where a clause may be cut off before the edition name: a comma, semicolon, dash or bracket.
_CLAUSE_CUT = re.compile(r"\s*(?:[,;(]|\s[\u2014\u2013-]\s)\s*")


#: The edition name as the subject that opens a sentence ("The Enterprise Edition adds ...",
#: "Aspose.Widget Enterprise Edition adds ...") and as the object of a closing prepositional phrase
#: ("... available in the Enterprise Edition") (BL-370).
_EDITION_SUBJECT = re.compile(
    r"^(?:(?:The|This|That|Our)\s+)?(?:[A-Z][\w.\-]*\s+){0,6}?Enterprise Edition(?=\s+[a-z])"
)
_EDITION_TAIL = re.compile(
    r"\s+(?:in|with|via|through|by|from|under|within|of)\s+(?:the\s+|our\s+|that\s+)?"
    r"(?:[A-Z][\w.\-]*\s+){0,6}?Enterprise Edition\b[.!?]?$"
)


def _edition_phrase_removed(text: str) -> str | None:
    """``text`` of one sentence with the edition named only as its subject read as ``It`` (the
    shell's closing sentence has just named it, and the prompt asks for 'It adds ...'), or as the
    object of a closing prepositional phrase cut off; the rest exactly as written. ``None`` when
    neither applies or a mention is left."""
    sentence = text.strip()
    rewritten = _EDITION_SUBJECT.sub("It", sentence, count=1)
    if rewritten != sentence and _EDITION_NAME not in rewritten:
        return rewritten
    tail = _EDITION_TAIL.search(sentence)
    if tail is not None:
        stem = sentence[: tail.start()].rstrip(" ,;")
        if len(stem.split()) >= 4 and _EDITION_NAME not in stem:
            return stem if stem.endswith((".", "!", "?")) else stem + "."
    return None


def _without_edition_name(text: str) -> str | None:
    """``text`` with no mention of the Enterprise Edition, by deletion only: each sentence that
    names it goes when another is left; otherwise the sentence is cut back before the clause
    (comma, semicolon, dash, bracket) that names it, when four or more words stay. ``None`` when
    nothing honest is left (fail closed), so no word is rewritten and no empty unit is shipped."""
    if _EDITION_NAME not in text:
        return None
    kept = _without_sentences_naming(text, [_EDITION_NAME])
    if kept is not None:
        return kept
    sentence = text.strip()
    head = sentence[: sentence.find(_EDITION_NAME)]
    for match in reversed(list(_CLAUSE_CUT.finditer(head))):
        stem = head[: match.start()].rstrip()
        if len(stem.split()) >= 4:
            return stem if stem.endswith((".", "!", "?")) else stem + "."
    return _edition_phrase_removed(text)


_HEADING_LEAD = re.compile(r"^\s*#{1,6}\s+")


def recover_heading_markers(output: dict[str, Any]) -> dict[str, Any] | None:
    """Terminal-safe correction for a unit that still opens with a Markdown heading marker
    (BL-370): the ``#`` run is deleted and the words stay exactly as written (a heading echo is
    the only place a ``#`` can be a heading in a one-paragraph unit; ``C#`` inside a sentence is
    prose and is no longer refused, ``authoring._HEADING_START``). Recorded in the repair notes;
    ``run_job`` re-validates. ``None`` when no unit opens with one or nothing would be left."""
    units = output.get("units")
    if not isinstance(units, list):
        return None
    notes: list[dict[str, Any]] = []
    for unit in units:
        text = unit.get("text") if isinstance(unit, dict) else None
        if not isinstance(text, str) or _HEADING_LEAD.match(text) is None:
            continue
        kept = _HEADING_LEAD.sub("", text, count=1).strip()
        if not kept:
            continue
        notes.append(
            {
                "fallback": "heading_marker_deleted",
                "rule": TERMINAL_SAFE_RULE_370,
                "slot": str(unit.get("slot")),
                "rejected_text": text,
                "text": kept,
            }
        )
        unit["text"] = kept
    if not notes:
        return None
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def recover_edition_name(output: dict[str, Any], *, task: SectionTask) -> dict[str, Any] | None:
    """Terminal-safe correction for the enterprise-relationship unit that still names the
    Enterprise Edition after every ask (BL-220; hosted Cells C++ run 44291563956): the shell's
    closing sentence names it once, so the sentence or clause that names it is deleted
    (:func:`_without_edition_name`) and the rest is kept as written. Recorded in the repair notes;
    ``run_job`` re-validates. ``None`` when nothing honest remains."""
    if task.section_id != "enterprise_relationship":
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    notes: list[dict[str, Any]] = []
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        kept = _without_edition_name(unit["text"])
        if kept is not None:
            notes.append(
                {
                    "fallback": "edition_name_deleted",
                    "rule": TERMINAL_SAFE_RULE,
                    "slot": str(unit.get("slot")),
                    "rejected_text": unit["text"],
                    "text": kept,
                }
            )
            unit["text"] = kept
    if not notes:
        return None
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def recover_failing_capabilities(
    output: dict[str, Any],
    *,
    task: SectionTask,
    facts: FactsDocument,
    checks: Callable[[dict[str, Any]], Sequence[str]],
) -> dict[str, Any] | None:
    """Terminal-safe floor for a key-capability unit that still fails its checks after every ask
    and every deletion (BL-170's residual; hosted PDF .NET run 43683719616, PDF C++ 43664910650):
    the unit is replaced by the fact-true sentence of a public type its own slot cites
    (:func:`fact_true_type_sentence`, the words the API-row fallback prints), the way R43(4) treats
    an API row. Only when every rejection line belongs to a ``capability:`` slot, the slot cites no
    inherited unit the section must carry (R14: that substance would lose its carrier), and the
    slot cites such a type; otherwise ``None`` and the job fails as before, never hiding another
    defect. ``run_job`` re-validates the result through the real checks."""
    if task.section_id != "key_capabilities":
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    rejection = list(checks(copy.deepcopy(output)))
    if not rejection:
        return None
    failing: set[str] = set()
    for error in rejection:
        owned = _slots_of(task, error)
        if owned is None or not owned[0].startswith("capability:"):
            return None
        failing.add(owned[0])
    symbols = {
        fact.id
        for fact in facts.facts
        if fact.polarity == "SUPPORTED" and (fact.attributes or {}).get("symbol_kind")
    }
    notes: list[dict[str, Any]] = []
    for unit in units:
        slot = str(unit.get("slot")) if isinstance(unit, dict) else ""
        if slot not in failing:
            continue
        cited = [str(i) for i in unit.get("fact_ids") or []]
        if any(i in task.must_carry for i in cited):
            return None
        symbol = next((i for i in sorted({*cited, *task.slot_facts.get(slot, ())}) if i in symbols), None)
        if symbol is None:
            return None
        text = fact_true_type_sentence(symbol, facts)
        notes.append(
            {
                "fallback": "capability_fact_true_sentence",
                "rule": TERMINAL_SAFE_RULE,
                "slot": slot,
                "symbol_fact_id": symbol,
                "rejected_text": str(unit.get("text", "")),
                "text": text,
            }
        )
        unit["text"] = text
        unit["fact_ids"] = [symbol]
    if not notes:
        return None
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def recover_unowed_omissions(output: dict[str, Any], *, task: SectionTask) -> dict[str, Any] | None:
    """Terminal-safe correction for an ``omitted`` list longer than the section can owe (BL-460;
    hosted Slides C++ run 44673592648: ``$.omitted: [...31 entries] is too long`` three times, the
    units themselves accepted). The prompt asks every accepted fact a unit does not cite to be
    listed with a reason; the model also listed the ``do_not_claim`` records (contradicted
    examples, unresolved formats) and repeated ids, so the list outgrew the schema's bound, which
    is the number of distinct facts the task offers (``output_bounds.omittable_ids``). An entry
    for a fact the task never offered accounts for nothing owed (``carried_unit_errors`` reads only
    the must-carry ids, which are offered), is never printed and is dropped; a repeated id keeps
    its first entry. Every dropped entry is recorded in the repair notes (R14); ``run_job``
    re-validates. ``None`` when every entry is an offered fact listed once."""
    omitted = output.get("omitted")
    if not isinstance(omitted, list):
        return None
    offered = omittable_ids(task)
    kept: list[Any] = []
    seen: set[str] = set()
    notes: list[dict[str, Any]] = []
    for item in omitted:
        fact_id = item.get("fact_id") if isinstance(item, dict) else None
        if not isinstance(fact_id, str):
            kept.append(item)
            continue
        if fact_id not in offered or fact_id in seen:
            notes.append(
                {
                    "fallback": "unowed_omission_dropped",
                    "rule": TERMINAL_SAFE_RULE_460,
                    "fact_id": fact_id,
                    "why": "repeated" if fact_id in seen else "not offered to this section",
                    "reason": item.get("reason"),
                }
            )
            continue
        seen.add(fact_id)
        kept.append(item)
    if not notes:
        return None
    output["omitted"] = kept
    output[RECOVERY_NOTES_KEY] = [*output.get(RECOVERY_NOTES_KEY, []), *notes]
    return output


def recover_authoring_output(
    output: dict[str, Any],
    *,
    task: SectionTask,
    facts: FactsDocument,
    checks: Callable[[dict[str, Any]], Sequence[str]] | None = None,
    name: str = "",
) -> dict[str, Any] | None:
    """The one ``recover=`` for a section_authoring task other than the opening: every last-resort
    correction of this module, in order, ending with the API-row fallback
    (:func:`recover_failing_api_rows`) when the job's ``checks`` are given. With the product
    ``name``, a key-capability unit also loses a value it spells (:func:`recover_value_sentences`)."""
    unowed = recover_unowed_omissions(output, task=task)
    output = output if unowed is None else unowed
    headed = recover_heading_markers(output)
    output = output if headed is None else headed
    valued = recover_value_sentences(output, task=task, facts=facts, name=name)
    output = output if valued is None else valued
    restated = recover_restating_sentences(output, task=task, facts=facts)
    restated = restated if restated is not None else valued
    withdrawn = recover_out_of_slot_citations(
        output if restated is None else restated, task=task, facts=facts
    )
    recovered = withdrawn if withdrawn is not None else restated
    if recovered is None:
        recovered = headed
    edition = recover_edition_name(output if recovered is None else recovered, task=task)
    recovered = edition if edition is not None else recovered
    if checks is not None:
        fallen = recover_failing_api_rows(
            output if recovered is None else recovered, task=task, facts=facts, checks=checks
        )
        if fallen is not None:
            return fallen
        floored = recover_failing_capabilities(
            output if recovered is None else recovered, task=task, facts=facts, checks=checks
        )
        if floored is not None:
            return floored
    return recovered if recovered is not None else unowed
