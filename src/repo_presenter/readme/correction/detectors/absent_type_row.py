"""A maintainers' API table row naming a type the public surface no longer has, removed.

BC-14 rule (i) (``readme/validation/surface_claims.py``) fails a README's own API table when a row
names a type no SUPPORTED ``public_symbol``/``enum_member``/``import_path`` fact records (``
absent_type_rows``): the library once had it, or never did, and the table drifted out of sync with
the current public surface. Real case (Lane L, Aspose.Cells FOSS for Rust, 2026-11-10): the live
table still lists `BorderStyle`, `CellValueKind`, `FillPatternKind`, `SheetVisibility` and
`ValidationMessageSeverity`, none of them a type the current crate exports.

Lane R's own validation/restore path already has the one deterministic reading of "printed" for a
kept table (``without_absent_type_rows``): the named rows gone, every other row, the header, the
separator and the surrounding prose exactly as written. This detector is that same reading,
expressed as a Lane L ``Edit`` against the live file: each absent row is removed *whole*, its own
line terminator included (``TABLE_ROW_REMOVAL``) -- blanking just the row's text, the only thing a
single-line ``FALSE_CLAIM_FIX`` could do, would leave an orphan blank line in the middle of a GFM
table, which ends the table early (BC-07's "code fence/table" reading, BC-09) instead of fixing it.
Every other row, the header and the separator are untouched; the detector never rewrites a row that
is still a real type, and never touches a delegate/callback/type-alias row (``absent_type_rows``
already excludes those: their absence from the symbol facts is a facts-coverage gap, not evidence
the type itself is not public).

Deliberately NOT a Lane L finding when the facts give no types at all, or the table reads as too
small or too mixed a share of real types to be an API type table in the first place:
``absent_type_rows`` itself returns nothing for either case (its own module docstring has the
tuned thresholds), so this detector simply has nothing to edit.
"""

from __future__ import annotations

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    TABLE_ROW_REMOVAL,
    Context,
    DetectorResult,
    Edit,
)
from repo_presenter.readme.validation.surface_claims import _supported, absent_type_rows

DETECTOR = "absent_type_row"
#: Evidence facts named on an edit, the same convention and count as ``stale_type_count``'s
#: ``_CITED``: a sample of the positive surface the absent row is measured against, not an
#: exhaustive citation (the detector's correctness rests on ``absent_type_rows`` itself).
_CITED = 8


@detector(DETECTOR)
def absent_type_row(ctx: Context) -> DetectorResult:
    drop = set(absent_type_rows(ctx.readme, ctx.facts))
    if not drop:
        return DetectorResult()
    symbols = (
        _supported(ctx.facts, "public_symbol")
        + _supported(ctx.facts, "enum_member")
        + _supported(ctx.facts, "import_path")
    )
    cited = tuple(fact.id for fact in symbols[:_CITED])
    if not cited:
        return DetectorResult()
    lines = ctx.lines
    edits: list[Edit] = []
    for index, line in enumerate(lines):
        if line.in_fence or line.text not in drop:
            continue
        if index + 1 >= len(lines):
            continue  # the table's last row has no trailing line terminator to remove with it
        end = lines[index + 1].start
        original = ctx.readme[line.start : end]
        if original.count("\n") != 1 or not original.endswith("\n"):
            continue  # not a single, whole line (should not happen; fail closed if it did)
        edits.append(
            Edit(
                kind=TABLE_ROW_REMOVAL,
                detector=DETECTOR,
                start=line.start,
                end=end,
                original=original,
                replacement="",
                fact_ids=cited,
                rationale=(
                    f"line {line.number} names a type no public_symbol, enum_member or "
                    "import_path fact records; the row is removed whole, not blanked"
                ),
            )
        )
    return DetectorResult(edits=tuple(edits))
