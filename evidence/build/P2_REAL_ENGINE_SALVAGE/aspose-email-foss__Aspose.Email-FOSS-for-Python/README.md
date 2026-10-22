# Lane L real-pipeline run: aspose-email-foss/Aspose.Email-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-email-foss/Aspose.Email-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 33 files cloned; live README fetched via `gh api`, 411 lines.

**Facts:** 203 facts built. 6 example receipts: 5 `EXECUTED`, 1 `FAILED`. One fact
`CONTRADICTED`: `example:005`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 3 total:**

- `[failing_example]` line 174: example on lines 174-186 — "example 5: FAILED;
  NameError". The failing snippet (from `facts.json`, `example:005`):
  ```python
  from aspose.email_foss import msg

  with msg.MsgReader.from_file(msg_path) as reader:
      cfb = reader.cfb_reader
      print(f"major_version={cfb.major_version} sector_size={cfb.sector_size}")

      header = reader.top_level_header
      print(f"recipient_count={header.recipient_count} attachment_count={header.attachment_count}")

      for entry in reader.iter_recipient_storages():
          print(f"recipient storage: {entry.name}")
  ```
  Checked the live README directly (not just this run's facts): `msg_path` is
  never assigned anywhere else in the document either — the `NameError` is a
  real defect in the README's own example #5, not an artifact of how the
  verifier staged inputs. Reported as observed; not patched (out of this
  card's scope).
- `[format_overclaim]` line 34: 'CFB' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 49: 'CFB' marked supported, no confirming SUPPORTED fact
  (second occurrence, different line).

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-email-foss__Aspose.Email-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
