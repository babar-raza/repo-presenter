"""Post-render correction of a stated "N public types" count the facts contradict.

Real text: the Go sentence is the live aspose.org README's own wording (Aspose.Cells-FOSS-for-Go,
which prints "14 public types" against 192 SUPPORTED public_symbol class/enum facts); the facts here
carry only the symbol kinds the count reads, generated in the same shape the extractors emit.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import correct_stated_type_counts

GO_SENTENCE = (
    "- **[Full API reference](https://reference.aspose.org/cells/go/)** - the complete, browsable "
    "reference for all 14 public types (the [API reference](#api-reference) section above covers "
    "the entry points)."
)


def _facts(classes: int, enums: int = 0, unsupported: int = 0) -> FactsDocument:
    def symbol(name: str, kind: str, polarity: str = "SUPPORTED") -> Fact:
        return Fact(
            id=f"public_symbol:{name.lower()}", kind="public_symbol", value=name,  # type: ignore[arg-type]
            evidence=(Evidence("src/api.go", None),), polarity=polarity,  # type: ignore[arg-type]
            attributes={"symbol_kind": kind},
        )

    rows = [symbol(f"Class{i}", "class") for i in range(classes)]
    rows += [symbol(f"Enum{i}", "enum") for i in range(enums)]
    rows += [symbol(f"Gone{i}", "class", "UNRESOLVED") for i in range(unsupported)]
    return FactsDocument("aspose-cells-foss/Aspose.Cells-FOSS-for-Go", "0" * 40, tuple(rows))


def test_the_published_stale_count_is_corrected_to_the_facts() -> None:
    text = f"# Aspose.Cells FOSS for Go\n\n{GO_SENTENCE}\n"
    fixed = correct_stated_type_counts(text, _facts(classes=180, enums=12))
    assert "all 192 public types" in fixed and "14 public types" not in fixed
    assert fixed.replace("192", "14") == text  # digits only; every other byte unchanged


def test_unsupported_symbols_are_not_counted() -> None:
    fixed = correct_stated_type_counts(GO_SENTENCE, _facts(classes=10, unsupported=5))
    assert "all 10 public types" in fixed


def test_a_count_that_already_matches_is_left_alone() -> None:
    text = GO_SENTENCE.replace("14", "192")
    assert correct_stated_type_counts(text, _facts(classes=180, enums=12)) == text


def test_a_count_inside_a_fenced_code_block_is_never_edited() -> None:
    text = f"Intro.\n\n```go\n// 14 public types in this sample output\n```\n\n{GO_SENTENCE}\n"
    fixed = correct_stated_type_counts(text, _facts(classes=180, enums=12))
    assert "// 14 public types in this sample output" in fixed
    assert "all 192 public types" in fixed


def test_no_computable_type_count_means_no_change() -> None:
    assert correct_stated_type_counts(GO_SENTENCE, _facts(classes=0)) == GO_SENTENCE


def test_a_text_without_a_stated_count_is_returned_unchanged() -> None:
    text = "Plain prose with 3 return classes in an example.\n\n```\ncode\n```\n"
    assert correct_stated_type_counts(text, _facts(classes=50)) == text


# --- a stubbed type / member is described as such in the Core API row ------------------------------
#
# Real text: Aspose.3D-FOSS-for-Python's Scope and Limitations (inherited_unit:067.list) says
# "`Watermark.encode_watermark()`/`decode_watermark()` and every `TransformBuilder` method raise
# `NotImplementedError`", and the Core API row for `Watermark` printed its docstring as a working
# capability, which BC-14 and the reviewer's claim_contradiction both blocked.

from pathlib import Path  # noqa: E402

from repo_presenter.core.registry.loader import load_registry  # noqa: E402
from repo_presenter.extractors.platforms.registry import plugin_for  # noqa: E402
from repo_presenter.readme.composition.renderer import RenderContext, _api_reference  # noqa: E402

THREED_PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
LIMITATIONS = (
    "- `Watermark.encode_watermark()`/`decode_watermark()` and every `TransformBuilder` method raise\n"
    "  `NotImplementedError` — build node transforms through `Transform`'s own translation,\n"
    "  rotation, and scaling properties instead of the fluent `TransformBuilder` chain.\n"
)


def _symbol(name: str, doc: str) -> Fact:
    return Fact(
        id=f"public_symbol:aspose.threed.utilities.{name.lower()}", kind="public_symbol",
        value=f"aspose.threed.utilities.{name}",  # type: ignore[arg-type]
        evidence=(Evidence("aspose/threed/utilities/x.py", None),), polarity="SUPPORTED",
        attributes={"symbol_kind": "class", "docstring": doc, "signature": f"class {name}"},
    )


def _rows(*extra_units: str) -> list[str]:
    registry = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")
    entry = next(e for e in registry.entries if e.repository == THREED_PYTHON)
    plugin_for(entry.ecosystem)
    facts = [
        _symbol("Watermark", "Utility to encode/decode blind watermark to/from a mesh."),
        _symbol("Mesh", "A polygon mesh."),
        _symbol("TransformBuilder", "Builds transforms."),
        Fact(
            id="inherited_unit:067.list", kind="inherited_unit", value=LIMITATIONS,  # type: ignore[arg-type]
            evidence=(Evidence("README.md", None),), polarity="SUPPORTED",
            attributes={"section": "Aspose.3D FOSS for Python > Scope and Limitations"},
        ),
    ]
    context = RenderContext(
        entry, FactsDocument(THREED_PYTHON, "0" * 40, tuple(facts)),
        {"sections": [], "api_hubs": []}, {"units": []}, {"dispositions": []},
    )
    return [line for line in _api_reference(context) if line.startswith("| `")]


def test_a_type_with_stubbed_members_says_so_inside_its_description_sentence() -> None:
    rows = {line.split("`")[1]: line for line in _rows()}
    # inside the first sentence: the validator judges one sentence at a time
    assert rows["Watermark"] == (
        "| `Watermark` | Utility to encode/decode blind watermark to/from a mesh "
        "(some members not implemented). |"
    )


def test_a_type_the_limitations_do_not_name_keeps_its_plain_description() -> None:
    rows = {line.split("`")[1]: line for line in _rows()}
    assert rows["Mesh"] == "| `Mesh` | A polygon mesh. |"


def test_a_wholly_stubbed_type_reads_not_implemented() -> None:
    # "every `TransformBuilder` method raise ..." stubs the type's members; a bare stubbed type
    # (StubIndex.types) is rendered "Not implemented." -- exercised through the same code path.
    from repo_presenter.readme.composition import renderer

    class _Idx:
        types = {"Mesh": "inherited_unit:1"}
        members: dict[str, dict[str, str]] = {}

        def __bool__(self) -> bool:
            return True

    registry = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")
    entry = next(e for e in registry.entries if e.repository == THREED_PYTHON)
    plugin_for(entry.ecosystem)
    facts = FactsDocument(THREED_PYTHON, "0" * 40, (_symbol("Mesh", "A polygon mesh."),))
    context = RenderContext(entry, facts, {"sections": []}, {"units": []}, {"dispositions": []})
    context._stub_cache = (_Idx(), {"aspose.threed.utilities.Mesh": "Mesh"})  # type: ignore[attr-defined]
    assert renderer._stub_marked(context, facts.facts[0], "A polygon mesh.") == "Not implemented."
