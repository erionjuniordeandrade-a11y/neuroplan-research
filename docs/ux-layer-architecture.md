# NeuroPlan UX layer — architecture

Research use only. Not for clinical or intraoperative decision-making.

## Purpose

A guided, friendly front-end over the existing 3D Slicer extension. It sequences
the research steps and enforces the two hard gates — it does **not** re-implement
any safety logic.

```
Import → De-ID → Fuse/Register → Segment (proposal) → Plan/Metrics → Export
```

## Option A (Streamlit) vs Option B (Dear PyGui)

| Axis | A · Streamlit | B · Dear PyGui |
|---|---|---|
| Time to guided flow | minutes (declarative) | more boilerplate |
| Status badges / step rail | trivial | manual layout |
| Offline / local | yes (localhost) | yes (native) |
| Native Slicer embedding | no (separate process) | closer, still separate |
| Audience fit (surgeon, demo) | web page, zero install feel | desktop app |

**Chosen: A · Streamlit.** For a pre-PMF research MVP the win is iteration speed
and a legible step rail with red/green gate badges. Slicer already runs as a
separate engine invoked over CLI, so a native desktop shell buys little now.
Dear PyGui becomes worth it only if we later need tight in-window 3D interaction.

## Layers

- `neuroplan_ui/pending_actions.py` — closed action vocabulary, including
  explicit `EXPORT_VISUALIZATION`; `PendingAction` and immutable `ActionQueue`
  require named confirmation before execution.
- `neuroplan_ui/command_parser.py` — text-to-single-pending-action. pt-BR and
  English aliases. Out-of-scope requests (diagnosis, treatment, approach,
  navigation, grading) are refused with a named reason **before** any allow-rule
  runs.
- `neuroplan_ui/workflow.py` — immutable `WorkflowState` gate machine. Blocks
  downstream steps (`GateBlocked`, named reason) until de-ID **and**
  registration pass; keeps AI segmentation a *proposal* until
  `accept_segmentation` records named human acceptance.
- `neuroplan_ui/slicer_bridge.py` — single seam to 3D Slicer. The current path
  uses offline synthetic stubs; live Slicer calls remain explicit TODOs and must
  fail loud when implemented.
- `neuroplan_ui/export.py` — banner-stamped research artifact exporter; rejects
  diagnosis, grade, treatment, recommendation, and approach fields.
- `neuroplan_ui/app.py` — Streamlit presentation only; safety logic stays in
  the modules above.

## Safety invariants (enforced in code, covered by tests)

1. No downstream step runs unless de-ID passed **and** registration passed.
2. Every command becomes a PENDING action; execution refuses unconfirmed actions.
3. "Segmente o tumor" creates a pending proposal, never a final segmentation;
   metrics are blocked until the surgeon reviews it.
4. 3D visualization export is a distinct pending action and is labelled
   experimental research visualization, never intraoperative navigation.

## Stubbed (honest about scope)

- Real ASR (microphone) — text interface only; voice is a TODO.
- MONAI/TotalSegmentator segmentation — proposal is a placeholder object.
- Deterministic metrics — returns a stub result (week 4), not fabricated numbers.
- Live Slicer-backed operations — the current bridge uses synthetic local
  stubs; Week 2+ should replace them with explicit Slicer calls.
