"""scripts/maintainer_content_audit.py (requirement 6 of docs/MAINTAINER_CONTENT_PRESERVATION.md)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "maintainer_content_audit", REPO / "scripts" / "maintainer_content_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_a_superseded_unit_whose_values_vanished_has_low_coverage():
    readme = "## API Reference\n\n| Type | Description |\n|---|---|\n| `HorizontalAlignment` | Alignment. |\n"
    unit = "- `HorizontalAlignment`: `Left`, `Center`, `Right`, `Justify`"
    assert audit.coverage(unit, readme) < audit.LOW
    assert audit.coverage("too short", readme) == 1.0


def test_omission_reasons_follow_the_rationale():
    assert audit.omission_reason("example:002 is CONTRADICTED", "inherited_unit:1.code_block") == (
        "tied to a CONTRADICTED example"
    )
    assert audit.omission_reason("", "inherited_unit:007.heading") == "heading, wrapper or badge markup"
    assert audit.omission_reason("No fact supports the table", "inherited_unit:012.table") == (
        "no fact supports it"
    )


def test_a_bundle_is_audited_from_its_own_files(tmp_path):
    key = "org__Repo"
    revision = tmp_path / key / key / ("a" * 40)
    revision.mkdir(parents=True)
    (revision.parent / "CURRENT").write_text("a" * 40, encoding="utf-8")
    (revision / "README.md").write_text("Supports Windows only.\n", encoding="utf-8")
    facts = [
        {"id": "inherited_unit:001.paragraph", "kind": "inherited_unit",
         "value": "Runs on Windows, Linux, macOS, Docker containers and serverless functions."},
        {"id": "inherited_unit:002.paragraph", "kind": "inherited_unit", "value": "Old marketing."},
    ]
    (revision / "facts.json").write_text(json.dumps({"facts": facts}), encoding="utf-8")
    rows = [
        {"unit_id": "inherited_unit:001.paragraph", "disposition": "SUPERSEDE_REDUNDANT",
         "rationale": "covered by package:target_framework"},
        {"unit_id": "inherited_unit:002.paragraph", "disposition": "OMIT_UNSUPPORTED",
         "rationale": "promotional"},
    ]
    (revision / "dispositions.json").write_text(json.dumps({"dispositions": rows}), encoding="utf-8")
    found = audit.bundle_dirs(tmp_path)
    assert list(found) == [key]
    result = audit.audit_bundle(found[key])
    assert result["counts"] == {"SUPERSEDE_REDUNDANT": 1, "OMIT_UNSUPPORTED": 1}
    assert result["omitted"] == {"promotional": 1}
    assert result["superseded"][0]["coverage"] < audit.LOW
