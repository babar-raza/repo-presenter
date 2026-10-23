"""Classify license text to an SPDX identifier.

Narrow slice (REUSE, verbatim) of the old repository-presenter project's ``components/readme/
evidence/facts/license.py`` -- only ``classify_license_text`` (the pure text classifier
``readme/validation/claims.py``'s rule (e) needs), not that module's own extraction-time
``license_facts``/``settle_declared_license``/``classify_declaration`` functions, which build
license facts from a cloned repository's files -- a different, not-yet-evaluated concern this
repository's own per-ecosystem extractors (``extractors/platforms/python.py`` and siblings)
currently handle their own way. Porting only the slice one caller actually needs follows this
repository's own established narrow-slice precedent (``fence_scan.py``, ``text_gate.py``).
"""

from __future__ import annotations

import re

_CLASSIFIERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmit license\b", re.IGNORECASE), "MIT"),
    (re.compile(r"\bapache license\b.*\bversion 2\.0\b", re.IGNORECASE | re.DOTALL), "Apache-2.0"),
    (
        re.compile(r"\bgnu general public license\b.*\bversion 3\b", re.IGNORECASE | re.DOTALL),
        "GPL-3.0",
    ),
    (re.compile(r"\bbsd 3-clause\b", re.IGNORECASE), "BSD-3-Clause"),
    (re.compile(r"\bbsd 2-clause\b", re.IGNORECASE), "BSD-2-Clause"),
    (re.compile(r"\bisc license\b", re.IGNORECASE), "ISC"),
    (re.compile(r"\bmozilla public license\b", re.IGNORECASE), "MPL-2.0"),
)

KNOWN_IDENTIFIERS: frozenset[str] = frozenset(spdx_id for _, spdx_id in _CLASSIFIERS)


def classify_license_text(text: str) -> str | None:
    """Return the SPDX identifier the license text states, or ``None`` if unrecognized."""
    for pattern, spdx_id in _CLASSIFIERS:
        if pattern.search(text):
            return spdx_id
    return None
