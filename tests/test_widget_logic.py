"""Pure widget-logic tests: advance decisions + badge mapping.

Mirrors the de-ID hard-block guarantee from the Slicer widget side (the widget
consults the same gate_policy as the Streamlit workflow), and proves a
PHI-carrying stage cannot be advanced in ANY permutation. Badge mapping is tested
exhaustively over the real GateState enum.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gate_policy  # noqa: E402
import widget_logic  # noqa: E402
from neuroplan_ui.workflow import GateState  # noqa: E402


# --- can_advance: de-ID hard block from the Slicer UI side -----------------

@pytest.mark.unit
@pytest.mark.parametrize("reason", ["", "   ", "looks fine to me",
                                    "I am certain it is clean"])
def test_deid_never_advances_on_failure(reason):
    # No reason, however emphatic, advances a failed de-ID step.
    assert widget_logic.can_advance(gate_policy.DEIDENTIFY, gate_passed=False,
                                    override_reason=reason) is False


@pytest.mark.unit
def test_passed_gate_always_advances():
    assert widget_logic.can_advance(gate_policy.DEIDENTIFY, gate_passed=True) is True
    assert widget_logic.can_advance(gate_policy.REGISTER, gate_passed=True) is True


@pytest.mark.unit
def test_overridable_gate_advances_only_with_reason():
    assert widget_logic.can_advance(gate_policy.REGISTER, gate_passed=False,
                                    override_reason="verified alignment") is True
    assert widget_logic.can_advance(gate_policy.REGISTER, gate_passed=False,
                                    override_reason="   ") is False


@pytest.mark.unit
def test_widget_and_streamlit_agree_on_hard_block():
    # Same shared policy → same answer on the de-ID hard block from both UIs.
    from neuroplan_ui.workflow import Stage, WorkflowState
    wf = WorkflowState.initial()
    assert wf.can_override(Stage.DEIDENTIFY) is False
    assert widget_logic.can_advance(gate_policy.DEIDENTIFY, gate_passed=False,
                                    override_reason="x") is False


# --- badge mapping: exhaustive over the real GateState --------------------

@pytest.mark.unit
def test_badge_defined_for_every_gate_state():
    # Every GateState value must map to a badge — no unknown state slips through.
    for state in GateState:
        badge = widget_logic.badge_for(state.value)
        assert badge in {widget_logic.BADGE_GREEN, widget_logic.BADGE_RED,
                         widget_logic.BADGE_AMBER, widget_logic.BADGE_GREY}


@pytest.mark.unit
def test_badge_semantics():
    assert widget_logic.badge_for("passed") == widget_logic.BADGE_GREEN
    assert widget_logic.badge_for("failed") == widget_logic.BADGE_RED
    assert widget_logic.badge_for("proposed") == widget_logic.BADGE_AMBER
    assert widget_logic.badge_for("overridden") == widget_logic.BADGE_AMBER
    assert widget_logic.badge_for("locked") == widget_logic.BADGE_GREY


@pytest.mark.unit
def test_badge_unknown_state_fails_loud():
    with pytest.raises(ValueError, match="unknown gate state"):
        widget_logic.badge_for("not-a-real-state")
