"""BL-630: the reviewer prints the packet's line label in a finding's text ('Line 0209: ...') but cites a
truncated number (lines [9]); the label names the line, so the citation moves to it (hosted 3D TypeScript
run 44924648803: lines 9, 26, 28, 29, 33 for 0209, 0226, 0228, 0229, 0233; the whole review was lost twice)."""

from __future__ import annotations

import copy

from repo_presenter.readme.review.llm_review import review_checks
from repo_presenter.readme.review.reply import (
    ReviewScope,
    repair_miscited_lines,
    resolve_cited_lines,
)
from tests.readme.review.review_support import FACTS, raw_finding, raw_reply


def _candidate() -> tuple[str, dict[str, int]]:
    rows = ["# Aspose.3D FOSS for TypeScript", "", "Opening sentence of the project that is long enough.", ""]
    rows += [f"Filler paragraph line number {i} of the opening." for i in range(5, 200)]
    rows += ["", "## API Reference", ""]
    at: dict[str, int] = {}
    for name, desc in (
        ("Light", "Class that inherits from Camera and declares the member lightType."),
        ("ReferenceMode", "Class that declares the members DIRECT, INDEX and INDEX_TO_DIRECT."),
        ("RotationMode", "Class that declares the members FIXED and ORBIT."),
    ):
        rows.append(f"| `{name}` | {desc} |")
        at[name] = len(rows)
    return "\n".join(rows) + "\n", at


def _finding(kind: str, line: int, text: str) -> dict:
    f = raw_finding(kind, text=text)
    f.pop("quote")
    f["lines"] = [line]
    return f


def test_the_exact_hosted_shape_is_repaired_and_the_review_is_valid() -> None:
    candidate, at = _candidate()
    assert at["Light"] > 200 and at["Light"] % 100 != at["Light"]
    scope = ReviewScope(frozenset({"api_reference"}), frozenset(at.values()))
    findings = [
        _finding("contradiction", at["Light"] % 100, f"Line {at['Light']:04d}: `Light` | Class that inherits from Camera and declares the member lightType."),
        _finding("unsupported_claim", at["ReferenceMode"] % 100, f"Line {at['ReferenceMode']:04d}: `ReferenceMode` | Class that declares the members DIRECT, INDEX and INDEX_TO_DIRECT."),
        _finding("unsupported_claim", at["RotationMode"] % 100, f"Line {at['RotationMode']:04d}: `RotationMode` | Class that declares the members FIXED and ORBIT."),
    ]
    reply = raw_reply("REJECT_FACTUAL", findings)
    assert resolve_cited_lines(copy.deepcopy(reply), candidate, scope)  # refused as written (the hosted failure)
    repair_miscited_lines(reply, candidate, scope)
    assert [f["lines"] for f in reply["findings"]] == [[n] for n in at.values()]
    assert resolve_cited_lines(reply, candidate, scope) == []
    again = copy.deepcopy(reply)
    repair_miscited_lines(again, candidate, scope)
    assert again == reply  # idempotent: a stored reply replays identically
    problems = review_checks(
        raw_reply("REJECT_FACTUAL", [copy.deepcopy(findings[0])]),
        candidate_readme=candidate, facts=FACTS, plan={}, scope=scope, changed=None,
    )
    assert not any("not shown" in p for p in problems)


def test_other_label_spellings_are_read() -> None:
    candidate, at = _candidate()
    scope = ReviewScope(frozenset({"api_reference"}), frozenset(at.values()))
    n = at["RotationMode"]
    for text in (
        f"{n:04d}| `RotationMode` | Class that declares the members FIXED and ORBIT.",
        f"line {n}: RotationMode Class that declares the members FIXED and ORBIT.",
    ):
        reply = raw_reply("REJECT_FACTUAL", [_finding("unsupported_claim", 3, text)])
        repair_miscited_lines(reply, candidate, scope)
        assert reply["findings"][0]["lines"] == [n], text


def test_negative_controls_leave_the_citation_to_be_refused() -> None:
    candidate, at = _candidate()
    n = at["RotationMode"]
    scope = ReviewScope(frozenset({"api_reference"}), frozenset(at.values()))
    unchanged = 9
    for label_line, text in (
        (n, f"Line {n:04d}: this sentence is not on that line at all, it was invented."),  # content mismatch
        (150, "Line 0150: `RotationMode` | Class that declares the members FIXED and ORBIT."),  # label not shown
        (None, "RotationMode | a paraphrase that prints nowhere in the candidate."),  # no label
        (n, "Line 0001: `RotationMode` | Class that declares the members FIXED and ORBIT."),  # label elsewhere, unshown
    ):
        reply = raw_reply("REJECT_FACTUAL", [_finding("unsupported_claim", unchanged, text)])
        repair_miscited_lines(reply, candidate, scope)
        assert reply["findings"][0]["lines"] == [unchanged], text
        assert resolve_cited_lines(reply, candidate, scope)
    # a valid citation is never moved by a label
    reply = raw_reply("REJECT_FACTUAL", [_finding("contradiction", at["Light"], f"Line {n:04d}: `RotationMode` | Class that declares the members FIXED and ORBIT.")])
    repair_miscited_lines(reply, candidate, scope)
    assert reply["findings"][0]["lines"] == [at["Light"]]
    # a whole-section kind is not repaired by a label either
    f = _finding("quality", 9, f"Line {n:04d}: `RotationMode` | Class that declares the members FIXED and ORBIT.")
    reply = raw_reply("REJECT_FACTUAL", [f])
    repair_miscited_lines(reply, candidate, scope)
    assert reply["findings"][0]["lines"] == [9]
