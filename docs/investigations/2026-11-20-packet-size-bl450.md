# BL-450: the section_authoring request grows with the repository (2026-11-20, R46)

Hosted re-run 44673623844 (PDF TypeScript Lane R, main 3b07ba8) ended `JobError: section_authoring: gateway answered HTTP 400:
ContextWindowExceededError ... your request has 258818 input tokens (8000 > 262144 - 258818)`. Zero provider calls were made
for this investigation.

## Cause, by first principles

The `section_authoring` job has two modes. Both build their packet from the facts document, and neither bounded it:

* **author** (one request per section, plus one per batch of up to 40 types): `accepted_facts` carries the full text of every
  fact the section may cite, and the inherited README units a section places (VERIFIED_PRESERVE and the like) are such facts.
* **coherence** (one request per batch of sections): `rendered_document` is the whole rendered README, which prints those same
  inherited units verbatim, and `accepted_facts` carries the union over the batch's sections of the same units in full. The
  README's own text is therefore sent twice.

PDF TypeScript's README is 557,612 characters (605 inherited units, 553,956 characters; the largest tables are 47k and 42k).
The packet is bounded by the upstream README, not by what the model needs.

Reproduced offline (facts of PDF Java for the product part, the real PDF TypeScript README at the pinned revision 47760f0 for the
inherited units, every unit placed verbatim across three sections; the real PDF TypeScript facts could not be extracted here, the
facts job builds the repository's examples and exhausted the disk):

| request | before | after |
|---|---|---|
| coherence, one batch of 6 sections | 1,217,754 characters | 352,992 characters |
| author, largest section (api_reference) | 282,192 | 282,192 (fits, unchanged) |

1,217,754 characters over the measured density of 4.6 to 5.3 characters per token (below) is 230k to 265k tokens; the hosted
refusal said 258,818. The refused request was almost certainly the coherence call: authoring, even with every unit placed in one
section, is about 60k tokens. The run log does not print which request it was, so this is an inference, not proven.

## Size distribution of what exists (24 sealed Lane R cells; the other 16 have no seal on the state remote, they are the failing ones)

Request characters, rebuilt from each seal's stored facts, plan, dispositions and units. Every rebuilt authoring request hash was
checked against the call ledger of PDF C++ (13 of 13 reproduce exactly, so the rebuild is the request). Density measured on
those: 2.6 to 5.3 characters per token (PDF C++ api_reference#types-1: 96,256 characters, 18,314 prompt tokens). Sorted by the
cell's largest request; before and after the change are identical for every cell (every request fits).

| cell | largest authoring request (chars) | section | largest coherence request (chars) | inherited README chars | facts |
|---|---|---|---|---|---|
| PDF Java | 126,724 | api_reference | 319,193 | 109,592 | 29,330 |
| Words .NET | 96,489 | api_reference | 193,942 | 71,404 | 19,834 |
| 3D .NET | 189,697 | api_reference#types-1 | 117,167 | 34,466 | 4,796 |
| Slides Python | 72,354 | api_reference#types-1 | 157,781 | 46,880 | 6,414 |
| PDF Cpp | 98,111 | api_reference#types-4 | 147,651 | 47,241 | 3,500 |
| HTML Python | 80,457 | api_reference#types-6 | 138,616 | 32,964 | 506 |
| 3D Python | 124,684 | api_reference#types-3 | 134,450 | 46,719 | 2,650 |
| Cells Rust | 90,875 | api_reference | 133,805 | 33,465 | 2,288 |
| Cells Cpp | 88,576 | api_reference | 121,666 | 32,946 | 2,350 |
| Slides Java | 54,041 | api_reference | 119,106 | 49,244 | 8,297 |
| Cells Go | 70,288 | api_reference | 98,965 | 29,476 | 959 |
| Note Python | 85,223 | api_reference#types-1 | 74,204 | 22,735 | 703 |
| Cells Python | 67,214 | api_reference | 83,749 | 5,353 | 2,295 |
| BarCode Python | 82,572 | api_reference#types-1 | 73,947 | 10,944 | 953 |
| Cells Java | 33,961 | api_reference | 82,379 | 29,907 | 4,101 |
| Email .Net | 73,272 | api_reference#types-1 | 59,175 | 17,169 | 511 |
| Email Cpp | 72,107 | api_reference#types-1 | 66,688 | 23,854 | 465 |
| Email Python | 42,200 | api_reference | 71,141 | 19,715 | 690 |
| Cells TypeScript | 59,309 | api_reference#types-1 | 67,023 | 14,766 | 400 |
| Cells .NET | 44,731 | api_reference | 66,203 | 5,712 | 1,516 |
| PSD .NET | 38,032 | api_reference | 48,834 | 8,119 | 489 |
| OCR .NET | 29,133 | key_capabilities | 45,142 | 12,737 | 202 |
| Imaging .NET | 28,817 | key_capabilities | 43,357 | 14,333 | 252 |
| PSD Java | 40,104 | api_reference#types-1 | 38,877 | 4,743 | 970 |

24 cells, largest request per cell: median 85,223, p90 189,697, maximum 319,193 characters (162 authoring requests: median
31,087; the coherence request is the larger one in 18 of the 24). The ratio of the coherence request to the cell's inherited
README text is 2.4 to 3.1 (PDF Java 319,193 over 109,592). PDF TypeScript's README is 553,956 characters of inherited units,
five times PDF Java's, which puts its coherence request at about 1.2 million characters.

## Fix (inside existing components, R27)

1. `authoring.bound_task` / `coherence.bound_coherence_packet`: a request estimated over `REQUEST_CHAR_CEILING` (360,000
   characters, at most about 140k tokens at the densest measured ratio) is shortened; a request under it is returned as it was.
   Only the text shown for a fact the section merely sees is cut (to the longest of 8000, 4000, 2000, 1000, 500, 250 characters
   that fits, at a line boundary, with a marker), and in coherence the document's own long blocks. Never cut: a fact a slot is bound
   to, a must-carry unit, identity and package facts, every id, the slots, the units, the schema. Each cut is recorded beside the
   stored call (`<request>.repaired-0.json`, rule BL-450, R14); a request that still does not fit at the shortest cap says so.
2. A batch of types over the ceiling is split in halves instead of cut (every type keeps its own facts in full).
3. `jobs.ContextWindowError` (a `JobError`): the gateway's context refusal with the measured size. Authoring and coherence catch
   it and ask again, at most twice, with a ceiling sized from that request's own characters per token.
