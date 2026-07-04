"""Thin integration seam between the dashboard and 3D Slicer.

Requirement 1: 3D Slicer stays the technical engine. This module is the *only*
place the dashboard talks to Slicer, so the UX layer never grows its own image
processing. When Slicer is present, calls would dispatch to ``slicer.util`` and
the native modules (registration via BRAINSFit/Elastix, segmentation via MONAI
Label, model export via the Model maker).

Slicer is NOT importable in a plain Python process, so every function here has
an **offline stub** that returns small synthetic NumPy arrays. That keeps the
whole dashboard runnable and testable offline (spec: offline, phantom/synthetic
data only) while the real Slicer calls remain clearly marked TODOs.

STUB STATUS (see neuroplan_ui/README.md for the authoritative list):
- load_volume            : STUB — returns a synthetic volume, does not read disk.
- register_and_resample  : STUB — returns synthetic fixed/moving arrays.
- propose_segmentation   : STUB — returns a synthetic proposal label array.
- export_model           : STUB — writes nothing to Slicer; viz-only placeholder.
"""
from __future__ import annotations

import dataclasses
from typing import Any

try:
    import numpy as np
except ImportError:  # numpy absent in doc-only environments
    np = None  # type: ignore

try:  # pragma: no cover - only true inside a running 3D Slicer
    import slicer  # type: ignore
    _IN_SLICER = True
except ImportError:
    _IN_SLICER = False


def _require_numpy() -> None:
    if np is None:
        raise RuntimeError("numpy is required for the offline Slicer stubs")


@dataclasses.dataclass(frozen=True)
class VolumeHandle:
    """Opaque handle to a volume. In Slicer this wraps a vtkMRMLVolumeNode; in
    the stub it carries a synthetic array so downstream stages have real data."""

    name: str
    array: Any            # numpy array (stub) or None when backed by a node
    is_synthetic: bool = True


def load_volume(file_ref: str, *, seed: int = 0) -> VolumeHandle:
    """STUB: return a synthetic volume for ``file_ref``.

    Real implementation would call ``slicer.util.loadVolume(file_ref)`` on
    already de-identified data. This stub never touches disk."""
    if _IN_SLICER:  # pragma: no cover
        raise NotImplementedError(
            "Slicer-backed load_volume is not implemented yet (week-2 work)")
    _require_numpy()
    rng = np.random.default_rng(seed)
    return VolumeHandle(name=file_ref, array=rng.normal(size=(32, 32, 32)))


def register_and_resample(fixed: VolumeHandle, moving: VolumeHandle, *,
                          misaligned: bool = False) -> tuple[Any, Any]:
    """STUB: return (fixed_array, moving_array) resampled to a common grid.

    ``misaligned=True`` returns an independent moving array so the registration
    gate can be exercised end-to-end (it should FAIL). Real implementation runs
    a rigid/affine registration in Slicer and resamples moving onto fixed."""
    if _IN_SLICER:  # pragma: no cover
        raise NotImplementedError(
            "Slicer-backed registration is not implemented yet (week-2 work)")
    _require_numpy()
    f = np.asarray(fixed.array, dtype=float)
    if misaligned:
        rng = np.random.default_rng(999)
        m = rng.normal(size=f.shape)      # independent -> low NMI -> gate FAILS
    else:
        m = f.copy()                       # perfectly aligned -> gate PASSES
    return f, m


@dataclasses.dataclass(frozen=True)
class SegmentationProposal:
    """An AI segmentation PROPOSAL. Never a final result (spec R4).

    Contract fields:
    - ``label_array``      the proposed binary label map.
    - ``scalar_confidence`` model confidence in [0, 1]. Carried as DATA; it is
      NOT shown to a human until calibration is proven — read it only through
      ``segmentation_proposal.displayable_confidence`` (see Phase 2/7).
    - ``per_voxel_uncertainty`` optional per-voxel uncertainty map; honest null
      (``None``) when the model does not provide one — never fabricated.
    - ``is_proposal``      always True; a proposal is never a final result.
    - ``accepted_by_human`` set only by a human acceptance step, never by the model.
    - ``reject`` / ``reject_reason`` the model may self-reject a low-quality output
      with a named reason (fail loud), rather than emit a bad proposal silently.
    """

    label_array: Any
    scalar_confidence: float
    per_voxel_uncertainty: Any = None
    is_proposal: bool = True
    accepted_by_human: bool = False
    reject: bool = False
    reject_reason: str = ""


def propose_segmentation(volume: VolumeHandle) -> SegmentationProposal:
    """STUB: return a synthetic proposal. Real implementation would call MONAI
    Label / TotalSegmentator and load the result into the Segment Editor for the
    surgeon to CORRECT. The proposal is always editable and never authoritative."""
    if _IN_SLICER:  # pragma: no cover
        raise NotImplementedError(
            "Slicer-backed segmentation proposal is not implemented (week-3)")
    _require_numpy()
    arr = np.asarray(volume.array, dtype=float)
    label = (arr > arr.mean()).astype("uint8")   # trivial synthetic mask
    return SegmentationProposal(label_array=label, scalar_confidence=0.42)


def export_model(label_array: Any, out_path: str) -> str:
    """STUB: placeholder for offline, experimental 3D model export (spec R6).

    Explicitly NOT clinical AR and NOT intraoperative. Real implementation would
    generate a surface model in Slicer and save an .obj/.stl for offline viewing
    only. This stub returns the intended path without writing a Slicer scene."""
    if _IN_SLICER:  # pragma: no cover
        raise NotImplementedError(
            "Slicer-backed model export is not implemented yet (week-5 work)")
    return out_path
