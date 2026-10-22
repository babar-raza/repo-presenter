# The fifteenth complete, real Lane R cascade — a nuanced partial-convergence coherence revision

2026-10-22. `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`. Fifteenth full cascade (through S8), a
seventh Python repository.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 82 dispositions / 18 units | Accepted (one `DEFER_UNRESOLVED` for an unsupported font-license claim). |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 9,899 characters, 171 lines. |
| S8 `coherence` | 2 batches, 2 calls total | `coherence#1`: 4 sections, 1 call (no reject), revised `opening/opening`. `coherence#2`: 1 call, no revisions. | Re-rendered: 9,939 characters. |

## The known defect, confirmed a fifteenth time — a nuanced coherence revision, neither clear win nor clear worsening

The pre-coherence render carries the duplicate-opening-paragraph defect in moderate form (lines
5 and 7–10 of `README.rendered.md`): both paragraphs mention parsing TeX/LaTeX and producing
PDF/DVI/SVG output, in different words.

Coherence's revision was accepted on the first attempt (no rejection), so the duplicate-opening
guard did not need to intervene here — but worth reporting precisely, not glossed over: the
revision made "opening" somewhat MORE similar to the preserved paragraph than before, now
explicitly stating "parses ... through its own interpreter" (matching the preserved paragraph's
"parses real TeX/LaTeX source through its own from-scratch interpreter") and naming "Computer
Modern fonts" (also named in the preserved paragraph), neither of which the original authored
text stated. This is a partial convergence, not the severe worsening observed in the sixth
(rust) and ninth (typescript) cascades, and not the clean differentiation observed in the
fourteenth (slides) cascade — it sits in between, and correctly stayed under the guard's
full-containment threshold (`states_all()` did not fire in either direction). Fifteenth for
fifteenth at the pre-coherence render; the guard remains correctly scoped to the severe end of
this range.

## Honest scope limits

- 15 of 36 repositories now have a FULL real cascade run through S8 (plus one,
  aspose-html-foss/Python, with S3-S6+render only; plus three abandoned attempts for unrelated
  or already-documented reasons this session).
