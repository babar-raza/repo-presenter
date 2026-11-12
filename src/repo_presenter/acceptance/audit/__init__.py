"""TC-014: the pure, offline, unit-testable logic of the independent-audit mechanism (M9).

This package builds three independent pieces of pure logic the M9 audit protocol
(``docs/design/2026-11-06-acceptance-redesign.md`` section 4.3) needs, each its own module:

* ``seed`` - blind-inject class A/D/D9/D14/D15 defects (or a clean control) into a copy of a
  sealed candidate's rendered README, recording a structured manifest the auditor never sees.
* ``score`` - pure arithmetic over completed audit findings plus a decrypted seed manifest:
  seeded recall, false-flag rate, defective-accepted rate.
* ``attest`` - verify a GitHub artifact attestation (``gh attestation verify``) for the audit
  writer's own output, fixture/mocked-subprocess only.

ACCEPTED here means this LOGIC is correct and unit-tested offline - it does NOT mean the M9 audit
mechanism is live. The hosted seeder/scorer/writer workflows that call this logic for real, against
a real GitHub Environment key and real GitHub attestations, are separate, later work gated on two
open owner actions this card cannot take itself: (1) a GitHub Environment restricted to the main
branch holding a provider/audit-seed secret key, and (3) CODEOWNERS review on this package's own
code paths. Do not read this package's tests passing as "the audit mechanism is operational."
"""

from __future__ import annotations

from repo_presenter.acceptance.audit import attest, score, seed

__all__ = ["attest", "score", "seed"]
