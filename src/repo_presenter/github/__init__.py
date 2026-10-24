"""Minimal GitHub REST wrapper: read dedup search + issue creation, local-GITHUB_TOKEN proven.

Pulled from the old repo (``E:\\...\\repository-presenter\\src\\repository_presenter\\core\\github``)
per ``migration/reuse-manifest.yaml`` component
"GitHub App, source freshness, authorization, PR branch/issue reconciliation". Originally only
issue creation and the fingerprint-marker dedup search were exercised end to end; the PR-effect
primitives (get_ref/create_ref/get_contents/put_contents/find_pull_requests/create_pull_request/
update_pull_request) were ported later into ``github/client.py`` for ``propose/effect.py`` (still
never fired live). ``update_repository``/``replace_topics`` (repository metadata) remain not
ported.
"""

from __future__ import annotations
