"""
PULSEFIND Validation Engine
---------------------------

Software-level reference implementation for validating core
PULSEFIND evidence-engine behaviors.

This module is intentionally deterministic and dependency-light.
It does NOT claim physical disaster-response performance.

Core behaviors implemented here:

- packet structure validation
- CRC validation
- freshness validation
- sequence / replay protection
- evidence decay
- evidence capping
- modality fusion
- disagreement handling
- coverage-gated negative evidence
- explainable evidence states
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import zlib


# ---------------------------------------------------------------------------
# PULSEFIND evidence states
# ---------------------------------------------------------------------------

class EvidenceState(str, Enum):
    HIGH_PRIORITY = "HIGH_PRIORITY"
    VERIFY = "VERIFY"
    LOW_EVIDENCE = "LOW_EVIDENCE"
    NOT_OBSERVED = "NOT_OBSERVED"
    STALE = "STALE"
    NODE_OFFLINE = "NODE_OFFLINE"
    TEAM_ACTIVE = "TEAM_ACTIVE"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationConfig:
    window_seconds: float = 4.0
    half_life_seconds: float = 30.0
    evidence_cap: float = 2.5

    # A HIGH_PRIORITY decision requires independent modalities.
    high_priority_threshold: float = 1.5

    # Evidence disagreement is deliberately routed to VERIFY.
    verify_threshold: float = 0.75

    # Packet freshness.
    max_packet_age_seconds: float = 30.0

    # Sensor health.
    stuck_n: int = 6


# ---------------------------------------------------------------------------
# Packet validation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Packet:
    node_id: str
    zone_id: str
    sequence: int
    timestamp: float
    payload: bytes
    crc: int

    @staticmethod
    def calculate_crc(payload: bytes) -> int:
        """
        Calculate a deterministic CRC-like checksum using CRC32.

        The purpose here is software validation of packet-integrity logic.
        It is not intended to reproduce a particular radio chipset's
        hardware CRC implementation.
        """
        return zlib.crc32(payload) & 0xFFFFFFFF

    @classmethod
    def create(
        cls,
        node_id: str,
        zone_id: str,
        sequence: int,
        timestamp: float,
        payload: bytes,
    ) -> "Packet":
        return cls(
            node_id=node_id,
            zone_id=zone_id,
            sequence=sequence,
            timestamp=timestamp,
            payload=payload,
            crc=cls.calculate_crc(payload),
        )


@dataclass
class PacketValidator:
    config: ValidationConfig = field(default_factory=ValidationConfig)

    # Sequence state is tracked per node AND zone.
    highest_sequence: dict[tuple[str, str], int] = field(default_factory=dict)

    def validate(
        self,
        packet: Packet,
        current_time: float,
    ) -> tuple[bool, str]:
        """
        Validation order:

        1. Structure
        2. CRC
        3. Freshness
        4. Sequence/replay check
        5. Commit sequence state only after acceptance

        This prevents rejected packets from poisoning sequence state.
        """

        if not packet.node_id or not packet.zone_id:
            return False, "INVALID_STRUCTURE"

        if packet.sequence < 0:
            return False, "INVALID_SEQUENCE"

        if not math.isfinite(packet.timestamp):
            return False, "INVALID_TIMESTAMP"

        expected_crc = Packet.calculate_crc(packet.payload)

        if packet.crc != expected_crc:
            return False, "CRC_FAILURE"

        age = current_time - packet.timestamp

        if age < 0:
            return False, "FUTURE_TIMESTAMP"

        if age > self.config.max_packet_age_seconds:
            return False, "STALE_PACKET"

        key = (packet.node_id, packet.zone_id)
        previous = self.highest_sequence.get(key)

        if previous is not None and packet.sequence <= previous:
            return False, "DUPLICATE_OR_REPLAY"

        # Commit state ONLY after every validation above succeeds.
        self.highest_sequence[key] = packet.sequence

        return True, "ACCEPTED"


# ---------------------------------------------------------------------------
# Temporal evidence
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    modality: str
    score: float
    timestamp: float


def decay_factor(
    age_seconds: float,
    half_life_seconds: float,
) -> float:
    """
    Exponential half-life decay.

    At age == half_life, the factor is 0.5.
    """
    if age_seconds < 0:
        raise ValueError("age_seconds cannot be negative")

    if half_life_seconds <= 0:
        raise ValueError("half_life_seconds must be positive")

    return math.pow(0.5, age_seconds / half_life_seconds)


def decayed_score(
    score: float,
    observation_time: float,
    current_time: float,
    half_life_seconds: float,
) -> float:
    if not math.isfinite(score):
        raise ValueError("score must be finite")

    age = max(0.0, current_time - observation_time)

    return score * decay_factor(
        age,
        half_life_seconds,
    )


# ---------------------------------------------------------------------------
# Sensor observations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    modality: str
    score: float
    timestamp: float

    # Whether the observation actually covers the candidate location.
    covers_candidate: bool = True

    # Sensor is operational.
    sensor_healthy: bool = True

    # Used to distinguish rescuer/team activity.
    team_active: bool = False


# ---------------------------------------------------------------------------
# Candidate evidence fusion
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    candidate_id: str

    evidence: dict[str, list[Evidence]] = field(
        default_factory=dict
    )

    uncertainty_radius_m: float = 0.0

    def add_observation(
        self,
        observation: Observation,
        current_time: float,
        config: ValidationConfig,
    ) -> None:

        # Team activity is not survivor evidence.
        if observation.team_active:
            return

        # A failed sensor contributes zero evidence.
        if not observation.sensor_healthy:
            return

        if not math.isfinite(observation.score):
            return

        # Coverage-gated negatives:
        # an observation outside the sensor's coverage cannot count
        # against the candidate.
        if observation.score <= 0 and not observation.covers_candidate:
            return

        score = decayed_score(
            observation.score,
            observation.timestamp,
            current_time,
            config.half_life_seconds,
        )

        self.evidence.setdefault(
            observation.modality,
            [],
        ).append(
            Evidence(
                modality=observation.modality,
                score=score,
                timestamp=observation.timestamp,
            )
        )

    def modality_scores(
        self,
        current_time: float,
        config: ValidationConfig,
    ) -> dict[str, float]:

        result: dict[str, float] = {}

        for modality, observations in self.evidence.items():

            total = 0.0

            for evidence in observations:
                age = max(
                    0.0,
                    current_time - evidence.timestamp,
                )

                total += evidence.score * decay_factor(
                    age,
                    config.half_life_seconds,
                )

            # Evidence is capped per modality.
            result[modality] = min(
                total,
                config.evidence_cap,
            )

        return result

    def classify(
        self,
        current_time: float,
        config: ValidationConfig,
    ) -> tuple[EvidenceState, str]:

        scores = self.modality_scores(
            current_time,
            config,
        )

        if not scores:
            return (
                EvidenceState.NOT_OBSERVED,
                "No usable sensor evidence is available.",
            )

        active = {
            modality: score
            for modality, score in scores.items()
            if score > 0
        }

        if not active:
            return (
                EvidenceState.NOT_OBSERVED,
                "No positive evidence remains after validation and decay.",
            )

        strong_modalities = [
            modality
            for modality, score in active.items()
            if score >= config.verify_threshold
        ]

        # Independent modality agreement is required for HIGH_PRIORITY.
        if (
            len(strong_modalities) >= 2
            and sum(active.values()) >= config.high_priority_threshold
        ):
            modalities = ", ".join(sorted(strong_modalities))

            return (
                EvidenceState.HIGH_PRIORITY,
                f"Independent modalities agree: {modalities}.",
            )

        # One strong modality or conflicting evidence goes to VERIFY.
        if strong_modalities:
            modalities = ", ".join(sorted(strong_modalities))

            return (
                EvidenceState.VERIFY,
                f"Evidence requires verification; supporting modality: {modalities}.",
            )

        return (
            EvidenceState.LOW_EVIDENCE,
            "Weak evidence is present but does not meet verification threshold.",
        )


# ---------------------------------------------------------------------------
# Utility functions used by tests
# ---------------------------------------------------------------------------

def compare_modalities(
    observations: list[Observation],
) -> str:
    """
    Simple conflict detector for independent modalities.

    Returns:
        AGREEMENT
        DISAGREEMENT
        INSUFFICIENT_DATA
    """

    positive = {
        obs.modality
        for obs in observations
        if obs.score > 0 and obs.sensor_healthy
    }

    if len(positive) < 2:
        return "INSUFFICIENT_DATA"

    scores = {
        obs.modality: obs.score
        for obs in observations
        if obs.sensor_healthy
    }

    if not scores:
        return "INSUFFICIENT_DATA"

    values = list(scores.values())

    if max(values) == 0:
        return "INSUFFICIENT_DATA"

    # Opposing evidence is represented by positive vs negative scores.
    signs = {value > 0 for value in values}

    if len(signs) > 1:
        return "DISAGREEMENT"

    return "AGREEMENT"
