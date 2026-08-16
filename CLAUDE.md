# CLAUDE.md — working rules for this repo

Rules established while designing this case. They exist because most of them
were learned from a failure, and the failure is noted where it applies.

## Every revision, without being asked

1. Bump the version: copy `src/geomNN.py` to `geomNN+1.py`, change parameters there.
   Never edit a released revision in place.
2. Run the single build script — it is the only path to shipped files:
   ```
   python3 src/build.py geom14 v14
   ```
3. It regenerates **all** of: views PNG, schematic PNG, README.md, colour 3MF,
   both STLs. Never generate one without the others.
4. Copy the output into `revisions/vNN/` and refresh the aliases in the repo root.

> **Why one script.** Around v5–v6 the exporter's import line was edited by hand
> and silently kept pointing at the old geometry module. Two revisions shipped
> stale files that were printed before anyone noticed. Nothing may reintroduce a
> path where the pictures and the printable files come from different models.

## Verification is part of the build, not a manual step

The build asserts and records these in the README:

| Check | Requirement |
|---|---|
| Case and lid meshes | closed, one body each |
| Lid protruding outside the case shell | must be 0.00 mm³ |
| Interference through the full slide travel | clear apart from the catch |
| Shipped 3MF reloaded vs model volume | must match |

If any regress, fix before shipping. Report the numbers, don't assert "verified".

## Writing rules

- The README opens with **why the model was built**, then what it is.
- Never use "watertight" in user-facing text. It is the mesh-topology term and
  reads as a waterproofing claim. Say "closed mesh, one body".
- Every number in the README is interpolated from the geometry module at build
  time. No hand-typed dimensions — they go stale.
- State the cleaning routine: warm water regularly, finished with an alcohol
  wipe, never submerged, never hot (PLA softens at 55–60 °C).

## Design invariants — don't break these silently

- **Flat base.** No chamfer on the bottom edge. The full footprint meets the
  plate. *(v4 lifted off the plate mid-print because of a 1 mm bottom chamfer.)*
- **Uniform wall.** Every profile is an offset of one outline, so the wall is
  identical on the flats and the diagonals. *(v6 had 3.4 mm flats but 1.91 mm
  diagonals, and the lid corners broke through.)*
- **Overhangs ≥ 45°.** The rail chamfer runs the full rail depth, giving ~56°.
  Never let it end in a feather edge.
- **Feature sizes on line-width multiples** (0.4 mm). Fractional widths get weak
  gap-fill beads.
- **The spring slot stays at 1.5 mm.** It is deliberately taller than bridge sag
  so the strip cannot fuse to the wall below. Never shrink it to quiet a slicer
  warning, and never add supports inside it — they cannot be removed and would
  jam the catch.
- **Outer dimensions land on whole millimetres**; the cavity is the fixed
  quantity and wall/floor thicknesses absorb the difference.
- **Catch tuning.** Net engagement = `det_h − 2 × clr`. Changing clearance
  changes the catch force; adjust `det_h` to compensate rather than letting it
  drift.

## Printing

Bambu Lab A1, 0.4 nozzle, 0.20 mm layers, 4 wall loops, no supports, 5 mm brim.
PLA Basic — white body, orange lid. PETG if the case needs to be washable.
Both parts print flat as laid out in the 3MF; no rotation.

Decline auto-support if the slicer offers it for the spring slot region. The
"floating cantilever" warning there is expected: the strip is a 30 mm bridge
anchored at both ends, not a cantilever.

## G-code

Not generated here. G-code is specific to the printer, filament and calibration
state, so it is sliced locally from the 3MF and dropped into `gcode/` if wanted.
