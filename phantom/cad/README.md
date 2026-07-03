# Phantom CAD Handoff

CAD files are not yet generated. When they are, record the source of truth here
before using the phantom for validation.

Required handoff fields:

- CAD tool and version:
- Native source file:
- Exported files:
- Units:
- Coordinate datum:
- Coordinate axes:
- Export date:
- Manufacturer / printer:
- Material notes:
- Expected manufacturing tolerance:
- Post-manufacturing metrology method:
- Measured-vs-nominal deviations:

The final CAD export must produce:

- `../ground_truth_targets.csv`
- `../ground_truth_fiducials.csv`

Use `source=cad_nominal` for direct CAD exports and `source=measured` when
metrology supersedes the nominal design.
