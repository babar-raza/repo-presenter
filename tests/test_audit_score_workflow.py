"""Structural checks on .github/workflows/audit-score.yml (the M9 hosted scorer): manual
dispatch only, the Environment is declared, the key is read only through `secrets.*`, and the
decrypted manifest/scorecard never gets committed in plaintext.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO / ".github" / "workflows" / "audit-score.yml"


def _load():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_workflow_file_exists_and_parses():
    doc, _text = _load()
    assert "jobs" in doc
    assert "score" in doc["jobs"]


def test_dispatch_is_manual_only_no_push_or_schedule_trigger():
    _doc, text = _load()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "\non:\n  push:" not in text


def test_the_environment_is_declared_so_audit_seed_key_resolves():
    doc, _text = _load()
    job = doc["jobs"]["score"]
    assert job.get("environment") == "acceptance-audit"


def test_audit_seed_key_is_read_only_through_secrets_never_hardcoded():
    _doc, text = _load()
    assert "secrets.AUDIT_SEED_KEY" in text
    import re

    assert not re.search(r"AUDIT_SEED_KEY\s*:\s*[\"']?[0-9a-fA-F]{64}", text)


def test_only_the_scorecard_is_committed_never_the_manifest_or_its_plaintext():
    _doc, text = _load()
    add_section = text.split("git add -f")[-1]
    assert "scorecard" in add_section
    assert "seed_manifest" not in add_section
