"""Run the real, salvaged Lane L pipeline end-to-end against one real repository.

Usage:
    python scripts/run_lane_l.py <owner>/<repo> <ecosystem> [clone_path]

``<ecosystem>`` is one of: python, net, java, cpp, go, rust, typescript, nodejs --
whichever ``extractors/platforms/<ecosystem>.py`` names (``registry.plugin_for``
discovers it by module name, same as the production code).

Wires: the ported platform extractor -> the shared fact model (core/facts.py) -> the
Lane L correction engine (readme/correction/). No agent reasoning anywhere in this
path -- every fact and every edit is produced by the ported code itself, independently
re-run after every change per this repo's own AGENTS.md discipline (never trust a
worker's or an agent's self-report).

This is deliberately NOT the old repo's full ``extract_facts`` orchestrator (468 lines,
pulling in ~10 more modules: license/asset/link/registry-lag facts, the full README
content-unit inventory). Per mission section 3 ("pull only small dependency-closed
components"), this script wires only what Lane L's ported detectors actually read:
manifest facts, surface facts, registry facts, format facts, and example facts. A
richer orchestrator is future work if Lane R's content-unit-preservation proof needs it.

The one honest gap this script surfaces rather than hides: a plugin's
``verify_examples()`` may still be a NOT_VERIFIED stub for ecosystems whose
``<ecosystem>_examples.py`` has not been ported yet (as of 2026-10-22: python is real;
net/java/cpp/go/rust/typescript/nodejs's execution-backed verifiers have not been
individually proven through this script) -- this script reports the real outcome
counts and does not pretend a stub result is more verified than it is.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import ExampleCandidate, collapse_blank_runs
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id
from repo_presenter.core.registry_entry_stub import RegistryEntryStub
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.correction.engine import correct
from repo_presenter.readme.correction.model import Context
from repo_presenter.readme.evidence.facts.examples import example_facts
from repo_presenter.readme.evidence.facts.formats import format_facts

_FENCE = re.compile(
    r"^```(?P<lang>\S*)\n(?P<body>.*?)\n```", re.MULTILINE | re.DOTALL
)


def select_examples(
    readme_text: str, source_path: str, ecosystem: str
) -> list[ExampleCandidate]:
    """Minimal fence extractor: every fenced block in ``ecosystem``'s own fence languages
    (``core.ecosystems.spec_for(ecosystem).example_fences`` -- the same vocabulary the real
    extractors key on), once each by normalized body.

    Deliberately simpler than the old repo's ``selection.py`` (which depends on the full
    README content-unit inventory, ``evidence/facts/inherited.py`` -- not yet ported). This
    is sufficient for Lane L's ``failing_example``/``format_overclaim`` detectors, which only
    read ``example``/``format`` facts, not content-unit IDs.
    """
    aliases = spec_for(ecosystem).example_fences
    candidates: list[ExampleCandidate] = []
    seen: set[str] = set()
    ordinal = 0
    for match in _FENCE.finditer(readme_text):
        lang = match.group("lang").lower()
        if lang not in aliases:
            continue
        body = match.group("body") + "\n"
        normalized = "\n".join(line.rstrip() for line in body.splitlines() if line.strip())
        if not normalized.strip() or normalized in seen:
            continue
        seen.add(normalized)
        ordinal += 1
        start_line = readme_text[: match.start()].count("\n") + 1
        end_line = start_line + body.count("\n") + 1
        candidates.append(
            ExampleCandidate(
                ordinal=ordinal,
                language=lang,
                code=collapse_blank_runs(body),
                source_path=source_path,
                start_line=start_line,
                end_line=end_line,
                unit_id=f"inherited_unit:{ordinal:03d}.code_block",
            )
        )
    return candidates


def tree_paths_of(root: Path) -> list[str]:
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def fetch_live_readme(repository: str) -> bytes:
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/readme", "--jq", ".content"],
        capture_output=True,
        text=True,
        check=True,
    )
    return base64.b64decode(result.stdout.strip())


def clone(repository: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", f"https://github.com/{repository}.git", str(dest)],
        check=True,
        capture_output=True,
    )


def build_facts(
    repository: str, root: Path, tree_paths: list[str], readme_text: str, ecosystem: str
) -> tuple[FactsDocument, list]:
    plugin = plugin_for(ecosystem)
    manifest = plugin.detect_manifest(root)
    identity = Fact(
        fact_id("identity", "repository"),
        "identity",
        repository,
        (Evidence("data/registry.json", "admitted registry entry"),),
    )
    facts: list[Fact] = [identity]
    if manifest is not None:
        manifest_facts = plugin.manifest_facts(root, manifest, tree_paths)
        registry_resolved, _probes = plugin.registry_facts([identity, *manifest_facts])
        resolved_by_id = {f.id: f for f in registry_resolved}
        facts.extend(resolved_by_id.get(f.id, f) for f in manifest_facts)
    facts.extend(plugin.surface_facts(root, tree_paths))

    candidates = select_examples(readme_text, "README.md", ecosystem)
    workspace = Path(tempfile.mkdtemp(prefix="rp_examples_"))
    receipts = plugin.verify_examples(root, tree_paths, candidates, workspace)
    facts.extend(example_facts(candidates, receipts, "receipts.json"))
    facts.extend(
        format_facts(
            candidates,
            receipts,
            plugin.format_claims,
            "receipts.json",
            plugin.format_declarations(root, tree_paths),
        )
    )
    return FactsDocument(repository=repository, source_revision="HEAD", facts=tuple(facts)), receipts


def main() -> None:
    if len(sys.argv) < 3:
        print(f"usage: python {sys.argv[0]} <owner>/<repo> <ecosystem> [clone_path]")
        print("  ecosystem: python, net, java, cpp, go, rust, typescript, nodejs")
        sys.exit(2)
    repository = sys.argv[1]
    ecosystem = sys.argv[2]
    clone_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(tempfile.mkdtemp(prefix="rp_clone_"))

    print(f"[1/5] cloning {repository} ({ecosystem}) -> {clone_path}")
    if not clone_path.exists() or not any(clone_path.iterdir()):
        clone_path.mkdir(parents=True, exist_ok=True)
        clone(repository, clone_path)
    tree_paths = tree_paths_of(clone_path)
    print(f"      {len(tree_paths)} files in tree")

    print("[2/5] fetching live README")
    readme_bytes = fetch_live_readme(repository)
    readme_text = readme_bytes.decode("utf-8", errors="replace")
    print(f"      {len(readme_text.splitlines())} lines")

    print("[3/5] building facts (manifest + surface + registry + examples + formats)")
    document, receipts = build_facts(repository, clone_path, tree_paths, readme_text, ecosystem)
    print(f"      {len(document.facts)} facts, {len(receipts)} example receipts")
    outcome_counts: dict[str, int] = {}
    for r in receipts:
        outcome_counts[r.outcome] = outcome_counts.get(r.outcome, 0) + 1
    print(f"      example outcomes: {outcome_counts}")
    contradicted = [f for f in document.facts if f.polarity == "CONTRADICTED"]
    print(f"      CONTRADICTED facts: {[f.id for f in contradicted]}")

    print("[4/5] running the real Lane L correction engine")
    entry = RegistryEntryStub(repository=repository)
    ctx = Context(entry=entry, facts=document, readme=readme_text, tree_paths=tuple(tree_paths))
    result = correct(ctx)
    print(f"      {len(result.edits)} edits applied")
    for edit in result.edits:
        print(f"        - {edit.kind} at {edit.start}-{edit.end}: {edit.rationale[:100]}")

    print("[5/5] findings (report-only, no auto-edit)")
    _, findings = None, []
    from repo_presenter.readme.correction.engine import collect

    _, findings = collect(ctx)
    for finding in findings:
        print(f"      - [{finding.detector}] line {finding.line}: {finding.reason[:150]}")
    if not findings:
        print("      (none)")

    out_dir = Path("scripts") / "_lane_l_output" / repository.replace("/", "__")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "facts.json").write_text(document.to_json(), encoding="utf-8")
    (out_dir / "corrected.md").write_text(result.corrected, encoding="utf-8")
    print(f"\nWrote {out_dir / 'facts.json'} and {out_dir / 'corrected.md'}")


if __name__ == "__main__":
    main()
