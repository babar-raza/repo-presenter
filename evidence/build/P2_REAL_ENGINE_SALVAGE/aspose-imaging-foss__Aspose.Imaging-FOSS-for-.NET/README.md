# Lane L run — Aspose.Imaging-FOSS-for-.NET

2026-10-22.

```
python scripts/run_lane_l.py aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET (net) -> <clone>
      36 files in tree
[2/5] fetching live README
      306 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      26 facts, 4 example receipts
      example outcomes: {'NOT_VERIFIED': 4}
      CONTRADICTED facts: ['install_command:dotnet']
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 26** — notably low compared with the other 6 repositories (36 files in the real
clone's tree, vs. hundreds for cells/slides/words). Not investigated further or "fixed" —
reported exactly as observed, per scope: this run touched no `src/` code. **Example
receipts: 4, all `NOT_VERIFIED`.** **One `CONTRADICTED` fact: `install_command:dotnet`** —
the only `CONTRADICTED` fact across all 6 repositories that produced output in this batch.
0 correction-engine edits auto-applied.

**Findings (28, report-only)** — all either `format_overclaim` (one per format token on
each of two README lines/blocks: PNG, JPEG, GIF, BMP, WEBP, ICO, TIFF, PSD, EMF, WMF,
DICOM, DJVU, AVIF, HEIC/HEIF — 14 tokens x 2 occurrences each at lines 35-38 and 94-107) or
the single `report_gaps`-free set already counted above. Representative lines, verbatim
from the run (reason text truncated by the script itself at 150 chars, not by this
report):

```
- [format_overclaim] line 94: the README marks 'PNG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; a human reviewer should check whether i
- [format_overclaim] line 95: the README marks 'JPEG' supported, ...
- [format_overclaim] line 96: the README marks 'GIF' supported, ...
- [format_overclaim] line 97: the README marks 'BMP' supported, ...
- [format_overclaim] line 98: the README marks 'WEBP (lossy / lossless / extended)' supported, ...
- [format_overclaim] line 99: the README marks 'ICO' supported, ...
- [format_overclaim] line 100: the README marks 'TIFF' supported, ...
- [format_overclaim] line 101: the README marks 'PSD' supported, ...
- [format_overclaim] line 102: the README marks 'EMF' supported, ...
- [format_overclaim] line 103: the README marks 'WMF (placeable)' supported, ...
- [format_overclaim] line 104: the README marks 'DICOM' supported, ...
- [format_overclaim] line 105: the README marks 'DJVU (single-page / multi-page DJVM)' supported, ...
- [format_overclaim] line 106: the README marks 'AVIF (still / animated)' supported, ...
- [format_overclaim] line 107: the README marks 'HEIC / HEIF' supported, ...
- [format_overclaim] line 35: the README marks 'PNG' supported, ...   (and JPEG/GIF/BMP same line)
- [format_overclaim] line 36: the README marks 'ICO' supported, ...   (and TIFF/WEBP same line)
- [format_overclaim] line 37: the README marks 'PSD' supported, ...  (and EMF/WMF same line)
- [format_overclaim] line 38: the README marks 'DICOM' supported, ... (and DJVU/AVIF/HEIC same line)
```

All 28 findings are the same `format_overclaim` detector firing twice per format name
(once at a prose/table listing around lines 94-107, once at a condensed listing around
lines 35-38) because, per the facts above, 0 SUPPORTED format facts exist for this
repository at all (consistent with the unusually low 26-fact count) — every format named
in the README is flagged for the same reason.

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
