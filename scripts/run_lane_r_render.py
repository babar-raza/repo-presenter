"""Render the REAL, fully composed Lane R README from the real S3-S6 artifacts, no LLM call.

Usage:
    python scripts/run_lane_r_render.py <owner>/<repo> <ecosystem> <clone_path>

Wires the real, accepted plan.json (S5), content_units.json (S6), and dispositions.json (S4)
through readme/composition/renderer.py's render_readme() -- deterministic code, the first time
this repository has rendered a complete candidate README from a real S3-S6 cascade rather than
a hand-built stand-in packet.

Requires run_lane_r_investigation.py, run_lane_r_reconciliation.py, run_lane_r_planning.py, and
run_lane_r_authoring_real.py to have been run first for the same repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import render_patch, render_readme
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts


def _tree_paths(root: Path) -> list[str]:
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def main() -> None:
    repository, ecosystem, clone_path_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    clone_path = Path(clone_path_arg)
    repo_dir = repository.replace("/", "__")
    plugin_for(ecosystem)  # see run_lane_r_planning.py's own comment on this exact real bug
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    out_dir = Path("scripts/_lane_r_output") / repo_dir

    print(f"[1/3] reading the real S3-S6 artifacts from {out_dir}")
    base_document = read_facts(facts_path)
    dispositions = json.loads((out_dir / "dispositions.json").read_text(encoding="utf-8"))
    plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
    units = json.loads((out_dir / "content_units.json").read_text(encoding="utf-8"))
    print(f"      {len(dispositions['dispositions'])} dispositions, {len(units['units'])} units")

    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    document = FactsDocument(repository, base_document.source_revision, (*base_document.facts, *inherited))

    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)

    print("[2/3] rendering (deterministic code, no LLM call)")
    rendered = render_readme(entry, document, plan, units, dispositions)
    print(f"      {len(rendered)} characters, {rendered.count(chr(10)) + 1} lines")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.rendered.md").write_text(rendered, encoding="utf-8", newline="\n")
    print(f"[3/3] wrote {out_dir / 'README.rendered.md'}")

    original = readme_bytes.decode("utf-8", errors="replace")
    patch = render_patch(original, rendered)
    (out_dir / "README.patch.diff").write_text(patch, encoding="utf-8", newline="\n")
    print(f"      wrote {out_dir / 'README.patch.diff'} ({len(patch.splitlines())} diff lines)")


if __name__ == "__main__":
    main()
