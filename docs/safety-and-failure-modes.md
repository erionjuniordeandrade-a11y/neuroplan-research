# Safety & Failure Modes

Unifying rule: **the tool observes and flags; the surgeon decides.** No step
auto-mutates a safety-relevant artifact. Every failure fails *loud*, not silent.

| # | Failure mode | Detection | Mitigation |
|---|---|---|---|
| 1 | PHI leaks into project | De-ID gate scan + tag allowlist | Hard block on import; log manifest; reject non-conforming files |
| 2 | Registration silently misaligned | Registration-quality metric below threshold | Red gate; block downstream; force surgeon confirm/redo — never proceed on a bad transform |
| 3 | AI over-segments / hallucinates lesion | Uncertainty map + confidence + out-of-distribution flag | Proposal-only; land in Segment Editor; auto-reject below confidence floor; report marks AI-assisted regions |
| 4 | Wrong-modality or wrong-orientation input | Header/geometry sanity checks | Refuse and explain; no silent reslice |
| 5 | Metric on incomplete / edited-away mask | Volume/connectivity sanity checks | Flag implausible values (honest nulls, no clamping) |
| 6 | User treats output as clinical | — | Mandatory banner + report language; no treatment fields in the schema by design |
| 7 | Model distribution ≠ input distribution | Validation calibration + OOD detector | Document intended distribution; flag off-distribution cases |
| 8 | Reproducibility loss | — | Save de-id volume + parameter file per case; deterministic metric layer |

## Hardening principles applied
- **Watchdogs observe; humans decide** — AI flags low confidence; it never
  finalizes a segmentation or a plan.
- **Honest nulls** — a failed registration reports "failed," never a silently
  degraded transform; an implausible volume is flagged, never clamped.
- **Name the mechanism; fail loud** — each gate states *why* it blocked.
- **Make the wrong thing structurally impossible** — the report schema has no
  fields for diagnosis, grade, or approach recommendation, so they cannot be emitted.
- **Destructive by opt-in only** — overwriting a prior segmentation requires an
  explicit, logged action.

## Mandatory report banner (verbatim)
> Research use only. Not for clinical or intraoperative decision-making.
> Requires review by a licensed neurosurgeon.
