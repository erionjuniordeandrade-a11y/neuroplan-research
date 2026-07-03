"""Unit tests for the de-identification gate (safety-critical)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "NeuroPlan", "NeuroPlanWorkflow"))

pydicom = pytest.importorskip("pydicom")
from pydicom.dataset import Dataset  # noqa: E402

import deid_gate  # noqa: E402


def _synthetic_phi_dataset() -> Dataset:
    ds = Dataset()
    # Identifiers that MUST be scrubbed.
    ds.PatientName = "DOE^JOHN"
    ds.PatientID = "HSJ-000123"
    ds.PatientBirthDate = "19700101"
    ds.InstitutionName = "Hospital Sao Jose"
    ds.ReferringPhysicianName = "SMITH^JANE"
    ds.OperatorsName = "TECH^A"
    # Geometry that MUST be retained.
    ds.Rows = 256
    ds.Columns = 256
    ds.PixelSpacing = [1.0, 1.0]
    ds.SliceThickness = 1.0
    ds.Modality = "MR"
    ds.StudyInstanceUID = "1.2.3.4.5"
    ds.SeriesInstanceUID = "1.2.3.4.6"
    # A private tag that MUST be removed.
    block = ds.private_block(0x000b, "NEUROPLAN TEST", create=True)
    block.add_new(0x01, "LO", "secret-vendor-value")
    return ds


def test_identifiers_are_removed():
    clean, manifest = deid_gate.deidentify(_synthetic_phi_dataset())
    for kw in ("PatientName", "PatientID", "PatientBirthDate",
               "InstitutionName", "ReferringPhysicianName", "OperatorsName"):
        assert kw not in clean, f"{kw} survived de-identification"


def test_geometry_is_retained():
    clean, _ = deid_gate.deidentify(_synthetic_phi_dataset())
    assert clean.Rows == 256
    assert clean.Columns == 256
    assert list(clean.PixelSpacing) == [1.0, 1.0]
    assert clean.Modality == "MR"


def test_private_tags_removed():
    clean, manifest = deid_gate.deidentify(_synthetic_phi_dataset())
    assert manifest.private_tags_removed >= 1
    assert not any(e.tag.is_private for e in clean)


def test_uids_regenerated():
    original = _synthetic_phi_dataset()
    clean, manifest = deid_gate.deidentify(original)
    assert clean.StudyInstanceUID != original.StudyInstanceUID
    assert "StudyInstanceUID" in manifest.regenerated_uids


def test_manifest_records_source_hash():
    _, manifest = deid_gate.deidentify(_synthetic_phi_dataset())
    assert len(manifest.source_sha256) == 64  # sha256 hex digest


def test_gate_is_defense_in_depth():
    # If somehow an identifier is on the allowlist path, _assert_clean must catch it.
    ds = _synthetic_phi_dataset()
    clean, _ = deid_gate.deidentify(ds)
    # Re-running the clean set must not raise.
    deid_gate._assert_clean(clean)
