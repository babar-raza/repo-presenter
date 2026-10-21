"""The one error type this slice raises: a GitHub read/write that cannot be trusted.

Trimmed from the old repo's ``core/errors.py`` (``PresenterError`` -> ``RepositoryMetadataError``).
Only the one subclass this component needs is ported; the old repo's wider error hierarchy
(registry errors, correction errors, etc.) is out of scope here.
"""

from __future__ import annotations


class PresenterError(Exception):
    """Base of every error this slice raises on purpose (never a bare ``Exception``)."""

    exit_code = 1


class RepositoryMetadataError(PresenterError):
    """A GitHub read or write did not come back in a shape the caller can safely act on."""

    exit_code = 2
