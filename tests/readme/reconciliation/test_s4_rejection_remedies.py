"""Two S4 rejections that killed real generation runs (batch 1, 2026-11-09), each now resolved by
the remedy the rejection text itself names, applied by ``dispositions.normalize``.

Real text throughout: the unit texts and the model's final rejected replies are copied verbatim
from the call stores of the two failed runs (``aspose-3d-foss/Aspose.3D-FOSS-for-Python`` unit
057.paragraph; ``aspose-psd-foss/Aspose.PSD-FOSS-for-Python`` unit 012.code_block).
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    dangling_pointers,
    reconcile_checks,
)


def _unit(uid: str, text: str, section: str) -> Fact:
    return Fact(
        uid, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": section}
    )


def _padded(section: str, *units: Fact) -> tuple[Fact, ...]:
    """Unrelated units before and after, so none sits in dangling_pointers' unjudged tail."""
    before = tuple(
        _unit(f"inherited_unit:{i:03d}.paragraph", "An unrelated paragraph.", section)
        for i in range(1, 5)
    )
    after = tuple(
        _unit(f"inherited_unit:{i:03d}.paragraph", "A later unrelated paragraph.", section)
        for i in range(900, 904)
    )
    return (*before, *units, *after)


def _entry(unit_id: str, disposition: str, destination: str | None, fact_ids: list[str], why: str):
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": fact_ids,
        "rationale": why,
    }


# --- 3D Python, unit 057.paragraph: dangling_pointer ------------------------------------------

_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
_API = "Aspose.3D FOSS for Python > API Reference"
_057 = (
    "`Scene` is the primary entry point: `Scene.open()`/`Scene.save()` load and write a scene graph\n"
    "built from `Node` objects, each of which holds a `Transform`, an optional `Mesh`-derived\n"
    "`Entity`, and zero or more `Material` instances. The full public class index is listed below by\n"
    "module."
)


def _3d_facts(*units: Fact) -> FactsDocument:
    base = (
        Fact("identity:repository", "identity", _3D, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        Fact("package:name", "package", "aspose-3d-foss", (Evidence("x"),)),
    )
    units = units or (_unit("inherited_unit:057.paragraph", _057, _API),)
    return FactsDocument(_3D, "f" * 40, (*base, *_padded(_API, *units)))


# the model's first and third replies for this unit, verbatim
_3D_REPLIES = {
    "first": _entry(
        "inherited_unit:057.paragraph", "VERIFIED_PRESERVE", "api_reference", [],
        "The paragraph introduces the API Reference section and is preserved as written.",
    ),
    "third": _entry(
        "inherited_unit:057.paragraph", "VERIFIED_PRESERVE", "opening",
        ["public_symbol:aspose.threed.scene", "public_symbol:aspose.threed.node"],
        "The paragraph accurately describes Scene as the primary entry point and its relationship "
        "to Node, Transform, Mesh, and Material based on verified public symbols",
    ),
}


def test_the_real_rejected_dangling_pointer_replies_now_pass_by_rewrite() -> None:
    facts = _3d_facts()
    for reply in _3D_REPLIES.values():
        output = {"dispositions": [dict(reply)]}
        assert dangling_pointers(output, facts), "fixture must really be a dangling pointer"
        assert reconcile_checks(output, facts) == []
        entry = output["dispositions"][0]
        assert entry["disposition"] == "VERIFIED_REWRITE"
        assert entry["destination_section"] == reply["destination_section"]  # untouched
        assert entry["fact_ids"] == reply["fact_ids"]  # untouched, nothing invented


def test_an_attributed_unit_with_a_dangling_pointer_is_still_refused() -> None:
    # PRESERVE_ATTRIBUTED is unverified maintainer prose: never re-authored from facts.
    reply = dict(_3D_REPLIES["first"], disposition="PRESERVE_ATTRIBUTED")
    errors = reconcile_checks({"dispositions": [reply]}, _3d_facts())
    assert any("dangling_pointer" in error for error in errors)


def test_a_unit_with_no_dangling_pointer_is_left_as_written() -> None:
    plain = (
        "`Scene` is the primary entry point: `Scene.open()`/`Scene.save()` load and write a scene "
        "graph built from `Node` objects."
    )
    facts = _3d_facts(_unit("inherited_unit:057.paragraph", plain, _API))
    output = {"dispositions": [dict(_3D_REPLIES["first"])]}
    assert dangling_pointers(output, facts) == []
    assert reconcile_checks(output, facts) == []
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


# --- PSD Python, unit 012.code_block: uncited_redundant_defer ---------------------------------

_PSD = "aspose-psd-foss/Aspose.PSD-FOSS-for-Python"
_012 = "```bash\npip install aspose-psd-foss\n```  "
_PSD_REPLY = _entry(
    "inherited_unit:012.code_block", "SUPERSEDE_REDUNDANT", "installation", ["identity:ecosystem"],
    "The pip install command is the canonical installation method for this Python package and is "
    "rendered by the installation section.",
)


def _psd_facts(*, build: bool = True, extra: tuple[Fact, ...] = ()) -> FactsDocument:
    base = [
        Fact("identity:repository", "identity", _PSD, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        _unit("inherited_unit:012.code_block", _012, "Aspose.PSD FOSS for Python > Installation"),
    ]
    if build:
        base += [
            Fact("build_test_asset:examples", "build_test_asset", "samples/", (Evidence("x"),)),
            Fact(
                "build_test_asset:tests", "build_test_asset", "src/aspose_psd_foss_test/",
                (Evidence("x"),),
            ),
        ]
    return FactsDocument(_PSD, "f" * 40, (*base, *extra))


def test_the_real_rejected_install_block_is_now_kept_as_written_where_build_facts_exist() -> None:
    output = {"dispositions": [dict(_PSD_REPLY)]}
    assert reconcile_checks(output, _psd_facts()) == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "development_testing"
    assert set(entry["fact_ids"]) == {
        "identity:ecosystem", "build_test_asset:examples", "build_test_asset:tests",
    }


def test_with_no_build_or_install_fact_there_is_no_mechanical_remedy_and_the_refusal_stands() -> None:
    output = {"dispositions": [dict(_PSD_REPLY)]}
    errors = reconcile_checks(output, _psd_facts(build=False))
    assert any("uncited_redundant_defer" in error for error in errors)
    assert output["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"


def test_a_block_that_is_a_tracked_unresolved_example_is_deferred_not_preserved() -> None:
    example = Fact(
        "example:001", "example", "pip install aspose-psd-foss",
        (Evidence("README.md", "unit inherited_unit:012.code_block"),),
        polarity="UNRESOLVED",
    )
    output = {"dispositions": [dict(_PSD_REPLY)]}
    errors = reconcile_checks(output, _psd_facts(extra=(example,)))
    assert output["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"
    assert not any("uncited_redundant_defer" in error for error in errors)
