# NeuroPlan

The shared language of NeuroPlan — an offline, research-only 3D Slicer companion
for preoperative planning of superficial supratentorial lesions. Every term here
is used the same way in code, tests, docs, and conversation. This file is a
glossary only; design decisions live in `handoff/` and any `docs/adr/`.

## Workflow & gating

**Gate**:
A quality checkpoint between two workflow stages that must be satisfied before
the downstream stage becomes reachable. A gate is a data state, not a UI hint.
_Avoid_: check, validation step.

**Hard block**:
A gate whose failure can NEVER be overridden, because passing it anyway would be
unsafe. De-identification is the only hard block: a scan that fails it may still
carry PHI. Defined once in `gate_policy.py`.
_Avoid_: hard gate, mandatory check.

**Override**:
An explicit, logged human decision to proceed past a FAILED gate, permitted only
for overridable gates (currently registration quality) and never for a hard
block. Requires a named operator and a non-empty reason.
_Avoid_: bypass, skip, force.

**Stage**:
One step of the ordered research workflow: Import → De-identify → Register/Fuse →
Propose Segmentation → Compute Metrics → Export.
_Avoid_: step (in code the canonical word is stage), phase (a phase is a *plan*
grouping, not a workflow stage).

**Pending action**:
A parsed natural-language command that has been queued but NOT executed. It runs
only after a named human confirms it. The parser produces pending actions; it
never executes.
_Avoid_: command, task, job.

**Confirmation**:
The act by which a named operator authorizes a pending action to execute. The
only path from pending to executed.
_Avoid_: approval, ack.

## AI & human-in-the-loop

**Proposal**:
An AI-generated segmentation offered as an editable draft, never a result. It
carries `accepted_by_human=False` until a human accepts it, and metrics stay
locked until then. The AI proposes; the surgeon decides.
_Avoid_: prediction, output, result, auto-segmentation.

**Acceptance**:
A named human's deliberate act of accepting a proposal, after editing it in the
Segment Editor. Distinct from confirmation (which is about queued actions).
_Avoid_: approval, sign-off.

**Honest null**:
A metric or field that returns "unknown / not computable from the given inputs"
(e.g. `None` with a named reason) rather than a fabricated value. Implausible
values are flagged, never silently clamped or corrected.
_Avoid_: default value, fallback, zero.

## Data, phantom & truth

**Phantom**:
A physical, manufactured object with known embedded geometry, used as the only
source of true error in mm/mL. Not a synthetic array — a real fabricated body.
_Avoid_: model, dummy, synthetic volume.

**Target**:
An embedded object in the phantom of known volume, diameter, centroid, and
depth-from-surface, standing in for a superficial supratentorial lesion.
_Avoid_: lesion (reserve "lesion" for the clinical thing being modeled), object.

**Fiducial**:
A marker at a known coordinate in the phantom, used to measure target
registration error (TRE).
_Avoid_: landmark, marker point.

**Ground truth**:
The known geometry a computed metric is compared against. It has two states:
_candidate_ (`source=design_candidate` — designed values, not yet physical) and
_measured_ (`source=measured` — from a scanned, fabricated phantom). "Validated
against the phantom" may only be claimed against MEASURED ground truth.
_Avoid_: gold standard, reference (unqualified).

**Depth-from-surface**:
The shortest distance from the phantom's outer surface shell to the nearest
point of a target, along the local surface normal. Undefined (honest null)
without the surface geometry.
_Avoid_: depth, distance-to-cortex.

## Output & scope

**Research artifact**:
The offline export describing a run (JSON and/or PDF), always carrying the
research banner and structurally incapable of holding a clinical-decision field
(diagnosis, grade, treatment, approach).
_Avoid_: report (loosely), output file, result.

**Banner**:
The fixed mandatory notice — "Research use only. Not for clinical or
intraoperative decision-making." — stamped on every artifact and screen.
_Avoid_: disclaimer, warning.

**Superficial supratentorial**:
The locked clinical scope: lesions near the brain surface, above the tentorium.
The scope NeuroPlan's phantom and metrics are designed for; anything else is out
of scope by design.
_Avoid_: cortical, shallow (informal).
