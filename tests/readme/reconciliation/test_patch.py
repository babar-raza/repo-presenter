"""The repair of a disposition as a per-unit patch (wave 4, BC-05 v7 content loss).

Eight of nine BC-05 failures reached ``targeted_repair`` and none was repaired by it. 3D-Java's two
retained replies are the case: the first moved the Gradle Kotlin DSL snippet back into
``installation`` (a free-string destination), the second handed back the same deferral, and each was
refused for its own ledger ("change R02 claims 'dispositions.15.disposition' changed ... the
causal stage's own input and this revision hold the identical value") because the model counted the
unit's position in *its* one-unit reply and the check counted it in the stored batch.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repo_presenter.core.facts import Fact, FactsDocument, read_facts
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.reconciliation import dispositions as d
from repo_presenter.readme.reconciliation.patch import (
    PATCH_UNITS,
    condensed,
    failing_units,
    patch_checks,
    patch_scope,
    target_batch,
    unit_changes,
)
from repo_presenter.readme.repair.targeted import (
    Defect,
    repair_checks,
    repair_schema,
)
from tests.support import REPO_ROOT

FIXTURES = Path(__file__).parent / "fixtures"
CASES = json.loads(
    (FIXTURES / "wave4_s4_content_loss.json").read_text(encoding="utf-8")
)
JAVA = CASES["3d_java"]
REPAIR = JAVA["repair"]
PROMPTS = load_manifests(REPO_ROOT / "prompts")
RECONCILIATION = PROMPTS["source_reconciliation"]
REPAIR_PROMPT = PROMPTS["targeted_repair"]
KOTLIN = "inherited_unit:016.code_block"
LABEL = "inherited_unit:015.paragraph"


def _facts() -> tuple[FactsDocument, list[Fact], FactsDocument]:
    facts = read_facts(FIXTURES / "wave4_3d_java.facts.json")
    units = [
        fact
        for fact in facts.by_kind("inherited_unit")
        if fact.id in set(JAVA["install_units"])
    ]
    return facts, units, d.reconciliation_batch_facts(facts, units)


def _stored() -> dict[str, Any]:
    """The batch as the old code left it: the retained re-ask reply, with the Kotlin snippet's
    claim withdrawn into a deferral, as are the other code blocks Installation cannot print (the old
    repository's ``_recover_uncovered`` fold, which this repository has not ported, did this)."""
    _, _, batch_facts = _facts()
    stored = {"dispositions": copy.deepcopy(JAVA["install_reply_2"])}
    d.normalize(stored, batch_facts)
    for entry in stored["dispositions"]:
        if entry["unit_id"].endswith(".code_block"):
            entry.update(disposition="DEFER_UNRESOLVED", destination_section=None)
            entry["rationale"] = d.RECOVERED_COVERAGE_RATIONALE
    return stored


def _record(*units: str, detail: str | None = None) -> dict[str, Any]:
    failure = {**REPAIR["failure"], **({"unit_id": units[0]} if units else {})}
    return {
        "id": "BC-05",
        "name": "dispositions",
        "causal_stage": "RECONCILING",
        "details": [detail or failure["detail"]],
        "failures": [{**REPAIR["failure"], "unit_id": unit} for unit in units],
    }


def _scope(record: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    facts, units, _ = _facts()
    return patch_scope(
        record if record is not None else _record(KOTLIN),
        {"reconciliation#1": _stored()},
        {"reconciliation#1": units},
        facts,
        RECONCILIATION,
        {},
        REPAIR_PROMPT.manifest.sampling.max_output_tokens,
    )


def _defect(record: dict[str, Any]) -> Defect:
    return Defect(
        REPAIR["reply_1"]["fingerprint"], "validation", "BC-05", None, "S4", record
    )


def _checks(scope: Any):  # type: ignore[no-untyped-def]
    _, _, batch_facts = _facts()
    return patch_checks(scope, lambda revised: d.reconcile_checks(revised, batch_facts))


def _judge(reply: dict[str, Any], scope: Any) -> tuple[list[str], dict[str, Any]]:
    """The repair's own checks over a reply, as ``run_job`` runs them; the checked output."""
    _, _, batch_facts = _facts()
    output = copy.deepcopy(reply)
    errors = repair_checks(
        output,
        _defect(_record(KOTLIN)),
        RECONCILIATION.manifest.output.schema_,
        "unit_ids",
        batch_facts,
        stage_checks=_checks(scope),
        original=_stored(),
        patch_contract=scope.contract,
        derive_changes=unit_changes,
    )
    return errors, output


# ---- who is at fault ------------------------------------------------------------------------


def test_the_units_at_fault_are_read_from_the_failure_records_field_not_their_sentence() -> (
    None
):
    sentence_only = {
        "failures": [{k: v for k, v in REPAIR["failure"].items()}]
    }  # as the run wrote it
    assert KOTLIN in sentence_only["failures"][0]["detail"]
    assert (
        failing_units(sentence_only) == []
    )  # a unit named only in prose is not a field
    assert failing_units(_record(KOTLIN)) == [KOTLIN]
    merged = {
        **_record(KOTLIN),
        "equivalent_findings": [
            _record("inherited_unit:018.code_block"),
            _record(KOTLIN),
        ],
    }
    assert failing_units(merged) == [KOTLIN, "inherited_unit:018.code_block"]


def test_the_batch_is_the_one_holding_the_unit_not_the_first() -> None:
    _, units, _ = _facts()
    other = [
        Fact("inherited_unit:200.paragraph", "inherited_unit", "x", units[0].evidence)
    ]
    batches = {"reconciliation#1": other, "reconciliation#2": units}
    available = {"reconciliation#1", "reconciliation#2"}
    assert target_batch(_record(KOTLIN), batches, available) == "reconciliation#2"
    assert (
        target_batch(_record(), batches, available) is None
    )  # names none: the first, as before
    assert target_batch(_record(KOTLIN), batches, {"reconciliation#1"}) is None


# ---- the scope and its contract -------------------------------------------------------------


def test_the_scope_is_the_unit_and_the_label_that_introduces_it() -> None:
    scope = _scope()
    assert scope is not None
    assert scope.unit_ids == (
        LABEL,
        KOTLIN,
    )  # document order; the label travels with its block
    shown = {entry["unit_id"]: entry for entry in scope.shown["dispositions"]}
    assert shown[KOTLIN]["unit_text"].startswith("```kotlin")
    assert shown[KOTLIN]["nearest_section_that_can_hold_it"] == "development_testing"
    assert shown[KOTLIN]["source_heading"].endswith("Installation")
    assert scope.deferred == {KOTLIN}  # the block is withheld
    # nothing else of the 155-unit batch's size is shown or asked for
    assert len(scope.shown["dispositions"]) == 2


def test_a_budget_no_reply_can_meet_keeps_the_whole_batch_repair() -> None:
    """Not even one disposition fits a repair budget this small: the patch is not offered (a
    ConfigError here would take the transaction down), and the earlier repair runs."""
    facts, units, _ = _facts()
    scope = patch_scope(
        _record(KOTLIN),
        {"reconciliation#1": _stored()},
        {"reconciliation#1": units},
        facts,
        RECONCILIATION,
        {},
        700,
    )
    assert scope is None


def test_a_defect_that_names_no_unit_keeps_the_whole_batch_repair() -> None:
    assert _scope(_record()) is None
    assert _scope({"failures": [REPAIR["failure"]]}) is None
    assert _scope(_record("inherited_unit:999.paragraph")) is None  # not in any batch


def test_the_reply_contract_is_bounded_to_those_units_and_the_sections_that_can_hold_them() -> (
    None
):
    scope = _scope()
    assert scope is not None
    reply = scope.contract["properties"]["dispositions"]
    assert reply["maxItems"] == 2
    placing, other = reply["items"]["anyOf"]
    assert placing["properties"]["unit_id"]["enum"] == [LABEL, KOTLIN]
    assert "installation" not in placing["properties"]["destination_section"]["enum"]
    assert "development_testing" in placing["properties"]["destination_section"]["enum"]
    assert other["properties"]["destination_section"][
        "oneOf"
    ]  # a supersession may still say so


def test_the_worst_reply_a_patch_admits_fits_the_repair_budget() -> None:
    """Email-Python's repair hit max_output_tokens (8,000) re-listing a whole batch. The bound is
    by construction: units asked for, a capped citation list each, a one-entry ledger."""
    _, units, _ = _facts()
    budget = REPAIR_PROMPT.manifest.sampling.max_output_tokens
    scope = _scope()
    assert scope is not None
    chars = d.output_chars_bound(scope.contract)
    assert chars is not None and chars / d.OUTPUT_CHARS_PER_TOKEN_FLOOR < budget / 2
    call = repair_schema(REPAIR_PROMPT, scope.contract, bound_changes=True)
    ledger = call["properties"]["changes"]
    assert (
        ledger["maxItems"] == 1
        and ledger["items"]["properties"]["fact_ids"]["maxItems"] == 0
    )
    assert call["properties"]["revised_output"] == scope.contract
    # a long list of units at fault is capped to what one reply can answer
    many = _record(*[unit.id for unit in units])
    capped = _scope(many)
    assert capped is not None and len(capped.unit_ids) <= PATCH_UNITS
    base = repair_schema(REPAIR_PROMPT, scope.contract)
    assert (
        base["properties"]["changes"]["maxItems"] == 12
    )  # the unbounded repair keeps its own


def test_the_contract_shown_to_the_model_names_enums_by_size_the_decoder_enforces_them() -> (
    None
):
    scope = _scope()
    assert scope is not None
    shown = condensed(scope.contract)
    citations = shown["properties"]["dispositions"]["items"]["anyOf"][0]["properties"][
        "fact_ids"
    ]
    assert (
        isinstance(citations["items"]["enum"], str)
        and "allowed values" in citations["items"]["enum"]
    )
    full = scope.contract["properties"]["dispositions"]["items"]["anyOf"][0][
        "properties"
    ]
    assert isinstance(
        full["fact_ids"]["items"]["enum"], list
    )  # the decoder keeps the real one


# ---- the retained replies -------------------------------------------------------------------


def test_the_real_first_reply_is_refused_for_the_destination_it_names() -> None:
    """Attempt 1: VERIFIED_MOVE of the snippet into ``installation``. The contract does not admit
    it, and the refusal says which destinations are allowed."""
    scope = _scope()
    assert scope is not None
    errors, _ = _judge(REPAIR["reply_1"], scope)
    assert any(
        "revised_output.dispositions[0]" in e and "'installation' is not one of [" in e
        for e in errors
    ), errors


def test_the_real_second_reply_is_refused_because_it_defers_the_unit_again() -> None:
    """Attempt 2 handed the same deferral back with a longer rationale. Its ledger was the reason it
    was refused; the defect it left standing is the reason it cannot be accepted."""
    scope = _scope()
    assert scope is not None
    errors, _ = _judge(REPAIR["reply_2"], scope)
    assert [e for e in errors if "still DEFER_UNRESOLVED" in e], errors
    assert not [
        e for e in errors if "claims" in e and "changed" in e
    ]  # no ledger complaint


def _corrected(destination: str = "development_testing") -> dict[str, Any]:
    """The reply attempt 1 should have been: the same one-unit revision, in a section that can hold
    it, with the model's own (mis-pathed) ledger as it wrote it."""
    reply = copy.deepcopy(REPAIR["reply_1"])
    entry = reply["revised_output"]["dispositions"][0]
    entry.update(disposition="VERIFIED_PRESERVE", destination_section=destination)
    entry["rationale"] = (
        "The Kotlin DSL declaration, kept with the commands that build the project."
    )
    return reply


def test_a_unit_kept_in_a_section_that_can_hold_it_is_accepted_with_a_derived_ledger() -> (
    None
):
    scope = _scope()
    assert scope is not None
    errors, output = _judge(_corrected(), scope)
    assert errors == []
    merged = output["revised_output"]["dispositions"]
    assert (
        len(merged) == 9
    )  # the batch, with the one unit replaced; the rest carried over
    assert next(e for e in merged if e["unit_id"] == KOTLIN)["destination_section"] == (
        "development_testing"
    )
    # the ledger is what changed, at the unit's position in the stored batch - not the model's
    # claim about a path in its own reply
    (change,) = output["changes"]
    assert change["path"] == "dispositions.5" and change["id"] == "R01"
    assert json.loads(change["before"])["disposition"] == "DEFER_UNRESOLVED"
    assert json.loads(change["after"])["destination_section"] == "development_testing"
    # and it is a ledger the repair manifest accepts when the stored repair is re-judged on reuse
    ledger = {
        "type": "object",
        "properties": {
            "changes": REPAIR_PROMPT.manifest.output.schema_["properties"]["changes"]
        },
    }
    assert (
        list(Draft202012Validator(ledger).iter_errors({"changes": output["changes"]}))
        == []
    )


def test_a_reply_may_not_revise_a_unit_it_was_not_asked_about() -> None:
    scope = _scope()
    assert scope is not None
    reply = _corrected()
    reply["revised_output"]["dispositions"].append(
        {
            "unit_id": "inherited_unit:012.paragraph",
            "disposition": "OMIT_UNSUPPORTED",
            "destination_section": None,
            "fact_ids": ["install_command:maven"],
            "rationale": "Dropped.",
        }
    )
    errors, _ = _judge(reply, scope)
    assert any(
        "inherited_unit:012.paragraph" in e and "is not one of" in e for e in errors
    ), errors


def test_a_patch_that_changes_nothing_is_not_a_repair() -> None:
    """Negative control: the ledger is derived from the difference, so a reply that restates the
    stored disposition derives an empty one and the deferral rule refuses it before that."""
    scope = _scope()
    assert scope is not None
    stored = _stored()
    same = {
        "fingerprint": REPAIR["reply_1"]["fingerprint"],
        "causal_stage": "S4",
        "revised_output": {
            "dispositions": [
                e for e in stored["dispositions"] if e["unit_id"] == KOTLIN
            ]
        },
        "changes": REPAIR["reply_1"]["changes"][:1],
    }
    errors, _ = _judge(same, scope)
    assert [e for e in errors if "still DEFER_UNRESOLVED" in e]
    assert unit_changes(stored, stored) == []


def test_without_a_patch_the_ledger_is_still_checked_against_the_stored_batch() -> None:
    """Unchanged behaviour for every other repair: a ledger that names a path whose value did not
    change is refused (item 93). Only a patch derives its own."""
    _, _, batch_facts = _facts()
    stored = _stored()
    claimed = copy.deepcopy(REPAIR["reply_2"])
    errors = repair_checks(
        claimed,
        _defect(_record(KOTLIN)),
        RECONCILIATION.manifest.output.schema_,
        "unit_ids",
        batch_facts,
        original=stored,
    )
    assert any("claims" in e and "identical value" in e for e in errors), errors


def test_a_patch_over_a_different_batch_leaves_the_others_untouched() -> None:
    facts, units, _ = _facts()
    other = [
        Fact("inherited_unit:200.paragraph", "inherited_unit", "x", units[0].evidence)
    ]
    scope = patch_scope(
        _record(KOTLIN),
        {"reconciliation#1": {"dispositions": []}, "reconciliation#2": _stored()},
        {"reconciliation#1": other, "reconciliation#2": units},
        facts,
        RECONCILIATION,
        {},
        REPAIR_PROMPT.manifest.sampling.max_output_tokens,
    )
    assert scope is not None and scope.batch_id == "reconciliation#2"


def test_the_cap_is_the_manifests_own_ledger_ceiling() -> None:
    ceiling = REPAIR_PROMPT.manifest.output.schema_["properties"]["changes"]["maxItems"]
    assert ceiling == PATCH_UNITS
