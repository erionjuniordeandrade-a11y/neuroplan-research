# NeuroPlan research UX layer (`neuroplan_ui`)

> **Research use only. Not for clinical or intraoperative decision-making.**

A friendly, **offline** dashboard + command layer over 3D Slicer for a
research-only workflow. It orchestrates safe technical stages, each behind a
quality gate, with mandatory human confirmation on sensitive actions. It makes
**no medical decisions** and never recommends diagnosis, treatment, surgical
approach, or intraoperative navigation.

## Workflow

```
Import → De-identify → Register/Fuse → Propose Segmentation
       → Compute Metrics → Export Research Artifacts
```

Each stage is a **gate**. A downstream stage is *structurally locked* (a data
state, not a UI hint) until the upstream gate is open — `PASSED` or an
explicit, logged human `OVERRIDDEN`.

## Modules

| File | Role |
|------|------|
| `banner.py` | The mandatory research notice + `stamp`/`assert_present` enforcement. |
| `pending_actions.py` | Closed action vocabulary, `PendingAction`, and immutable `ActionQueue`; confirmation is the only path to execution. |
| `command_parser.py` | NL text → **pending** action; **refuses** clinical-decision requests. |
| `workflow.py` | The gated state machine (de-ID, registration, segmentation-proposal, metrics, export). |
| `slicer_bridge.py` | The single seam to 3D Slicer; **offline synthetic stubs** today. |
| `export.py` | Banner-stamped research artifact; rejects clinical-decision fields. |
| `app.py` | Streamlit dashboard (thin; all safety logic is in the modules above). |

The gates delegate to the already-tested standalone safety modules in
`NeuroPlan/NeuroPlanWorkflow/`: `deid_gate.py` and `registration_quality.py`.
Those remain the single source of truth for *how* to de-identify and score a
registration; this layer only orchestrates and gates on their results.

## Run it

```bash
pip install -r requirements-dev.txt
streamlit run neuroplan_ui/app.py     # fully offline, synthetic data
pytest tests/                         # safety + confirmation tests
```

## Safety guarantees (mapped to the spec) and how they're enforced

| Requirement | Enforcement |
|-------------|-------------|
| Offline, non-clinical | No network calls anywhere; `slicer_bridge` synthesizes data locally. |
| Phantom / synthetic / de-ID public data only | De-ID gate is the only entry to `Register`; nothing bypasses it. |
| No medical decisions | `export.py` rejects `diagnosis`/`grade`/`treatment`/`approach` fields; parser refuses those intents. |
| De-ID blocks unsafe import (R2) | `WorkflowState.run_deidentify`: a `DeidRejection` leaves `Register` `LOCKED`. |
| Registration gate blocks downstream (R3) | A failed score leaves `Segment`+downstream `LOCKED`. |
| Segmentation is a proposal, not a result (R4) | `propose_segmentation` sets `PROPOSED`; `Metrics` refuses to open until `accept_segmentation` records human acceptance. |
| NL commands are pending, not auto-run (R5) | Parser only *creates* actions; `ActionQueue.confirm` (named operator) is the sole execution path. |
| 3D export is offline viz only (R6) | `EXPORT_VISUALIZATION` is a distinct pending action; exported artifacts flag `model_export.not_for = "clinical AR or intraoperative navigation"`. |
| Every output carries the notice | `banner.assert_present` re-checks on build and on serialize. |

## Explicit STUBS (not yet real)

These are placeholders with clear boundaries. None of them touch a real patient
scan, a network, or a running Slicer today.

- **`slicer_bridge.load_volume`** — returns a synthetic 32³ NumPy volume; does
  **not** read from disk. Real: `slicer.util.loadVolume` on de-identified data.
- **`slicer_bridge.register_and_resample`** — returns synthetic aligned (or, with
  `misaligned=True`, independent) arrays to exercise the gate. Real: rigid/affine
  registration + resample inside Slicer.
- **`slicer_bridge.propose_segmentation`** — returns a trivial threshold mask with
  a fixed confidence. Real: MONAI Label / TotalSegmentator proposal loaded into
  the Segment Editor for surgeon correction.
- **`slicer_bridge.export_model`** — returns the intended output path without
  writing anything. Real: offline surface-model export (.obj/.stl) for
  experimental viewing only.
- **`app.py` execute path** — runs the workflow against a single synthetic case
  (`synthetic_case_0`), not real imported files.
- **Metrics values in `app.py`** — the export uses illustrative fixed numbers
  (`volume_ml=4.19`, etc.). Real deterministic, phantom-anchored metrics are the
  `NeuroPlanWorkflowLogic.compute_metrics` week-4 task.

## Known LIMITATIONS

- **Burned-in pixel PHI is not detected.** The de-ID gate flags
  `BurnedInAnnotation` but neither it nor this layer inspects pixel data. Do not
  feed scans that may have burned-in identifiers. (Tracked as an audit finding.)
- **No persistence.** Workflow state and the audit log live in Streamlit
  `session_state` for the session only; nothing is written to durable storage.
- **The audit log is not tamper-evident.** It records operator + reason +
  timestamp but is in-memory; a real deployment needs append-only storage.
- **Single-case model.** The dashboard tracks one workflow at a time; no
  case management, no batch import.
- **Command parser is keyword-based.** It has no medical knowledge; it routes
  safe verbs and blocks unsafe ones by pattern. It errs toward "unrecognized"
  rather than guessing, but is not a general NLU.
- **Registration threshold is unvalidated.** `DEFAULT_NMI_THRESHOLD` is a
  conservative placeholder pending phantom calibration (see `docs/validation-plan.md`).
```
