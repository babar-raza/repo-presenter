"""One-off proof-of-concept for the facts-persistence fix (project/state.yaml's
next_step_fix_2026_10_24 / BUILD_DEFECT_BRIDGE_2026_10_24): backfills `inherited_unit` facts for
ONE repository without a full git clone, using the GitHub Contents/Trees API directly (read-only
fact extraction needs no push-safety, so core/git_safety/clone.py's hardened clone wrapper would
be overkill here -- this script is not a substitute for it elsewhere).

This does not backfill the whole P2_REAL_ENGINE_SALVAGE cohort (30 repositories) -- that remains
a deliberately deferred, separate decision (project/state.yaml). This is the smallest real proof
that the fix in scripts/run_lane_r_render.py actually produces usable `inherited_unit` facts, run
against the one repository this session already has the deepest, hand-verified context on
(aspose-font-foss/Aspose.Font-FOSS-for-Python).

Usage:
    python scripts/backfill_inherited_facts.py <owner>/<repo> <repo_dir> <ecosystem>

Deliberately does NOT overwrite facts.json in place: that file is this repository's own
committed historical evidence record of what the cascade actually used at the time, and
mission non-negotiable #6 ("evidence records come from tooling, never from model narration")
cuts both ways -- backfilling it retroactively would blur "what the cascade actually used" with
"what we added later," for a one-off proof this script does not need to make. Writes a sibling
file, facts.poc_backfill.json, alongside the untouched original.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.facts import read_facts, write_facts
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts

FACTS_ROOT = Path("evidence/build/P2_REAL_ENGINE_SALVAGE")


def _gh_api(path: str) -> object:
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=True, encoding="utf-8"
    )
    return json.loads(result.stdout)


def main() -> None:
    repository, repo_dir, ecosystem = sys.argv[1], sys.argv[2], sys.argv[3]
    facts_path = FACTS_ROOT / repo_dir / "facts.json"

    print(f"[1/4] reading current facts.json ({facts_path})")
    base_document = read_facts(facts_path)
    existing_inherited = sum(1 for f in base_document.facts if f.kind == "inherited_unit")
    print(f"      {len(base_document.facts)} facts, {existing_inherited} already inherited_unit")

    print(f"[2/4] fetching the live default branch head for {repository}")
    repo_info = _gh_api(f"repos/{repository}")
    default_branch = repo_info["default_branch"]
    head = _gh_api(f"repos/{repository}/commits/{default_branch}")
    revision = head["sha"]
    print(f"      {default_branch} @ {revision}")

    print("[3/4] fetching README.md and the file tree")
    readme_meta = _gh_api(f"repos/{repository}/contents/README.md?ref={revision}")
    import base64

    readme_bytes = base64.b64decode(readme_meta["content"])
    tree = _gh_api(f"repos/{repository}/git/trees/{revision}?recursive=1")
    tree_paths = [entry["path"] for entry in tree["tree"] if entry.get("type") == "blob"]
    print(f"      {len(readme_bytes)} README bytes, {len(tree_paths)} tracked files")

    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    out_path = facts_path.with_name("facts.poc_backfill.json")
    print(f"[4/4] computed {len(inherited)} inherited_unit facts; writing {out_path} "
          f"(facts.json itself is left untouched)")

    kept = tuple(f for f in base_document.facts if f.kind != "inherited_unit")
    document = type(base_document)(repository, base_document.source_revision, (*kept, *inherited))
    facts_hash = write_facts(document, out_path)
    print(f"      wrote {out_path} ({facts_hash[:12]}) -- live revision was {revision}, "
          f"facts.json's own source_revision field left as {base_document.source_revision!r} "
          f"(not changed by this script; that field is a separate rigor question, not this "
          f"backfill's concern)")


if __name__ == "__main__":
    main()
