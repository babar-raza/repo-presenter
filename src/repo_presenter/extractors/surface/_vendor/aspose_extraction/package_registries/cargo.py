# Vendored from aspose.org at 16d75e95d4, unmodified except for the import rewrite its file
# record names (migration/reuse-manifest.yaml). Do not edit here: change it by a recorded patch.
"""cargo.py -- crates.io publish-verification adapter.

Public API endpoint: https://crates.io/api/v1/crates/{name} (unauthenticated GET).
"""

from __future__ import annotations

import json

from . import CheckResult, default_fetch


def check_published(candidate: dict, *, fetch=None) -> CheckResult:
    fetch = fetch or default_fetch
    name = candidate["name"]
    url = f"https://crates.io/api/v1/crates/{name}"
    resp = fetch(url)

    if resp is None:
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="crates-io-api")

    if resp.status_code == 404:
        return CheckResult(published=False, ambiguous=False, evidence_url=url, method="crates-io-api")

    if resp.status_code != 200:
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="crates-io-api")

    try:
        data = json.loads(resp.body)
        crate = data.get("crate", {})
        owner = crate.get("id")
        project_url = crate.get("repository") or crate.get("homepage")
    except (json.JSONDecodeError, AttributeError):
        return CheckResult(published=False, ambiguous=True, evidence_url=url, method="crates-io-api")

    return CheckResult(
        published=True,
        ambiguous=False,
        evidence_url=url,
        method="crates-io-api",
        verified_owner=owner,
        project_url=project_url,
        candidate_name=name,
    )


def search(family: str, *, fetch=None) -> list[CheckResult]:
    """Real crates.io search API. Queries for "aspose {family}" and returns
    check_published() results for every hit whose crate name looks aspose-related."""
    fetch = fetch or default_fetch
    query_url = f"https://crates.io/api/v1/crates?q=aspose+{family}&per_page=20"
    resp = fetch(query_url)
    if resp is None or resp.status_code != 200:
        return []
    try:
        data = json.loads(resp.body)
        crates = data.get("crates", [])
    except (json.JSONDecodeError, AttributeError):
        return []

    results = []
    for c in crates:
        crate_name = c.get("name", "")
        if "aspose" not in crate_name.lower():
            continue
        result = check_published({"name": crate_name}, fetch=fetch)
        if result.published and not result.ambiguous:
            results.append(result)
    return results
