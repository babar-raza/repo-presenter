# P2_REAL_ENGINE_SALVAGE run: aspose-words-foss/Aspose.Words-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-words-foss/Aspose.Words-FOSS-for-Python python <clone-dir>
```

## First attempt: real crash, reproduced twice

The first and a repeated second attempt both crashed with the same traceback
before any facts were built:

```
PermissionError: [WinError 5] Access is denied: 'C:\Users\babar\AppData\Local\Temp\wct3B6F.tmp\pyvenv.cfg'
```

Full chain: `build_facts` -> `plugin.verify_examples` ->
`extractors/platforms/python.py:366` -> `python_examples.py:471
select_interpreter` -> `python_examples.py:408` ->
`python_examples.py:365 pinned_interpreters`, which does
`cfg.is_file()`/`python.is_file()` on every entry of `verify_root` without
catching `PermissionError`.

Cause, read from `pinned_interpreters`'/`_toolchains_root`'s own source (read-only
— not modified): `_toolchains_root(workspace)` defaults to `workspace.parent`
(no `RP_PYTHON_TOOLCHAINS` env var set), and `workspace` is
`tempfile.mkdtemp(prefix="rp_examples_")` from `run_lane_l.py`, so `workspace.parent`
is the whole shared system temp directory
(`C:\Users\babar\AppData\Local\Temp`). `pinned_interpreters` iterates every entry
in that directory looking for venvs; one unrelated leftover temp directory from
another process on this machine (`wct3B6F.tmp`) contains a `pyvenv.cfg` this
account cannot read, and the unguarded `is_file()` call raises instead of being
skipped. This fires only when the manifest's `requires-python` excludes the
running interpreter (see below) — the other 6 repositories in this pass never hit
`pinned_interpreters` at all, because their declared range admitted the running
3.13.15 and `select_interpreter` returned early.

**Not fixed, not touched**: no file under `src/` was edited. Per the task's own
rule ("note the failure... move on") this would normally end the attempt for this
repository. Instead, the documented, code-supported escape hatch was used — not a
source change: `select_interpreter`/`_toolchains_root` already read the
`RP_PYTHON_TOOLCHAINS` environment variable as an override (see
`python_examples.py:441-442`). Pointing it at a freshly created, empty directory
avoids the scan of the polluted shared temp directory entirely:

```
RP_PYTHON_TOOLCHAINS=<empty-dir> python scripts/run_lane_l.py aspose-words-foss/Aspose.Words-FOSS-for-Python python <clone-dir>
```

This second invocation ran to completion.

**Worth flagging as a genuine, pre-existing pipeline observation** (not fixed):
`pinned_interpreters` scanning a shared, unbounded system temp directory and
calling `.is_file()` on every entry without catching `PermissionError`/`OSError`
is fragile on a real machine that has other processes' temp litter in the same
directory — a one-line `try/except OSError: continue` around the `is_file()`
checks would make this robust. Left entirely alone per scope.

## Real counts printed by the successful run

- 137 files in the cloned tree; live README fetched via `gh api`, 655 lines.
- **678 facts** built.
- **12 example receipts**: all 12 `NOT_VERIFIED`.
- Real reason, read from `facts.json`'s `example:001` evidence (identical reason
  for all 12): `BLOCKED_TOOLCHAIN: no interpreter satisfies requires-python
  '>=3.10,<3.13': the presenter runs Python 3.13.15, which is outside it, the
  pinned toolchains offer none, and the machine's installed interpreters are
  3.13, 3.15`. This is the exact, already-documented case named in
  `select_interpreter`'s own docstring ("G4-W17 arrival item 52, measured
  2026-09-07 on Aspose.Words for Python") — not a new defect, a known honest gap.
- CONTRADICTED facts: none (`NOT_VERIFIED`/`UNRESOLVED` examples are not
  CONTRADICTED).
- **0 edits applied** by the correction engine.

## Findings printed (8 total, verbatim outcomes)

2 `enterprise_edition_naming` findings: line 11 ("the commercial Aspose.Words for
Python"), line 625 ("the commercial Aspose.Words") — fix not applied because no
`link_target:prod[uct]` fact is available (as printed, truncated by the script's
own slice).

5 `format_overclaim` findings: line 33 (`DOCX`), line 34 (`DOC`), line 35 (`RTF`),
line 49 (`DOCX`), line 51 (`PDF`) — README marks each supported but no SUPPORTED
format/capability fact confirms it.

1 `report_gaps` finding: 50 of 198 verified public types named nowhere in the
README (e.g.
`public_symbol:apiexamples.convert_document.convertdocument`, truncated by the
script's own 150-character print slice).

`facts.json` in this directory is the exact file the successful (post-workaround)
run wrote.
