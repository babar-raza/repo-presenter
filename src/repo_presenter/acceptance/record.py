"""The acceptance contract (TC-013) - one source every reader of "is this candidate accepted"
reads, instead of each caller inventing its own notion of it.

This is a NEW, PARALLEL package. It does not replace, read or write
``data/reviewer_calibration.json`` or ``src/repo_presenter/readme/review/calibration_status.py``:
those stay exactly as they are, frozen at iteration 5 / status ``NOT_PASSED``, per owner ruling
R10 - nothing may ever write ``PASSED`` into that file again
(``test_data_reviewer_calibration_json_is_never_written_passed`` in this card's own test suite,
and ``tests/readme/review/test_calibration_status.py`` in the existing one, both assert this
statically). This module instead defines a NEW, separately committed pair of files -
``data/acceptance_calibration.json`` (per-mechanism-class PASSED certificates) and
``data/acceptance_responsibility.json`` (the matrix of mechanism classes a candidate must clear) -
and reads them with the exact fail-closed discipline ``calibration_status.load_calibration``
uses: a missing file, an unreadable file, or a malformed document is never an exception and never
a silent pass, it is read as "no certificate"/"no matrix", which can never satisfy
``AcceptanceCertificates.complete``. Neither file exists yet on disk as of this card
(``TC-022a``/``TC-022b`` create and populate them later) - every test in this card's own suite
uses local fixtures, never the real paths.

Eight states, append-only, computed by code from an ``AcceptanceRecord``'s explicit fields -
never hand-set by a caller:

  ``generated`` - the floor every record starts at.
  ``sealed`` - the candidate bundle is sealed.
  ``deterministically-validated`` - ``repo_presenter.recertify.Recertification.certified`` for the
    latest seal is ``True`` ("recertify / the blocking checks pass under current code"); this
    module only ACCEPTS that boolean as an input field, it never recomputes it - reuse, not
    reinvention.
  ``provisionally-accepted`` - exactly (a) every mechanism class
    ``data/acceptance_responsibility.json`` lists has an append-only PASSED certificate in
    ``data/acceptance_calibration.json`` (``AcceptanceCertificates.complete``); (b) this
    candidate's own mechanism verdicts all PASS (``AcceptanceRecord.mechanism_verdicts_pass``);
    (c) every per-candidate canary was caught (``AcceptanceRecord.canaries_caught``). No audit
    required.
  ``independently-accepted`` - (a)+(b)+(c) above, PLUS (d) ``audit_passed`` is ``True`` in the
    record AND the record carries a VERIFIED GitHub artifact attestation (``attested=True``,
    produced only by a real ``verify_attestation`` call in ``build_record`` - never hand-set).
  ``publication-ready`` / ``delivered`` / ``live-verified`` - further milestones on top of
    ``independently-accepted`` (an explicit readiness signal; the PR actually opened; the PR
    merged and the upstream README confirmed byte-identical). This card does not own populating
    these preconditions - the hosted writer (``TC-014``) and the seal-path switch (``TC-024``) do
    - it only defines the chain and fails closed on their absence, exactly like the certificate
    chain above.

``mechanism-passing`` is a REPORTING LABEL, never a stored state: ``deterministically-validated``
OR ``provisionally-accepted``. A record in either state, lacking ``audit_passed``/``attested``, is
NEVER classified as ``independently-accepted`` and never satisfies ``PUBLISHABLE_STATES`` -
``test_mechanism_passing_without_audit_never_reaches_independently_accepted`` proves it.

Attestation: ``verify_attestation`` is a pure function around ``gh attestation verify`` (subprocess
call, injectable ``runner``). It returns ``False`` on any non-zero exit, timeout, or missing ``gh``
CLI - unverifiable is never verified. This card's own checks never run a live ``gh`` session; that
live proof belongs to ``TC-014`` and M1's own closeout evidence.

Public entry points:

* ``classify_record(record: AcceptanceRecord) -> AcceptanceState`` - the pure classifier. What a
  test fixture calls directly.
* ``load_certificates(calibration_path=None, responsibility_path=None) -> AcceptanceCertificates``
  - the fail-closed reader of the two new committed files.
* ``build_record(repository, lane, **signals) -> AcceptanceRecord`` - assembles a record from
  whatever per-candidate signals a caller has (sealed, deterministically_validated,
  mechanism_verdicts, canaries, audit_passed, an attestation bundle to verify, the later
  publication/delivery/live-verification flags), merging in the global certificate availability.
  Every signal defaults to the value that fails closed.
* ``classify(repository, lane, **signals) -> AcceptanceState`` -
  ``classify_record(build_record(repository, lane, **signals))``. This is the ONE function later,
  direct supervisor work (not this card - ``ops/**`` is globally denied to every taskcard) wires
  ``ops/checks/portfolio_delivery_count.py``'s acceptance classification and
  ``ops/checks/calibration_status.py``'s ``--file``/``--matrix`` flags to call.

``propose.effect`` gate 3b calls ``classify`` and refuses with ``Refusal.ACCEPTANCE_NOT_CERTIFIED``
unless the result is in ``PUBLISHABLE_STATES`` (``publication-ready`` or later).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "GENERATED",
    "SEALED",
    "DETERMINISTICALLY_VALIDATED",
    "PROVISIONALLY_ACCEPTED",
    "INDEPENDENTLY_ACCEPTED",
    "PUBLICATION_READY",
    "DELIVERED",
    "LIVE_VERIFIED",
    "STATES",
    "MECHANISM_PASSING",
    "PUBLISHABLE_STATES",
    "AcceptanceState",
    "AcceptanceCertificates",
    "AcceptanceRecord",
    "load_certificates",
    "build_record",
    "classify_record",
    "classify",
    "mechanism_passing",
    "verify_attestation",
]

GENERATED = "generated"
SEALED = "sealed"
DETERMINISTICALLY_VALIDATED = "deterministically-validated"
PROVISIONALLY_ACCEPTED = "provisionally-accepted"
INDEPENDENTLY_ACCEPTED = "independently-accepted"
PUBLICATION_READY = "publication-ready"
DELIVERED = "delivered"
LIVE_VERIFIED = "live-verified"

#: Append-only, in reachable order (each later state is reachable only on top of earlier ones -
#: see ``classify_record``).
STATES: tuple[str, ...] = (
    GENERATED,
    SEALED,
    DETERMINISTICALLY_VALIDATED,
    PROVISIONALLY_ACCEPTED,
    INDEPENDENTLY_ACCEPTED,
    PUBLICATION_READY,
    DELIVERED,
    LIVE_VERIFIED,
)

#: A reporting-only label - never a stored state, never returned by ``classify_record``.
MECHANISM_PASSING = "mechanism-passing"

AcceptanceState = Literal[
    "generated",
    "sealed",
    "deterministically-validated",
    "provisionally-accepted",
    "independently-accepted",
    "publication-ready",
    "delivered",
    "live-verified",
]

#: The threshold ``propose.effect`` gate 3b (and anything else gating a write) needs: a candidate
#: counts as ready to publish once it reaches one of these.
PUBLISHABLE_STATES: frozenset[str] = frozenset({PUBLICATION_READY, DELIVERED, LIVE_VERIFIED})

DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "acceptance_calibration.json"
)
DEFAULT_RESPONSIBILITY_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "acceptance_responsibility.json"
)


@dataclass(frozen=True)
class AcceptanceCertificates:
    """The two NEW committed files, read fail-closed. ``required_mechanisms`` is ``None`` only
    when the responsibility matrix itself could not be read or parsed - a missing matrix is never
    read as an empty, vacuously-satisfied set of requirements."""

    required_mechanisms: frozenset[str] | None
    certified_mechanisms: frozenset[str] = frozenset()
    problem: str = ""

    @property
    def complete(self) -> bool:
        """Every required mechanism class has a PASSED certificate. ``False`` whenever the
        matrix itself is unavailable - never vacuously ``True`` on a missing matrix."""
        if self.required_mechanisms is None:
            return False
        return self.required_mechanisms.issubset(self.certified_mechanisms)


def _no_certificates(problem: str) -> AcceptanceCertificates:
    return AcceptanceCertificates(required_mechanisms=None, problem=problem)


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    """``(document, problem)`` - ``document`` is ``None`` on any doubt at all; never raises."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return None, f"cannot read {path.name}: {error}"
    try:
        document = json.loads(text)
    except ValueError as error:
        return None, f"{path.name} is not valid JSON: {error}"
    if not isinstance(document, dict):
        return None, f"{path.name} is not a JSON object"
    return document, ""


def load_certificates(
    calibration_path: Path | None = None,
    responsibility_path: Path | None = None,
) -> AcceptanceCertificates:
    """Read ``data/acceptance_responsibility.json`` (the mechanism-class matrix) and
    ``data/acceptance_calibration.json`` (the append-only PASSED certificates) fail-closed. A
    missing/unreadable/malformed responsibility matrix makes ``complete`` unconditionally
    ``False`` (``required_mechanisms is None``); a missing/unreadable/malformed calibration file
    (with a real matrix) is read as zero certificates, never as "trust everything"."""
    responsibility_target = (
        DEFAULT_RESPONSIBILITY_PATH if responsibility_path is None else responsibility_path
    )
    calibration_target = (
        DEFAULT_CALIBRATION_PATH if calibration_path is None else calibration_path
    )

    matrix_document, matrix_problem = _read_json_object(responsibility_target)
    if matrix_document is None:
        return _no_certificates(
            f"acceptance responsibility matrix unavailable: {matrix_problem}"
        )
    classes = matrix_document.get("mechanism_classes")
    if not isinstance(classes, list) or not all(isinstance(item, str) for item in classes):
        return _no_certificates(
            f"{responsibility_target.name}'s mechanism_classes must be a list of strings"
        )
    required = frozenset(classes)

    calibration_document, calibration_problem = _read_json_object(calibration_target)
    if calibration_document is None:
        return AcceptanceCertificates(
            required_mechanisms=required,
            certified_mechanisms=frozenset(),
            problem=f"acceptance calibration file unavailable: {calibration_problem}",
        )
    certificates = calibration_document.get("certificates")
    if not isinstance(certificates, list):
        return AcceptanceCertificates(
            required_mechanisms=required,
            certified_mechanisms=frozenset(),
            problem=f"{calibration_target.name}'s certificates must be a list",
        )
    certified: set[str] = set()
    for entry in certificates:
        if not isinstance(entry, dict):
            continue
        mechanism_class = entry.get("mechanism_class")
        if isinstance(mechanism_class, str) and entry.get("status") == "PASSED":
            certified.add(mechanism_class)
    return AcceptanceCertificates(
        required_mechanisms=required, certified_mechanisms=frozenset(certified)
    )


@dataclass(frozen=True)
class AcceptanceRecord:
    """The raw, explicit signals ``classify_record`` folds into one ``AcceptanceState``. Every
    field defaults to the value that fails closed: an ``AcceptanceRecord`` built with no further
    information classifies as ``generated`` and nothing higher - exactly like a missing
    calibration file reads as ``NOT_PASSED`` in ``readme.review.calibration_status``, never an
    exception, never a silent pass."""

    repository: str
    lane: str
    sealed: bool = False
    #: ``repo_presenter.recertify.Recertification.certified`` for the latest seal, reused as-is.
    deterministically_validated: bool = False
    #: Per mechanism class -> whether THIS candidate's own verdict for that class is PASS.
    mechanism_verdicts: Mapping[str, bool] = field(default_factory=dict)
    #: Per canary id -> whether it was caught. Vacuously all-caught when empty: no canary run
    #: means nothing was missed, but this module never invents a canary that was never run.
    canaries: Mapping[str, bool] = field(default_factory=dict)
    certificates: AcceptanceCertificates = field(
        default_factory=lambda: _no_certificates("no certificates loaded for this record")
    )
    audit_passed: bool = False
    #: Set ``True`` only by ``build_record`` after a real, successful ``verify_attestation`` call
    #: - never hand-set ``True`` by a caller that has not actually verified one.
    attested: bool = False
    publication_ready_signal: bool = False
    pr_opened: bool = False
    pr_merged: bool = False
    readme_matches_upstream: bool = False

    @property
    def mechanism_verdicts_pass(self) -> bool:
        """(b): the candidate's own mechanism verdicts all PASS. Empty is never vacuously
        passing - no recorded verdict is not a passed one."""
        return bool(self.mechanism_verdicts) and all(self.mechanism_verdicts.values())

    @property
    def canaries_caught(self) -> bool:
        """(c): every per-candidate canary was caught. Vacuously ``True`` on no canaries."""
        return all(self.canaries.values())

    @property
    def provisional_criteria_met(self) -> bool:
        """(a)+(b)+(c): every required mechanism class certified, this candidate's own mechanism
        verdicts all pass, every per-candidate canary caught - the whole of
        ``provisionally-accepted``, and the prerequisite for ``independently-accepted``."""
        return (
            self.certificates.complete
            and self.mechanism_verdicts_pass
            and self.canaries_caught
        )


def classify_record(record: AcceptanceRecord) -> AcceptanceState:
    """The pure fold from an ``AcceptanceRecord``'s explicit signals to one ``AcceptanceState``.
    Each later state is reachable only on top of the one before it in this chain - never looks at
    anything but the record's own fields, and a doubtful/absent field was already turned into the
    failing default by whoever built the record (``build_record`` or a test fixture)."""
    state: AcceptanceState = GENERATED
    if record.sealed:
        state = SEALED
    if record.deterministically_validated:
        state = DETERMINISTICALLY_VALIDATED
    if record.provisional_criteria_met:
        state = PROVISIONALLY_ACCEPTED
        if record.audit_passed and record.attested:
            state = INDEPENDENTLY_ACCEPTED
            if record.publication_ready_signal:
                state = PUBLICATION_READY
                if record.pr_opened:
                    state = DELIVERED
                    if record.pr_merged and record.readme_matches_upstream:
                        state = LIVE_VERIFIED
    return state


def mechanism_passing(state: AcceptanceState) -> bool:
    """The ``mechanism-passing`` REPORTING LABEL: ``deterministically-validated`` OR
    ``provisionally-accepted``. Never ``True`` for ``independently-accepted`` or higher - those
    states already imply more than mechanism-passing, they do not need the label."""
    return state in (DETERMINISTICALLY_VALIDATED, PROVISIONALLY_ACCEPTED)


GhRunner = Callable[..., "subprocess.CompletedProcess[bytes]"]


def _run_gh(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
    return subprocess.run(args, capture_output=True, timeout=120, check=False)


def verify_attestation(
    artifact_path: str | Path,
    expected_workflow: str,
    expected_ref: str = "refs/heads/main",
    *,
    runner: GhRunner = _run_gh,
) -> bool:
    """``True`` only when ``gh attestation verify`` exits ``0`` against ``artifact_path``, signed
    by exactly ``expected_workflow`` on ``expected_ref`` (``--signer-workflow
    <expected_workflow>@<expected_ref>``). Any non-zero exit, a timeout, or a missing ``gh`` CLI
    is ``False`` - unverifiable is never verified. Pure: ``runner`` defaults to a real
    ``subprocess.run`` call but a test injects a fake one; nothing here is run live by this
    card's own checks (no network, no ``gh`` session required)."""
    signer_workflow = f"{expected_workflow}@{expected_ref}"
    try:
        result = runner(
            [
                "gh",
                "attestation",
                "verify",
                str(artifact_path),
                "--signer-workflow",
                signer_workflow,
            ]
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def build_record(
    repository: str,
    lane: str,
    *,
    sealed: bool = False,
    deterministically_validated: bool = False,
    mechanism_verdicts: Mapping[str, bool] | None = None,
    canaries: Mapping[str, bool] | None = None,
    audit_passed: bool = False,
    attestation_path: str | Path | None = None,
    expected_workflow: str | None = None,
    expected_ref: str = "refs/heads/main",
    publication_ready_signal: bool = False,
    pr_opened: bool = False,
    pr_merged: bool = False,
    readme_matches_upstream: bool = False,
    calibration_path: Path | None = None,
    responsibility_path: Path | None = None,
    gh_runner: GhRunner = _run_gh,
) -> AcceptanceRecord:
    """Assemble an ``AcceptanceRecord`` from whatever per-candidate signals the caller has,
    merging in the global certificate availability (``load_certificates``) and, only when an
    attestation bundle is actually given, a real ``verify_attestation`` call. ``attested`` is
    ``True`` only when BOTH ``attestation_path`` and ``expected_workflow`` are given AND the
    verification call itself returns ``True`` - absent either, this never claims a verification
    that was never made."""
    certificates = load_certificates(calibration_path, responsibility_path)
    attested = False
    if attestation_path is not None and expected_workflow is not None:
        attested = verify_attestation(
            attestation_path, expected_workflow, expected_ref, runner=gh_runner
        )
    return AcceptanceRecord(
        repository=repository,
        lane=lane,
        sealed=sealed,
        deterministically_validated=deterministically_validated,
        mechanism_verdicts=dict(mechanism_verdicts or {}),
        canaries=dict(canaries or {}),
        certificates=certificates,
        audit_passed=audit_passed,
        attested=attested,
        publication_ready_signal=publication_ready_signal,
        pr_opened=pr_opened,
        pr_merged=pr_merged,
        readme_matches_upstream=readme_matches_upstream,
    )


def classify(repository: str, lane: str, **signals: Any) -> AcceptanceState:
    """The ONE public entry point later glue code calls -
    ``classify_record(build_record(repository, lane, **signals))``. See ``build_record`` for
    every keyword this accepts. Intended callers, as direct supervisor work after this card is
    ACCEPTED (not this card's own job - ``ops/**`` is globally denied to every taskcard):
    ``ops/checks/portfolio_delivery_count.py``'s acceptance classification and
    ``ops/checks/calibration_status.py``'s ``--file``/``--matrix`` flags."""
    return classify_record(build_record(repository, lane, **signals))
