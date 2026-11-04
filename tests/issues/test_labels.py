"""Stage 7 (ASSIGNMENT/LABELS): deterministic label derivation; no assignees by default."""
from __future__ import annotations

from dataclasses import replace

from repo_presenter.issues.labels import labels_for
from repo_presenter.issues.model import DEFECT_CLASSES

from .factory import _handoff


def test_labels_are_base_plus_defect_class():
    h = _handoff(defect_class="LICENSE_MISSING_ROOT")
    assert labels_for(h) == ("repo-presenter", "defect:license_missing_root")


def test_labels_without_defect_class_are_base_only():
    assert labels_for(replace(_handoff(), defect_class=None)) == ("repo-presenter",)


def test_every_known_class_maps_deterministically_and_distinctly():
    seen = {labels_for(replace(_handoff(), defect_class=c))[1] for c in DEFECT_CLASSES}
    assert len(seen) == len(DEFECT_CLASSES)
    assert all(len(label) <= 50 for label in seen)  # GitHub's label-name limit
    assert labels_for(_handoff()) == labels_for(_handoff())
