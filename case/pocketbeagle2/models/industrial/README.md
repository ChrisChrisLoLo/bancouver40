# PocketBeagle 2 Industrial — design files

PocketBeagle 2 Industrial (BeagleBoard part 100003007, ~US$50; standard PB2 is 102110780):
TI AM6254 (-40..85 °C), 1 GB DDR4, 64 GB eMMC populated, red PCB, pre-soldered headers.
BeagleBoard says the PCB layout is **unchanged** from PocketBeagle 2 Rev A, so the Rev A files below
apply. There is no Industrial-specific CAD in the official repo.

Source: <https://openbeagle.org/pocketbeagle/pocketbeagle-2> (main, CC BY-SA 4.0, © BeagleBoard.org Foundation),
pinout from docs.beagleboard.org `boards/pocketbeagle-2/04-expansion.rst`.

| File | What |
|---|---|
| `pocketbeagle2_sch.pdf` | Rev A schematic (Seeed, 2024-12-04); sheet 16 = P1/P2 headers |
| `pocketbeagle2 revA_dimension.pdf` | Rev A outline: 55 x 35 mm, header positions |
| `pocketbeagle2 revA_241205.brd` | Rev A layout (Cadence Allegro binary — KiCad can't import it) |
| `pocketbeagle2 v07_3D.FCStd` | BeagleBoard's newest 3D model (v07, pre-Rev A, no header pins) |
| `pocketbeagle2_v07.step` | that model converted to STEP (FreeCAD console, no colours); same origin as `../pocketbeagle2_v03_21_EVT.stp` |
| `pb2_header_pinout.csv` | P1/P2 pin, GPIO, ball, pad register, modes 0-9 (from the docs); power/analog/reset pins taken from the schematic |
| `PocketBeagle-2-P1.svg`, `-P2.svg` | official pinout diagrams |
| `pocketbeagle-2.syscfg` | TI SysConfig pinmux |
| `PCN_PocketBeagle_2_20250226.pdf` | AM6232 -> AM6254 change |
| `04-expansion.rst` | docs source of the pinout tables (has typos in its power-pin rows; trust the schematic) |

Not verified: whether the Industrial's pre-soldered headers are the same 8.5 mm female sockets as the
standard board's (the fit-check case assumes they are).

Not in git (too large; regenerate or download): `pocketbeagle2_v07.step` (110 MB; convert `pocketbeagle2 v07_3D.FCStd`
with FreeCAD, or use `mech/pb2_envelope.step`), `pocketbeagle2 revA_241205.brd` (49 MB; download from the OpenBeagle
repo's `design/` folder).
