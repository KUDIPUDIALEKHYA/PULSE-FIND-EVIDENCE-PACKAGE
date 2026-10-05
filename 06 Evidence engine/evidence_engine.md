# Evidence Engine
Parameters:
WINDOW = 4 seconds
HALF_LIFE = 30 seconds
EVIDENCE CAP = 2.5
STUCK_N = 6
SIGMA_MIN = 2.0
SIGMA_GAIN = 1.5

Handles evidence accumulation, reliability, temporal decay, freshness, sensor health,
coverage, conflict, multimodal fusion, team suppression, state generation and explanations.

Safety rules:
- Missing evidence is not negative evidence.
- Stale evidence is not equivalent to fresh evidence.
- Conflicting modalities remain VERIFY.
- One modality alone does not automatically become HIGH PRIORITY.
