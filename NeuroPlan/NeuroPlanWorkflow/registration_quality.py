"""Registration-quality gate.

A bad transform silently poisons every downstream step (segmentation, model,
metrics). This module scores a registration and BLOCKS downstream work when the
score is below threshold — honest nulls, fail loud, no silent "close enough".

Pure NumPy so it is unit-testable without 3D Slicer. The Slicer module feeds it
resampled fixed/moving arrays after registration.
"""
from __future__ import annotations

import dataclasses

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

# Threshold for the normalized-mutual-information proxy below which the gate
# blocks. Calibrate on phantom pairs (see docs/validation-plan.md); this is a
# conservative default, not a validated value.
DEFAULT_NMI_THRESHOLD = 1.05


@dataclasses.dataclass(frozen=True)
class RegistrationQuality:
    nmi: float          # normalized mutual information (>1 means shared info)
    passed: bool
    threshold: float
    reason: str         # named mechanism, always populated


def _entropy(hist: "np.ndarray") -> float:
    p = hist[hist > 0]
    p = p / p.sum()
    return float(-(p * np.log(p)).sum())


def normalized_mutual_information(fixed: "np.ndarray", moving: "np.ndarray",
                                  bins: int = 64) -> float:
    """NMI = (H(fixed) + H(moving)) / H(fixed, moving). 1.0 = independent."""
    if np is None:
        raise RuntimeError("numpy is required for registration quality")
    f = np.asarray(fixed, dtype=float).ravel()
    m = np.asarray(moving, dtype=float).ravel()
    if f.shape != m.shape:
        raise ValueError("fixed and moving must be resampled to the same grid")
    joint, _, _ = np.histogram2d(f, m, bins=bins)
    h_f = _entropy(joint.sum(axis=1))
    h_m = _entropy(joint.sum(axis=0))
    h_fm = _entropy(joint)
    if h_fm == 0:
        return 0.0
    return (h_f + h_m) / h_fm


def score(fixed: "np.ndarray", moving: "np.ndarray",
          threshold: float = DEFAULT_NMI_THRESHOLD) -> RegistrationQuality:
    """Score a registration and decide the gate. Never raises on a bad
    registration — it returns passed=False with a reason so the UI can block
    downstream steps and show the surgeon *why*."""
    try:
        nmi = normalized_mutual_information(fixed, moving)
    except Exception as exc:  # geometry mismatch etc. — fail loud, don't proceed
        return RegistrationQuality(
            nmi=float("nan"), passed=False, threshold=threshold,
            reason=f"could not compute registration quality: {exc}",
        )
    passed = nmi >= threshold
    reason = (
        f"NMI {nmi:.3f} >= threshold {threshold:.3f}: registration accepted"
        if passed else
        f"NMI {nmi:.3f} < threshold {threshold:.3f}: LIKELY MISALIGNED — "
        f"downstream steps blocked; surgeon must confirm or redo"
    )
    return RegistrationQuality(nmi=nmi, passed=passed, threshold=threshold,
                              reason=reason)
