"""NeuroPlanWorkflow — 3D Slicer scripted module (guided, research-only).

A single linear wizard wrapping the native Slicer tools so surgeons unfamiliar
with Slicer follow one ordered path:

    Import -> Fuse -> Segment -> Model -> Measure -> Report

Each step has a quality GATE that must pass (or be explicitly overridden with a
logged reason) before Next unlocks. The AI only *proposes*; the surgeon edits in
the native Segment Editor. No diagnosis / approach / intraoperative logic exists.

This is a scaffold: step logic is stubbed with clear TODOs, but the safety gates
(de-ID, registration quality) call the real, tested standalone modules.
"""
from __future__ import annotations

# NOTE: slicer / qt / ctk imports only resolve inside a running 3D Slicer.
try:
    import slicer  # type: ignore
    from slicer.ScriptedLoadableModule import (  # type: ignore
        ScriptedLoadableModule, ScriptedLoadableModuleWidget,
        ScriptedLoadableModuleLogic,
    )
    _IN_SLICER = True
except ImportError:  # doc/lint/test environments
    _IN_SLICER = False
    ScriptedLoadableModule = object            # type: ignore
    ScriptedLoadableModuleWidget = object      # type: ignore
    ScriptedLoadableModuleLogic = object       # type: ignore

from . import deid_gate, registration_quality

BANNER = (
    "Research use only. Not for clinical or intraoperative decision-making. "
    "Requires review by a licensed neurosurgeon."
)

STEPS = ("Import", "Fuse", "Segment", "Model", "Measure", "Report")


class NeuroPlanWorkflow(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "NeuroPlan Workflow (research)"
        parent.categories = ["Research"]
        parent.contributors = ["NeuroPlan contributors"]
        parent.helpText = (
            "Guided, offline, research-only planning workflow for superficial "
            "supratentorial lesions. " + BANNER
        )
        parent.acknowledgementText = "Built on 3D Slicer. Apache-2.0."


class NeuroPlanWorkflowLogic(ScriptedLoadableModuleLogic):
    """Business logic — deliberately thin over the tested standalone modules."""

    # --- Step 1: Import + de-ID gate (hard block) --------------------------
    def import_and_deidentify(self, datasets):
        """Run the de-ID gate. Raises deid_gate.DeidRejection on any identifier
        that survives — the caller must surface the rejection, never import."""
        return deid_gate.gate_files(datasets)

    # --- Step 2: Registration quality gate --------------------------------
    def evaluate_registration(self, fixed_array, moving_array, threshold=None):
        """Score the registration. Returns a RegistrationQuality; the widget
        blocks Next when passed is False."""
        kwargs = {} if threshold is None else {"threshold": threshold}
        return registration_quality.score(fixed_array, moving_array, **kwargs)

    # --- Step 3: AI segmentation PROPOSAL ---------------------------------
    def propose_segmentation(self, volume_node):
        """TODO(week3): call MONAI Label / TotalSegmentator; return a candidate
        label map + per-voxel uncertainty + scalar confidence + reject flag.
        The proposal is loaded into the Segment Editor for the surgeon to CORRECT.
        It is never treated as final."""
        raise NotImplementedError("week 3")

    # --- Step 5: Deterministic planning metrics ---------------------------
    def compute_metrics(self, segmentation_node, fiducials=None):
        """TODO(week4): volume (mL), max diameter (mm), depth-from-surface (mm),
        distance-to-fiducial (mm). Pure geometry, phantom-anchored. Flags
        implausible values (honest nulls) instead of clamping."""
        raise NotImplementedError("week 4")

    # --- Step 6: Structured research report -------------------------------
    def build_report(self, case):
        """TODO(week5): emit JSON + PDF with the mandatory banner. The schema has
        NO fields for diagnosis, grade, or approach — structurally impossible to
        emit clinical recommendations."""
        raise NotImplementedError("week 5")


class NeuroPlanWorkflowWidget(ScriptedLoadableModuleWidget):
    """Guided single-panel wizard. TODO(week6): full UI. Scaffold documents the
    intended step gating so the build order is unambiguous."""

    def setup(self):
        if _IN_SLICER:
            ScriptedLoadableModuleWidget.setup(self)
        self.logic = NeuroPlanWorkflowLogic()
        self._step = 0
        # TODO(week1-6): progress rail, per-step panels, red/green gate badges,
        # "override with reason" (logged), always-visible report preview + banner.

    def can_advance(self, gate_passed: bool, override_reason: str = "") -> bool:
        """Next unlocks only when the step gate passes, or the surgeon explicitly
        overrides with a logged reason."""
        if gate_passed:
            return True
        if override_reason.strip():
            # TODO: append {step, reason, operator, timestamp} to the case audit log.
            return True
        return False
