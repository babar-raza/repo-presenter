# Targeted recheck: the duplicate-opening fix, re-fired against the ninth cascade's own repository

2026-10-22. Per mission non-negotiable #4 (portfolio-first: every shared-defect fix gets a
targeted, not global, recheck after) and the CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL card's own
"remaining" note, this re-fires S6 authoring and S8 coherence -- live LLM calls, not just the unit
tests already in the commit -- against `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, the ninth
cascade's own repository and the single worst instance of the defect this session observed
(coherence's revision there made "opening" a near word-for-word copy of the preserved paragraph
beside it). S3/S4/S5 are unchanged and were not re-fired; only S6 and S8, the two call sites this
fix touches, were re-run from the same accepted investigation.json/dispositions.json/plan.json.

## S6 (authoring), re-fired

Unaffected, as expected: the original defect was never in S6's own first-draft output for this
repository (that pre-coherence authored "opening" unit was already distinct from the preserved
paragraph -- the pairing is what the ninth cascade's own evidence entry already recorded). The
re-fired S6 call produced an equivalent, independently-distinct "opening" unit again, accepted on
the first attempt.

## S8 (coherence), re-fired -- this is the real test

`coherence#1` needed **2 calls** this time (the original run needed only 1): the new
dispositions-aware check in `unit_checks()` (reached via `coherence_checks()`) rejected the
model's first attempt, and the re-ask produced a second, accepted attempt.

The resulting `opening` text is now genuinely distinct from the preserved paragraph, not a
near-duplicate of it:

```
It reads and writes 3D scene data in formats such as glTF, OBJ, STL, FBX, and COLLADA, converts
scenes between these formats using `Scene.fromFile`, `Scene.openFromBuffer`, `Scene.save`, and
`Scene.saveToBuffer`, and builds and manipulates 3D scenes through `Scene`, `Node`, `Mesh`,
`Material`, `Camera`, and `Light` objects, supporting geometry construction, material assignment,
and animation with keyframes.
```

against the preserved paragraph beside it ("Aspose.3D FOSS for TypeScript is a free, open-source,
MIT-licensed TypeScript/JavaScript library for building and converting 3D scenes in Node.js...").
Compare this to the original ninth-cascade result
(`evidence/build/P2_REAL_ENGINE_SALVAGE/lane_r_ninth_full_cascade/README.coherent.md`), where
coherence's revision was a near word-for-word copy of the preserved paragraph.

## Conclusion

The fix holds under a live re-run, not just the unit tests already committed with it: on this
repository, coherence's own tendency to push "opening" toward the preserved paragraph was caught
and corrected on retry, not merely detected in a synthetic fixture. This is one targeted
recheck, not a global one -- the sixth cascade's repository (the other worsened case) has not yet
been re-fired, and the fix's own card already states it is partial (catches near-total
duplication only, not the milder structural redundancy most cascades showed).
