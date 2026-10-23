# aspose-imaging-foss/.NET, retried: S6 succeeds this time, S8 fails closed on the same guard

2026-10-23. `aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET`. First attempt at this
repository's cascade (seventeenth-cascade round, 2026-10-22) failed closed at S6 on the
duplicate-opening guard. Retried from S6 onward (S3-S5 saved artifacts reused, not re-run).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S6 `section_authoring` (retry) | 1 per authored task | All accepted this time -- the model's "opening" attempt named specific operations (`ImageProbe.DetectFormat()`, `ImageProbe.Probe()`, format list, zero `PackageReference` entries) genuinely distinct from the preserved paragraph. |
| Render | 0 (deterministic code) | 7,326 characters, 126 lines -- the smallest rendered README this session. |
| S8 `coherence` (retry) | 1 batch | **Failed closed again** -- coherence's own attempt to revise "opening" produced a near word-for-word copy of the preserved paragraph's sentence; rejected twice; recovery found nothing salvageable. |

## The known defect, and a fifth confirmed fail-closed instance -- this time at S8

The pre-coherence render (lines 5 and 7–8) still carries the duplicate-opening-paragraph defect
in mild-to-moderate form -- the two paragraphs describe the same `ImageProbe` format-detection
behavior in different words, but the retried S6 unit stayed genuinely distinct enough to be
accepted (no near-total duplication at that stage this time).

S8 coherence then attempted to revise "opening" anyway and, on both attempts, produced text
that WAS a near-total duplicate -- the fifth confirmed instance of
`CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`'s own documented fail-closed consequence, and the
first one observed specifically at S8 rather than S6. Full details, including both rejected
attempts, are recorded in
`evidence/build/P2_REAL_ENGINE_SALVAGE/duplicate_opening_fix_fails_closed_on_email_net/README.md`'s
own "Fifth confirmed instance" section.

## Honest scope limits

- This repository's cascade remains incomplete: S6 now succeeds, but S8 does not. Left
  incomplete, not forced through with a workaround -- consistent with every other confirmed
  fail-closed instance this session.
