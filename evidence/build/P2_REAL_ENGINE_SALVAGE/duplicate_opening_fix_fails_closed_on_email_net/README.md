# A new, real consequence of the duplicate-opening fix: S6 fails closed on aspose-email-foss/.NET

2026-10-22. While firing a twelfth Lane R cascade against
`aspose-email-foss/Aspose.Email-FOSS-for-.Net`, S6 authoring's `run_job` call for the "opening"
task raised `JobError: section_authoring: output rejected twice`. This is the first time the
duplicate-opening-paragraph fix (`CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`) has caused a hard
failure rather than either (a) passing silently (most cascades) or (b) a reject→accept/reject→
unchanged cycle that still completed (the two targeted rechecks, and this session's eleventh
cascade). This is a real, new observation about the fix's behavior under live conditions, not a
bug in the check: reporting it precisely, not hiding it.

## What happened, in order

1. S4 reconciliation disposed `inherited_unit:004.paragraph` -- the live README's own rich,
   comprehensive opening paragraph (names `.msg`/CFB/EML formats, "no required third-party
   package dependencies," "no Microsoft Outlook installation," and the services/desktop/CLI use
   case) -- `VERIFIED_PRESERVE` into `opening`.
2. S6's first attempt at the freshly authored `opening` unit cited `inherited_unit:004.paragraph`
   itself among its `fact_ids` and produced text that paraphrases that paragraph almost
   sentence-for-sentence (see `attempt_1_rejected.json`). The new check correctly rejected it,
   quoting the exact restated clauses ("the product's identity, license, or
   dependency-freedom").
3. The re-ask's second attempt (`attempt_2_rejected.json`) dropped every other fact (`identity:
   repository`, `package:name`, `package:target_framework`, `package:version`,
   `dependency:none`, `public_symbol:aspose.email.foss` -- all explicitly omitted with reasons)
   and kept only a compressed restatement of the exact same reading/writing claims the preserved
   paragraph already makes, still citing only `inherited_unit:004.paragraph`. The check correctly
   rejected this too -- it is still a restatement, just a shorter one.
4. `recover_opening_duplicates_preserved`'s own `coverage.uncovered()` call found no sentence of
   this second attempt that the preserved paragraph does not already state at the required 70%
   stem-overlap threshold -- there is nothing genuinely new to keep -- so recovery correctly
   returned `None` rather than fabricate replacement text, and the job failed closed exactly as
   it would with no `recover` at all.

## Why this is not a false positive

The model was never actually citation-starved in a way that made a non-redundant "opening" unit
impossible in principle -- `investigation.json`'s own uncertainties name real, more specific
facts (`CfbWriter`, `SetProperty()`, EML MIME-variant support) the model could have used instead
of restating the preserved paragraph's own claims. It chose, twice, to lean on the one fact
(`inherited_unit:004.paragraph`) that is guaranteed to be "safe" (verbatim-supported) rather than
reach for the more specific, genuinely differentiating facts available to it. The check is
behaving exactly as designed: it does not know how to write better prose, it only knows how to
refuse prose that restates what the renderer already prints verbatim beside it.

## The honest conclusion

This is a real, previously unobserved consequence of a correct, narrowly-scoped fix: for a
repository whose README's own preserved paragraph is unusually comprehensive, the fix can turn a
previously silent, undetected duplicate into a hard pipeline failure that halts the cascade and
needs a human or a smarter retry strategy (e.g. a `recover` that explicitly steers the re-ask
toward the dossier's own more specific facts, not implemented here) to resolve. That is the
correct trade-off given this project's own non-negotiables (no silent overruling of a negative
finding; report observations, not claims of progress) -- a halted cascade that surfaces a real
problem is strictly better than a completed one that silently ships a duplicate. This cascade
(aspose-email-foss/Aspose.Email-FOSS-for-.Net) is left incomplete, not forced through with a
workaround; the twelfth full cascade this session fires against a different repository instead.

## Second confirmed instance: aspose-page-foss/Aspose.Page-FOSS-for-Python

The identical pattern recurred while attempting a fourteenth-cascade repository. The live
README's preserved paragraph states: "is a free, open-source, MIT-licensed, pure-Python library
for working with PostScript, Encapsulated PostScript (EPS), and XPS documents. It reads and
authors PS/EPS and XPS content directly, builds page content programmatically through its own
render model, and writes PDF or raster ... output without Ghostscript or Adobe tooling." Both of
S6's attempts for "opening" (`page_foss_attempt_1_rejected.json`,
`page_foss_attempt_2_rejected.json`) restated the same formats, the same render-model mechanism,
and the same "without Ghostscript or Adobe tooling" claim in different words; the second attempt
again dropped most other citable facts rather than reach for genuinely distinguishing ones. The
check correctly rejected both; recovery found nothing salvageable; the job failed closed. This
repository's cascade is also left incomplete, not forced through. Two independent repositories
have now shown this exact fail-closed pattern (an unusually comprehensive/well-written preserved
README paragraph leaves the model nothing non-redundant to say for "opening"), reinforcing that
it is a real, repeatable consequence of this fix's correct behavior, not a one-off fluke.

## Third confirmed instance: aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET

A third, independent recurrence. The live README's preserved paragraph states: "is a free,
open-source .NET library ... that does zero-dependency image format detection and header
probing. `ImageProbe` identifies a file's format and reads its basic properties — dimensions,
bit depth, and frame count — directly from the file header." Both of S6's attempts for "opening"
(`imaging_foss_attempt_1_rejected.json`, `imaging_foss_attempt_2_rejected.json`) restated exactly
this -- format detection, dimensions, bit depth, frame count, read from the header -- in
different words, citing only `inherited_unit:004.paragraph`. Correctly rejected both times;
recovery found nothing salvageable; job failed closed. Three independent repositories now
confirm this fail-closed pattern recurs whenever a repository's preserved paragraph is unusually
complete, across .NET and Python alike.

## Fourth confirmed instance: aspose-slides-foss/Aspose.Slides-FOSS-for-Java

A fourth independent recurrence, this time Java. The preserved content spans several inherited
units (reading/writing `.pptx`, building the OOXML package without external tools, preserving
unknown XML on save, the `Presentation` class as object-model root, no Office/COM/proprietary
runtime, JDK 21+ with no runtime dependencies beyond the JDK). Both of S6's attempts for
"opening" (`slides_java_attempt_1_rejected.json`, `slides_java_attempt_2_rejected.json`) restated
this same substance, citing those same preserved units directly rather than reaching for the
dossier's own more specific facts (`public_symbol:relationship`, `public_symbol:getfontname`,
all explicitly omitted with reasons in the second attempt). Correctly rejected both times;
recovery found nothing salvageable; job failed closed. Four independent repositories, across
.NET and Python and now Java, confirm this is a real, repeatable consequence of the fix's
correct behavior.
