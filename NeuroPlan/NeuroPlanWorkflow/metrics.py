"""Deterministic, phantom-anchored planning metrics.

Pure NumPy so it is unit-testable without 3D Slicer, and checked against the
phantom DESIGN geometry (see ``phantom/ground_truth_targets.candidate.csv`` and
``docs/validation-plan.md``). NOTE: those CSVs are ``source=design_candidate`` —
i.e. *designed* values, not yet *measured* from a fabricated phantom. So the
metric layer is currently validated against design intent, NOT physical reality;
do not describe it as "validated against the phantom" in any publication until
the candidate ground truth is promoted from a scanned, measured phantom. The
Slicer module feeds it a binary label array plus voxel spacing from a node.

Design posture (matches the rest of NeuroPlan):
- **Deterministic.** Same mask + spacing -> same numbers, always. No randomness,
  no fitting.
- **Honest nulls, never clamp.** A metric that cannot be computed from the given
  inputs (e.g. depth-from-surface with no surface mask) returns ``None`` with a
  named reason — it is never faked as 0. Implausible values are *flagged*
  (``warnings``) and still returned, never silently corrected.
- **Geometry only.** Volume, size, position, distances. No diagnosis, grade, or
  clinical interpretation — those are structurally absent by design.

Coordinates are in millimeters throughout. ``spacing`` is ``(sx, sy, sz)`` mm
per voxel along array axes 0, 1, 2. ``origin`` shifts the array's (0,0,0) voxel
into the phantom/world frame; default origin is the array corner.
"""
from __future__ import annotations

import dataclasses

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy absent only in doc tooling
    np = None  # type: ignore

# Sanity bounds for the honest-null plausibility flags. These do NOT clamp; a
# value outside them is still returned, with a warning attached, so a human sees
# the anomaly instead of a quietly-corrected number.
_MAX_PLAUSIBLE_VOLUME_ML = 2000.0     # larger than an intracranial volume
_MAX_PLAUSIBLE_DIAMETER_MM = 300.0    # larger than a human head


@dataclasses.dataclass(frozen=True)
class MetricSet:
    """The deterministic geometry of one segmented target.

    ``None`` on an optional metric means "could not be computed from the inputs
    given" (honest null), not "zero". ``warnings`` lists implausible-value flags;
    an empty tuple means every computed value passed its sanity check.
    """

    voxel_count: int
    volume_ml: float
    max_diameter_mm: float
    centroid_mm: tuple[float, float, float]
    depth_from_surface_mm: float | None
    distance_to_fiducial_mm: float | None
    warnings: tuple[str, ...]


def _require_numpy() -> None:
    if np is None:
        raise RuntimeError("numpy is required for metric computation")


def _as_bool_mask(mask: "np.ndarray") -> "np.ndarray":
    m = np.asarray(mask)
    if m.ndim != 3:
        raise ValueError("segmentation mask must be a 3D array")
    return m.astype(bool)


def _spacing_array(spacing: tuple[float, float, float]) -> "np.ndarray":
    sp = np.asarray(spacing, dtype=float)
    if sp.shape != (3,):
        raise ValueError("spacing must be (sx, sy, sz) in mm")
    if np.any(sp <= 0):
        raise ValueError("voxel spacing must be positive in every axis")
    return sp


def voxel_volume_ml(mask: "np.ndarray",
                    spacing: tuple[float, float, float]) -> float:
    """Volume of the foreground, in milliliters (1 mL = 1000 mm³)."""
    _require_numpy()
    m = _as_bool_mask(mask)
    sp = _spacing_array(spacing)
    voxel_mm3 = float(sp.prod())
    return float(m.sum()) * voxel_mm3 / 1000.0


def _surface_coords(mask: "np.ndarray",
                    spacing: "np.ndarray") -> "np.ndarray":
    """Return the (N, 3) mm coordinates of foreground voxels on the surface.

    A voxel is on the surface if it is foreground and at least one of its six
    face-neighbors is background (the array is padded so border voxels count as
    surface). Pure NumPy — no scipy dependency.
    """
    m = _as_bool_mask(mask)
    p = np.pad(m, 1, mode="constant", constant_values=False)
    interior = (
        p[2:, 1:-1, 1:-1] & p[:-2, 1:-1, 1:-1] &
        p[1:-1, 2:, 1:-1] & p[1:-1, :-2, 1:-1] &
        p[1:-1, 1:-1, 2:] & p[1:-1, 1:-1, :-2]
    )
    surface = m & ~interior
    coords = np.argwhere(surface).astype(float)
    return coords * spacing


def _max_pairwise_distance(coords: "np.ndarray") -> float:
    """Exact maximum Euclidean distance between any two rows of ``coords``.

    O(n²) time, O(n) memory — fine at phantom scale (a few thousand surface
    voxels). Measured between voxel centers, so it slightly under-reports the
    true tip-to-tip extent by up to about one voxel.
    """
    n = len(coords)
    if n < 2:
        return 0.0
    best = 0.0
    for i in range(n):
        d = np.sqrt(((coords[i] - coords) ** 2).sum(axis=1)).max()
        if d > best:
            best = float(d)
    return best


def max_diameter_mm(mask: "np.ndarray",
                    spacing: tuple[float, float, float]) -> float:
    """Maximum caliper (Feret) diameter of the foreground, in mm."""
    _require_numpy()
    sp = _spacing_array(spacing)
    return _max_pairwise_distance(_surface_coords(mask, sp))


def centroid_mm(mask: "np.ndarray", spacing: tuple[float, float, float],
                origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
                ) -> tuple[float, float, float]:
    """Center of mass of the foreground, in mm in the (origin-shifted) frame."""
    _require_numpy()
    m = _as_bool_mask(mask)
    sp = _spacing_array(spacing)
    coords = np.argwhere(m).astype(float)
    if len(coords) == 0:
        raise ValueError("cannot take centroid of an empty segmentation")
    c = coords.mean(axis=0) * sp + np.asarray(origin, dtype=float)
    return (float(c[0]), float(c[1]), float(c[2]))


def depth_from_surface_mm(target_mask: "np.ndarray",
                          surface_mask: "np.ndarray | None",
                          spacing: tuple[float, float, float]) -> float | None:
    """Shortest distance from the phantom's outer surface to the target.

    Honest null: returns ``None`` if no surface mask is supplied or it is empty —
    depth is undefined without the surface, and a fabricated 0 would read as
    "on the surface". O(n·m) over the two surface point sets.
    """
    _require_numpy()
    if surface_mask is None:
        return None
    sp = _spacing_array(spacing)
    shell = _surface_coords(surface_mask, sp)
    target = _surface_coords(target_mask, sp)
    if len(shell) == 0 or len(target) == 0:
        return None
    best = float("inf")
    for pt in target:
        d = np.sqrt(((shell - pt) ** 2).sum(axis=1)).min()
        if d < best:
            best = float(d)
    return best


def distance_to_fiducial_mm(mask: "np.ndarray",
                            spacing: tuple[float, float, float],
                            fiducial_mm: tuple[float, float, float] | None,
                            origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
                            ) -> float | None:
    """Distance from the target centroid to a fiducial point (mm).

    Honest null: returns ``None`` when no fiducial is supplied.
    """
    _require_numpy()
    if fiducial_mm is None:
        return None
    c = np.asarray(centroid_mm(mask, spacing, origin), dtype=float)
    f = np.asarray(fiducial_mm, dtype=float)
    return float(np.sqrt(((c - f) ** 2).sum()))


def compute_metrics(mask: "np.ndarray", spacing: tuple[float, float, float], *,
                    surface_mask: "np.ndarray | None" = None,
                    fiducial_mm: tuple[float, float, float] | None = None,
                    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
                    ) -> MetricSet:
    """Compute the full deterministic metric set for one segmented target.

    Optional inputs (``surface_mask``, ``fiducial_mm``) yield honest nulls when
    absent rather than fabricated values. Implausible results are flagged in
    ``warnings`` (never clamped)."""
    _require_numpy()
    m = _as_bool_mask(mask)
    count = int(m.sum())
    warnings: list[str] = []

    if count == 0:
        # Empty segmentation: report zeros but flag loudly; no target to measure.
        return MetricSet(
            voxel_count=0, volume_ml=0.0, max_diameter_mm=0.0,
            centroid_mm=(float("nan"),) * 3,
            depth_from_surface_mm=None, distance_to_fiducial_mm=None,
            warnings=("empty segmentation — no target voxels to measure",),
        )

    volume = voxel_volume_ml(m, spacing)
    diameter = max_diameter_mm(m, spacing)
    centroid = centroid_mm(m, spacing, origin)
    depth = depth_from_surface_mm(m, surface_mask, spacing)
    fid = distance_to_fiducial_mm(m, spacing, fiducial_mm, origin)

    if not (0.0 < volume <= _MAX_PLAUSIBLE_VOLUME_ML):
        warnings.append(
            f"volume {volume:.3f} mL is outside the plausible range "
            f"(0, {_MAX_PLAUSIBLE_VOLUME_ML}] — review the segmentation")
    if not (0.0 < diameter <= _MAX_PLAUSIBLE_DIAMETER_MM):
        warnings.append(
            f"max diameter {diameter:.1f} mm is outside the plausible range "
            f"(0, {_MAX_PLAUSIBLE_DIAMETER_MM}] — review the segmentation")

    return MetricSet(
        voxel_count=count, volume_ml=volume, max_diameter_mm=diameter,
        centroid_mm=centroid, depth_from_surface_mm=depth,
        distance_to_fiducial_mm=fid, warnings=tuple(warnings),
    )
