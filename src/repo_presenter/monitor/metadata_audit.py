"""Read-only repository metadata audit (BL-772, WP-9; R50: every component of ``plans/idea.md``, "Central
Agent" / "Visual Assets"; ported from the OBSERVATION half only of the old project's
``components/metadata/{capture,proposal}.py``).

For every active registry repository it reads, with bounded GETs and no write of any kind, what GitHub holds:
description, homepage, topics, license, the community-profile files, and the default branch's tree (security
policy, contributing guide, code of conduct, issue and pull-request templates, CODEOWNERS, and image assets
such as a banner or logo). It reports per-repository findings and portfolio totals as JSON and markdown.

Nothing here can change GitHub: the module imports only ``github/read_client.py`` (GET only), holds no write
token and has no PATCH, PUT, POST or DELETE call (``tests/monitor/test_metadata_audit.py`` pins that). The old
``apply.py`` and ``preservation.py`` (the write half) are deliberately not ported: applying metadata is a
separate, owner-gated step (R3, R15, R22).

The repository's social preview image is not exposed by the REST API; it is recorded as ``not observable``,
never guessed.

Usage: python -m repo_presenter.monitor.metadata_audit [--registry data/registry.json] [--out-dir DIR]
           [--repository owner/name ...]       (token: GH_TOKEN, optional; raises the rate limit only)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_presenter.github.read_client import (
    GITHUB_API_ROOT,
    Fetch,
    _get_with_retry,
    fetch_get,
    fetch_tree,
)

SCHEMA_VERSION = 1
DESCRIPTION_MAX = 350  # GitHub's own field limit
#: the two constant, always-true labels the old proposal used (``STATIC_TOPICS``)
EXPECTED_TOPICS = ("aspose", "foss")
_IMAGE = re.compile(r"\.(png|jpe?g|gif|svg|webp)$", re.IGNORECASE)
_VISUAL_NAME = re.compile(r"(banner|logo|social|preview|hero|cover|icon)", re.IGNORECASE)

#: check id -> (label, predicate over the observed row); a failing check is a finding.
CHECKS: tuple[tuple[str, str], ...] = (
    ("description", "description set"),
    ("description_length", "description within GitHub's 350 characters"),
    ("topics", "at least three topics"),
    ("expected_topics", "topics include aspose and foss"),
    ("license", "license detected by GitHub"),
    ("readme", "README present"),
    ("security_policy", "SECURITY.md present"),
    ("contributing", "CONTRIBUTING present"),
    ("code_of_conduct", "CODE_OF_CONDUCT present"),
    ("issue_template", "issue template present"),
    ("pr_template", "pull-request template present"),
    ("visual_asset", "an image asset (banner, logo or screenshot) in the repository"),
    ("not_archived", "repository not archived"),
)


def _get_json(url: str, *, token: str | None, fetch: Fetch, sleep: Callable[[float], None] | None) -> tuple[Any, str | None]:
    try:
        response = _get_with_retry(url, token=token, fetch=fetch, sleep=sleep)
    except Exception as exc:  # noqa: BLE001 -- a failed read is recorded, never raised
        return None, f"{type(exc).__name__}: {exc}"
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    try:
        return response.json(), None
    except ValueError as exc:
        return None, f"malformed JSON: {exc}"


def _has(paths: Sequence[str], *patterns: str) -> list[str]:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    return [p for p in paths if any(c.search(p) for c in compiled)]


def classify_tree(paths: Sequence[str]) -> dict[str, Any]:
    """Community and visual files in a repository tree (pure)."""
    images = [p for p in paths if _IMAGE.search(p)]
    return {
        "readme": _has(paths, r"^(\.github/|docs/)?README(\.\w+)?$"),
        "security_policy": _has(paths, r"^(\.github/|docs/)?SECURITY\.(md|rst|txt)$"),
        "contributing": _has(paths, r"^(\.github/|docs/)?CONTRIBUTING(\.(md|rst|txt))?$"),
        "code_of_conduct": _has(paths, r"^(\.github/|docs/)?CODE_OF_CONDUCT(\.(md|rst|txt))?$"),
        "issue_template": _has(paths, r"^\.github/ISSUE_TEMPLATE(/|\.md$)"),
        "pr_template": _has(paths, r"^(\.github/|docs/)?PULL_REQUEST_TEMPLATE(\.md|/)"),
        "codeowners": _has(paths, r"^(\.github/|docs/)?CODEOWNERS$"),
        "funding": _has(paths, r"^\.github/FUNDING\.yml$"),
        "changelog": _has(paths, r"^CHANGELOG(\.(md|rst|txt))?$"),
        "license_file": _has(paths, r"^(LICENSE|LICENCE|COPYING)(\.(md|txt))?$"),
        "images": images[:20],
        "image_count": len(images),
        "named_visuals": [p for p in images if _VISUAL_NAME.search(p.rsplit("/", 1)[-1])][:10],
    }


def observe_repository(
    repository: str,
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """One repository's metadata row from three read-only GETs (repo, community profile, tree)."""
    row: dict[str, Any] = {"repository": repository, "errors": []}
    repo, error = _get_json(f"{GITHUB_API_ROOT}/repos/{repository}", token=token, fetch=fetch, sleep=sleep)
    if repo is None or not isinstance(repo, dict):
        row["errors"].append(f"repository: {error}")
        row["observed"] = False
        row["findings"] = ["unknown:all"]
        return row
    license_info = repo.get("license") if isinstance(repo.get("license"), dict) else None
    row.update(
        observed=True,
        description=repo.get("description"),
        homepage=repo.get("homepage") or None,
        topics=sorted(str(t) for t in repo.get("topics") or []),
        license=(license_info or {}).get("spdx_id"),
        default_branch=repo.get("default_branch"),
        archived=bool(repo.get("archived")),
        visibility=repo.get("visibility"),
        has_issues=bool(repo.get("has_issues")),
        pushed_at=repo.get("pushed_at"),
        social_preview="not observable (the REST API does not expose it)",
    )
    profile, error = _get_json(
        f"{GITHUB_API_ROOT}/repos/{repository}/community/profile", token=token, fetch=fetch, sleep=sleep
    )
    if isinstance(profile, dict):
        files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
        row["community_profile"] = {
            "health_percentage": profile.get("health_percentage"),
            "files": sorted(k for k, v in files.items() if v),
        }
    else:
        row["errors"].append(f"community profile: {error}")
        row["community_profile"] = None
    branch = row.get("default_branch")
    tree = fetch_tree(repository, str(branch), token=token, fetch=fetch, sleep=sleep) if branch else None
    if tree is not None and tree.error is None:
        row["tree"] = classify_tree(tree.paths)
        row["tree"]["truncated"] = tree.truncated
    else:
        row["errors"].append(f"tree: {tree.error if tree else 'no default branch'}")
        row["tree"] = None
    row["findings"] = findings(row)
    return row


def findings(row: dict[str, Any]) -> list[str]:
    """The failing checks for one observed row (pure); a check whose input could not be read is
    ``unknown:<id>``, never a pass."""
    if not row.get("observed"):
        return ["unknown:all"]
    tree = row.get("tree")
    profile = row.get("community_profile")
    profile_files = set((profile or {}).get("files") or [])
    topics = set(row.get("topics") or [])
    description = row.get("description") or ""

    def from_tree(key: str, profile_key: str | None = None) -> str | None:
        if tree is None and profile is None:
            return "unknown"
        found = bool(tree and tree.get(key)) or (profile_key is not None and profile_key in profile_files)
        if not found and tree is None:
            return "unknown"
        return None if found else "fail"

    results: dict[str, str | None] = {
        "description": None if description.strip() else "fail",
        "description_length": "fail" if len(description) > DESCRIPTION_MAX else None,
        "topics": None if len(topics) >= 3 else "fail",
        "expected_topics": None if set(EXPECTED_TOPICS) <= topics else "fail",
        "license": None if row.get("license") not in (None, "NOASSERTION") else "fail",
        "readme": from_tree("readme", "readme"),
        "security_policy": from_tree("security_policy"),
        "contributing": from_tree("contributing", "contributing"),
        "code_of_conduct": from_tree("code_of_conduct", "code_of_conduct"),
        "issue_template": from_tree("issue_template", "issue_template"),
        "pr_template": from_tree("pr_template", "pull_request_template"),
        "visual_asset": ("unknown" if tree is None else (None if tree.get("image_count") else "fail")),
        "not_archived": "fail" if row.get("archived") else None,
    }
    return [f"{'unknown:' if v == 'unknown' else ''}{k}" for k, v in results.items() if v]


def audit(
    repositories: Sequence[dict[str, Any]],
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Audit every given ``{"repository", "family", "platform"}`` row; the report is data only."""
    rows = []
    for entry in repositories:
        row = observe_repository(entry["repository"], token=token, fetch=fetch, sleep=sleep)
        row["family"], row["platform"] = entry.get("family"), entry.get("platform")
        rows.append(row)
    totals = {check: 0 for check, _ in CHECKS}
    unknown = {check: 0 for check, _ in CHECKS}
    for row in rows:
        for finding in row["findings"]:
            if finding == "unknown:all":
                for check in unknown:
                    unknown[check] += 1
            elif finding.startswith("unknown:"):
                unknown[finding.split(":", 1)[1]] += 1
            else:
                totals[finding] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "generated_at": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repositories": len(rows),
        "observed": sum(1 for r in rows if r.get("observed")),
        "failing_by_check": totals,
        "unknown_by_check": unknown,
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    labels = dict(CHECKS)
    lines = [
        "# Repository metadata audit (read-only)",
        "",
        f"Generated {report['generated_at']}. {report['observed']} of {report['repositories']} repositories "
        "observed. Reads only (repository, community profile, default-branch tree); nothing was written.",
        "",
        "## Portfolio totals",
        "",
        "| check | failing | unknown |",
        "|---|---|---|",
    ]
    for check, _ in CHECKS:
        lines.append(f"| {labels[check]} | {report['failing_by_check'][check]} | {report['unknown_by_check'][check]} |")
    lines += ["", "## Per repository", "", "| repository | license | topics | findings |", "|---|---|---|---|"]
    for row in report["rows"]:
        if not row.get("observed"):
            lines.append(f"| {row['repository']} | - | - | not observed: {'; '.join(row['errors'])} |")
            continue
        lines.append(
            f"| {row['repository']} | {row.get('license') or 'none'} | {len(row.get('topics') or [])} | "
            f"{', '.join(row['findings']) or 'none'} |"
        )
    lines += ["", "Social preview images are not observable through the REST API and are not counted."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=Path("data/registry.json"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--repository", action="append", default=[])
    args = parser.parse_args(argv)

    document = json.loads(args.registry.read_text(encoding="utf-8"))
    entries = [e for e in document["entries"] if e.get("active")]
    if args.repository:
        entries = [e for e in entries if e["repository"] in set(args.repository)]
    report = audit(entries, token=os.environ.get("GH_TOKEN") or None)
    text = render_markdown(report)
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "metadata-audit.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        (args.out_dir / "metadata-audit.md").write_text(text, encoding="utf-8")
    print(text)
    # Non-zero only when nothing at all could be observed (a blind observer); findings are the result.
    return 0 if report["observed"] else 2


if __name__ == "__main__":
    sys.exit(main())
