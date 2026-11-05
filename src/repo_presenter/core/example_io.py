"""Which file-name literals an example READS (so a fixture may be staged under them) and which it
WRITES (so nothing may be).

REUSE (2026-11-05, owner-directed "aspose.org has recently implemented example verification in
full, see if you can reuse anything"): ported from the aspose.org pipeline's
``scripts/pipeline/lib/example_verification/fixtures.py`` (``_statement_prefix``, ``_classify``,
``input_fixture_names`` and their word lists; sibling checkout at
``32cb4ebd2c9e5e35dcdd7616e4d9091a7bed4fd4``), logic unchanged; see
``migration/reuse-manifest.yaml``.

Why: this repository's Python example verifier staged a fixture under EVERY file-like literal an
example named. An example that writes ``document.save("hello.pdf")`` therefore found a repository
PDF already at ``hello.pdf``, and a library that refuses to overwrite (Aspose.PDF for Python's
``save`` raises ``FileExistsError`` on an existing destination) failed: a README example that
works was recorded CONTRADICTED. Measured 2026-11-05 on Aspose.PDF for Python: 19 of its 37
CONTRADICTED examples were exactly this. A literal the example writes is now never staged
(``written_names``); a literal it reads, or that cannot be classified, is staged as before.
"""

from __future__ import annotations

import re

_QUOTED_FILE_RE = re.compile(
    r"""["']((?:[A-Za-z0-9_][A-Za-z0-9_.,+ -]*/)*[A-Za-z0-9_][A-Za-z0-9_.,+ -]*\.[A-Za-z0-9]{1,6})["']"""
)
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
#: WHOLE WORDS of a call/constructor/variable name (camelCase / PascalCase / snake_case split) that
#: mean "this literal is WRITTEN" -- matched as words, never substrings, so ``target``, ``address``,
#: ``profile``, ``prefix`` do not hit ``get``/``add``/``file``/``fix``.
_OUTPUT_WORDS = frozenset(
    {"save", "write", "export", "output", "dump", "store",
     # local fixes (not in the aspose.org original, reported there): `File::create`, `os.Create`,
     # `new FileWriter(...)` write their file, and matched as whole words they never fired.
     "create", "writer"}
)
#: ... and READ. ``new X("f")`` (a constructor taking a file literal) also counts.
_INPUT_WORDS = frozenset(
    {"open", "load", "read", "parse", "from", "input", "source", "import", "merge", "append",
     "attach", "embed", "get", "add", "with", "file"}
)
_WORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")

INPUT = "input"
OUTPUT = "output"
UNKNOWN = "unknown"


def _words(ident: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(ident.replace("_", " "))}


def _statement_prefix(code: str, start: int) -> str:
    """Text of the current statement before ``start`` (since the last ``;``, ``{``, ``}`` or
    newline)."""
    cut = max(code.rfind(c, 0, start) for c in (";", "{", "}", "\n"))
    return code[cut + 1 : start]


#: The one local addition to the ported rules: Python builds an object without ``new``, so
#: ``Document("input.pdf")`` -- a capitalised callee whose first argument is the literal -- is the
#: same read as ``new Document("input.pdf")`` (otherwise it would be "unknown" and not staged).
_CONSTRUCTOR_CALL = re.compile(r"(?:^|[^\w.])(?:\w+\.)*(?!Create\b|New\b)[A-Z]\w*\(\s*$")
#: ``open(<literal>, "w")``: the mode decides, not the word ``open`` (local fix, reported to
#: aspose.org): a write/append/exclusive-create mode makes the literal an output.
_OPEN_CALL = re.compile(r"(?:^|[^\w.])(?:\w+\.)?open\(\s*$")
_WRITE_MODE = re.compile(r"""^\s*,\s*(?:mode\s*=\s*)?["'][rbt]*[wax+]""")


def _classify(prefix: str) -> str:
    idents = _IDENT_RE.findall(prefix)
    words: set[str] = set()
    for ident in idents:
        words |= _words(ident)
    if words & _OUTPUT_WORDS or any(i.lower().startswith("to_") for i in idents):
        return OUTPUT
    if "new" in {i.lower() for i in idents} or words & _INPUT_WORDS:
        return INPUT
    if _CONSTRUCTOR_CALL.search(prefix):
        return INPUT
    return UNKNOWN


def literal_roles(code: str) -> dict[str, set[str]]:
    """Each quoted, extension-bearing relative file name -> the roles its occurrences play."""
    roles: dict[str, set[str]] = {}
    for match in _QUOTED_FILE_RE.finditer(code):
        name = match.group(1).replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/"):
            continue
        prefix = _statement_prefix(code, match.start())
        role = _classify(prefix)
        if _OPEN_CALL.search(prefix) and _WRITE_MODE.match(code[match.end() :]):
            role = OUTPUT
        roles.setdefault(name, set()).add(role)
    return roles


def written_names(code: str) -> set[str]:
    """The file names any occurrence of which the example WRITES: nothing may be staged under
    them. This is what this repository's verifier uses (see ``python_examples.stage_fixtures``):
    aspose.org's stricter ``input_fixture_names`` would also refuse every literal it cannot
    classify, and measured 2026-11-05 that turned four working examples into NEEDS_INPUT or
    FAILED (``bind_pdf("input.pdf")``, a list passed to ``concatenate``, a loop over a tuple of
    names), because this verifier's retry serves only one measured missing path per re-run."""
    return {name for name, roles in literal_roles(code).items() if OUTPUT in roles}


def input_fixture_names(code: str) -> list[str]:
    """The file names the example READS: kept only when every occurrence is an input. First-seen
    order, de-duplicated."""
    return [name for name, roles in literal_roles(code).items() if roles == {INPUT}]
