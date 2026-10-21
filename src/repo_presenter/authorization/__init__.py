"""Effect-authorization gating: typed refusal codes a write path reports before any remote effect.

Trimmed from the old repo's ``core/authorization`` per ``migration/reuse-manifest.yaml`` component
"GitHub App, source freshness, authorization, PR branch/issue reconciliation". Only the vocabulary
this repository's issue-filing slice needs is pulled in (``refusals.py``); the old repo's fuller
per-write authorization *record* machinery (``proposal.py``, ``record_provenance.py`` -- an
owner-signed, expiring, evidence-digest-bound approval artifact for a README-correction PR effect)
is not ported yet. It is a real, larger component that belongs to a later taskcard once this
repository has a correction-PR effect to gate, not the one-issue slice this pull proves.
"""

from __future__ import annotations
