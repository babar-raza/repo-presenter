# 2026-11-04 (TC-012): the smallest credible Docker isolation, matching the existing two-job
# trust boundary rather than inventing a new one.
#
# This image runs ONLY the `facts` stage -- the UNPRIVILEGED half of present.yml that executes
# the upstream repository's own code (example builds). It bakes in no secret of any kind, on
# purpose: `python -m repo_presenter.present --stage facts ...` needs none, and baking a
# provider key or state-write token into a container image would be a strictly WORSE isolation
# story than GitHub Actions' own per-job ephemeral runner + just-in-time secret injection that
# the `present` job already relies on. The `present` stage (which holds secrets, per
# tests/test_present.py's own structural guarantee) is intentionally NOT containerized here --
# hosted runners already isolate it, and this image is for LOCAL validation of the one stage
# that genuinely benefits from an extra isolation layer around untrusted upstream code.
#
# Usage (local validation only, never a hosted deployment target):
#   docker build -t repo-presenter-facts .
#   docker run --rm -v "$PWD/.present-work:/tmp/work" -v "$PWD/.present-facts:/tmp/facts" \
#     repo-presenter-facts --repository <owner/name> --ecosystem <ecosystem> \
#     --workdir /tmp/work --facts-dir /tmp/facts
# CORRECTION (2026-11-04, found by comparing this file with the code): an earlier version of this
# comment said the container "never fetches" code and showed `--network=none` for a real run. That
# was wrong. The facts stage itself resolves the default-branch revision (git ls-remote) and clones
# the pinned revision over HTTPS (present.py -> core/git_safety/clone.py), which is why git is
# installed below, so a real run needs network access to the repository host. What this image
# does guarantee, and what CI exercises: it runs as an unprivileged user (UID 10001), bakes in no
# secret, and with NO network the stage FAILS CLOSED (exit code 3, "cannot resolve the
# default-branch revision") rather than producing anything. The `present` stage (which holds
# secrets) is intentionally NOT containerized here -- hosted runners already isolate it.

FROM python:3.13-slim

# The facts stage clones the pinned upstream revision with git (verified missing 2026-11-04: the
# slim base has none, so the stage failed with FileNotFoundError: 'git').
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layered so dependency installation caches independently of source changes.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e . \
    && useradd --create-home --uid 10001 runner
COPY scripts/ ./scripts/
COPY data/ ./data/

USER runner

ENTRYPOINT ["python", "-m", "repo_presenter.present", "--stage", "facts"]
