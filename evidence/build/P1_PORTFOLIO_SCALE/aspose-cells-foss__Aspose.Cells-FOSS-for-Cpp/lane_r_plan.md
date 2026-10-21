# Lane R document plan — aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp

## Note on this directory's prior state

A prior attempt in this build directory left only a `live_readme.md` file with no `facts.json` or
other evidence alongside it. That file was treated as possibly stale/unverified per instruction
and was re-fetched fresh in this session (new `gh api` reads for both the head commit and the
README blob) rather than trusted. The `source_revision`/`readme_blob_sha` recorded in
`facts.json` are from this session's own fresh fetch, not inherited from the prior file.

## Case classification

Mission §7 case (A): a substantial live README (599 lines), full fixed-core section set, correct
badge order (including an Issues badge, an addition beyond the standard four), correct banner
placement, correct Enterprise Edition naming, and a left-to-right, non-stacked At a Glance
diagram.

## Why this plan converges to the live structure rather than inventing a new one

No C++ compiler or CMake toolchain is available on this machine, so verification here is
code-reading only, per the playbook's explicit allowance for that constraint. This session went
beyond reading only this repository's own source, however: the README's Installation section
makes specific claims about the *published NuGet package's actual contents* (Windows-only
binaries, an MSVC v14x-only `.targets` file, a bundled CMake config) that cannot be verified from
this repository's git history at all -- there is no `.nuspec`, `.targets`, or `lib/` directory
checked into the repository, and no CI/packaging workflow either. This session downloaded the
real, currently-published `aspose.cells.cpp.foss.26.4.1.nupkg` from `api.nuget.org` and inspected
its actual contents directly (archive listing and text extraction only, no code execution from
the package) to verify these claims against the real artifact rather than leaving them
unverifiable. Every one of those specific claims came back confirmed, in some cases down to exact
error-message text.

## What this session found that needed a precise correction

Two genuine, narrow factual inaccuracies in the README's own Scope and Limitations section,
both found by direct source reading:

1. `LoadFormat` declares **two** enum members (`Auto`, `Xlsx`), not "a single `Xlsx` member" as
   claimed -- `SaveFormat` does have exactly one member, so the claim was half-right.
2. The claim "The only `Comment` field in the public API belongs to `DefinedName`" is
   contradicted by `DocumentProperties::GetComments()`/`SetComments()`, a second, independent
   `Comment`-named field (document-level metadata, not a cell note) that a GitHub code search for
   `Comment` under `include/` surfaced immediately.

Both corrections are narrow, in-place edits to the exact sentences at fault -- the surrounding
bullets' substantive claims (no XLS/XLSB/ODS/CSV support, no cell-level comment object, legacy
SpreadsheetML mappers throw, conditional-formatting rule-drop warning) are all independently
confirmed accurate and retained verbatim.

## What a different peer-family observation would have changed, and didn't

No other repository in this batch is from the `aspose-cells-foss` org, so there was no same-family
peer to cross-check against; this repository's facts stand entirely on their own.

## Resulting candidate

`lane_r_candidate.md` is byte-identical to `lane_l_candidate.md` -- two precise, in-place
corrections to the Scope and Limitations section, no other change.
