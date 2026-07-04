"""Single source of truth for which workflow gates a human may override.

De-identification is a HARD BLOCK: a scan that fails de-ID may still carry PHI,
and no human reason can make that safe. Both the offline Streamlit workflow
(``neuroplan_ui/workflow.py``) and the in-Slicer widget
(``NeuroPlanWorkflow.py``) consult THIS module so the rule cannot drift between
the two code paths (hardening: never a "KEEP IN SYNC" comment — share one
source). Stage keys are canonical lowercase identifiers, independent of either
UI's display labels.
"""
from __future__ import annotations

# Canonical stage keys used across both UIs.
IMPORT = "import"
DEIDENTIFY = "deidentify"
REGISTER = "register"
SEGMENT = "segment"
METRICS = "metrics"
EXPORT = "export"

# Gates a FAILED result may NEVER be overridden past. De-identification is the
# one true hard block: overriding it would let PHI through.
HARD_BLOCK_STAGES: frozenset[str] = frozenset({DEIDENTIFY})


def is_overridable(stage_key: str) -> bool:
    """True if a FAILED gate at ``stage_key`` may be overridden by a human with a
    logged reason. Always False for a hard-block stage (e.g. de-identification).
    """
    return stage_key not in HARD_BLOCK_STAGES
