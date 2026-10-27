"""Persist and read ``review_verdict.json`` (plan D8).

Schema 2 records the reviewer's own verdict, the prompt version, the model served and the request
and reply hashes, and for every finding its ``claim_kind``, ``status`` and clearance proof, so an
ACCEPT that rests on a REJECT being cleared is auditable from the file alone. Schema 1 (the
deterministic-only reviewer) still reads: its ``kind: "deterministic"`` findings become
``source: "deterministic"`` and its ``refuted_by.evidence`` becomes ``evidence``. A schema-1
``kind: "judgment"`` finding fails the read, because schema 2 has no annotate-only tier and silently
reading it as either blocking or ignorable would change a recorded verdict.

Reading fails closed on any shape it cannot rebuild, and on a stored verdict that does not equal
the fold of the stored findings (``ReviewVerdict.__post_init__``). A reviewer-logic mismatch is
the caller's currency question, not a parse error.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import REVIEWER_LOGIC_VERSION, ReviewVerdict

SCHEMA_VERSION = 2


class ReviewVerdictError(ValueError):
    """A persisted review-verdict artifact does not have the shape this module can read back."""


def write_review_verdict(verdict: ReviewVerdict, path: Path) -> str:
    """Persist one candidate's verdict as the durable, sealable artifact. Returns the sha256 of
    the bytes written."""
    document = {
        "schema_version": SCHEMA_VERSION,
        "reviewer_logic_version": REVIEWER_LOGIC_VERSION,
        "verdict": verdict.verdict,
        "model_verdict": verdict.model_verdict,
        "retryable": verdict.retryable,
        "reason": verdict.fold.reason,
        "prompt_version": verdict.prompt_version,
        "model_served": verdict.model_served,
        "request_sha256": verdict.request_sha256,
        "reply_sha256": verdict.reply_sha256,
        "findings": [finding.to_record() for finding in verdict.findings],
    }
    data = (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _v1_finding(path: Path, raw: dict[str, Any]) -> Finding:
    kind = raw.get("kind")
    if kind == "judgment":
        raise ReviewVerdictError(
            f"{path}: a schema-1 judgment finding cannot be read: schema 2 has no annotate-only tier"
        )
    if kind != "deterministic":
        raise ReviewVerdictError(f"{path}: unknown finding kind {kind!r}")
    refutation = raw.get("refuted_by")
    if not isinstance(refutation, dict):
        raise ReviewVerdictError(
            f"{path}: a schema-1 deterministic finding carries no refutation"
        )
    return Finding(
        rule=raw["rule"],
        source="deterministic",
        message=raw["message"],
        quote=raw.get("quote", ""),
        evidence=refutation["evidence"],
    )


def load_review_verdict(path: Path) -> ReviewVerdict:
    """Read back a ``write_review_verdict`` artifact (schema 2) or a schema-1 one."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewVerdictError(f"{path}: cannot read/parse as JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReviewVerdictError(f"{path}: top level must be a JSON object")
    try:
        verdict = payload["verdict"]
        raw_findings = payload["findings"]
    except KeyError as exc:
        raise ReviewVerdictError(f"{path}: missing required field {exc}") from exc
    if verdict not in ("ACCEPT", "REJECT"):
        raise ReviewVerdictError(f"{path}: unknown verdict {verdict!r}")
    if not isinstance(raw_findings, list):
        raise ReviewVerdictError(f"{path}: findings must be a list")
    schema = payload.get("schema_version", 1)
    if schema not in (1, SCHEMA_VERSION):
        raise ReviewVerdictError(f"{path}: unknown schema_version {schema!r}")
    findings: list[Finding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            raise ReviewVerdictError(f"{path}: each finding must be an object")
        try:
            findings.append(
                _v1_finding(path, raw) if schema == 1 else Finding.from_record(raw)
            )
        except ReviewVerdictError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ReviewVerdictError(f"{path}: unreadable finding: {exc}") from exc
    meta: dict[str, Any] = (
        {}
        if schema == 1
        else {
            key: payload.get(key)
            for key in (
                "model_verdict",
                "prompt_version",
                "model_served",
                "request_sha256",
                "reply_sha256",
            )
        }
    )
    try:
        return ReviewVerdict(verdict=verdict, findings=tuple(findings), **meta)
    except ValueError as exc:
        raise ReviewVerdictError(f"{path}: {exc}") from exc
