# Lane R plan — aspose-words-foss/Aspose.Words-FOSS-for-Python

**Case A (substantial live README).** This README is a mature, dense, fixed-core-compliant
document: a navigation list matching an actual heading skeleton, a mermaid "At a Glance" diagram,
an 8-bullet Key Capabilities list with concrete class/method names, Installation/Dependencies
sections that match `pyproject.toml` exactly, a Quick Start plus seven "Additional Examples" that
are all real runnable code (and, per this session's execution, all of them actually run), a large
but genuinely module-grouped API Reference table, a Documentation & Resources section, and —
notably — a Scope and Limitations section that already does exactly the kind of precise,
narrow, implementation-grounded disclosure this project asks a Lane R candidate to produce (the
DOC-write, ISO29500-STRICT, and PdfSaveOptions-unconsumed-fields bullets all independently
verified SUPPORTED against the source in this session). This is not a thin or structurally
deficient README; it reads as though it was already built to this project's own standard.

**Lane R converges to Lane L.** Of 15 facts checked this session, exactly one was CONTRADICTED
(F-RTF-STANDARD-FAILS: standard plain-text RTF fails to load with `NotOleFileError`, a real,
reproducible upstream defect already tracked as open issue #3 — not a new finding, so no
`draft_upstream_issue.md` was written). That single fact is exactly the kind of narrow,
implementation-precise gap the existing Scope and Limitations section already documents three of
(DOC write, ISO29500 STRICT, 8 unconsumed PdfSaveOptions fields) — so the correct Lane R move is to
add a fourth bullet in the same voice and place, which is exactly what Lane L already did. There is
no case-B divergence to construct: nothing here is thin, missing a fixed-core section, or weakly
evidenced enough to warrant a from-facts rebuild. `lane_r_candidate.md` is therefore identical to
`lane_l_candidate.md`.

One fact (F-API-PUBLIC-TYPE-COUNT, the "146 public types" claim) is UNVERIFIED rather than
SUPPORTED or CONTRADICTED — a raw class count (193) is consistent with but does not reproduce the
curated 146 figure. This is retained as-is (UNVERIFIED_BUT_UNCHALLENGED in content_units.json),
per the project rule against silently asserting an unverified claim as true or false.
