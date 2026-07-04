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

from . import deid_gate, gate_policy, metrics, registration_quality

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
    def compute_metrics(self, segmentation_node, fiducials=None,
                        surface_node=None):
        """Deterministic geometry: volume (mL), max diameter (mm),
        depth-from-surface (mm), distance-to-fiducial (mm). The math lives in the
        tested, Slicer-independent :mod:`metrics` module (phantom-anchored, honest
        nulls, flags implausible values instead of clamping). This method's only
        job is the Slicer seam: turn nodes into arrays + spacing, then delegate.

        Prefer :meth:`compute_metrics_from_arrays` in tests and offline callers —
        it needs no Slicer node."""
        mask, spacing = self._array_and_spacing(segmentation_node)
        surface_mask = (self._array_and_spacing(surface_node)[0]
                        if surface_node is not None else None)
        fiducial_mm = fiducials[0] if fiducials else None
        return metrics.compute_metrics(
            mask, spacing, surface_mask=surface_mask, fiducial_mm=fiducial_mm)

    def compute_metrics_from_arrays(self, mask, spacing, *,
                                    surface_mask=None, fiducial_mm=None,
                                    origin=(0.0, 0.0, 0.0)):
        """Slicer-free entry point to the metric layer (delegates to
        :func:`metrics.compute_metrics`). This is what the tests exercise."""
        return metrics.compute_metrics(
            mask, spacing, surface_mask=surface_mask,
            fiducial_mm=fiducial_mm, origin=origin)

    @staticmethod
    def _array_and_spacing(node):
        """TODO(week4, Slicer seam): extract a binary label array + (sx,sy,sz)
        spacing from a Slicer segmentation/volume node. Only reachable inside a
        running 3D Slicer; offline callers use ``compute_metrics_from_arrays``."""
        if not _IN_SLICER:
            raise NotImplementedError(
                "node->array extraction requires a running 3D Slicer; use "
                "compute_metrics_from_arrays(mask, spacing) offline")
        # In Slicer: slicer.util.arrayFromSegmentBinaryLabelmap(...) for the mask
        # and node.GetSpacing() for the voxel spacing.
        raise NotImplementedError("week 4 — Slicer node extraction")

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

    def can_advance(self, stage_key: str, gate_passed: bool,
                    override_reason: str = "") -> bool:
        """Next unlocks only when the step gate passes, or the surgeon explicitly
        overrides with a logged reason — EXCEPT for hard-block stages.

        The hard-block rule (de-identification) comes from the shared
        ``gate_policy`` module, the same source neuroplan_ui/workflow.py uses, so
        a PHI-carrying scan can never be waved through from either UI. ``stage_key``
        is a canonical key from :mod:`gate_policy` (e.g. ``gate_policy.DEIDENTIFY``).
        """
        if gate_passed:
            return True
        if not gate_policy.is_overridable(stage_key):
            return False  # hard block — no override, no matter the reason
        if override_reason.strip():
            # TODO: append {step, reason, operator, timestamp} to the case audit log.
            return True
        return False
