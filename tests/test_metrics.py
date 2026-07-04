"""Deterministic metric tests, validated against the phantom ground truth.

For each designed target in phantom/ground_truth_targets.candidate.csv we
synthesize a voxel mask of the designed shape/size and assert the computed
volume and max-diameter match the DESIGNED values within a discretization
tolerance. This is the phantom-anchored contract for the metric layer.
"""
import csv
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))

np = pytest.importorskip("numpy")
import metrics  # noqa: E402

_TARGETS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "phantom",
    "ground_truth_targets.candidate.csv")


def _load_targets() -> list[dict]:
    with open(_TARGETS_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ellipsoid_mask(dims_mm, spacing=1.0) -> "np.ndarray":
    """Voxelize a centered ellipsoid of full dimensions ``dims_mm`` (x, y, z)."""
    semi = np.asarray(dims_mm, dtype=float) / 2.0
    half = (np.ceil(semi / spacing) + 1).astype(int)
    axes = [np.arange(-h, h + 1) * spacing for h in half]
    grid = np.meshgrid(*axes, indexing="ij")
    norm = sum((g / s) ** 2 for g, s in zip(grid, semi))
    return norm <= 1.0


def _target_ids():
    return [t["object"] for t in _load_targets()]


@pytest.fixture(params=_load_targets(), ids=_target_ids())
def target(request):
    return request.param


# --- phantom-anchored validation ------------------------------------------

def test_volume_matches_designed(target):
    dims = (float(target["dimension_x_mm"]), float(target["dimension_y_mm"]),
            float(target["dimension_z_mm"]))
    designed_ml = float(target["volume_ml"])
    # Voxelize at 0.5 mm: finer sampling converges to the analytic volume within
    # a few percent, so we can hold a tight 5% tolerance (was 10% at 1 mm).
    mask = _ellipsoid_mask(dims, spacing=0.5)
    got = metrics.voxel_volume_ml(mask, (0.5, 0.5, 0.5))
    assert got == pytest.approx(designed_ml, rel=0.05), \
        f"{target['object']}: volume {got:.3f} vs designed {designed_ml:.3f}"


def test_max_diameter_matches_designed(target):
    dims = (float(target["dimension_x_mm"]), float(target["dimension_y_mm"]),
            float(target["dimension_z_mm"]))
    designed_mm = float(target["max_diameter_mm"])
    mask = _ellipsoid_mask(dims, spacing=1.0)
    got = metrics.max_diameter_mm(mask, (1.0, 1.0, 1.0))
    # Measured between voxel centers → under-reports true extent by ≤ ~1 voxel.
    assert abs(got - designed_mm) <= 2.0, \
        f"{target['object']}: diameter {got:.1f} vs designed {designed_mm:.1f}"


# --- deterministic + geometric properties ---------------------------------

def test_metrics_are_deterministic():
    mask = _ellipsoid_mask((20, 20, 20))
    a = metrics.compute_metrics(mask, (1.0, 1.0, 1.0))
    b = metrics.compute_metrics(mask, (1.0, 1.0, 1.0))
    assert a == b


def test_anisotropic_spacing_scales_volume():
    mask = _ellipsoid_mask((20, 20, 20))
    iso = metrics.voxel_volume_ml(mask, (1.0, 1.0, 1.0))
    # Doubling one axis's spacing doubles the physical volume of each voxel.
    aniso = metrics.voxel_volume_ml(mask, (2.0, 1.0, 1.0))
    assert aniso == pytest.approx(2.0 * iso, rel=1e-9)


def test_centroid_recovers_known_center():
    mask = _ellipsoid_mask((16, 16, 16))
    # Mask is symmetric about its array center; centroid ≈ geometric center.
    c = metrics.centroid_mm(mask, (1.0, 1.0, 1.0))
    center = [(s - 1) / 2.0 for s in mask.shape]
    for got, exp in zip(c, center):
        assert got == pytest.approx(exp, abs=0.5)


# --- honest nulls ----------------------------------------------------------

def test_depth_is_honest_null_without_surface():
    mask = _ellipsoid_mask((16, 16, 16))
    result = metrics.compute_metrics(mask, (1.0, 1.0, 1.0))
    assert result.depth_from_surface_mm is None  # not a fabricated 0.0


def test_distance_to_fiducial_is_null_without_fiducial():
    mask = _ellipsoid_mask((16, 16, 16))
    result = metrics.compute_metrics(mask, (1.0, 1.0, 1.0))
    assert result.distance_to_fiducial_mm is None


def test_distance_to_fiducial_is_computed_when_given():
    mask = _ellipsoid_mask((16, 16, 16))
    c = metrics.centroid_mm(mask, (1.0, 1.0, 1.0))
    fiducial = (c[0] + 3.0, c[1] + 4.0, c[2])  # 3-4-5 triangle → distance 5
    result = metrics.compute_metrics(mask, (1.0, 1.0, 1.0), fiducial_mm=fiducial)
    assert result.distance_to_fiducial_mm == pytest.approx(5.0, abs=1e-6)


def test_depth_from_surface_centered_target():
    # A single central voxel inside a 60 mm ball; depth = the ball radius.
    shell = _ellipsoid_mask((60, 60, 60))
    target = np.zeros_like(shell)
    cx, cy, cz = (s // 2 for s in shell.shape)
    target[cx, cy, cz] = True
    depth = metrics.depth_from_surface_mm(target, shell, (1.0, 1.0, 1.0))
    assert depth is not None
    assert depth == pytest.approx(30.0, abs=1.5)  # radius of the 60 mm ball


@pytest.mark.parametrize("offset_mm, expected_depth", [(0, 30.0), (10, 20.0),
                                                       (20, 10.0)])
def test_depth_from_surface_is_geometrically_exact(offset_mm, expected_depth):
    # Solid ball radius 30 mm; a target voxel offset along +x by `offset_mm`.
    # Its shortest distance to the outer surface is exactly radius - offset.
    # This rigorously validates the depth ALGORITHM (the phantom shell geometry
    # for CSV-anchored depth is deferred — see the note below).
    shell = _ellipsoid_mask((60, 60, 60))
    target = np.zeros_like(shell)
    cx, cy, cz = (s // 2 for s in shell.shape)
    target[cx + offset_mm, cy, cz] = True
    depth = metrics.depth_from_surface_mm(target, shell, (1.0, 1.0, 1.0))
    assert depth is not None
    assert depth == pytest.approx(expected_depth, abs=1.5)


# NOTE: Anchoring depth_from_surface against the depth_from_surface_mm column of
# phantom/ground_truth_targets.candidate.csv is DEFERRED until the phantom OUTER
# SHELL geometry is committed as data (an analytic datum or a shell mask). Those
# designed depths are measured from a surface not yet defined in the repo, so a
# CSV-anchored depth test cannot be written honestly today. The algorithm itself
# is validated exactly by test_depth_from_surface_is_geometrically_exact above.


def test_empty_segmentation_flags_and_nulls():
    mask = np.zeros((10, 10, 10), dtype=bool)
    result = metrics.compute_metrics(mask, (1.0, 1.0, 1.0))
    assert result.voxel_count == 0
    assert result.volume_ml == 0.0
    assert result.depth_from_surface_mm is None
    assert any("empty segmentation" in w for w in result.warnings)


def test_implausible_volume_is_flagged_not_clamped():
    # A 20 cm cube → ~8000 mL, well over the plausibility ceiling.
    mask = np.ones((40, 40, 40), dtype=bool)
    result = metrics.compute_metrics(mask, (5.0, 5.0, 5.0))
    assert result.volume_ml > metrics._MAX_PLAUSIBLE_VOLUME_ML  # returned as-is
    assert any("plausible range" in w for w in result.warnings)


# --- input validation ------------------------------------------------------

def test_rejects_non_3d_mask():
    with pytest.raises(ValueError, match="3D array"):
        metrics.voxel_volume_ml(np.ones((4, 4)), (1.0, 1.0, 1.0))


def test_rejects_nonpositive_spacing():
    mask = _ellipsoid_mask((10, 10, 10))
    with pytest.raises(ValueError, match="positive"):
        metrics.voxel_volume_ml(mask, (1.0, 0.0, 1.0))
