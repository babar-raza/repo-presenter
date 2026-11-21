"""BL-600/BL-602 zero-call proof on the stored seals of the four clean controls the round-4 audit still flagged.

For Email C++ (API rows 126-137), OCR .NET (capability bullets 50, 51, Enterprise line 261), PSD Java (capability
bullets 47-50) and Page Python (opening, line 7): re-render the stored seal (it must equal the stored README byte for
byte), feed each faulted line to the BL-240 degrade exactly as ``cascade._degrade_settled`` does with a blocking model
finding, re-render, run every blocking validator, and ask the audit's own derivation whether each replaced line is
derivable and clearable. A fabricated authored line (negative control) must stay not derivable and be withheld when
flagged. No provider call. Needs ``git fetch origin '+refs/repository-presenter-state/*:refs/repository-presenter-state/*'``.

    PYTHONPATH=src python scripts/measure_bl600_authored_flags.py [--workdir DIR] [email ocr page psdj]
"""

from __future__ import annotations

import argparse
import copy
import importlib
import json
import subprocess
import tempfile
from pathlib import Path

for _plugin in ("go", "java", "rust", "typescript", "cpp", "nodejs", "net", "python"):
    importlib.import_module("repo_presenter.extractors.platforms." + _plugin)

from repo_presenter import recertify as rc  # noqa: E402
from repo_presenter.core.registry.loader import load_registry  # noqa: E402
from repo_presenter.core.state import bundle_store as bs  # noqa: E402
from repo_presenter.readme.review.derivation import lane_r_derivation  # noqa: E402
from repo_presenter.readme.validation import must_correct as mc  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CELLS = {
    "email": ("aspose-email-foss/Aspose.Email-FOSS-for-Cpp", list(range(126, 138)),
              ("type:public_symbol:aspose.email.foss.msg.mapi_message",
               "mapi_message class encrypts every attachment with AES-256 before it is stored.")),
    "ocr": ("aspose-ocr-foss/Aspose.OCR-FOSS-for-.NET", [50, 51, 261], ("capability:5", "It targets net11.0 and net12.0.")),
    "page": ("aspose-page-foss/Aspose.Page-FOSS-for-Python", [7],
             ("opening", "Aspose.Page FOSS for Python encrypts PDF files with AES-256 and uploads them to the cloud.")),
    "psdj": ("aspose-psd-foss/Aspose.PSD-FOSS-for-Java", [47, 48, 49, 50],
             ("capability:3", "It converts PSD files to PNG on the GPU at 120 frames per second.")),
}


def _seal(repository: str, scratch: Path):
    git_dir = REPO / ".git"
    refs = subprocess.check_output(
        ["git", "-C", str(REPO), "for-each-ref", "--format=%(refname) %(objectname)",
         "refs/repository-presenter-state/bundles/"], text=True)
    for line in refs.splitlines():
        ref, commit = line.split()
        if bs.parse_bundle_ref(ref) == (repository, "R"):
            record = bs._read_seal(git_dir, commit, repository, "R", scratch / bs._slug(repository))
            return Path(record.bundle), record.revision
    raise SystemExit(f"no Lane R bundle ref for {repository}")


class Cell:
    def __init__(self, repository: str, workdir: Path):
        self.repository = repository
        self.bundle, self.revision = _seal(repository, workdir / "seals")
        self.entry = {e.repository: e for e in load_registry(REPO / "data/registry.json").entries}[repository]
        self.source = rc.fetch_source(repository, self.revision, workdir / "src")
        self.doc = rc._bundle_facts(self.bundle, self.entry, self.source)
        sealed_disp, sealed_plan = rc._load_json(self.bundle, "dispositions.json"), rc._load_json(self.bundle, "plan.json")
        disp = rc.current_dispositions(sealed_disp, self.doc, sealed_plan)
        plan = rc.current_plan(sealed_plan, self.doc, disp)
        name = "content_units.coherent.json" if (self.bundle / "content_units.coherent.json").is_file() else "content_units.json"
        units = rc.current_units(rc._load_json(self.bundle, name), self.doc)
        inv = rc._load_json(self.bundle, "investigation.json") if (self.bundle / "investigation.json").is_file() else {}
        plan, units = mc.corrected_authored(plan, units, self.doc, inv, disp)
        self.disp = rc.settled_dispositions(self.entry, self.doc, plan, units, disp)
        self.plan, self.units = plan, units

    def evaluate(self, plan, units, disp):
        failing, details, art = rc._evaluate_lane_r(self.bundle, self.entry, self.source, disp, units, plan_override=plan)
        return art["README.md"].decode(), failing, details

    def derive(self, readme, plan, units, disp, lines):
        return lane_r_derivation(readme, entry=self.entry, facts=self.doc, plan=plan, units=units,
                                 dispositions=disp, ask=lines)


def _degrade(cell: Cell, plan, units, disp, readme: str, lines: list[int]):
    rows = readme.splitlines()
    flags = [mc.ClaimFlag(rows[n - 1].strip(), "review unsupported_claim", "REVIEW:llm") for n in lines]
    return mc.degrade_claims(plan, units, disp, flags, cell.doc, readme=readme)


def run(key: str, workdir: Path) -> None:
    repository, lines, (slot, fake) = CELLS[key]
    cell = Cell(repository, workdir)
    base, failing, _ = cell.evaluate(cell.plan, cell.units, cell.disp)
    print(f"== {key}: re-render equals the stored README: {base == (cell.bundle / 'README.md').read_text()}; failing {failing}")
    plan, units, disp, records = _degrade(cell, cell.plan, cell.units, cell.disp, base, lines)
    after, failing, details = cell.evaluate(plan, units, disp)
    print("   degrade records:", sorted({(r.get('action'), r.get('rule')) for r in records}))
    print("   validators after:", failing or "clean", details[:2])
    changed = [i + 1 for i, row in enumerate(after.splitlines()) if row not in set(base.splitlines())]
    derived = cell.derive(after, plan, units, disp, changed)
    for n in changed:
        print(f"   line {n}: derivable={n in derived.derivable} clearable={n in derived.clearable}")
    # negative control: a fabricated authored line is not derivable, and the same lever withholds it when flagged
    fake_units = copy.deepcopy(cell.units)
    for unit in fake_units["units"]:
        if unit["slot"] == slot:
            unit["text"] = fake
    text, _, _ = cell.evaluate(cell.plan, fake_units, cell.disp)
    line = next(i + 1 for i, row in enumerate(text.splitlines()) if fake[:30] in row)
    fd = cell.derive(text, cell.plan, fake_units, cell.disp, [line])
    p2, u2, d2, recs = _degrade(cell, cell.plan, fake_units, cell.disp, text, [line])
    out, bad, _ = cell.evaluate(p2, u2, d2)
    print(f"   negative control line {line}: derivable={line in fd.derivable} clearable={line in fd.clearable}; "
          f"degrade {[r['action'] for r in recs]}; still printed={fake[:30] in out}; validators {bad or 'clean'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cells", nargs="*", default=list(CELLS))
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bl600-") as tmp:
        for key in args.cells:
            run(key, args.workdir or Path(tmp))


if __name__ == "__main__":
    main()
