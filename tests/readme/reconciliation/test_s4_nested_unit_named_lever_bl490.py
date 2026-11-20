"""BL-490: a rejection that names a nested inherited unit (``014.002.list``) reaches the bounded asks.

Real data: hosted run 44701825510 (2026-11-20, PDF TypeScript Lane R), first model job S4
``source_reconciliation``: ``inherited_unit:014.002.list: uncited_prose_omit: OMIT_UNSUPPORTED on a
list needs at least one fact ID ... the unit's exact text is "- **Hyphenation** ..."``, rejected
twice and then a job error. The unit id has two numeric segments (a list nested under a numbered
heading); ``_UNIT_ERROR`` read one, so ``_rejected_unit_ids`` found no unit, returned ``[]`` ("a
defect no narrowed ask can address") and neither the narrowed ask nor ``_settle_unresolved`` ever ran.
The reply below is synthesised from the printed rejection and unit; no provider call is made.
"""

from __future__ import annotations

import json

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    _reconciliation_merge,
    _rejected_unit_ids,
    _settle_unresolved,
    reconcile_checks,
)

REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript"
SECTION = "Aspose.PDF FOSS for TypeScript > Features > Text"
NESTED = "inherited_unit:014.002.list"
TEXT = (
    "- **Hyphenation** — opt-in `hyphenate: { lang }` on `AddTextBlock`, soft-hyphen aware.\n"
    "- **Justification** — `align: 'justify'` on a text block."
)
LOGGED = (
    "inherited_unit:014.002.list: uncited_prose_omit: OMIT_UNSUPPORTED on a list needs at least "
    "one fact ID that shows the claim unsupported, or the unit must be placed in a section the "
    "shell can hold; the unit's exact text is "
)


def _unit(unit: str, text: str, section: str = SECTION) -> Fact:
    return Fact(unit, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": section})


def _facts(*extra: Fact, text: str = TEXT) -> FactsDocument:
    return FactsDocument(REPO, "f" * 40, (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "typescript", (Evidence("x"),)),
        Fact("package:name", "package", "@aspose/pdf-foss", (Evidence("x"),)),
        _unit(NESTED, text),
        *extra,
    ))


def _entry(disposition, destination=None, fact_ids=(), unit=NESTED) -> dict:
    return {"unit_id": unit, "disposition": disposition, "destination_section": destination,
            "fact_ids": list(fact_ids), "rationale": "No fact supports these features."}


def _reply(disposition="OMIT_UNSUPPORTED", destination=None, fact_ids=(), unit=NESTED) -> str:
    return json.dumps({"dispositions": [_entry(disposition, destination, fact_ids, unit)]})


def test_the_logged_rejection_is_reproduced_and_names_the_nested_unit() -> None:
    errors = reconcile_checks(json.loads(_reply()), _facts())
    assert any(e.startswith(LOGGED) for e in errors), errors
    assert _rejected_unit_ids(errors) == [NESTED]  # origin/main: [] (no narrowed ask, job error)


def test_every_depth_of_unit_id_is_named() -> None:
    lines = [f"inherited_unit:{n}: uncited_prose_omit: x" for n in ("003.paragraph", "014.002.list", "014.002.003.table")]
    assert _rejected_unit_ids(lines) == [l.split(": ")[0] for l in lines]


def test_the_nested_unit_is_kept_as_written_after_the_last_ask() -> None:
    facts = _facts()
    settled = json.loads(_settle_unresolved(_reply(), [NESTED], facts))["dispositions"][0]
    assert settled["disposition"] == "PRESERVE_ATTRIBUTED"
    assert settled["destination_section"] == "key_capabilities"
    assert settled["rationale"].startswith("Kept as the maintainers wrote it")
    assert "omitted" in settled["rationale"]
    assert reconcile_checks(json.loads(json.dumps({"dispositions": [settled]})), facts) == []


def test_the_narrowed_merge_path_settles_the_same_way() -> None:
    facts = _facts()
    merged = _reconciliation_merge(_reply(), _reply(), [NESTED])
    assert json.loads(_settle_unresolved(merged, [NESTED], facts))["dispositions"][0]["disposition"] == "PRESERVE_ATTRIBUTED"


def test_a_nested_code_block_is_kept_verified() -> None:
    unit = "inherited_unit:014.002.code_block"
    facts = FactsDocument(REPO, "f" * 40, (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("build_test_asset:npm", "build_test_asset", "npm test", (Evidence("package.json"),)),
        _unit(unit, "```ts\nnpm run demo\n```"),
    ))
    out = json.loads(_settle_unresolved(_reply(unit=unit), [unit], facts))["dispositions"][0]
    assert out["disposition"] == "VERIFIED_PRESERVE"


def test_a_unit_that_cannot_be_placed_fails_closed() -> None:
    facts = _facts()
    import repo_presenter.readme.reconciliation.dispositions as d
    original = d.nearest_holdable
    d.nearest_holdable = lambda *a, **k: None
    try:
        assert _settle_unresolved(_reply(), [NESTED], facts) == _reply()
    finally:
        d.nearest_holdable = original


def test_a_unit_citing_a_contradicted_fact_is_left_alone() -> None:
    bad = Fact("install_command:hyph", "install_command", "hyphenate", (Evidence("x"),), polarity="CONTRADICTED")
    facts = _facts(bad)
    reply = _reply(fact_ids=("install_command:hyph",))
    assert json.loads(_settle_unresolved(reply, [NESTED], facts))["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"


def test_a_shell_rendered_kind_is_left_alone() -> None:
    unit = "inherited_unit:014.002.badge_row"
    facts = FactsDocument(REPO, "f" * 40, (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        _unit(unit, "[![x](y)](z)"),
    ))
    reply = _reply(unit=unit)
    assert _settle_unresolved(reply, [unit], facts) == reply


def test_a_unit_not_asked_about_is_never_touched() -> None:
    other = "inherited_unit:015.paragraph"
    assert _settle_unresolved(_reply(), [other], _facts()) == _reply()


def test_a_passing_reply_is_returned_untouched() -> None:
    ok = _reply("VERIFIED_PRESERVE", "key_capabilities")
    # a list kept verified without a cited fact is judged by the real checks; the settle never alters a kept unit
    assert _settle_unresolved(ok, [NESTED], _facts()) == ok


def test_the_first_pass_still_refuses_the_uncited_omission() -> None:
    assert any("uncited_prose_omit" in e for e in reconcile_checks(json.loads(_reply()), _facts()))
