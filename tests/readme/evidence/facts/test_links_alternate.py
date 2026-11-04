"""Alternate-source rule: a github.com blob/raw link whose direct check cannot be established is
asked of raw.githubusercontent.com. BROKEN, RESOLVED (direct), RESOLVED (alternate) and UNCHECKED
stay distinct. Fake transport only; no network."""

from __future__ import annotations

import httpx
import pytest

from repo_presenter.readme.evidence.facts.links import (
    LinkResult,
    check_external,
    link_facts,
)

GH = "https://github.com/o/r/blob/main/docs/a.md"
RAW = "https://raw.githubusercontent.com/o/r/main/docs/a.md"


class FakeTransport:
    """url -> (status, final url) or an exception; records every call."""

    def __init__(self, table: dict[str, object]) -> None:
        self.table = table
        self.calls: list[str] = []

    def __call__(self, url: str) -> tuple[int, str]:
        self.calls.append(url)
        item = self.table[url]
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, tuple)
        return item


def _check(
    table: dict[str, object], href: str = GH
) -> tuple[LinkResult, FakeTransport]:
    transport = FakeTransport(table)
    return check_external(href, fetch=transport, sleep=lambda _s: None), transport


def test_direct_200_resolves_directly_without_an_alternate_call() -> None:
    result, transport = _check({GH: (200, GH)})
    assert (result.outcome, result.source) == ("RESOLVED", "direct")
    assert transport.calls == [GH]


def test_direct_404_is_broken_and_never_asks_the_alternate() -> None:
    result, transport = _check({GH: (404, GH)})
    assert result.outcome == "MISSING"
    assert transport.calls == [GH]


@pytest.mark.parametrize("direct", [403, 429, 502])
def test_unreachable_direct_plus_raw_200_resolves_via_the_alternate(
    direct: int,
) -> None:
    result, transport = _check({GH: (direct, GH), RAW: (200, RAW)})
    assert result.outcome == "RESOLVED"
    assert result.source == "raw.githubusercontent.com"
    assert "via raw.githubusercontent.com" in result.detail
    assert RAW in transport.calls


def test_direct_403_plus_raw_404_stays_unchecked() -> None:
    result, _ = _check({GH: (403, GH), RAW: (404, RAW)})
    assert result.outcome == "UNCHECKED"


def test_direct_403_plus_raw_403_stays_unchecked() -> None:
    result, _ = _check({GH: (403, GH), RAW: (403, RAW)})
    assert result.outcome == "UNCHECKED"


def test_raw_redirecting_off_the_raw_host_is_not_authoritative() -> None:
    result, _ = _check({GH: (403, GH), RAW: (200, "https://elsewhere.example/x")})
    assert result.outcome == "UNCHECKED"


def test_connection_error_plus_raw_200_resolves_via_the_alternate() -> None:
    result, _ = _check({GH: httpx.ConnectError("down"), RAW: (200, RAW)})
    assert (result.outcome, result.source) == ("RESOLVED", "raw.githubusercontent.com")


def test_connection_error_on_both_stays_unchecked() -> None:
    result, _ = _check({GH: httpx.ConnectError("down"), RAW: httpx.ConnectError("x")})
    assert result.outcome == "UNCHECKED"


def test_github_raw_path_form_is_also_rewritten() -> None:
    href = "https://github.com/o/r/raw/main/docs/a.md"
    result, _ = _check({href: (403, href), RAW: (200, RAW)}, href)
    assert result.outcome == "RESOLVED"


@pytest.mark.parametrize(
    "href",
    [
        "https://github.com/o/r/blob/feature%2Fx/a.md",  # encoded ref
        "https://github.com/o/r/blob/main/../secret.md",  # traversal
        "https://github.com/o/r/blob/main/%2e%2e/secret.md",  # encoded traversal
        "https://github.com/o/r/blob/main/a%2Fb.md",  # encoded slash
        "https://github.com/o/r/blob/main/",  # no path
        "https://github.com:8443/o/r/blob/main/a.md",  # unusual port
    ],
)
def test_unsafe_ref_or_path_is_never_rewritten(href: str) -> None:
    result, transport = _check({href: (403, href)}, href)
    assert result.outcome == "UNCHECKED"
    assert transport.calls == [href]


@pytest.mark.parametrize(
    "href",
    [
        "https://github.com/o/r/issues/1",
        "https://github.com/o/r/tree/main/docs",
        "https://gitlab.com/o/r/blob/main/a.md",
        "https://example.com/o/r/blob/main/a.md",
    ],
)
def test_other_urls_keep_their_behaviour(href: str) -> None:
    result, transport = _check({href: (403, href)}, href)
    assert (result.outcome, result.detail) == ("UNCHECKED", "HTTP 403 (access-gated)")
    assert transport.calls == [href]


def test_alternate_resolution_is_recorded_distinctly_in_the_fact_evidence() -> None:
    body = f"[a]({GH})\n".encode()
    via = FakeTransport({GH: (403, GH), RAW: (200, RAW)})
    facts, probes = link_facts("README.md", body, [], fetch=via)
    assert facts[0].polarity == "SUPPORTED"
    assert facts[0].evidence[1].detail == "RESOLVED via raw.githubusercontent.com"
    assert "raw.githubusercontent.com" in (probes[0].observation or "")
    plain, _ = link_facts("README.md", body, [], fetch=FakeTransport({GH: (200, GH)}))
    assert plain[0].evidence[1].detail == "RESOLVED"
    stuck = FakeTransport({GH: (403, GH), RAW: (404, RAW)})
    blocked, _ = link_facts("README.md", body, [], fetch=stuck)
    assert blocked[0].polarity == "UNRESOLVED"
    assert blocked[0].evidence[1].detail == "UNCHECKED"
    gone, _ = link_facts("README.md", body, [], fetch=FakeTransport({GH: (404, GH)}))
    assert gone[0].polarity == "CONTRADICTED"
    assert gone[0].evidence[1].detail == "MISSING"
