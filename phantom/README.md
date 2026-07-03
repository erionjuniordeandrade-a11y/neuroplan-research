# Phantom — Ground-Truth Geometry

The phantom is the **only** source of true error in mm/mL. Design it so every
metric the tool computes has a known reference.

## Design goals
- Embedded objects of **known** volume, max diameter, and depth-from-surface,
  approximating superficial supratentorial lesions.
- Fiducial markers at known coordinates for target registration error (TRE).
- Visible on **both** MRI (T1-post equivalent contrast) and CT for fusion testing.

## Ground-truth table (fill from CAD / print spec)
| Object | Shape | Designed volume (mL) | Max diameter (mm) | Depth from surface (mm) |
|---|---|---|---|---|
| L1 | sphere | [ ] | [ ] | [ ] |
| L2 | ellipsoid | [ ] | [ ] | [ ] |
| … | | | | |

## Fiducials
| Marker | X (mm) | Y (mm) | Z (mm) |
|---|---|---|---|
| F1 | [ ] | [ ] | [ ] |
| … | | | |

## Usage
1. Scan phantom on MRI + CT.
2. Run the full NeuroPlan workflow.
3. Compare computed volume/diameter/depth against the designed values above.
4. Compare fiducial localization against designed coordinates (TRE).

> Do **not** commit the phantom scans themselves — `.gitignore` excludes imaging.
> Commit only this spec and the CAD/print files if small.
