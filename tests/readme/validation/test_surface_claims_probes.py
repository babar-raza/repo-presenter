"""TC-017b work item 3: TC-017a's independent export-surface probes wired additively into
``surface_claims.py``'s rules (h) (type counts) and (i) (API-table names).

Every fixture is a real, on-disk Python package (the simplest ecosystem probe to exercise end to
end) plus a facts document that, in the "bug" cases, deliberately disagrees with what is actually
on disk -- the exact common-mode gap this card exists to close: a wrong extractor fact that would
otherwise go unchallenged because the only check available was built from that same wrong fact.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import _lines, claim_findings
from repo_presenter.readme.validation.surface_claims import surface_findings

REVISION = "a" * 40


def _write_fixture_package(root: Path) -> None:
    """A real Python package with exactly two public classes, ``Widget`` and ``Gadget``."""
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "widget.py").write_text(
        "class Widget:\n"
        "    def render(self):\n"
        "        pass\n"
        "\n"
        "class Gadget:\n"
        "    def spin(self):\n"
        "        pass\n",
        encoding="utf-8",
    )


def _type_fact(qualified_name: str) -> Fact:
    return Fact(
        f"public_symbol:{qualified_name.lower()}",
        "public_symbol",
        qualified_name,
        (Evidence("pkg/widget.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class"},
    )


def _ecosystem_fact() -> Fact:
    return Fact(
        "identity:ecosystem",
        "identity",
        "python",
        (Evidence("pyproject.toml", "ecosystem detected"),),
    )


def _facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        "acme/widgets",
        REVISION,
        (_ecosystem_fact(), _type_fact("pkg.widget.Widget"), _type_fact("pkg.widget.Gadget"), *extra),
    )


TABLE = (
    "| Class | Description |\n"
    "|---|---|\n"
    "| `Widget` | Renders the primary view. |\n"
    "| `Gadget` | Spins the secondary view. |\n"
)


# --- rule (i): API-table names, probe-confirmed ------------------------------------------------


def test_a_table_the_facts_and_the_probe_both_confirm_passes(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    findings = surface_findings(_lines(TABLE), _facts(), probe_root=tmp_path)
    assert findings == []


def test_a_name_the_facts_call_known_but_the_probe_says_is_not_exported_fails(
    tmp_path: Path,
) -> None:
    _write_fixture_package(tmp_path)
    # The facts document claims a third public class, "Phantom" -- an extractor bug: no such
    # class exists anywhere in the real source tree.
    bogus = _type_fact("pkg.widget.Phantom")
    readme = TABLE + "| `Phantom` | Materializes on demand. |\n"
    findings = surface_findings(_lines(readme), _facts(bogus), probe_root=tmp_path)
    assert len(findings) == 1
    assert "`Phantom`" in findings[0].detail
    assert "python export-surface probe" in findings[0].detail
    assert "pkg.widget.Phantom" in findings[0].detail


def test_without_a_probe_root_the_same_bogus_fact_is_not_caught(tmp_path: Path) -> None:
    # Confirms the wiring is additive, never a silent behavior change for a caller that supplies
    # no probe_root (every production caller today) -- the facts alone call `Phantom` known, so
    # with no probe the row is not flagged at all.
    _write_fixture_package(tmp_path)
    bogus = _type_fact("pkg.widget.Phantom")
    readme = TABLE + "| `Phantom` | Materializes on demand. |\n"
    assert surface_findings(_lines(readme), _facts(bogus)) == []
    assert surface_findings(_lines(readme), _facts(bogus), probe_root=None) == []


def test_an_unknown_ecosystem_never_crashes_and_adds_no_finding(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    other_ecosystem = Fact(
        "identity:ecosystem", "identity", "cobol", (Evidence("x", "y"),)
    )
    facts = FactsDocument(
        "acme/widgets",
        REVISION,
        (
            other_ecosystem,
            _type_fact("pkg.widget.Widget"),
            _type_fact("pkg.widget.Gadget"),
            _type_fact("pkg.widget.Phantom"),
        ),
    )
    readme = TABLE + "| `Phantom` | Materializes on demand. |\n"
    assert surface_findings(_lines(readme), facts, probe_root=tmp_path) == []


def test_a_probe_root_with_no_ecosystem_fact_at_all_never_crashes(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    facts = FactsDocument(
        "acme/widgets",
        REVISION,
        (_type_fact("pkg.widget.Widget"), _type_fact("pkg.widget.Gadget")),
    )
    assert surface_findings(_lines(TABLE), facts, probe_root=tmp_path) == []


# --- rule (h): type counts, probe-confirmed -----------------------------------------------------


def test_a_stated_count_the_facts_allow_but_the_probe_contradicts_fails(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    # A third fact (another extractor bug) inflates the fact-derived type count to 3, and a
    # generated sentence states exactly that inflated, fact-matching number -- the fact-only
    # check alone has nothing to flag, since the stated count matches the (wrong) facts exactly.
    bogus = _type_fact("pkg.widget.Phantom")
    readme = "The public API surface spans 3 public types, listed below.\n"
    findings = surface_findings(_lines(readme), _facts(bogus), probe_root=tmp_path)
    assert len(findings) == 1
    assert "'3 public types'" in findings[0].detail
    assert "counts 2, not 3" in findings[0].detail


def test_a_stated_count_the_facts_and_the_probe_both_agree_on_passes(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    readme = "The public API surface spans 2 public types, listed below.\n"
    assert surface_findings(_lines(readme), _facts(), probe_root=tmp_path) == []


def test_without_a_probe_root_the_inflated_count_claim_passes_the_fact_only_check(
    tmp_path: Path,
) -> None:
    _write_fixture_package(tmp_path)
    bogus = _type_fact("pkg.widget.Phantom")
    readme = "The public API surface spans 3 public types, listed below.\n"
    assert surface_findings(_lines(readme), _facts(bogus)) == []


# --- end-to-end through claim_findings -----------------------------------------------------------


def test_claim_findings_threads_probe_root_through_to_the_surface_rules(tmp_path: Path) -> None:
    _write_fixture_package(tmp_path)
    bogus = _type_fact("pkg.widget.Phantom")
    readme = TABLE + "| `Phantom` | Materializes on demand. |\n"
    findings = claim_findings(readme, _facts(bogus), probe_root=tmp_path)
    assert len(findings) == 1 and "`Phantom`" in findings[0].detail
    assert claim_findings(readme, _facts(bogus)) == []
