# Drop inventory: every item ever dropped from a live README, decided (R14)

Date: 2026-11-06. Branch: `w/drop-inventory`. Owner ruling R14 (`docs/CONSOLIDATED_GOALS_2026-11-06.md`
Part B): every drop is examined and decided, and the system is calibrated to decide every similar drop the
same way. This is the evidence for that calibration. **No pipeline change, no candidate or seal edit, zero
provider calls.** Decisions: `data/drop_decisions.json` (schema 2; `decisions[0]` is the first decision,
unchanged). Reproduction scripts: `docs/investigations/2026-11-06-drop-inventory-data/`.

## Scope and method

* **Seals read: 60.** Every commit of every bundle ref on `origin` via `bundle_store.seal_history`
  (59 seals: 22 Lane R across 11 repositories, 37 Lane L across 13) plus the committed
  `candidates/aspose-3d-foss__Aspose.3D-FOSS-for-.NET` bundle. Every seal is at the repository's current
  HEAD (pinned read-only clones, `core.git_safety.clone.pinned_read_only_clone`, matched every seal revision).
* **Calibration candidates (iterations 4/5):** their bases are these same seals
  (`registration.json` `facts_revision` = seal revision); mutants are not drops from a live README and carry
  no dispositions. They add no items.
* **What counts as dropped.** For Lane R, every inherited unit of every seal (any disposition, including
  placing ones) is split into items: each list item, table row, sentence, code block, heading and badge row.
  An item is dropped when `validation.content_presence.unstated(strict=True)`, the test BC-05 uses, finds it
  unstated in the sealed README. Lane L: every line of `README.original.md` the sealed README does not carry.
* **De-duplication:** by repository and normalized text across seal revisions. `occurrences` counts seals.
* **Evidence:** the original README and source at the seal revision, `facts.json`, the sealed README, the
  language's own export mechanism (Rust `src/lib.rs` re-exports, TS `index.ts` exports, C++ `include/`
  headers, Python package `__init__`/`__all__`), local compile checks (`g++ -fsyntax-only`), HTTP status of
  external links (read-only GET).
* **Current pipeline measure:** the pipeline "re-adds" an item when BC-05 fails its unit with a missing piece
  inside the item, or BC-17 (`parity_gate.content_losses` against the original README) reports a loss
  matching it, on the latest seal holding the item. Otherwise it keeps the drop.

## Totals

| | Distinct items | Occurrences |
|---|---:|---:|
| All | **649** | 853 |
| READD (wrong drop) | **207** | 253 |
| KEEP_DROPPED (correct drop) | **442** | 600 |
| Lane L (all KEEP_DROPPED) | 3 | 7 |

200 of the 207 READD items are still dropped in the latest seal of their repository. Lane L: 34 of 37 seals
are byte-identical to the live README. The other 3 seals, plus 2 earlier seals with the same edits, only
replace "the commercial X" with "X — Enterprise Edition".

The stored disposition of the 207 READD items: SUPERSEDE_REDUNDANT 129, OMIT_UNSUPPORTED 48,
VERIFIED_REWRITE 13, DEFER_UNRESOLVED 11, VERIFIED_PRESERVE 5, CORRECT_WITH_EVIDENCE 1. So 19 losses carry a
*placing* or *correcting* disposition that the pipeline treats as non-loss.

## Rule table

Every item is covered by exactly one rule. "Agree" means the current pipeline decides the item the same way.

| Rule | Predicate | Decision | Items | Agree | Disagree |
|---|---|---|---:|---:|---:|
| R-CODE-EVIDENCE | code block: its example is not CONTRADICTED, every path and identifier it names exists at the revision, no identical block is printed | READD | 10 | 9 | 1 |
| R-HARNESS | code block CONTRADICTED only by an isolation failure: a helper or optional dependency that the block itself names and that the repository defines or documents | READD | 2 | 0 | 2 |
| R-CONTRADICTED | code block fails against the source for a reason inside the block | KEEP | 2 | 2 | 0 |
| R-DIAGRAM | maintainers' mermaid block, when the candidate draws its own | KEEP | 11 | 11 | 0 |
| R-VERSION-REPLACED | install snippet reprinted by the candidate with the verified current version | KEEP | 3 | 0 | 3 |
| R-CORRECTION-PRINTED | CORRECT_WITH_EVIDENCE unit whose correction is printed nowhere | READD | 1 | 0 | 1 |
| R-LINK-RESOLVES | link or path whose target exists or resolves, printed nowhere | READD | 20 | 12 | 8 |
| R-LINK-DEAD | link or path whose target does not exist at the revision | KEEP | 2 | 2 | 0 |
| R-API-PRIVATE | API row whose subject is outside the language's own export surface | KEEP | 186 | 179 | 7 |
| R-API-REQUALIFIED | `Name-suffix` row carried as `<qualifier>.Name` | KEEP | 46 | 34 | 12 |
| R-API-FILLER | public subject; the original description is generator filler ("Class with N methods") | KEEP | 13 | 10 | 3 |
| R-API-ROW-MISSING | public subject with no row in the candidate | READD | 4 | 2 | 2 |
| R-API-DESC | public subject; the maintainer description (spec section, members, tag, signature) was replaced by a generic restatement | READD | 100 | 93 | 7 |
| R-API-IDENT | prose names a public member that is printed nowhere | READD | 16 | 9 | 7 |
| R-PROSE-VALID | a technical statement the source does not contradict, printed nowhere | READD | 40 | 15 | 25 |
| R-VERSION | a dependency or tool version pinned in a project file, printed nowhere | READD | 4 | 2 | 2 |
| R-LEADIN | lead-in or heading of a block, decided with its block | as block (10 READD, 2 KEEP) | 12 | 1 | 11 |
| R-CARRIED | substance printed; only a markup token, an example value or a literal spelling differs | KEEP | 107 | 40 | 67 |
| R-POSITIONAL | positional pointer ("collected below") | KEEP | 2 | 2 | 0 |
| R-COUNT | a public-type count the verified surface contradicts | KEEP | 2 | 2 | 0 |
| R-HEADING | heading or `<details>` markup the renderer owns, content decided separately | KEEP | 50 | 50 | 0 |
| R-BADGE | badge whose information is printed elsewhere, or a decorative count | KEEP | 13 | 0 | 13 |
| R-NAMING | Lane L `enterprise_edition_naming` edit | KEEP | 3 | 3 | 0 |
| **Total** | | | **649** | **478** | **171** |

**Current-pipeline agreement: 478 / 649 = 73.7 %.** The 171 disagreements split two ways:

* **65 misses**: the pipeline accepts a wrong drop. These are what R14 forbids.
* **106 over-flags**: the pipeline would force back a correct drop, which costs repair rounds and can push a
  repair to re-add noise.

## Disagreements by rule (inventory ids = `decisions[].inventory_id`)

**Misses (pipeline keeps a drop that must be re-added):**

* **R-PROSE-VALID, 25.** Examples: the platform, migration and no-tests statements for Cells .NET (#1-3, 8, 9).
  The Windows-only NuGet restriction for C++ (#16). Go example-module guidance (#49-51). Java worksheet
  layout and stored error values (#58, 59). Rust dependency roles (#78, 79). Imaging AVIF/DJVU precision
  (#491-493, 503). The Note `_internal` warning and the PDF font environment variable (#519, 542).
  Cause: a VERIFIED_REWRITE or OMIT drop of a sentence that has no code span. BC-17 sees only code blocks,
  installs, identifiers, links and versions. BC-05 sees only SUPERSEDE.
* **R-LEADIN, 11.** BC-05 exempts every lead-in whatever its block's fate. In the Imaging seal the lead-in
  was withheld with a block that should have been re-added (#506). Elsewhere the lead-in's explanation was
  lost while its block was printed (#502), and the 3D section headings went with their dropped blocks.
* **R-LINK-RESOLVES, 8.** The TS `examples/*.ts` table (#216-224) is OMIT_UNSUPPORTED: those cells are code
  spans, not links, so BC-17 does not test them as links. All of the files exist.
* **R-API-DESC, 7, and R-API-IDENT, 7.** BC-05 `owed()` trusts `facts.json` for the public surface. The facts
  miss struct fields (Rust `CellStyle.pattern`), enum variants (`CellsError::Io`), enum members (Note
  `FileFormat`, `TagStatus`, `HorizontalAlignment`), Python attributes (Note `Outline`) and methods
  (HTML `JSContext.register_module`). C++ rows (#23, 28, 29) are on non-SUPERSEDE units.
* **R-HARNESS, 2.** Go `generateSmallPNG` (#44) and Cells Python skia (#69). A CONTRADICTED example fact
  exempts the drop in BC-17, even when the failure is the harness lacking a helper or optional dependency
  that the block itself names.
* **R-API-ROW-MISSING, 2.** TS `HtmlExporter` and `HtmlReader` (#246, 247) are DEFER_UNRESOLVED and exported
  by `aspose_cells/html/index.ts`.
* **R-VERSION, 2.** The 3D test dependency versions (#615, 616) are OMIT on a unit without code-span versions.
* **R-CORRECTION-PRINTED, 1.** The Cells .NET PackageReference (#5). CORRECT_WITH_EVIDENCE counts as always
  non-loss, but the correction was never printed.
* **R-CODE-EVIDENCE, 1.** The 3D converter build command (#644). It is a `bash` fence, so BC-17's
  `code_blocks` category skips command fences.

**Over-flags (pipeline would re-add a correct drop):**

* **R-CARRIED, 67.** `unstated(strict=True)` misses carried content in these cases:
  * a code span re-qualified (`Worksheet.Cells()` printed as `Worksheet.Cells`, or `ImageProbe.Probe()` printed as `Probe`);
  * an example token dropped from an example list ("B2", `[0, 0]`);
  * a license link printed under another path (`License/LICENSE.txt` printed as `LICENSE.txt`, #10);
  * a message literal dropped from an exception name;
  * a paraphrase below the word-share threshold.
* **R-BADGE, 13.** BC-17 counts every badge-row link as a lost link: contributor and issue counters, a runtime
  floor that is printed in Dependencies, and a license badge colour.
* **R-API-REQUALIFIED, 12.** PDF Java `Field-forms` printed as `forms.Field`, and C++
  `DiagnosticSeverity-Aspose_Cells_FOSS` printed as `Cells_FOSS.DiagnosticSeverity`. BC-05 and BC-17 compare
  the literal disambiguated name.
* **R-API-PRIVATE, 7.** HTML private-module classes (`_browsing_context.py`, `tree/_*.py`) and one TS
  non-export (#235). The HTML README marks them internal and no package `__all__` exports them. BC-05 still
  owes them because the facts list a few of their names as public.
* **R-VERSION-REPLACED, 3.** PDF Java Maven and Gradle at 26.6.0, printed at 26.9.0 (#548, 549), and 3D
  `--version 26.1.0` (#612). BC-17's version exemption needs a same-shape replacement in a *package* fact
  printed in the README, and BC-05 compares lines.
* **R-API-FILLER, 3.** The Rust "Enum with N methods and M members" rows (#181, 182, 184).

## Exceptions and limits (each item still has a rule)

1. **#18 (Cells C++, `example:002`).** KEEP_DROPPED (R-CONTRADICTED), reproduced: the block omits
   `#include "aspose/cells_foss/WorksheetCollection.h"`. The fix is mechanical, so a CORRECT_WITH_EVIDENCE
   repair (add the include) would serve the reader better than dropping it.
2. **#514 (Note `example:001`).** KEEP_DROPPED on the executed receipt (AttributeError on the maintainers'
   own fixture). I did not re-run it, because running repository code was out of scope.
3. **#630-632 (3D .NET docs, kb and reference.aspose.org links).** READD by URL pattern: sibling seals print
   the same family URLs. These hosts are unreachable from this sandbox and have no `link_target` fact.
   They should be verified in an environment that can reach them.
4. **#348 (HTML `SelectorList`).** KEEP_DROPPED. `css/__init__.py` imports it but excludes it from `__all__`,
   and its docstring calls every other name internal. A naive "imported by `__init__`" check calls it public.
5. **Detector limits.** About 107 of the KEEP items are false positives of the same strict word-share test
   that BC-05 uses. The item-level BC-05/BC-17 mapping is a best effort: a label match within the item.
   Unit-level numbers are also stored, as `bc05_unit_fails` and `bc17_unit_fails`.
6. **The committed 3D .NET candidate** is an older pipeline output. It accounts for 31 of the 207 READD items:
   whole Quick Start, Additional Examples, Development and Testing, and Documentation sections were dropped
   with "section condition does not hold".

## What the calibration implies (input to the pipeline fix, not done here)

1. One loss test for **every** disposition, including VERIFIED_REWRITE, VERIFIED_PRESERVE and
   CORRECT_WITH_EVIDENCE. It should cover sentence-level prose, not only code spans, links and versions.
2. Take the public surface from the language's own export mechanism, not from `facts.json` alone, both for
   owing members and for excusing private rows.
3. A CONTRADICTED example only excuses a drop when the failure is inside the block; harness-isolation
   failures do not count.
4. Treat equivalence as carried: re-qualified names, the same file under another path, the same snippet at
   the verified current version, and decorative badges.
5. Decide a lead-in or heading with its block. Never exempt it unconditionally.
6. Keep maintainer API descriptions for public symbols; only generator filler may be replaced.
