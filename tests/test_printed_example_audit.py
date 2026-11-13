"""scripts/printed_example_audit.py: every printed example mapped to its fact, by the pipeline's
own identity (normalized code of the value or of the printed, prelude-carrying program)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "printed_example_audit", REPO / "scripts" / "printed_example_audit.py"
)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


def _example(ordinal: int, code: str, polarity: str, receipt: str, prelude: str = "") -> Fact:
    return Fact(
        f"example:{ordinal:03d}",
        "example",
        code,
        (
            Evidence("README.md", f"lines 1-3; python fence; unit inherited_unit:00{ordinal}.code_block"),
            Evidence("receipts.json", receipt),
        ),
        polarity=polarity,  # type: ignore[arg-type]
        attributes={"prelude": prelude} if prelude else None,
    )


def test_every_printed_fence_is_mapped_to_its_fact_with_its_cause() -> None:
    facts = FactsDocument(
        repository="o/r",
        source_revision="a" * 40,
        facts=(
            _example(1, "print(greet())\n", "SUPPORTED", "example 1: EXECUTED; exit 0",
                     prelude="from widget import greet"),
            _example(2, "scene.open('model.obj')\n", "UNRESOLVED",
                     "example 2: NEEDS_INPUT; FileNotFoundError: the example opens an input"),
            _example(3, "print(Document())\n", "CONTRADICTED", "example 3: FAILED; NameError"),
        ),
    )
    readme = (
        "# R\n\n```python\nfrom widget import greet\nprint(greet())\n```\n\n"
        "```py\nscene.open('model.obj')\n```\n\n"
        "```python\nprint(Document())\n```\n\n"
        "```bash\npip install widget\n```\n\n"
        "```python\nprint('never extracted')\n```\n"
    )
    rows = audit.audit_readme(readme, facts, "python")
    assert [(r["fact"], r["polarity"]) for r in rows] == [
        ("example:001", "SUPPORTED"),
        ("example:002", "UNRESOLVED"),
        ("example:003", "CONTRADICTED"),
        (None, "NO_FACT"),
    ]
    assert rows[0]["cause"] == ""
    assert rows[1]["cause"] == "needs an input file the repository does not provide"
    assert rows[2]["cause"] == "failed: NameError (README import not supplied)"
    report = audit.summary([{**r, "lane": "L", "ecosystem": "python", "repository": "o/r"} for r in rows])
    assert report["printed"] == 4
    assert report["by_lane"] == {"L": {"SUPPORTED": 1, "UNRESOLVED": 1, "CONTRADICTED": 1, "NO_FACT": 1}}


def test_the_cause_classes_follow_the_verifiers_own_wording() -> None:
    assert audit.cause("example 1: NOT_VERIFIED; x.csproj : error NU1902: Warning As Error") == (
        "toolchain: NuGet vulnerability audit as error (date-dependent, not the revision)"
    )
    assert audit.cause("BLOCKED_TOOLCHAIN: the Cargo toolchain did not report a version").startswith(
        "toolchain: rustup"
    )
    assert audit.cause("the fence uses `sheet` without binding it").startswith("fragment")
    assert audit.cause("example 4: FAILED; TypeError") == "failed: the code is wrong at this revision"
