# Vendored from aspose.org at 16d75e95d4, unmodified except for the import rewrite its file
# record names (migration/reuse-manifest.yaml). Do not edit here: change it by a recorded patch.
"""go.py -- Go Modules publish-verification adapter.

Public API endpoint: https://proxy.golang.org/{module-path}/@v/list
(unauthenticated GET; module path must be case-encoded per the Go module
proxy protocol -- every uppercase letter is escaped as '!' + its lowercase form).

A 200 response with a non-empty body (at least one version line) means
published; a 404/410 means not published; anything else is ambiguous.
"""

from __future__ import annotations

from . import CheckResult, default_fetch


def _escape_module_path(module_path: str) -> str:
    """Go module proxy case-encoding: each uppercase letter becomes '!' + its lowercase form."""
    return "".join(f"!{c.lower()}" if c.isupper() else c for c in module_path)


def check_published(candidate: dict, *, fetch=None) -> CheckResult:
    fetch = fetch or default_fetch
    module_path = candidate["module_path"]
    escaped_path = _escape_module_path(module_path)
    url = f"https://proxy.golang.org/{escaped_path}/@v/list"
    resp = fetch(url)

    if resp is None:
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="go-proxy-api")

    if resp.status_code in (404, 410):
        return CheckResult(published=False, ambiguous=False, evidence_url=url, method="go-proxy-api")

    if resp.status_code != 200:
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="go-proxy-api")

    if not resp.body.strip():
        # 200 with an empty version list is not a documented proxy behavior;
        # treat conservatively as ambiguous rather than assuming published.
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="go-proxy-api")

    return CheckResult(
        published=True, ambiguous=False, evidence_url=url, method="go-proxy-api",
        project_url=f"https://{module_path}", candidate_name=module_path,
    )
