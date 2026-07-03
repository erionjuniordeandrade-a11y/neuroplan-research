# Research Protocol Skeleton (IRB / CEP-CONEP)

> Fill the bracketed fields. Structure written for a Brazilian CEP/CONEP submission;
> generic enough to adapt. This study is **methodological / technical validation**,
> **non-interventional**, and changes **no patient's care**.

## 1. Title & type
- **Title:** [Feasibility and validation of an offline research workflow for
  preoperative planning of superficial supratentorial lesions in 3D Slicer]
- **Type:** Retrospective, non-interventional methodological validation on
  de-identified public imaging + geometric phantoms.

## 2. Objectives
- **Primary:** Assess feasibility, segmentation agreement, and planning-metric
  accuracy of the workflow versus reference standards.
- **Secondary:** Assess usability for surgeons unfamiliar with native 3D Slicer.

## 3. Design
Retrospective analysis of public/de-identified datasets and phantom scans. No
prospective enrollment; no clinical decisions derived from outputs.

## 4. Data sources & handling
- **Sources (MVP):** public datasets only — BraTS, TCIA collections, IXI — plus
  in-house geometric phantoms. **No** institutional patient data in the MVP.
- **De-identification:** all imaging passes the de-ID gate SOP
  (`de-identification-SOP.md`) before ingestion. A de-ID manifest is logged per case.
- **Storage:** offline, encrypted at rest, access-logged. No network transfer.
- **No re-identification** attempts of any kind.

## 5. Ethics points (state explicitly)
- (a) Not a medical device / not for clinical use — research software only.
- (b) All outputs reviewed by a licensed neurosurgeon.
- (c) Public de-identified data → typically qualifies as non-human-subjects or
  minimal-risk; document the determination the CEP requires.
- (d) No autonomous AI decision — aligns with **CFM Resolution 2.454/2026**
  (AI as decision support; physician retains responsibility).
- (e) Data offline/encrypted/access-logged; no re-identification.

## 6. Risks & benefits
- **Risk:** essentially none to patients (retrospective, de-identified, public).
  Residual risk = re-identification → mitigated by the de-ID SOP + public-only data.
- **Benefit:** methodological; potential to lower the barrier to research-grade
  planning workflows.

## 7. Endpoints & statistics
- Segmentation: Dice, Hausdorff-95 (AI proposal vs reference; surgeon-corrected vs reference).
- Registration: target registration error (mm) on fiducials; registration-quality distribution.
- Metrics: volume error (mL, Bland–Altman), diameter/depth error (mm) vs phantom ground truth.
- Reproducibility: inter-/intra-operator ICC.
- Usability: System Usability Scale (SUS); time-to-plan.
- **Reporting:** pilot-scale feasibility. Never use the word "validated" for small N.

## 8. Regulatory note
Not submitted as SaMD; confined to research use. Attach a short statement to that
effect if the CEP asks about device classification.
