# aspose.org example verifier — findings to fix upstream

The single place where problems found in aspose.org's example verification
(`scripts/pipeline/lib/example_verification/`) are logged, so they can be fixed there too (owner
request, 2026-11-05). Each entry: what is wrong, a minimal reproduction, where, the impact in
aspose.org itself, and the fix used here. Read against the sibling checkout at
`32cb4ebd2c9e5e35dcdd7616e4d9091a7bed4fd4` (2026-11-04).

This repository reused aspose.org's input-vs-output literal classifier
(`fixtures.py: _statement_prefix`, `_classify`, `input_fixture_names`) in
`src/repo_presenter/core/example_io.py`; every reproduction below was run against that port with
its local fixes switched off, so it is aspose.org's logic, and is pinned by a test in
`tests/core/test_example_io.py`. Nothing was executed from aspose.org itself.

| # | Severity in aspose.org | Finding | Where |
|---|---|---|---|
| 1 | **Active** (Java) | A writer constructor's literal is classified as an **input** | `fixtures.py:319`, `:344` |
| 2 | Latent (Rust, Go runners don't use the classifier) | `create` is not an output word; Rust `File::create(...)` is an **input** | `fixtures.py:319`, `:321` |
| 3 | Latent (Python runner doesn't use the classifier) | `open(<file>, "w")` is an **input**: the mode is never read | `fixtures.py:337-346` |
| 4 | Gap (Python) | A Python constructor taking the file (`Document("in.pdf")`) is **unknown**, so it is never treated as an input | `fixtures.py:344` |
| 5 | Minor | A call split over lines loses its callee: `doc.save(\n "out.pdf")` is **unknown** | `fixtures.py:330-334` |
| 6 | Coverage | Only the Java, .NET and Go runners use the classifier; Python, Rust, C++ and TypeScript have no input/output distinction at all | `runners/*.py` |

## 1. A writer constructor's literal is classified as an input — ACTIVE

```java
Writer w = new FileWriter("out.txt");      // classified: input
```

`_OUTPUT_WORDS` is matched against **whole words** of identifiers (deliberately, so `target` does not
match `get`). `FileWriter` splits into `file` + `writer`; `writer` is not `write`, so no output word
fires, and `new` then classifies the literal as an **input**. The same holds for
`BufferedWriter`, `PrintWriter`, `StreamWriter` (C#), `XmlWriter`, … — every `*Writer` type.

**Impact in aspose.org**: the Java runner's `default_prelude` stages a generated fixture under the name
the example is about to write (harmless only if the API overwrites), and the Java/.NET/Go runners'
`_is_expected_input` relabels a missing-file error on that path as **FIXTURE-UNAVAILABLE**. An example
that writes into a directory that does not exist (`new FileWriter("outputfiles/out.txt")` with no
`outputfiles/`) is a real README defect, and it is reported as a missing fixture instead.

**Fix used here**: `writer` added to the output words (and `create`, below).

## 2. `create` is not an output word — latent

```rust
let f = File::create("out.txt")?;          // classified: input (`File` -> word "file")
```
```go
f, _ := os.Create("out.xlsx")              // classified: unknown
```

`File::create`, `os.Create`, `Files.createFile` create (write) their file, but `create` is in neither
list, and Rust's `File` hits the input word `file`. aspose.org's Rust runner does not consult the
classifier and Go's yields `unknown` here, so nothing goes wrong today; it would the day either runner
starts using it. **Fix used here**: `create` added to the output words.

## 3. `open(<file>, "w")` is classified as an input — latent

```python
with open("out.txt", "w") as f:            # classified: input
    f.write("x")
```

`_classify` reads only the text *before* the literal, so `open` (an input word) decides, and the mode
argument after it is never looked at. Also `open("log.txt", mode="a")`, `"x"`, `"w+"`, `"wb"`. The
Python runner does not use the classifier today. **Fix used here**: when the callee is `open(` and
the next argument is a write/append/exclusive/update mode, the literal is an output; `"r"`/`"rb"`
remain inputs.

## 4. A Python constructor taking the file is unknown — gap

```python
doc = Document("in.pdf")                   # classified: unknown (no `new` in Python)
```

`new X("f")` counts as a read; Python has no `new`, so the most common Python form of opening a sample
document is never classified as an input. Safe (fail closed: unknown is never staged), but it means a
Python runner built on this classifier would never pre-stage the input of `Document("in.pdf")`.
**Fix used here**: a capitalised callee whose first argument is the literal counts as a constructor
(excluding `Create(`/`New(`, which are Go-style factories, see 2).

## 5. A call split over lines loses its callee — minor

```python
doc.save(
    "out.pdf",
)                                          # classified: unknown
```

`_statement_prefix` cuts at the last `;`, `{`, `}` **or newline**, so the prefix of a literal on its
own line is empty. Fail-closed (unknown is never staged, never relabelled), so this only loses a
correct classification. Not fixed here either; a fix would cut at the last statement boundary rather
than the last newline (tracking open brackets).

## 6. Four runners have no input/output distinction — coverage

`input_fixture_names` / `default_prelude` are used by `runners/java.py`, `runners/dotnet.py` and
`runners/go.py` only. The Python, Rust, C++ and TypeScript runners neither pre-stage inputs nor tell an
input from an output, so a missing input there cannot be told apart from a real defect by this
mechanism. Not a bug in the classifier; a gap in where it is applied.

## Why this repository needed it

This repository's own Python example verifier staged a repository file under **every** file-like
literal an example named. Aspose.PDF for Python's `document.save("hello.pdf")` therefore found a PDF
already at `hello.pdf`, and that library's `save` refuses to overwrite: 19 of the 37 examples recorded
CONTRADICTED for that README were this (`FileExistsError`). aspose.org's classifier, with fixes 1-4,
is now what decides which literals get a fixture here.
