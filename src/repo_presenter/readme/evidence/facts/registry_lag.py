"""The registry-lag fact ID: when a registry's stable release lags the pinned source tree.

Ported (TRIMMED, ADAPT) from the old repository-presenter project's ``components/readme/
evidence/facts/registry_lag.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).
Only the constant ``reconciliation/dispositions.py`` reads is ported; the live registry-comparison
logic that produces this fact is extraction-time apparatus (PENDING_REVIEW elsewhere).
"""

from __future__ import annotations

from repo_presenter.core.facts import fact_id

REGISTRY_LAG_FACT_ID = fact_id("package", "registry_lag")
