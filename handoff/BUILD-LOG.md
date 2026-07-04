# NeuroPlan — Build Log

Step history + Known Gaps. Newest first. See `handoff/DEVELOPMENT-PLAN.md` for
the full phased roadmap and `CONTEXT.md` for the domain glossary.

---

## 2026-07-04 — Phase 3: widget decision logic (offline half) `[OFFLINE]`

- Added pure `NeuroPlan/NeuroPlanWorkflow/widget_logic.py`: `can_advance`
  (de-ID hard block via shared `gate_policy`) + `badge_for` (gate-state → badge,
  fails loud on unknown state). Widget `NeuroPlanWorkflow.can_advance` now
  delegates to it; the widget is a thin renderer.
- `tests/test_widget_logic.py`: de-ID never advances on failure for ANY reason;
  overridable gate needs a reason; badge mapping exhaustive over `GateState`.
- Verification tier: safety-critical (de-ID hard block from 2nd UI) → unit tests.
- Suite 106 → 116.

## 2026-07-04 — Phase 2: segmentation-proposal contract + confidence gate `[OFFLINE]`

- Extended `slicer_bridge.SegmentationProposal` (per_voxel_uncertainty honest
  null, reject + reject_reason). Added pure
  `NeuroPlan/NeuroPlanWorkflow/segmentation_proposal.py`: `validate_proposal`
  (fails loud on non-proposal / pre-accepted / bad confidence / unreasoned
  reject / shape mismatch) and `displayable_confidence` (honest null until
  `CONFIDENCE_CALIBRATED`, decision 4).
- `tests/test_segmentation_proposal.py` (9). Suite 97 → 106.
- Verification tier: safety-critical (AI-proposes/human-decides) → unit tests.

## 2026-07-04 — Phase 0: housekeeping & phantom-CSV fixture `[OFFLINE]`

- Baseline before this phase: `./.venv/bin/pytest -q` → **86 passed**.
- Added `tests/conftest.py` registering the `unit` / `integration` markers.
- Added `tests/test_phantom_ground_truth.py`: asserts every candidate CSV volume
  matches the documented `(4/3)·pi·rx·ry·rz/1000` formula and every max-diameter
  equals the largest axis, and guards that all rows stay `source=design_candidate`.
  This locks the phantom design so an off-formula hand edit fails CI.
- Verification tier: local logic → unit test.

## Known Gaps (carried forward)

- **Metric layer is validated against DESIGN geometry, not measured reality.**
  The `.candidate` CSVs are `source=design_candidate`. No "validated against the
  phantom" claim until Phase 6 promotes them from a scanned physical phantom.
- **Slicer seams are stubs** (`slicer_bridge.load_volume`,
  `register_and_resample`, `propose_segmentation`, `NeuroPlanWorkflow._array_and_spacing`).
  Require a running 3D Slicer / MONAI / GPU. See DEVELOPMENT-PLAN Phases 4–5.
- **PDF report deferred** (DEVELOPMENT-PLAN Phase 1) — off the feasibility-paper
  critical path; JSON artifact suffices for now. `reportlab` not yet in
  `requirements-dev.txt`.
- **Depth-from-surface not CSV-anchored** — blocked on committing the phantom
  outer-shell geometry; algorithm validated exactly instead (see tests/test_metrics.py).

---

## Prior history (pre-Phase-0, on main)

- Research UX layer `neuroplan_ui/` built and converged from a duplicate parallel
  session; deterministic metric layer added; Fable-5 audit fixes landed (unified
  de-ID hard-block `gate_policy`, deepened export guard, honest UID comment); CI
  workflow added. Suite reached 86 passing. Full plan + `CONTEXT.md` written.
