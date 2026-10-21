## Dedup check (required before filing)

`gh issue list --repo aspose-email-foss/Aspose.Email-FOSS-for-.Net --state all` returns
zero issues of any kind (open or closed) as of 2026-10-21. No duplicate exists.

---

## Draft issue

**Title:** 2 of 20 xUnit tests in `MapiMessageEmlTests` fail on a standard Windows
checkout (`core.autocrlf=true`) due to double-CRLF corruption in the tests' own fixture
construction

**Repository:** aspose-email-foss/Aspose.Email-FOSS-for-.Net
**Commit verified against:** `59125b4732df0eedbc4d4c2ab978698ed4348eb7` (current `main` head
as of 2026-10-21)

### Summary

Running the README's own documented command,
`dotnet test tests/Aspose.Email.Foss.Tests/Aspose.Email.Foss.Tests.csproj`, on a fresh
Windows checkout with Git's common default `core.autocrlf=true` produces 2 failures out
of 20 tests, both in `MapiMessageEmlTests`:

- `LoadFromEmlHandlesFoldedHeadersAndBase64Text` — expected `"Base64 body"`, got `""`.
- `LoadFromEmlHandlesMultipartRelatedInlineAttachment` — expected `HtmlBody` to contain
  `"cid:inline-1"`, got `null`.

### Root cause

Both tests build a synthetic `.eml` fixture from a C# raw string literal and then call:

```csharp
Encoding.ASCII.GetBytes(eml.Replace("\n", "\r\n", StringComparison.Ordinal))
```

When the `.cs` source file itself already has CRLF line endings — exactly what
`core.autocrlf=true` produces on checkout, and confirmed this is how these two test
methods are actually stored in this repository on a Windows clone — the raw string
literal's embedded line breaks are already `\r\n`. The `.Replace("\n", "\r\n")` call then
matches the `\n` *inside* each existing `\r\n` pair and turns it into `\r\n`, so every
line ending becomes `\r\r\n` (a doubled carriage return). This corrupts the synthetic
MIME message's header folding and multipart boundary lines before the library's own EML
parser ever sees valid input, so the parser correctly produces empty/`null` fields for a
malformed message — this is not a bug in `MapiMessage.LoadFromEml`'s MIME/CFB parsing
itself.

### Reproduction (independently confirmed, not just inspected)

1. Built an isolated console app referencing the real library, with the identical raw
   string literal + `.Replace("\n", "\r\n")` logic as the failing tests.
2. Saved as a plain LF file: reproduces the tests' intended (passing) behavior exactly —
   `HtmlBody` correctly quoted-printable-decoded, 1 attachment found with the right
   `ContentId`/`MimeType`/`Data`.
3. Re-saved byte-for-byte with CRLF line endings only (no other change): reproduces the
   exact failure — `HtmlBody` empty, 0 attachments found.

This isolates the cause to the checkout line-ending + `.Replace()` interaction, not to
anything environment-specific beyond that.

### Suggested fix

In both tests, replace the line-ending normalization with something idempotent regardless
of the source file's own line endings, e.g. normalize to `\n` first:
`eml.Replace("\r\n", "\n", StringComparison.Ordinal).Replace("\n", "\r\n", StringComparison.Ordinal)`,
or construct the fixture bytes directly rather than via string `.Replace()`.

### Impact

Low severity (test-only; the shipped library's own EML parsing is unaffected, confirmed
separately), but real: a contributor who clones this repository on Windows with the
default Git configuration and follows the README's own "Development and Testing"
instructions verbatim will see 2 failing tests out of the box, which could be mistaken
for a real regression.
