"""Upstream-defect issue filing: fingerprint-marker dedup, then a gated create.

Pulled from the old repo's ``components/issues/`` per ``migration/reuse-manifest.yaml``. That
directory is large (approval records, close approvals, redetection, the funnel/ledger report,
quality gates on drafted bodies, batch processing); this pull imports only the slice proven end to
end today: ``dedup.py`` (the fingerprint-marker search over ``repo_presenter.github.client``) and
``file.py`` (the gated create that checks dedup first). The rest stays PENDING_REVIEW.
"""

from __future__ import annotations
