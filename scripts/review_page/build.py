#!/usr/bin/env python
"""Build the "README Candidate Review" page (docs/REVIEW_PAGE.md) from the durable state, reproducibly (R38).

Every RECERTIFIED latest seal (zero-call `repo_presenter.recertify --all`) becomes one candidate on the page: its sealed
README, its Lane L diff and original, whether it is an R16 no-op, and whether an attested M9 record accepted it. README
images are fetched once and embedded (the viewer's page cannot load external images), large raster images re-encoded at
reading width; mermaid 10.9.1 is inlined from the npm package (the page must not depend on a CDN).

    python scripts/review_page/build.py --out <file.html> [--remote origin] [--mermaid <mermaid.min.js>]

Publishing the built file to the review artifact is a supervisor step (the Artifact tool runs in the session, not in
Actions); see docs/REVIEW_PAGE.md. Owner feedback saved on the page lives in the artifact's `feedback` collection.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TEMPLATE = HERE / "template.html"
MERMAID_TARBALL = "https://registry.npmjs.org/mermaid/-/mermaid-10.9.1.tgz"
MAX_IMAGE_BYTES = 400_000
REENCODE_OVER = 60_000
IMAGE_WIDTH = 900


def _git_show(commit: str, path: str) -> str | None:
    done = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, cwd=REPO)
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


def certified_seals(remote: str) -> list[dict]:
    subprocess.run(["git", "fetch", "-q", remote, "+refs/repository-presenter-state/*:refs/repository-presenter-state/*"],
                   cwd=REPO, check=False)
    done = subprocess.run([sys.executable, "-m", "repo_presenter.recertify", "--all", "--json", "--remote", remote],
                          capture_output=True, text=True, cwd=REPO, check=True)
    return [row for row in json.loads(done.stdout) if row.get("outcome") == "RECERTIFIED"]


def attested(remote: str) -> set[tuple[str, str]]:
    sys.path.insert(0, str(REPO / "ops" / "checks"))
    sys.path.insert(0, str(REPO / "src"))
    import portfolio_delivery_count as pdc  # noqa: PLC0415

    return set(pdc.read_attested_acceptances(remote=remote))


def candidates(remote: str) -> list[dict]:
    accepted = attested(remote)
    out = []
    for row in certified_seals(remote):
        commit, rev, lane = row["seal_commit"], row["revision"], row["lane"]
        readme = _git_show(commit, f"{rev}/README.md")
        if readme is None:
            continue
        original = _git_show(commit, f"{rev}/README.original.md") if lane == "L" else None
        # Both lanes seal the diff against the live README at the pinned revision; the owner reviews both (2026-11-13).
        diff = _git_show(commit, f"{rev}/README.patch.diff") or ""
        noop = lane == "L" and original is not None and original.replace("\r\n", "\n") == readme.replace("\r\n", "\n")
        out.append({
            "repository": row["repository"], "lane": lane, "revision": rev[:12], "seal": commit[:12],
            "readme": readme, "diff": diff, "noop": noop,
            "audited": (row["repository"], lane) in accepted,
            "id": hashlib.sha1(f"{row['repository']}|{lane}".encode()).hexdigest()[:10],
        })
    return sorted(out, key=lambda c: (c["lane"], c["repository"]))


_IMG = re.compile(r'!\[[^\]]*\]\(([^)\s]+)|<img[^>]+src="([^"]+)"')


def _shrink(raw: bytes) -> str | None:
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        return None
    image = Image.open(io.BytesIO(raw))
    image.load()
    if image.width > IMAGE_WIDTH:
        image = image.resize((IMAGE_WIDTH, round(image.height * IMAGE_WIDTH / image.width)))
    if image.mode in ("P", "LA"):
        image = image.convert("RGBA")
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=80)
    return "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()


def _fetch(item: tuple[str, str, str]) -> tuple[str, str, str | None]:
    repository, revision, src = item
    if src.startswith("data:"):
        return repository, src, None
    url = src if src.startswith("http") else urllib.parse.urljoin(
        f"https://raw.githubusercontent.com/{repository}/{revision}/", src)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "readme-review-preview"})
        with urllib.request.urlopen(request, timeout=20) as response:
            kind = (response.headers.get("Content-Type") or "").split(";")[0]
            raw = response.read()
    except Exception:  # noqa: BLE001 -- an unreachable image keeps its alt text on the page
        return repository, src, None
    if not kind.startswith("image/"):
        return repository, src, None
    if kind != "image/svg+xml" and len(raw) > REENCODE_OVER:
        return repository, src, _shrink(raw)
    if len(raw) > MAX_IMAGE_BYTES:
        return repository, src, None
    return repository, src, f"data:{kind};base64," + base64.b64encode(raw).decode()


def images(cands: list[dict]) -> dict[str, dict[str, str]]:
    wanted = {(c["repository"], c["revision"], a or b) for c in cands for a, b in _IMG.findall(c["readme"])}
    embedded: dict[str, dict[str, str]] = {}
    with ThreadPoolExecutor(16) as pool:
        for repository, src, data in pool.map(_fetch, sorted(wanted)):
            if data:
                embedded.setdefault(repository, {})[src] = data
    return embedded


def mermaid_source(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    with urllib.request.urlopen(MERMAID_TARBALL, timeout=60) as response:
        archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
    return archive.extractfile("package/dist/mermaid.min.js").read().decode("utf-8")


FFFD = chr(0xFFFD)  # written by code point: a literal U+FFFD in source is what the Artifact tool rejects


def _embed_json(text: str) -> str:
    # Inside <script type="application/json">: "<\\/" is the same JSON string and can never close the element.
    return text.replace("</", "<\\/").replace(FFFD, "\\uFFFD")


def _embed_js(text: str) -> str:
    # Library code: change nothing but what could end the element or what the Artifact tool rejects (mermaid has one
    # U+FFFD, inside a string literal, where the escape is identical).
    if re.search(r"</script", text, re.I):
        raise ValueError("library source contains </script; refusing to inline it")
    return text.replace(FFFD, "\\uFFFD")


def build(out: Path, remote: str, mermaid: str | None) -> dict:
    cands = candidates(remote)
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__DATA__", _embed_json(json.dumps(cands, ensure_ascii=False)), 1)
    page = page.replace("__IMAGES__", _embed_json(json.dumps(images(cands))), 1)
    page = page.replace("__MERMAID__", _embed_js(mermaid_source(mermaid)), 1)
    out.write_text(page, encoding="utf-8")
    return {
        "candidates": len(cands),
        "lane_r": sum(c["lane"] == "R" for c in cands),
        "lane_l": sum(c["lane"] == "L" for c in cands),
        "lane_l_noop": sum(c["noop"] for c in cands),
        "audited": sum(c["audited"] and not c["noop"] for c in cands),
        "bytes": len(page.encode("utf-8")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--mermaid", help="a local mermaid.min.js (10.9.1) instead of downloading the npm package")
    args = parser.parse_args(argv)
    print(json.dumps(build(args.out, args.remote, args.mermaid)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
