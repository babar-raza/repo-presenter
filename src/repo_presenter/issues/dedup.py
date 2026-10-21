"""The fingerprint marker every filed issue body carries, and the dedup search built on it.

Ported from the old repo's ``components/issues/file.py`` (``fingerprint_marker``,
``body_with_marker``) and ``core/github/client.py::find_issue_with_marker``, combined into one
dedup primitive: *has this exact defect already been filed against this repository, as a fact
about the live repository itself, not a local artifact's claimed status.*

The old repo's ``MARKER_PREFIX`` differs by project name (``repository-presenter-defect`` vs. this
repository's ``repo-presenter-defect``) -- a filing from one project is never mistaken for the
other's.
"""

from __future__ import annotations

from repo_presenter.github.client import CreatedIssue, FetchFn, default_fetch, find_issue_with_marker

MARKER_PREFIX = "<!-- repo-presenter-defect:"
MARKER_SUFFIX = "-->"


def fingerprint_marker(defect_fingerprint: str) -> str:
    """The hidden marker every filed body carries, so the target repository itself records which
    defect an issue is for. It is exactly what :func:`check_dedup` searches for."""
    return f"{MARKER_PREFIX} {defect_fingerprint} {MARKER_SUFFIX}"


def body_with_marker(body: str, defect_fingerprint: str) -> str:
    """``body`` with the fingerprint marker appended once, unless it is already present."""
    marker = fingerprint_marker(defect_fingerprint)
    if marker in body:
        return body
    return f"{body.rstrip()}\n\n{marker}\n"


def check_dedup(
    owner: str,
    name: str,
    defect_fingerprint: str,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
) -> CreatedIssue | None:
    """Has this exact defect already been filed against ``owner/name``?

    Searches the live repository for an issue whose body carries this defect's fingerprint marker
    (open or closed, never a pull request). Returns the existing issue when found, so a caller
    records it rather than filing a duplicate; returns ``None`` only after a complete scan found no
    match. Raises :class:`repo_presenter.github.errors.RepositoryMetadataError` when the scan is
    inconclusive -- absence is never assumed from a partial read.
    """
    marker = fingerprint_marker(defect_fingerprint)
    return find_issue_with_marker(owner, name, marker, token=token, fetch=fetch)
