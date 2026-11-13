"""The four shapes that made the zero-call restore unable to clear BC-05 / BC-17 (real data).

Hosted Lane R runs 43411932927 (aspose-3d-foss/Aspose.3D-FOSS-for-Python) and 43411924300
(aspose-words-foss/Aspose.Words-FOSS-for-.NET), both failing deterministically on BC-05/BC-17 with no
LLM review: the restore kept the lost units, but each restore added a new failing check and was
discarded whole.

1. BC-17 owed the registry install BC-02 forbids: ``validation.parity._fact_rows`` handed the parity
   gate facts WITHOUT their evidence, so ``unconfirmed_registry_packages`` (which reads the registry
   reading from the evidence) found nothing and ``inherited_unit:013.code_block``'s
   ``python3 -m pip install aspose-3d-foss`` stayed owed; restored, BC-02 failed on it.
2. The maintainers' API table (``inherited_unit:060.table``) sells three stubs as working
   (``FbxExporter.save``, ``Scene.render``, ``Watermark.encode/decode_watermark`` -- the same
   README's own limitation list, ``067.list``, says they raise): restored verbatim, BC-14 failed.
3. Words .NET's kept paragraphs link ``[open an issue](../../issues)``, the repository's github.com
   issues page, which BC-06 read as a missing tree path.
4. Words .NET's ``082.paragraph`` ends ``...looks useful to you:`` and was restored without the
   ``083.list`` it introduces: BC-07's dangling colon.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.restore_units import restore_lost_units
from repo_presenter.readme.validation.failures import DEFAULT_POLICY
from repo_presenter.readme.validation.links import link_failures
from repo_presenter.readme.validation.parity import parity_failures
from repo_presenter.readme.validation.surface_claims import kept_table_form, stub_rows

UNCONFIRMED = (
    "package registry: a distribution of this name exists, but ownership not confirmed: the "
    "registry's project URLs point at another repository"
)


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attrs: str) -> Fact:
    return Fact(
        fact_id, kind, value, (Evidence("README.md", None),), polarity=polarity,  # type: ignore[arg-type]
        attributes=attrs or None,
    )


# --- 1. BC-17 reads the registry reading the facts record -------------------------------------------

_BLOCK = "```bash\npython3 -m pip install aspose-3d-foss\n```"
_BENCH = f"# Aspose.3D FOSS for Python\n\n## Installation\n\n{_BLOCK}\n"
_CANDIDATE = (
    "# Aspose.3D FOSS for Python\n\n## Installation\n\nThe package `aspose-3d-foss` could not be "
    "confirmed on PyPI. Install from a source checkout:\n\n```bash\ngit clone "
    "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git\npip install .\n```\n"
)


def _install(polarity: str, reading: str) -> Fact:
    return Fact(
        "install_command:pip",
        "install_command",
        "pip install aspose-3d-foss",
        (
            Evidence("setup.py", "distribution name declared by the manifest"),
            Evidence("https://pypi.org/pypi/aspose-3d-foss/json", reading),
        ),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _parity_candidate(install: Fact) -> SimpleNamespace:
    unit = _fact(
        "inherited_unit:013.code_block", "inherited_unit", _BLOCK,
        section="Aspose.3D FOSS for Python > Installation",
    )
    facts = FactsDocument("aspose-3d-foss/Aspose.3D-FOSS-for-Python", "0" * 40, (unit, install))
    return SimpleNamespace(
        readme=_CANDIDATE,
        benchmark_readme=_BENCH,
        facts=facts,
        dispositions={
            "dispositions": [
                {
                    "unit_id": "inherited_unit:013.code_block",
                    "disposition": "SUPERSEDE_REDUNDANT",
                    "destination_section": "installation",
                    "rationale": "the Installation section replaces it",
                }
            ]
        },
    )


def test_bc17_does_not_owe_the_registry_install_of_an_unconfirmed_package() -> None:
    failures = parity_failures(_parity_candidate(_install("UNRESOLVED", UNCONFIRMED)))
    assert not [f for f in failures if "pip install aspose-3d-foss" in f.detail]


def test_bc17_still_owes_the_same_command_when_the_registry_confirms_the_package() -> None:
    failures = parity_failures(_parity_candidate(_install("SUPPORTED", "package registry: found")))
    assert any(
        f.unit == "inherited_unit:013.code_block" and "pip install aspose-3d-foss" in f.detail
        for f in failures
    )


# --- 2. a kept maintainers' table never prints a row selling a stated stub as working --------------

_LIMITS = _fact(
    "inherited_unit:067.list", "inherited_unit",
    "- FBX support is experimental. `FbxExporter.save()`/`save_to_stream()` both raise "
    "`NotImplementedError` outright, so FBX is import-only at best.\n"
    "- `Watermark.encode_watermark()`/`decode_watermark()` raise `NotImplementedError`.",
)
_TABLE = (
    "| Class | Description |\n|---|---|\n"
    "| `FbxExporter` | FbxExporter.save saves the given Scene to a file path using specified "
    "FbxSaveOptions. |\n"
    "| `FbxImporter` | FbxImporter.supports_format returns True if the given file format is "
    "supported for import. |\n"
    "| `Watermark` | Utility to encode/decode blind watermark to/from a mesh. |\n"
    "| `Mesh` | A polygon mesh with control points and polygons. |"
)


def _surface(*extra: Fact) -> FactsDocument:
    types = [
        _fact(f"public_symbol:aspose.threed.{name.lower()}", "public_symbol", f"aspose.threed.{name}")
        for name in ("FbxExporter", "FbxImporter", "Watermark", "Mesh")
    ]
    for fact in types:
        object.__setattr__(fact, "evidence", (Evidence("aspose/threed/__init__.py", "; class; "),))
        object.__setattr__(fact, "attributes", {"symbol_kind": "class"})
    table = _fact("inherited_unit:060.table", "inherited_unit", _TABLE)
    return FactsDocument("aspose-3d-foss/Aspose.3D-FOSS-for-Python", "0" * 40, (*types, table, *extra))


def test_a_row_selling_a_maintainer_stated_stub_is_not_printed() -> None:
    facts = _surface(_LIMITS)
    rows = stub_rows(_TABLE, facts)
    assert [row.split("|")[1].strip() for row in rows] == ["`FbxExporter`", "`Watermark`"]
    printed = kept_table_form(_TABLE, facts)
    assert "FbxExporter.save saves" not in printed and "encode/decode blind" not in printed
    assert "| `FbxImporter` |" in printed and "| `Mesh` |" in printed
    assert printed.splitlines()[:2] == ["| Class | Description |", "|---|---|"]


def test_without_a_limitation_statement_the_table_prints_as_written() -> None:
    assert kept_table_form(_TABLE, _surface()) == _TABLE


# --- 3. ../../issues is the repository's github.com issues page -------------------------------------


def _link_candidate(readme: str) -> SimpleNamespace:
    facts = FactsDocument("aspose-words-foss/Aspose.Words-FOSS-for-.NET", "0" * 40, ())
    return SimpleNamespace(
        readme=readme, facts=facts, tree_paths=["README.md", "src/Foo.cs"], plan={},
        policy=DEFAULT_POLICY,
    )


def test_a_github_issues_link_is_not_a_missing_tree_path() -> None:
    readme = "# T\n\nBug reports are welcome, please [open an issue](../../issues).\n"
    assert not [f for f in link_failures(_link_candidate(readme)) if "issues" in f.detail]


def test_a_missing_tree_path_still_fails() -> None:
    readme = "# T\n\nSee [the notes](docs/NOTES.md) and [more](../../issuesx).\n"
    details = [f.detail for f in link_failures(_link_candidate(readme))]
    assert any("docs/NOTES.md" in d for d in details) and any("issuesx" in d for d in details)


# --- 4. a restored lead-in brings the block it introduces -------------------------------------------

_SECTION = "Aspose.Words FOSS for .NET > Enjoying it? Star it"


def test_a_restored_lead_in_restores_its_block_into_the_same_section() -> None:
    lead = _fact(
        "inherited_unit:082.paragraph", "inherited_unit",
        "This project is brand new, and stars are how GitHub decides whether anyone else gets to "
        "discover it. If Aspose.Words FOSS looks useful to you:",
        section=_SECTION,
    )
    block = _fact(
        "inherited_unit:083.list", "inherited_unit",
        "- **Star** the repo.\n- **Watch** it.\n- **Tell someone.**",
        section=_SECTION,
    )
    facts = FactsDocument("aspose-words-foss/Aspose.Words-FOSS-for-.NET", "0" * 40, (lead, block))
    dispositions = {
        "dispositions": [
            {"unit_id": lead.id, "disposition": "SUPERSEDE_REDUNDANT", "destination_section": "opening"},
            {"unit_id": block.id, "disposition": "OMIT_UNSUPPORTED", "destination_section": None},
        ]
    }
    out, changes = restore_lost_units(
        dispositions, facts, [lead.id], {"scope_limitations", "opening"}, None
    )
    rows = {row["unit_id"]: row for row in out["dispositions"]}
    assert {change["unit_id"] for change in changes} == {lead.id, block.id}
    assert rows[lead.id]["disposition"] in {"VERIFIED_PRESERVE", "PRESERVE_ATTRIBUTED"}
    assert rows[block.id]["disposition"] in {"VERIFIED_PRESERVE", "PRESERVE_ATTRIBUTED"}
    assert rows[block.id]["destination_section"] == rows[lead.id]["destination_section"]
