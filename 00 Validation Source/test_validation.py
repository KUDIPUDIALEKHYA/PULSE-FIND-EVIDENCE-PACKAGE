import math

from validation_engine import (
    Candidate,
    EvidenceState,
    Observation,
    Packet,
    PacketValidator,
    ValidationConfig,
    compare_modalities,
    decay_factor,
    decayed_score,
)


def test_valid_packet_is_accepted():
    packet = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=1,
        timestamp=100.0,
        payload=b"thermal:0.8",
    )

    validator = PacketValidator()

    accepted, reason = validator.validate(
        packet,
        current_time=105.0,
    )

    assert accepted is True
    assert reason == "ACCEPTED"


def test_bad_crc_is_rejected():
    packet = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=1,
        timestamp=100.0,
        payload=b"thermal:0.8",
    )

    corrupted = Packet(
        node_id=packet.node_id,
        zone_id=packet.zone_id,
        sequence=packet.sequence,
        timestamp=packet.timestamp,
        payload=packet.payload,
        crc=packet.crc + 1,
    )

    validator = PacketValidator()

    accepted, reason = validator.validate(
        corrupted,
        current_time=105.0,
    )

    assert accepted is False
    assert reason == "CRC_FAILURE"


def test_future_timestamp_is_rejected():
    packet = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=100000,
        timestamp=200.0,
        payload=b"thermal:0.8",
    )

    validator = PacketValidator()

    accepted, reason = validator.validate(
        packet,
        current_time=100.0,
    )

    assert accepted is False
    assert reason == "FUTURE_TIMESTAMP"

    # Rejected packet must NOT poison sequence state.
    assert validator.highest_sequence == {}


def test_stale_packet_is_rejected():
    packet = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=1,
        timestamp=0.0,
        payload=b"thermal:0.8",
    )

    validator = PacketValidator()

    accepted, reason = validator.validate(
        packet,
        current_time=100.0,
    )

    assert accepted is False
    assert reason == "STALE_PACKET"


def test_duplicate_packet_is_rejected():
    validator = PacketValidator()

    first = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=5,
        timestamp=100.0,
        payload=b"audio:0.7",
    )

    second = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=5,
        timestamp=101.0,
        payload=b"audio:0.7",
    )

    assert validator.validate(
        first,
        current_time=105.0,
    ) == (True, "ACCEPTED")

    assert validator.validate(
        second,
        current_time=106.0,
    ) == (False, "DUPLICATE_OR_REPLAY")


def test_replay_with_lower_sequence_is_rejected():
    validator = PacketValidator()

    first = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=10,
        timestamp=100.0,
        payload=b"data",
    )

    replay = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=9,
        timestamp=101.0,
        payload=b"data",
    )

    assert validator.validate(
        first,
        current_time=105.0,
    ) == (True, "ACCEPTED")

    assert validator.validate(
        replay,
        current_time=106.0,
    ) == (False, "DUPLICATE_OR_REPLAY")


def test_sequence_state_is_per_node_and_zone():
    validator = PacketValidator()

    packet_a = Packet.create(
        node_id="N01",
        zone_id="Z01",
        sequence=1,
        timestamp=100.0,
        payload=b"a",
    )

    packet_b = Packet.create(
        node_id="N02",
        zone_id="Z01",
        sequence=1,
        timestamp=100.0,
        payload=b"b",
    )

    assert validator.validate(
        packet_a,
        current_time=101.0,
    ) == (True, "ACCEPTED")

    assert validator.validate(
        packet_b,
        current_time=101.0,
    ) == (True, "ACCEPTED")


def test_decay_half_life_is_one_half():
    config = ValidationConfig()

    factor = decay_factor(
        config.half_life_seconds,
        config.half_life_seconds,
    )

    assert math.isclose(
        factor,
        0.5,
        rel_tol=1e-9,
    )


def test_decay_at_zero_age_is_one():
    assert math.isclose(
        decay_factor(0.0, 30.0),
        1.0,
        rel_tol=1e-9,
    )


def test_decayed_score():
    result = decayed_score(
        score=1.0,
        observation_time=0.0,
        current_time=30.0,
        half_life_seconds=30.0,
    )

    assert math.isclose(
        result,
        0.5,
        rel_tol=1e-9,
    )


def test_invalid_nan_score_is_rejected():
    candidate = Candidate("C01")

    observation = Observation(
        modality="thermal",
        score=float("nan"),
        timestamp=100.0,
    )

    candidate.add_observation(
        observation,
        current_time=101.0,
        config=ValidationConfig(),
    )

    assert candidate.evidence == {}


def test_invalid_infinite_score_is_rejected():
    candidate = Candidate("C01")

    observation = Observation(
        modality="thermal",
        score=float("inf"),
        timestamp=100.0,
    )

    candidate.add_observation(
        observation,
        current_time=101.0,
        config=ValidationConfig(),
    )

    assert candidate.evidence == {}


def test_uncovered_negative_observation_does_not_count():
    candidate = Candidate("C01")

    observation = Observation(
        modality="thermal",
        score=-1.0,
        timestamp=100.0,
        covers_candidate=False,
    )

    candidate.add_observation(
        observation,
        current_time=101.0,
        config=ValidationConfig(),
    )

    assert candidate.evidence == {}


def test_failed_sensor_contributes_zero_evidence():
    candidate = Candidate("C01")

    observation = Observation(
        modality="thermal",
        score=2.0,
        timestamp=100.0,
        sensor_healthy=False,
    )

    candidate.add_observation(
        observation,
        current_time=101.0,
        config=ValidationConfig(),
    )

    assert candidate.evidence == {}


def test_team_activity_is_not_survivor_evidence():
    candidate = Candidate("C01")

    observation = Observation(
        modality="thermal",
        score=2.0,
        timestamp=100.0,
        team_active=True,
    )

    candidate.add_observation(
        observation,
        current_time=101.0,
        config=ValidationConfig(),
    )

    assert candidate.evidence == {}


def test_single_modality_goes_to_verify():
    candidate = Candidate("C01")
    config = ValidationConfig()

    candidate.add_observation(
        Observation(
            modality="thermal",
            score=1.0,
            timestamp=100.0,
        ),
        current_time=100.0,
        config=config,
    )

    state, _ = candidate.classify(
        current_time=100.0,
        config=config,
    )

    assert state == EvidenceState.VERIFY


def test_two_independent_modalities_can_reach_high_priority():
    candidate = Candidate("C01")
    config = ValidationConfig()

    candidate.add_observation(
        Observation(
            modality="thermal",
            score=1.0,
            timestamp=100.0,
        ),
        current_time=100.0,
        config=config,
    )

    candidate.add_observation(
        Observation(
            modality="audio",
            score=1.0,
            timestamp=100.0,
        ),
        current_time=100.0,
        config=config,
    )

    state, reason = candidate.classify(
        current_time=100.0,
        config=config,
    )

    assert state == EvidenceState.HIGH_PRIORITY
    assert "Independent modalities agree" in reason


def test_no_observation_is_not_observed():
    candidate = Candidate("C01")
    config = ValidationConfig()

    state, reason = candidate.classify(
        current_time=100.0,
        config=config,
    )

    assert state == EvidenceState.NOT_OBSERVED
    assert "No usable sensor evidence" in reason


def test_modality_agreement():
    observations = [
        Observation(
            modality="thermal",
            score=1.0,
            timestamp=100.0,
        ),
        Observation(
            modality="audio",
            score=1.0,
            timestamp=100.0,
        ),
    ]

    assert compare_modalities(observations) == "AGREEMENT"


def test_insufficient_modalities():
    observations = [
        Observation(
            modality="thermal",
            score=1.0,
            timestamp=100.0,
        )
    ]

    assert compare_modalities(observations) == "INSUFFICIENT_DATA"


def test_evidence_is_capped_per_modality():
    candidate = Candidate("C01")
    config = ValidationConfig(
        evidence_cap=2.5,
    )

    for i in range(10):
        candidate.add_observation(
            Observation(
                modality="thermal",
                score=1.0,
                timestamp=100.0 + i,
            ),
            current_time=100.0 + i,
            config=config,
        )

    scores = candidate.modality_scores(
        current_time=109.0,
        config=config,
    )

    assert scores["thermal"] <= 2.5
