"""BL-791 (hosted Lane L TeX Python, run 44993635165: example 9 'FAILED; InputError').

The real shape: the README's "Messages and Logging" example runs ``\\input chapter1`` with
``extra_format_paths=[Path("tex-inputs")]``. The product answers ``InputError: cannot resolve input
file 'chapter1'`` because the reader's own ``chapter1.tex`` is not in the repository -- the same
situation as a ``FileNotFoundError``, an input the example leaves to the reader, so it is
``NEEDS_INPUT`` (an UNRESOLVED example fact), never a CONTRADICTED one that Lane L must report as a
defect of the README. A failure that does not name a file the example itself names stays FAILED.
"""

from __future__ import annotations

from repo_presenter.core.execution import ExecutionResult
from repo_presenter.extractors.platforms.python_examples import _classify

CODE = 'source = create_input_source("\\\\input chapter1\\n\\\\bye")\n'
TRACE = (
    "Traceback (most recent call last):\n  File \"example.py\", line 5, in <module>\n"
    "aspose_tex.exceptions.InputError: cannot resolve input file 'chapter1'\n"
)


def _result(stderr: str) -> ExecutionResult:
    return ExecutionResult(("python", "example.py"), 1, "", stderr, False)


def test_the_products_own_missing_input_error_is_needs_input() -> None:
    outcome, detail = _classify(_result(TRACE), CODE)
    assert outcome == "NEEDS_INPUT" and "InputError" in detail


def test_a_missing_file_the_example_never_names_stays_failed() -> None:
    outcome, _ = _classify(_result(TRACE.replace("chapter1", "other")), CODE)
    assert outcome == "FAILED"


def test_a_different_error_that_mentions_the_name_stays_failed() -> None:
    stderr = "x.InputError: unbalanced braces near 'chapter1'\n"
    assert _classify(_result(stderr), CODE)[0] == "FAILED"


def test_the_message_decides_not_the_exception_class() -> None:
    stderr = "ValueError: cannot find file 'chapter1'\n"
    outcome, _ = _classify(_result(stderr), CODE)
    assert outcome == "NEEDS_INPUT"  # the named input matters, not what the library calls the error
