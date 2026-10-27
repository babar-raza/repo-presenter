"""S4 (disposition) repair through readme/repair/loop.py, offline, on the Font-FOSS-for-Python case.

The case: aspose-font-foss/Aspose.Font-FOSS-for-Python's README inherits, in its "MCP Server"
section, ``pip install "aspose-font[mcp]"``. The distribution it publishes is ``aspose-font-foss``
(``install_command:pip`` and ``package:name``, both SUPPORTED), so the command asks pip for a
package that does not exist. The independent reviewer REJECTed the candidate; the line is not
authored, it is a preserved unit, so the finding routes to S4 (``defect_bridge``), where the repair
is a per-unit patch (``reconciliation/patch.py``).

The facts are a verbatim slice of
``evidence/build/P2_REAL_ENGINE_SALVAGE/aspose-font-foss__Aspose.Font-FOSS-for-Python/
facts.poc_backfill.json`` (the evidence directory holds facts, not the S4 dispositions, so the
stored disposition below is reconstructed: the unit is kept as written in a section that can hold
it). No provider is called: the model's replies are scripted through the fake client
``tests/test_cascade.py`` uses, and every call still runs through ``run_job`` with its checks.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.cascade import _run_reconciliation
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.repair.loop import RepairContext, repair_defect
from repo_presenter.readme.repair.targeted import Defect, RepairLedger
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import (
    Finding,
    Refutation,
    ReviewVerdict,
)
from tests.readme.composition.synthetic import make_entry
from tests.test_cascade import CONFIG, _completion, _FakeClient

FIXTURE = Path(__file__).parents[1] / "reconciliation" / "fixtures"
PROMPTS_PATH = Path(__file__).resolve().parents[3] / "prompts"
HEADING = "inherited_unit:098.heading"
LEAD_IN = "inherited_unit:099.paragraph"
COMMAND = "inherited_unit:100.code_block"
AFTER = "inherited_unit:101.paragraph"
WRONG_LINE = 'pip install "aspose-font[mcp]"'
HOME = "key_capabilities"
INSTALL_FACT = "install_command:pip"
MESSAGE = (
    "line 568: the install command names the distribution aspose-font, but the package this "
    "repository publishes is aspose-font-foss"
)


def _entry(
    unit: str, disposition: str, destination: str | None, fact_ids: list[str], why: str
) -> dict[str, Any]:
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": fact_ids,
        "rationale": why,
    }


STORED = {
    "dispositions": [
        _entry(HEADING, "NON_CONTENT", None, [], "heading, not content"),
        _entry(
            LEAD_IN,
            "VERIFIED_PRESERVE",
            HOME,
            [],
            "introduces the command that follows",
        ),
        _entry(
            COMMAND,
            "VERIFIED_PRESERVE",
            HOME,
            [],
            "the MCP server command, kept as written",
        ),
        _entry(
            AFTER,
            "VERIFIED_PRESERVE",
            HOME,
            ["dependency:optional.mcp.mcp-1.0"],
            "kept",
        ),
    ]
}
PLAN = {
    "sections": [
        {"section_id": section, "include": True}
        for section in (
            "opening",
            "key_capabilities",
            "api_reference",
            "scope_limitations",
        )
    ]
}


def _facts() -> FactsDocument:
    return read_facts(FIXTURE / "font_python_mcp_install.facts.json")


def _reply(fingerprint: str, *entries: dict[str, Any]) -> dict[str, Any]:
    return {
        "causal_stage": "S4",
        "fingerprint": fingerprint,
        "revised_output": {"dispositions": list(entries)},
        "changes": [
            {
                "id": "R01",
                "path": "dispositions.0",
                "before": "",
                "after": "",
                "fact_ids": [],
            }
        ],
    }


def _omitted(fingerprint: str) -> dict[str, Any]:
    """Omit the command and its lead-in, citing the SUPPORTED fact that says what is published."""
    return _reply(
        fingerprint,
        _entry(
            LEAD_IN,
            "OMIT_UNSUPPORTED",
            None,
            [INSTALL_FACT],
            "introduces an omitted command",
        ),
        _entry(
            COMMAND,
            "OMIT_UNSUPPORTED",
            None,
            [INSTALL_FACT],
            "names a package not published",
        ),
    )


def _corrected(fingerprint: str) -> dict[str, Any]:
    return _reply(
        fingerprint,
        _entry(
            LEAD_IN,
            "VERIFIED_PRESERVE",
            HOME,
            [],
            "introduces the command that follows",
        ),
        _entry(
            COMMAND,
            "CORRECT_WITH_EVIDENCE",
            HOME,
            [INSTALL_FACT],
            "The package is aspose-font-foss; the command must name it.",
        ),
    )


def _moved(fingerprint: str) -> dict[str, Any]:
    return _reply(
        fingerprint,
        _entry(LEAD_IN, "VERIFIED_MOVE", "api_reference", [], "kept with its command"),
        _entry(
            COMMAND, "VERIFIED_MOVE", "api_reference", [INSTALL_FACT], "kept as written"
        ),
    )


def _unchanged(fingerprint: str) -> dict[str, Any]:
    return _reply(fingerprint, *copy.deepcopy(STORED["dispositions"][1:3]))


def _defect() -> Defect:
    """The defect the reviewer's REJECT becomes, routed exactly as settle_candidate routes it."""
    facts = _facts()
    finding = Finding(
        rule="claim_contradiction",
        kind="deterministic",
        message=MESSAGE,
        refuted_by=Refutation(rule="claim_contradiction", evidence="package:name"),
        quote=WRONG_LINE,
    )
    [defect] = build_defects(
        ReviewVerdict(verdict="REJECT", findings=(finding,)),
        units=[],
        plan=PLAN,
        dispositions=STORED,
        facts=facts,
        ecosystem="python",
        repairer=load_manifests(PROMPTS_PATH)["targeted_repair"].sha256,
    )
    return defect


class _Case:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.facts = _facts()
        self.entry = make_entry()
        self.prompts = load_manifests(PROMPTS_PATH)
        self.store = CallStore(tmp_path / "calls")
        self.context = JobContext(self.entry.repository, self.facts.source_revision)
        self.ledger = Ledger(tmp_path / "ledger.jsonl")
        self.monkeypatch = monkeypatch
        # The stored batch is what the cascade's own S4 stage writes: one scripted call, through
        # run_job, so the request hash the repair recomputes is the one the cascade computed.
        self.script([STORED])
        self.stage = self._reconcile()
        self.repairs = RepairLedger(tmp_path / "repairs.json")
        self.rc = RepairContext(
            entry=self.entry,
            facts=self.facts,
            prompts=self.prompts,
            config=CONFIG,
            ledger=self.ledger,
            store=self.store,
            context=self.context,
            investigation={},
            dispositions=self.stage,
            plan=PLAN,
            tasks=[],
            name="Aspose.Font FOSS",
        )

    def script(self, replies: list[dict[str, Any]]) -> _FakeClient:
        client = _FakeClient([_completion(reply) for reply in replies])
        self.monkeypatch.setattr(
            jobs_module.transport, "build_client", lambda config: client
        )
        return client

    def _reconcile(self) -> dict[str, Any]:
        return _run_reconciliation(
            entry=self.entry,
            document=self.facts,
            investigation={},
            prompts=self.prompts,
            config=CONFIG,
            ledger=self.ledger,
            store=self.store,
            context=self.context,
        )

    def stored_now(self) -> dict[str, Any]:
        """What the next cascade run reads for S4: served from the store, with no call made."""
        client = self.script([])
        served = self._reconcile()
        assert client.chat.completions.replies == []
        return served


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Case:
    return _Case(tmp_path, monkeypatch)


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


def test_the_reviewers_finding_on_the_inherited_command_routes_to_s4_with_its_message() -> (
    None
):
    defect = _defect()
    assert (defect.stage, defect.record["misrouted"]) == ("S4", True)
    assert defect.record["message"] == MESSAGE
    assert (
        "failures" not in defect.record
    )  # the unit is found from the quote, not carried


def test_the_fixture_is_the_defect_shape_a_preserved_command_against_a_supported_install_fact(
    case: _Case,
) -> None:
    facts = case.facts
    command = next(f for f in facts.facts if f.id == COMMAND)
    assert command.value == f"```bash\n{WRONG_LINE}\npython -m aspose_font.mcp\n```"
    supported = {f.id: f.value for f in facts.facts if f.polarity == "SUPPORTED"}
    assert supported[INSTALL_FACT] == "pip install aspose-font-foss"
    assert supported["package:name"] == "aspose-font-foss"
    assert _by_unit(case.stage)[COMMAND]["disposition"] == "VERIFIED_PRESERVE"


def test_an_omission_citing_the_install_fact_repairs_the_command_and_nothing_else(
    case: _Case,
) -> None:
    defect = _defect()
    client = case.script([_omitted(defect.fingerprint)])

    assert repair_defect(case.rc, defect, case.repairs) is True

    attempt = case.repairs.attempts[defect.fingerprint]
    assert (attempt["outcome"], attempt["stage"], attempt["misrouted"]) == (
        "repaired",
        "S4",
        True,
    )
    # the ledger is derived from the difference: the lead-in and the command, at their stored
    # positions in the batch, not the model's own claim
    assert [change["path"] for change in attempt["changes"]] == [
        "dispositions.1",
        "dispositions.2",
    ]
    assert client.chat.completions.replies == []

    repaired = _by_unit(case.stored_now())
    assert repaired[LEAD_IN]["disposition"] == "OMIT_UNSUPPORTED"
    assert INSTALL_FACT in repaired[LEAD_IN]["fact_ids"]
    # normalize does not let a reply omit an install-class command block while an install fact
    # exists (it reads that as the model dropping a verified command): it is folded to a deferral
    # citing the fact, which still takes the wrong command out of the README
    assert repaired[COMMAND]["disposition"] == "DEFER_UNRESOLVED"
    assert repaired[COMMAND]["destination_section"] is None
    assert INSTALL_FACT in repaired[COMMAND]["fact_ids"]
    # every other unit is byte-identical to what was stored
    stored = _by_unit(STORED)
    assert {u: e for u, e in repaired.items() if u not in {LEAD_IN, COMMAND}} == {
        u: e for u, e in stored.items() if u not in {LEAD_IN, COMMAND}
    }


def test_correct_with_evidence_is_refused_for_a_command_block_by_the_existing_rule(
    case: _Case,
) -> None:
    """A block BC-08 holds to the finished README is printed as written or superseded by the
    Installation row: the stage has no way to print a corrected command, so this reply, which is
    what a repair would naturally try first, is refused (twice: the job re-asks once)."""
    defect = _defect()
    client = case.script(
        [_corrected(defect.fingerprint), _corrected(defect.fingerprint)]
    )
    before = copy.deepcopy(case.stage)

    assert repair_defect(case.rc, defect, case.repairs) is False

    attempt = case.repairs.attempts[defect.fingerprint]
    assert (
        attempt["outcome"] == "unrepairable"
        and "unprinted_command" in attempt["reason"]
    )
    assert client.chat.completions.replies == []
    assert case.stored_now() == before


def test_moving_the_command_to_another_section_is_not_a_repair(case: _Case) -> None:
    """The finding is about the printed text, which a move still prints as written."""
    defect = _defect()
    client = case.script([_moved(defect.fingerprint), _moved(defect.fingerprint)])
    before = copy.deepcopy(case.stage)

    assert repair_defect(case.rc, defect, case.repairs) is False

    attempt = case.repairs.attempts[defect.fingerprint]
    assert attempt["outcome"] == "unrepairable"
    assert "still VERIFIED_MOVE, which prints the quoted text" in attempt["reason"]
    assert client.chat.completions.replies == []
    assert case.stored_now() == before


def test_the_request_asks_for_the_command_and_its_lead_in_only(case: _Case) -> None:
    defect = _defect()
    seen: list[dict[str, Any]] = []
    client = case.script([_omitted(defect.fingerprint)])
    create = client.chat.completions.create

    def spy(**payload: Any) -> Any:
        seen.append(payload)
        return create(**payload)

    client.chat.completions.create = spy
    repair_defect(case.rc, defect, case.repairs)

    (payload,) = seen
    schema = payload["response_format"]["json_schema"]["schema"]
    reply = schema["properties"]["revised_output"]["properties"]["dispositions"]
    assert reply["maxItems"] == 2
    assert reply["items"]["anyOf"][0]["properties"]["unit_id"]["enum"] == [
        LEAD_IN,
        COMMAND,
    ]
    assert schema["properties"]["changes"]["maxItems"] == 1
    user = payload["messages"][1]["content"]
    escaped = json.dumps(WRONG_LINE)[1:-1]  # the packet is JSON in the prompt
    assert escaped in user and MESSAGE in user and HEADING not in user.split("Facts")[0]


def test_a_reply_that_hands_back_the_same_disposition_is_rejected_and_nothing_is_stored(
    case: _Case,
) -> None:
    defect = _defect()
    before = copy.deepcopy(case.stage)
    client = case.script(
        [_unchanged(defect.fingerprint), _unchanged(defect.fingerprint)]
    )

    assert repair_defect(case.rc, defect, case.repairs) is False

    attempt = case.repairs.attempts[defect.fingerprint]
    assert attempt["outcome"] == "unrepairable"
    assert "unchanged" in attempt["reason"]
    assert (
        client.chat.completions.replies == []
    )  # the job's own re-ask ran, then stopped
    assert case.stored_now() == before


def test_a_defect_that_names_no_placed_unit_is_recorded_unrepairable_without_a_call(
    case: _Case,
) -> None:
    defect = _defect()
    defect = Defect(
        defect.fingerprint,
        defect.source,
        defect.label,
        defect.section_id,
        defect.stage,
        {**defect.record, "quote": "text that no placed unit holds"},
    )
    client = case.script([])
    assert repair_defect(case.rc, defect, case.repairs) is False
    attempt = case.repairs.attempts[defect.fingerprint]
    assert (
        attempt["outcome"] == "unrepairable"
        and "regenerate unrelated units" in attempt["reason"]
    )
    assert client.chat.completions.replies == []


def test_after_the_repair_the_reviewers_loss_rule_still_flags_the_deferred_fence(
    case: _Case,
) -> None:
    """Characterisation, not an endorsement: a deferral accounts for nothing (``_accounting_units``),
    so the fence the repair removed is, to ``live_readme_loss``, content lost without an accounting
    disposition. The repair above is therefore real but not yet enough for the reviewer to ACCEPT
    this README; the open question is in the report, not decided here."""
    from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule

    defect = _defect()
    case.script([_omitted(defect.fingerprint)])
    repair_defect(case.rc, defect, case.repairs)
    original = "\n\n".join(f.value for f in case.facts.by_kind("inherited_unit"))
    candidate = (
        "## MCP Server\n\nThe MCP server now covers low-level inspection tools.\n"
    )
    findings = live_readme_loss_rule(
        original, candidate, facts=case.facts, dispositions=case.stored_now()
    )
    assert any("aspose-font[mcp]" in finding.quote for finding in findings)
