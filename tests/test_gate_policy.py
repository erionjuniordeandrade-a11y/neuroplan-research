"""The de-ID hard block is defined once (gate_policy) and honored by BOTH the
Streamlit workflow and the Slicer widget — no per-UI re-implementation."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gate_policy  # noqa: E402


def test_deidentify_is_a_hard_block():
    assert not gate_policy.is_overridable(gate_policy.DEIDENTIFY)


def test_registration_is_overridable():
    assert gate_policy.is_overridable(gate_policy.REGISTER)


def test_ui_workflow_can_override_uses_shared_policy():
    from neuroplan_ui.workflow import Stage, WorkflowState
    wf = WorkflowState.initial()
    assert wf.can_override(Stage.REGISTER) is gate_policy.is_overridable(
        gate_policy.REGISTER)
    assert wf.can_override(Stage.DEIDENTIFY) is gate_policy.is_overridable(
        gate_policy.DEIDENTIFY)
    assert wf.can_override(Stage.DEIDENTIFY) is False


def test_slicer_widget_can_advance_refuses_deid_override():
    # The widget must NOT advance past a failed de-ID step, even with a reason,
    # because it consults the same shared gate_policy. Import the widget as a
    # package (its slicer imports are guarded, so it loads offline).
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "NeuroPlan"))
    import NeuroPlanWorkflow.NeuroPlanWorkflow as npw  # noqa: E402

    widget = npw.NeuroPlanWorkflowWidget()
    # Failed de-ID + a reason -> still blocked (hard block).
    assert widget.can_advance(gate_policy.DEIDENTIFY, gate_passed=False,
                              override_reason="looks fine to me") is False
    # Failed registration + a reason -> allowed (overridable judgment call).
    assert widget.can_advance(gate_policy.REGISTER, gate_passed=False,
                              override_reason="verified alignment") is True
    # A passed gate always advances.
    assert widget.can_advance(gate_policy.DEIDENTIFY, gate_passed=True) is True
