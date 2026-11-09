"""Structural checks on .github/workflows/audit-seed.yml (the M9 hosted seeder): manual dispatch
only, the Environment is declared (so AUDIT_SEED_KEY actually resolves), and the key is read
only through `secrets.*`, never hardcoded or read from any other source.
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


def test_dispatch_is_manual_only_no_push_or_schedule_trigger():
    _doc, text = _load()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "\non:\n  push:" not in text


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
    assert doc.get("permissions") == {"contents": "write"}


def test_candidates_and_manifest_are_uploaded_as_ephemeral_artifacts_not_committed():
    _doc, text = _load()
    assert "actions/upload-artifact" in text
    assert "seed_manifest.enc" in text
    # The manifest ciphertext itself is never committed to the repository -- only the
    # commitment hash and the (non-secret) case index are.
    assert "git add -f evidence" in text
    assert "seed_manifest.enc" not in text.split("git add -f")[-1]
