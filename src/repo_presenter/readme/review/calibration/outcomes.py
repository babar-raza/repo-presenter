"""The calibration harness's own outcome vocabulary.

Deliberately lower-case and distinct from ``ReviewVerdict.verdict`` (``"ACCEPT"`` / ``"REJECT"``):
a harness outcome is what a reviewer's verdict is *compared with*, never a value handed to a
verdict, and the structural invariant of ``tests/readme/review/test_review_invariants.py`` keeps
the upper-case words out of every place that is not the fold.
"""

from __future__ import annotations

ACCEPT = "accept"
REJECT = "reject"
UNAVAILABLE = "unavailable"
