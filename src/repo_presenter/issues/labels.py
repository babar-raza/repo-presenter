"""Stage 7 (ASSIGNMENT/LABELS): the labels a filed issue carries.

Deterministic: a pure function of the handoff's ``defect_class``. There are deliberately NO
assignees here: neither the registry schema (``core/registry/models.py``'s ``RegistryEntry``) nor
the ``Handoff`` model has an assignee field, so nothing may be assigned until one is added and
reviewed. ``create_issue`` accepts ``assignees`` for that future caller; this module never
supplies any.
"""

from __future__ import annotations

from repo_presenter.issues.model import Handoff

BASE_LABEL = "repo-presenter"


def labels_for(handoff: Handoff) -> tuple[str, ...]:
    """``("repo-presenter",)``, plus ``defect:<class>`` (lower-case) when the class is known."""
    if handoff.defect_class is None:
        return (BASE_LABEL,)
    return (BASE_LABEL, f"defect:{handoff.defect_class.lower()}")
