# Third ecosystem's real format-detection catch — a different defect shape than .NET's

2026-10-22 (updated — supersedes this directory's first version, which honestly reported the
`format_claims`/`format_declarations` stub gap this entry closes).
`python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-Java java <clone>`.

**What changed since the first run**: `format_declarations` was stubbed (`return []`) for Java,
same as every ecosystem except Python at the time. Now closed:

**`extractors/platforms/java_format_declarations.py`** (new engineering, not a port): reads every
`.java` file for (a) a `new FileFormat(...)`/subclass `super(...)` constructor call — the
declaration — and (b) an `ext.equals("...")` dispatch arm inside a `load`/`save`/
`createLoadOptions`/`createSaveOptions` method — the registration, direction from the method
name. Correlated by extension string directly (Java's own dispatch tests the literal extension,
never a format identifier the way .NET's switch does, so there is no identifier to join on).

**Different real defect shape than .NET's**: this repository's live README does not over-claim
any format — its "At a Glance" diagram only claims STL, which really is registered both
directions. The real, measured gap is the *opposite* direction:

```
[report_gaps] line 0: 2 verified format(s) named nowhere in the README: format:input.glb, format:output.glb
```

GLB is declared (`GLTF2_BINARY`, extension `"glb"`) and matched by the `load`/`save`/
`createLoadOptions`/`createSaveOptions` dispatch chains (`ext.equals("gltf") || ext.equals("glb")`),
so this reader correctly reports it as registered both directions — an honest under-claim catch,
the same direction the old repo's own `report_gaps` detector already covers, now extended to
Java by having any format facts to feed it at all.

**Known, stated limitation this run surfaced but does not fix**: `GltfReader.load()` and
`GltfWriter.save()` are themselves unimplemented `// TODO` stubs in the real source — dispatched
but not actually working. This reader's registration signal is "a dispatch arm matches", not "the
matched handler actually does anything"; telling dispatched-but-stubbed apart from genuinely
working needs reading the handler body's own implementation, which is out of scope for a static
declaration+dispatch reader and is recorded here rather than silently papered over. The GLB
under-claim finding above is therefore not fully trustworthy as stated — a human reviewer
following it would discover the stub, which is exactly why `report_gaps`' own finding is advisory
("would fill"), never an auto-edit.

**One real false positive found and fixed along the way**: the Starting-Points/Outputs node label
`"An existing STL file (binary or ASCII)"` caused `format_overclaim` to flag "ASCII" as an
unsupported second format claim — it is a content-encoding qualifier of the STL claim right next
to it, not a separate format. Added to the same evidence-based `_NOT_A_FORMAT` exclusion list as
the earlier AVEVA/PDMS fix, with a regression test reproducing the exact false positive.

**Unrelated, already-known finding, still correctly reported**: `enterprise_edition_naming`
still flags line 634's "the commercial Aspose.3D for Java" naming substitution (see this
directory's prior version / `migration/reuse-manifest.yaml` for the original catch) — unaffected
by this pass, confirming the two detector families don't interfere with each other.

## Honest scope limits

- `java_examples.py` (execution-backed example verification) is still not ported — all 7 example
  receipts are `NOT_VERIFIED`. This proof is entirely static, not execution-backed.
- The dispatched-but-stub gap above is real and stated, not silently resolved.
- Verified against one repository, one family. Not yet run against the other Java repos in the
  registry to see whether the same two patterns generalize or need adjustment.
