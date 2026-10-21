# Vendored from aspose.org at 16d75e95d4, unmodified except for the import rewrite its file
# record names (migration/reuse-manifest.yaml). Do not edit here: change it by a recorded patch.
"""package_registries -- per-registry publish-verification adapters.

Each sibling module (pypi.py, nuget.py, npm.py, go.py, cargo.py) exposes one function:

    check_published(candidate: dict, *, fetch=None) -> CheckResult

`candidate` is the registry-appropriate coordinate shape. `fetch` is an injected
`(url: str) -> FetchResponse | None` callable (None on connection error/timeout) --
dependency injection instead of monkeypatching `urllib`/`requests`, so tests stay
fixture-based with zero live network calls.
"""

from __future__ import annotations

from typing import NamedTuple


class FetchResponse(NamedTuple):
    status_code: int
    body: bytes


class CheckResult(NamedTuple):
    published: bool
    ambiguous: bool  # True if the check could not conclusively determine state
    evidence_url: str
    method: str
    verified_owner: str | None = None
    project_url: str | None = None  # project/homepage/repository URL from the registry's own API
    candidate_name: str | None = None  # the actual name this result was checked against


REQUIRED_CONSECUTIVE_CHECKS = 2


def default_fetch(url: str, *, timeout: float = 10.0) -> FetchResponse | None:
    """Default `fetch` implementation: a plain unauthenticated GET via stdlib
    urllib (no `requests` dependency). Returns None on any connection-level failure
    (timeout, DNS, refused) rather than raising, so adapters can treat that
    uniformly as `ambiguous` alongside unexpected HTTP statuses.
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "aspose-org-package-registry-watch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return FetchResponse(status_code=resp.status, body=resp.read())
    except urllib.error.HTTPError as exc:
        return FetchResponse(status_code=exc.code, body=b"")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def is_corroborated_match(candidate_name: str, project_url: "str | None", expected_repo_fragment: str) -> bool:
    """A live registry hit only confirms the FOSS product if the candidate name contains "foss"
    in some form, OR corroborating metadata (the registry's own project/homepage URL) exactly
    references the product's known FOSS GitHub org/repo."""
    if "foss" in candidate_name.lower():
        return True
    if project_url and expected_repo_fragment.lower() in project_url.lower():
        return True
    return False


def apply_debounce(current_consecutive: int, result: CheckResult) -> tuple[int, bool]:
    """Given the current consecutive-agreeing-checks counter and a new
    CheckResult, return (new_counter, should_flip_to_published).

    Rules:
      - An ambiguous result never advances the counter and never flips state
        (fail closed -- a false "published" is worse than staying "not yet
        published" one cycle longer).
      - A published=False result resets the counter to 0.
      - A published=True result increments the counter; once it reaches
        REQUIRED_CONSECUTIVE_CHECKS, the caller should flip state to
        published and may reset the counter.
    """
    if result.ambiguous:
        return current_consecutive, False
    if not result.published:
        return 0, False
    new_counter = current_consecutive + 1
    return new_counter, new_counter >= REQUIRED_CONSECUTIVE_CHECKS
