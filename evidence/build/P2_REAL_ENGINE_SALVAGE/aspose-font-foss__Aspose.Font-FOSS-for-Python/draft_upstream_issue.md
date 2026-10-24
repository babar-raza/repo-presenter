<!--
NOT FILED. Per mission section 9: "The first live upstream effect for each new
effect capability requires a target named by the owner and exact available
authorization." This repository's Issues effect path has been exercised and
owner-authorized once this session (aspose-3d-foss/Aspose.3D-FOSS-for-Python#4);
this specific filing has not. This file is the complete, evidence-backed
proposal only -- filing it as a real GitHub issue requires an explicit owner
go-ahead.

Provenance: found by this repository's own independent reviewer
(readme/review/independent_reviewer.py, built 2026-10-24) during its first real
pass against the P2_REAL_ENGINE_SALVAGE cascade cohort
(project/state.yaml: RUN_INDEPENDENT_REVIEW_P2_COHORT_2026_10_24). Traced to
root cause via README.patch.diff before drafting this: the broken line is
inherited verbatim from the live upstream README, not introduced by this
project's own authoring/rendering pipeline.
-->

**Target repository:** `aspose-font-foss/Aspose.Font-FOSS-for-Python`
**Target revision:** `0735cc2797665a21ccf96409289c7d4f2da054d9` (current `main` as of 2026-10-24)

## Proposed title

The MCP Server install command in the README names a package that is not published --
`pip install "aspose-font[mcp]"` should be `pip install "aspose-font-foss[mcp]"`

## Proposed body

The "## MCP Server" section's install example:

```bash
pip install "aspose-font[mcp]"
python -m aspose_font.mcp
```

names the distribution `aspose-font`. The package this repository actually publishes (declared
in `pyproject.toml`'s own `name` field) is `aspose-font-foss`. No package named plain
`aspose-font` is published by this project, so this exact command, copy-pasted as written, asks
pip for the wrong distribution.

### Repro

Reading `pyproject.toml` at the pinned revision directly shows:

```toml
[project]
name = "aspose-font-foss"
```

while the README's own MCP Server section (line 568 as of the pinned revision) reads:

```bash
pip install "aspose-font[mcp]"
```

The `python -m aspose_font.mcp` line on the next line is correct as written (the installed
*module* is `aspose_font`, independent of the *distribution* name) -- only the `pip install`
target is wrong.

### Impact on the published README

A reader following this section's own instructions verbatim gets a pip resolution failure (or,
worse, installs an unrelated same-named package if one ever appears on PyPI) rather than this
project's own MCP server support.

### Suggested fix shape (not a patch; for triage only)

Change `pip install "aspose-font[mcp]"` to `pip install "aspose-font-foss[mcp]"` in the MCP
Server section. No other install example in the README repeats this mistake (the main
Installation section correctly uses `aspose-font-foss` throughout).

## Dedup check performed

Run 2026-10-24: `gh issue list --repo aspose-font-foss/Aspose.Font-FOSS-for-Python --state all`
returns **0 issues total** (open or closed) -- the repository currently has no issues at all, so
this cannot be a duplicate. `--search "mcp"` independently confirms `[]`.
