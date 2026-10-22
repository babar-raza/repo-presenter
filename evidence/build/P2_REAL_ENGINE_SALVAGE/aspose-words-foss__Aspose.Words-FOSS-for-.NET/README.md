# Lane L run — Aspose.Words-FOSS-for-.NET

2026-10-22.

```
python scripts/run_lane_l.py aspose-words-foss/Aspose.Words-FOSS-for-.NET net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-words-foss/Aspose.Words-FOSS-for-.NET (net) -> <clone>
      8262 files in tree
[2/5] fetching live README
      961 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      6643 facts, 5 example receipts
      example outcomes: {'NOT_VERIFIED': 5}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 6643** — the largest fact count of all 7 repositories in this batch, consistent
with it being by far the largest tree (8262 files). **Example receipts: 5, all
`NOT_VERIFIED`** (net's execution-backed example verifier is not yet ported). No
`CONTRADICTED` facts. 0 correction-engine edits auto-applied.

**Findings (20, report-only):**

- `enterprise_edition_naming` line 85: names the aspose.com product with a substitute for
  its proper name ("the commercial [Aspose.Words for .NET](https://products.aspose.com/words/net/)").
- `enterprise_edition_naming` line 95: possible violation ("commercial product").
- `enterprise_edition_naming` line 150: same pattern ("the commercial Aspose.Words for
  .NET").
- `enterprise_edition_naming` line 915: same pattern, different link
  (`https://products.aspose.com/words/net/`).
- `enterprise_edition_naming` line 944: same pattern, different link
  (`https://docs.aspose.com/words/net/`).
- `format_overclaim` line 80: README marks `DOCX / DOCM / DOTX / DOTM` supported, no
  SUPPORTED format/capability fact confirms wiring.
- `format_overclaim` line 81: README marks `Flat OPC (all variants)` supported, same gap.
- `format_overclaim` line 82: README marks `Markdown` supported, same gap.
- `format_overclaim` line 83: README marks `Plain text` supported, same gap.
- `format_overclaim` lines 13, 35 (x5 each): README marks `DOCX`, `DOCM`, `DOTX`, `DOTM`,
  `OPC` supported individually, same gap, repeated at two listing locations.
- `report_gaps` line 0: 3 of 618 verified public types named nowhere in the README
  (would fill API Reference — `public_symbol:aspose.words.inodecollection`, and 2 more;
  script's own printed list truncated at 150 chars).

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
