"""Tests for banner enforcement and clinical-field rejection in exports."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neuroplan_ui import banner, export  # noqa: E402


def test_stamp_adds_exact_banner():
    out = banner.stamp({"a": 1})
    assert out[banner.BANNER_KEY] == banner.RESEARCH_BANNER
    assert out["a"] == 1


def test_stamp_does_not_mutate_input():
    src = {"a": 1}
    banner.stamp(src)
    assert banner.BANNER_KEY not in src


def test_stamp_overwrites_a_softened_notice():
    out = banner.stamp({banner.BANNER_KEY: "totally fine for surgery"})
    assert out[banner.BANNER_KEY] == banner.RESEARCH_BANNER


def test_assert_present_raises_when_missing():
    with pytest.raises(banner.BannerMissing):
        banner.assert_present({"metrics": {}})


def test_build_artifact_is_banner_stamped():
    artifact = export.build_artifact(
        case_label="phantom_01",
        metrics={"volume_ml": 4.19, "max_diameter_mm": 20.0},
        registration_reason="NMI 2.0 >= 1.05: accepted",
        audit=[],
    )
    banner.assert_present(artifact)  # does not raise
    assert artifact[banner.BANNER_KEY] == banner.RESEARCH_BANNER
    assert "diagnosis" not in artifact


def test_build_artifact_rejects_clinical_fields():
    with pytest.raises(export.ForbiddenField, match="diagnosis"):
        export.build_artifact(
            case_label="phantom_01",
            metrics={"volume_ml": 4.19, "diagnosis": "meningioma"},
            registration_reason="ok",
            audit=[])


def test_model_export_is_flagged_non_clinical():
    artifact = export.build_artifact(
        case_label="phantom_01",
        metrics={"volume_ml": 4.19},
        registration_reason="ok",
        audit=[],
        model_path="out/model.obj")
    assert artifact["model_export"]["not_for"] == \
        "clinical AR or intraoperative navigation"


def test_to_json_roundtrips_with_banner():
    artifact = export.build_artifact(
        case_label="phantom_01", metrics={"volume_ml": 1.0},
        registration_reason="ok", audit=[])
    text = export.to_json(artifact)
    assert banner.RESEARCH_BANNER in text
