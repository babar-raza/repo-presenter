# Lane R document plan -- aspose-words-foss/Aspose.Words-FOSS-for-.NET

## Case classification

Case (A): a substantial, high-quality live README. At this revision the README is
962 lines, already carries the project's fixed-core section set (At a Glance,
Navigation, What it can do, Supported formats, Getting started, Dependencies, A
quick example, Additional examples, API Reference, What's not included, Development
and Testing, The story behind this code, Documentation & Resources, Enjoying it/
Contributing/License), a left-to-right At a Glance mermaid diagram, correct badge
placement, and a "What's not included (and where to get it)" section that is
unusually candid for an upstream README -- it names the exact commercial subsystems
removed (page layout/rendering, additional formats, mail merge/LINQ reporting/
comparison/signing/font-subsetting) rather than glossing over them. It is not case
(B): nothing here is thin, missing, or incredible as a baseline.

## Why Lane R converges to Lane L here

Verification against source (facts.json) found the README's substantive engineering
claims to be almost entirely accurate: the Supported Formats table is an exact,
verified 1:1 match to the real dispatch code in both directions (ReaderFactory.cs
for load, WriterFactory.cs for save -- F-FORMATS-LOAD, F-FORMATS-SAVE); the
Dependencies section's package list, versions, and per-target-framework scoping
exactly matches the real csproj PackageReference conditions (F-DEPS-MATCH-CSPROJ);
the single-assembly/shared-namespace/three-target packaging claims all check out
against the csproj and nuspec (F-ASSEMBLY-SINGLE, F-NAMESPACE, F-TARGETS); the
field-evaluation caveat about page numbers "evaluating to 0" is literally what the
FieldNumPages implementation does, marked with its own "// FOSS" comment
(F-FIELD-NUMPAGES-ZERO); and the signature-handling claims (verify/inspect/remove
work, creating new signatures does not) match the DigitalSignatureUtil dispatch
precisely, including the detail that signing is disabled across every format branch,
not just DOCX (F-SIGN-CREATE-DISABLED, F-SIGN-VERIFY-REMOVE-WORK). The two Quick
Start / Additional Examples API calls spot-checked (`Document.AppendDocument`,
`Document.AcceptAllRevisions`) both exist with real, non-stub implementations.

Exactly one verifiable defect was found in the README's own prose: a count
self-inconsistency (615 public types in the API Reference section's own closing
sentence vs. 617 public types in the separate Documentation & Resources section,
independently resolved to 615 by directly recounting the README's own table rows --
F-APITYPE-COUNT-SELFCONSISTENCY). That is a one-number fix, not a structural or
tonal problem, and does not call the surrounding section's organization or voice
into question anywhere else.

Given a live document that is this close to independently verified ground truth,
the correct Lane R output is the same document, in its own voice and structure, with
only that one number corrected -- not a differently organized document manufactured
to prove Lane R can generate something different. Rebuilding this README from a
generic shell would discard a baseline that mostly held up to verification, which
this project's own rules treat as a mission violation in its own right, not a
stronger result.

## The one thing Lane R does NOT fold into the README

Verification also surfaced a real upstream packaging defect: the published
`Aspose.Words.FOSS` nuspec's dependency groups for `.NETStandard2.0` and `net8.0`
omit `System.Text.Encoding.CodePages` as a dependency, even though the shipped
assembly for those targets is built against it and calls into it unconditionally
the first time `Document`'s static constructor runs -- which is the very first line
of the README's own Quick Start example (F-NUSPEC-CODEPAGES-GAP in facts.json). This
is not a false sentence in the README (the Dependencies section's own prose is
accurate per F-DEPS-MATCH-CSPROJ) -- it is a defect in the separately-published
package metadata. Per this project's rule that upstream defect reporting is a
separate effect path from README changes, this is reported only via
`draft_upstream_issue.md` and intentionally left out of both Lane L and Lane R
candidates.

## Resulting candidate

`lane_r_candidate.md` is byte-identical to `lane_l_candidate.md`: both lanes,
applied independently to the same verified facts, correctly converge on the live
README's own structure and voice with the single 617->615 correction applied.
