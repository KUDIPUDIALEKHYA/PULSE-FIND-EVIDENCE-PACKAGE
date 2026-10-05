# PULSEFIND Validation Source

This directory contains the executable software-validation and simulation source used to evaluate the PULSEFIND evidence and candidate-processing logic.

## Purpose

The purpose of this validation source is to make the software-level claims in the PULSEFIND evidence package inspectable and reproducible.

The validation focuses on deterministic system behavior rather than claiming physical disaster-response performance.

## Validation Areas

The source is intended to cover:

1. Packet structure validation
2. CRC validation
3. Freshness validation
4. Sequence handling
5. Duplicate and replay protection
6. Temporal evidence windows
7. Evidence decay
8. Evidence caps
9. Sensor failure handling
10. Coverage-gated negative evidence
11. Multimodal evidence fusion
12. Modality disagreement
13. Candidate association
14. Candidate uncertainty
15. Replay determinism
16. Ablation experiments
17. Baseline comparisons
18. Synthetic mission simulation

## Reproducibility

Each experiment should record:

- configuration
- random seed
- input conditions
- raw output
- calculated metrics
- execution status

Randomized experiments must use explicit seeds so that a run can be repeated.

## Evidence Classification

Results produced by this source are software-validation or simulation results unless a separate physical experiment provides physical measurements.

Simulation results must not be represented as physical measurements.

## Source-to-Result Chain

The intended validation chain is:

```text
Source code
    ↓
Configuration
    ↓
Test / simulation execution
    ↓
Raw results
    ↓
Metric calculation
    ↓
Validation report
