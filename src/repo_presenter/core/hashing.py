"""Canonical text hashing: one SHA-256 for one text regardless of its line endings.

Ported (REUSE, verbatim) from the old repository-presenter project's ``core/hashing.py`` per
migration/reuse-manifest.yaml ("readme/composition/" entry): line endings are normalised to LF
before hashing so a manifest or a rendered document hashes the same on every platform.
"""

from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
