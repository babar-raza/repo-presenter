# Label-curation brief (pre-registered, read-only, no model is being graded by you)

You are labelling a calibration corpus. For each base assigned to you, you get:

- `readme`: a candidate README (Markdown) for one open-source library.
- `facts`: a JSON file `{"repository", "source_revision", "facts": [ {id, kind, value, polarity, attributes, evidence, ...} ]}`
  — the ONLY evidence that counts. Kinds include `public_symbol` (value = the real identifier; `attributes`
  may hold `docstring`, `symbol_kind`, `signature`), `format`, `package`, `install_command`, `dependency`,
  `example` (README code that was executed/compiled; polarity SUPPORTED/CONTRADICTED/NOT_VERIFIED), `license`,
  `link_target`, `identity`, `import_path`, `build_test_asset`, and `inherited_unit` (paragraphs of the
  maintainers' live README — maintainer text, NOT evidence: a claim only an inherited unit states is still
  unsupported, and an inherited unit stating a limitation can CONTRADICT a candidate claim).
- `live`: the maintainers' live README (context only, not evidence).

Your job: find every sentence/clause in `readme` that an independent reviewer, held to the standard below,
would be RIGHT to reject. Record each as a minimal repair. The purpose is that, after your repairs, the
README is a genuinely clean twin; and each repair you record becomes a real-defect test case.

## The standard (verbatim from the reviewer's own instructions)

- A README identifier is supported when it equals a fact `value`.
- A specific claim — a number, an identifier, a format, a capability, a performance, fidelity or
  compatibility statement — that no fact states or implies is a finding however plausible it sounds.
- A public symbol's docstring, symbol_kind and signature are what the extractor read from the source: a
  sentence that paraphrases them is supported by that fact.
- A sentence that says the product does something, beside a limitation (in the README, or in an
  inherited unit) that says it does not, is a contradiction.
- An unscoped absolute dependency claim ("no dependencies", "dependency-free", "pure X") that no dependency
  fact proves is a finding. A phrase disclosing that one platform's implementation depends on another
  ("via Java", "a wrapper around X") is a finding.
- NOT findings: a sentence that only introduces, organises or summarises what neighbouring text and facts
  say; wording/ordering preferences; differences from the live README; generic but true navigation text;
  headings, tables of contents, badges, link lists to the product's own docs.
- Code blocks: an example whose `example` fact is SUPPORTED is fine; do not repair code blocks unless a fact
  is CONTRADICTED for exactly that code. Do not judge install commands/version numbers unless a
  `package`/`install_command` fact contradicts them (then it is a `contradiction`).

Be careful and evidence-driven: before recording an `unsupported_claim`, SEARCH the facts (values,
docstrings, signatures, formats, dependency facts) for the claim with grep/python — case-insensitive, with
synonyms. Record it only if nothing states or implies it. Before recording a `contradiction`, name the
fact id that contradicts it. When unsure, do not record (a missed defect makes the measurement stricter,
a wrong repair corrupts a label). Do NOT record pure style/quality issues.

## Output

Write `<curation_dir>/<base name with ':' replaced by '_'>.json`, a JSON list (possibly empty `[]`) of:

```json
{"old": "<exact substring of readme, unique, copied byte for byte, smallest span holding the defect>",
 "new": "<replacement: usually the clause deleted with punctuation fixed, or a fact-supported rewording>",
 "klass": "unsupported_claim" | "contradiction",
 "reason": "<one sentence: what is claimed and which search found nothing / which fact id contradicts it>",
 "fact_ids": ["<ids you checked or that contradict>"],
 "targets": ["<1-3 lower-case keywords of the defect>"]}
```

Rules for `old`/`new`: `old` must occur EXACTLY ONCE in the readme (verify with python
`text.count(old) == 1`, reading the file as UTF-8); keep it within one line/paragraph, not spanning a
heading or a code fence; `new` must not introduce any new claim; repairs must not overlap each other.
Validate your file with python before finishing: valid JSON, each `old` count == 1, and applying all
repairs in order succeeds. Read files as UTF-8 explicitly.

Do not modify any file other than your own output files. Do not copy README text anywhere else. Report
back only: for each base, the number of repairs by klass, and one line on anything you were unsure about.
