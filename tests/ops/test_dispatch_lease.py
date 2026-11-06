"""gatecli dispatch-next / worker-tick (owner ruling R8, 2026-11-06): lease-based autonomous
continuation over the EXISTING gate state machine.

Every test runs against a synthetic, on-disk sandbox: a temp ops/instructions.jsonl (the real
persistence the lease lives in) plus synthetic cards/receipts fed to gateverify.rebuild_state's
own IO seams, so the real derivation (compute_rows + the lease_expired un-dispatch) is what is
exercised -- never a re-implementation of it. The independent verify is mocked at the single
seam worker-tick uses (gatecli._independent_verify), proving worker-tick routes every
acceptance through it and never grades a card itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ops"))

import gatecli  # noqa: E402
import gateverify  # noqa: E402

BASE = "a" * 40
WORKER_COMMIT = "b" * 40


def _card(cid, deps=(), **extra):
    return {
        "id": cid, "gate": "GATE1_QUALITY", "track": "t", "purpose": f"do {cid}",
        "depends_on": list(deps), "write_paths": [f"src/{cid}.py"],
        "checks": [{"command": f"python -c 'print(1)'  # {cid}", "expect": "exit 0",
                    "timeout_seconds": 5, "proves": ["REQ-X"]}],
        "negative_control": {"mutate": "true"}, **extra,
    }


CARDS = {
    "TC-101": _card("TC-101"),
    "TC-102": _card("TC-102", deps=["TC-101"]),          # blocked: prerequisite not accepted
    "TC-103": _card("TC-103", requires_owner_decision=True),
}


class Clock:
    def __init__(self, ts):
        self.ts = ts

    def __call__(self):
        return self.ts


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    ops = tmp_path / "ops"
    ops.mkdir()
    ins = ops / "instructions.jsonl"
    ins.write_text("", encoding="utf-8")
    receipts: dict = {}
    clock = Clock("2026-11-06T10:00:00Z")

    monkeypatch.setattr(gatecli, "INSTRUCTIONS_JSONL", ins)
    monkeypatch.setattr(gatecli, "now_utc", clock)
    monkeypatch.setattr(gatecli, "all_cards", lambda: CARDS)
    monkeypatch.setattr(gatecli, "_head_sha", lambda rev="HEAD": BASE)
    monkeypatch.setattr(gatecli, "_card_sha_at", lambda cid, rev: "c" * 64)
    monkeypatch.setattr(gateverify, "all_cards", lambda: CARDS)
    monkeypatch.setattr(gateverify, "STATUS_JSONL", ops / "status.jsonl")
    monkeypatch.setattr(gateverify, "load_receipt", lambda gate, cid: receipts.get(cid))
    monkeypatch.setattr(gateverify, "card_is_stale", lambda cid, r: False)
    monkeypatch.setattr(gateverify, "receipt_is_coherent", lambda r, card=None: [])
    monkeypatch.setattr(gateverify, "receipt_artifact_present", lambda gate, cid: True)
    return {"ins": ins, "receipts": receipts, "clock": clock, "tmp": tmp_path}


def _args(**kw):
    base = {"holder": "worker-1", "ttl_minutes": 60, "dry_run": False, "no_dashboard": True,
            "base": None, "head": "HEAD", "no_advance": False}
    base.update(kw)
    return type("A", (), base)()


def _run(fn, capsys, **kw):
    rc = fn(_args(**kw))
    return rc, json.loads(capsys.readouterr().out)


def _status(cid):
    rows, _ = gateverify.rebuild_state()
    return next(r for r in rows if r["id"] == cid)["status"]


def _lines(sb):
    return [json.loads(x) for x in sb["ins"].read_text(encoding="utf-8").splitlines() if x.strip()]


def test_acquire_writes_a_schema_valid_lease_and_is_idempotent(sandbox, capsys):
    rc, out = _run(gatecli.cmd_dispatch_next, capsys)
    assert rc == 0 and out["status"] == "DISPATCHED"
    a = out["assignment"]
    assert a["card"] == "TC-101" and a["write_paths"] == ["src/TC-101.py"]
    assert a["lease"] == {"holder": "worker-1", "base_sha": BASE,
                          "acquired_at": "2026-11-06T10:00:00Z", "expires_at": "2026-11-06T11:00:00Z"}
    assert a["commit_subject_tag"] == "(GATE1_QUALITY/TC-101)"
    assert any(c.startswith("python ops/gatecli.py review TC-101 --base " + BASE) for c in a["judged_by"])
    assert _status("TC-101") == "IN_PROGRESS"

    sandbox["clock"].ts = "2026-11-06T10:30:00Z"
    rc2, out2 = _run(gatecli.cmd_dispatch_next, capsys)
    assert rc2 == 0 and out2["status"] == "LEASE_HELD"
    assert out2["assignment"] == a                       # the same assignment, byte for byte
    assert len(_lines(sandbox)) == 1                      # nothing new written


def test_a_different_holder_is_refused_while_the_lease_is_live(sandbox, capsys):
    _run(gatecli.cmd_dispatch_next, capsys)
    rc, out = _run(gatecli.cmd_dispatch_next, capsys, holder="worker-2")
    assert rc == 1 and out["status"] == "REFUSED"
    assert len(_lines(sandbox)) == 1


def test_dry_run_writes_nothing(sandbox, capsys):
    rc, out = _run(gatecli.cmd_dispatch_next, capsys, dry_run=True)
    assert out["status"] == "DRY_RUN_WOULD_DISPATCH" and _lines(sandbox) == []


def test_blocked_prerequisites_and_owner_decisions_are_never_dispatched(sandbox, capsys, monkeypatch):
    # TC-101 accepted -> TC-102 READY (first in tick order); TC-103 awaits the owner.
    sandbox["receipts"]["TC-101"] = {"accepted": True, "head_rev": BASE, "gate": "GATE1_QUALITY"}
    sandbox["receipts"]["TC-103"] = {"accepted": False, "reason": "owner"}
    _, out = _run(gatecli.cmd_dispatch_next, capsys)
    assert out["assignment"]["card"] == "TC-102"

    # Only blocked cards left: TC-102's prerequisite is missing, TC-103 awaits the owner.
    sandbox["ins"].write_text("", encoding="utf-8")
    blocked = {"TC-101": _card("TC-101", deps=["TC-999"]), "TC-102": CARDS["TC-102"],
               "TC-103": CARDS["TC-103"]}
    sandbox["receipts"].clear()
    sandbox["receipts"]["TC-103"] = {"accepted": False, "reason": "owner"}
    monkeypatch.setattr(gateverify, "all_cards", lambda: blocked)
    monkeypatch.setattr(gatecli, "all_cards", lambda: blocked)
    _, out = _run(gatecli.cmd_dispatch_next, capsys)
    assert out["status"] == "IDLE" and _lines(sandbox) == []


def test_worker_tick_with_no_progress_keeps_the_lease(sandbox, capsys, monkeypatch):
    _run(gatecli.cmd_dispatch_next, capsys)
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [])
    called = []
    monkeypatch.setattr(gatecli, "_independent_verify", lambda *a: called.append(a))
    rc, out = _run(gatecli.cmd_worker_tick, capsys)
    assert rc == 0 and out["actions"][0]["action"] == "no_progress"
    assert called == [] and len(_lines(sandbox)) == 1
    assert _status("TC-101") == "IN_PROGRESS"


def test_lease_expiry_returns_the_card_to_ready_and_redispatches(sandbox, capsys, monkeypatch):
    _run(gatecli.cmd_dispatch_next, capsys)
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [])
    sandbox["clock"].ts = "2026-11-06T11:00:00Z"          # exactly at expires_at

    rc, out = _run(gatecli.cmd_worker_tick, capsys, dry_run=True)
    assert out["actions"][0]["action"] == "would_expire" and len(_lines(sandbox)) == 1

    rc, out = _run(gatecli.cmd_worker_tick, capsys, no_advance=True)
    assert out["actions"][0]["action"] == "expired"
    assert _lines(sandbox)[-1]["kind"] == "lease_expired"
    assert gatecli.active_lease() is None
    assert _status("TC-101") == "READY"                  # crashed worker's card is READY again

    # another worker may now take it; the crash did not consume an attempt
    _, out = _run(gatecli.cmd_dispatch_next, capsys, holder="worker-2")
    assert out["status"] == "DISPATCHED" and out["assignment"]["attempt"] == 1
    assert out["assignment"]["lease"]["holder"] == "worker-2"


def test_tagged_commit_is_judged_only_by_the_independent_verify(sandbox, capsys, monkeypatch):
    _run(gatecli.cmd_dispatch_next, capsys)
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [WORKER_COMMIT])
    calls = []

    def fake_verify(cid, base, head):
        calls.append((cid, base, head))
        receipt = {"accepted": True, "reason": "all gates passed", "head_rev": head,
                   "gate": "GATE1_QUALITY"}
        sandbox["receipts"][cid] = receipt                # what do_verify would persist
        return receipt

    monkeypatch.setattr(gatecli, "_independent_verify", fake_verify)

    _, out = _run(gatecli.cmd_worker_tick, capsys, dry_run=True)
    assert out["actions"][0]["action"] == "would_verify" and calls == []

    _, out = _run(gatecli.cmd_worker_tick, capsys)
    assert calls == [("TC-101", BASE, WORKER_COMMIT)]
    assert out["actions"][0]["action"] == "verified_accepted"
    rel = [l for l in _lines(sandbox) if l["kind"] == "lease_release"]
    assert rel and rel[0]["lease"]["outcome"] == "accepted"
    assert _status("TC-101") == "ACCEPTED"
    # ...and it advanced: TC-102's prerequisite is now met, so it was leased next
    assert out["actions"][1]["action"] == "advance"
    assert out["actions"][1]["assignment"]["card"] == "TC-102"


def test_failed_verify_renews_the_lease_as_rework_and_never_reverifies_the_same_head(
        sandbox, capsys, monkeypatch):
    _run(gatecli.cmd_dispatch_next, capsys)
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [WORKER_COMMIT])
    calls = []

    def fake_verify(cid, base, head):
        calls.append(head)
        r = {"accepted": False, "reason": "checks failed: x"}
        sandbox["receipts"][cid] = r
        return r

    monkeypatch.setattr(gatecli, "_independent_verify", fake_verify)
    sandbox["clock"].ts = "2026-11-06T10:50:00Z"
    _, out = _run(gatecli.cmd_worker_tick, capsys)
    assert out["actions"][0]["action"] == "rework_lease_renewed"
    lease = gatecli.active_lease()
    assert lease["attempt"] == 2 and lease["expires_at"] == "2026-11-06T11:50:00Z"
    assert lease["verified_head"] == WORKER_COMMIT
    assert _status("TC-101") == "IN_PROGRESS"

    _, out = _run(gatecli.cmd_worker_tick, capsys)
    assert out["actions"][0]["action"] == "no_progress" and calls == [WORKER_COMMIT]


def test_third_failed_attempt_is_failed_internal_and_the_loop_moves_on(sandbox, capsys, monkeypatch):
    heads = iter(["1" * 40, "2" * 40, "3" * 40])
    current = {}
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [current["h"]])

    def fake_verify(cid, base, head):
        r = {"accepted": False, "reason": "checks failed"}
        sandbox["receipts"][cid] = r
        return r

    monkeypatch.setattr(gatecli, "_independent_verify", fake_verify)
    _run(gatecli.cmd_dispatch_next, capsys)
    for _ in range(3):
        current["h"] = next(heads)
        _, out = _run(gatecli.cmd_worker_tick, capsys, no_advance=True)
    assert out["actions"][0]["action"] == "failed_internal"
    assert gatecli.active_lease() is None
    assert _status("TC-101") == "FAILED_INTERNAL"


def test_every_written_line_validates_against_the_instruction_schema(sandbox, capsys, monkeypatch):
    _run(gatecli.cmd_dispatch_next, capsys)
    sandbox["clock"].ts = "2026-11-06T12:00:00Z"
    monkeypatch.setattr(gatecli, "tagged_commits", lambda b, h, c: [])
    _run(gatecli.cmd_worker_tick, capsys)
    schema = json.loads((REPO_ROOT / "schemas" / "instruction-line.schema.json").read_text(encoding="utf-8"))
    import jsonschema
    for line in _lines(sandbox):
        jsonschema.Draft202012Validator(schema).validate(line)


DRIVER = textwrap.dedent("""
    import json, sys
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    import gatecli, gateverify
    cards = json.loads(sys.argv[3])
    ops = Path(sys.argv[2])
    gatecli.INSTRUCTIONS_JSONL = ops / "instructions.jsonl"
    gatecli.now_utc = lambda: sys.argv[4]
    gatecli.all_cards = lambda: cards
    gatecli._head_sha = lambda rev="HEAD": "a" * 40
    gatecli._card_sha_at = lambda cid, rev: "c" * 64
    gateverify.all_cards = lambda: cards
    gateverify.STATUS_JSONL = ops / "status.jsonl"
    gateverify.load_receipt = lambda gate, cid: None
    sys.exit(gatecli.main(["dispatch-next", "--holder", "worker-1", "--no-dashboard"]))
""")


def test_lease_persists_across_fresh_processes(sandbox, capsys):
    _, first = _run(gatecli.cmd_dispatch_next, capsys)
    driver = sandbox["tmp"] / "driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(driver), str(REPO_ROOT / "ops"), str(sandbox["ins"].parent),
         json.dumps(CARDS), "2026-11-06T10:20:00Z"],
        capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    second = json.loads(res.stdout)
    assert second["status"] == "LEASE_HELD"
    assert second["assignment"] == first["assignment"]
    assert len(_lines(sandbox)) == 1
