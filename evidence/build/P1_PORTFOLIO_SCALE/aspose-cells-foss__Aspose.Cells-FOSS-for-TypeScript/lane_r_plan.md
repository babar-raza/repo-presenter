# Lane R document plan — aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript

## Case classification

Mission §7 case (A): substantial live README as structural/content baseline. The
live README (343 lines) already matches the fixed-core section set exactly
(Navigation, At a Glance, Key Capabilities, Installation, Dependencies, Quick Start,
Additional Examples, API Reference, Documentation & Resources, Scope and
Limitations, Development and Testing, License), uses the correct badge order and
banner placement, correct Enterprise Edition naming in its one cross-link, and a
left-to-right, non-stacked At a Glance diagram (Starting Points -> Core
Capabilities -> Outputs). It is not deficient or missing (case B).

## Why this plan converges to the live structure

This repository's own facts.json found exactly one CONTRADICTED claim this
session (F-SAVE-HTML-IS-FRAMESET-NOT-SINGLE-DOC): the "Export a Workbook to HTML"
example and the Scope and Limitations section were both silent about `save()`'s
HTML output actually being a multi-file Excel frameset, not the single document a
reader would expect. Every other independently re-derived claim — the dependency
versions, the HTML auto-detect-on-load behavior, `toHtml()`'s genuinely
single-string output, the Cell/Worksheet method signatures, the MIT license, and
the "no npm package published yet" claim (cross-checked against the live npm
registry) — held up against direct source reading. Per docs/MISSION_AUTHORITY.md
("each live README owns its own tone, prose structure, and heading skeleton; these
are never replaced by a template" and "only what a verified fact or standing
constraint forces is corrected"), a Lane R reconstruction of this repository
correctly reproduces the live document's own structure and voice with only that one
fact-forced correction — not a differently organized document invented to prove
Lane R can generate from scratch.

## Verification-depth caveat specific to this repository

Node.js/npm/tsx are not available in this environment (playbook-confirmed), so
every fact here (including the frameset finding) was derived by reading the actual
TypeScript source, not by running it. This is a narrower verification depth than
the Python/.NET repositories in this portfolio batch, where execution was possible.
The frameset finding is nonetheless a deterministic code-reading result — `save()`'s
branch for `SaveFormat.HTML` unconditionally calls `saveAsHtmlFrameset()`, which
unconditionally writes the seven files enumerated in facts.json — not an inference
from incomplete information.

## Resulting candidate

`lane_r_candidate.md` is byte-identical to `lane_l_candidate.md`: both lanes,
applied independently to the same verified facts and the same live-structure-as-
reference rule, converge on the same corrected document given how close the live
README already was to the verified truth.
