# Architect Brief — 6-Week MVP

Scope: superficial supratentorial lesions, single fusion pair (T1-post MRI + CT),
rigid registration, public data + phantom, offline.

| Week | Deliverable | Verification |
|---|---|---|
| 1 | Extension skeleton + **de-ID gate** end-to-end on a public dataset | PHI-scrub unit test on synthetic tagged DICOM (`tests/test_deid_gate.py`) |
| 2 | Rigid **registration/fusion** (`BRAINSFit`) + registration-quality metric with red/green threshold | Register a known phantom pair; confirm metric flags a deliberately misaligned input |
| 3 | **AI segmentation proposal** (MONAI Label / TotalSegmentator) into Segment Editor + uncertainty overlay | Dice vs. manually-corrected reference on 3–5 public cases |
| 4 | 3D model + **deterministic planning metrics** (volume, diameter, depth, distance-to-fiducial) | Metrics vs. phantom of known geometry (ground-truth anchor) |
| 5 | **Structured report** + mandatory banner + failure-detection gates | Force each failure mode; confirm report refuses/flags |
| 6 | Buffer + simplified guided UX + internal dry run | Full walkthrough on phantom + 2–3 public cases, timed |

Weeks 5–6 are non-negotiable — the safety/report layer is the point, not a trim target.

## Build order rationale
De-ID first (nothing else is safe to touch data without it). Registration + its
gate before AI (a bad transform poisons everything downstream). Metrics validated on
phantom before touching realistic data. Report/safety last so it wraps a working core.

## Load-bearing modules (white-box)
- `deid_gate.py` — the ingestion hard block.
- Registration-quality gate — blocks downstream on bad transform.
- Metric layer — deterministic; phantom-anchored.

## Known Gaps (append during build; never fold into current step)
- (none yet)
