"""The receipt schema forbids additional properties, so a field the writer emits but the schema
omits makes every NEWLY written receipt INCOHERENT (found 2026-11-04: `checker_fileset_scheme`,
added to ops/gateverify.py without being added to schemas/receipt.schema.json; the fresh TC-012
receipt failed its own schema while `gatecli validate` still printed OK). These tests close that
class of drift."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "receipt.schema.json").read_text(encoding="utf-8"))
RECEIPTS = sorted((ROOT / "evidence" / "build").glob("*/*/receipt.json"))


def test_there_are_committed_receipts_to_check() -> None:
    assert RECEIPTS, "no receipts found: the glob or the layout changed"


@pytest.mark.parametrize("path", RECEIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.parent.name}")
def test_every_receipt_that_claims_acceptance_validates_against_the_schema(path: Path) -> None:
    """Only receipts that claim ``accepted: true`` are trusted, so only they must be well formed.
    Old non-accepted receipts that predate later schema fields (for example ``scope.evaluated``)
    are historical records, not live claims, and are left as they are."""
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if not receipt.get("accepted"):
        pytest.skip("not an accepted receipt: historical record, not a live claim")
    jsonschema.validate(receipt, SCHEMA)


def test_every_top_level_field_the_writer_emits_is_declared_in_the_schema() -> None:
    """Read the writer's source: EVERY receipt dict literal in ops/gateverify.py (it builds more
    than one: an early-exit path and the full one). Every top-level string key any of them assigns
    must be a declared schema property."""
    source = (ROOT / "ops" / "gateverify.py").read_text(encoding="utf-8")
    keys: set[str] = set()
    literals = 0
    position = 0
    while (hit := source.find('"schema_version": 1', position)) != -1:
        start = source.rindex("\n", 0, hit) + 1
        block = source[start : source.index("\n    }\n", start)]
        keys |= set(re.findall(r'^ {8}"([a-z_0-9]+)":', block, flags=re.MULTILINE))
        literals += 1
        position = hit + 1
    assert literals >= 2, "expected the early-exit and the full receipt literals"
    assert {"schema_version", "card", "accepted", "checker_fileset_scheme"} <= keys, keys
    missing = keys - set(SCHEMA["properties"])
    assert not missing, f"fields written by gateverify but absent from receipt.schema.json: {missing}"


def test_a_scheme_value_is_accepted_and_an_unknown_one_is_not() -> None:
    receipt = json.loads(RECEIPTS[0].read_text(encoding="utf-8"))
    receipt["checker_fileset_scheme"] = "v2"
    jsonschema.validate(receipt, SCHEMA)
    receipt["checker_fileset_scheme"] = "v9"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(receipt, SCHEMA)
