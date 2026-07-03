"""Streamlit dashboard for the NeuroPlan research workflow.

Run offline with:

    streamlit run neuroplan_ui/app.py

This is a thin presentation layer. All safety logic lives in the imported
modules (workflow gates, pending-action confirmation, banner enforcement); the
UI only renders their state and forwards operator decisions. It runs fully
offline against synthetic data from :mod:`neuroplan_ui.slicer_bridge`.

    Research use only. Not for clinical or intraoperative decision-making.
"""
from __future__ import annotations

import dataclasses

import streamlit as st

from . import export, slicer_bridge
from .banner import RESEARCH_BANNER
from .command_parser import parse_command
from .pending_actions import ActionKind, ActionQueue
from .workflow import Gates, GateState, Stage, STAGE_ORDER, WorkflowState

_GATE_BADGE = {
    GateState.LOCKED: "⛔ locked",
    GateState.READY: "⚪ ready",
    GateState.PASSED: "✅ passed",
    GateState.FAILED: "🔴 FAILED",
    GateState.PROPOSED: "📝 proposed (needs acceptance)",
    GateState.OVERRIDDEN: "⚠️ overridden (logged)",
}


def _init_state() -> None:
    if "workflow" not in st.session_state:
        st.session_state.workflow = WorkflowState.initial()
    if "queue" not in st.session_state:
        st.session_state.queue = ActionQueue()
    if "gates" not in st.session_state:
        try:
            st.session_state.gates = Gates.default()
        except Exception as exc:  # pydicom/numpy missing — surface, don't crash
            st.session_state.gates = None
            st.session_state.gates_error = str(exc)


def _operator() -> str:
    return st.sidebar.text_input(
        "Operator (required to confirm actions)", key="operator").strip()


def _render_banner() -> None:
    st.info(f"🔬 {RESEARCH_BANNER}")


def _render_progress(wf: WorkflowState) -> None:
    st.subheader("Workflow gates")
    cols = st.columns(len(STAGE_ORDER))
    for col, stage in zip(cols, STAGE_ORDER):
        col.markdown(f"**{stage.value}**")
        col.caption(_GATE_BADGE[wf.state_of(stage)])


def _render_command_bar(operator: str) -> None:
    st.subheader("Command (natural language → pending action)")
    st.caption(
        "Commands never run automatically. Recognized safe verbs create a "
        "PENDING action you must confirm below. Clinical-decision requests are "
        "refused.")
    text = st.text_input("Type a command", key="cmd_text")
    if st.button("Parse command") and text:
        result = parse_command(text)
        if result.refused:
            st.error(result.message)
        elif result.unrecognized:
            st.warning(result.message)
        else:
            st.session_state.queue = st.session_state.queue.add(result.action)
            st.success(result.message)


def _render_queue(operator: str) -> None:
    st.subheader("Pending actions — human confirmation required")
    queue: ActionQueue = st.session_state.queue
    pending = queue.pending()
    if not pending:
        st.caption("No pending actions.")
    for action in pending:
        with st.container(border=True):
            st.write(f"**#{action.id} · {action.kind.value}** — "
                     f"“{action.raw_text}”")
            reason = st.text_input(
                "Note (optional)", key=f"reason_{action.id}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirm & run", key=f"confirm_{action.id}"):
                if not operator:
                    st.error("Set an operator name in the sidebar first.")
                else:
                    _confirm_and_run(action.id, operator, reason)
            if c2.button("✋ Reject", key=f"reject_{action.id}"):
                st.session_state.queue = queue.reject(
                    action.id, operator or "unknown", reason)
                st.rerun()


def _confirm_and_run(action_id: int, operator: str, reason: str) -> None:
    queue: ActionQueue = st.session_state.queue
    queue = queue.confirm(action_id, operator, reason)
    action = queue.get(action_id)
    wf: WorkflowState = st.session_state.workflow
    gates: Gates | None = st.session_state.get("gates")
    note = ""
    try:
        wf, note = _execute(action.kind, wf, gates)
        queue = queue.mark_executed(action_id, note)
    except Exception as exc:
        queue = queue.mark_failed(action_id, str(exc))
        note = f"failed: {exc}"
    st.session_state.workflow = wf
    st.session_state.queue = queue
    st.toast(note or "done")
    st.rerun()


def _execute(kind: ActionKind, wf: WorkflowState,
             gates: Gates | None) -> tuple[WorkflowState, str]:
    """Run a confirmed action against synthetic data. Offline demo path."""
    if kind is ActionKind.IMPORT:
        return wf.run_import(["synthetic_case_0"]), "import recorded"
    if kind is ActionKind.DEIDENTIFY:
        if gates is None:
            raise RuntimeError("de-ID gate unavailable (pydicom not installed)")
        wf = wf.run_deidentify([_synthetic_dicom_dataset()], gates)
        return wf, wf.last_message
    if kind is ActionKind.REGISTER:
        if gates is None:
            raise RuntimeError("registration gate unavailable (numpy missing)")
        v = slicer_bridge.load_volume("synthetic_case_0")
        f, m = slicer_bridge.register_and_resample(v, v)
        wf = wf.run_registration(f, m, gates)
        return wf, wf.last_message
    if kind is ActionKind.SEGMENT:
        return wf.propose_segmentation(), "segmentation proposed"
    if kind is ActionKind.METRICS:
        return wf.run_metrics(), "metrics computed"
    if kind is ActionKind.EXPORT:
        return wf.open_export(), "export stage opened"
    if kind is ActionKind.EXPORT_VISUALIZATION:
        wf = wf.open_export(visualization=True)
        return wf, wf.last_message
    raise RuntimeError(f"unhandled action kind {kind}")


def _synthetic_dicom_dataset():
    """Tiny synthetic DICOM-like dataset for the offline dashboard demo."""
    try:
        from pydicom.dataset import Dataset
    except ImportError as exc:  # pragma: no cover - surfaced by Gates.default too
        raise RuntimeError("pydicom is required for the de-ID demo") from exc

    ds = Dataset()
    ds.Rows = 64
    ds.Columns = 64
    ds.Modality = "MR"
    ds.StudyInstanceUID = "1.2.3.4.5"
    ds.SeriesInstanceUID = "1.2.3.4.6"
    return ds


def _render_segmentation_acceptance(operator: str) -> None:
    wf: WorkflowState = st.session_state.workflow
    if wf.state_of(Stage.SEGMENT) is not GateState.PROPOSED:
        return
    st.subheader("Segmentation proposal — surgeon acceptance required")
    st.caption("The AI proposal is an editable draft. Metrics stay locked until "
               "you accept it.")
    reason = st.text_input("Acceptance note", key="seg_accept_reason")
    if st.button("Accept proposal"):
        if not operator:
            st.error("Set an operator name in the sidebar first.")
        else:
            st.session_state.workflow = wf.accept_segmentation(operator, reason)
            st.rerun()


def _render_override(operator: str) -> None:
    wf: WorkflowState = st.session_state.workflow
    all_failed = [s for s in STAGE_ORDER if wf.state_of(s) is GateState.FAILED]
    # De-identification is a hard block — never offer it as overridable.
    hard_blocked = [s for s in all_failed if not wf.can_override(s)]
    for s in hard_blocked:
        st.error(f"🚫 {s.value} FAILED — this is a hard block and cannot be "
                 f"overridden. Fix the input and re-run.")
    failed = [s for s in all_failed if wf.can_override(s)]
    if not failed:
        return
    st.subheader("⚠️ Override a failed gate (logged)")
    stage = st.selectbox("Failed stage", failed, format_func=lambda s: s.value)
    reason = st.text_area("Reason (required, logged to audit)", key="ovr_reason")
    if st.button("Override with logged reason"):
        try:
            st.session_state.workflow = wf.override(stage, operator, reason)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_export() -> None:
    wf: WorkflowState = st.session_state.workflow
    if not wf.is_open(Stage.METRICS):
        return
    st.subheader("Export research artifact")
    if wf.export_summary:
        st.caption(wf.export_summary)
    audit = [dataclasses.asdict(e) | {"stage": e.stage.value} for e in wf.audit]
    artifact = export.build_artifact(
        case_label="synthetic_case_0",
        metrics={"volume_ml": 4.19, "max_diameter_mm": 20.0,
                 "depth_from_surface_mm": 10.0},
        registration_reason=getattr(wf.registration, "reason", "n/a"),
        audit=audit,
        model_path=slicer_bridge.export_model(None, "out/model.obj"),
    )
    st.download_button("Download artifact JSON", export.to_json(artifact),
                       file_name="neuroplan_artifact.json", mime="application/json")
    st.json(artifact)


def _render_audit() -> None:
    wf: WorkflowState = st.session_state.workflow
    if wf.audit:
        with st.expander("Audit log"):
            for e in wf.audit:
                st.text(f"{e.timestamp} · {e.stage.value} · {e.event} · "
                        f"{e.operator} · {e.reason}")


def main() -> None:
    st.set_page_config(page_title="NeuroPlan (research)", page_icon="🔬")
    st.title("NeuroPlan — research planning workflow")
    _render_banner()
    _init_state()
    if st.session_state.get("gates") is None:
        st.warning(
            "Safety gate modules unavailable: "
            f"{st.session_state.get('gates_error', 'unknown')}. "
            "Install requirements-dev.txt to enable de-ID and registration.")
    operator = _operator()
    wf: WorkflowState = st.session_state.workflow
    _render_progress(wf)
    st.caption(f"Last: {wf.last_message}" if wf.last_message else "")
    _render_command_bar(operator)
    _render_queue(operator)
    _render_segmentation_acceptance(operator)
    _render_override(operator)
    _render_export()
    _render_audit()


if __name__ == "__main__":
    main()
