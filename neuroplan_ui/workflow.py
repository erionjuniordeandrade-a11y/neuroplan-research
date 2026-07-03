"""The gated research workflow state machine.

Orchestrates the six research stages the spec requires:

    Import -> De-identify -> Register/Fuse -> Propose Segmentation
           -> Compute Metrics -> Export Research Artifacts

Every stage has a GATE. A downstream stage is *structurally* locked (its state
is ``LOCKED``) until the upstream gate is open (``PASSED`` or ``OVERRIDDEN``).
This is a data guarantee, not a UI hint: the widget cannot advance the model
past a failed gate without either passing it or an explicit, logged human
override.

Safety invariants enforced here (mapping to the spec requirements):
- R2  De-identification blocks import: :meth:`run_deidentify` is the only way to
      open the REGISTER stage, and a :class:`DeidRejection` leaves it locked.
- R3  Registration quality blocks downstream: a failed score leaves SEGMENT and
      everything after it locked.
- R4  Segmentation is a proposal, never a result: :meth:`propose_segmentation`
      records a proposal with ``accepted_by_human=False``; METRICS refuses to
      open until :meth:`accept_segmentation` records human acceptance.
- Human confirmation: :meth:`override` and :meth:`accept_segmentation` require a
      named operator and (for overrides) a non-empty reason, and append to an
      immutable audit log.

The gate functions are injected (:class:`Gates`) so this module is unit-testable
without pydicom / numpy / Slicer, and so the real safety modules remain the
single source of truth for *how* to de-identify and score a registration.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Sequence


class Stage(str, Enum):
    IMPORT = "Import"
    DEIDENTIFY = "De-identify"
    REGISTER = "Register/Fuse"
    SEGMENT = "Propose Segmentation"
    METRICS = "Compute Metrics"
    EXPORT = "Export Research Artifacts"


STAGE_ORDER: tuple[Stage, ...] = (
    Stage.IMPORT, Stage.DEIDENTIFY, Stage.REGISTER,
    Stage.SEGMENT, Stage.METRICS, Stage.EXPORT,
)


class GateState(str, Enum):
    LOCKED = "locked"          # upstream not satisfied; cannot act
    READY = "ready"            # upstream open; this stage may run
    PASSED = "passed"          # gate satisfied
    FAILED = "failed"          # gate ran and blocked
    PROPOSED = "proposed"      # segmentation only: proposal exists, unaccepted
    OVERRIDDEN = "overridden"  # gate failed but human accepted responsibility


# States that let the *next* stage proceed.
_OPEN_STATES = frozenset({GateState.PASSED, GateState.OVERRIDDEN})

# Gates a human may override with a logged reason. De-identification is a HARD
# BLOCK and is deliberately absent: a scan that fails de-ID carries PHI and must
# never reach downstream stages, override or not. Registration quality is a
# judgment call the surgeon is allowed to accept responsibility for.
_OVERRIDABLE_STAGES = frozenset({Stage.REGISTER})


class GateBlocked(RuntimeError):
    """Raised when an action is attempted on a stage whose gate is not open."""


@dataclasses.dataclass(frozen=True)
class AuditEntry:
    stage: Stage
    event: str
    operator: str
    reason: str
    timestamp: str


@dataclasses.dataclass(frozen=True)
class Gates:
    """Injected gate implementations. Defaults bind the real safety modules."""

    deidentify: Callable[[Sequence[Any]], list[Any]]
    score_registration: Callable[..., Any]

    @staticmethod
    def default() -> "Gates":
        # Lazy imports: the real gates pull in pydicom / numpy, which need not be
        # present to construct or test the state machine with fakes.
        import os
        import sys

        pkg = os.path.join(os.path.dirname(__file__), "..",
                           "NeuroPlan", "NeuroPlanWorkflow")
        if pkg not in sys.path:
            sys.path.insert(0, pkg)
        import deid_gate  # type: ignore
        import registration_quality  # type: ignore

        return Gates(
            deidentify=deid_gate.gate_files,
            score_registration=registration_quality.score,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclasses.dataclass(frozen=True)
class WorkflowState:
    gates: dict[Stage, GateState]
    audit: tuple[AuditEntry, ...] = ()
    # Lightweight facts surfaced to the UI; never patient data.
    deid_summary: str = ""
    registration: Any = None      # RegistrationQuality | None
    segmentation_accepted: bool = False
    export_summary: str = ""
    last_message: str = ""

    # ---- construction ----------------------------------------------------
    @staticmethod
    def initial() -> "WorkflowState":
        gates = {s: GateState.LOCKED for s in STAGE_ORDER}
        gates[Stage.IMPORT] = GateState.READY
        return WorkflowState(gates=gates)

    # ---- queries ---------------------------------------------------------
    def state_of(self, stage: Stage) -> GateState:
        return self.gates[stage]

    def is_open(self, stage: Stage) -> bool:
        return self.gates[stage] in _OPEN_STATES

    def can_override(self, stage: Stage) -> bool:
        """True only for gates a human is permitted to override. De-ID is a hard
        block and always returns False here."""
        return stage in _OVERRIDABLE_STAGES

    def can_run(self, stage: Stage) -> bool:
        """True when ``stage`` is unlocked and every prior stage is open."""
        idx = STAGE_ORDER.index(stage)
        if any(self.gates[s] not in _OPEN_STATES for s in STAGE_ORDER[:idx]):
            return False
        return self.gates[stage] in (
            GateState.READY, GateState.FAILED, GateState.PROPOSED,
            GateState.PASSED, GateState.OVERRIDDEN,
        )

    # ---- internal transition helper -------------------------------------
    def _transition(self, changes: dict[Stage, GateState], *,
                    audit: AuditEntry | None = None, message: str = "",
                    **fields: Any) -> "WorkflowState":
        new_gates = dict(self.gates)
        new_gates.update(changes)
        # Re-lock stages whose upstream is no longer open, and open the stage
        # immediately after the last open one.
        _recompute_readiness(new_gates)
        new_audit = self.audit + (audit,) if audit else self.audit
        new_state = dataclasses.replace(
            self, gates=new_gates, audit=new_audit,
            last_message=message or self.last_message, **fields)
        # If the segmentation stage got re-locked by an upstream regression, its
        # human acceptance no longer holds — clear it so downstream can never
        # run on a stale approval.
        if not new_state.is_open(Stage.SEGMENT) and new_state.segmentation_accepted:
            new_state = dataclasses.replace(new_state, segmentation_accepted=False)
        return new_state

    # ---- stage actions ---------------------------------------------------
    def run_import(self, file_refs: Sequence[str]) -> "WorkflowState":
        if not self.can_run(Stage.IMPORT):
            raise GateBlocked("Import stage is not ready")
        n = len(list(file_refs))
        return self._transition(
            {Stage.IMPORT: GateState.PASSED},
            message=f"Registered {n} file reference(s) for de-identification.",
        )

    def run_deidentify(self, datasets: Sequence[Any],
                       gates: Gates) -> "WorkflowState":
        """R2: run the de-ID hard block. Success opens REGISTER; a rejection
        leaves DEIDENTIFY (and everything downstream) blocked."""
        if not self.is_open(Stage.IMPORT):
            raise GateBlocked("cannot de-identify before Import")
        dataset_list = list(datasets)
        if not dataset_list:
            reason = "no datasets supplied to de-identification gate"
            entry = AuditEntry(Stage.DEIDENTIFY, "deid_rejected", "system",
                               reason, _now_iso())
            return self._transition(
                {Stage.DEIDENTIFY: GateState.FAILED}, audit=entry,
                message=f"De-identification REJECTED: {reason}",
                deid_summary=f"rejected: {reason}")
        try:
            results = gates.deidentify(dataset_list)
        except Exception as exc:  # DeidRejection or any scrub failure — fail loud
            entry = AuditEntry(Stage.DEIDENTIFY, "deid_rejected", "system",
                               str(exc), _now_iso())
            return self._transition(
                {Stage.DEIDENTIFY: GateState.FAILED}, audit=entry,
                message=f"De-identification REJECTED: {exc}",
                deid_summary=f"rejected: {exc}")
        summary = f"{len(results)} dataset(s) de-identified and cleared."
        return self._transition(
            {Stage.DEIDENTIFY: GateState.PASSED},
            message=summary, deid_summary=summary)

    def run_registration(self, fixed: Any, moving: Any, gates: Gates,
                         threshold: float | None = None) -> "WorkflowState":
        """R3: score the registration and gate downstream on the result."""
        if not self.is_open(Stage.DEIDENTIFY):
            raise GateBlocked("cannot register before de-identification passes")
        kwargs = {} if threshold is None else {"threshold": threshold}
        quality = gates.score_registration(fixed, moving, **kwargs)
        if getattr(quality, "passed", False):
            return self._transition(
                {Stage.REGISTER: GateState.PASSED},
                message=quality.reason, registration=quality)
        entry = AuditEntry(Stage.REGISTER, "registration_failed", "system",
                           getattr(quality, "reason", ""), _now_iso())
        return self._transition(
            {Stage.REGISTER: GateState.FAILED}, audit=entry,
            message=quality.reason, registration=quality)

    def propose_segmentation(self) -> "WorkflowState":
        """R4: record a segmentation PROPOSAL. Not a result — METRICS stays
        locked until a human accepts it via :meth:`accept_segmentation`."""
        if not self.is_open(Stage.REGISTER):
            raise GateBlocked("cannot segment before registration is open")
        return self._transition(
            {Stage.SEGMENT: GateState.PROPOSED},
            segmentation_accepted=False,
            message="Segmentation PROPOSED — editable draft; requires surgeon "
                    "acceptance before metrics.")

    def accept_segmentation(self, operator: str,
                            reason: str = "") -> "WorkflowState":
        """Human-in-the-loop acceptance of the proposal (R4 + confirmation)."""
        if self.gates[Stage.SEGMENT] is not GateState.PROPOSED:
            raise GateBlocked("no segmentation proposal to accept")
        if not operator.strip():
            raise ValueError("accepting a segmentation requires a named operator")
        entry = AuditEntry(Stage.SEGMENT, "segmentation_accepted",
                           operator.strip(), reason.strip(), _now_iso())
        return self._transition(
            {Stage.SEGMENT: GateState.PASSED}, audit=entry,
            segmentation_accepted=True,
            message=f"Segmentation accepted by {operator.strip()}.")

    def override(self, stage: Stage, operator: str,
                 reason: str) -> "WorkflowState":
        """Explicit, logged human override of a FAILED gate. Requires a named
        operator and a non-empty reason — an unexplained override is refused.

        De-identification is NOT overridable: a de-ID failure means PHI may
        remain, which no human reason can make safe. Attempting to override it
        is refused loudly."""
        if stage not in _OVERRIDABLE_STAGES:
            raise GateBlocked(
                f"{stage.value} is a hard block and cannot be overridden "
                f"(only {', '.join(s.value for s in _OVERRIDABLE_STAGES)} may "
                f"be overridden)")
        if self.gates[stage] is not GateState.FAILED:
            raise GateBlocked(f"{stage.value} is not in a FAILED state to override")
        if not operator.strip():
            raise ValueError("override requires a named operator")
        if not reason.strip():
            raise ValueError("override requires a non-empty reason (logged)")
        entry = AuditEntry(stage, "gate_overridden", operator.strip(),
                           reason.strip(), _now_iso())
        return self._transition(
            {stage: GateState.OVERRIDDEN}, audit=entry,
            message=f"{stage.value} gate OVERRIDDEN by {operator.strip()} "
                    f"(reason logged).")

    def run_metrics(self) -> "WorkflowState":
        if not self.is_open(Stage.SEGMENT):
            raise GateBlocked(
                "cannot compute metrics before a segmentation is accepted")
        if not self.segmentation_accepted:
            raise GateBlocked(
                "segmentation proposal has not been accepted by a human")
        return self._transition(
            {Stage.METRICS: GateState.PASSED},
            message="Deterministic metrics computed (phantom-anchored).")

    def open_export(self, *, visualization: bool = False) -> "WorkflowState":
        if not self.is_open(Stage.METRICS):
            raise GateBlocked("cannot export before metrics are computed")
        summary = (
            "Experimental offline 3D visualization export ready — research "
            "artifact only; not clinical AR or intraoperative navigation."
            if visualization else
            "Structured research artifact export ready — no clinical fields."
        )
        return self._transition(
            {Stage.EXPORT: GateState.PASSED},
            message=summary, export_summary=summary)


def _recompute_readiness(gates: dict[Stage, GateState]) -> None:
    """Lock any stage whose upstream is not open; mark the first blocked stage
    after an open run as READY (unless it already carries its own result).

    Once the open chain breaks, EVERY downstream stage is forced back to LOCKED
    — including ones that had already PASSED / been PROPOSED / been OVERRIDDEN.
    Otherwise a later upstream regression (e.g. re-running de-ID to a failure)
    would leave a stale-open downstream stage, and export could run on invalid
    upstream state. In normal forward progress no downstream stage is ever open
    ahead of its upstream, so this only ever fires on a genuine regression."""
    open_so_far = True
    for stage in STAGE_ORDER:
        if not open_so_far:
            # Upstream broken: re-lock everything downstream, unconditionally.
            gates[stage] = GateState.LOCKED
            continue
        if gates[stage] in _OPEN_STATES:
            continue
        # First not-yet-open stage on an open chain becomes actionable.
        if gates[stage] is GateState.LOCKED:
            gates[stage] = GateState.READY
        open_so_far = False
