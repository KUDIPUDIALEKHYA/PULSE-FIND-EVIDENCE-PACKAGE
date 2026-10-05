# PULSEFIND — Evidence-Based Multimodal Rescue System

PULSEFIND is a multimodal disaster-response prototype designed to help rescuers prioritize areas for verification using evidence from multiple sensing modalities.

## Core Principle

> No single sensor counts as proof.

PULSEFIND does not claim to directly determine whether a survivor exists. Instead, it combines observations into evidence states that indicate where further verification should be prioritized.

## Evidence States

The system uses ordinal states rather than survivor-probability claims:

- `HIGH_PRIORITY`
- `VERIFY`
- `LOW_EVIDENCE`
- `NOT_OBSERVED`
- `STALE`
- `NODE_OFFLINE`
- `TEAM_ACTIVE`

## Evidence Engine

The validation model includes:

- packet structure validation
- CRC validation
- freshness checking
- sequence and replay protection
- duplicate handling
- temporal evidence windows
- evidence decay
- evidence caps
- sensor-health handling
- multimodal evidence fusion
- disagreement handling

A failed or blind sensor contributes **zero evidence** rather than being interpreted as evidence that no survivor is present.

## Candidate Engine

Candidate-level processing is designed to:

- associate observations with persistent candidates
- maintain uncertainty
- maintain modality-specific evidence
- apply temporal decay
- use coverage-gated negative evidence
- produce an explainable candidate state

## Validation Philosophy

The repository separates different kinds of evidence.

### Software validation

Executable tests and simulations can establish whether the implemented logic behaves according to its specified rules.

### Simulation results

Synthetic experiments can measure system behavior under controlled scenarios.

### Physical validation

Physical measurements require an actual physical experiment and corresponding records. Software simulation results are not presented as physical measurements.

## Reproducibility

Validation experiments should record:

- source code
- configuration
- random seeds
- test inputs
- raw outputs
- calculated metrics
- execution commands

The objective is that another engineer can inspect the implementation and reproduce the software-validation results.

## Repository Structure

```text
00 Validation Source/
01 Documentation/
02 Architecture/
03 Hardware/
04 Firmware/
05 Packet protocol/
06 Evidence engine/
07 Candidate engine/
08 Dashboard/
09 Automated tests/
10 Physical test records/
11 Raw sensor logs/
12 Packet logs/
13 Replay data/
14 Simulation results/
15 Ablation results/
16 Baseline results/
17 Test report/
18 Photos/
19 Demo video/
20 Final presentation/
