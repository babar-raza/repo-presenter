"""BL-189: M9 acceptance is bound to the audited README bytes, not only the upstream revision.

End to end through the real chain with fixtures (zero provider calls, zero network): the seeder's seed plan and
files -> the writer's records -> the counter's attested reader and ``apply_attested`` -> the R15 publication
gate, plus the seeder's own control selection. Falsifier: two different READMEs of one repository, lane and
revision -- an attestation for the first neither accepts nor suppresses the second."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, decrypt_seed_manifest
from repo_presenter.acceptance.record import (
    CONTENT_BOUND,
    DIGEST_MALFORMED,
    DIGEST_MISMATCH,
    REVISION_ONLY,
    acceptance_binding,
    candidate_sha256,
)
from repo_presenter.core.state.bundle_store import SealRecord
from repo_presenter.propose import portfolio_gate

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


seeder = _load("bl189_run_m9_seeder", ROOT / "scripts" / "run_m9_seeder.py")
writer = _load("bl189_run_acceptance_writer", ROOT / "scripts" / "run_acceptance_writer.py")
pdc = _load("bl189_portfolio_delivery_count", ROOT / "ops" / "checks" / "portfolio_delivery_count.py")

REPO = "org/repo-a"
REV = "r" * 40
ALLOW = {"repositories": [{"repository": REPO, "effects": ["pull_request"]}]}

TEMPLATE = """# {name} FOSS

{name} FOSS does a thing with `{name}Widget`, which has 4 public types organized into one
module and exposes `{name}Widget.render` for building output.

## Classes

| Class | Description |
|---|---|
| `{name}Widget` | The main widget object exposed by this library. |
| `{name}Options` | Configuration options for `{name}Widget`. |

## Installation

```bash
pip install {name}-foss
```
"""


def _readme(name: str, crlf: bool = False) -> bytes:
    text = TEMPLATE.format(name=name)
    return (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")


def _seal(name: str, lane: str, i: int, readme: bytes | None = None) -> SealRecord:
    return SealRecord(
        repository=f"own:{name}", lane=lane, commit="c" * 40, revision=f"{i:04d}" + "a" * 36,
        manifest_state="ACCEPTED", dependencies={}, review=None,
        readme=readme if readme is not None else _readme(name, crlf=(i == 0)),
    )


def _history(n: int = 12) -> dict:
    return {(f"own:repo-{lane}-{i}", lane): [_seal(f"repo-{lane}-{i}", lane, i)] for lane in ("L", "R") for i in range(n)}


# --- the shared digest rule --------------------------------------------------------------------------------


def test_binding_classification_is_total_and_never_raises():
    good = candidate_sha256(b"x")
    assert acceptance_binding(good, good) == CONTENT_BOUND
    assert acceptance_binding(None, good) == REVISION_ONLY
    assert acceptance_binding(candidate_sha256(b"y"), good) == DIGEST_MISMATCH
    for bad in ("", good.upper(), good[:63], good + "0", " " + good, 5, True, [], {}, b"a" * 64, "g" * 64, good + "\n"):
        assert acceptance_binding(bad, good) == DIGEST_MALFORMED, repr(bad)


# --- writer: what it can see, end to end through seeder -> writer -> counter --------------------------------


def _run_chain(tmp_path, monkeypatch, *, tamper=None):
    """Seeder main (real files, real encrypted manifest) -> writer main (real decrypt, frozen findings) ->
    the document. ``tamper(candidates_dir)`` may change an audited file after the seeder wrote it."""
    history = _history()
    monkeypatch.setattr(seeder, "seal_history", lambda **_: history)
    monkeypatch.setattr(seeder, "recertified_seals", lambda remote="origin": {(r, l, s[-1].revision) for (r, l), s in history.items()})
    monkeypatch.setattr(seeder, "judged_controls", lambda remote="origin": {})
    key = b"\x09" * 32
    monkeypatch.setenv("AUDIT_SEED_KEY", key.hex())
    out = tmp_path / "seed"
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--out-dir", str(out)])
    assert seeder.main() == 0
    if tamper:
        tamper(out / "candidates")
    manifest = writer.key_manifest_by_case_id(decrypt_seed_manifest((out / "seed_manifest.enc").read_bytes(), key))
    findings = [
        {"candidate_id": m["candidate_id"], "claim": "x", "verdict": "false", "path": "README.md", "line": m["line"]}
        for m in manifest if m["shape"] != CLEAN_SHAPE
    ]
    (tmp_path / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    recert = {(f"own:repo-{lane}-{i}", lane): (history[(f"own:repo-{lane}-{i}", lane)][-1].revision, True)
              for lane in ("L", "R") for i in range(12)}
    monkeypatch.setattr(writer, "baseline_checker", lambda *a, **k: (lambda case_id, line: False))
    rc = writer.main(
        ["--seed-run-id", "5", "--manifest", str(out / "seed_manifest.enc"), "--findings", str(tmp_path / "findings.json"),
         "--case-index", str(out / "case_index.json"), "--out", str(tmp_path / "records.json")],
        recertify=lambda: recert,
    )
    assert rc == 0
    return history, manifest, json.loads((tmp_path / "records.json").read_text(encoding="utf-8")), out


def test_seeder_commits_the_original_digest_only_inside_the_encrypted_manifest(tmp_path, monkeypatch):
    history, manifest, _doc, out = _run_chain(tmp_path, monkeypatch)
    index = json.loads((out / "case_index.json").read_text(encoding="utf-8"))
    assert all("candidate_sha256" not in e and "original_sha256" not in e for e in index)  # blinding: nothing public
    by_case = {e["case_id"]: e for e in index}
    for entry in manifest:
        e = by_case[entry["case_id"]]
        original = history[(e["repository"], e["lane"])][-1].readme
        assert entry["original_sha256"] == hashlib.sha256(original).hexdigest()


def test_clean_control_records_carry_the_digest_of_the_sealed_bytes_including_crlf(tmp_path, monkeypatch):
    history, manifest, doc, out = _run_chain(tmp_path, monkeypatch)
    shapes = {m["case_id"]: m["shape"] for m in manifest}
    controls = [r for r in doc["records"] if r["role"] == "clean_control"]
    assert controls and doc["batch_passed"] is True
    for record in controls:
        sealed = history[(record["repository"], record["lane"])][-1].readme
        assert record["candidate_sha256"] == hashlib.sha256(sealed).hexdigest()
        assert record["audit_passed"] is True and shapes[record["case_id"]] == CLEAN_SHAPE
    # CRLF originals (the i == 0 seals) are digested over their exact bytes, whichever role the case took
    crlf = [r for r in doc["records"] if b"\r\n" in history[(r["repository"], r["lane"])][-1].readme]
    assert crlf
    for record in crlf:
        assert record["candidate_sha256"] == hashlib.sha256(history[(record["repository"], record["lane"])][-1].readme).hexdigest()


def test_a_seeded_copy_is_bound_to_the_original_never_the_mutated_text(tmp_path, monkeypatch):
    history, _manifest, doc, out = _run_chain(tmp_path, monkeypatch)
    seeded = [r for r in doc["records"] if r["role"] == "seeded"]
    assert seeded
    for record in seeded:
        original = history[(record["repository"], record["lane"])][-1].readme
        mutated = (out / "candidates" / f"{record['case_id']}.md").read_bytes()
        assert mutated != original
        assert record["candidate_sha256"] == hashlib.sha256(original).hexdigest() != hashlib.sha256(mutated).hexdigest()
        assert record["audit_passed"] is False


def test_a_clean_control_the_auditor_did_not_read_as_sealed_cannot_pass(tmp_path, monkeypatch):
    def tamper(candidates):
        for path in sorted(candidates.glob("*.md")):
            path.write_text(path.read_text(encoding="utf-8") + "\nextra\n", encoding="utf-8")

    _history_, manifest, doc, _out = _run_chain(tmp_path, monkeypatch, tamper=tamper)
    controls = [r for r in doc["records"] if r["role"] == "clean_control"]
    assert controls
    for record in controls:
        assert record["audit_passed"] is False and "candidate_sha256" not in record
        assert "not the sealed README" in record["identity_problem"]


def test_end_to_end_the_counter_binds_to_the_bytes_and_a_rerender_of_identical_bytes_stays_bound(tmp_path, monkeypatch):
    history, _manifest, doc, _out = _run_chain(tmp_path, monkeypatch)
    blob = json.dumps(doc).encode()
    ok = lambda args: subprocess.CompletedProcess(args, 0, stdout=b"[]", stderr=b"")  # noqa: E731
    attested = pdc.read_attested_records(lambda: [("acceptance-record/run-5", "acceptance-records-5.json", blob)], ok)
    controls = [r for r in doc["records"] if r["role"] == "clean_control"]
    assert len(attested) == len(controls)
    outcomes = []
    for record in controls:
        sealed = history[(record["repository"], record["lane"])][-1].readme
        outcomes.append(pdc.LaneOutcome(
            repository=record["repository"], lane=record["lane"], record_state="x", pipeline_good=True, current=True,
            bucket=pdc.UNCALIBRATED, revision=record["revision"], readme_sha256=hashlib.sha256(sealed).hexdigest(),
        ))
    # the audited REVISION is the same for a different README: copy the first control's outcome with other bytes
    other = pdc.LaneOutcome(**{**outcomes[0].__dict__, "readme_sha256": hashlib.sha256(b"a different README").hexdigest()})
    pdc.apply_attested([*outcomes, other], attested, {})
    assert all(o.independently_accepted and o.acceptance_binding == "content_bound" for o in outcomes)
    assert not other.independently_accepted and other.acceptance_binding == ""
    assert "not the README bytes now sealed" in other.reason


# --- counter -----------------------------------------------------------------------------------------------


def _outcome(readme: bytes | None = b"README A", revision: str = REV, lane: str = "R") -> "pdc.LaneOutcome":
    return pdc.LaneOutcome(
        repository=REPO, lane=lane, record_state="x", pipeline_good=True, current=True, bucket=pdc.UNCALIBRATED,
        revision=revision, readme_sha256=candidate_sha256(readme) if readme is not None else "",
    )


def _rec(digest="__absent__", revision=REV):
    return pdc.AttestedRecord(revision, None if digest == "__absent__" else digest)


def test_two_readmes_same_repo_lane_revision_each_need_their_own_attestation():
    a, b = candidate_sha256(b"README A"), candidate_sha256(b"README B")
    only_a = {(REPO, "R"): [_rec(a)]}
    for_a, for_b = _outcome(b"README A"), _outcome(b"README B")
    pdc.apply_attested([for_a, for_b], only_a, ALLOW)
    assert for_a.independently_accepted and for_a.acceptance_binding == "content_bound" and for_a.publication_ready
    assert not for_b.independently_accepted and not for_b.publication_ready
    assert for_b.bucket == pdc.UNCALIBRATED and "covers" not in for_b.reason and "not the README bytes now sealed" in for_b.reason
    # both attested (in either order): each is accepted for its own bytes, neither suppresses the other
    for order in ([_rec(a), _rec(b)], [_rec(b), _rec(a)]):
        x, y = _outcome(b"README A"), _outcome(b"README B")
        pdc.apply_attested([x, y], {(REPO, "R"): order}, ALLOW)
        assert x.independently_accepted and y.independently_accepted


def test_identical_bytes_rerendered_stay_bound_and_a_different_revision_does_not():
    digest = candidate_sha256(b"README A")
    again = _outcome(b"README A")
    pdc.apply_attested([again], {(REPO, "R"): [_rec(digest)]}, ALLOW)
    assert again.acceptance_binding == "content_bound"
    moved = _outcome(b"README A", revision="s" * 40)
    pdc.apply_attested([moved], {(REPO, "R"): [_rec(digest)]}, ALLOW)
    assert not moved.independently_accepted


def test_a_legacy_digestless_record_counts_unchanged_but_is_revision_only_and_not_publication_ready():
    for attested in ({(REPO, "R"): REV}, {(REPO, "R"): [_rec()]}):  # old {cell: revision} shape and the new one
        o = _outcome()
        pdc.apply_attested([o], attested, ALLOW)
        assert o.independently_accepted and o.bucket == pdc.ACCEPTED
        assert o.acceptance_binding == "revision_only" and "predates candidate digests" in o.acceptance_gap
        assert o.publication_ready is False


@pytest.mark.parametrize("bad", ["", "A" * 64, "a" * 63, "g" * 64, " " + "a" * 63, 7, [], {}])
def test_a_malformed_digest_never_counts_and_never_crashes(bad):
    o = _outcome()
    pdc.apply_attested([o], {(REPO, "R"): [_rec(bad)]}, ALLOW)
    assert not o.independently_accepted and o.acceptance_binding == ""
    assert "malformed candidate digest" in o.acceptance_gap


def test_a_seal_with_no_readme_bytes_cannot_be_content_bound_but_a_legacy_record_still_counts():
    o_new, o_old = _outcome(None), _outcome(None)
    pdc.apply_attested([o_new], {(REPO, "R"): [_rec(candidate_sha256(b"x"))]}, ALLOW)
    pdc.apply_attested([o_old], {(REPO, "R"): [_rec()]}, ALLOW)
    assert not o_new.independently_accepted and o_old.acceptance_binding == "revision_only"


def _doc(*records):
    return json.dumps({"schema": pdc.RECORDS_SCHEMA, "seed_run_id": "1", "dry_run": False, "records": list(records)}).encode()


def _raw(**over):
    base = {"case_id": "c", "repository": REPO, "lane": "R", "revision": REV, "role": "clean_control",
            "deterministically_validated": True, "mechanism_verdicts": {"recertify": True}, "canaries": {}, "audit_passed": True}
    return {**base, **over}


def test_the_reader_keeps_every_record_and_distinguishes_absent_null_and_present_digests():
    ok = lambda args: subprocess.CompletedProcess(args, 0, stdout=b"[]", stderr=b"")  # noqa: E731
    good = candidate_sha256(b"A")
    blob = _doc(_raw(), _raw(candidate_sha256=good), _raw(candidate_sha256=None), _raw(candidate_sha256="XYZ"), _raw(audit_passed=False))
    read = pdc.read_attested_records(lambda: [("acceptance-record/x", "acceptance-records-1.json", blob)], ok)
    assert [r.candidate_sha256 for r in read[(REPO, "R")]] == [None, good, "", "XYZ"]
    assert pdc.read_attested_acceptances(lambda: [("acceptance-record/x", "acceptance-records-1.json", blob)], ok) == {(REPO, "R"): REV}
    unattested = lambda args: subprocess.CompletedProcess(args, 1, stdout=b"", stderr=b"")  # noqa: E731
    assert pdc.read_attested_records(lambda: [("acceptance-record/x", "acceptance-records-1.json", blob)], unattested) == {}


def test_summary_reports_content_bound_and_revision_only_totals_next_to_independently_accepted():
    a, b = _outcome(b"A"), _outcome(b"B")
    b.repository = "org/repo-b"
    pdc.apply_attested([a, b], {(REPO, "R"): [_rec(candidate_sha256(b"A"))], ("org/repo-b", "R"): [_rec()]}, {})
    calibration = SimpleNamespace(status="NOT_PASSED", problem="")
    row = pdc.summarize([a, b], calibration)["lane_r"]
    assert row[pdc.ACCEPTED] == 2 and row["content_bound"] == 1 and row["revision_only"] == 1
    assert row["acceptance_binding"] == {REPO: "content_bound", "org/repo-b": "revision_only"}
    keys = list(row)
    assert keys.index("content_bound") == keys.index(pdc.ACCEPTED) + 1


# --- R15 publication gate ----------------------------------------------------------------------------------


def test_publication_gate_fails_closed_on_a_revision_only_acceptance_and_says_why():
    legacy = _outcome()
    pdc.apply_attested([legacy], {(REPO, "R"): REV}, ALLOW)
    other_lane = _outcome(lane="L")
    pdc.apply_attested([other_lane], {(REPO, "L"): [_rec(candidate_sha256(b"README A"))]}, ALLOW)
    other_lane.no_action = False
    other_lane.certification = legacy.certification = "RECERTIFIED"
    result = portfolio_gate.evaluate(
        [REPO], [legacy, other_lane], [], today=date(2026, 11, 18), head_of=lambda repo: REV
    )
    assert result.ready is False
    why = {(r, lane): w for r, lane, w in result.missing}
    assert list(why) == [(REPO, "R")]
    assert "not the README bytes now sealed" in why[(REPO, "R")] and REV[:12] in why[(REPO, "R")]
    assert result.terminal[(REPO, "L")] == portfolio_gate.ACCEPTED


def test_publication_gate_refuses_a_cell_attested_for_other_bytes():
    o = _outcome(b"README B")
    o.certification = "RECERTIFIED"
    pdc.apply_attested([o], {(REPO, "R"): [_rec(candidate_sha256(b"README A"))]}, ALLOW)
    result = portfolio_gate.evaluate([REPO], [o], [], today=date(2026, 11, 18), head_of=lambda repo: REV)
    why = dict(((r, lane), w) for r, lane, w in result.missing)[(REPO, "R")]
    assert "other README bytes" in why and "content-bound audit is required" in why


# --- seeder: control selection and fetch failure ----------------------------------------------------------


def test_a_control_is_taken_only_for_the_audited_bytes_but_legacy_records_stay_eligible():
    seal = _seal("x", "R", 3, readme=b"README A")
    other = _seal("x", "R", 3, readme=b"README B")
    key = lambda digest: ("own:x", "R", seal.revision, digest)  # noqa: E731
    judged = {key(candidate_sha256(b"README A")): True}
    assert seeder.judged_for(judged, "own:x", "R", seal) == (True, CONTENT_BOUND)
    assert seeder.judged_for(judged, "own:x", "R", other) == (None, "")  # other bytes: neither judged nor suppressed
    legacy = {key(""): True}
    assert seeder.judged_for(legacy, "own:x", "R", seal) == (True, REVISION_ONLY)
    assert seeder.judged_for({("own:x", "R", seal.revision): False}, "own:x", "R", other) == (False, REVISION_ONLY)
    # the plan: the judged seal gets no control slot, the other README of the same revision is still audit material
    by_lane = {"R": [("own:x", seal)], "L": []}
    assert seeder._accepted_seal(judged, "own:x", "R", seal) is True
    assert seeder._accepted_seal(judged, "own:x", "R", other) is False
    fresh = lambda s: seeder.fresh_candidates({"R": [("own:x", SimpleNamespace(**{**s.__dict__, "counted": True}))]}, judged)  # noqa: E731
    assert fresh(seal) == [] and fresh(other) == [("own:x", "R", other.revision)]
    assert by_lane  # shape used by the plan


def test_build_seed_plan_does_not_spend_a_control_slot_on_a_seal_accepted_for_other_bytes():
    history = _history()
    by_lane = {"L": [], "R": []}
    for (repo, lane), seals in sorted(history.items()):
        by_lane[lane].append((repo, seals[-1]))
    target_repo, target_seal = by_lane["R"][0]
    accepted_here = {(target_repo, "R", target_seal.revision, candidate_sha256(target_seal.readme)): True}
    accepted_other = {(target_repo, "R", target_seal.revision, candidate_sha256(b"something else")): True}
    _, manifest_here = seeder.build_seed_plan(by_lane, 0, accepted_here)
    _, manifest_other = seeder.build_seed_plan(by_lane, 0, accepted_other)
    case_id = hashlib.sha256(f"{target_repo}|R|{target_seal.revision}".encode()).hexdigest()[:16]
    shape = lambda manifest: next(m["shape"] for m in manifest if m["case_id"] == case_id)  # noqa: E731
    assert shape(manifest_here) != CLEAN_SHAPE  # accepted for these bytes: not a control slot
    assert [m["original_sha256"] for m in manifest_here if m["case_id"] == case_id] == [candidate_sha256(target_seal.readme)]


def _git_runner(script):
    def run(cmd, **kwargs):
        stdout, code = script(cmd[1:])
        return subprocess.CompletedProcess(cmd, code, stdout=stdout, stderr=b"boom" if code else b"")
    return run


def _record_doc(*records) -> bytes:
    return json.dumps({"schema": "acceptance-records/1", "dry_run": False, "records": list(records)}).encode()


def test_a_failed_listing_fetch_tree_or_blob_is_not_an_empty_record_set(monkeypatch):
    def script_for(failing):
        def script(args):
            if args[0] == failing:
                return b"", 128
            if args[0] == "ls-remote":
                return b"abc\trefs/heads/acceptance-record/run-1\n", 0
            if args[0] == "fetch":
                return b"", 0
            if args[0] == "ls-tree":
                return b"acceptance-records-1.json\n", 0
            return _record_doc({"role": "clean_control", "repository": "o/r", "lane": "R", "revision": "v", "audit_passed": True}), 0
        return script

    for failing in ("ls-remote", "fetch", "ls-tree", "show"):
        monkeypatch.setattr(subprocess, "run", _git_runner(script_for(failing)))
        with pytest.raises(seeder.RecordsUnavailable):
            seeder.judged_controls("origin")
    monkeypatch.setattr(subprocess, "run", _git_runner(script_for(None)))
    assert seeder.judged_controls("origin") == {("o/r", "R", "v", ""): True}


def test_no_acceptance_branches_is_a_genuinely_empty_set(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _git_runner(lambda args: (b"", 0)))
    assert seeder.judged_controls("origin") == {}


def test_the_gate_and_main_report_an_unreadable_record_set_instead_of_seeding(monkeypatch, capsys):
    def boom(remote="origin"):
        raise seeder.RecordsUnavailable("git ls-remote failed")

    monkeypatch.setattr(seeder, "judged_controls", boom)
    monkeypatch.setattr(seeder.run_request, "remote_heads", lambda remote: [])
    monkeypatch.setattr(seeder, "select_candidates", lambda remote="origin": {"L": [], "R": []})
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--gate", "--require-fresh", "--run-id", "1"])
    assert seeder.main() == 1
    assert "could not be read" in capsys.readouterr().err


def test_a_record_with_a_malformed_digest_judges_nothing_in_the_seeder(monkeypatch):
    good = candidate_sha256(b"x")
    docs = _record_doc(
        {"role": "clean_control", "repository": "o/r", "lane": "R", "revision": "v", "audit_passed": True, "candidate_sha256": "XYZ"},
        {"role": "clean_control", "repository": "o/s", "lane": "R", "revision": "v", "audit_passed": True, "candidate_sha256": good},
    )

    def script(args):
        return {"ls-remote": (b"abc\trefs/heads/acceptance-record/run-1\n", 0), "fetch": (b"", 0),
                "ls-tree": (b"acceptance-records-1.json\n", 0)}.get(args[0], (docs, 0))

    monkeypatch.setattr(subprocess, "run", _git_runner(script))
    assert seeder.judged_controls("origin") == {("o/s", "R", "v", good): True}
