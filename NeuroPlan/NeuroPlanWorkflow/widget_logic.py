"""Pure decision logic for the in-Slicer widget.

Everything the Slicer widget decides — can the surgeon advance past a step, what
badge colour a gate shows — lives here as pure functions over plain state (no Qt,
no Slicer, no widgets). The widget becomes a thin renderer that calls these, so
the safety-relevant logic is unit-tested without a running 3D Slicer.

The de-ID hard block is enforced through the shared :mod:`gate_policy`, the SAME
source the Streamlit workflow uses — a PHI-carrying stage cannot be advanced from
either UI.
"""
from __future__ import annotations

try:  # package context (inside 3D Slicer / the NeuroPlanWorkflow package)
    from . import gate_policy
except ImportError:  # top-level import (tests / offline, dir on sys.path)
    import gate_policy  # type: ignore


# Badge semantics for a stage's gate state — UI-agnostic (the widget maps these
# to colours/icons). Kept as plain strings so this module never imports the
# neuroplan_ui GateState enum (correct layering: NeuroPlan/ depends on nothing UI).
BADGE_GREEN = "green"   # gate passed
BADGE_RED = "red"       # gate failed
BADGE_AMBER = "amber"   # needs human attention (proposal awaiting accept / overridden)
BADGE_GREY = "grey"     # inactive (locked or merely ready)

_BADGE_BY_STATE: dict[str, str] = {
    "locked": BADGE_GREY,
    "ready": BADGE_GREY,
    "passed": BADGE_GREEN,
    "failed": BADGE_RED,
    "proposed": BADGE_AMBER,
    "overridden": BADGE_AMBER,
}


def badge_for(gate_state_key: str) -> str:
    """Map a gate-state key (e.g. ``GateState.FAILED.value`` == ``"failed"``) to a
    badge. Fails loud on an unknown state rather than silently defaulting."""
    try:
        return _BADGE_BY_STATE[gate_state_key]
    except KeyError:
        raise ValueError(f"unknown gate state {gate_state_key!r}")


def can_advance(stage_key: str, gate_passed: bool,
                override_reason: str = "") -> bool:
    """Whether the widget may unlock the step after ``stage_key``.

    - A passed gate always advances.
    - A hard-block stage (de-identification, per :mod:`gate_policy`) NEVER
      advances on a failure, no matter the reason.
    - Any other failed gate advances only with a non-empty, logged reason.
    """
    if gate_passed:
        return True
    if not gate_policy.is_overridable(stage_key):
        return False  # hard block — no override, no matter the reason
    return bool(override_reason.strip())
