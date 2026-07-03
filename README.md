# NeuroPlan (research)

An **offline, open-source research aid** for preoperative planning of **superficial
supratentorial cranial lesions**, built as a 3D Slicer extension. It helps a
neurosurgeon import de-identified imaging, register/fuse MRI+CT, obtain an
AI-*assisted* segmentation proposal, generate a 3D model, compute basic planning
metrics, and export a structured research report.

> **Research use only.** Not a medical device. Not for clinical deployment,
> autonomous diagnosis, intraoperative guidance, or treatment decisions. Every
> output must be reviewed by a licensed neurosurgeon. Use phantom, public, or
> fully de-identified data only.

## What it is / is not

| Is | Is not |
|---|---|
| A research workflow on already-acquired, de-identified imaging | A diagnostic or decision-support device |
| An AI that *proposes* segmentations for a surgeon to correct | An autonomous segmenter |
| A deterministic geometry/metric calculator | An approach/treatment recommender |
| Offline, reproducible from de-id volume + parameter file | Networked / PACS-integrated / OR-integrated |

## Scope (MVP)

- **Lesions:** superficial supratentorial only.
- **Fusion:** single pair — MRI **T1-post** + **CT**, rigid/affine registration.
- **Data:** public datasets (BraTS / TCIA / IXI) + geometric phantoms. **No** real
  prospective or institutional patient data in the MVP.

See [`docs/EXCLUSIONS.md`](docs/EXCLUSIONS.md) for what is deliberately out of scope.

## Architecture

Layered, offline-first, host = 3D Slicer (extension, **not** a fork):

```
DICOM ─▶ [De-ID gate] ─▶ [Registration/fusion + quality gate] ─▶
        [AI segmentation PROPOSAL + uncertainty] ─▶ [Segment Editor (human)] ─▶
        [3D model + deterministic metrics] ─▶ [Structured research report]
```

Unifying rule: **the tool observes and flags; the surgeon decides.** No step
auto-mutates a safety-relevant artifact; every failure fails *loud*, not silent.

## Documentation

- [`docs/research-protocol.md`](docs/research-protocol.md) — IRB/CEP-ready protocol skeleton
- [`docs/validation-plan.md`](docs/validation-plan.md) — phantom + public-data validation
- [`docs/safety-and-failure-modes.md`](docs/safety-and-failure-modes.md) — failure modes & mitigations
- [`docs/de-identification-SOP.md`](docs/de-identification-SOP.md) — the ingestion gate SOP
- [`docs/EXCLUSIONS.md`](docs/EXCLUSIONS.md) — explicit non-goals
- [`handoff/ARCHITECT-BRIEF.md`](handoff/ARCHITECT-BRIEF.md) — 6-week MVP build plan

## Status

Week 1 scaffold. Regulatory posture: research software, **not** submitted as SaMD;
confined to research use. Aligned with CFM Resolution 2.454/2026 (AI as decision
*support*; physician retains responsibility).

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
