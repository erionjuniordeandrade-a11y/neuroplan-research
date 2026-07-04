# NeuroPlan — Full Forward Development Plan

> Research-only, offline 3D Slicer companion for preoperative planning of superficial
> supratentorial lesions. NOT a medical device, NOT diagnostic, NOT intraoperative,
> NOT a treatment recommender. Phantom / synthetic / de-identified public data ONLY.
> Apache-2.0. Solo neurosurgeon-researcher, pre-PMF, no clinical impact today.

This document is the single execution reference. It is written to be runnable by a
less-capable model with zero prior context. Every phase lists concrete files, a
machine-checkable acceptance command, the CLAUDE.md verification tier, dependencies,
effort, and explicit STOP conditions. **Read Sections 4 and 5 before touching any code.**

Baseline (verified 2026-07-04): `./.venv/bin/pytest -q` → **86 passed**. Keep it green
between every slice.

---

## 0. Goal & execution order (confirmed 2026-07-04)

**Primary near-term goal: a defensible pilot-FEASIBILITY PAPER.** This reorders the
roadmap. Four decisions govern execution (they override the raw phase numbering below):

1. **Critical path = measured phantom + validation.** The paper stands or falls on
   Phase 6 (promote ground truth from `design_candidate` → `measured`) and Phase 7
   (Tier-A/B validation). Everything else serves those two.

2. **PDF report (Phase 1) is DEFERRED off the critical path.** A PDF with no measured
   data in it is not paper-critical (YAGNI now). The JSON research artifact already
   exists and is enough to drive validation. Build the PDF only *after* Phase 4, when
   there is real data to render. STOP: `reportlab` is **not** in `requirements-dev.txt`
   — add and pin it before starting the PDF, do not assume it is on disk.

3. **Risk-first: do Phase 4a (spike) at the FIRST Slicer session**, before investing in
   the remaining offline polish. The biggest unknown is whether BRAINSFit/Elastix output
   feeds the NMI gate cleanly and whether de-ID provably precedes `loadVolume`. Prove that
   end-to-end on ONE pair before betting more work on top of it.

4. **Confidence: build the data, gate the display.** The proposal may *carry* a scalar
   confidence / per-voxel uncertainty (Phase 2 contract, Phase 5 model), but it is NEVER
   shown in any UI or written to any artifact until Phase 7's confidence-vs-error AUC
   check passes. The display is structurally gated on calibration — false trust is
   impossible by construction, not by discipline.

**Execution order (not the numeric order):**
`Phase 0` → **`Phase 4a` (first Slicer session, risk-first)** → `Phase 2` → `Phase 3`
→ `Phase 4` → `Phase 5` → `Phase 6` (critical) → `Phase 7` (critical) → `Phase 1` (PDF, deferred).

---

## 1. Current state (what exists, what's proven, what's stubbed)

### Proven / done (offline-verifiable, unit-tested)
| Concern | File | Status |
|---|---|---|
| De-ID hard-block gate (tag allowlist + PHI reject + UID regen + manifest) | `NeuroPlan/NeuroPlanWorkflow/deid_gate.py` | Done. `DeidRejection` fails loud. Tested `tests/test_deid_gate.py`. |
| Registration-quality gate (NMI, `DEFAULT_NMI_THRESHOLD=1.05`, honest nulls) | `NeuroPlan/NeuroPlanWorkflow/registration_quality.py` | Done. `score()->RegistrationQuality(passed,...)`. Tested `tests/test_registration_quality.py`. |
| Deterministic metric layer (volume mL, max diameter, centroid, depth, fiducial dist) | `NeuroPlan/NeuroPlanWorkflow/metrics.py` | Done. Pure NumPy, honest nulls, flags-not-clamps. Tested `tests/test_metrics.py`. **Validated against DESIGN geometry only — not measured.** |
| Shared de-ID override policy (single source of truth for both UIs) | `NeuroPlan/NeuroPlanWorkflow/gate_policy.py` | Done. `HARD_BLOCK_STAGES={deidentify}`. Tested `tests/test_gate_policy.py`. |
| Gated workflow state machine (6 stages, structural lock, immutable audit) | `neuroplan_ui/workflow.py` | Done. Re-locks downstream on upstream regression. Tested `tests/test_workflow_gates.py`. |
| Research-artifact export (JSON, mandatory banner, forbidden clinical fields) | `neuroplan_ui/export.py`, `neuroplan_ui/banner.py` | Done for JSON. Tested `tests/test_export_banner.py`. **No PDF yet.** |
| Command parser + pending actions (offline UX plumbing) | `neuroplan_ui/command_parser.py`, `neuroplan_ui/pending_actions.py` | Done. Tested. |
| Streamlit offline app shell | `neuroplan_ui/app.py` | Runs offline on synthetic data. |
| CI | `.github/workflows/test.yml` | Runs pytest. |
| Phantom design spec + candidate ground truth | `phantom/README.md`, `phantom/ground_truth_targets.candidate.csv`, `phantom/ground_truth_fiducials.candidate.csv` | Design only — `source=design_candidate`. NOT measured. |

### Stubbed / not implemented (the remaining real work)
| Seam | File / symbol | Blocked on |
|---|---|---|
| Real Slicer volume load | `neuroplan_ui/slicer_bridge.py::load_volume` (synthetic) | running 3D Slicer |
| Real registration + resample | `slicer_bridge.py::register_and_resample` (synthetic) | running 3D Slicer |
| AI segmentation proposal | `slicer_bridge.py::propose_segmentation` (trivial threshold) + `NeuroPlanWorkflow.py::propose_segmentation` (`NotImplementedError("week 3")`) | MONAI Label / TotalSegmentator + GPU |
| Slicer node → (mask, spacing) seam | `NeuroPlanWorkflow.py::_array_and_spacing` (`NotImplementedError("week 4")`) | running 3D Slicer |
| PDF report | `NeuroPlanWorkflow.py::build_report` (`NotImplementedError("week 5")`); PDF absent from `export.py` | none — offline-buildable |
| Slicer widget UI (progress rail, gate badges, logged override) | `NeuroPlanWorkflow.py::NeuroPlanWorkflowWidget` (scaffold) | running 3D Slicer to verify |
| Model export | `slicer_bridge.py::export_model` (returns path only) | running 3D Slicer |
| Measured phantom ground truth | `phantom/ground_truth_*.csv` (do not exist yet) | physical fabrication + scan |

### Architectural invariant already in place
Pure, tested modules hold ALL safety logic; both UIs (Streamlit `workflow.py` and Slicer
`NeuroPlanWorkflow.py`) are thin and consult the *same* `gate_policy`. The Slicer seams
are isolated single functions (`_array_and_spacing`, the `slicer_bridge` fns) so offline
work never blocks on Slicer. **Preserve this: no safety logic in UI code, ever.**

---

## 2. Phased roadmap

Sequencing note (see Section 3): phases split into **OFFLINE-BUILDABLE NOW** (no Slicer/GPU/
phantom — build and verify between Slicer sessions) and **REQUIRES external environment**.
For a solo researcher the correct order front-loads all offline work so Slicer/phantom
sessions are short and high-yield. Re-sequenced from the raw week 2..6 order accordingly.

---

### Phase 0 — Housekeeping & test-harness hardening `[OFFLINE] [S]`
**Goal:** lock the green baseline and make the phantom CSV a real fixture before it anchors anything.

Tasks:
1. Add `handoff/BUILD-LOG.md` (referenced by CLAUDE.md handoff protocol; currently missing). Record baseline "86 passed".
2. Add `tests/test_phantom_ground_truth.py`: parse `phantom/ground_truth_targets.candidate.csv`, assert the volume column equals the sphere/ellipsoid formula from `phantom/README.md` within 1e-3 for each row (this catches CSV drift and proves the *design* is internally consistent — NOT that it is measured).
3. Add a `conftest.py` marker registration (`unit`, `integration`) per `rules/ecc/python/testing.md`.

Acceptance: `./.venv/bin/pytest -q` green with **≥88 passed**; new test fails if any CSV volume cell is edited off-formula.
Verification tier: local logic → unit test. Deps: none. STOP: none.

---

### Phase 1 — PDF report + report schema lock `[OFFLINE] [M]` `[DEFERRED — run LAST, after Phase 4]`
**Goal:** implement `build_report` → JSON **and** PDF, both banner-stamped, schema structurally incapable of clinical fields.

> **DEFERRED (Section 0, decision 2):** for a feasibility paper this is off the critical
> path — the JSON artifact already exists. Do this only after Phase 4, when there is real
> data to render. **STOP before starting: `reportlab` is not in `requirements-dev.txt` —
> add + pin it first.** Watch the `import matplotlib.cm as mpl_cm` ordering clash (founder
> CLAUDE.md): import reportlab first, matplotlib lazily.

Tasks:
1. In `neuroplan_ui/export.py` add `build_pdf(artifact, out_path)` using **reportlab** (already on disk per founder CLAUDE.md). The PDF MUST render `banner.RESEARCH_BANNER` on every page (header or footer) and MUST route the payload through the existing `_assert_no_clinical_content` guard before rendering.
2. Implement `NeuroPlanWorkflowLogic.build_report(case)` in `NeuroPlan/NeuroPlanWorkflow/NeuroPlanWorkflow.py` to delegate to `export.build_artifact` + `export.build_pdf` (thin seam — no new safety logic in the Slicer module).
3. Extend `tests/test_export_banner.py` (or add `tests/test_pdf_report.py`):
   - a PDF is produced and the extracted text contains the banner on page 1 (use `pypdf`/`pdfplumber` text extraction; if neither is available, assert the reportlab canvas received the banner string via a seam).
   - `build_pdf` raises `ForbiddenField` when the artifact carries `diagnosis`/`approach`/`who_grade`/etc. (reuse `_FORBIDDEN_FIELDS`).
   - the artifact schema exposes NO settable clinical field (assert `_FORBIDDEN_FIELDS` are all rejected).

Acceptance: `./.venv/bin/pytest -q -k "pdf or banner"` green; a generated sample PDF exists under a tmp path and contains the banner text.
Verification tier: artifact/report layout → visual check **plus** unit test on the banner + forbidden-field guard (safety-adjacent → keep the test, not just the eyeball).
Deps: Phase 0. STOP: if reportlab clashes with matplotlib import ordering (`import matplotlib.cm as mpl_cm`, per founder CLAUDE.md) — import reportlab first, matplotlib lazily.

---

### Phase 2 — Segmentation-proposal contract & state (offline half) `[OFFLINE] [M]`  ← was week 3, offline slice
**Goal:** freeze the *contract* and gating for an AI proposal without any MONAI/GPU. The model call is Phase 5; here we make everything around it correct and tested offline.

Tasks:
1. Formalize `slicer_bridge.SegmentationProposal` as the contract: `label_array`, `scalar_confidence`, `is_proposal=True`, `accepted_by_human=False`, plus an added `per_voxel_uncertainty` (optional array, honest-null when absent) and a `reject: bool` flag with reason (the docstring in `NeuroPlanWorkflow.propose_segmentation` already promises these).
2. Add a pure `segmentation_proposal.py` module in `NeuroPlan/NeuroPlanWorkflow/` holding validation only (no model): `validate_proposal(proposal) -> None` that fails loud if `is_proposal` is False, if confidence ∉ [0,1], or if shape mismatches the volume. This is the deep-module seam MONAI plugs into later.
2b. **Confidence display gate (Section 0, decision 4):** the proposal *carries* `scalar_confidence`/`per_voxel_uncertainty` as data, but add a module-level `CONFIDENCE_CALIBRATED = False` flag and a `displayable_confidence(proposal)` accessor that returns `None` (honest null) while the flag is False. The UI and `export.py` read confidence ONLY through this accessor, so confidence cannot reach a human until Phase 7 sets the flag True. Test: `displayable_confidence` returns `None` regardless of the proposal's stored confidence while uncalibrated.
3. Wire `neuroplan_ui/workflow.py` already enforces "proposal never final" (`accept_segmentation` requires named operator). Add a test asserting metrics stay `LOCKED` until `accept_segmentation`, and that an upstream regression clears acceptance (regression already coded in `_recompute_readiness` — add explicit coverage).

Acceptance: `./.venv/bin/pytest -q -k "segmentation or proposal"` green; `validate_proposal` rejects a proposal with `is_proposal=False` and one with `scalar_confidence=1.7`.
Verification tier: safety-critical (human-decides invariant) → unit tests + human review.
Deps: Phase 0. STOP: do NOT import monai/torch here — this phase must run in the plain `.venv`.

---

### Phase 3 — Slicer widget UI logic (offline-testable half) `[OFFLINE] [M]`  ← was week 6, logic slice
**Goal:** make the widget's *decision logic* (gate badges, override, step advance) fully unit-tested without a running Slicer, so the in-Slicer session only has to wire pixels.

Tasks:
1. `can_advance` already exists and consults `gate_policy`. Extract any remaining advance/badge logic into pure helpers on `NeuroPlanWorkflowLogic` (or a new `widget_logic.py`) that take plain state, not Qt widgets.
2. Add `tests/test_widget_logic.py`: de-ID FAILED + any reason → `can_advance` False (hard block); a non-hard-block FAILED + non-empty reason → True; empty reason → False. Mirror the `test_gate_policy.py` guarantees from the Slicer side.
3. Define the badge state mapping (red/green/overridden) as a pure function returning an enum/string, tested exhaustively over `GateState`.

Acceptance: `./.venv/bin/pytest -q -k "widget"` green; a PHI-carrying stage cannot be advanced from the Slicer UI code path in any test permutation.
Verification tier: safety-critical (de-ID hard block from second UI) → unit tests + human review.
Deps: Phase 2. STOP: none (Qt not imported in tests — guarded by `_IN_SLICER`).

---

### Phase 4a — Risk-first Slicer spike `[REQUIRES 3D SLICER] [S]`  ← do FIRST of all Slicer work
**Goal (Section 0, decision 3):** in ONE short Slicer session, prove the single riskiest
integration end-to-end before investing more, and prove the safety ordering holds.

Tasks (throwaway/spike quality — not the final seam):
1. Load one already-de-identified phantom-or-public volume pair via `slicer.util.loadVolume`.
2. Run a rigid registration (BRAINSFit/Elastix), resample moving onto fixed, pull arrays.
3. Feed those arrays to the EXISTING `registration_quality.score(...)` — confirm it returns
   `passed=True` on the aligned pair and `passed=False` on a deliberately misaligned pair.
4. Confirm, by reading the call path, that the de-ID gate runs BEFORE `loadVolume` touches disk.

Acceptance: the real NMI gate passes/fails correctly on real Slicer output for one pair;
the de-ID-before-load ordering is demonstrated. Write the result to `handoff/BUILD-LOG.md`.
Verification tier: spike → manual, logged. Deps: Phase 0.
**STOP:** if BRAINSFit/Elastix output cannot be shaped into the arrays the NMI gate expects,
or de-ID cannot be proven to precede load — STOP and redesign Phase 4 before doing Phases
1–3 polish. This spike exists precisely to surface that early.

---

### Phase 4 — Real Slicer integration: load + register + node→array `[REQUIRES 3D SLICER] [L]`  ← week 2 + week-4 seam
**Goal:** replace the three synthetic Slicer stubs with real calls. Cannot be verified without a running 3D Slicer — schedule as a focused Slicer session AFTER Phases 0–3.

Tasks (each is an isolated seam; keep offline stubs as the `_IN_SLICER is False` branch):
1. `slicer_bridge.load_volume`: `slicer.util.loadVolume(file_ref)` on already-de-identified data; return a `VolumeHandle` wrapping the node (`is_synthetic=False`). De-ID gate MUST run before any load reaches disk.
2. `slicer_bridge.register_and_resample`: rigid/affine via BRAINSFit/Elastix; resample moving onto fixed grid; return arrays for the NMI gate.
3. `NeuroPlanWorkflow._array_and_spacing`: `slicer.util.arrayFromSegmentBinaryLabelmap(...)` + `node.GetSpacing()` → `(mask, (sx,sy,sz))`, then delegate to the already-tested `metrics.compute_metrics`.

Acceptance (in-Slicer, manual + scripted): load a public/phantom pair; `register_and_resample` output passes the NMI gate on an aligned pair and FAILS on a deliberately misaligned pair (`misaligned=True` equivalent); `compute_metrics_from_arrays` and the node path return identical numbers on the same volume. Offline suite still green (`./.venv/bin/pytest -q`).
Verification tier: API behavior change → request/response + regression test; de-ID-before-load path → human review.
Deps: Phases 0–3; requires 3D Slicer install. STOP: if de-ID cannot be proven to run before `loadVolume`, do NOT ship the load path — the hard block precedes disk I/O.

---

### Phase 5 — AI segmentation proposal via MONAI/TotalSegmentator `[REQUIRES SLICER + MONAI + GPU] [L]`  ← week 3
**Goal:** produce an editable proposal loaded into the Segment Editor, never final.

Tasks:
1. Implement `NeuroPlanWorkflowLogic.propose_segmentation(volume_node)` calling MONAI Label / TotalSegmentator; return the Phase-2 `SegmentationProposal` contract (label map + per-voxel uncertainty + scalar confidence + reject flag).
2. Load result into the native Segment Editor as an **editable** segment; the workflow keeps `accepted_by_human=False` until the surgeon accepts.
3. Run `validate_proposal` (Phase 2) on every model output before it reaches the UI.

Acceptance (in-Slicer): a proposal appears as an editable segment; metrics remain locked until explicit acceptance; `validate_proposal` rejects a malformed model output. Offline suite unaffected and green.
Verification tier: safety-critical (AI-proposes/human-decides) → unit tests on the contract (offline) + human review of the model wiring.
Deps: Phase 4 + MONAI/GPU. STOP: if the model has no usable confidence/uncertainty output, ship WITHOUT a confidence display rather than a fabricated one — a non-predictive confidence "manufactures false trust" (validation-plan.md, Critical calibration check).

---

### Phase 6 — Physical phantom fabrication + ground-truth promotion `[REQUIRES FABRICATION + SCANNER] [L]`  ← week 4 truth
**Goal:** promote `*.candidate.csv` (`source=design_candidate`) to measured `phantom/ground_truth_targets.csv` / `ground_truth_fiducials.csv` (`source=measured`). **This is the gate that turns "validated against design" into "validated against reality."**

Tasks (per `phantom/README.md` acceptance checklist):
1. Finalize CAD, document coordinate datum, export target + fiducial tables; fill `phantom/cad/README.md`.
2. Fabricate; record manufacturing tolerance / post-print metrology.
3. Scan on MRI (T1-post-equiv) + CT; localize fiducials; replace nominal values with measured → write `ground_truth_targets.csv` / `ground_truth_fiducials.csv` with `source=measured` (do NOT commit scans; `.gitignore` excludes imaging).
4. Point `tests/test_phantom_ground_truth.py` at the measured CSV once present; keep candidate test as design-consistency check.

Acceptance: measured CSVs exist with `source=measured`; every `phantom/README.md` acceptance checkbox is satisfiable; metric-error test compares NeuroPlan output vs measured within a pre-registered tolerance.
Verification tier: data migration (designed→measured ground truth) → dry run + backup + human review; this underpins every publishable claim.
Deps: Phase 4 (need working load+register+metrics to measure against). STOP: until this lands, NO document, abstract, or README may say "validated against the phantom" — only "validated against design geometry" (metrics.py docstring already says this; hold that line).

---

### Phase 7 — Full end-to-end validation per `docs/validation-plan.md` `[REQUIRES SLICER + PHANTOM + PUBLIC DATA] [L]`
**Goal:** execute Tier A (phantom → true error) and Tier B (BraTS/TCIA/IXI → realism/distribution) and the calibration check.

Tasks: TRE on fiducials; volume/diameter/depth error (Bland–Altman) vs measured; Dice/HD95 of proposal AND surgeon-corrected vs reference; **confidence-vs-error correlation (AUC)** per the Critical calibration check; deliberately-bad-transform block test; SUS + time-to-plan pilot.
Acceptance: a validation report with all metrics framed as **pilot feasibility**; registration gate demonstrably blocks ≥2 bad transforms with named reasons.
Verification tier: full — human review + tests + logged runs.
Deps: Phases 4–6. STOP: only flip `segmentation_proposal.CONFIDENCE_CALIBRATED = True` (the
gate from Phase 2, decision 4) if the AUC demonstrably shows confidence correlates with error.
If it does not correlate, leave the flag False — the display stays off by construction. Never
ship false trust.

---

## 3. Environment matrix (what a solo researcher can do when)

| Phase | Slicer | MONAI/GPU | Physical phantom | Buildable & verifiable offline now? |
|---|:--:|:--:|:--:|:--:|
| 0 Housekeeping | – | – | – | ✅ |
| 1 PDF report | – | – | – | ✅ |
| 2 Seg contract (offline) | – | – | – | ✅ |
| 3 Widget logic (offline) | – | – | – | ✅ |
| 4 Slicer load/register/seam | ✅ | – | (phantom or public data) | ❌ needs Slicer |
| 5 AI proposal | ✅ | ✅ | – | ❌ needs Slicer+GPU |
| 6 Phantom promotion | ✅ | – | ✅ | ❌ needs fabrication+scan |
| 7 E2E validation | ✅ | ✅ | ✅ | ❌ needs everything |

**Do Phases 0–3 completely before booking any Slicer time.** They are ~all the remaining
pure-Python work and leave only pixel-wiring and measurement for the environment-bound sessions.

---

## 4. Safety invariants — preserve across EVERY phase

| Invariant | Where enforced | Where tested | Rule when extending |
|---|---|---|---|
| **De-ID hard block** (PHI can never pass; non-overridable) | `gate_policy.HARD_BLOCK_STAGES`, `deid_gate.gate_files`, `workflow.override`, `NeuroPlanWorkflow.can_advance` | `test_gate_policy.py`, `test_deid_gate.py`, `test_workflow_gates.py` | Any new UI/stage consults `gate_policy` — never re-implements the rule. Load runs AFTER de-ID (Phase 4 STOP). |
| **Honest nulls / fail loud** (never clamp; None+reason, flag-not-correct) | `metrics.py` (None + warnings), `registration_quality.py`, `deid_gate.DeidRejection` | `test_metrics.py`, `test_registration_quality.py` | New metrics/model outputs return None+reason on missing input; implausible values flagged, never silently fixed. |
| **AI proposes / human decides** | `workflow.accept_segmentation` (named operator), `SegmentationProposal.accepted_by_human=False` | `test_workflow_gates.py` | Model output (Phase 5) is a proposal; metrics locked until human acceptance; upstream regression clears acceptance. |
| **Offline only** | `_IN_SLICER` guards + synthetic stubs; no network calls anywhere | suite runs with no network | No new import that phones home; MONAI runs local. |
| **Banner on every artifact** | `banner.stamp` + `assert_present`, re-checked in `to_json`/`write_json` | `test_export_banner.py` | PDF (Phase 1) stamps banner on every page; any new export routes through `banner`. |
| **No clinical-decision fields** | `export._FORBIDDEN_FIELDS` + recursive `_assert_no_clinical_content` (keys AND values) | `test_export_banner.py` | Report schema (Phase 1) stays structurally incapable of diagnosis/grade/approach; new fields pass the guard. |

Any change that would weaken one of these is out of scope by definition → log to
`BUILD-LOG.md` Known Gaps, do not merge.

---

## 5. Definition of Done for the research MVP + defensible validation story

**MVP is done when:**
1. A surgeon runs the full path in 3D Slicer on a phantom pair: import → de-ID gate → register → NMI gate → AI proposal (editable) → human-accept → deterministic metrics → JSON+PDF export with banner. (Phases 1–5.)
2. Every gate blocks loudly and is overridable ONLY where policy allows (de-ID never). (Phases 3–4.)
3. Metrics match **measured** phantom ground truth within a pre-registered tolerance. (Phase 6.)
4. `./.venv/bin/pytest -q` green in CI; offline suite covers all safety logic; 80%+ coverage on safety modules.

**Defensible validation story (tie to `docs/validation-plan.md`):**
- Tier A phantom gives *true error* in mm/mL (TRE, volume/diameter/depth error, reproducibility).
- Tier B public data gives realism/distribution (Dice/HD95, failure-detection sensitivity).
- The confidence score is only claimed useful if it *correlates with error* (AUC reported); otherwise removed.
- **The load-bearing honesty gap:** today the metric layer is validated against *designed* geometry
  (`source=design_candidate`), not a measured phantom. Until Phase 6 promotes the CSVs to `source=measured`,
  the only defensible phrase is "validated against design geometry." Every abstract/README must respect this.
  All claims framed as **pilot feasibility**, never clinical performance.

---

## 6. Risks & defended deferrals

| Deferred | Because | Risk of deferral | Defer-to milestone |
|---|---|---|---|
| Real Slicer load/register | needs running Slicer; can't verify offline | Offline stubs could drift from real API | Phase 4 |
| MONAI/GPU segmentation | needs GPU + Slicer; heavy dep | Proposal contract untested against real model output | Phase 5 (contract tested offline in Phase 2 de-risks this) |
| Measured phantom ground truth | needs fabrication + scanner time/cost | Publishing "validated" would be false | Phase 6 (hard gate on all validation claims) |
| Confidence calibration | needs held-out labeled data | A non-predictive score manufactures false trust | Phase 7 (remove score if AUC ≈ chance) |
| Model export (.obj/.stl) | Slicer-dependent, non-safety-critical, viz-only | Low — explicitly non-clinical | Phase 4/after; log to Known Gaps if slipped |
| Inter-operator reproducibility | needs a second operator | Weaker reproducibility claim | Phase 7 |

---

## 7. Next 3 concrete actions (start now, offline `.venv`)

Reflecting Section 0 (feasibility-paper goal, PDF deferred, risk-first spike):

1. **Phase 0:** create `handoff/BUILD-LOG.md` (record "86 passed" baseline) and add
   `tests/test_phantom_ground_truth.py` asserting each candidate CSV volume matches the
   sphere/ellipsoid formula from `phantom/README.md`. Run `./.venv/bin/pytest -q` → expect ≥88 passed.
2. **Phase 2:** add `NeuroPlan/NeuroPlanWorkflow/segmentation_proposal.py::validate_proposal`
   and extend `SegmentationProposal` with `per_voxel_uncertainty` + `reject`; add the
   `CONFIDENCE_CALIBRATED` flag + `displayable_confidence` accessor (decision 4) with tests;
   add tests that a non-proposal or out-of-range confidence is rejected. Freezes the contract MONAI plugs into.
3. **Phase 3:** extract the widget's advance/badge decision logic into pure helpers and add
   `tests/test_widget_logic.py` mirroring the de-ID hard-block guarantee from the Slicer side.

Then, at the **first available 3D Slicer session, run Phase 4a (the risk-first spike) BEFORE
anything else Slicer-side** — it may force a Phase 4 redesign. PDF (Phase 1) is deliberately
last. Measured phantom (Phase 6) + validation (Phase 7) are the paper's critical path.
