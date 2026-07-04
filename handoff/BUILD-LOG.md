# NeuroPlan — Build Log

Step history + Known Gaps. Newest first. See `handoff/DEVELOPMENT-PLAN.md` for
the full phased roadmap and `CONTEXT.md` for the domain glossary.

---

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
