"""The ported slice of the consumed-scope recheck: currency states, classification, receipts,
and the patch round-trip.

Adapted from the old repository-presenter project's
``tests/components/readme/bundle/test_recheck.py``. That file's "pure pieces" section (the only
part not built on a real committed bundle + registry + prompts + validation/review/composition
fixture) is ported close to verbatim below. Everything built on ``Fixture`` (a real sealed bundle
copied beside the old repo's own ``data/registry.json`` and ``prompts/``) is dropped, because it
exercises ``recheck_bundle``/``recheck_portfolio`` -- not ported here; see
``repo_presenter.readme.bundle.recheck``'s module docstring for exactly what is missing and why.
The receipt tests below are rewritten to construct :class:`Recheck` rows directly instead of
through ``recheck_bundle``, since the receipt cache itself (``receipt_key``/``read_receipt``/
``write_receipt``) does not need a bundle at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.readme.bundle import recheck
from repo_presenter.readme.bundle.recheck import (
    CURRENT,
    RECHECKED_CURRENT,
    UNVERIFIED,
    UPDATE_OPTIONAL,
    UPDATE_REQUIRED,
    Recheck,
    ScopeResult,
    classify,
    read_receipt,
    receipt_key,
    recheck_scope,
    render_lines,
    reverse_apply,
    write_receipt,
)

DIRECTORY = "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python"


def test_a_difference_the_recheck_has_no_row_for_raises_rather_than_guessing() -> None:
    with pytest.raises(Exception, match="no recheck for the dependency 'surprise'"):
        recheck_scope("surprise")
    assert recheck_scope("prompts.anything") == "provenance"
    assert recheck_scope("environment.inherited_units_version") == "extraction"


def _result(scope: str, outcome: str) -> ScopeResult:
    return ScopeResult(scope, outcome, ("x",))


@pytest.mark.parametrize(
    ("scopes", "currency", "cost"),
    [
        ([], CURRENT, None),
        ([_result("provenance", "PROVENANCE")], UPDATE_OPTIONAL, None),
        ([_result("validator", "PASSED")], RECHECKED_CURRENT, None),
        (
            [_result("validator", "PASSED"), _result("provenance", "PROVENANCE")],
            RECHECKED_CURRENT,
            None,
        ),
        ([_result("reviewer", "UNVERIFIED")], UNVERIFIED, None),
        ([_result("presentation", "FAILED")], UPDATE_REQUIRED, "rerender_only"),
        (
            [_result("presentation", "FAILED"), _result("validator", "FAILED")],
            UPDATE_REQUIRED,
            "recompose",
        ),
        ([_result("reviewer", "FAILED")], UPDATE_REQUIRED, "recompose"),
        (
            [_result("reviewer", "UNVERIFIED"), _result("authoring", "FAILED")],
            UPDATE_REQUIRED,
            "recompose",
        ),
    ],
)
def test_the_currency_follows_the_scope_outcomes(
    scopes: list[ScopeResult], currency: str, cost: str | None
) -> None:
    assert classify(scopes) == (currency, cost)


def test_the_original_readme_is_recovered_only_when_the_patch_round_trips() -> None:
    original = "# Title\n\nold line\nkept\n"
    candidate = "# Title\n\nnew line\nkept\nadded\n"
    patch = recheck.render_patch(original, candidate)
    assert reverse_apply(candidate, patch) == original
    assert recheck.original_readme(candidate, patch) == original
    # a patch that is not the diff of what it recovers is not trusted
    assert recheck.original_readme(candidate, patch.replace("@@ -1,4", "@@ -1,9")) is None
    assert recheck.original_readme(candidate, patch + "-extra\n") is None


def test_the_rendering_names_every_state_and_the_split() -> None:
    row = Recheck(DIRECTORY, "a" * 40, UPDATE_REQUIRED, "recompose", (), (), (), "k")
    text = "\n".join(render_lines([row]))
    assert "UPDATE_REQUIRED (recompose)" in text and "recompose 1" in text
    assert "counted 0 of 1" in text


# --- receipts: a cache keyed by the manifest digest and the running constants ------------------
# Rewritten against Recheck/receipt_key/write_receipt/read_receipt directly (no recheck_bundle).


def _row(currency: str = RECHECKED_CURRENT) -> Recheck:
    return Recheck(
        DIRECTORY,
        "a" * 40,
        currency,
        None,
        ("components.renderer",),
        (),
        (ScopeResult("presentation", "PASSED", ("components.renderer",), "re-render matches"),),
        "",
    )


def test_a_receipt_is_a_cache_keyed_by_the_manifest_digest_and_the_running_constants(
    tmp_path: Path,
) -> None:
    code = {"components": {"renderer": "1"}, "environment": {}}
    manifest_sha = "m" * 64
    key = receipt_key(manifest_sha, code)
    computed = Recheck(**{**_row().__dict__, "key": key})
    path = write_receipt(tmp_path, computed, manifest_sha)
    assert path == tmp_path / "candidates" / DIRECTORY / "rechecks" / (computed.revision + ".json")

    cached = read_receipt(tmp_path, DIRECTORY, computed.revision, key)
    assert cached is not None and cached.cached
    assert cached.currency == computed.currency
    assert [s.to_json() for s in cached.scopes] == [s.to_json() for s in computed.scopes]


def test_a_receipt_under_another_key_or_with_a_forged_body_is_ignored(tmp_path: Path) -> None:
    code = {"components": {"renderer": "1"}, "environment": {}}
    manifest_sha = "m" * 64
    key = receipt_key(manifest_sha, code)
    computed = Recheck(**{**_row().__dict__, "key": key})
    path = write_receipt(tmp_path, computed, manifest_sha)

    # another running code: the constants the scopes consumed differ, so the key does
    other = {"components": {"renderer": "9999"}, "environment": {}}
    assert receipt_key(manifest_sha, other) != key
    assert read_receipt(tmp_path, DIRECTORY, computed.revision, key) is not None
    assert (
        read_receipt(tmp_path, DIRECTORY, computed.revision, receipt_key(manifest_sha, other))
        is None
    )
    # another manifest digest (the state moved, say) is another key as well
    assert receipt_key("0" * 64, code) != key

    # a forged receipt: the currency edited by hand no longer hashes to its own digest
    document = json.loads(path.read_text(encoding="utf-8"))
    document["currency"] = CURRENT
    path.write_text(json.dumps(document), encoding="utf-8")
    assert read_receipt(tmp_path, DIRECTORY, computed.revision, key) is None
    path.write_text("not json", encoding="utf-8")
    assert read_receipt(tmp_path, DIRECTORY, computed.revision, key) is None


def test_recheck_bundle_and_recheck_portfolio_name_what_they_still_need() -> None:
    """The orchestration this port deliberately leaves out raises rather than faking a result."""
    with pytest.raises(NotImplementedError, match="core.candidates"):
        recheck.recheck_bundle()
    with pytest.raises(NotImplementedError, match="recheck_bundle"):
        recheck.recheck_portfolio()
