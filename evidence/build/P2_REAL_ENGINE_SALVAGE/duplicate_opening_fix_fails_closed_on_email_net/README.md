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
