"""TC-013: the eight-state acceptance chain, folded purely from an ``AcceptanceRecord``'s own
fields - REQ-ACCEPT-001/002. Every assertion that must tell `independently-accepted` apart from
`provisionally-accepted` compares against a hard-coded literal string, not the imported constant,
so a mutation that collapses the two constants to the same string value (this card's own
``negative_control``) cannot slip through by having both sides of the comparison mutated
together."""

from __future__ import annotations

from repo_presenter.acceptance.record import (
    AcceptanceCertificates,
    AcceptanceRecord,
    DELIVERED,
    DETERMINISTICALLY_VALIDATED,
    GENERATED,
    INDEPENDENTLY_ACCEPTED,
    LIVE_VERIFIED,
    MECHANISM_PASSING,
    PROVISIONALLY_ACCEPTED,
    PUBLICATION_READY,
    PUBLISHABLE_STATES,
    SEALED,
    STATES,
    classify_record,
    mechanism_passing,
)

COMPLETE_CERTIFICATES = AcceptanceCertificates(
    required_mechanisms=frozenset({"lane_r_pipeline", "reviewer_calibration"}),
    certified_mechanisms=frozenset({"lane_r_pipeline", "reviewer_calibration"}),
)
INCOMPLETE_CERTIFICATES = AcceptanceCertificates(
    required_mechanisms=frozenset({"lane_r_pipeline", "reviewer_calibration"}),
    certified_mechanisms=frozenset({"lane_r_pipeline"}),
)
NO_MATRIX_CERTIFICATES = AcceptanceCertificates(required_mechanisms=None)


def _record(**overrides: object) -> AcceptanceRecord:
    fields: dict[str, object] = {
        "repository": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
        "lane": "R",
    }
    fields.update(overrides)
    return AcceptanceRecord(**fields)  # type: ignore[arg-type]


# --- the state constants themselves are pinned literals -----------------------------------------


def test_the_eight_states_are_exactly_these_literal_strings() -> None:
    """Pinned against hard-coded literals, not against each other - this is what the card's own
    negative control (collapsing INDEPENDENTLY_ACCEPTED's value into PROVISIONALLY_ACCEPTED's)
    must break."""
    assert GENERATED == "generated"
    assert SEALED == "sealed"
    assert DETERMINISTICALLY_VALIDATED == "deterministically-validated"
    assert PROVISIONALLY_ACCEPTED == "provisionally-accepted"
    assert INDEPENDENTLY_ACCEPTED == "independently-accepted"
    assert PUBLICATION_READY == "publication-ready"
    assert DELIVERED == "delivered"
    assert LIVE_VERIFIED == "live-verified"
    assert PROVISIONALLY_ACCEPTED != INDEPENDENTLY_ACCEPTED
    assert STATES == (
        "generated",
        "sealed",
        "deterministically-validated",
        "provisionally-accepted",
        "independently-accepted",
        "publication-ready",
        "delivered",
        "live-verified",
    )


# --- the floor and the independent "sealed"/"deterministically-validated" flags -----------------


def test_a_bare_record_classifies_as_generated() -> None:
    assert classify_record(_record()) == "generated"


def test_sealed_alone_reaches_sealed() -> None:
    assert classify_record(_record(sealed=True)) == "sealed"


def test_deterministically_validated_does_not_need_sealed() -> None:
    """Reuses ``recertify.Recertification.certified`` as an input boolean, not recomputed, and
    is independent of the ``sealed`` flag - the card states these as separate conditions."""
    record = _record(sealed=False, deterministically_validated=True)
    assert classify_record(record) == "deterministically-validated"


# --- provisionally-accepted: exactly (a) + (b) + (c) ---------------------------------------------


def test_provisionally_accepted_needs_all_three_of_a_b_c() -> None:
    base = dict(
        certificates=COMPLETE_CERTIFICATES,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"canary-1": True, "canary-2": True},
    )
    assert classify_record(_record(**base)) == "provisionally-accepted"

    # (a) missing: the responsibility matrix itself is unavailable.
    missing_matrix = dict(base, certificates=NO_MATRIX_CERTIFICATES)
    assert classify_record(_record(**missing_matrix)) != "provisionally-accepted"

    # (a) incomplete: not every required mechanism class has a certificate.
    incomplete = dict(base, certificates=INCOMPLETE_CERTIFICATES)
    assert classify_record(_record(**incomplete)) != "provisionally-accepted"

    # (b) a mechanism verdict fails.
    failing_verdict = dict(
        base, mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": False}
    )
    assert classify_record(_record(**failing_verdict)) != "provisionally-accepted"

    # (b) no verdicts recorded at all - never vacuously passing.
    no_verdicts = dict(base, mechanism_verdicts={})
    assert classify_record(_record(**no_verdicts)) != "provisionally-accepted"

    # (c) a canary was missed.
    missed_canary = dict(base, canaries={"canary-1": True, "canary-2": False})
    assert classify_record(_record(**missed_canary)) != "provisionally-accepted"


def test_no_canaries_at_all_is_vacuously_caught() -> None:
    """Documented choice: no canary registered for a candidate means nothing was missed."""
    record = _record(
        certificates=COMPLETE_CERTIFICATES,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={},
    )
    assert classify_record(record) == "provisionally-accepted"


# --- independently-accepted: (a)+(b)+(c) PLUS (d) audit_passed AND attested ---------------------


def _provisional_fields() -> dict[str, object]:
    return dict(
        certificates=COMPLETE_CERTIFICATES,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"canary-1": True},
    )


def test_independently_accepted_needs_audit_passed_and_attested() -> None:
    both = _record(**_provisional_fields(), audit_passed=True, attested=True)
    assert classify_record(both) == "independently-accepted"

    audit_only = _record(**_provisional_fields(), audit_passed=True, attested=False)
    assert classify_record(audit_only) == "provisionally-accepted"
    assert classify_record(audit_only) != "independently-accepted"

    attested_only = _record(**_provisional_fields(), audit_passed=False, attested=True)
    assert classify_record(attested_only) == "provisionally-accepted"
    assert classify_record(attested_only) != "independently-accepted"


def test_independently_accepted_still_needs_a_b_c() -> None:
    """audit_passed and attested alone, without the provisional criteria, reach nothing above the
    deterministic floor - (d) is additive to (a)+(b)+(c), never a substitute for it."""
    record = _record(audit_passed=True, attested=True)
    result = classify_record(record)
    assert result != "independently-accepted"
    assert result != "provisionally-accepted"


# --- mechanism-passing: a reporting label only, never independently-accepted or higher ----------


def test_mechanism_passing_reporting_label() -> None:
    assert mechanism_passing("deterministically-validated") is True
    assert mechanism_passing("provisionally-accepted") is True
    assert mechanism_passing("generated") is False
    assert mechanism_passing("sealed") is False
    assert mechanism_passing("independently-accepted") is False
    assert mechanism_passing("publication-ready") is False
    assert MECHANISM_PASSING == "mechanism-passing"
    assert MECHANISM_PASSING not in STATES


def test_mechanism_passing_without_audit_never_reaches_independently_accepted_or_the_publish_gate() -> (
    None
):
    """The card's own requirement, verbatim: a record in deterministically-validated or
    provisionally-accepted, lacking audit_passed, is NEVER independently-accepted and never
    satisfies the publish gate."""
    deterministic_only = _record(deterministically_validated=True)
    provisional_only = _record(**_provisional_fields())
    for record in (deterministic_only, provisional_only):
        state = classify_record(record)
        assert mechanism_passing(state) is True
        assert state != "independently-accepted"
        assert state not in PUBLISHABLE_STATES


# --- publication-ready / delivered / live-verified: further milestones -------------------------


def _independently_accepted_fields() -> dict[str, object]:
    return dict(**_provisional_fields(), audit_passed=True, attested=True)


def test_publication_ready_delivered_live_verified_chain() -> None:
    independent = _record(**_independently_accepted_fields())
    assert classify_record(independent) == "independently-accepted"
    assert classify_record(independent) not in PUBLISHABLE_STATES

    ready = _record(**_independently_accepted_fields(), publication_ready_signal=True)
    assert classify_record(ready) == "publication-ready"
    assert classify_record(ready) in PUBLISHABLE_STATES

    delivered = _record(
        **_independently_accepted_fields(), publication_ready_signal=True, pr_opened=True
    )
    assert classify_record(delivered) == "delivered"

    live_verified = _record(
        **_independently_accepted_fields(),
        publication_ready_signal=True,
        pr_opened=True,
        pr_merged=True,
        readme_matches_upstream=True,
    )
    assert classify_record(live_verified) == "live-verified"

    # pr_merged without a confirmed README match never reaches live-verified.
    merged_but_unverified = _record(
        **_independently_accepted_fields(),
        publication_ready_signal=True,
        pr_opened=True,
        pr_merged=True,
        readme_matches_upstream=False,
    )
    assert classify_record(merged_but_unverified) == "delivered"


def test_delivered_requires_publication_ready_first() -> None:
    """pr_opened alone, without the independently-accepted + publication_ready_signal chain
    beneath it, never reaches delivered."""
    record = _record(**_provisional_fields(), pr_opened=True)
    assert classify_record(record) not in ("delivered", "publication-ready", "live-verified")
