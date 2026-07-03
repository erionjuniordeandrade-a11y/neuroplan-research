# Phantom Design Spec — Ground-Truth Geometry

The phantom is the **only** source of true error in mm/mL. Design and document it
so every metric NeuroPlan computes has a known reference before public datasets
are used for realism testing.

This spec is the ground-truth contract for:

- Week 2 registration/fusion validation.
- Week 4 deterministic metric validation.
- Regression tests for "fail loud" behavior when a known-bad transform is used.

Do **not** commit phantom scans. `.gitignore` excludes imaging files. Commit only
the design spec, small CAD/print files, and derived ground-truth metadata.

## Required design properties

- Embedded targets with known volume, max diameter, centroid, and
  depth-from-surface, approximating superficial supratentorial lesions.
- At least 8 non-coplanar fiducial markers with known coordinates for target
  registration error (TRE).
- Targets and fiducials visible on both MRI (T1-post equivalent contrast) and CT.
- Single rigid body with no moving internal parts between MRI and CT scans.
- Printed/manufactured with recorded tolerances; measured values replace nominal
  CAD values when they differ.

## Coordinate system

Use one phantom reference frame for CAD, MRI, CT, and all ground-truth tables.

- Units: millimeters.
- Origin: center of the phantom base plate unless the CAD defines a better fixed
  datum. Record the final datum here.
- Axes: RAS-style convention for compatibility with Slicer exports:
  - X = right.
  - Y = anterior.
  - Z = superior.
- All lesion centroid and fiducial coordinates must be exported from CAD in this
  frame.
- Depth-from-surface means the shortest distance from the outer cortical/surface
  shell to the nearest point of the target along the local surface normal.

## Phantom body

Minimum viable build:

- A head-like supratentorial shell or cap with a stable flat base.
- A CT-visible skull/surface shell and MRI-visible interior medium.
- Removable or permanently embedded lesion inserts that do not shift between
  scans.
- Fiducials distributed across the full volume, not only around the targets.

Recommended material requirements:

- MRI-safe and CT-compatible.
- No ferromagnetic components.
- Low shrinkage or post-print metrology to quantify shrinkage.
- Lesion inserts and fiducials must have contrast separable from the background
  on both modalities.

## Candidate target layout

The table below is a starter design for CAD. Replace nominal values with the
final CAD export and measured metrology before using the phantom as ground truth.
The same candidate values are mirrored in
`ground_truth_targets.candidate.csv`.

| Object | Shape | Dimensions (mm) | Centroid X/Y/Z (mm) | Designed volume (mL) | Max diameter (mm) | Depth from surface (mm) | Purpose |
|---|---:|---:|---:|---:|---:|---:|---|
| L1 | sphere | diameter 12 | -35 / -25 / 45 | 0.905 | 12 | 5 | small superficial target |
| L2 | sphere | diameter 20 | 35 / -20 / 50 | 4.189 | 20 | 10 | mid-size spherical target |
| L3 | ellipsoid | 28 x 18 x 14 | -25 / 30 / 55 | 3.695 | 28 | 18 | anisotropic target |
| L4 | ellipsoid | 36 x 24 x 18 | 30 / 28 / 48 | 8.143 | 36 | 25 | larger superficial target |
| L5 | ellipsoid | 24 x 24 x 8 | 0 / 5 / 72 | 2.413 | 24 | 4 | shallow plaque-like target |

Volume formulae:

- Sphere: `(4 / 3) * pi * radius^3 / 1000`.
- Ellipsoid: `(4 / 3) * pi * radius_x * radius_y * radius_z / 1000`.

If an irregular/lobulated target is added later, its ground truth must come from
the CAD mesh volume and an exported max-diameter calculation, not from manual
measurement in Slicer.

## Fiducial layout

Use at least 8 markers; 10 are recommended so one poor marker does not collapse
the TRE estimate. Marker centers must be exported from CAD and copied here.
The same candidate values are mirrored in
`ground_truth_fiducials.candidate.csv`.

| Marker | X (mm) | Y (mm) | Z (mm) | Notes |
|---|---:|---:|---:|---|
| F1 | -70 | -45 | 15 | inferior posterior-left field anchor |
| F2 | 70 | -45 | 15 | inferior posterior-right field anchor |
| F3 | -70 | 45 | 15 | inferior anterior-left field anchor |
| F4 | 70 | 45 | 15 | inferior anterior-right field anchor |
| F5 | -55 | -20 | 70 | superior posterior-left anchor |
| F6 | 55 | -20 | 70 | superior posterior-right anchor |
| F7 | -35 | 35 | 80 | superior anterior-left anchor |
| F8 | 35 | 35 | 80 | superior anterior-right anchor |
| F9 | 0 | -55 | 50 | midline posterior anchor |
| F10 | 0 | 55 | 50 | midline anterior anchor |

Fiducial acceptance requirements:

- Minimum center-to-center spacing: 20 mm.
- Not all markers may lie on the same plane.
- Each marker must be individually identifiable in both MRI and CT.
- Marker center localization uncertainty must be recorded after the first scan.

## Ground-truth files to produce

Before Week 2 validation, produce these files from the finalized CAD/metrology
record:

- `phantom/ground_truth_targets.csv`
- `phantom/ground_truth_fiducials.csv`
- `phantom/cad/README.md` describing CAD source, units, coordinate datum, export
  date, and manufacturing tolerance.

The checked-in `*.candidate.csv` files are design inputs only. Do not treat them
as ground truth until CAD export and manufacturing/metrology records replace
`source=design_candidate`.

Suggested `ground_truth_targets.csv` columns:

```csv
object,shape,dimension_x_mm,dimension_y_mm,dimension_z_mm,centroid_x_mm,centroid_y_mm,centroid_z_mm,volume_ml,max_diameter_mm,depth_from_surface_mm,source
L1,sphere,12,12,12,-35,-25,45,0.905,12,5,cad_nominal
```

Suggested `ground_truth_fiducials.csv` columns:

```csv
marker,x_mm,y_mm,z_mm,diameter_mm,source
F1,-70,-45,15,4,cad_nominal
```

Use `source=measured` once post-manufacturing metrology supersedes nominal CAD.

## Scan protocol

Use the same physical phantom position for MRI and CT when feasible. If the
phantom must be moved, do not adjust internal components between scans.

Minimum acquisition records:

- Modality, scanner/model, sequence/protocol name.
- Voxel spacing and slice thickness.
- Reconstruction kernel for CT.
- Date of scan may be stored in the local lab record but should not be copied
  into committed DICOM/NIfTI metadata.
- Operator and scan notes in a local lab notebook, not in committed imaging.

Recommended imaging targets:

- CT: isotropic or near-isotropic reconstruction when available.
- MRI: T1-post-equivalent contrast with target and fiducial visibility sufficient
  for manual center localization.
- Both modalities: field of view includes every target and fiducial.

## Validation uses

### Week 2 — registration/fusion

1. Scan the finalized phantom on MRI and CT.
2. Run de-identification/import.
3. Run rigid registration.
4. Resample the moving volume into the fixed grid.
5. Run the NMI registration-quality gate.
6. Localize fiducials in both volumes and compute TRE against the known
   ground-truth coordinates.
7. Apply at least two deliberately bad transforms, such as translation-only and
   rotation-only perturbations, and confirm the registration gate blocks them
   with a named reason.

Record both:

- The continuous NMI score used by `registration_quality.py`.
- The geometric TRE in millimeters.

The NMI threshold is an engineering gate and must be calibrated on this phantom;
it is not a clinical threshold.

### Week 4 — metrics

For each target, compare NeuroPlan output against this spec:

- Volume error in mL and percent.
- Max-diameter error in mm.
- Depth-from-surface error in mm.
- Distance-to-fiducial error in mm when that metric is enabled.

Do not tune metric code on public datasets before it passes this phantom check.

## Acceptance checklist

The phantom is ready to anchor validation only when all items are complete:

- [ ] CAD source and coordinate datum are documented.
- [ ] Target table exported from CAD.
- [ ] Fiducial table exported from CAD.
- [ ] Manufacturing tolerance or post-print metrology is recorded.
- [ ] Every target is visible on MRI and CT.
- [ ] Every fiducial is visible and individually identifiable on MRI and CT.
- [ ] De-ID gate accepts the exported phantom scans.
- [ ] Registration gate accepts the aligned pair.
- [ ] Registration gate blocks deliberately misaligned pairs.
- [ ] TRE and metric-error calculations are reproducible by a second operator.
