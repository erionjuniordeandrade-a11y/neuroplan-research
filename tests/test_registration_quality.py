"""Unit tests for the registration-quality gate (safety-critical)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))

np = pytest.importorskip("numpy")
import registration_quality as rq  # noqa: E402


def test_aligned_volumes_score_high_and_pass():
    rng = np.random.default_rng(0)
    fixed = rng.normal(size=(32, 32, 32))
    moving = fixed.copy()  # perfectly aligned
    result = rq.score(fixed, moving, threshold=rq.DEFAULT_NMI_THRESHOLD)
    assert result.passed
    assert result.nmi >= result.threshold
    assert "accepted" in result.reason


def test_misaligned_volumes_are_blocked():
    rng = np.random.default_rng(1)
    fixed = rng.normal(size=(32, 32, 32))
    moving = rng.normal(size=(32, 32, 32))  # independent → NMI near 1.0
    result = rq.score(fixed, moving, threshold=rq.DEFAULT_NMI_THRESHOLD)
    assert not result.passed
    assert "blocked" in result.reason.lower()


def test_shape_mismatch_fails_loud_not_crash():
    fixed = np.zeros((16, 16, 16))
    moving = np.zeros((8, 8, 8))
    result = rq.score(fixed, moving)
    assert not result.passed
    assert "could not compute" in result.reason
    assert result.nmi != result.nmi  # NaN


def test_nmi_of_identical_exceeds_independent():
    rng = np.random.default_rng(2)
    a = rng.normal(size=(24, 24, 24))
    b = rng.normal(size=(24, 24, 24))
    assert rq.normalized_mutual_information(a, a) > \
        rq.normalized_mutual_information(a, b)
