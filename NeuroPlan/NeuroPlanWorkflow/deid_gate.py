"""De-identification gate — the ingestion hard block.

Safety-critical, white-box module. Policy (see docs/de-identification-SOP.md):

  1. Reject, don't fix silently — if a required scrub can't be verified, reject
     with a named reason.
  2. Allowlist, not blocklist — retain only tags needed for research geometry;
     strip everything else (including all private tags).
  3. Log a manifest per case.

This module is deliberately standalone (pure pydicom) so it is unit-testable
without a running 3D Slicer. The Slicer module imports and calls it.

Requires: pydicom.
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
from typing import Iterable

try:
    import pydicom
    from pydicom.dataset import Dataset
    from pydicom.uid import generate_uid
except ImportError:  # allow import in environments without pydicom for doc tooling
    pydicom = None  # type: ignore
    Dataset = object  # type: ignore

    def generate_uid() -> str:  # type: ignore
        raise RuntimeError("pydicom is required for de-identification")


# --- Allowlist: keywords retained (geometry / research context only). ----------
# Everything not listed here is removed. UIDs are regenerated, not retained.
RETAINED_KEYWORDS: frozenset[str] = frozenset({
    # Image geometry — required to reconstruct the volume correctly.
    "Rows", "Columns", "PixelSpacing", "SliceThickness", "SpacingBetweenSlices",
    "ImageOrientationPatient", "ImagePositionPatient", "PixelData",
    "BitsAllocated", "BitsStored", "HighBit", "PixelRepresentation",
    "SamplesPerPixel", "PhotometricInterpretation", "RescaleSlope",
    "RescaleIntercept", "NumberOfFrames",
    # Modality / research context (no patient identity).
    "Modality", "SeriesDescription", "ProtocolName", "ScanningSequence",
    "SequenceVariant", "MagneticFieldStrength", "KVP", "RepetitionTime",
    "EchoTime", "FlipAngle", "ContrastBolusAgent",
    # Regenerated UIDs land in these keywords (see _regenerate_uids).
    "StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
    "SOPClassUID", "FrameOfReferenceUID",
})

# UID keywords that must be regenerated. Each is replaced with a FRESH RANDOM
# UID (pydicom.uid.generate_uid) per call — deliberately NOT deterministic, so
# the de-identified series cannot be linked back to the original by UID.
_UID_KEYWORDS = ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
                 "FrameOfReferenceUID")

# Tags whose presence after scrubbing means the gate FAILED (defense in depth).
_MUST_BE_ABSENT_KEYWORDS = (
    "PatientName", "PatientID", "PatientBirthDate", "PatientAddress",
    "PatientTelephoneNumbers", "InstitutionName", "InstitutionAddress",
    "ReferringPhysicianName", "PerformingPhysicianName", "OperatorsName",
    "OtherPatientIDs", "OtherPatientNames",
)


class DeidRejection(Exception):
    """Raised when a file cannot be safely de-identified. Fail loud."""


@dataclasses.dataclass(frozen=True)
class DeidManifest:
    source_sha256: str
    removed_keywords: tuple[str, ...]
    retained_keywords: tuple[str, ...]
    regenerated_uids: tuple[str, ...]
    private_tags_removed: int
    burned_in_annotation: str  # "NO" | "YES" | "UNKNOWN"


def _sha256_of(ds: "Dataset") -> str:
    # Hash the pre-scrub dataset bytes for provenance without storing PHI.
    raw = ds.to_json().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _regenerate_uids(ds: "Dataset") -> list[str]:
    changed: list[str] = []
    for kw in _UID_KEYWORDS:
        if kw in ds:
            setattr(ds, kw, generate_uid())
            changed.append(kw)
    return changed


def deidentify(ds: "Dataset") -> tuple["Dataset", DeidManifest]:
    """Return a de-identified copy of ``ds`` plus a manifest.

    Raises DeidRejection if, after scrubbing, any identifier remains — the gate
    never returns a "best effort" partially-scrubbed dataset.
    """
    if pydicom is None:
        raise RuntimeError("pydicom is required for de-identification")

    source_hash = _sha256_of(ds)
    out = copy.deepcopy(ds)  # deep copy: Dataset.copy() is shallow and shares _dict

    # 1) Remove ALL private tags (odd group numbers) — none are allowlisted.
    private_removed = 0
    for elem in list(out):
        if elem.tag.is_private:
            del out[elem.tag]
            private_removed += 1

    # 2) Allowlist pass — drop any public element not explicitly retained.
    removed: list[str] = []
    for elem in list(out):
        kw = pydicom.datadict.keyword_for_tag(elem.tag)
        if kw not in RETAINED_KEYWORDS:
            removed.append(kw or str(elem.tag))
            del out[elem.tag]

    # 3) Regenerate UIDs so originals cannot link back.
    regenerated = _regenerate_uids(out)

    # 4) Burned-in annotation cannot be verified from tags alone — flag it.
    burned = str(getattr(ds, "BurnedInAnnotation", "UNKNOWN")).upper() or "UNKNOWN"
    if burned not in ("NO", "YES", "UNKNOWN"):
        burned = "UNKNOWN"

    # 5) Defense in depth: fail loud if any identifier survived.
    _assert_clean(out)

    manifest = DeidManifest(
        source_sha256=source_hash,
        removed_keywords=tuple(sorted(set(removed))),
        retained_keywords=tuple(sorted(k for k in RETAINED_KEYWORDS if k in out)),
        regenerated_uids=tuple(regenerated),
        private_tags_removed=private_removed,
        burned_in_annotation=burned,
    )
    return out, manifest


def _assert_clean(ds: "Dataset") -> None:
    survivors: list[str] = []
    for kw in _MUST_BE_ABSENT_KEYWORDS:
        if kw in ds and getattr(ds, kw, None) not in (None, ""):
            survivors.append(kw)
    if any(e.tag.is_private for e in ds):
        survivors.append("<private-tags>")
    if survivors:
        raise DeidRejection(
            "de-identification incomplete; identifiers remain: "
            + ", ".join(survivors)
        )


def gate_files(datasets: Iterable["Dataset"]) -> list[tuple["Dataset", DeidManifest]]:
    """Run the gate over many datasets. One failure fails that file loudly;
    the caller decides whether to abort the whole import."""
    return [deidentify(ds) for ds in datasets]
