"""Minimal GitHub REST wrapper: read dedup search + issue creation, local-GH_TOKEN proven.

Pulled from the old repo (``E:\\...\\repository-presenter\\src\\repository_presenter\\core\\github``)
per ``migration/reuse-manifest.yaml`` component
"GitHub App, source freshness, authorization, PR branch/issue reconciliation". Only the slice this
repository has actually exercised end to end is imported: issue creation and the fingerprint-marker
dedup search. The old repo's metadata (update_repository/replace_topics) and pull-request effect
primitives (get_ref/create_ref/get_contents/put_contents/find_pull_requests/create_pull_request/
update_pull_request) are intentionally NOT ported yet -- they belong to a later taskcard, not this
one.
"""

from __future__ import annotations
