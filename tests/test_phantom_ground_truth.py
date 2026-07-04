"""Phantom ground-truth DESIGN-consistency tests.

Asserts that every volume and max-diameter cell in the candidate ground-truth CSV
matches the geometric formula documented in phantom/README.md. This catches CSV
drift (a hand-edited cell going off-formula) and proves the *design* is internally
consistent.

IMPORTANT: this proves the numbers are self-consistent by DESIGN — NOT that they
are measured from a fabricated phantom. Those CSVs are `source=design_candidate`.
Do not read a pass here as physical validation (see DEVELOPMENT-PLAN.md Phase 6).
"""
import csv
import math
import os

import pytest

_TARGETS_CSV = os.path.join(
    os.path.dirname(__file__), "..", "phantom",
    "ground_truth_targets.candidate.csv")


def _rows():
    with open(_TARGETS_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _expected_volume_ml(dx: float, dy: float, dz: float) -> float:
    # phantom/README.md: (4/3)·pi·rx·ry·rz / 1000, radii = dimension / 2.
    # A sphere is the special case of equal axes, so one formula covers both.
    rx, ry, rz = dx / 2.0, dy / 2.0, dz / 2.0
    return (4.0 / 3.0) * math.pi * rx * ry * rz / 1000.0


def _ids():
    return [r["object"] for r in _rows()]


@pytest.fixture(params=_rows(), ids=_ids())
def row(request):
    return request.param


@pytest.mark.unit
def test_designed_volume_matches_formula(row):
    dims = (float(row["dimension_x_mm"]), float(row["dimension_y_mm"]),
            float(row["dimension_z_mm"]))
    expected = _expected_volume_ml(*dims)
    got = float(row["volume_ml"])
    assert got == pytest.approx(expected, abs=1e-3), (
        f"{row['object']}: CSV volume {got} vs formula {expected:.6f} — "
        f"CSV drifted off the documented geometry")


@pytest.mark.unit
def test_designed_max_diameter_is_largest_axis(row):
    dims = [float(row["dimension_x_mm"]), float(row["dimension_y_mm"]),
            float(row["dimension_z_mm"])]
    got = float(row["max_diameter_mm"])
    assert got == pytest.approx(max(dims), abs=1e-9), (
        f"{row['object']}: CSV max diameter {got} != largest axis {max(dims)}")


@pytest.mark.unit
def test_every_target_is_a_design_candidate():
    # Guardrail: if any row flips to source=measured, this test must be revisited
    # (measured data is validated differently — see DEVELOPMENT-PLAN.md Phase 6).
    for r in _rows():
        assert r["source"] == "design_candidate", (
            f"{r['object']}: source is '{r['source']}', not design_candidate — "
            f"promote the measured-validation path before trusting this as truth")
