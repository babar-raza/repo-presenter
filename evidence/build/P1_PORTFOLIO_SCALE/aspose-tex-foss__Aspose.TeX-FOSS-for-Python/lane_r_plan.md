# Lane R plan — aspose-tex-foss/Aspose.TeX-FOSS-for-Python

**Case A (substantial live README).** The live README at `181015d2eee3e19f8af3d84e4a932ac84ad47c7c`
already has every fixed-core section (title/badges, Navigation, At a Glance, Key Capabilities,
Installation, Dependencies, Quick Start, Additional Examples, API Reference, Documentation &
Resources, Scope and Limitations, Development and Testing, License), each with real, specific
content: a mermaid diagram that matches the actual Starting-Points/Capabilities/Outputs shape of
this library, Quick Start code that uses the real public API (`TeXJob`, `TeXOptions`, `PdfDevice`,
`create_input_source`), a Scope and Limitations section that already honestly discloses five
concrete, source-verified limitations (Pre-Alpha status, `load_format="plain"` incompleteness,
math-mode non-layout, `\halign`/`\valign` stubs, hyphenation inactivity, named file-stream I/O
stubs), and an API Reference table whose class names, field names, and defaults match the actual
source text verbatim. This is not a thin or templated README; it is a credible, well-organized
baseline that happens to describe a package whose source currently fails to import.

**Lane R converges to Lane L.** Every CONTRADICTED fact in `facts.json` traces to one root cause —
`F-PACKAGE-IMPORT-BROKEN`: at this pinned revision, 101 of 118 `.py` files (including
`presentation/__init__.py`, which defines the entire public API surface) have collapsed to
single-space indentation that doesn't increase for nested block bodies, so `import aspose_tex`
raises `IndentationError` immediately and `pytest` cannot collect 67 of the 68 test modules. This
defect is already filed upstream as issue #2, opened by this same project on 2026-10-20 against
this exact commit, so it is independently confirmed rather than a one-off local artifact. Because
the defect is a single, uniform, repo-wide root cause rather than a collection of independent
per-format or per-class defects (contrast the worked example's narrower OBJ-export-only finding),
the one precise, minimal correction the mission's rules call for is a single new bullet at the top
of Scope and Limitations — the section this README itself already uses as its disclosure
mechanism for exactly this kind of caveat — rather than annotating each of the ~10 individual code
blocks that implicitly assume the package runs. That one bullet is honest about the scope of the
problem (file count, first failure point, test-collection impact, upstream issue link) without
touching a single other sentence. Every other fact checked this session — package naming, PyPI
non-publication, dependency declarations, the `TeXOptions`/`OutputDevice`/exception class surfaces,
and all five of the README's pre-existing Scope bullets — is SUPPORTED by source text read
directly from the pinned commit. There is no deficient-README case to argue here and no basis for
a from-facts reconstruction that diverges from Lane L: `lane_r_candidate.md` is identical to
`lane_l_candidate.md`.

One deliberate choice: the Development and Testing section's own sentence ("68 test modules cover
...") is left untouched rather than separately edited, even though F-TEST-SUITE-CANNOT-RUN shows
those modules currently fail to collect. The new Scope bullet already states plainly that "pytest
cannot collect 67 of the 68 test modules," which directly addresses this section's claim without
requiring a second, redundant edit elsewhere in the document — consistent with making the smallest
number of precise edits that fully discharge the verified facts, not the smallest edit to any one
sentence in isolation.
