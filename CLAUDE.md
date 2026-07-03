# NeuroPlan (research) — project context

Offline 3D Slicer **extension** (not a fork) that assists a neurosurgeon with
research-only preoperative planning of **superficial supratentorial lesions**.

## Non-negotiable posture
- Research use only. Not a medical device, not SaMD. Not diagnostic, not
  intraoperative, not a treatment recommender.
- AI **proposes**, surgeon **decides**. Human-in-the-loop is mandatory, not optional.
- Offline only. No network, no PACS write-back, no cloud.
- De-identified / public / phantom data ONLY. The de-ID gate is a hard block.
- Every failure fails loud (honest nulls). No silent clamping of a bad transform
  or an implausible metric.

## Locked decisions
- License: **Apache-2.0**.
- MVP data: **public datasets only** (BraTS / TCIA / IXI) + geometric phantoms.
- Clinical scope: **superficial supratentorial**, fusion pair **T1-post MRI + CT**,
  rigid/affine registration.

## Layout
- `NeuroPlan/` — Slicer extension (scripted module `NeuroPlanWorkflow`).
- `docs/` — protocol, validation, safety, de-ID SOP, exclusions.
- `handoff/` — architect brief / build log.
- `phantom/` — phantom design + ground-truth geometry.
- `tests/` — Python unit tests (pytest) for the safety-critical logic.

## Load-bearing safety modules (white-box — read every line)
- De-identification gate (`deid_gate.py`) — tag allowlist + PHI reject.
- Registration-quality gate — blocks downstream steps on a bad transform.
- Metric layer — deterministic, verified against phantom ground truth.

## Verification tier
- De-ID gate / registration gate / metrics: unit tests + human review (safety-critical).
- UX/report layout: visual check.

## References
- CFM Resolution 2.454/2026 (AI = decision support; physician responsible).
- Slicer scripted-module + Extension Wizard conventions.
