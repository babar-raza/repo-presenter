"""BL-390: the M9 auditor treats the renderer's own fact-true API row as the renderer's.

Hosted M9 round 44588173276, clean control Aspose.Note Python line 301: ``| `IncorrectDocumentStructureException` |
Declared; not thrown by library code. |`` is printed by the renderer from the SUPPORTED fact
``implementation:never_thrown.aspose.note.incorrectdocumentstructureexception`` (it REPLACED the authored
sentence), yet the sentinel re-derivation labelled it ``authored``, so the model's ``contradiction`` finding on it
(``kept_because: authored unit text``) could not be cleared and counted as an auditor false flag. The fixture is
the control's own stored facts (trimmed to four types), plan, dispositions and authored units.
"""

from __future__ import annotations

import gzip
import importlib.util
import shutil
from pathlib import Path

from repo_presenter.core.facts import read_facts
from repo_presenter.core.registry.loader import load_registry, require_listed

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "m9" / "note_bl390"


def _auditor():
    spec = importlib.util.spec_from_file_location("run_m9_auditor", REPO / "scripts" / "run_m9_auditor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bundle(tmp_path: Path) -> Path:
    for name in ("facts", "content_units", "plan", "dispositions"):
        with gzip.open(FIXTURE / f"{name}.json.gz", "rb") as source, (tmp_path / f"{name}.json").open("wb") as target:
            shutil.copyfileobj(source, target)
    return tmp_path


def test_the_not_thrown_row_is_the_renderers_and_a_flag_on_it_is_cleared(tmp_path):
    auditor = _auditor()
    bundle = _bundle(tmp_path)
    entry = require_listed(load_registry(REPO / "data" / "registry.json"), "aspose-note-foss/Aspose.Note-FOSS-for-Python")
    facts = read_facts(bundle / "facts.json")
    derived = auditor.rederived_readme("R", bundle, entry, "", (), facts)
    rows = derived.text.splitlines()
    origin = {row.split("|")[1].strip(" `"): derived.origins[n]["source"] for n, row in enumerate(rows) if row.startswith("| `")}
    assert origin["IncorrectDocumentStructureException"] == "renderer"
    # an authored sentence stays authored: only the renderer's own constant is relabelled
    assert origin["Document"] == "authored" and origin["License"] == "authored"
    number = next(n for n, row in enumerate(rows, 1) if "IncorrectDocumentStructureException" in row and "| Declared;" in row)
    result = auditor.derivation("R", derived.text, facts, derived, repository="aspose-note-foss/Aspose.Note-FOSS-for-Python",
                                register=auditor.load_register(), ask={number})
    assert number in result.clearable
    document = next(n for n, row in enumerate(rows, 1) if row.startswith("| `Document`"))
    assert document not in result.clearable  # authored text is never cleared by derivation
