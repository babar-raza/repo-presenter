"""The build-status badge's own fact-ID constant.

Ported (TRIMMED, ADAPT) from the old repository-presenter project's ``components/readme/
evidence/facts/assets.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry). Only
``CI_BADGE_FACT_ID`` is ported -- the one symbol ``readme/composition/planning.py`` and
``renderer.py`` actually import from this module (a shell-owned link target the badge row renders
from, excluded from every model-assignable link).

The rest of the old module (``asset_facts``, ``ci_badge_fact``, workflow/tree scanning) is
extraction-time apparatus; see migration/reuse-manifest.yaml's separate, PENDING_REVIEW
extraction entry.
"""

from __future__ import annotations

from repo_presenter.core.facts import fact_id

CI_BADGE_FACT_ID = fact_id("link_target", "badge.ci")
