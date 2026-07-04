"""Validation + display policy for AI segmentation proposals.

Pure, Slicer-independent, model-independent. This is the deep-module SEAM the
MONAI / TotalSegmentator call plugs into later: whatever produces a proposal, it
must pass :func:`validate_proposal` before the UI ever sees it, and its
confidence may only reach a human through :func:`displayable_confidence`.

Two safety invariants live here (see docs/safety-and-failure-modes.md and
handoff/DEVELOPMENT-PLAN.md, decision 4):

1. **AI proposes, human decides.** A proposal that claims to be final
   (``is_proposal is False``) is rejected loudly — the model may never emit a
   result, only a draft.
2. **No false trust.** A confidence score is shown to a human ONLY once it has
   been proven to correlate with error (the Phase-7 calibration check). Until
   ``CONFIDENCE_CALIBRATED`` is flipped True, ``displayable_confidence`` returns
   an honest null, so an uncalibrated number can never reach the UI or an export.

Validation is duck-typed: it checks the semantic properties of a proposal
object, so it does not couple this module to the UI dataclass that defines the
contract (``neuroplan_ui.slicer_bridge.SegmentationProposal``).
"""
from __future__ import annotations

from typing import Any

# Flip to True ONLY when the Phase-7 confidence-vs-error AUC check demonstrates
# the model's confidence correlates with actual error. Until then, confidence is
# carried as data but never displayed. Flipping this without that evidence would
# manufacture false trust — do not.
CONFIDENCE_CALIBRATED = False


class InvalidProposal(Exception):
    """Raised when an object does not satisfy the proposal safety contract."""


def validate_proposal(proposal: Any, volume_shape: tuple[int, ...] | None = None
                      ) -> None:
    """Fail loud unless ``proposal`` is a safe, well-formed AI proposal.

    Rejects (raises :class:`InvalidProposal`) when:
    - it claims to be final (``is_proposal`` is not True),
    - it arrives pre-accepted (``accepted_by_human`` is True — only a human step
      may set that),
    - its ``scalar_confidence`` is missing or outside [0, 1],
    - ``volume_shape`` is given and the label array's shape does not match it.

    A self-rejected proposal (``reject is True``) must carry a reason; that is a
    valid loud failure, not a contract violation, so it passes validation with
    its reason intact (the caller decides what to do with a rejected proposal).
    """
    if getattr(proposal, "is_proposal", None) is not True:
        raise InvalidProposal(
            "not a proposal (is_proposal must be True) — the model may never "
            "emit a final segmentation, only an editable draft")

    if getattr(proposal, "accepted_by_human", False):
        raise InvalidProposal(
            "proposal arrived already accepted_by_human — acceptance is a human "
            "step and must never be set by the model")

    conf = getattr(proposal, "scalar_confidence", None)
    if conf is None or not (0.0 <= float(conf) <= 1.0):
        raise InvalidProposal(
            f"scalar_confidence {conf!r} is missing or outside [0, 1]")

    if getattr(proposal, "reject", False) and not str(
            getattr(proposal, "reject_reason", "")).strip():
        raise InvalidProposal(
            "proposal is self-rejected (reject=True) but carries no "
            "reject_reason — a rejection must name its reason (fail loud)")

    if volume_shape is not None:
        label = getattr(proposal, "label_array", None)
        shape = getattr(label, "shape", None)
        if shape is not None and tuple(shape) != tuple(volume_shape):
            raise InvalidProposal(
                f"label array shape {tuple(shape)} does not match the volume "
                f"shape {tuple(volume_shape)}")


def displayable_confidence(proposal: Any) -> float | None:
    """The confidence value that may be shown to a human — or ``None``.

    Returns the proposal's ``scalar_confidence`` ONLY when ``CONFIDENCE_CALIBRATED``
    is True. While confidence is uncalibrated this returns an honest null, so no
    UI or export can display a number that has not been proven predictive.
    """
    if not CONFIDENCE_CALIBRATED:
        return None
    conf = getattr(proposal, "scalar_confidence", None)
    return None if conf is None else float(conf)
