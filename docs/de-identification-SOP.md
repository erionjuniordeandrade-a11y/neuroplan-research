# De-identification Gate — SOP

The de-ID gate is a **hard block**: no volume enters the working project until it
passes. This is a white-box, safety-critical module — read every line, test every path.

## Policy
1. **Reject, don't fix silently.** If a required scrub cannot be verified, the file
   is rejected with a named reason — never imported "best effort."
2. **Allowlist, not blocklist.** Keep only the DICOM tags needed for research
   geometry/context; strip everything else. A blocklist misses the tag you forgot.
3. **Log a manifest per case** — source hash, tags removed/retained, defacing
   applied (y/n), operator, timestamp. Reproducibility + audit.
4. **Public data assumed already de-identified** — still runs the gate as a
   conformance check; the gate is the single source of truth, not the dataset's label.

## Retained (allowlist — geometry/context only)
- Pixel data and image geometry: rows/cols, pixel spacing, slice thickness,
  image orientation/position, modality, frame of reference.
- De-identified study/series UIDs (regenerated, not original).
- Acquisition params needed for research (e.g. sequence type, KVP) — **no** dates
  tied to the patient, **no** operator/institution identifiers unless required and
  approved.

## Removed / regenerated (examples — see `NeuroPlan/.../deid_gate.py` for the enforced list)
- PatientName, PatientID, PatientBirthDate, PatientAddress, PatientTelephone.
- Institution name/address, referring/performing physician, operator name.
- All private tags (odd group numbers) unless explicitly allowlisted.
- Original SOP/Study/Series Instance UIDs → regenerated.
- Burned-in annotations → flag for review; do not assume clean.

## Optional
- **Defacing** for surface-rendered MRI (face/ear removal) when the render could
  re-identify. Off by default; enable per protocol.

## Enforcement
The canonical, enforced tag list lives in code (`deid_gate.py`) with a unit test
(`tests/test_deid_gate.py`) so the SOP and the implementation cannot silently drift
("make the wrong thing structurally impossible").
