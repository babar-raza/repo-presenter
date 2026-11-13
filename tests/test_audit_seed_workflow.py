"""Structural checks on .github/workflows/audit-seed.yml (the M9 round): the schedule, dispatch and
workflow_call triggers only (R37, 2026-11-13: the round runs itself; a gate job spends a seed only when
no batch is open), the Environment is declared on the seed job (so AUDIT_SEED_KEY actually resolves),
and the key is read only through `secrets.*`, never hardcoded or read from any other source.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO / ".github" / "workflows" / "audit-seed.yml"


def _load():
    # "on" parses as the boolean True under PyYAML's default loader; load raw text too for the
    # trigger check instead of relying on the parsed key.
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_workflow_file_exists_and_parses():
    doc, _text = _load()
    assert "jobs" in doc
    assert "seed" in doc["jobs"]


def test_triggers_are_schedule_dispatch_and_call_never_push():
    doc, text = _load()
    triggers = doc["on"] if "on" in doc else doc[True]
    assert set(triggers) == {"schedule", "workflow_dispatch", "workflow_call"}
    assert "\non:\n  push:" not in text
    # the seed job only runs when the gate (one open batch at a time) said so
    assert doc["jobs"]["seed"]["needs"] == "gate"
    assert doc["jobs"]["seed"]["if"] == "needs.gate.outputs.action == 'seed'"


def test_the_environment_is_declared_so_audit_seed_key_resolves():
    doc, _text = _load()
    job = doc["jobs"]["seed"]
    assert job.get("environment") == "acceptance-audit"


def test_audit_seed_key_is_read_only_through_secrets_never_hardcoded():
    _doc, text = _load()
    assert "secrets.AUDIT_SEED_KEY" in text
    # No 32-byte hex literal anywhere that could be a hardcoded key standing in for the secret.
    import re

    assert not re.search(r"AUDIT_SEED_KEY\s*:\s*[\"']?[0-9a-fA-F]{64}", text)


def test_permissions_are_minimal_contents_write_only_for_the_commitment_commit():
    doc, _text = _load()
    assert doc.get("permissions") == {"contents": "read"}
    assert doc["jobs"]["gate"]["permissions"] == {"contents": "read"}
    assert doc["jobs"]["seed"]["permissions"] == {"contents": "write"}


def test_candidates_and_manifest_are_uploaded_as_ephemeral_artifacts_not_committed():
    _doc, text = _load()
    assert "actions/upload-artifact" in text
    assert "seed_manifest.enc" in text
    # The manifest ciphertext itself is never committed to the repository -- only the
    # commitment hash and the (non-secret) case index are.
    assert "git add -f evidence" in text
    assert "seed_manifest.enc" not in text.split("git add -f")[-1]
