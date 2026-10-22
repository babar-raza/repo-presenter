# Lane L run — Aspose.Email-FOSS-for-.Net

2026-10-22.

```
python scripts/run_lane_l.py aspose-email-foss/Aspose.Email-FOSS-for-.Net net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-email-foss/Aspose.Email-FOSS-for-.Net (net) -> <clone>
      72 files in tree
[2/5] fetching live README
      320 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      230 facts, 4 example receipts
      example outcomes: {'NOT_VERIFIED': 4}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 230.** **Example receipts: 4, all `NOT_VERIFIED`** (net's execution-backed example
verifier is not yet ported). No `CONTRADICTED` facts. 0 correction-engine edits
auto-applied.

**Findings (4, report-only):**

- `format_overclaim` line 34: README marks `CFB` supported, no SUPPORTED format/capability
  fact confirms it is wired up.
- `format_overclaim` line 35: README marks `MSG` supported, same gap.
- `format_overclaim` line 47: README marks `CFB` supported, same gap (second occurrence).
- `format_overclaim` line 48: README marks `MSG` supported, same gap (second occurrence).

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
