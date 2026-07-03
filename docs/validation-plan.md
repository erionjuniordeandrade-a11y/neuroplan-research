# Validation Plan

Two tiers, because they answer different questions. Tier A gives you **true error**;
Tier B gives you **realism and distribution**.

## Tier A — Phantom (ground truth you control)
3D-printed or gel phantoms with **known geometry**: embedded objects of known
volume, position, and depth. This is the only place you obtain true error in mm/mL.

Validate:
- **Registration accuracy** — target registration error (TRE) on fiducials.
- **Metric accuracy** — measured vs. designed volume / max diameter / depth.
- **Reproducibility** — test–retest and inter-operator variability.

Phantom spec + expected geometry live in [`../phantom/README.md`](../phantom/README.md).

## Tier B — Public datasets (realism, distribution)
| Dataset | Use |
|---|---|
| **BraTS** | Multi-sequence MRI with expert masks → segmentation agreement |
| **TCIA** (meningioma / metastasis MRI+CT) | Fusion + superficial-lesion realism |
| **IXI** | Normal MRI → registration baselines |

Validate:
- Dice / Hausdorff-95 of the AI proposal AND of the surgeon-corrected output vs. reference masks.
- Registration-quality metric distribution across cases.
- **Failure-detection sensitivity** — does the tool flag the cases where Dice is low?

## Metrics to report
Dice, Hausdorff-95, TRE (mm), volume error (mL, Bland–Altman), inter-/intra-operator
ICC, SUS, time-to-plan. All framed as **pilot** feasibility.

## Critical calibration check
Verify that the **uncertainty/confidence** score actually correlates with error on
held-out data. A confidence score that does not predict failure is worse than none —
it manufactures false trust. Report the correlation (e.g. AUC of confidence vs.
"Dice below threshold").
