"""Tests for the gated workflow state machine (safety-critical).

Uses injected fake gates so the state machine is tested without pydicom/numpy.
Covers the spec's hard requirements:
- R2 de-identification blocks import/downstream on rejection,
- R3 registration failure blocks downstream,
- R4 segmentation is a proposal; metrics locked until human acceptance,
- overrides require a named operator and a logged reason.
"""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neuroplan_ui.workflow import (  # noqa: E402
    Gates, GateBlocked, GateState, Stage, WorkflowState,
)


class _DeidReject(Exception):
    pass


def _gates(*, deid_ok: bool = True, reg_pass: bool = True) -> Gates:
    def deidentify(datasets):
        if not deid_ok:
            raise _DeidReject("identifiers remain: PatientName")
        return [("clean", "manifest")]

    def score(fixed, moving, **kw):
        return types.SimpleNamespace(
            passed=reg_pass,
            reason=("accepted" if reg_pass else "LIKELY MISALIGNED — blocked"),
        )

    return Gates(deidentify=deidentify, score_registration=score)


def _through_deid(reg_pass: bool = True) -> tuple[WorkflowState, Gates]:
    gates = _gates(reg_pass=reg_pass)
    wf = WorkflowState.initial().run_import(["case"]).run_deidentify(["ds"], gates)
    return wf, gates


# --- initial locking ------------------------------------------------------

def test_only_import_is_actionable_initially():
    wf = WorkflowState.initial()
    assert wf.state_of(Stage.IMPORT) is GateState.READY
    for stage in (Stage.REGISTER, Stage.SEGMENT, Stage.METRICS, Stage.EXPORT):
        assert wf.state_of(stage) is GateState.LOCKED


# --- R2: de-identification gate -------------------------------------------

def test_cannot_register_before_deidentification():
    wf = WorkflowState.initial().run_import(["case"])
    with pytest.raises(GateBlocked, match="before de-identification"):
        wf.run_registration([[1]], [[1]], _gates())


def test_deid_rejection_blocks_downstream():
    gates = _gates(deid_ok=False)
    wf = WorkflowState.initial().run_import(["case"]).run_deidentify(["ds"], gates)
    assert wf.state_of(Stage.DEIDENTIFY) is GateState.FAILED
    assert wf.state_of(Stage.REGISTER) is GateState.LOCKED
    assert any(e.event == "deid_rejected" for e in wf.audit)


def test_empty_deid_input_fails_loud_and_blocks_downstream():
    wf = WorkflowState.initial().run_import(["case"]).run_deidentify([], _gates())
    assert wf.state_of(Stage.DEIDENTIFY) is GateState.FAILED
    assert wf.state_of(Stage.REGISTER) is GateState.LOCKED
    assert "no datasets supplied" in wf.deid_summary
    assert any(e.event == "deid_rejected" for e in wf.audit)


def test_deid_success_opens_registration():
    wf, _ = _through_deid()
    assert wf.state_of(Stage.DEIDENTIFY) is GateState.PASSED
    assert wf.state_of(Stage.REGISTER) is GateState.READY


# --- R3: registration-quality gate ----------------------------------------

def test_registration_failure_blocks_segmentation():
    wf, gates = _through_deid(reg_pass=False)
    wf = wf.run_registration([[1]], [[1]], gates)
    assert wf.state_of(Stage.REGISTER) is GateState.FAILED
    assert wf.state_of(Stage.SEGMENT) is GateState.LOCKED
    with pytest.raises(GateBlocked):
        wf.propose_segmentation()


def test_registration_pass_opens_segmentation():
    wf, gates = _through_deid()
    wf = wf.run_registration([[1]], [[1]], gates)
    assert wf.state_of(Stage.REGISTER) is GateState.PASSED
    assert wf.state_of(Stage.SEGMENT) is GateState.READY


# --- R4: segmentation is a proposal ---------------------------------------

def test_metrics_locked_until_segmentation_accepted():
    wf, gates = _through_deid()
    wf = wf.run_registration([[1]], [[1]], gates).propose_segmentation()
    assert wf.state_of(Stage.SEGMENT) is GateState.PROPOSED
    assert not wf.segmentation_accepted
    with pytest.raises(GateBlocked, match="accepted"):
        wf.run_metrics()


def test_accept_segmentation_requires_operator():
    wf, gates = _through_deid()
    wf = wf.run_registration([[1]], [[1]], gates).propose_segmentation()
    with pytest.raises(ValueError, match="named operator"):
        wf.accept_segmentation("  ")


def test_accepted_segmentation_unlocks_metrics_and_logs():
    wf, gates = _through_deid()
    wf = (wf.run_registration([[1]], [[1]], gates)
            .propose_segmentation()
            .accept_segmentation("Dr. Erion", "edited margins"))
    assert wf.segmentation_accepted
    wf = wf.run_metrics()
    assert wf.state_of(Stage.METRICS) is GateState.PASSED
    assert any(e.event == "segmentation_accepted" for e in wf.audit)


# --- exports --------------------------------------------------------------

def test_export_blocked_until_metrics_are_computed():
    wf, gates = _through_deid()
    wf = (wf.run_registration([[1]], [[1]], gates)
            .propose_segmentation()
            .accept_segmentation("Dr. Erion"))
    with pytest.raises(GateBlocked, match="before metrics"):
        wf.open_export()


def test_structured_export_opens_after_metrics():
    wf, gates = _through_deid()
    wf = (wf.run_registration([[1]], [[1]], gates)
            .propose_segmentation()
            .accept_segmentation("Dr. Erion")
            .run_metrics()
            .open_export())
    assert wf.state_of(Stage.EXPORT) is GateState.PASSED
    assert "no clinical fields" in wf.export_summary


def test_experimental_visualization_export_is_labeled_non_clinical():
    wf, gates = _through_deid()
    wf = (wf.run_registration([[1]], [[1]], gates)
            .propose_segmentation()
            .accept_segmentation("Dr. Erion")
            .run_metrics()
            .open_export(visualization=True))
    assert wf.state_of(Stage.EXPORT) is GateState.PASSED
    assert "Experimental offline 3D visualization" in wf.export_summary
    assert "not clinical AR or intraoperative navigation" in wf.export_summary


# --- overrides ------------------------------------------------------------

def test_override_requires_reason_and_operator():
    wf, gates = _through_deid(reg_pass=False)
    wf = wf.run_registration([[1]], [[1]], gates)
    with pytest.raises(ValueError, match="reason"):
        wf.override(Stage.REGISTER, "op", "   ")
    with pytest.raises(ValueError, match="operator"):
        wf.override(Stage.REGISTER, "  ", "looked fine on inspection")


def test_override_opens_gate_and_is_logged():
    wf, gates = _through_deid(reg_pass=False)
    wf = wf.run_registration([[1]], [[1]], gates)
    wf = wf.override(Stage.REGISTER, "Dr. Erion", "manually verified alignment")
    assert wf.state_of(Stage.REGISTER) is GateState.OVERRIDDEN
    assert wf.is_open(Stage.REGISTER)
    entry = [e for e in wf.audit if e.event == "gate_overridden"][-1]
    assert entry.operator == "Dr. Erion"
    assert entry.reason == "manually verified alignment"


def test_cannot_override_a_passed_gate():
    wf, gates = _through_deid()
    wf = wf.run_registration([[1]], [[1]], gates)
    with pytest.raises(GateBlocked, match="FAILED state"):
        wf.override(Stage.REGISTER, "op", "reason")


# --- de-identification is a NON-overridable hard block --------------------

def test_deid_gate_cannot_be_overridden():
    # A de-ID rejection carries PHI risk; no human reason may unlock downstream.
    gates = _gates(deid_ok=False)
    wf = WorkflowState.initial().run_import(["case"]).run_deidentify([], gates)
    assert wf.state_of(Stage.DEIDENTIFY) is GateState.FAILED
    assert not wf.can_override(Stage.DEIDENTIFY)
    with pytest.raises(GateBlocked, match="hard block"):
        wf.override(Stage.DEIDENTIFY, "Dr. Erion", "I checked, looks fine")
    assert wf.state_of(Stage.REGISTER) is GateState.LOCKED


# --- upstream regression re-locks already-open downstream stages -----------

def test_upstream_regression_relocks_downstream():
    # Drive the pipeline all the way to METRICS PASSED...
    wf, gates = _through_deid()
    wf = (wf.run_registration([[1]], [[1]], gates)
            .propose_segmentation()
            .accept_segmentation("Dr. Erion", "ok")
            .run_metrics())
    assert wf.state_of(Stage.METRICS) is GateState.PASSED
    assert wf.segmentation_accepted

    # ...then a later de-ID re-run FAILS. Everything downstream must re-lock,
    # and the stale segmentation acceptance must be cleared.
    bad = _gates(deid_ok=False)
    wf = wf.run_deidentify([], bad)
    assert wf.state_of(Stage.DEIDENTIFY) is GateState.FAILED
    for stage in (Stage.REGISTER, Stage.SEGMENT, Stage.METRICS, Stage.EXPORT):
        assert wf.state_of(stage) is GateState.LOCKED, stage
    assert not wf.is_open(Stage.METRICS)
    assert not wf.segmentation_accepted


# --- default gates wire to the real safety modules ------------------------

def test_default_gates_bind_real_modules():
    pytest.importorskip("pydicom")
    pytest.importorskip("numpy")
    gates = Gates.default()
    assert callable(gates.deidentify)
    assert callable(gates.score_registration)
