"""TC-009a: verify one freshly minted GitHub App installation token and write the execution proof.

Owner authorization: docs/DECISION_LOG.md, 2026-11-05, ``OWNER-AUTH-2026-11-05-TC009A-ONE-MINT`` --
exactly one mint, no upstream write. Run only by ``.github/workflows/tc-009a-mint-proof.yml``, in the
same job as the mint (a reusable workflow cannot hand a token out: GitHub drops job outputs that hold
a secret). Reads the token from ``GH_APP_INSTALLATION_TOKEN``, verifies it with
``token_provenance.verify_installation_token`` (an installation token whose reach is exactly the
target repository), and writes ``mint_proof.json``. The token itself is never printed or written.

    python scripts/mint_proof.py --repository owner/name --out <proof.json> [--run-id N]

Exit 0 only when the proof records ``minted`` and ``verified_via_token_provenance`` both true.
A proof file that already exists is never overwritten: one authorized mint, one proof.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.github.token_provenance import (
    APP_INSTALLATION_TOKEN_ENV_VAR,
    INSTALLATION_TOKEN_PREFIX,
    verify_installation_token,
)

AUTHORIZATION_REF = "OWNER-AUTH-2026-11-05-TC009A-ONE-MINT"


def build_proof(repository: str, token: str, *, run_id: str, verify=verify_installation_token):
    """The proof record for ``token``; never contains the token or any part of it."""
    minted = token.startswith(INSTALLATION_TOKEN_PREFIX)
    decision = verify(repository, token) if minted else None
    verified = bool(decision is not None and decision.ok)
    return {
        "card": "TC-009a",
        "authorization_ref": AUTHORIZATION_REF,
        "repository": repository,
        "minted": minted,
        "verified_via_token_provenance": verified,
        "verification_detail": "" if verified or decision is None else str(decision.reason),
        "run_id": run_id,
        "recorded_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "upstream_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    args = parser.parse_args(argv)
    if args.out.exists():
        print(f"refused: {args.out} already exists -- one authorized mint, one proof")
        return 1
    token = os.environ.get(APP_INSTALLATION_TOKEN_ENV_VAR, "")
    if not token:
        print(f"refused: {APP_INSTALLATION_TOKEN_ENV_VAR} is empty -- the mint step produced nothing")
        return 1
    proof = build_proof(args.repository, token, run_id=str(args.run_id))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))
    return 0 if proof["minted"] and proof["verified_via_token_provenance"] else 1


if __name__ == "__main__":
    sys.exit(main())
