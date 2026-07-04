"""Tests for the segmentation-proposal contract, validation, and confidence gate.

Covers the two safety invariants in segmentation_proposal.py:
- AI proposes / human decides (a non-proposal or pre-accepted output is rejected);
- no false trust (confidence is an honest null until calibration is proven).
Plus the workflow guarantee that metrics stay locked until a human accepts.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

np = pytest.importorskip("numpy")
import segmentation_proposal as sp  # noqa: E402
from neuroplan_ui.slicer_bridge import SegmentationProposal  # noqa: E402


def _proposal(**kw):
    defaults = dict(label_array=np.ones((4, 4, 4), dtype="uint8"),
                    scalar_confidence=0.5)
    defaults.update(kw)
    return SegmentationProposal(**defaults)


# --- validate_proposal: AI proposes, human decides ------------------------

@pytest.mark.unit
def test_valid_proposal_passes():
    sp.validate_proposal(_proposal())  # does not raise


@pytest.mark.unit
def test_rejects_non_proposal():
    with pytest.raises(sp.InvalidProposal, match="is_proposal must be True"):
        sp.validate_proposal(_proposal(is_proposal=False))


@pytest.mark.unit
def test_rejects_preaccepted_proposal():
    with pytest.raises(sp.InvalidProposal, match="already accepted"):
        sp.validate_proposal(_proposal(accepted_by_human=True))


@pytest.mark.unit
def test_rejects_out_of_range_confidence():
    with pytest.raises(sp.InvalidProposal, match="outside"):
        sp.validate_proposal(_proposal(scalar_confidence=1.7))


@pytest.mark.unit
def test_self_rejection_requires_a_reason():
    with pytest.raises(sp.InvalidProposal, match="reject_reason"):
        sp.validate_proposal(_proposal(reject=True, reject_reason="  "))
    # A rejection WITH a reason is a valid loud failure, not a contract violation.
    sp.validate_proposal(_proposal(reject=True, reject_reason="low SNR"))


@pytest.mark.unit
def test_shape_mismatch_is_rejected():
    with pytest.raises(sp.InvalidProposal, match="does not match"):
        sp.validate_proposal(_proposal(), volume_shape=(8, 8, 8))
    sp.validate_proposal(_proposal(), volume_shape=(4, 4, 4))  # matching shape ok


# --- confidence gate: no false trust --------------------------------------

@pytest.mark.unit
def test_confidence_is_null_while_uncalibrated():
    assert sp.CONFIDENCE_CALIBRATED is False  # default posture
    assert sp.displayable_confidence(_proposal(scalar_confidence=0.99)) is None


@pytest.mark.unit
def test_confidence_shown_only_when_calibrated(monkeypatch):
    monkeypatch.setattr(sp, "CONFIDENCE_CALIBRATED", True)
    assert sp.displayable_confidence(_proposal(scalar_confidence=0.8)) == 0.8


@pytest.mark.unit
def test_per_voxel_uncertainty_is_honest_null_by_default():
    # Absent uncertainty is None, never a fabricated array.
    assert _proposal().per_voxel_uncertainty is None
